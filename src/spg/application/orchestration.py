"""Bounded in-process driving of existing governed Work transitions."""

from __future__ import annotations

from dataclasses import dataclass
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


class ProductionOrchestrator:
    """A process-local driver over authoritative Work and Runtime Reality."""

    def __init__(
        self,
        work_service: WorkApplicationService,
        *,
        max_automatic_transitions: int = DEFAULT_MAX_AUTOMATIC_TRANSITIONS,
    ) -> None:
        if max_automatic_transitions < 1:
            raise ValueError("automatic transition bound must be positive")
        self.work_service = work_service
        self.max_automatic_transitions = max_automatic_transitions
        self._condition = Condition(RLock())
        self._active_work_ids: set[UUID] = set()
        self._threads: dict[UUID, Thread] = {}
        self._last_outcomes: dict[UUID, OrchestrationOutcome] = {}
        self._outcome_listeners: list[Callable[[OrchestrationOutcome], None]] = []
        self._stopping = Event()

    def schedule(self, work_id: UUID) -> bool:
        """Schedule one Work once; duplicate activations are rejected."""

        with self._condition:
            if self._stopping.is_set() or work_id in self._active_work_ids:
                return False
            self._last_outcomes.pop(work_id, None)
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
        while transitions < self.max_automatic_transitions:
            if self._stopping.is_set():
                return OrchestrationOutcome(
                    work_id,
                    transitions,
                    self.work_service.get_work(work_id).status,
                    OrchestrationStopReason.APPLICATION_STOPPING,
                )
            before = self.work_service.get_work(work_id)
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
