from datetime import timedelta
from uuid import uuid4
from dataclasses import replace
import pytest
from sqlalchemy import select, update
from fastapi import FastAPI
from fastapi.testclient import TestClient
from alembic.config import Config
from alembic import command
from spg.config import Settings
from spg.evaluation.contracts import *
from spg.evaluation.catalog import definitions, create_fresh_holdout, import_core
from spg.evaluation.service import QualityService, now
from spg.evaluation.operations import OperationsService
from spg.api.admin import install_admin
from spg.api.authority import install_authority_boundary
from spg.infrastructure.persistence.quality_schema import *

pytestmark=pytest.mark.postgresql

@pytest.fixture
def quality(postgres_database):
    command.upgrade(Config('alembic.ini'),'head')
    with postgres_database.engine.begin() as c:
        for t in reversed(quality_tables):c.execute(t.delete())
    return QualityService(postgres_database,Settings(runtime_revision='d'*40))


def finish(q,campaign,experiment=None,key=None,result='PASS'):
    r=q.request_run(CampaignRequest(campaign_id=campaign['id'],experiment_id=experiment,variant_key=key),'human:owner')
    run=q.claim_run();assert run['id']==r['id']
    aids=[]
    for c in q.run_members(run['id']):
        aid=q.begin_case(run,c['id']);aids.append(aid)
        q.finish_case(run,aid,(Evaluation(evaluator=Evaluator.DETERMINISTIC,outcome=result,
            evidence_refs=('owner:qualified',),evaluator_version='independent-test',stage=Stage.IRK,
            finding_code='KNOWN_ORACLE_FAILURE' if result=='FAIL' else None),),{'owner':'test-fixture'},.1)
    return q.finish_run(run),aids


def experiment(q):
    c=q.register_case(definitions()[0])
    return q.create_experiment(ExperimentRequest(case_id=c['case_id'],name='bounded strategy',rationale='compare timeout',
        variants=(Variant(key='a',label='A',model='NOT_APPLICABLE',provider='qualification-fixture',policy={'case_timeout_seconds':600}),
            Variant(key='b',label='B',model='NOT_APPLICABLE',provider='qualification-fixture',policy={'case_timeout_seconds':300})),changed_variables=('policy',)),'human:owner')


def test_same_case_identity_aliases_and_immutable_versions(quality):
    q=quality;a=q.register_case(definitions()[0]);b=q.register_case(definitions()[0].model_copy(update={'aliases':('old-id',)}))
    assert a['id']==b['id'] and q.list_cases()[0]['aliases']==['old-id']
    c=q.register_case(definitions()[0].model_copy(update={'title':'new label'}))
    assert c['case_id']==a['case_id'] and c['version']==2 and q.case_history(c['case_id'])['versions'][0]['id']==a['id']


def test_fake_scenario_cannot_borrow_known_oracle(quality):
    with pytest.raises(QualityError,match='CASE_DOES_NOT_MATCH'):
        quality.register_case(definitions()[0].model_copy(update={'motive':'different untested intent'}))


def test_campaign_repeatability_and_exact_version_binding(quality):
    c=import_core(quality);assert import_core(quality)['id']==c['id']
    one,_=finish(quality,c);two,_=finish(quality,c)
    assert one['id']!=two['id'] and one['state']==two['state']=='PASS'
    assert one['watt_revision']=='d'*40 and one['policy_fingerprint']==two['policy_fingerprint']


def test_holdout_hidden_from_optimization_and_public_history(quality):
    h=create_fresh_holdout(quality);c=quality.list_cases()[0]
    assert c['definition']['sealed'] and 'private_material' not in c['definition'] and 'motive' not in c['definition']
    with pytest.raises(QualityError,match='HOLDOUT_CANNOT'):quality.create_experiment(ExperimentRequest(case_id=h['case_id'],name='x',rationale='x',changed_variables=('policy',),variants=(Variant(key='a',label='a',model='m',provider='p',policy={'x':1}),Variant(key='b',label='b',model='m',provider='p',policy={'x':2}))),'human:owner')
    r,aids=finish(quality,h['campaign']);d=quality.run_detail(r['id']);assert d['cases'][0]['lineage']=={'sealed':True}
    with pytest.raises(QualityError,match='HOLDOUT_CANNOT'):quality.llm_evaluation(aids[0])


