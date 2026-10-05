from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.domain.native_execution import (AttemptTerminalOutcome, ExecutionMode,
    KernelRunResult, CloudExecutionStatus, QueueProgressionState, WorkerStatus,
    NativeExecutionConflict)
from spg.infrastructure.persistence.native_execution_schema import executor_scheduler_state
from tests.integration.test_native_executor_runtime import (
    _admission, _offer, clean_native_runtime, git_repository,
)

pytestmark = pytest.mark.postgresql


def release(service, grant):
    service.finish_allocation(grant, KernelRunResult(
        runtime_mode=ExecutionMode.FINISHED, terminal_outcome=AttemptTerminalOutcome.STOPPED,
        final_checkpoint_id=None, step_count=0, inference_submissions=0,
        tool_effects=0, summary="Controlled capacity qualification complete"))


def enqueue(service, database, repository, work=None, priority=0):
    work = work or uuid4()
    admission = _admission(database, repository, work_id=work).model_copy(update={
        "fairness_group": f"work:{work}", "priority": priority})
    service.admit(admission)
    return admission.binding.attempt_id


def test_multislot_race_truthful_capacity_draining_and_bounded_heartbeat(
    postgres_database, git_repository,
):
    service = NativeExecutorRuntimeService(postgres_database)
    ids = [enqueue(service, postgres_database, git_repository) for _ in range(3)]
    offer = _offer().model_copy(update={"worker_id": "capacity:two", "max_concurrency": 2})
    service.register_worker(offer)
    service.heartbeat_worker(offer)
    barrier = Barrier(6)
    def claim(_):
        barrier.wait()
        return service.allocate(offer)
    with ThreadPoolExecutor(max_workers=6) as pool:
        grants = [item for item in pool.map(claim, range(6)) if item is not None]
    assert len(grants) == 2
    assert len({item.allocation.attempt_id for item in grants}) == 2
    counts = {event['payload']['active_execution_count_at_grant']
              for grant in grants for event in service.execution_evidence(grant.allocation.attempt_id)
              if event['event_type'] == 'ExecutionCapacityAllocated'}
    assert counts == {1, 2}
    worker = service.list_workers()[0]
    assert (worker.active_execution_count, worker.available_slots) == (2, 0)
    waiting_id = next(item for item in ids if item not in {g.allocation.attempt_id for g in grants})
    waiting = service.execution_request(waiting_id)
    assert waiting.status is CloudExecutionStatus.QUEUED
    assert waiting.scheduling.progression_state is QueueProgressionState.CAPACITY_WAIT
    assert waiting.scheduling.occupied_slots == 2
    service.reconcile_queue_ownership()
    before = len(service.execution_evidence(waiting_id))
    service.reconcile_queue_ownership()
    assert len(service.execution_evidence(waiting_id)) == before
    release(service, grants[0])
    worker = service.list_workers()[0]
    assert worker.status is WorkerStatus.BUSY
    assert (worker.active_execution_count, worker.available_slots) == (1, 1)
    assert service.execution_request(waiting_id).scheduling.available_slots == 1
    service.activate_allocation(grants[1])
    service.set_worker_draining(offer.worker_id, draining=True)
    for _ in range(10):
        service.heartbeat_worker(offer)
        assert service.allocate(offer) is None
    assert not service.list_workers()[0].safe_to_restart
    release(service, grants[1])
    drained = service.set_worker_draining(offer.worker_id, draining=True)
    assert drained.safe_to_restart and drained.available_slots == 0
    service.register_worker(offer)
    assert service.heartbeat_worker(offer).status is WorkerStatus.DRAINING
    assert service.execution_request(waiting_id).scheduling.draining_worker_count == 1
    events = service.worker_evidence(offer.worker_id)
    assert sum(item["event_type"] == "WorkerAllocationDeferred" and item["payload"]["reason"] == "DRAINING" for item in events) == 1
    service.set_worker_draining(offer.worker_id, draining=False)
    next_grant = service.allocate(offer)
    assert next_grant is not None and next_grant.allocation.attempt_id == waiting_id
    release(service, next_grant)


def test_fair_cursor_and_aging_survive_runtime_recreation(postgres_database, git_repository):
    clock = [datetime.now(timezone.utc) + timedelta(seconds=1)]
    service = NativeExecutorRuntimeService(postgres_database, now=lambda: clock[0])
    a, b = uuid4(), uuid4()
    ids = {a: [enqueue(service, postgres_database, git_repository, a, 100) for _ in range(3)],
           b: [enqueue(service, postgres_database, git_repository, b, -100)]}
    offer = _offer().model_copy(update={"worker_id": "capacity:fair"})
    service.heartbeat_worker(offer)
    clock[0] += timedelta(minutes=6)
    service.heartbeat_worker(offer)
    first = service.allocate(offer)
    assert first is not None
    first_work = first.queue_entry.work_id
    release(service, first)
    with postgres_database.unit_of_work() as uow:
        uow.session.execute(update(executor_scheduler_state).values(policy_version='fair-round-robin-v1'))
        uow.commit()
    restarted = NativeExecutorRuntimeService(postgres_database, now=lambda: clock[0])
    second = restarted.allocate(offer)
    assert second is not None and second.queue_entry.work_id != first_work
    assert "aging" in second.allocation.decision_reason
    with postgres_database.unit_of_work() as uow:
        state = uow.session.execute(select(executor_scheduler_state)).mappings().one()
        assert state["last_fairness_group"] == second.queue_entry.fairness_group
        assert state["policy_version"] == restarted.scheduler.policy_version
    release(restarted, second)
    assert sum(service.execution_request(item).status is CloudExecutionStatus.QUEUED
               for group in ids.values() for item in group) == 2


def test_draining_intent_survives_expiry_and_reregistration(postgres_database):
    clock = [datetime.now(timezone.utc)]
    service = NativeExecutorRuntimeService(postgres_database, now=lambda: clock[0])
    offer = _offer(lease_seconds=5)
    service.heartbeat_worker(offer)
    service.set_worker_draining(offer.worker_id, draining=True)
    clock[0] += timedelta(seconds=6)
    service.reconcile_worker_liveness()
    assert service.register_worker(offer).status is WorkerStatus.DRAINING
    assert service.heartbeat_worker(offer).status is WorkerStatus.DRAINING
    assert service.allocate(offer) is None
    assert service.list_workers()[0].safe_to_restart


@pytest.mark.parametrize("started", [False, True])
def test_worker_loss_preserves_execution_and_fences_prior_lease(
    postgres_database, git_repository, started,
):
    clock = [datetime.now(timezone.utc) + timedelta(seconds=1)]
    service = NativeExecutorRuntimeService(postgres_database, now=lambda: clock[0])
    execution = enqueue(service, postgres_database, git_repository)
    offer = _offer(lease_seconds=5).model_copy(update={"worker_id": "capacity:lost"})
    grant = service.allocate(offer)
    assert grant is not None
    if started:
        service.activate_allocation(grant)
    clock[0] += timedelta(seconds=6)
    assert service.reconcile_expired_leases() == (execution,)
    restarted = NativeExecutorRuntimeService(postgres_database, now=lambda: clock[0])
    assert restarted.execution_request(execution).status is CloudExecutionStatus.QUEUED
    next_grant = restarted.allocate(offer)
    assert next_grant is not None and next_grant.allocation.lease_epoch == grant.allocation.lease_epoch + 1
    with pytest.raises(NativeExecutionConflict, match="stale|fenced|expired"):
        service.heartbeat(grant)
    release(restarted, next_grant)
