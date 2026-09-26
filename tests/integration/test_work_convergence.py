"""Work convergence survives transactions, fresh stores and attempt-ID churn."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore


def test_no_progress_cannot_be_reset_by_new_candidate_or_boundary(postgres_database):
    work_id = uuid4()
    intent = "a" * 64
    observations = []
    for index in range(3):
        with postgres_database.unit_of_work() as uow:
            observations.append(NativeExecutionStore(uow.session).observe_work_convergence(
                work_id=work_id, intent_identity=intent, boundary=f"boundary-{index}",
                reality_identity=str(index).zfill(64), candidate_identity=str(uuid4()),
                failure_signature=str(index).zfill(64), failed=True,
                missing_acceptance=("RUNTIME_VERIFIED", "PREVIEW_READY")))
            uow.commit()
    assert [row.no_progress_count for row in observations] == [1, 2, 3]
    assert observations[-1].condition == "NON_CONVERGING"
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        restarted = store.observe_work_convergence(work_id=work_id,
            intent_identity=intent, boundary="RESTART", reality_identity="b" * 64,
            missing_acceptance=("PREVIEW_READY", "RUNTIME_VERIFIED"))
        assert restarted.condition == "NON_CONVERGING"
        assert restarted.predecessor_id == observations[-1].id
        assert len(store.work_convergence_history(work_id)) == 4
        progressed = store.observe_work_convergence(work_id=work_id,
            intent_identity=intent, boundary="RUNTIME", reality_identity="c" * 64,
            missing_acceptance=("PREVIEW_READY",))
        assert progressed.no_progress_count == 0
        assert progressed.attempts == 5
        assert progressed.condition == "NOT_YET_CONVERGED"
        review = store.observe_work_convergence(work_id=work_id,
            intent_identity=intent, boundary="PREVIEW", reality_identity="d" * 64,
            missing_acceptance=(), evidence={"human_acceptance": "PENDING"})
        assert review.condition == "CONVERGED_FOR_REVIEW"
        assert review.evidence["human_acceptance"] == "PENDING"
        uow.commit()


def test_lifetime_budget_and_human_authority_are_independent(postgres_database):
    work_id = uuid4()
    start = datetime.now(UTC)
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        store.observe_work_convergence(work_id=work_id, intent_identity="e" * 64,
            boundary="EXECUTOR", reality_identity="f" * 64,
            missing_acceptance=("BUILD", "PREVIEW"), now=start)
        timed_out = store.observe_work_convergence(work_id=work_id, intent_identity="e" * 64,
            boundary="PREVIEW", reality_identity="f" * 64,
            missing_acceptance=("PREVIEW",), now=start + timedelta(hours=3))
        assert timed_out.condition == "NON_CONVERGING"
        assert timed_out.elapsed_seconds == 10800
        new_intent = store.observe_work_convergence(work_id=work_id, intent_identity="1" * 64,
            boundary="SECRETS", reality_identity="f" * 64,
            missing_acceptance=("EXTERNAL_SECRET",), authority_required=True,
            human_intervention=True)
        assert new_intent.condition == "ESCALATED"
        assert new_intent.attempts == 1
        assert new_intent.human_intervention_count == 1
        uow.commit()
