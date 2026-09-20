"""Real Git/PostgreSQL/Node proof of software delivery and an isolated HTTP runtime."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import socket
import subprocess
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import UUID
from zipfile import ZipFile
from fastapi.testclient import TestClient
import pytest

from test_work_delivery import (clean_schema, create_asset, bind, _GuidedDesignSemanticCapability,
    _SchedulingOrchestrator, _GeneralProductDesignCapability)
from spg.api import create_http_application
from spg.application.assets import RepositoryAssetService
from spg.application.delivery import DeliveryApplicationService, read_artifact
from spg.application.software_runtime import SoftwareRuntimeService
from spg.application.interaction import WorkInteractionService
from spg.application.work import WorkApplicationService
from spg.application.steering_bootstrap import SteeringBootstrapService
from spg.application.steering_driver import PlanSteeringDriver
from spg.domain.change import ProductionTargetKind
from spg.domain.delivery import DeliveryTargetRequest, HumanAcceptanceRequest
from spg.domain.steering import SemanticProductionProposal
from spg.domain.product import AttentionAction, AttentionKind, AttentionResolutionRequest, ProductInvariantViolation
from spg.domain.execution import ProviderReportedOutcome
from spg.providers.contract_verifier import ContractDrivenRepositoryVerifier
from spg.providers.deterministic_executor import (DeterministicTestExecutor, DeterministicExecutionSpecification,
    DeterministicFileOperation, DeterministicFileOperationType)
from spg.infrastructure.persistence.product_store import ProductStore

pytestmark = pytest.mark.postgresql
SOURCE = {
    'index.html': '<!doctype html><html><body><h1>Inventory</h1><script src="inventory.js"></script></body></html>\n',
    'inventory.js': 'function low(q, threshold) { return q < threshold; }\nif (typeof module !== "undefined") module.exports = {low};\n',
    'tests/inventory.test.cjs': 'const {test}=require("node:test"); const assert=require("node:assert/strict"); const {low}=require("../inventory.js");\ntest("threshold boundary",()=>{assert.equal(low(1,2),true); assert.equal(low(2,2),false);});\n',
}

class SoftwareIntent(_GeneralProductDesignCapability):
    def interpret(self, basis):
        return super().interpret(basis).model_copy(update={'desired_outcome': 'Implement a runnable inventory application with tested low-stock rules'})

class SoftwareDesign(_GuidedDesignSemanticCapability):
    def execute(self, input):
        result = super().execute(input)
        if result.proposed_production:
            result = result.model_copy(update={'proposed_production': SemanticProductionProposal(
                target_kind=ProductionTargetKind.CODE_WORK, objective='Implement the reviewed inventory behavior with executable tests',
                code_targets=tuple(SOURCE), verification_expectation='Node tests independently prove threshold boundary behavior')})
        return result

def produce(database, tmp_path, *, failing=False, user_repository=True,
            authorize_candidate=True, set_delivery_target=True):
    interaction = WorkInteractionService(database, capability=SoftwareIntent())
    item = interaction.create_interaction(human_identity='human:test')
    understanding = interaction.append_and_assess(item.id, 'Build an inventory application', human_identity='human:test')
    service = WorkApplicationService(database, workspace_root=tmp_path/'workspaces')
    work = service.admit_interaction_work(item.id, assessment_id=understanding.latest_assessment.id,
        basis_fingerprint=understanding.latest_assessment.basis_fingerprint, authority_identity='human:test', use_default_resource=False)
    assert work.engineering_scope.bindings == ()
    assets = RepositoryAssetService(database, tmp_path/'assets', tmp_path/'imports')
    if user_repository:
        asset = create_asset(assets, 'Software')
        work = bind(service, work, asset)
    sources = dict(SOURCE)
    if failing:
        sources['inventory.js'] = sources['inventory.js'].replace('q < threshold', 'q <= threshold')
    executor = DeterministicTestExecutor(DeterministicExecutionSpecification(operations=tuple(
        DeterministicFileOperation(operation=DeterministicFileOperationType.CREATE, repository_relative_path=path, content=content)
        for path, content in sources.items()), reported_outcome=ProviderReportedOutcome.SUCCESS))
    service = WorkApplicationService(database, workspace_root=tmp_path/'workspaces', executor=executor, verifier=ContractDrivenRepositoryVerifier(database))
    SteeringBootstrapService(database).bootstrap(work.work_id)
    driver = PlanSteeringDriver(database, service, _SchedulingOrchestrator(), semantic_capability=SoftwareDesign())
    driver.activate(work.work_id)
    attention = next(a for a in service.list_attention(work_id=work.work_id) if a.kind is AttentionKind.PRODUCTION_PROPOSAL_REVIEW)
    service.resolve_attention(attention.id, AttentionResolutionRequest(action=AttentionAction.APPROVE, authority_identity='human:test'))
    driver.activate(work.work_id)
    for _ in range(20):
        service.advance_work(work.work_id)
        for a in service.list_attention(work_id=work.work_id):
            if a.kind is AttentionKind.CANDIDATE_AUTHORIZATION and authorize_candidate:
                service.resolve_attention(a.id, AttentionResolutionRequest(action=AttentionAction.AUTHORIZE, authority_identity='human:test'))
        result = service.get_work_result(work.work_id)
        if (result.trusted_result or (not authorize_candidate and result.repository_state == 'SEALED_CANDIDATE')
                or service.get_work(work.work_id).status.value == 'BLOCKED'):
            break
    driver.shutdown()
    delivery = DeliveryApplicationService(database)
    if set_delivery_target:
        delivery.set_target(work.work_id, DeliveryTargetRequest(kind='SOFTWARE_ARTIFACT', title='Inventory', acceptance_criteria=('Low-stock boundary works',),
            authority_identity='human:test', software_form='WEB_APPLICATION', runtime_recipe={'adapter':'STATIC_WEB', 'entrypoint':'index.html'}))
    return service, work.work_id, delivery, assets

def test_exact_candidate_is_previewable_before_repository_authorization(postgres_database, tmp_path):
    service, work_id, delivery, _ = produce(
        postgres_database, tmp_path, authorize_candidate=False, set_delivery_target=False)
    result = service.get_work_result(work_id)
    assert result.repository_state == 'SEALED_CANDIDATE'
    assert not result.trusted_result
    context = delivery.candidate_context(work_id)
    assert context is not None and context['authorization_pending']
    assert context['entrypoint'] == 'index.html'
    assert context['verification'] and all(item.endswith(': PASS') for item in context['verification'])
    before = service.get_work_result(work_id)
    assert delivery.candidate_artifact(work_id, context['candidate_fingerprint'], 'index.html') == SOURCE['index.html'].encode()
    assert delivery.candidate_download(work_id, context['candidate_fingerprint'], 'index.html') == SOURCE['index.html'].encode()
    assert service.get_work_result(work_id) == before
    with pytest.raises(ProductInvariantViolation, match='stale'):
        delivery.candidate_artifact(work_id, '0' * 64, 'index.html')
    with pytest.raises(ProductInvariantViolation, match='stale'):
        delivery.candidate_download(work_id, '0' * 64, 'index.html')
    application = create_http_application(
        database=postgres_database,
        work_service=service,
    )
    with TestClient(application) as client:
        preview = client.post(f'/api/works/{work_id}/candidate-preview').json()
        response = client.get(preview['url'])
        assert response.status_code == 200
        policy = response.headers['Content-Security-Policy']
        assert "img-src 'self' data: blob: https:" in policy
        assert "script-src 'self' 'unsafe-inline'" in policy
        assert "connect-src 'none'" in policy
        assert "default-src *" not in policy
        assert "script-src *" not in policy

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]

def test_code_to_package_runtime_restore_and_explicit_acceptance(postgres_database, tmp_path):
    service, work_id, delivery, assets = produce(postgres_database, tmp_path)
    assert service.get_work_result(work_id).trusted_result
    manifest = delivery.publish(work_id)
    assert manifest.software and manifest.software.changed_files
    assert any(item['obligation'].startswith('NODE_TEST_TARGET:') for item in manifest.software.verification)
    assert all(item['result']=='PASS' for item in manifest.software.verification)
    assert delivery.publish(work_id).id == manifest.id
    bundle = delivery.package(work_id, manifest.id)
    assert delivery.package(work_id, manifest.id) == bundle
    with ZipFile(BytesIO(bundle)) as archive:
        assert 'verification.json' in archive.namelist()
        for artifact in manifest.artifacts:
            assert sha256(archive.read('source/'+artifact.path)).hexdigest() == artifact.sha256
        extract = tmp_path/'reproduce'; archive.extractall(extract)
    check = subprocess.run(['node','--test','tests/inventory.test.cjs'], cwd=extract/'source', capture_output=True)
    assert check.returncode == 0, check.stderr
    request = HumanAcceptanceRequest(manifest_fingerprint=manifest.fingerprint, decision='ACCEPT', authority_identity='human:test', rationale='Manually inspected test fixture')
    with pytest.raises(ProductInvariantViolation, match='accessible'):
        delivery.decide(work_id, manifest.id, request)
    runtime = SoftwareRuntimeService(delivery, enabled=True, first_port=free_port(), port_count=1)
    delivery.runtime_probe = runtime.probe
    try:
        with pytest.raises(ProductInvariantViolation, match='Start and inspect'):
            delivery.decide(work_id, manifest.id, request)
        ready = runtime.start(work_id, manifest.id)
        assert ready['status']=='READY'
        with urlopen(ready['url']) as response:
            assert response.read() == SOURCE['index.html'].encode()
            policy = response.headers['Content-Security-Policy']
            assert "img-src 'self' data: blob: https:" in policy
            assert "connect-src 'none'" in policy
            assert "script-src *" not in policy
        with pytest.raises(HTTPError):
            urlopen(ready['url'].replace('index.html','../.git/config'))
        with pytest.raises(HTTPError):
            urlopen(Request(ready['url'], headers={'Host':'untrusted.example'}))
        assert delivery.view(work_id)['deliveries'][0]['acceptance'] is None
        runtime.shutdown()
        assert runtime.view(work_id, manifest.id)['status']=='NOT_READY'
        runtime.restore()
        assert runtime.probe(work_id, manifest.id)['status']=='READY'
        assert delivery.decide(work_id, manifest.id, request).decision.value=='ACCEPT'
    finally:
        runtime.shutdown()


def test_work_without_user_repository_uses_managed_workspace_and_delivers(postgres_database, tmp_path):
    service, work_id, delivery, _ = produce(
        postgres_database,
        tmp_path,
        user_repository=False, set_delivery_target=False,
    )

    assert service.get_work_result(work_id).trusted_result
    projection = service.get_work(work_id)
    assert projection.engineering_scope is not None
    assert len(projection.engineering_scope.bindings) == 1
    with postgres_database.unit_of_work() as uow:
        product = ProductStore(uow.session)
        resource = product.resource_for_work(work_id)
        revision = product.current_work_reality_revision(work_id)
        assert resource is not None
        assert revision is not None
        assert resource.repository_identity.startswith("watt://repositories/")
        assert revision.change_set == ("execution-workspace:ALLOCATED",)
        assert revision.admitted_by == "system:watt-managed-execution-workspace"

    context = delivery.context(work_id)
    assert context['target_source'] == 'GOVERNED_REALITY'
    assert context['target']['runtime_recipe']['entrypoint'] == 'index.html'
    assert context['target']['acceptance_criteria'][0] == service.get_work(work_id).desired_outcome
    assert 'browser-runnable' in context['target']['acceptance_criteria'][-2]
    assert 'governed verification obligations' in context['target']['acceptance_criteria'][-1]
    assert context['verification'] and context['artifacts']
    manifest = delivery.publish(work_id)
    assert manifest.software is not None
    assert delivery.context(work_id)['target_source'] == 'GOVERNED_REALITY'
    assert {item.path for item in manifest.artifacts} >= set(SOURCE)
    with ZipFile(BytesIO(delivery.package(work_id, manifest.id))) as archive:
        assert archive.read("source/index.html") == SOURCE["index.html"].encode()
    runtime = SoftwareRuntimeService(
        delivery,
        enabled=True,
        first_port=free_port(),
        port_count=1,
    )
    try:
        ready = runtime.start(work_id, manifest.id)
        assert ready["status"] == "READY"
        with urlopen(ready["url"]) as response:
            assert response.read() == SOURCE["index.html"].encode()
            assert "script-src 'self' 'unsafe-inline'" in response.headers["Content-Security-Policy"]
    finally:
        runtime.shutdown()

def test_failing_behavior_test_cannot_publish_software(postgres_database, tmp_path):
    service, work_id, delivery, _ = produce(postgres_database, tmp_path, failing=True)
    assert not service.get_work_result(work_id).trusted_result
    with pytest.raises(ProductInvariantViolation, match='Verification'):
        delivery.publish(work_id)

def test_software_blob_reader_rejects_links_and_traversal(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True).stdout.decode().strip()
    git('init','-b','main');(repo/'index.html').write_text('<html></html>\n');(repo/'secret.txt').write_text('fixture\n')
    git('add','.');git('-c','user.name=Test','-c','user.email=test@localhost','commit','-m','fixture')
    revision=git('rev-parse','HEAD')
    assert read_artifact(str(repo),revision,'index.html',software=True)
    for path in ['../secret.txt','.git/config','x//index.html','/index.html','index.html\x00']:
        with pytest.raises(ProductInvariantViolation):read_artifact(str(repo),revision,path,software=True)
    blob=git('rev-parse',revision+':secret.txt')
    git('update-index','--add','--cacheinfo','120000',blob,'linked.html')
    git('-c','user.name=Test','-c','user.email=test@localhost','commit','-m','link fixture')
    with pytest.raises(ProductInvariantViolation,match='regular Git blob'):
        read_artifact(str(repo),git('rev-parse','HEAD'),'linked.html',software=True)
