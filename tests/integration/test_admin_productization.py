"""Read-only historical Trace, owner auth, sealed answers and explicit Human tie."""
from uuid import UUID
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from spg.config import Settings
from spg.api.authority import install_authority_boundary
from spg.api.admin import install_admin
from spg.evaluation.production_trace import ProductionTraceService
from spg.evaluation.contracts import PreferenceRequest, QualityError, CampaignRequest, Evaluation, Evaluator
from spg.evaluation.catalog import definitions, create_fresh_holdout
from spg.infrastructure.persistence.quality_schema import quality_case_runs
from tests.integration.test_quality_admin import quality, finish, experiment
import pytest
pytestmark=pytest.mark.postgresql


def test_trace_pins_saved_owner_facts_not_current_case_definition(quality):
    q=quality;v=q.register_case(definitions()[0]);c=q.register_campaign('trace','History',[v['id']])
    r=q.request_run(CampaignRequest(campaign_id=c['id']),'human:owner');run=q.claim_run();aid=q.begin_case(run,v['id'])
    q.finish_case(run,aid,(Evaluation(evaluator=Evaluator.DETERMINISTIC,outcome='PASS',evidence_refs=('owner:saved',),evaluator_version='1'),),
        {'input':'精确的原始输入','owner_observations':[{'owners':{'interaction_messages':[{'id':'old-msg','actor':'HUMAN','content':'精确的原始输入','created_at':'2026-10-07T01:00:00Z'}],
        'production_work_units':[{'id':'old-pwu','objective':'当时的目标','completion_contract':{},'condition':'SATISFIED'}]}}]},1)
    q.finish_run(run)
    q.register_case(definitions()[0].model_copy(update={'title':'今日新标题'}))
    with q.database.engine.connect() as conn:before=dict(conn.execute(select(quality_case_runs).where(quality_case_runs.c.id==aid)).mappings().one())
    t=ProductionTraceService(q.database,q.settings,q).case_trace(aid)
    assert t['scene']!= '今日新标题' and t['first_human_input']=='精确的原始输入'
    assert t['units'][0]['objective']=='当时的目标' and t['basis']['case_version']==1
    with q.database.engine.connect() as conn:after=dict(conn.execute(select(quality_case_runs).where(quality_case_runs.c.id==aid)).mappings().one())
    assert before==after


def test_sealed_holdout_trace_does_not_expose_private_material(quality):
    h=create_fresh_holdout(quality);r,ids=finish(quality,h['campaign'])
    t=ProductionTraceService(quality.database,quality.settings,quality).case_trace(ids[0])
    assert t['basis']['mode']=='SEALED' and t['first_human_input'] is None and not t['semantic']
    assert 'private_material' not in str(t)


def test_trace_api_uses_existing_auth_and_rejects_unsupported_owner_lookup(quality):
    q=quality;v=q.register_case(definitions()[0]);c=q.register_campaign('api','API',[v['id']]);_,ids=finish(q,c)
    s=Settings(auth_mode='required',operator_token='private-test-owner-secret-at-least32',runtime_revision='d'*40)
    app=FastAPI();install_authority_boundary(app,database=q.database,settings=s);install_admin(app,q.database,s)
    with TestClient(app) as client:
        path=f'/api/admin/case-runs/{ids[0]}/trace'
        assert client.get(path).status_code==401
        client.post('/auth/session',json={'token':s.operator_token.get_secret_value()})
        assert client.get(path).status_code==200
        assert client.get('/api/admin/traces/arbitrary/'+str(ids[0])).json()['code']=='TRACE_IDENTIFIER_NOT_SUPPORTED'
        cockpit=client.get('/api/admin/overview').json()['cockpit']
        assert cockpit['observed']==1 and cockpit['current_revision']=='d'*40


def test_explicit_tie_has_no_manufactured_winner_and_does_not_override_failure(quality):
    q=quality;e=experiment(q);camp=q.campaigns()[0];_,a=finish(q,camp,e['id'],'a');_,b=finish(q,camp,e['id'],'b',result='FAIL')
    p=q.preference(PreferenceRequest(experiment_id=e['id'],ranking=('a','b'),strength='TIE',
        acceptability={'a':True,'b':False},case_run_ids={'a':a[0],'b':b[0]},confidence=.8,reason_tags=('intent',),rationale='Human explicitly finds no preferred outcome'),'human:owner')
    assert p['record']['winner'] is None and not p['record']['ranking_is_total_order']
    with q.database.engine.connect() as db:assert db.execute(select(quality_case_runs.c.state).where(quality_case_runs.c.id==b[0])).scalar_one()=='FAIL'
    assert not q.arena()['learning_signals'] and not q.arena()['promotion_decisions']


def test_strength_requires_matching_exact_pairwise_direction(quality):
    q=quality;e=experiment(q);camp=q.campaigns()[0];_,a=finish(q,camp,e['id'],'a');_,b=finish(q,camp,e['id'],'b')
    with pytest.raises(QualityError,match='PREFERENCE_STRENGTH_MISMATCH'):
        q.preference(PreferenceRequest(experiment_id=e['id'],ranking=('a','b'),strength='CLEAR_B',acceptability={'a':True,'b':True},
            case_run_ids={'a':a[0],'b':b[0]},confidence=.8,reason_tags=('intent',),rationale='mismatched direction'),'human:owner')
