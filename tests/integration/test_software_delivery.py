"""Real Git/PostgreSQL/Node proof of software delivery and an isolated HTTP runtime."""
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import socket
import subprocess
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import UUID, uuid4
from zipfile import ZipFile
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from test_work_delivery import (clean_schema, create_asset, bind, _GuidedDesignSemanticCapability,
    _SchedulingOrchestrator, _GeneralProductDesignCapability)
from test_wic_governed_work_admission import _UnguidedSemanticCapability
from spg.api import create_http_application
from spg.application.assets import RepositoryAssetService
from spg.domain.assets import RepositoryIntakeRequest
from spg.application.delivery import DeliveryApplicationService, read_artifact
from spg.application.software_runtime import SoftwareRuntimeService
from spg.application.interaction import WorkInteractionService
from spg.application.guided_design import GuidedDesignApplicationService
from spg.application.work import WorkApplicationService
from spg.application.steering_bootstrap import SteeringBootstrapService
from spg.application.steering_driver import PlanSteeringDriver
from spg.domain.change import ProductionTargetKind
from spg.domain.planning import PlannedArtifactOperation
from spg.domain.delivery import DeliveryTargetRequest, HumanAcceptanceRequest
from spg.domain.steering import SemanticProductionProposal
from spg.domain.product import AttentionAction, AttentionKind, AttentionResolutionRequest, ProductInvariantViolation, ProductRecordNotFound
from spg.domain.execution import ProviderReportedOutcome
from spg.providers.contract_verifier import ContractDrivenRepositoryVerifier
from spg.providers.deterministic_executor import (DeterministicTestExecutor, DeterministicExecutionSpecification,
    DeterministicFileOperation, DeterministicFileOperationType)
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.github_delivery_schema import remote_delivery_authorizations

pytestmark = pytest.mark.postgresql
SOURCE = {
    'index.html': '<!doctype html><html><body><h1>Inventory</h1><script src="inventory.js"></script></body></html>\n',
    'inventory.js': 'function low(q, threshold) { return q < threshold; }\nif (typeof module !== "undefined") module.exports = {low};\n',
    'tests/inventory.test.cjs': 'const {test}=require("node:test"); const assert=require("node:assert/strict"); const {low}=require("../inventory.js");\ntest("threshold boundary",()=>{assert.equal(low(1,2),true); assert.equal(low(2,2),false);});\n',
}
FULL_APP_RUNTIME_FILES = {
    'Dockerfile': 'FROM python:3.13 AS native-verification\nCOPY . /app\n',
    'pyproject.toml': '[project]\nname="inventory"\nversion="0.1"\n',
    'uv.lock': 'version = 1\n',
    'alembic.ini': '[alembic]\nscript_location = migrations\n',
    'docker/start_app.py': 'print("started")\n',
    'migrations/versions/001.py': 'revision = "001"\n',
}

class SoftwareIntent(_GeneralProductDesignCapability):
    def interpret(self, basis):
        return super().interpret(basis).model_copy(update={'desired_outcome': 'Implement a runnable inventory application with tested low-stock rules'})

class SoftwareDesign(_GuidedDesignSemanticCapability):
    def execute(self, input):
        if input.design_context is None:
            assert input.approved_artifact_references
            result = _UnguidedSemanticCapability().execute(input)
        else:
            result = super().execute(input)
        if result.proposed_production:
            if input.approved_artifact_references:
                proposal = SemanticProductionProposal(
                    target_kind=ProductionTargetKind.CODE_WORK,
                    objective='Implement the reviewed inventory behavior with executable tests',
                    code_targets=tuple(SOURCE),
                    verification_expectation='Node tests independently prove threshold boundary behavior',
                )
            else:
                design_target = result.proposed_production.artifact_targets[0].model_copy(
                    update={'path': 'docs/design.md', 'operation': PlannedArtifactOperation.CREATE}
                )
                proposal = result.proposed_production.model_copy(
                    update={'artifact_targets': (design_target,)}
                )
            result = result.model_copy(update={'proposed_production': proposal})
        return result

