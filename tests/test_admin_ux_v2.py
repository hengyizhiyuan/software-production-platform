"""User-facing read projections must retain exact evidence and unknown values."""
from datetime import datetime, timezone
from types import SimpleNamespace
import json
import pytest
from spg.evaluation.admin_dashboard import period_start, performance_qualification
from spg.evaluation.admin_projection import issue_projection
from spg.evaluation.contracts import QualityError
from spg.evaluation.production_trace import project_trace


def test_dashboard_calendar_periods_use_shanghai_and_reject_arbitrary_ranges():
    now = datetime(2026, 10, 7, 3, 0, tzinfo=timezone.utc)
    assert period_start('TODAY', now).isoformat() == '2026-10-06T16:00:00+00:00'
    assert period_start('7D', now).isoformat() == '2026-09-30T16:00:00+00:00'
    assert period_start('30D', now).isoformat() == '2026-09-07T16:00:00+00:00'
    with pytest.raises(QualityError, match='DASHBOARD_PERIOD_NOT_SUPPORTED'):
        period_start('ALL', now)


def test_missing_or_wrong_period_performance_is_unknown_not_zero(tmp_path):
    settings = SimpleNamespace(owner_runtime_store_root=tmp_path)
    now = datetime.now(timezone.utc)
    assert performance_qualification(settings, now, now) is None
    folder = tmp_path/'qualifications/watt-core-performance-p0-v1'
    folder.mkdir(parents=True)
    (folder/'qualification-report-summary.json').write_text(json.dumps({'observed_at':'2020-01-01T00:00:00+00:00'}))
    assert performance_qualification(settings, now, now) is None


def test_finding_closure_affordance_requires_exact_later_regression_evidence():
    occurrence = dict(id='f', case_id='c', case_run_id='old', state='OPEN', created_at='2026-10-06', regression_case_id='c')
    cluster = dict(affected_cases=['c'], last_seen='2026-10-06', occurrences=[occurrence], findings_case_runs=['old'])
    case = dict(id='c', cohorts=['REGRESSION'], definition={'title':'真实场景'})
    result = dict(id='new', case_id='c', state='PASS', created_at='2026-10-07')
    assert issue_projection(cluster, [result], [case])['eligible_closures'][0]['finding_id'] == 'f'
    for row in [{**result,'case_id':'other'}, {**result,'state':'FAIL'}, {**result,'created_at':'2026-10-05'}]:
        assert not issue_projection(cluster, [row], [case])['eligible_closures']
    assert not issue_projection(cluster, [result], [{**case,'cohorts':['GOLDEN']}])['eligible_closures']
    occurrence['state'] = 'CLOSED'
    assert not issue_projection(cluster, [result], [case])['eligible_closures']


def test_trace_header_elapsed_is_case_wall_time_not_sum_of_parallel_units():
    p = project_trace({}, scene='场景', purpose='验证', case={'state':'PASS','elapsed_seconds':3.5}, detail=False)
    assert p['elapsed_seconds'] == 3.5 and p['advanced'] == {}
    assert project_trace({}, scene='未知', purpose='验证')['elapsed_seconds'] is None
