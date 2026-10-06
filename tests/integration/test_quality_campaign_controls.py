"""Permanent incidents: safe campaign control, frozen reruns and systemic-stop fencing."""
from datetime import timedelta
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select, update
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_quality_admin import quality
from spg.api.admin import install_admin
from spg.evaluation.catalog import definitions, import_core
from spg.evaluation.contracts import CampaignRequest, RerunRequest, Evaluation, Evaluator, Stage, QualityError
from spg.evaluation.service import QualityService, now
from spg.infrastructure.persistence.quality_schema import quality_campaign_runs, quality_case_runs, quality_run_controls

pytestmark = pytest.mark.postgresql


def start(q):
    c = import_core(q)
    r = q.request_run(CampaignRequest(campaign_id=c['id']), 'human:owner')
    return q.claim_run(), q.run_members(r['id'])


def complete(q, r, vid, outcome='PASS', stage=None, oracle=None):
    aid=q.begin_case(r,vid)
    q.finish_case(r,aid,(Evaluation(evaluator=Evaluator.DETERMINISTIC,outcome=outcome,
        evidence_refs=('owner:control-regression',),evaluator_version='independent-oracle',
        stage=stage,finding_code='CANONICAL_INVARIANT_BROKEN' if outcome=='FAIL' else None,
        details={'oracle_id':oracle} if oracle else {}),),{},.1)
    return aid


def test_pause_inflight_finishes_safe_boundary_resume_same_run_no_replay(quality):
    q=quality;r,vs=start(q);first=complete(q,r,vs[0]['id']);active=q.begin_case(r,vs[1]['id'])
    assert q.control_run(r['id'],'PAUSE','human:owner')['state']=='PAUSE_REQUESTED'
    assert q.begin_case(r,vs[2]['id']) is None
    q.finish_case(r,active,(Evaluation(evaluator=Evaluator.DETERMINISTIC,outcome='PASS',evidence_refs=('x',),evaluator_version='1'),),{},1)
    assert not q.checkpoint(r)
    restored=QualityService(q.database,q.settings)
    before=restored.run_detail(r['id']);assert before['state']=='PAUSED' and before['progress']['completed']==2
    restored.control_run(r['id'],'RESUME','human:owner');resumed=restored.claim_run()
    assert resumed['id']==r['id'] and resumed['lease_token']!=r['lease_token']
    assert restored.begin_case(resumed,vs[0]['id']) is None
    assert restored.begin_case(resumed,vs[1]['id']) is None
    assert restored.begin_case(resumed,vs[2]['id'])
    with pytest.raises(QualityError,match='FENCED'):q.finish_case(r,first,(),{},0)


def test_stop_preserves_completed_and_inflight_remaining_not_run(quality):
    q=quality;r,vs=start(q);complete(q,r,vs[0]['id']);aid=q.begin_case(r,vs[1]['id'])
    assert q.control_run(r['id'],'STOP','human:owner')['state']=='STOPPING'
    q.finish_case(r,aid,(Evaluation(evaluator=Evaluator.DETERMINISTIC,outcome='FAIL',evidence_refs=('x',),evaluator_version='1'),),{},.2)
    assert not q.checkpoint(r)
    d=q.run_detail(r['id']);assert d['state']=='STOPPED'
    assert d['progress']['PASS']==1 and d['progress']['FAIL']==1 and d['progress']['NOT_RUN']==13
    assert len(d['cases'])==2 and d['failure_cluster_keys']
    with pytest.raises(QualityError,match='INVALID_CAMPAIGN'):q.control_run(r['id'],'RESUME','human:owner')


@pytest.mark.parametrize('action,state',[('PAUSE','PAUSED'),('STOP','STOPPED')])
def test_control_between_allocations_stops_old_runner_without_kill(quality,action,state):
    q=quality;r,vs=start(q);complete(q,r,vs[0]['id'])
    assert q.control_run(r['id'],action,'human:owner')['state']==state
    assert not q.checkpoint(r) and q.begin_case(r,vs[1]['id']) is None


