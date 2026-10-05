from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from spg.application.executor_runtime import FairCapacityScheduler
from spg.domain.native_execution import (
    CloudExecutionStatus, ExecutionQueueEntryRecord, QueueCondition,
    ResourceEnvelope, WorkerOffer, WorkerStatus,
)


def _entry(*, priority: int, age_seconds: int = 0) -> ExecutionQueueEntryRecord:
    now = datetime.now(timezone.utc)
    return ExecutionQueueEntryRecord(
        id=uuid4(), command_id=uuid4(), request_digest="0" * 64,
        actor_identity="human:test", work_id=uuid4(), pwu_id=uuid4(),
        attempt_id=uuid4(), grant_revision=1, fairness_group="test",
        priority=priority, condition=QueueCondition.QUEUED,
        required_capabilities=("MODEL_EXECUTION",),
        required_provider_profile="scripted", required_resource_profile="standard",
        enqueued_at=now - timedelta(seconds=age_seconds), available_at=now,
    )


def _offer() -> WorkerOffer:
    return WorkerOffer(
        worker_id="cloud-worker-test", name="Test Worker", hostname="test-host",
        runtime_version="v1", max_concurrency=1,
        worker_profile="test", provider_profiles=("scripted",),
        resource_profiles=("standard",), capability_identities=("MODEL_EXECUTION",),
    )


def test_worker_identity_capacity_and_lifecycle_contracts() -> None:
    offer = _offer()
    assert offer.worker_id == "cloud-worker-test"
    assert offer.max_concurrency == 1
    assert set(WorkerStatus) == {
        WorkerStatus.REGISTERING, WorkerStatus.READY, WorkerStatus.BUSY,
        WorkerStatus.OFFLINE, WorkerStatus.DRAINING,
    }
    assert CloudExecutionStatus.RECOVERY_REQUIRED.value == "RECOVERY_REQUIRED"
    with pytest.raises(ValidationError):
        WorkerOffer.model_validate(_offer().model_dump() | {"max_concurrency": 0})


def test_scheduler_uses_priority_within_group_without_starving_old_work() -> None:
    scheduler = FairCapacityScheduler(aging_threshold=timedelta(minutes=5))
    low = _entry(priority=0, age_seconds=10)
    high = _entry(priority=5)
    decision = scheduler.choose([low, high], _offer(),
                                now=datetime.now(timezone.utc), last_fairness_group=None)
    assert decision.selected_queue_entry_id == high.id
    aged = _entry(priority=-5, age_seconds=600)
    decision = scheduler.choose([aged, high], _offer(),
                                now=datetime.now(timezone.utc), last_fairness_group=None)
    assert decision.selected_queue_entry_id == aged.id


def test_resource_envelope_has_bounded_runtime_log_and_artifact_limits() -> None:
    envelope = ResourceEnvelope(envelope_id=uuid4(), policy_version="cloud-worker-v1",
                                provider_profile="scripted")
    assert envelope.max_active_seconds > 0
    assert envelope.max_log_bytes == 65536
    assert envelope.max_artifact_bytes == 67108864
    with pytest.raises(ValidationError):
        ResourceEnvelope(envelope_id=uuid4(), policy_version="cloud-worker-v1",
                         provider_profile="scripted", max_artifact_bytes=0)
