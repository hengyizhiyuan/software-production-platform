"""Bounded in-process driving of existing governed Work transitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import logging
from threading import Condition, Event, RLock, Thread
from time import monotonic
from typing import Callable
from uuid import UUID

from spg.application.work import WorkApplicationService
from spg.domain.product import WorkProjection, WorkStatus


LOGGER = logging.getLogger(__name__)

# Eight deterministic steps reach Candidate Attention and two follow Human
# authorization. Two safety steps keep an activation finite without fragility.
DEFAULT_MAX_AUTOMATIC_TRANSITIONS = 12
_AUTOMATIC_STATUSES = frozenset({WorkStatus.READY, WorkStatus.RUNNING})
_STOP_STATUSES = frozenset(
    {
        WorkStatus.PRE_WORK,
        WorkStatus.DRAFT,
        WorkStatus.NEEDS_REFINEMENT,
        WorkStatus.AWAITING_APPROVAL,
        WorkStatus.NEEDS_ATTENTION,
        WorkStatus.BLOCKED,
        WorkStatus.COMPLETED,
    }
)


class OrchestrationStopReason(StrEnum):
    """Ephemeral driver outcome; never a second production state machine."""

    HUMAN_OR_TERMINAL_BOUNDARY = "HUMAN_OR_TERMINAL_BOUNDARY"
    NO_SAFE_PROGRESS = "NO_SAFE_PROGRESS"
    TRANSITION_LIMIT_REACHED = "TRANSITION_LIMIT_REACHED"
    APPLICATION_STOPPING = "APPLICATION_STOPPING"
    INFRASTRUCTURE_ERROR = "INFRASTRUCTURE_ERROR"
    PRODUCTION_CYCLE_TRUSTED = "PRODUCTION_CYCLE_TRUSTED"


@dataclass(frozen=True, slots=True)
class OrchestrationOutcome:
    work_id: UUID
    transitions_executed: int
    work_status: WorkStatus | None
    stop_reason: OrchestrationStopReason
    operator_message: str | None = None


@dataclass(frozen=True, slots=True)
class OrchestrationProgress:
    """Ephemeral operational telemetry, never production authority."""

    phase: str
    activity: str
    transitions_completed: int
    transitions_total: int | None
    started_at: datetime | None
    updated_at: datetime
    elapsed_seconds: float
    still_working: bool
    blocked_reason: str | None = None


class ProductionOrchestrator:
    """A process-local driver over authoritative Work and Runtime Reality."""

    def __init__(
        self,
        work_service: WorkApplicationService,
        *,
        max_automatic_transitions: int = DEFAULT_MAX_AUTOMATIC_TRANSITIONS,
        activation_guard: Callable[[UUID], bool] | None = None,
    ) -> None:
        if max_automatic_transitions < 1:
            raise ValueError("automatic transition bound must be positive")
        self.work_service = work_service
        self.max_automatic_transitions = max_automatic_transitions
        self.activation_guard = activation_guard or (lambda _work_id: True)
        self._condition = Condition(RLock())
        self._active_work_ids: set[UUID] = set()
        self._threads: dict[UUID, Thread] = {}
        self._last_outcomes: dict[UUID, OrchestrationOutcome] = {}
        self._progress: dict[UUID, OrchestrationProgress] = {}
        self._outcome_listeners: list[Callable[[OrchestrationOutcome], None]] = []
        self._stopping = Event()

    def configure_activation_guard(self, guard: Callable[[UUID], bool]) -> None:
        """Apply the same prerequisite gate to fresh and restart scheduling."""

        self.activation_guard = guard

    def schedule(self, work_id: UUID) -> bool:
        """Schedule one Work once; duplicate activations are rejected."""

        if not self.activation_guard(work_id):
            return False
        with self._condition:
            if self._stopping.is_set() or work_id in self._active_work_ids:
                return False
            self._last_outcomes.pop(work_id, None)
            now = datetime.now(UTC)
            self._progress[work_id] = OrchestrationProgress(
                "SCHEDULED", "Waiting for the automatic production driver", 0,
                None, now, now, 0.0, True,
            )
            self._active_work_ids.add(work_id)
            thread = Thread(
                target=self._run_scheduled,
                args=(work_id,),
                name=f"spg-orchestration-{work_id}",
                daemon=True,
            )
            self._threads[work_id] = thread
            try:
                thread.start()
            except BaseException:
                self._threads.pop(work_id, None)
                self._active_work_ids.remove(work_id)
                self._condition.notify_all()
                raise
        return True

    def resume_safely_eligible_works(self) -> tuple[UUID, ...]:
        """Reschedule ordinary progress without authorizing Provider retry."""

        scheduled: list[UUID] = []
        for work in self.work_service.list_works():
            if (
                not work.steering_enabled
                and work.status in _AUTOMATIC_STATUSES
                and self.activation_guard(work.work_id)
                and self.schedule(work.work_id)
            ):
                scheduled.append(work.work_id)
        return tuple(scheduled)

    def add_outcome_listener(
        self,
        listener: Callable[[OrchestrationOutcome], None],
    ) -> None:
        """Register an ephemeral wakeup listener; no progression truth is copied."""

        with self._condition:
            if listener not in self._outcome_listeners:
                self._outcome_listeners.append(listener)

    def orchestrate(self, work_id: UUID) -> OrchestrationOutcome:
        """Drive fresh Reality through one legal transition at a time."""

        transitions = 0
        initial = self.work_service.get_work(work_id)
        pwu_count = len((initial.production_plan_runtime or {}).get("pwus", ()))
        transition_limit = max(
            self.max_automatic_transitions,
            self.max_automatic_transitions * pwu_count,
        )
        while transitions < transition_limit:
            if self._stopping.is_set():
                return OrchestrationOutcome(
                    work_id,
                    transitions,
                    self.work_service.get_work(work_id).status,
                    OrchestrationStopReason.APPLICATION_STOPPING,
                )
            before = self.work_service.get_work(work_id)
            self._record_progress(
                work_id, before.current_production_step,
                before.what_happens_next, transitions,
            )
            if self._trusted_steering_cycle(before):
                return OrchestrationOutcome(
                    work_id,
                    transitions,
                    before.status,
                    OrchestrationStopReason.PRODUCTION_CYCLE_TRUSTED,
                )
            if before.status in _STOP_STATUSES:
                return OrchestrationOutcome(
                    work_id,
                    transitions,
                    before.status,
                    OrchestrationStopReason.HUMAN_OR_TERMINAL_BOUNDARY,
                )
            if before.status not in _AUTOMATIC_STATUSES:
                return self._no_safe_progress(work_id, transitions, before)
            before_fingerprint = self._fingerprint(work_id, before)

            # The existing service selects and executes at most one governed
            # action. This driver never precomputes a transition list.
            self.work_service.advance_work(work_id)
            transitions += 1
            after = self.work_service.get_work(work_id)
            self._record_progress(
                work_id, after.current_production_step,
                after.most_recent_meaningful_event, transitions,
            )
            if self._trusted_steering_cycle(after):
                return OrchestrationOutcome(
                    work_id,
                    transitions,
                    after.status,
                    OrchestrationStopReason.PRODUCTION_CYCLE_TRUSTED,
                )
            if after.status in _STOP_STATUSES:
                return OrchestrationOutcome(
                    work_id,
                    transitions,
                    after.status,
                    OrchestrationStopReason.HUMAN_OR_TERMINAL_BOUNDARY,
                )
            if self._fingerprint(work_id, after) == before_fingerprint:
                return self._no_safe_progress(work_id, transitions, after)

        current = self.work_service.get_work(work_id)
        message = (
            "Automatic transition limit reached; operator review is required "
            "before another bounded activation."
        )
        LOGGER.warning("%s Work=%s", message, work_id)
        return OrchestrationOutcome(
            work_id,
            transitions,
            current.status,
            OrchestrationStopReason.TRANSITION_LIMIT_REACHED,
            message,
        )

    def is_active(self, work_id: UUID) -> bool:
        with self._condition:
            return work_id in self._active_work_ids

    def last_outcome(self, work_id: UUID) -> OrchestrationOutcome | None:
        with self._condition:
            return self._last_outcomes.get(work_id)

    def progress(self, work_id: UUID) -> OrchestrationProgress | None:
        """Return the latest process-local observation without advancing Work."""

        with self._condition:
            current = self._progress.get(work_id)
            if current is None or not current.still_working or current.started_at is None:
                return current
            return OrchestrationProgress(
                current.phase, current.activity, current.transitions_completed,
                current.transitions_total, current.started_at, current.updated_at,
                max(current.elapsed_seconds, (datetime.now(UTC) - current.started_at).total_seconds()),
                True, current.blocked_reason,
            )

    def wait_until_idle(self, work_id: UUID, timeout: float) -> bool:
        """Wait only for bounded observation; never advance production."""

        deadline = monotonic() + timeout
        with self._condition:
            while work_id in self._active_work_ids:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return True

    def shutdown(self, timeout: float = 2.0) -> None:
        """Stop scheduling and allow a short, bounded graceful drain."""

        self._stopping.set()
        deadline = monotonic() + max(timeout, 0.0)
        with self._condition:
            threads = tuple(self._threads.values())
        for thread in threads:
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            thread.join(remaining)

    def _run_scheduled(self, work_id: UUID) -> None:
        try:
            outcome = self.orchestrate(work_id)
        except Exception as error:
            LOGGER.exception("Production orchestration stopped for Work=%s", work_id)
            outcome = OrchestrationOutcome(
                work_id,
                0,
                None,
                OrchestrationStopReason.INFRASTRUCTURE_ERROR,
                "Orchestration stopped on infrastructure error; operator "
                f"review is required ({type(error).__name__}).",
            )
        finally:
            with self._condition:
                prior = self._progress.get(work_id)
                now = datetime.now(UTC)
                blocked = outcome.operator_message if outcome.stop_reason in {
                    OrchestrationStopReason.NO_SAFE_PROGRESS,
                    OrchestrationStopReason.TRANSITION_LIMIT_REACHED,
                    OrchestrationStopReason.INFRASTRUCTURE_ERROR,
                } else None
                if blocked is None and outcome.work_status is WorkStatus.BLOCKED:
                    blocked = (
                        "Work reached a governed blocked state; inspect the most "
                        "recent production event and Runtime evidence."
                    )
                self._progress[work_id] = OrchestrationProgress(
                    outcome.work_status.value if outcome.work_status else "STOPPED",
                    outcome.operator_message or outcome.stop_reason.value,
                    outcome.transitions_executed, None,
                    None if prior is None else prior.started_at, now,
                    0.0 if prior is None or prior.started_at is None else (now - prior.started_at).total_seconds(),
                    False, blocked,
                )
                self._last_outcomes[work_id] = outcome
                self._threads.pop(work_id, None)
                self._active_work_ids.discard(work_id)
                listeners = tuple(self._outcome_listeners)
                self._condition.notify_all()
            for listener in listeners:
                try:
                    listener(outcome)
                except Exception:
                    LOGGER.exception(
                        "Production outcome listener failed Work=%s", work_id
                    )

    def _record_progress(
        self, work_id: UUID, phase: str, activity: str, transitions: int,
    ) -> None:
        now = datetime.now(UTC)
        with self._condition:
            prior = self._progress.get(work_id)
            started = now if prior is None or prior.started_at is None else prior.started_at
            self._progress[work_id] = OrchestrationProgress(
                phase, activity, transitions, None, started, now,
                (now - started).total_seconds(), True,
            )

    def _fingerprint(self, work_id: UUID, projection: WorkProjection) -> str:
        reality_fingerprint = getattr(
            self.work_service,
            "orchestration_reality_fingerprint",
            None,
        )
        if callable(reality_fingerprint):
            return reality_fingerprint(work_id)
        return projection.model_dump_json(exclude_none=False)

    @staticmethod
    def _trusted_steering_cycle(projection: WorkProjection) -> bool:
        return bool(
            projection.steering_enabled
            and projection.current_production_run_id is not None
            and projection.current_production_cycle_trusted
        )

    @staticmethod
    def _no_safe_progress(
        work_id: UUID,
        transitions: int,
        projection: WorkProjection,
    ) -> OrchestrationOutcome:
        message = (
            "No unambiguous governed transition changed Reality; operator review "
            "or an explicit Human decision is required."
        )
        return OrchestrationOutcome(
            work_id,
            transitions,
            projection.status,
            OrchestrationStopReason.NO_SAFE_PROGRESS,
            message,
        )