def test_preference_exact_evidence_and_owner_scoped_signals(quality):
    q=quality;e=experiment(q);camp=q.campaigns()[0]
    a,aa=finish(q,camp,e['id'],'a');b,bb=finish(q,camp,e['id'],'b',result='FAIL')
    p=q.preference(PreferenceRequest(experiment_id=e['id'],ranking=('b','a'),acceptability={'a':True,'b':False},case_run_ids={'a':aa[0],'b':bb[0]},confidence=.8,reason_tags=('semantic',),rationale='subjectively B clearer'),'human:owner')
    assert p['record']['candidate_provenance']['b']['objective_state']=='FAIL'
    assert q.run_detail(b['id'])['cases'][0]['state']=='FAIL'
    assert any(x['evaluator']=='HUMAN' for x in q.run_detail(b['id'])['cases'][0]['evaluations'])
    sig=q.attribute(AttributionRequest(source_kind='PREFERENCE',source_id=p['id'],owners=(Stage.IRK,Stage.MODEL_ROUTING),confidence=.5,rationale='hypothesis'),'human:owner')
    assert len(sig['learning_signal_ids'])==2 and not sig['changes_production']
    assert q.arena()['learning_signals'][0]['record']['interpretation']=='HYPOTHESIS'


def test_preference_rejects_wrong_variant_evidence(quality):
    q=quality;e=experiment(q);camp=q.campaigns()[0];_,a=finish(q,camp,e['id'],'a');_,b=finish(q,camp,e['id'],'b')
    with pytest.raises(QualityError,match='ARENA_EVIDENCE_MISMATCH'):q.preference(PreferenceRequest(experiment_id=e['id'],ranking=('a','b'),acceptability={'a':True,'b':True},case_run_ids={'a':b[0],'b':a[0]},confidence=1,reason_tags=('test',),rationale='wrong'),'human:owner')


def test_findings_cluster_exact_oracle_and_promote_same_case(quality):
    q=quality;v=q.register_case(definitions()[1]);c=q.register_campaign('incident','Incident',[v['id']])
    finish(q,c,result='FAIL');finish(q,c,result='FAIL')
    cluster=q.clusters()[0];assert cluster['occurrence_count']==2 and cluster['stage']=='IRK'
    p=q.promote_regression(__import__('uuid').UUID(cluster['findings'][0]),'human:owner')
    assert p['case_id']==v['case_id'] and q.clusters()[0]['regression_status']=='PERMANENT_CASE'


def test_lease_fence_recovery_skips_completed_case_and_single_slot(quality):
    q=quality;c=import_core(q);one=q.request_run(CampaignRequest(campaign_id=c['id']),'human:owner');q.request_run(CampaignRequest(campaign_id=c['id']),'human:owner')
    run=q.claim_run();assert q.claim_run() is None
    vs=q.run_members(run['id']);a=q.begin_case(run,vs[0]['id']);q.finish_case(run,a,(Evaluation(evaluator=Evaluator.DETERMINISTIC,outcome='PASS',evidence_refs=('x',),evaluator_version='1'),),{},1)
    q.begin_case(run,vs[1]['id'])
    with q.database.engine.begin() as db:db.execute(update(quality_campaign_runs).where(quality_campaign_runs.c.id==run['id']).values(lease_expires_at=now()-timedelta(seconds=1)))
    resumed=q.claim_run();assert resumed['id']==one['id'] and resumed['lease_token']!=run['lease_token']
    assert q.begin_case(resumed,vs[0]['id']) is None
    with pytest.raises(QualityError,match='FENCED'):q.begin_case(run,vs[2]['id'])
    a2=q.begin_case(resumed,vs[1]['id']);assert a2