def produce(database, tmp_path, *, failing=False, user_repository=True,
            authorize_candidate=True, set_delivery_target=True,
            full_application_baseline=False, human_requirement=None, product_id=None,
            intent_capability=None, design_capability=None, design_content=None):
    interaction = WorkInteractionService(database, capability=intent_capability or SoftwareIntent())
    item = interaction.create_interaction(human_identity='human:test', product_id=product_id)
    understanding = interaction.append_and_assess(item.id,
        human_requirement or 'Build an inventory application in these exact output files: ' + ', '.join(SOURCE),
        human_identity='human:test')
    service = WorkApplicationService(database, workspace_root=tmp_path/'workspaces')
    work = service.admit_interaction_work(item.id, assessment_id=understanding.latest_assessment.id,
        basis_fingerprint=understanding.latest_assessment.basis_fingerprint, authority_identity='human:test', use_default_resource=False)
    if product_id is None:
        assert work.engineering_scope.bindings == ()
    assets = RepositoryAssetService(database, tmp_path/'assets', tmp_path/'imports')
    if user_repository:
        if full_application_baseline:
            source = tmp_path / 'imports' / 'full-application'
            source.mkdir(parents=True)
            subprocess.run(['git', 'init', '-b', 'main'], cwd=source, check=True,
                capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Delivery Test'],
                cwd=source, check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'delivery@example.invalid'],
                cwd=source, check=True, capture_output=True)
            for path, content in {'README.md': '# Inventory\n',
                                  **FULL_APP_RUNTIME_FILES}.items():
                destination = source / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(content)
            subprocess.run(['git', 'add', '.'], cwd=source, check=True,
                capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'runtime baseline'],
                cwd=source, check=True, capture_output=True)
            asset = assets.intake(RepositoryIntakeRequest(request_id=uuid4(),
                title='Full application', description='Bounded Watt runtime',
                source=str(source), authority_identity='human:test'))
        else:
            asset = create_asset(assets, 'Software')
        work = bind(service, work, asset)
    sources = dict(SOURCE)
    if failing:
        sources['inventory.js'] = sources['inventory.js'].replace('q < threshold', 'q <= threshold')
    design_executor = DeterministicTestExecutor(DeterministicExecutionSpecification(
        operations=(DeterministicFileOperation(
            operation=DeterministicFileOperationType.CREATE,
            repository_relative_path='docs/design.md',
            content=design_content or '# Inventory application design\n\nImplement a tested low-stock boundary.\n',
        ),),
        reported_outcome=ProviderReportedOutcome.SUCCESS,
    ))
    design_service = WorkApplicationService(
        database, workspace_root=tmp_path/'workspaces', executor=design_executor,
        verifier=ContractDrivenRepositoryVerifier(database),
    )
    SteeringBootstrapService(database).bootstrap(work.work_id)
    design_driver = PlanSteeringDriver(
        database, design_service, _SchedulingOrchestrator(),
        semantic_capability=design_capability or SoftwareDesign(), max_automatic_transitions=32,
    )
    design_driver.activate(work.work_id)
    for attention in design_service.list_attention(work_id=work.work_id):
        if attention.kind is AttentionKind.PRODUCTION_PROPOSAL_REVIEW:
            design_service.resolve_attention(attention.id, AttentionResolutionRequest(
                action=AttentionAction.APPROVE, authority_identity='human:test',
            ))
            design_driver.activate(work.work_id)
    for _ in range(20):
        design_service.advance_work(work.work_id)
        for attention in design_service.list_attention(work_id=work.work_id):
            if attention.kind is AttentionKind.CANDIDATE_AUTHORIZATION:
                design_service.resolve_attention(attention.id, AttentionResolutionRequest(
                    action=AttentionAction.AUTHORIZE, authority_identity='human:test',
                ))
        if GuidedDesignApplicationService(database).approved_design_artifact_references(work.work_id):
            break
    assert GuidedDesignApplicationService(database).approved_design_artifact_references(work.work_id)
    design_driver.shutdown()

    executor = DeterministicTestExecutor(DeterministicExecutionSpecification(operations=tuple(
        DeterministicFileOperation(operation=DeterministicFileOperationType.CREATE, repository_relative_path=path, content=content)
        for path, content in sources.items()), reported_outcome=ProviderReportedOutcome.SUCCESS))
    service = WorkApplicationService(database, workspace_root=tmp_path/'workspaces', executor=executor, verifier=ContractDrivenRepositoryVerifier(database))
    driver = PlanSteeringDriver(database, service, _SchedulingOrchestrator(), semantic_capability=design_capability or SoftwareDesign(), max_automatic_transitions=32)
    initial_activation = driver.activate(work.work_id)
    assert initial_activation.stop_reason.value in {'PRODUCTION_RUNNING', 'HUMAN_ATTENTION'}, [item.reason for item in service.list_attention(work_id=work.work_id)]
    production_reviews = tuple(
        item for item in service.list_attention(work_id=work.work_id)
        if item.kind is AttentionKind.PRODUCTION_PROPOSAL_REVIEW
    )
    if production_reviews:
        service.resolve_attention(
            production_reviews[0].id,
            AttentionResolutionRequest(
                action=AttentionAction.APPROVE,
                authority_identity='human:test',
            ),
        )
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
    assert result.repository_state == 'SEALED_CANDIDATE', (
        service.get_work(work_id).status,
        service.get_work(work_id).production_plan,
        [item.kind.value for item in service.list_attention(work_id=work_id)],
        result.remaining_blocker_or_risk,
    )
    assert not result.trusted_result
    context = delivery.candidate_context(work_id)
    assert context is not None and context['authorization_pending']
    assert context['entrypoint'] == 'index.html'
    assert 'index.html' in delivery.candidate_code_diff(work_id, context['candidate_fingerprint'])
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


