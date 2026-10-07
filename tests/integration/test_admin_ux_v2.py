"""Exercise UX projections against the real schema in an isolated PostgreSQL."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from spg.api.admin import install_admin
from spg.evaluation.admin_projection import run_summaries, assurance_summary
from spg.evaluation.admin_dashboard import dashboard
from spg.evaluation.catalog import definitions
from tests.integration.test_quality_admin import quality, finish
import pytest
pytestmark = pytest.mark.postgresql


def test_dashboard_is_read_only_and_never_fakes_user_telemetry(quality):
    q = quality
    with q.database.engine.connect() as c:
        before = c.scalar(text('SELECT count(*) FROM quality_campaign_runs'))
    for period in ['TODAY','7D','30D']:
        d = dashboard(q.database,q.settings,period)
        assert all(m['value'] is None for m in d['users'])
        assert next(m for m in d['production'] if '当前完成' in m['label'])['value'] is None
        assert d['from'] <= d['to'] and d['timezone']=='Asia/Shanghai'
    with q.database.engine.connect() as c:
        assert c.scalar(text('SELECT count(*) FROM quality_campaign_runs')) == before


def test_run_summary_compares_nearest_exact_observation_and_no_source_edits(quality):
    q=quality;v=q.register_case(definitions()[0]);campaign=q.register_campaign('summary','Run 的目的',[v['id']])
    first,_=finish(q,campaign,result='FAIL');second,_=finish(q,campaign);current,_=finish(q,campaign,result='FAIL')
    with q.database.unit_of_work() as u:
        ledger=[dict(r) for r in u.session.execute(text("""SELECT a.id,a.state,a.created_at,a.case_version_id,a.campaign_run_id,v.case_id,
            v.definition->>'title' AS title,r.policy_fingerprint,r.experiment_id FROM quality_case_runs a
            JOIN quality_case_versions v ON v.id=a.case_version_id JOIN quality_campaign_runs r ON r.id=a.campaign_run_id
            ORDER BY a.created_at DESC""")).mappings()]
    summaries=run_summaries(q.database,q.recent_runs(),q.campaigns(),ledger)
    row=next(s for s in summaries if s['id']==current['id'])['human_summary']
    assert row['coverage_count']==1 and row['coverage']==[definitions()[0].title]
    assert row['comparison_available'] and row['changes'][0]['kind']=='REGRESSION'
    assert row['changes'][0]['before']=='PASS'
    assert next(s for s in summaries if s['id']==first['id'])['human_summary']['comparison_available'] is False
    unchanged=run_summaries(q.database,q.recent_runs(),q.campaigns(),ledger+ledger)
    assert row==next(s for s in unchanged if s['id']==current['id'])['human_summary']


def test_new_dashboard_routes_retain_validation_and_canonical_work_projection(quality):
    app=FastAPI();install_admin(app,quality.database,quality.settings)
    class WorkOwner:
        def get_works(self, ids):
            return ()
    app.state.work_service=WorkOwner()
    with TestClient(app) as client:
        assert client.get('/api/admin/dashboard?period=7D').status_code==200
        assert client.get('/api/admin/dashboard?period=ALL').json()['code']=='DASHBOARD_PERIOD_NOT_SUPPORTED'
        response=client.get('/api/admin/dashboard/work-outcomes').json()
        assert response['completed']==0 and '不是本期完成事件' in response['scope']


def test_guardian_failure_and_unobserved_result_are_distinct(quality):
    records=[dict(candidate_id='a',candidate_fingerprint='fp',gate='FAIL_REPAIRABLE',assessed_at='2026-10-07'),
        dict(candidate_id='b',candidate_fingerprint='fp2',gate='UNAVAILABLE',assessed_at='2026-10-07')]
    result=assurance_summary(quality.database,{'results':records})
    assert result['blocked_candidates']==1 and result['unknown_candidates']==1
    assert result['false_positive'] is None and not result['pending_review']


def test_comparison_pairs_ignore_newer_promotion_holdout_and_preserve_exact_version(quality):
    from spg.evaluation.admin_projection import experiment_comparisons
    from spg.evaluation.catalog import create_fresh_holdout
    from tests.integration.test_quality_admin import experiment
    q=quality;e=experiment(q);campaign=q.campaigns()[0]
    a,aa=finish(q,campaign,e['id'],'a');b,bb=finish(q,campaign,e['id'],'b')
    h=create_fresh_holdout(q);finish(q,h['campaign'],e['id'],'b')
    pairs=experiment_comparisons(q.database,[e])[str(e['id'])]
    assert pairs['a']['case_run_id']==str(aa[0]) and pairs['b']['case_run_id']==str(bb[0])
    assert pairs['b']['run_id']==str(b['id']) and pairs['b']['case_version_id']==str(e['case_version_id'])
    with q.database.engine.connect() as c:
        assert c.scalar(text('SELECT count(*) FROM quality_preferences'))==0