def test_promotion_requires_regression_and_fresh_holdout(quality):
    q=quality;e=experiment(q);r,_=finish(q,q.campaigns()[0],e['id'],'b')
    with pytest.raises(QualityError,match='PROMOTION_REQUIRES_GOLDEN'):q.promote(PromotionRequest(experiment_id=e['id'],variant_key='b',campaign_run_ids=(r['id'],),rationale='not enough'),'human:owner')
    h=create_fresh_holdout(q);hr,_=finish(q,h['campaign'],e['id'],'b')
    p=q.promote(PromotionRequest(experiment_id=e['id'],variant_key='b',campaign_run_ids=(r['id'],hr['id']),rationale='explicit approved'),'human:owner')
    assert p['record']['decision']=='APPROVED_FOR_GOVERNED_CHANGE' and not p['record']['runtime_policy_changed']
    assert q.promote(PromotionRequest(experiment_id=e['id'],variant_key='b',campaign_run_ids=(r['id'],hr['id']),rationale='retry'),'human:owner')['id']==p['id']


def test_new_regression_cannot_be_omitted_from_old_campaign(quality):
    q=quality;a=q.register_case(definitions()[0]);c=q.register_campaign('old','old',[a['id']])
    new=definitions()[0].model_copy(update={'title':'new oracle label'});q.register_case(new)
    with pytest.raises(QualityError,match='REGRESSION_VERSION_STALE'):q.request_run(CampaignRequest(campaign_id=c['id']),'human:owner')


def test_admin_uses_existing_owner_auth_and_csrf(quality):
    s=Settings(auth_mode='required',operator_token='test-owner-secret-at-least-32-characters',runtime_revision='d'*40)
    app=FastAPI();install_authority_boundary(app,database=quality.database,settings=s);install_admin(app,quality.database,s)
    with TestClient(app) as client:
        assert client.get('/admin').status_code==200
        assert client.get('/api/admin/cases').status_code==401
        assert client.post('/auth/session',json={'token':s.operator_token.get_secret_value()}).status_code==200
        assert client.get('/api/admin/cases').status_code==200
        assert client.post('/api/admin/catalog/import',headers={'Origin':'http://evil.invalid'}).status_code==403
        assert client.post('/api/admin/catalog/import',headers={'Origin':'http://testserver'}).status_code==200


def test_operations_unknown_topology_and_bounded_retention(quality,tmp_path,monkeypatch):
    from spg.evaluation import operations
    s=Settings(admin_host_proc=tmp_path/'missing',admin_host_data=tmp_path/'missing',admin_node_id='i-current')
    o=OperationsService(quality.database,s)
    monkeypatch.setattr(o,'production',lambda:dict(workers=[],queue=[],queue_depth=4,active_executions=1))
    monkeypatch.setattr(o,'services',lambda:dict(services=[],state='UNAVAILABLE'))
    monkeypatch.setattr(o,'storage',lambda:dict(postgresql={'bytes':100,'method':'actual'}))
    o.observe();o.observe_resource('SERVICES');o.observe_resource('STORAGE');snap=o.snapshot();assert snap['state']=='CURRENT' and snap['service_observation_state']=='UNAVAILABLE'
    assert snap['node']['cpu_percent'] is None and snap['production']['queue_depth']==4
    assert snap['topology']['nodes'][0]['id']=='i-current' and snap['topology']['storage_placements'][0]['storage_id']=='postgresql'
    with quality.database.engine.begin() as c:c.execute(update(operations_metric_samples).values(created_at=now()-timedelta(days=4)))
    assert o.latest()['state']=='STALE';o.observe();assert len(o.history())==1