def test_required_guardian_static_review_precedes_explicit_acceptance(postgres_database, tmp_path):
    import time
    from guardian.runtime import JsonSoftwareAssuranceStore
    from spg.application.candidate_preview import CandidatePreviewApplicationService
    from spg.application.guardian_assurance import GuardianAssuranceClient
    from spg.infrastructure.candidate_preview_runtime import DockerCandidatePreviewRuntime
    from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore

    service, work_id, delivery, _ = produce(postgres_database, tmp_path,
        authorize_candidate=False, set_delivery_target=False)
    owner = JsonSoftwareAssuranceStore(tmp_path / 'guardian-owner')
    preview = CandidatePreviewApplicationService(delivery,
        JsonProductionEnvironmentStore(tmp_path / 'preview-state'),
        DockerCandidatePreviewRuntime(tmp_path / 'preview-runtime', docker_binary='must-not-use-docker'))
    assurance = GuardianAssuranceClient(delivery, preview.store, owner)
    preview.assurance_client = assurance
    delivery.guardian_assurance_client = assurance
    delivery.candidate_runtime_probe = preview.require_served_for_delivery
    service.configure_candidate_review(preview.prepare_review, preview.review_ready, preview.review_state)
    context = delivery.candidate_context(work_id)
    assert not preview.review_ready(work_id, UUID(context['candidate_id']))
    assert not any(a.kind is AttentionKind.CANDIDATE_AUTHORIZATION for a in service.list_attention(work_id=work_id))
    try:
        service.prepare_candidate_review(work_id)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not assurance.passed(work_id, UUID(context['candidate_id'])):
            time.sleep(.05)
        projection = assurance.projection(work_id)
        assert projection['gate'] == 'PASS', projection
        assert len(projection['required_pwu_ids']) == 1
        assert list((owner.root / 'results').glob('*.json'))
        assert not service.get_work_result(work_id).trusted_result
        authority = next(a for a in service.list_attention(work_id=work_id)
            if a.kind is AttentionKind.CANDIDATE_AUTHORIZATION)
        service.resolve_attention(authority.id, AttentionResolutionRequest(
            action=AttentionAction.AUTHORIZE, authority_identity='human:qualification'))
        for _ in range(8):
            service.advance_work(work_id)
            if service.get_work_result(work_id).trusted_result:
                break
        assert service.get_work_result(work_id).trusted_result
        manifest = delivery.publish(work_id)
        assert manifest.repository_revision == context['repository_revision']
        assert delivery.view(work_id)['deliveries'][0]['acceptance'] is None
        request = HumanAcceptanceRequest(manifest_fingerprint=manifest.fingerprint,
            decision='ACCEPT', authority_identity='human:qualification', rationale='Review exact qualified result')
        acceptance = delivery.decide(work_id, manifest.id, request)
        assert acceptance.decision.value == 'ACCEPT'
        assert delivery.decide(work_id, manifest.id, request).id == acceptance.id
    finally:
        preview.shutdown()


