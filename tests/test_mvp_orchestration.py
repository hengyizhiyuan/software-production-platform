"""Focused deterministic contracts for MVP Production Orchestration Lite."""

from pathlib import Path
from threading import Event
from uuid import UUID, uuid4

import pytest

from spg.application.orchestration import (
    OrchestrationStopReason,
    ProductionOrchestrator,
)
from spg.domain.product import WorkProjection, WorkStatus


def _projection(
    work_id: UUID,
    status: WorkStatus,
    version: int = 0,
) -> WorkProjection:
    return WorkProjection(
        work_id=work_id,
        goal_id=None,
        raw_user_requirement="governed Work",
        title="Governed Work",
        desired_outcome="produce one artifact",
        constraints=(),
        tags=(),
        engineering_scope=None,
        status=status,
        current_production_step=f"STEP_{version}",
        most_recent_meaningful_event=f"EVENT_{version}",
        what_happens_next="follow governed Reality",
        human_attention_required=status
        in {
            WorkStatus.AWAITING_APPROVAL,
            WorkStatus.NEEDS_ATTENTION,
            WorkStatus.BLOCKED,
        },
        result_summary=None,
    )


class _ScriptedWorkService:
    def __init__(self, work_id: UUID, statuses: list[WorkStatus]) -> None:
        self.work_id = work_id
        self.statuses = statuses
        self.index = 0
        self.get_calls = 0
        self.advance_calls = 0

    def get_work(self, work_id: UUID) -> WorkProjection:
        assert work_id == self.work_id
        self.get_calls += 1
        return _projection(work_id, self.statuses[self.index], self.index)

    def advance_work(self, work_id: UUID) -> WorkProjection:
        assert work_id == self.work_id
        self.advance_calls += 1
        if self.index < len(self.statuses) - 1:
            self.index += 1
        return self.get_work(work_id)

    def list_works(self) -> tuple[WorkProjection, ...]:
        return (self.get_work(self.work_id),)


def test_orch_03_04_09_10_fresh_reality_one_transition_and_human_stop() -> None:
    work_id = uuid4()
    service = _ScriptedWorkService(
        work_id,
        [
            WorkStatus.READY,
            WorkStatus.RUNNING,
            WorkStatus.RUNNING,
            WorkStatus.NEEDS_ATTENTION,
        ],
    )
    outcome = ProductionOrchestrator(service).orchestrate(work_id)

    assert service.advance_calls == 3
    assert service.get_calls >= service.advance_calls * 2
    assert outcome.transitions_executed == 3
    assert outcome.work_status is WorkStatus.NEEDS_ATTENTION
    assert outcome.stop_reason is OrchestrationStopReason.HUMAN_OR_TERMINAL_BOUNDARY


@pytest.mark.parametrize(
    "status",
    [
        WorkStatus.DRAFT,
        WorkStatus.NEEDS_REFINEMENT,
        WorkStatus.AWAITING_APPROVAL,
        WorkStatus.NEEDS_ATTENTION,
        WorkStatus.BLOCKED,
        WorkStatus.COMPLETED,
    ],
)
def test_orch_16_17_human_blocked_and_terminal_reality_never_advance(
    status: WorkStatus,
) -> None:
    work_id = uuid4()
    service = _ScriptedWorkService(work_id, [status])

    outcome = ProductionOrchestrator(service).orchestrate(work_id)

    assert service.advance_calls == 0
    assert outcome.work_status is status
    assert outcome.stop_reason is OrchestrationStopReason.HUMAN_OR_TERMINAL_BOUNDARY


def test_orch_19_22_23_automatic_loop_is_bounded_and_ephemeral() -> None:
    work_id = uuid4()
    service = _ScriptedWorkService(
        work_id,
        [WorkStatus.READY, WorkStatus.RUNNING, WorkStatus.RUNNING],
    )
    orchestrator = ProductionOrchestrator(service, max_automatic_transitions=2)

    outcome = orchestrator.orchestrate(work_id)

    assert service.advance_calls == 2
    assert outcome.stop_reason is OrchestrationStopReason.TRANSITION_LIMIT_REACHED
    assert "operator review" in (outcome.operator_message or "")
    assert not hasattr(orchestrator, "production_state")


def test_orch_18_same_work_cannot_run_twice_concurrently() -> None:
    work_id = uuid4()
    entered = Event()
    release = Event()

    class BlockingService(_ScriptedWorkService):
        def advance_work(self, selected_work_id: UUID) -> WorkProjection:
            entered.set()
            assert release.wait(2)
            self.index = 1
            return self.get_work(selected_work_id)

    service = BlockingService(
        work_id,
        [WorkStatus.READY, WorkStatus.NEEDS_ATTENTION],
    )
    orchestrator = ProductionOrchestrator(service)

    assert orchestrator.schedule(work_id) is True
    assert entered.wait(2)
    assert orchestrator.schedule(work_id) is False
    release.set()
    assert orchestrator.wait_until_idle(work_id, 2)
    assert orchestrator.last_outcome(work_id) is not None


def test_orch_restart_reschedules_only_ordinary_ready_or_running_work() -> None:
    work_ids = {status: uuid4() for status in WorkStatus}

    class MultiWorkService:
        def list_works(self) -> tuple[WorkProjection, ...]:
            return tuple(
                _projection(work_id, status)
                for status, work_id in work_ids.items()
            )

    class RecordingOrchestrator(ProductionOrchestrator):
        def __init__(self) -> None:
            super().__init__(MultiWorkService())
            self.scheduled: list[UUID] = []

        def schedule(self, work_id: UUID) -> bool:
            self.scheduled.append(work_id)
            return True

    orchestrator = RecordingOrchestrator()
    scheduled = orchestrator.resume_safely_eligible_works()

    assert scheduled == (
        work_ids[WorkStatus.READY],
        work_ids[WorkStatus.RUNNING],
    )
    assert orchestrator.scheduled == list(scheduled)


def test_orch_06_07_22_24_driver_has_no_provider_or_recovery_bypass() -> None:
    source = (
        Path(__file__).parents[1]
        / "src"
        / "spg"
        / "application"
        / "orchestration.py"
    ).read_text(encoding="utf-8")
    assert "advance_work(work_id)" in source
    for forbidden in (
        "Codex",
        "dispatch_and_observe",
        "resume_provider",
        "retry_provider",
        "RecoveryService",
        "redis",
        "celery",
    ):
        assert forbidden not in source
