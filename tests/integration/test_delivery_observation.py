"""GC delivery resolver divergence: real PostgreSQL/Git production and HTTP bytes."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import subprocess
from uuid import UUID, uuid4
from zipfile import ZipFile
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import insert, select, update
from spg.api.http import create_http_application
from spg.application.bootstrap import Application
from spg.application.delivery import DeliveryApplicationService, fingerprint
from spg.application.delivery_observation import DeliveryObservationService
from spg.config import Settings
from spg.evaluation.production_trace import ProductionTraceService
from spg.evaluation.service import QualityService
from spg.infrastructure.persistence import metadata
from tests.integration.test_work_delivery import clean_schema
from tests.integration.test_software_delivery import produce

pytestmark=pytest.mark.postgresql


def client(db, service, tmp_path):
    settings=Settings(admin_enabled=True,auth_mode='test-only-disabled',owner_runtime_mode='OFF',
        native_executor_enabled=False,managed_source_provider='gitea',
        managed_source_endpoint='http://gitea.fixture.invalid',managed_source_username='watt-managed',
        managed_source_password='fixture-only',owner_runtime_store_root=tmp_path/'owner',
        native_executor_production_environment_store_root=tmp_path/'preview')
    return TestClient(create_http_application(Application(settings),database=db,work_service=service)),settings


def action(db,wid,response):
    with db.unit_of_work() as u:
        pid=u.session.scalar(select(metadata.tables['product_works'].c.product_id).where(metadata.tables['product_works'].c.id==wid))
    events=DeliveryObservationService(db).for_work(wid,pid)
    identity=response.headers['x-watt-delivery-action-id']
    return next(a for a in events if a['action_id']==identity)


def assert_response(a,r):
    assert a['response']['byte_size']==len(r.content)
    assert a['response']['sha256']==sha256(r.content).hexdigest()
    assert a['request_id']==r.headers['x-watt-request-id']
    assert a['audit_record_valid']
    assert a['response']['client_received']==a['response']['client_saved']=='UNAVAILABLE'


def test_current_delivery_response_lineage_repeat_failures_and_trace_read_only(postgres_database,tmp_path,monkeypatch):
    db=postgres_database;service,wid,delivery,_=produce(db,tmp_path,set_delivery_target=False)
    manifest=delivery.publish(wid);c,s=client(db,service,tmp_path)
    base=f'/api/works/{wid}/deliveries/{manifest.id}'
    initiating=str(uuid4())
    r=c.get(base+'/download',params={'initiating_action_id':initiating,'surface':'DELIVERABLE'})
    assert r.status_code==200,r.text[:100];a=action(db,wid,r);assert_response(a,r)
    assert a['phases']==['USER_ACTION_INITIATED','SERVER_RESOLVED','SERVER_SERVED']
    assert a['initiating_action_id']==initiating and a['surface_basis']=='CLIENT_DECLARED'
    assert a['classification']=='PASS' and a['resolver_policy']=='AUTHORIZED_RUNTIME_DELIVERY'
    assert a['selected']['manifest_id']==str(manifest.id)
    assert a['selected']['runtime_commit_id']==str(manifest.runtime_commit_id)
    assert a['selected']['revision']==manifest.repository_revision
    assert a['response']['returned_filename'].endswith('.zip')
    assert a['response']['content_type']=='application/zip'
    with ZipFile(BytesIO(r.content)) as z:
        files={i['path']:i for i in a['inventory']['files']}
        for item in manifest.artifacts:
            assert files['source/'+item.path]['sha256']==item.sha256
            assert sha256(z.read('source/'+item.path)).hexdigest()==item.sha256
    repeat=c.get(base+'/download');b=action(db,wid,repeat);assert_response(b,repeat)
    assert r.content==repeat.content and a['action_id']!=b['action_id']
    item=c.get(base+'/artifact',params={'path':'index.html'});assert item.status_code==200
    ia=action(db,wid,item);assert_response(ia,item)
    assert ia['expected']['payload_sha256']==sha256(item.content).hexdigest()
    candidate=delivery.candidate_context(wid)
    cr=c.get(f"/api/works/{wid}/candidate-download/{candidate['candidate_fingerprint']}/index.html")
    assert cr.status_code==200 and cr.content==item.content
    ca=action(db,wid,cr);assert_response(ca,cr);assert ca['selected']['candidate_id']==candidate['candidate_id']
    missing=c.get(f'/api/works/{wid}/deliveries/{uuid4()}/download')
    assert missing.status_code==404
    ma=action(db,wid,missing);assert_response(ma,missing)
    assert ma['phases']==['USER_ACTION_INITIATED','SERVER_NOT_SERVED']
    assert ma['classification']=='NOT_SERVED' and ma['response']['error_code']=='NOT_FOUND'
    bad_candidate=c.get(f'/api/works/{wid}/candidate-download/'+('0'*64)+'/index.html')
    assert bad_candidate.status_code==409 and action(db,wid,bad_candidate)['classification']=='NOT_SERVED'
    table=metadata.tables['work_delivery_manifests'];original=manifest.model_dump(mode='json')
    for corrupt in [dict(original,repository_revision='0'*40),dict(original,runtime_commit_id=str(uuid4())),
            {**original,'artifacts':[{**x,'sha256':'0'*64} for x in original['artifacts']]}]:
        if corrupt['repository_revision']==manifest.repository_revision and corrupt['runtime_commit_id']==str(manifest.runtime_commit_id):
            corrupt['fingerprint']=fingerprint({k:v for k,v in corrupt.items() if k not in {'id','fingerprint','created_at'}})
        with db.engine.begin() as conn:conn.execute(update(table).where(table.c.id==manifest.id).values(payload=corrupt))
        rejected=c.get(base+'/download');assert rejected.status_code==409,rejected.text
        ra=action(db,wid,rejected);assert_response(ra,rejected)
        assert ra['classification']=='NOT_SERVED' and ra['phases'][-1]=='SERVER_NOT_SERVED'
    with db.engine.begin() as conn:conn.execute(update(table).where(table.c.id==manifest.id).values(payload=original))
    def forbidden(*a,**k):raise AssertionError('ordinary Trace must not build or hash packages')
    monkeypatch.setattr(DeliveryApplicationService,'package',forbidden)
    monkeypatch.setattr(DeliveryApplicationService,'publish',forbidden)
    monkeypatch.setattr(DeliveryApplicationService,'artifact',forbidden)
    t=ProductionTraceService(db,s,QualityService(db,s)).entity_trace('work',wid,detail=False)
    assert t['served_delivery']['historical_action_identity']=='NOT_RECORDED'
    assert any(x['action_id']==a['action_id'] for x in t['served_delivery']['actions'])
    assert not t['acceptance']
    # An application re-composition reads the same durable append-only facts.
    assert action(db,wid,r)['response']==a['response']
    c.close()


def test_gc_official_old_baseline_is_legitimate_but_authorized_stale_export_diverges(postgres_database,tmp_path,monkeypatch):
    """Historic accident shape: produced/verified/authorized HTML but Product v0 README.

    Only provider transport uses a local Git fixture; actual Product resolver,
    canonical records, authorized production and HTTP export remain real.
    """
    from spg.infrastructure.managed_source_provider import GiteaManagedSourceProvider
    db=postgres_database;service,wid,delivery,_=produce(db,tmp_path,set_delivery_target=False)
    manifest=delivery.publish(wid);c,s=client(db,service,tmp_path)
    assert all(v['result']=='PASS' for v in manifest.software.verification)
    preview=c.post(f'/api/works/{wid}/candidate-preview')
    assert preview.status_code==200,preview.text
    entry=c.get(preview.json()['url'])
    assert entry.status_code==200 and entry.content==delivery.artifact(wid,manifest.id,'index.html')
    with db.unit_of_work() as u:
        p=__import__('spg.infrastructure.persistence.product_store',fromlist=['ProductStore']).ProductStore(u.session)
        binding=p.runtime_binding(wid);resource=p.resource(binding.resource_id)
        pid=u.session.scalar(select(metadata.tables['product_works'].c.product_id).where(metadata.tables['product_works'].c.id==wid))
    if pid is None:
        from spg.application.product_assets import ProductAssetService
        pid=UUID(ProductAssetService(db).create('human:owner','Golden resolver divergence',provision_source=False)['id'])
        with db.engine.begin() as conn:
            conn.execute(update(metadata.tables['product_works']).where(metadata.tables['product_works'].c.id==wid).values(product_id=pid))
    repo=Path(resource.location_ref)
    baseline=subprocess.check_output(['git','-C',str(repo),'rev-list','--max-parents=0',manifest.repository_revision],text=True).strip()
    tree=subprocess.check_output(['git','-C',str(repo),'rev-parse',baseline+'^{tree}'],text=True).strip()
    with db.engine.begin() as conn:
        conn.execute(update(metadata.tables['software_products']).where(metadata.tables['software_products'].c.id==pid).values(owner_id='human:owner'))
        conn.execute(insert(metadata.tables['product_managed_sources']).values(product_id=pid,repository_identity=resource.repository_identity,
            provider_kind='gitea',provider_reference='local-exact-git',accepted_ref='accepted',accepted_revision=baseline,accepted_tree=tree,version=0,origin={}))
        conn.execute(insert(metadata.tables['product_source_versions']).values(id=uuid4(),product_id=pid,version=0,revision=baseline,tree=tree,authority_identity='human:owner'))
        conn.execute(insert(metadata.tables['work_source_bases']).values(work_id=wid,product_id=pid,resource_id=resource.id,source_version=0,source_revision=baseline,source_tree=tree,work_ref='refs/heads/work'))
    monkeypatch.setattr(GiteaManagedSourceProvider,'clone_access',lambda *a:{'url':'not-stored'})
    def materialize(self,reference,revision,destination,purpose):
        subprocess.run(['git','clone','--no-hardlinks',str(repo),str(destination)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(destination),'checkout','--detach',revision],check=True,capture_output=True)
    monkeypatch.setattr(GiteaManagedSourceProvider,'materialize',materialize)
    url=f'/api/products/{pid}/code-assets/export'
    legitimate=c.get(url,params={'action_semantic':'DOWNLOAD_OFFICIAL_PRODUCT_SOURCE','context_work_id':str(wid),'surface':'PRODUCT_SOURCE_EXPORT'})
    assert legitimate.status_code==200,legitimate.text
    la=action(db,wid,legitimate);assert_response(la,legitimate)
    assert la['classification']=='PASS' and la['resolver_policy']=='ACCEPTED_PRODUCT_BASELINE'
    assert la['selected']['revision']==baseline!=manifest.repository_revision
    with ZipFile(BytesIO(legitimate.content)) as z:assert z.namelist()==['README.md']
    wrong=c.get(url,params={'action_semantic':'DOWNLOAD_CURRENT_AUTHORIZED_DELIVERY','context_work_id':str(wid)})
    assert wrong.status_code==200;wa=action(db,wid,wrong);assert_response(wa,wrong)
    assert wa['classification']=='OBSERVED_DELIVERY_DIVERGENCE'
    assert wa['expected']['runtime_commit_id']==str(manifest.runtime_commit_id)
    assert wa['expected']['revision']==manifest.repository_revision and wa['selected']['revision']==baseline
    current=c.get(url,params={'revision':manifest.repository_revision,'action_semantic':'DOWNLOAD_CANDIDATE_SOURCE','context_work_id':str(wid)})
    assert current.status_code==200,current.text
    ca=action(db,wid,current);assert_response(ca,current);assert ca['classification']=='PASS'
    assert ca['selected']['candidate_id']==wa['expected']['candidate_id']
    assert ca['selected']['runtime_commit_id']==str(manifest.runtime_commit_id)
    assert 'not-stored' not in str(wa)
    assert delivery.view(wid)['deliveries'][0]['acceptance'] is None
    assert c.get(url,params={'revision':'api_key=private'}).status_code==409
    assert 'api_key=private' not in str(DeliveryObservationService(db).for_work(wid,pid))
    assert c.get(url,params={'context_work_id':str(uuid4())}).status_code==409
    assert c.get(url,params={'action_semantic':'DOWNLOAD_DELIVERY_ARTIFACT'}).status_code==409
    c.close()


def test_document_only_http_delivery_stays_document_and_preserves_acceptance(postgres_database,tmp_path):
    from tests.integration.test_work_delivery import admit_empty,create_asset,bind,DesignCapability,_SchedulingOrchestrator
    from spg.application.assets import RepositoryAssetService
    from spg.application.work import WorkApplicationService
    from spg.application.steering_bootstrap import SteeringBootstrapService
    from spg.application.steering_driver import PlanSteeringDriver
    from spg.domain.delivery import DeliveryTargetRequest
    from spg.domain.product import AttentionKind,AttentionAction,AttentionResolutionRequest
    from spg.domain.execution import ProviderReportedOutcome
    from spg.providers.deterministic_executor import DeterministicTestExecutor,DeterministicExecutionSpecification,DeterministicFileOperation,DeterministicFileOperationType
    from spg.providers.contract_verifier import ContractDrivenRepositoryVerifier
    db=postgres_database;work,projection=admit_empty(db,tmp_path)
    assets=RepositoryAssetService(db,tmp_path/'assets',tmp_path/'imports')
    projection=bind(work,projection,create_asset(assets,'Observed document delivery'))
    executor=DeterministicTestExecutor(DeterministicExecutionSpecification(operations=(DeterministicFileOperation(
        operation=DeterministicFileOperationType.CREATE,repository_relative_path='docs/design.md',
        content='# Governed document\n\nExact approved design.\n'),),reported_outcome=ProviderReportedOutcome.SUCCESS))
    service=WorkApplicationService(db,workspace_root=tmp_path/'workspaces',executor=executor,verifier=ContractDrivenRepositoryVerifier(db))
    SteeringBootstrapService(db).bootstrap(projection.work_id)
    driver=PlanSteeringDriver(db,service,_SchedulingOrchestrator(),semantic_capability=DesignCapability())
    driver.activate(projection.work_id)
    proposal=next(a for a in service.list_attention(work_id=projection.work_id) if a.kind is AttentionKind.PRODUCTION_PROPOSAL_REVIEW)
    service.resolve_attention(proposal.id,AttentionResolutionRequest(action=AttentionAction.APPROVE,authority_identity='human:test'))
    driver.activate(projection.work_id)
    for _ in range(20):
        service.advance_work(projection.work_id)
        for a in service.list_attention(work_id=projection.work_id):
            if a.kind is AttentionKind.CANDIDATE_AUTHORIZATION:service.resolve_attention(a.id,AttentionResolutionRequest(action=AttentionAction.AUTHORIZE,authority_identity='human:test'))
        if service.get_work_result(projection.work_id).trusted_result:break
    delivery=DeliveryApplicationService(db)
    delivery.set_target(projection.work_id,DeliveryTargetRequest(kind='DOCUMENT_PACKAGE',title='Document only',acceptance_criteria=('Inspect approved design',),authority_identity='human:test'))
    manifest=delivery.publish(projection.work_id);assert manifest.software is None
    c,_=client(db,service,tmp_path)
    response=c.get(f'/api/works/{projection.work_id}/deliveries/{manifest.id}/download')
    assert response.status_code==200,response.text
    a=action(db,projection.work_id,response);assert_response(a,response);assert a['classification']=='PASS'
    with ZipFile(BytesIO(response.content)) as z:
        assert 'artifacts/docs/design.md' in z.namelist()
        assert not any(p.startswith('source/') for p in z.namelist())
    assert not any(p['path'].startswith('source/') for p in a['inventory']['files'])
    assert delivery.view(projection.work_id)['deliveries'][0]['acceptance'] is None
    driver.shutdown();c.close()