def test_script_only_code_candidate_exposes_review_diff(postgres_database, tmp_path, monkeypatch):
    # A functional Preview can be based on the unchanged entrypoint. Review
    # availability must follow the Code Work Candidate, not changed HTML files.
    unchanged_entrypoint = SOURCE['index.html']
    monkeypatch.delitem(SOURCE, 'index.html')
    def asset_with_entrypoint(assets, title):
        # Capture the entrypoint in the imported baseline before Work binding;
        # it is intentionally absent from the produced change set.
        source = tmp_path / 'imports' / 'static-baseline'
        source.mkdir(parents=True)
        for args in [('init', '-b', 'main'), ('config', 'user.name', 'Delivery Test'),
                     ('config', 'user.email', 'delivery@example.invalid')]:
            subprocess.run(['git', '-C', str(source), *args], check=True, capture_output=True)
        (source / 'README.md').write_text('# Software\n')
        (source / 'index.html').write_text(unchanged_entrypoint)
        subprocess.run(['git', '-C', str(source), 'add', '.'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(source), 'commit', '-m', 'Static baseline'], check=True, capture_output=True)
        return assets.intake(RepositoryIntakeRequest(request_id=uuid4(), title=title,
            description='Exact unchanged static entrypoint', source=str(source), authority_identity='human:test'))
    monkeypatch.setattr(__import__(__name__, fromlist=['create_asset']), 'create_asset', asset_with_entrypoint)
    service, work_id, delivery, _ = produce(
        postgres_database, tmp_path, authorize_candidate=False, set_delivery_target=False)
    context = delivery.candidate_context(work_id)
    assert context['preview_kind'] == 'STATIC_WEB'
    assert context['entrypoint'] == 'index.html'
    diff = delivery.candidate_code_diff(work_id, context['candidate_fingerprint'])
    assert 'inventory.js' in diff

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


def test_full_application_delivery_uses_exact_served_candidate_for_acceptance(
    postgres_database, tmp_path,
):
    service, work_id, delivery, _ = produce(postgres_database, tmp_path,
        set_delivery_target=False, full_application_baseline=True)
    assert service.get_work_result(work_id).trusted_result
    context = delivery.context(work_id)
    assert context['target']['runtime_recipe'] == {
        'adapter': 'FULL_APPLICATION_RUNTIME', 'entrypoint': None}
    manifest = delivery.publish(work_id)
    assert manifest.software.runtime_recipe.adapter == 'FULL_APPLICATION_RUNTIME'
    assert {item.path for item in manifest.artifacts} >= set(FULL_APP_RUNTIME_FILES)
    acceptance = HumanAcceptanceRequest(manifest_fingerprint=manifest.fingerprint,
        decision='ACCEPT', authority_identity='human:test',
        rationale='Reviewed the exact served application')
    with pytest.raises(ProductInvariantViolation, match='exact served Candidate'):
        delivery.decide(work_id, manifest.id, acceptance)
    calls = []
    delivery.full_application_runtime_probe = lambda *args: calls.append(args)
    decision = delivery.decide(work_id, manifest.id, acceptance)
    assert decision.decision.value == 'ACCEPT'
    assert calls[0][0] == work_id
    assert calls[0][2] == manifest.repository_revision
    with postgres_database.unit_of_work() as uow:
        remote_count = uow.session.execute(select(func.count()).select_from(
            remote_delivery_authorizations)).scalar_one()
    assert remote_count == 0
    if receipt_path := os.environ.get('WATT_GUARDIAN_QUALIFICATION_RECEIPT'):
        destination = Path(receipt_path).with_name('Q4-acceptance-delivery-boundary.json')
        destination.write_text(json.dumps({
            'work_id': str(work_id), 'manifest_id': str(manifest.id),
            'candidate_revision': manifest.repository_revision,
            'human_acceptance_id': str(decision.id), 'human_acceptance': 'ACCEPT',
            'remote_delivery_authorization_count': remote_count,
            'guardian_pass_receipt': str(Path(receipt_path).name),
        }, indent=2) + '\n', encoding='utf-8')

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