def test_skip_only_queued_and_new_rerun_preserves_exact_versions_original_results(quality):
    q=quality;r,vs=start(q);complete(q,r,vs[0]['id'],'FAIL')
    with pytest.raises(QualityError,match='ONLY_QUEUED'):q.skip_case(r['id'],vs[0]['id'],'human:owner')
    q.skip_case(r['id'],vs[1]['id'],'human:owner');assert q.begin_case(r,vs[1]['id']) is None
    q.control_run(r['id'],'STOP','human:owner');before=q.run_detail(r['id'])['cases']
    for mode,ids,count in [('FAILED',(),1),('SELECTED',(vs[0]['id'],vs[1]['id']),2),('ALL',(),15)]:
        new=q.rerun(r['id'],RerunRequest(mode=mode,case_version_ids=ids),'human:owner')
        detail=q.run_detail(new['id']);assert new['id']!=r['id'] and new['parent_run_id']==r['id'] and detail['progress']['total']==count
        assert detail['members'][0]['source_case_run_id']==before[0]['id']
        q.control_run(new['id'],'STOP','human:owner')
    assert q.run_detail(r['id'])['cases']==before
    with pytest.raises(QualityError,match='EXACT_RERUN'):q.rerun(r['id'],RerunRequest(mode='SELECTED',case_version_ids=(uuid4(),)),'human:owner')


def test_system_stop_requires_four_distinct_exact_witnesses_not_generic_errors(quality):
    q=quality;r,vs=start(q)
    for i in range(5):complete(q,r,vs[i]['id'],'FAIL' if i<4 else 'PASS',Stage.PLANNING,'nonempty-pwu-v1')
    assert not q.checkpoint(r)
    d=q.run_detail(r['id']);assert d['state']=='PAUSED'
    trigger=next(x for x in d['controls'] if x['action']=='SYSTEM_STOP_THE_LINE')
    assert len(next(iter(trigger['record']['clusters'].values())))==4
    assert q.claim_run() is None
    q.control_run(r['id'],'STOP','human:owner');r,vs=start(q)
    for i in range(5):complete(q,r,vs[i]['id'],'FAIL')
    assert q.checkpoint(r) and q.run_detail(r['id'])['state']=='RUNNING'


@pytest.mark.parametrize('action,expected',[('PAUSE','PAUSED'),('STOP','STOPPED')])
def test_expired_inflight_requested_control_recovers_without_reallocation(quality,action,expected):
    q=quality;r,vs=start(q);complete(q,r,vs[0]['id']);q.begin_case(r,vs[1]['id']);q.control_run(r['id'],action,'human:owner')
    with q.database.engine.begin() as c:c.execute(update(quality_campaign_runs).where(quality_campaign_runs.c.id==r['id']).values(lease_expires_at=now()-timedelta(seconds=1)))
    assert q.claim_run() is None
    d=q.run_detail(r['id']);assert d['state']==expected and d['progress']['RUNNING']==0
    assert d['progress']['PASS']==1


def test_admin_http_controls_and_rerun_use_existing_owner_surface(quality):
    q=quality;c=import_core(q);app=FastAPI();install_admin(app,q.database,q.settings)
    with TestClient(app) as client:
        r=client.post('/api/admin/runs',json={'campaign_id':str(c['id'])}).json();rid=r['id']
        assert client.post(f'/api/admin/runs/{rid}/control',json={'action':'PAUSE'}).json()['state']=='PAUSED'
        assert client.post(f'/api/admin/runs/{rid}/control',json={'action':'RESUME'}).json()['id']==rid
        assert client.post(f'/api/admin/runs/{rid}/control',json={'action':'STOP'}).json()['state']=='STOPPED'
        new=client.post(f'/api/admin/runs/{rid}/rerun',json={'mode':'SELECTED','case_version_ids':[str(c['id'])]})
        assert new.status_code==409
        vid=str(q.run_members(UUID(rid))[0]['id']) if q.run_members(UUID(rid)) else str(q.run_detail(UUID(rid))['members'][0]['case_version_id'])
        new=client.post(f'/api/admin/runs/{rid}/rerun',json={'mode':'SELECTED','case_version_ids':[vid]})
        assert new.status_code==200 and new.json()['parent_run_id']==rid
        assert client.get('/api/admin/runs/'+new.json()['id']).json()['progress']['total']==1


def test_fixed_pilot_never_auto_expands_or_regenerates_holdout(quality):
    from spg.evaluation.pilot import register_pilot, register_control_regression
    q=quality;import_core(q);register_control_regression(q)
    p=register_pilot(q);assert len(next(c for c in q.campaigns() if c['id']==p['id'])['case_version_ids'])==10
    versions=next(c for c in q.campaigns() if c['id']==p['id'])['case_version_ids']
    assert register_pilot(q)['id']==p['id']
    r=q.request_run(CampaignRequest(campaign_id=p['id']),'human:owner')
    detail=q.run_detail(r['id']);assert detail['progress']['total']==10
    assert len(detail['fresh_holdout'])==1
    sealed=next(m for m in detail['members'] if 'FRESH_HOLDOUT' in m['cohorts'])
    assert sealed['definition']=={'sealed':True}
    assert set(q.run_members(r['id'])[i]['id'] for i in range(10))==set(versions)
