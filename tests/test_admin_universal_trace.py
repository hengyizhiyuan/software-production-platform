from threading import Condition, RLock
from types import SimpleNamespace
from uuid import uuid4
from spg.application.steering_driver import PlanSteeringDriver
from spg.domain.steering import SteeringDriverStopReason
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore
from spg.evaluation.work_registry import work_summary


def test_read_only_preview_reader_does_not_create_runtime_state(tmp_path):
    root=tmp_path/'missing-owner-root'
    store=JsonProductionEnvironmentStore(root,create_root=False)
    assert store.current_candidate_preview(uuid4()) is None and not root.exists()


def test_batch_steering_observations_do_not_hydrate_or_mutate_work():
    driver=object.__new__(PlanSteeringDriver);driver._condition=Condition(RLock())
    active,blocked=uuid4(),uuid4();driver._active_work_ids={active}
    driver._last_outcomes={blocked:SimpleNamespace(stop_reason=SteeringDriverStopReason.BLOCKED)}
    r=driver.read_progression_observations()
    assert r[str(active)]=={'active':True,'stop_reason':None}
    assert r[str(blocked)]=={'active':False,'stop_reason':'BLOCKED'}
    r[str(active)]['active']=False
    assert driver._active_work_ids=={active}


def test_unknown_quality_is_not_zero_or_pass_and_deployment_failure_remains_visible():
    row=dict(work_id=uuid4(),raw_user_requirement='需求',state='PREPARING',complete=False,stage=None,deployment_state='FAILED',open_finding_count=None)
    r=work_summary(row)
    assert r['state_label']=='准备生产' and r['open_finding_count'] is None
    assert '部署 FAILED' in r['issue_hint'] and 'PASS' not in r['result_label']


def test_failed_production_does_not_become_success_from_completed_queue():
    from spg.evaluation.production_trace import project_trace
    tables={'executor_queue':[{'id':'q','condition':'COMPLETED'}],
        'provider_execution_reports':[{'id':'r','outcome':'FAILURE'}],
        'execution_events':[{'id':'e','event_type':'ExecutionFailed','pwu_id':'u'}]}
    t=project_trace(tables,scene='失败 Work',purpose='失败证据',detail=False)
    assert not t['candidate']
    report=next(e for e in t['timeline'] if e['source_ref']=='provider_execution_reports:r')
    assert report['state']=='FAIL' and report['detail']['outcome']=='FAILURE'
    failure=next(e for e in t['timeline'] if e['source_ref']=='execution_events:e')
    assert failure['title']=='执行失败' and failure['state']=='FAIL'