def test_finding_closure_requires_later_regression_and_recurrence_reopens(quality):
    from uuid import UUID
    q=quality;v=q.register_case(definitions()[0]);c=q.register_campaign('incident','Incident',[v['id']])
    finish(q,c,result='FAIL');fid=UUID(q.clusters()[0]['findings'][0]);q.promote_regression(fid,'human:owner')
    _,ids=finish(q,c)
    q.close_finding(fid,FindingClosureRequest(qualified_case_run_id=ids[0],rationale='qualified fix'), 'human:owner')
    assert q.clusters()[0]['closure_state']=='CLOSED'
    finish(q,c,result='FAIL');assert q.clusters()[0]['closure_state']=='OPEN'


def test_campaign_cohorts_are_pinned_before_later_relabeling(quality):
    q=quality;d=definitions()[0].model_copy(update={'cohorts':(Cohort.GOLDEN,)})
    v=q.register_case(d);c=q.register_campaign('before','Before',[v['id']]);finish(q,c,result='FAIL')
    from uuid import UUID
    q.promote_regression(UUID(q.clusters()[0]['findings'][0]),'human:owner')
    with q.database.engine.connect() as db:
        assert db.execute(select(quality_campaign_members.c.cohorts).where(quality_campaign_members.c.campaign_id==c['id'])).scalar_one()==['GOLDEN']
    updated=q.register_campaign('before','Before',[v['id']]);assert updated['version']==2


def test_old_watt_revision_is_not_executed_under_new_runtime(quality):
    q=quality;c=import_core(q);q.request_run(CampaignRequest(campaign_id=c['id']),'human:owner')
    q.settings=Settings(runtime_revision='e'*40)
    assert q.claim_run() is None and q.recent_runs()[0]['state']=='BLOCKED'


def test_sealed_holdout_finding_closes_without_entering_optimization(quality):
    from uuid import UUID
    q=quality;h=create_fresh_holdout(q);finish(q,h['campaign'],result='FAIL')
    fid=UUID(q.clusters()[0]['findings'][0]);_,aids=finish(q,h['campaign'])
    q.close_finding(fid,FindingClosureRequest(qualified_case_run_id=aids[0],rationale='bounded qualification infrastructure recovery'),'human:owner')
    assert q.clusters()[0]['closure_state']=='CLOSED'
    assert q.list_cases()[0]['cohorts']==['FRESH_HOLDOUT']
    with pytest.raises(QualityError,match='HOLDOUT_CANNOT'):q.promote_regression(fid,'human:owner')


def test_normal_admin_snapshot_never_executes_infrastructure_probes(quality, tmp_path, monkeypatch):
    from spg.evaluation.operations import OperationsService
    operations=OperationsService(quality.database,Settings(admin_node_id='i-exact'))
    def forbidden():raise AssertionError('read HTTP path performed a host census')
    monkeypatch.setattr(operations,'services',forbidden)
    monkeypatch.setattr(operations,'storage',forbidden)
    snapshot=operations.snapshot()
    assert snapshot['resource_freshness']['services']['state']=='NOT_SAMPLED'
    assert snapshot['resource_freshness']['storage']['state']=='NOT_SAMPLED'
    assert snapshot['storage']['postgresql']['bytes'] is None


def test_operations_sample_freshness_and_retention_are_separate_from_host(quality, monkeypatch):
    from spg.evaluation.operations import OperationsService
    o=OperationsService(quality.database,Settings(admin_node_id='i-exact',admin_storage_interval_seconds=60))
    monkeypatch.setattr(o,'services',lambda:dict(state='OBSERVED',services=[]))
    monkeypatch.setattr(o,'storage',lambda:dict(postgresql={'bytes':42},docker={'categories':[]}))
    o.observe_resource('SERVICES');o.observe_resource('STORAGE')
    assert o.latest()['state']=='NOT_SAMPLED'
    with quality.database.engine.begin() as c:
        c.execute(update(operations_metric_samples).values(created_at=now()-timedelta(seconds=181)))
    snapshot=o.snapshot()
    assert snapshot['resource_freshness']['storage']['state']=='STALE'
    assert snapshot['storage']['postgresql']['bytes']==42
    assert snapshot['node'] is None