def test_preview_package_exact_lineage_and_invalid_delivery_fail_closed(postgres_database, tmp_path):
    """Software packaging must use the joined exact tree, not summary document paths."""
    from spg.domain.delivery import DeliveryPublicationRequest
    from spg.infrastructure.persistence.delivery_schema import work_delivery_manifests
    from sqlalchemy import update
    from uuid import uuid4
    service, work_id, delivery, assets = produce(postgres_database, tmp_path, set_delivery_target=False)
    context = delivery.candidate_context(work_id)
    basis = DeliveryPublicationRequest(candidate_fingerprint=context['candidate_fingerprint'],
        repository_revision=context['repository_revision'])
    with pytest.raises(ProductInvariantViolation, match='stale'):
        delivery.publish(work_id, basis.model_copy(update={'repository_revision':'0'*40}))
    manifest = delivery.publish(work_id, basis)
    assert manifest.software.runtime_recipe.adapter == 'STATIC_WEB'
    assert manifest.repository_revision == context['repository_revision']
    assert manifest.software.runtime_recipe.entrypoint == context['entrypoint']
    assert {'index.html', 'inventory.js', 'tests/inventory.test.cjs'} <= {a.path for a in manifest.artifacts}
    from unittest.mock import patch
    with patch.object(delivery, 'package', side_effect=AssertionError('read must not package')), patch.object(delivery, 'publish', side_effect=AssertionError('read must not publish')):
        assert delivery.view(work_id)['deliveries'][0]['manifest']['id'] == str(manifest.id)
        assert delivery.context(work_id)['trusted']
    bundle = delivery.package(work_id, manifest.id)
    with ZipFile(BytesIO(bundle)) as archive:
        assert json.loads(archive.read('delivery-manifest.json'))['repository_revision'] == context['repository_revision']
        assert json.loads(archive.read('delivery-target.json'))['kind'] == 'SOFTWARE_ARTIFACT'
        assert sorted(n for n in archive.namelist() if n.startswith('source/')) == sorted('source/'+a.path for a in manifest.artifacts)
        for artifact in manifest.artifacts:
            data = archive.read('source/'+artifact.path)
            assert len(data) == artifact.size_bytes
            assert sha256(data).hexdigest() == artifact.sha256
        assert archive.read('source/index.html') == delivery.candidate_artifact(work_id, context['candidate_fingerprint'], 'index.html')
    # Durable exact Git/manifest packaging is independent of the application process.
    restored = DeliveryApplicationService(postgres_database)
    assert restored.package(work_id, manifest.id) == bundle
    with pytest.raises(ProductInvariantViolation, match='stale'):
        restored.candidate_download(work_id, '0'*64, 'index.html')
    with pytest.raises(ProductRecordNotFound, match='manifest not found'):
        restored.package(uuid4(), manifest.id)
    def replace(payload):
        with postgres_database.unit_of_work() as u:
            u.session.execute(update(work_delivery_manifests).where(work_delivery_manifests.c.id==manifest.id).values(payload=payload))
            u.commit()
    original = manifest.model_dump(mode='json')
    corrupt = dict(original, repository_revision='0'*40)
    replace(corrupt)
    with pytest.raises(ProductInvariantViolation, match='lineage'):
        restored.package(work_id, manifest.id)
    from spg.application.delivery import fingerprint
    corrupt = manifest.model_dump(mode='json')
    corrupt['artifacts'][0]['sha256']='0'*64
    corrupt['fingerprint']=fingerprint({k:v for k,v in corrupt.items() if k not in {'id','fingerprint','created_at'}})
    replace(corrupt)
    with pytest.raises(ProductInvariantViolation, match='bytes differ'):
        restored.package(work_id, manifest.id)
    corrupt = manifest.model_dump(mode='json')
    corrupt['artifacts']=[a for a in corrupt['artifacts'] if a['path']!='index.html']
    corrupt['fingerprint']=fingerprint({k:v for k,v in corrupt.items() if k not in {'id','fingerprint','created_at'}})
    replace(corrupt)
    with pytest.raises(ProductInvariantViolation, match='source tree'):
        restored.package(work_id, manifest.id)
    replace(original)
    assert restored.package(work_id, manifest.id)==bundle


def test_historical_document_target_cannot_silently_publish_a_governed_site(postgres_database, tmp_path):
    service, work_id, delivery, assets = produce(postgres_database, tmp_path, set_delivery_target=False)
    target = delivery.set_target(work_id, DeliveryTargetRequest(kind='DOCUMENT_PACKAGE',
        title='Early document target', acceptance_criteria=('Read documentation',),authority_identity='human:test'))
    with pytest.raises(ProductInvariantViolation, match='conflicts with governed software'):
        delivery.publish(work_id)
    view=delivery.view(work_id)
    assert view['target']['id']==str(target.id)
    assert view['target']['kind']=='DOCUMENT_PACKAGE'
    assert view['deliveries']==[]
