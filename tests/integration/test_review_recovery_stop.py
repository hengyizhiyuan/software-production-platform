"""Real PostgreSQL stop/admission receipts; isolated test data only."""
from uuid import uuid4
import pytest
from spg.application.steering_driver import PlanSteeringDriver
from spg.application.steering_production import FulfillmentProjectionNotReady
from spg.application.orchestration import ProductionOrchestrator
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.application import governed_obligations as a
from tests.integration.test_mvp_semantic_step_execution import clean_schema, product, _admitted_plan
from tests.test_c3_reviewer_contract_feedback import run_case

pytestmark=pytest.mark.postgresql


def test_long_formation_reason_reaches_durable_human_attention(product,postgres_database,monkeypatch):
    works,_=product
    admitted,_=_admitted_plan(works)
    driver=PlanSteeringDriver(postgres_database,works,ProductionOrchestrator(works))
    reason='OBLIGATION_SOURCE_CONSUMPTION_CONSUMER_MISMATCH'
    def stop(_): raise FulfillmentProjectionNotReady(uuid4(),{'terminal_reason':reason})
    monkeypatch.setattr(driver,'iterate',stop)
    monkeypatch.setattr(driver,'_schedule_formation_round',lambda *_:False)
    result=driver.activate(admitted.work_id)
    assert result.stop_reason.value=='BLOCKED'
    with postgres_database.unit_of_work() as uow:
        last=NativeExecutionStore(uow.session).work_convergence_history(admitted.work_id)[-1]
        assert last.condition=='NON_CONVERGING'
        assert len(last.failure_signature)==64
        assert last.evidence['failure_details']['terminal_reason']==reason
    assert works.get_work(admitted.work_id).human_attention_required
    fresh=PlanSteeringDriver(postgres_database,works,ProductionOrchestrator(works))
    assert fresh.activate(admitted.work_id).stop_reason.value=='BLOCKED'
    assert fresh.project(admitted.work_id).human_attention_required


def test_unexpected_scheduler_failure_is_persisted(product,postgres_database,monkeypatch):
    works,_=product
    admitted,_=_admitted_plan(works)
    driver=PlanSteeringDriver(postgres_database,works,ProductionOrchestrator(works))
    def broken(_): raise RuntimeError('isolated failure')
    monkeypatch.setattr(driver,'activate',broken)
    driver._run_scheduled(admitted.work_id)
    with postgres_database.unit_of_work() as uow:
        last=NativeExecutionStore(uow.session).work_convergence_history(admitted.work_id)[-1]
        assert last.boundary=='STEERING_ERROR' and last.condition=='NON_CONVERGING'
        assert last.evidence['failure_details']['error_type']=='RuntimeError'
    assert works.get_work(admitted.work_id).human_attention_required


def test_same_candidate_review_terminal_survives_jsonb_storage(postgres_database):
    rev,ir,inv,provider,calls,execute=run_case(same_candidate=True,empty_operands=True)
    result=execute()
    assert all(b.state!='UNRESOLVED' for b in result)
    original=result[0].formation_receipt['candidate_attempts']
    with postgres_database.unit_of_work() as uow:
        store=RuntimeStore(uow.session)
        from datetime import datetime,UTC
        for row in original:
            store.insert_governance({'id':uuid4(),'decision_type':'WORK_FULFILLMENT_OBSERVATION',
                'authority_identity':'work-governance:derived-candidate-observation',
                'subject_type':'WORK_FULFILLMENT_BASIS','subject_identity':inv['inventory_fingerprint'],
                'scope':row,'rationale':'isolated replay qualification','created_at':datetime.now(UTC)})
        uow.commit()
    provider._fulfillment_receipts=[]
    replay=a.form_fulfillment_projection(rev,ir,provider=provider,database=postgres_database,
        source_revision=inv['source_revision'],exact_target_paths=inv['exact_target_paths'])
    assert all(b.state!='UNRESOLVED' for b in replay),replay[0].formation_receipt['terminal_reason']
    assert len(calls)==3
    a.validate_fulfillment_projection(replay,rev,ir,source_revision=inv['source_revision'],exact_target_paths=inv['exact_target_paths'])
