"""Bounded process-local driver over authoritative Steering and SPG Reality."""

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
import json
import logging
from datetime import UTC, datetime
from threading import Condition, Event, RLock, Thread, Timer
from time import monotonic
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.application.orchestration import (
    OrchestrationOutcome,
    OrchestrationStopReason,
    ProductionOrchestrator,
)
from spg.application.assets import RepositoryAssetService
from spg.application.repository_branch_authority import governed_branch_creation_target
from spg.application.guided_design import GuidedDesignApplicationService
from spg.application.steering import SteeringApplicationService
from spg.application.semantic_steps import SemanticStepApplicationService
from spg.application.steering_decision import (
    DeterministicPlanSteeringCapability,
    PlanFrameAssembler,
    SteeringDecisionApplicationService,
)
from spg.application.steering_production import SteeringProductionService
from spg.application.work import WorkApplicationService
from spg.domain.product import (
    ProductInvariantViolation,
    RuntimeFactSummary,
    WorkStatus,
)
from spg.domain.guided_design import DesignReadinessState
from spg.domain.change import ProductionTargetKind
from spg.domain.planning import OnePwuFitClassification
from spg.domain.steering import (
    NextStepCandidate,
    PlanFrame,
    PlanFrameBlockerKind,
    PlanSteeringCapability,
    RealityReferenceKind,
    ReviseSteeringPlanRequest,
    SemanticStepCapability,
    SemanticStepResultRecord,
    SteeringActionType,
    SteeringActivationResult,
    SteeringAttentionReason,
    SteeringAuthorityAssessment,
    SteeringAutomaticProgressionState,
    SteeringDecisionRecord,
    SteeringDriverStopReason,
    SteeringHistoryEventType,
    SteeringInvariantViolation,
    SteeringIterationResult,
    SteeringOutcome,
    SteeringPlanProjection,
    SteeringStepSpec,
    SteeringStepState,
    SteeringStepType,
    TransitionSteeringStepRequest,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.interaction_store import InteractionStore
from spg.infrastructure.persistence.guided_design_store import GuidedDesignStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.domain.native_execution import SelfRefineActionRecord, SelfRefineEventRecord
from spg.infrastructure.model_runtime import ModelProviderError


LOGGER = logging.getLogger(__name__)
DEFAULT_MAX_STEERING_TRANSITIONS = 32
DEFAULT_PROVIDER_RETRY_BASE_DELAY_SECONDS = 1.0
DEFAULT_PROVIDER_RETRY_MAX_DELAY_SECONDS = 30.0


class PlanSteeringDriver:
    """Reload, decide, and dispatch one persisted semantic action per iteration."""

    def __init__(
        self,
        database: Database,
        work_service: WorkApplicationService,
        production_orchestrator: ProductionOrchestrator,
        *,
        capability: PlanSteeringCapability | None = None,
        semantic_capability: SemanticStepCapability | None = None,
        repository_assets: RepositoryAssetService | None = None,
        max_automatic_transitions: int = DEFAULT_MAX_STEERING_TRANSITIONS,
        provider_retry_base_delay_seconds: float = DEFAULT_PROVIDER_RETRY_BASE_DELAY_SECONDS,
        provider_retry_max_delay_seconds: float = DEFAULT_PROVIDER_RETRY_MAX_DELAY_SECONDS,
        provider_retry_attempt_budget: int = 3,
        provider_retry_same_failure_threshold: int = 2,
        provider_retry_time_budget_seconds: int = 300,
    ) -> None:
        if max_automatic_transitions < 1:
            raise ValueError("Steering transition bound must be positive")
        if provider_retry_base_delay_seconds <= 0:
            raise ValueError("Provider retry base delay must be positive")
        if provider_retry_max_delay_seconds < provider_retry_base_delay_seconds:
            raise ValueError("Provider retry max delay must not be less than base delay")
        if min(provider_retry_attempt_budget, provider_retry_same_failure_threshold, provider_retry_time_budget_seconds) < 1:
            raise ValueError("Provider recovery budgets must be positive")
        self.database = database
        self.work_service = work_service
        self.production_orchestrator = production_orchestrator
        self.max_automatic_transitions = max_automatic_transitions
        self.provider_retry_base_delay_seconds = provider_retry_base_delay_seconds
        self.provider_retry_max_delay_seconds = provider_retry_max_delay_seconds
        self.provider_retry_attempt_budget = provider_retry_attempt_budget
        self.provider_retry_same_failure_threshold = provider_retry_same_failure_threshold
        self.provider_retry_time_budget_seconds = provider_retry_time_budget_seconds
        self.steering = SteeringApplicationService(database)
        self.frames = PlanFrameAssembler(database)
        self.decisions = SteeringDecisionApplicationService(
            database,
            capability or DeterministicPlanSteeringCapability(),
        )
        self.production = SteeringProductionService(database)
        repository_assets = repository_assets or RepositoryAssetService(
            database,
            work_service.workspace_root.parent / "repository-assets",
            work_service.workspace_root.parent / "repository-imports",
        )
        self.semantic = SemanticStepApplicationService(
            database,
            semantic_capability,
            work_service=work_service,
            repository_assets=repository_assets,
        )
        self.guided_design = GuidedDesignApplicationService(database)
        self._condition = Condition(RLock())
        self._active_work_ids: set[UUID] = set()
        self._pending_work_ids: set[UUID] = set()
        self._threads: dict[UUID, Thread] = {}
        self._last_outcomes: dict[UUID, SteeringActivationResult] = {}
        self._provider_retry_attempts: dict[UUID, int] = {}
        self._provider_retry_timers: dict[UUID, Timer] = {}
        self._retryable_provider_failures: set[UUID] = set()
        self._stopping = Event()
        self._governed_repository_action: Callable[[UUID, UUID, str], dict | None] | None = None
        listener = getattr(production_orchestrator, "add_outcome_listener", None)
        if callable(listener):
            listener(self._production_stopped)

    def iterate(self, work_id: UUID) -> SteeringIterationResult:
        """Perform at most one semantic Steering action from freshly loaded facts."""

        before = self.reality_fingerprint(work_id)
        work = self.work_service.get_work(work_id)
        if work.status is WorkStatus.COMPLETED:
            return self._result(
                work_id,
                before,
                action=None,
                stop=SteeringDriverStopReason.COMPLETE,
            )
        reconstruction = self.steering.reconstruct(work_id)
        current = reconstruction.current_step
        if current is None:
            return self._result(
                work_id,
                before,
                action=None,
                stop=SteeringDriverStopReason.NO_PROGRESS,
            )
        frame = self.frames.assemble(work_id)
        revision_blocked = any(
            blocker.kind is PlanFrameBlockerKind.CURRENT_RESULT_MAY_BE_INSUFFICIENT
            for blocker in frame.open_blocking_reality
        )
        revision_acknowledged = bool(
            frame.work_reality_revision_id is not None
            and any(
                reference.kind is RealityReferenceKind.WORK_REALITY_REVISION
                and reference.identity == frame.work_reality_revision_id
                for reference in frame.reconstruction.active_revision.revision.reality_refs
            )
        )
        # A newly admitted Human request can supersede a broad design agenda
        # without first producing a stale Candidate or an active Runtime binding.
        # Reuse the existing governed plan-revision path rather than continuing
        # to ask questions from a plan that predates the current Work request.
        request_revision_unacknowledged = self._unacknowledged_admitted_request(
            frame, revision_acknowledged=revision_acknowledged
        )
        other_blockers = tuple(
            blocker
            for blocker in frame.open_blocking_reality
            if blocker.kind is not PlanFrameBlockerKind.CURRENT_RESULT_MAY_BE_INSUFFICIENT
        )
        if (revision_blocked or request_revision_unacknowledged) and not revision_acknowledged:
            return self._revise_for_current_work_reality(frame, before)
        repository_action = self._repository_action_iteration(frame, before)
        if repository_action is not None:
            return repository_action
        if work.status is WorkStatus.BLOCKED or other_blockers:
            return self._result(
                work_id,
                before,
                action=None,
                stop=SteeringDriverStopReason.BLOCKED,
            )
        if (
            current.type is SteeringStepType.DESIGN
            and self.semantic.result_for_step(current.id) is not None
            and work.change_proposal is not None
            and set(work.change_proposal.allowed_areas)
            & set(work.change_proposal.forbidden_areas)
        ):
            return self._revise_invalid_code_scope(frame, before)
        if work.status is WorkStatus.NEEDS_ATTENTION:
            return self._result(
                work_id,
                before,
                action=None,
                stop=SteeringDriverStopReason.HUMAN_ATTENTION,
            )

        if current.type in {SteeringStepType.VERIFY_ACCEPT, SteeringStepType.COMPLETE}:
            design_artifact = self._approved_intermediate_design_artifact(frame)
            if design_artifact:
                return self._revise_after_design_artifact(frame, before)

        if current.type is SteeringStepType.PRODUCE:
            if work.production_plan is None:
                return self._revise_for_missing_production_plan(frame, before)
            if (
                work.production_plan.target_kind is ProductionTargetKind.CODE_WORK
                and self.guided_design.get_optional(work_id) is not None
                and not self.guided_design.approved_design_artifact_references(work_id)
            ):
                return self._revise_for_missing_production_plan(
                    frame, before, missing_design_artifact=True
                )
            return self._produce_iteration(frame, before)
        if current.type in {SteeringStepType.DESIGN, SteeringStepType.REFINE}:
            return self._semantic_iteration(frame, before)
        return self._decision_iteration(frame, before)

    def _revise_invalid_code_scope(
        self, frame: PlanFrame, before: str,
    ) -> SteeringIterationResult:
        references = tuple(item.reference for item in frame.basis.resolved_reality)
        self.steering.revise_plan(
            ReviseSteeringPlanRequest(
                steering_plan_id=frame.reconstruction.steering_plan_id,
                superseded_revision_id=frame.reconstruction.active_revision.revision.id,
                rationale=(
                    "The proposed code scope both allows and forbids the same area; "
                    "form a corrected proposal from the complete repository path inventory."
                ),
                reality_refs=references,
                steps=(
                    SteeringStepSpec(
                        type=SteeringStepType.DESIGN,
                        objective="Correct the implementation target and scope",
                        completion_condition="A non-conflicting code proposal is reviewable",
                        state=SteeringStepState.CURRENT,
                    ),
                    SteeringStepSpec(
                        type=SteeringStepType.PRODUCE,
                        objective="Implement the admitted code change",
                        completion_condition="The code change reaches trusted Runtime Commit",
                    ),
                    SteeringStepSpec(
                        type=SteeringStepType.VERIFY_ACCEPT,
                        objective="Verify the implemented change",
                        completion_condition="Governed evidence supports the Work outcome",
                    ),
                    SteeringStepSpec(
                        type=SteeringStepType.COMPLETE,
                        objective="Complete the Work outcome",
                        completion_condition="The requested behavior is truthfully satisfied",
                    ),
                ),
            )
        )
        return self._result(
            frame.work_id, before,
            action=SteeringActionType.PLAN_REVISION, stop=None,
        )

    def _approved_intermediate_design_artifact(self, frame: PlanFrame) -> bool:
        with self.database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            work = product.work(frame.work_id)
            binding = product.runtime_binding(frame.work_id)
            if work is None or binding is None or work.production_plan is None:
                return False
            if work.production_plan.target_kind is not ProductionTargetKind.DOCUMENTATION_WORK:
                return False
            if binding.work_reality_revision_id != work.current_work_reality_revision_id:
                return False
            summary = product.runtime_summary(binding)
            if (
                summary.extra.get("task_contract_mode") != "DESIGN_ARTIFACT"
                or summary.runtime_commit_id is None
            ):
                return False
        return bool(self.guided_design.approved_design_artifact_references(frame.work_id))

    def _revise_after_design_artifact(
        self, frame: PlanFrame, before: str,
    ) -> SteeringIterationResult:
        references = tuple(item.reference for item in frame.basis.resolved_reality)
        self.steering.revise_plan(
            ReviseSteeringPlanRequest(
                steering_plan_id=frame.reconstruction.steering_plan_id,
                superseded_revision_id=frame.reconstruction.active_revision.revision.id,
                rationale=(
                    "The approved design artifact is an intermediate prerequisite; "
                    "the admitted working-software outcome still requires implementation."
                ),
                reality_refs=references,
                steps=(
                    SteeringStepSpec(
                        type=SteeringStepType.DESIGN,
                        objective="Form the bounded code change from the approved design artifact",
                        completion_condition="A reviewable implementation proposal is admitted",
                        state=SteeringStepState.CURRENT,
                    ),
                    SteeringStepSpec(
                        type=SteeringStepType.PRODUCE,
                        objective="Implement the approved design in the admitted repository",
                        completion_condition="The code change reaches trusted Runtime Commit",
                    ),
                    SteeringStepSpec(
                        type=SteeringStepType.VERIFY_ACCEPT,
                        objective="Verify the implemented change against the Work outcome",
                        completion_condition="Governed evidence supports the requested behavior",
                    ),
                    SteeringStepSpec(
                        type=SteeringStepType.COMPLETE,
                        objective="Complete the admitted Work outcome",
                        completion_condition="The requested working behavior is truthfully satisfied",
                    ),
                ),
            )
        )
        return self._result(
            frame.work_id, before,
            action=SteeringActionType.PLAN_REVISION, stop=None,
        )

    def configure_governed_repository_action(
        self, action: Callable[[UUID, UUID, str], dict | None],
    ) -> None:
        """Bind the existing admission executor behind Steering's current Reality."""

        self._governed_repository_action = action

    def _repository_action_iteration(
        self, frame: PlanFrame, before: str,
    ) -> SteeringIterationResult | None:
        action = self._governed_repository_action
        if action is None:
            return None
        with self.database.unit_of_work() as uow:
            revision = ProductStore(uow.session).current_work_reality_revision(frame.work_id)
            branch = (
                None if revision is None else governed_branch_creation_target(
                    revision.engineering_semantic_facts,
                    record_for_id=InteractionStore(uow.session).record,
                )
            )
        if not branch or revision is None or revision.repository_ref == f"refs/heads/{branch}":
            return None
        observation = action(frame.work_id, revision.source_interaction_id, revision.admitted_by)
        if observation is None:
            return None
        if observation.get("condition") == "READY":
            return self._result(
                frame.work_id, before,
                action=SteeringActionType.REPOSITORY_ACTION, stop=None,
            )
        return self._result(
            frame.work_id, before,
            action=None,
            stop=(
                SteeringDriverStopReason.PRODUCTION_RUNNING
                if observation.get("condition") in {"REQUESTED", "RUNNING"}
                else SteeringDriverStopReason.BLOCKED
            ),
        )

    def _revise_for_current_work_reality(
        self,
        frame: PlanFrame,
        before: str,
    ) -> SteeringIterationResult:
        revision_id = frame.work_reality_revision_id
        if revision_id is None:
            return self._result(
                frame.work_id,
                before,
                action=None,
                stop=SteeringDriverStopReason.BLOCKED,
            )
        references = tuple(
            item.reference for item in frame.basis.resolved_reality
        )
        self.steering.revise_plan(
            ReviseSteeringPlanRequest(
                steering_plan_id=frame.reconstruction.steering_plan_id,
                superseded_revision_id=(
                    frame.reconstruction.active_revision.revision.id
                ),
                rationale=(
                    "Reassess the admitted Work Reality revision without treating "
                    "the prior production cycle as the current result."
                ),
                reality_refs=references,
                steps=(
                    SteeringStepSpec(
                        type=SteeringStepType.DESIGN,
                        objective=(
                            "Reassess the latest admitted change against existing "
                            "design and production Reality"
                        ),
                        completion_condition=(
                            "The latest Work Reality has a bounded production direction"
                        ),
                        state=SteeringStepState.CURRENT,
                    ),
                    SteeringStepSpec(
                        type=SteeringStepType.PRODUCE,
                        objective=(
                            "Produce the next exact change admitted from the latest "
                            "Work Reality"
                        ),
                        completion_condition=(
                            "The new bounded production cycle reaches trusted Runtime Commit"
                        ),
                    ),
                    SteeringStepSpec(
                        type=SteeringStepType.VERIFY_ACCEPT,
                        objective=(
                            "Assess the new production evidence against the latest "
                            "Work outcome"
                        ),
                        completion_condition=(
                            "Governed evidence supports acceptance or further reassessment"
                        ),
                    ),
                    SteeringStepSpec(
                        type=SteeringStepType.COMPLETE,
                        objective="Complete the latest admitted Work outcome",
                        completion_condition=(
                            "The latest admitted Work Reality is truthfully satisfied"
                        ),
                    ),
                ),
            )
        )
        return self._result(
            frame.work_id,
            before,
            action=SteeringActionType.PLAN_REVISION,
            stop=None,
        )

    def _revise_for_missing_production_plan(
        self,
        frame: PlanFrame,
        before: str,
        *,
        missing_design_artifact: bool = False,
    ) -> SteeringIterationResult:
        """Recover an inadmissible PRODUCE frontier without rewriting history."""

        references = tuple(item.reference for item in frame.basis.resolved_reality)
        self.steering.revise_plan(
            ReviseSteeringPlanRequest(
                steering_plan_id=frame.reconstruction.steering_plan_id,
                superseded_revision_id=(
                    frame.reconstruction.active_revision.revision.id
                ),
                rationale=(
                    "Recover the missing approved design artifact before code production."
                    if missing_design_artifact else
                    "Recover the admitted Work Reality by rebuilding the missing "
                    "current Production Plan before any production cycle is admitted."
                ),
                reality_refs=references,
                steps=(
                    SteeringStepSpec(
                        type=SteeringStepType.DESIGN,
                        objective=(
                            "Prepare the exact design artifact required for the latest "
                            "admitted change"
                            if missing_design_artifact else
                            "Rebuild the exact bounded production direction for the "
                            "latest admitted Work Reality"
                        ),
                        completion_condition=(
                            "A bounded design-artifact Production Plan is materialized"
                            if missing_design_artifact else
                            "A current reviewable Production Plan is materialized"
                        ),
                        state=SteeringStepState.CURRENT,
                    ),
                    SteeringStepSpec(
                        type=SteeringStepType.PRODUCE,
                        objective=(
                            "Produce the next exact change admitted from the latest "
                            "Work Reality"
                        ),
                        completion_condition=(
                            "The new bounded production cycle reaches trusted Runtime Commit"
                        ),
                    ),
                    SteeringStepSpec(
                        type=SteeringStepType.VERIFY_ACCEPT,
                        objective=(
                            "Assess the new production evidence against the latest "
                            "Work outcome"
                        ),
                        completion_condition=(
                            "Governed evidence supports acceptance or further reassessment"
                        ),
                    ),
                    SteeringStepSpec(
                        type=SteeringStepType.COMPLETE,
                        objective="Complete the latest admitted Work outcome",
                        completion_condition=(
                            "The latest admitted Work Reality is truthfully satisfied"
                        ),
                    ),
                ),
            )
        )
        return self._result(
            frame.work_id,
            before,
            action=SteeringActionType.PLAN_REVISION,
            stop=None,
        )

    def activate(self, work_id: UUID) -> SteeringActivationResult:
        """Continue bounded stepwise actions until a typed stop is reached."""

        if self._provider_failure_escalated(work_id):
            return SteeringActivationResult(
                work_id=work_id,
                iterations_executed=0,
                stop_reason=SteeringDriverStopReason.CAPABILITY_UNAVAILABLE,
            )

        iterations = 0
        last_action = None
        while iterations < self.max_automatic_transitions:
            if self._stopping.is_set():
                return SteeringActivationResult(
                    work_id=work_id,
                    iterations_executed=iterations,
                    stop_reason=SteeringDriverStopReason.SHUTDOWN,
                    last_action=last_action,
                )
            try:
                result = self.iterate(work_id)
            except (SteeringInvariantViolation, ProductInvariantViolation):
                LOGGER.exception("Steering stopped on governed invariant Work=%s", work_id)
                return SteeringActivationResult(
                    work_id=work_id,
                    iterations_executed=iterations,
                    stop_reason=SteeringDriverStopReason.BLOCKED,
                    last_action=last_action,
                )
            except ModelProviderError as error:
                self._record_provider_failure(work_id, error)
                LOGGER.warning(
                    "Steering waits for Provider recovery Work=%s kind=%s retryable=%s request_sent=%s usage_unknown=%s",
                    work_id,
                    error.kind.value,
                    error.retryable,
                    error.request_sent,
                    error.usage_unknown,
                )
                return SteeringActivationResult(
                    work_id=work_id,
                    iterations_executed=iterations,
                    stop_reason=SteeringDriverStopReason.CAPABILITY_UNAVAILABLE,
                    last_action=last_action,
                )
            self._clear_provider_failure(work_id)
            if result.action is not None:
                iterations += 1
                last_action = result.action
            if result.stop_reason is not None:
                return SteeringActivationResult(
                    work_id=work_id,
                    iterations_executed=iterations,
                    stop_reason=result.stop_reason,
                    last_action=last_action,
                )
            if not result.progressed:
                return SteeringActivationResult(
                    work_id=work_id,
                    iterations_executed=iterations,
                    stop_reason=SteeringDriverStopReason.NO_PROGRESS,
                    last_action=last_action,
                )
        return SteeringActivationResult(
            work_id=work_id,
            iterations_executed=iterations,
            stop_reason=SteeringDriverStopReason.TRANSITION_BOUND,
            last_action=last_action,
        )

    def schedule(self, work_id: UUID) -> bool:
        """Schedule one bounded activation; duplicate wakeups are coalesced."""

        with self._condition:
            if self._stopping.is_set():
                return False
            waiting = self._provider_retry_timers.pop(work_id, None)
            if waiting is not None:
                waiting.cancel()
            if work_id in self._active_work_ids:
                self._pending_work_ids.add(work_id)
                return False
            self._last_outcomes.pop(work_id, None)
            self._active_work_ids.add(work_id)
            thread = Thread(
                target=self._run_scheduled,
                args=(work_id,),
                name=f"spg-steering-{work_id}",
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
        """Reconstruct restart eligibility without conversation or session state."""

        scheduled: list[UUID] = []
        for work in self.work_service.list_works():
            stale_attention_with_new_request = False
            if work.steering_enabled and work.status is WorkStatus.NEEDS_ATTENTION:
                try:
                    frame = self.frames.assemble(work.work_id)
                    stale_attention_with_new_request = self._unacknowledged_admitted_request(
                        frame
                    )
                except (SteeringInvariantViolation, ProductInvariantViolation):
                    pass
            if (
                work.steering_enabled
                and (
                    work.status in {WorkStatus.READY, WorkStatus.RUNNING}
                    or stale_attention_with_new_request
                )
                and not self.production_orchestrator.is_active(work.work_id)
                and self._restart_eligible(work.work_id)
                and self.schedule(work.work_id)
            ):
                scheduled.append(work.work_id)
        return tuple(scheduled)

    def _unacknowledged_admitted_request(
        self, frame: PlanFrame, *, revision_acknowledged: bool | None = None,
    ) -> bool:
        if frame.work_reality_revision_id is None:
            return False
        if revision_acknowledged is None:
            revision_acknowledged = any(
                reference.kind is RealityReferenceKind.WORK_REALITY_REVISION
                and reference.identity == frame.work_reality_revision_id
                for reference in frame.reconstruction.active_revision.revision.reality_refs
            )
        if revision_acknowledged:
            return False
        with self.database.unit_of_work() as uow:
            revision = ProductStore(uow.session).current_work_reality_revision(frame.work_id)
        return bool(
            revision is not None
            and revision.id == frame.work_reality_revision_id
            and revision.source_kind == "INTERACTION_ASSESSMENT"
            and "requests" in revision.change_set
        )

    def project(self, work_id: UUID) -> SteeringPlanProjection:
        reconstruction = self.steering.reconstruct(work_id)
        work = self.work_service.get_work(work_id)
        current = reconstruction.current_step
        decision = reconstruction.latest_decision
        if decision is not None and decision.steering_plan_revision_id != (
            reconstruction.active_revision.revision.id
        ):
            decision = None
        with self._condition:
            active = work_id in self._active_work_ids
            waiting_resource = work_id in self._provider_retry_timers
            last = self._last_outcomes.get(work_id)
        production_active = self.production_orchestrator.is_active(work_id)
        state = (
            SteeringAutomaticProgressionState.ACTIVE
            if active
            else SteeringAutomaticProgressionState.WAITING_RESOURCE
            if waiting_resource
            else SteeringAutomaticProgressionState.WAITING_PRODUCTION
            if production_active
            else SteeringAutomaticProgressionState.STOPPED
        )
        stop_reason = None if last is None else last.stop_reason
        if production_active:
            stop_reason = SteeringDriverStopReason.PRODUCTION_RUNNING
        elif work.status is WorkStatus.COMPLETED:
            stop_reason = SteeringDriverStopReason.COMPLETE
        elif work.status is WorkStatus.BLOCKED:
            stop_reason = SteeringDriverStopReason.BLOCKED
        elif work.status is WorkStatus.NEEDS_ATTENTION:
            stop_reason = SteeringDriverStopReason.HUMAN_ATTENTION
        return SteeringPlanProjection(
            work_id=work_id,
            work_objective=reconstruction.work_objective,
            steering_enabled=True,
            steering_plan_id=reconstruction.steering_plan_id,
            active_revision_id=reconstruction.active_revision.revision.id,
            active_revision_number=(
                reconstruction.active_revision.revision.revision_number
            ),
            completed_steps=reconstruction.completed_steps,
            current_step=current,
            known_next_steps=reconstruction.known_future_steps,
            plan_change_history=tuple(
                event
                for event in reconstruction.history
                if event.event_type is SteeringHistoryEventType.PLAN_REVISION
            ),
            latest_decision=decision,
            selection_rationale=None if decision is None else decision.reason,
            steering_outcome=(
                None if decision is None else decision.steering_outcome
            ),
            automatic_progression_state=state,
            current_production_cycle_number=work.current_production_cycle_number,
            current_production_run_id=work.current_production_run_id,
            current_production_cycle_trusted=work.current_production_cycle_trusted,
            human_attention_required=work.human_attention_required,
            last_stop_reason=stop_reason,
        )

    def is_active(self, work_id: UUID) -> bool:
        with self._condition:
            return work_id in self._active_work_ids

    def last_outcome(self, work_id: UUID) -> SteeringActivationResult | None:
        with self._condition:
            return self._last_outcomes.get(work_id)

    def wait_until_idle(self, work_id: UUID, timeout: float) -> bool:
        deadline = monotonic() + timeout
        with self._condition:
            while work_id in self._active_work_ids:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return True

    def shutdown(self, timeout: float = 2.0) -> None:
        self._stopping.set()
        deadline = monotonic() + max(timeout, 0.0)
        with self._condition:
            threads = tuple(self._threads.values())
            retry_timers = tuple(self._provider_retry_timers.values())
            self._provider_retry_timers.clear()
        for timer in retry_timers:
            timer.cancel()
        for thread in threads:
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            thread.join(remaining)
        close_semantic = getattr(self.semantic.capability, "close", None)
        if callable(close_semantic):
            close_semantic()

    def reality_fingerprint(self, work_id: UUID) -> str:
        """Hash only freshly reconstructed persisted Work/Plan/Runtime Reality."""

        reconstruction = self.steering.reconstruct(work_id)
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            guided = GuidedDesignStore(unit_of_work.session)
            work = product.work(work_id)
            bindings = product.runtime_bindings(work_id)
            resource = product.resource_for_work(work_id)
            pointer = None if resource is None else runtime.current_pointer(repository_identity=resource.repository_identity, repository_ref=resource.authoritative_ref)
            design_process = guided.process_for_work(work_id)
            design_agenda = (
                None
                if design_process is None
                else guided.active_revision(design_process.id)
            )
            payload = {
                "work": None if work is None else work.model_dump(mode="json"),
                "steering": reconstruction.model_dump(mode="json"),
                "cycles": [
                    {
                        "binding": binding.model_dump(mode="json"),
                        "runtime": product.runtime_summary(binding).model_dump(
                            mode="json"
                        ),
                    }
                    for binding in bindings
                ],
                "baseline_pointer": (
                    None if pointer is None else pointer.model_dump(mode="json")
                ),
                "guided_design": {
                    "process": (
                        None
                        if design_process is None
                        else design_process.model_dump(mode="json")
                    ),
                    "agenda": (
                        None
                        if design_agenda is None
                        else design_agenda.model_dump(mode="json")
                    ),
                },
            }
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def _produce_iteration(
        self,
        frame: PlanFrame,
        before: str,
    ) -> SteeringIterationResult:
        current = frame.reconstruction.current_step
        assert current is not None
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            binding = product.runtime_binding_for_step(current.id)
            summary = (
                RuntimeFactSummary()
                if binding is None
                else product.runtime_summary(binding)
            )

        if binding is not None and summary.runtime_commit_id is not None:
            return self._transition_iteration(frame, before)
        if binding is not None and (
            summary.completion_outcome == "NOT_PRODUCED"
            or any(result != "PASS" for result in summary.verification_results)
            or (
                summary.integration_state is not None
                and summary.integration_state != "CONVERGED"
            )
        ):
            return self._result(
                frame.work_id,
                before,
                action=None,
                stop=SteeringDriverStopReason.BLOCKED,
            )
        if self.production_orchestrator.is_active(frame.work_id):
            return self._result(
                frame.work_id,
                before,
                action=None,
                stop=SteeringDriverStopReason.PRODUCTION_RUNNING,
            )
        if binding is None:
            admission = self.production.admit_cycle(
                self.production.materialize_request(frame.work_id)
            )
            if admission.attention_decision_id is not None:
                return self._result(
                    frame.work_id,
                    before,
                    action=SteeringActionType.HUMAN_ATTENTION,
                    stop=SteeringDriverStopReason.HUMAN_ATTENTION,
                )
            scheduled = self.production_orchestrator.schedule(frame.work_id)
            if not scheduled and not self.production_orchestrator.is_active(
                frame.work_id
            ):
                return self._result(
                    frame.work_id,
                    before,
                    action=SteeringActionType.PRODUCTION_CYCLE_ADMISSION,
                    stop=SteeringDriverStopReason.BLOCKED,
                )
            return self._result(
                frame.work_id,
                before,
                action=SteeringActionType.PRODUCTION_CYCLE_ADMISSION,
                stop=SteeringDriverStopReason.PRODUCTION_RUNNING,
            )

        last = self.production_orchestrator.last_outcome(frame.work_id)
        if last is not None and last.stop_reason in {
            OrchestrationStopReason.NO_SAFE_PROGRESS,
            OrchestrationStopReason.INFRASTRUCTURE_ERROR,
        }:
            return self._result(
                frame.work_id,
                before,
                action=None,
                stop=SteeringDriverStopReason.NO_PROGRESS,
            )
        # A transition bound ends one finite ORCH activation; it is not itself
        # a governed production failure. Steering may schedule another bounded
        # activation from freshly reconstructed Reality so a long but finite
        # verification contract does not require a technical Human Continue.
        scheduled = self.production_orchestrator.schedule(frame.work_id)
        if not scheduled and not self.production_orchestrator.is_active(
            frame.work_id
        ):
            return self._result(
                frame.work_id,
                before,
                action=None,
                stop=SteeringDriverStopReason.BLOCKED,
            )
        return self._result(
            frame.work_id,
            before,
            action=SteeringActionType.PRODUCTION_SCHEDULE,
            stop=SteeringDriverStopReason.PRODUCTION_RUNNING,
        )

    def _decision_iteration(
        self,
        frame: PlanFrame,
        before: str,
    ) -> SteeringIterationResult:
        current = frame.reconstruction.current_step
        assert current is not None
        decision = self._admit_or_reuse(frame)
        if decision.steering_outcome is SteeringOutcome.HUMAN_ATTENTION:
            return self._result(
                frame.work_id,
                before,
                action=SteeringActionType.HUMAN_ATTENTION,
                stop=SteeringDriverStopReason.HUMAN_ATTENTION,
            )
        if current.type is SteeringStepType.COMPLETE:
            return self._result(
                frame.work_id,
                before,
                action=SteeringActionType.COMPLETE,
                stop=SteeringDriverStopReason.COMPLETE,
            )
        return self._transition_iteration(frame, before, decision=decision)

    def _semantic_iteration(
        self,
        frame: PlanFrame,
        before: str,
    ) -> SteeringIterationResult:
        current = frame.reconstruction.current_step
        assert current is not None
        stored_result = self.semantic.result_for_step(current.id)
        guided = self.guided_design.get_optional(frame.work_id)
        if self.semantic.capability is not None and guided is not None:
            result = self.semantic.execute(frame.work_id)
            if stored_result is None or stored_result.id != result.id:
                if result.human_attention_recommendation is not None:
                    self._admit_semantic_attention(frame.work_id, result)
                    return self._result(
                        frame.work_id,
                        before,
                        action=SteeringActionType.HUMAN_ATTENTION,
                        stop=SteeringDriverStopReason.HUMAN_ATTENTION,
                    )
                return self._result(
                    frame.work_id,
                    before,
                    action=SteeringActionType.SEMANTIC_RESULT_ADMISSION,
                    stop=None,
                )
        elif stored_result is None:
            if self.semantic.capability is not None:
                result = self.semantic.execute(frame.work_id)
                if result.human_attention_recommendation is not None:
                    self._admit_semantic_attention(frame.work_id, result)
                    return self._result(
                        frame.work_id,
                        before,
                        action=SteeringActionType.HUMAN_ATTENTION,
                        stop=SteeringDriverStopReason.HUMAN_ATTENTION,
                    )
                return self._result(
                    frame.work_id,
                    before,
                    action=SteeringActionType.SEMANTIC_RESULT_ADMISSION,
                    stop=None,
                )
            return self._result(
                frame.work_id,
                before,
                action=None,
                stop=SteeringDriverStopReason.CAPABILITY_UNAVAILABLE,
            )
        else:
            result = stored_result
        if result.human_attention_recommendation is not None:
            latest = frame.reconstruction.latest_decision
            if not (
                latest is not None
                and latest.current_step_id == current.id
                and latest.steering_outcome is SteeringOutcome.HUMAN_ATTENTION
                and latest.basis_fingerprint == frame.basis.fingerprint
            ):
                self._admit_semantic_attention(frame.work_id, result)
            return self._result(
                frame.work_id,
                before,
                action=SteeringActionType.HUMAN_ATTENTION,
                stop=SteeringDriverStopReason.HUMAN_ATTENTION,
            )
        if not result.completion_satisfied:
            return self._result(
                frame.work_id,
                before,
                action=None,
                stop=SteeringDriverStopReason.NO_PROGRESS,
            )
        guided_step_linked = guided is not None and any(
            issue.steering_step_id == current.id for issue in guided.issues
        )
        design = (
            self.guided_design.record_semantic_result(frame.work_id, result)
            if guided_step_linked
            else guided
        )
        fresh = self.frames.assemble(frame.work_id)
        if (
            design is not None
            and design.readiness.state is DesignReadinessState.READY
            and result.proposed_production is not None
            and not self._production_proposal_reviewed(frame.work_id, result.id)
        ):
            if self._admit_bounded_managed_proposal(frame.work_id, result):
                return self._decision_iteration(self.frames.assemble(frame.work_id), before)
            existing = fresh.reconstruction.latest_decision
            if not (
                existing is not None
                and existing.current_step_id == current.id
                and existing.steering_outcome is SteeringOutcome.HUMAN_ATTENTION
                and existing.attention_reason
                is SteeringAttentionReason.PRODUCTION_PROPOSAL_REVIEW_REQUIRED
                and existing.basis_fingerprint == fresh.basis.fingerprint
            ):
                refs = tuple(item.reference for item in fresh.basis.resolved_reality)
                self.decisions.admit(
                    frame.work_id,
                    NextStepCandidate(
                        type=SteeringStepType.HUMAN_DECISION,
                        objective="Review the governed production proposal",
                        reason=(
                            "Guided design is READY and has formed an exact proposal; "
                            "Human must understand it before production admission"
                        ),
                        reality_refs=refs,
                        human_required=True,
                        completion_condition=(
                            "Human explicitly admits or requests refinement of the exact proposal"
                        ),
                        proposed_outcome=SteeringOutcome.HUMAN_ATTENTION,
                        basis_fingerprint=fresh.basis.fingerprint,
                        authority_assessment=SteeringAuthorityAssessment.WITHIN_AUTHORITY,
                        attention_reason=(
                            SteeringAttentionReason.PRODUCTION_PROPOSAL_REVIEW_REQUIRED
                        ),
                        recommendation="Review objective, scope, constraints, impact, and verification before admitting production",
                        expected_impact=(
                            "Approval permits existing Plan Steering and SPG admission; "
                            "no approval means no Run or PWU"
                        ),
                    ),
                )
            return self._result(
                frame.work_id,
                before,
                action=SteeringActionType.HUMAN_ATTENTION,
                stop=SteeringDriverStopReason.HUMAN_ATTENTION,
            )
        return self._decision_iteration(fresh, before)

    def _production_proposal_reviewed(self, work_id: UUID, result_id: UUID) -> bool:
        with self.database.unit_of_work() as unit_of_work:
            records = RuntimeStore(unit_of_work.session).governance_for_subject(
                str(work_id)
            )
        return any(
            record.decision_type in {
                "APPROVE_GUIDED_PRODUCTION_PROPOSAL",
                "AUTO_ADMIT_BOUNDED_MANAGED_PROPOSAL",
                "AUTO_ADMIT_DESIGN_ARTIFACT_PROPOSAL",
            }
            and record.scope.get("semantic_result_id") == str(result_id)
            for record in records
        )

    def _admit_bounded_managed_proposal(
        self, work_id: UUID, result: SemanticStepResultRecord
    ) -> bool:
        """Auto-admit only a safe prerequisite artifact or prerequisite-backed code.

        Initial Guided Design must materialize a reviewable artifact. Bounded
        managed code remains eligible only after that artifact is Human-approved
        and committed. External or broad changes retain exact proposal review.
        """
        proposal = result.proposed_production
        if (
            proposal is None
            or not result.completion_satisfied
            or result.human_attention_recommendation is not None
        ):
            return False
        design_artifact = (
            proposal.target_kind is ProductionTargetKind.DOCUMENTATION_WORK
            and len(proposal.artifact_targets) == 1
        )
        approved_design = self.guided_design.approved_design_artifact_references(
            work_id
        )
        bounded_code = (
            proposal.target_kind is ProductionTargetKind.CODE_WORK
            and bool(approved_design)
            and 1 <= len(proposal.code_targets) <= 4
        )
        if not design_artifact and not bounded_code:
            return False
        with self.database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            runtime = RuntimeStore(uow.session)
            work = product.work(work_id)
            resource = product.resource_for_work(work_id)
            if (work is None or resource is None
                    or work.production_plan is None
                    or work.production_plan.fit_classification is not OnePwuFitClassification.ONE_PWU_FIT
                    or product.runtime_binding_for_step(result.step_id) is not None):
                return False
            admitted = runtime.governance_for_subject(str(work_id))
            work_admitted = any(
                record.decision_type == "ADMIT_LONG_LIVED_WORK"
                for record in admitted
            )
            source_admitted = any(
                record.decision_type == "ADMIT_LONG_LIVED_WORK"
                and record.scope.get("source_revision")
                == work.production_plan.source_revision
                for record in admitted
            )
            managed_workspace_admitted = any(
                record.decision_type == "ALLOCATE_MANAGED_EXECUTION_WORKSPACE"
                and record.scope.get("resource_id") == str(resource.id)
                and record.scope.get("source_baseline_id")
                == str(work.production_plan.source_baseline_id)
                and record.scope.get("source_revision")
                == work.production_plan.source_revision
                for record in admitted
            )
            if not work_admitted or not (source_admitted or managed_workspace_admitted):
                return False
            identity = uuid5(NAMESPACE_URL, f"spg:auto-managed-proposal:{result.id}")
            if not any(record.id == identity for record in admitted):
                decision_type = (
                    "AUTO_ADMIT_DESIGN_ARTIFACT_PROPOSAL"
                    if design_artifact
                    else "AUTO_ADMIT_BOUNDED_MANAGED_PROPOSAL"
                )
                runtime.insert_governance({
                    "id": identity,
                    "decision_type": decision_type,
                    "authority_identity": "steering:auto-within-work-authority",
                    "subject_type": "GUIDED_PRODUCTION_PROPOSAL",
                    "subject_identity": str(work_id),
                    "scope": {
                        "work_id": str(work_id),
                        "work_reality_revision_id": str(work.current_work_reality_revision_id),
                        "semantic_result_id": str(result.id),
                        "source_revision": work.production_plan.source_revision,
                        "code_targets": list(proposal.code_targets),
                        "artifact_targets": [
                            item.model_dump(mode="json")
                            for item in proposal.artifact_targets
                        ],
                        "approved_design_artifact_references": list(
                            approved_design
                        ),
                    },
                    "rationale": (
                        "The exact bounded, reversible proposal either materializes "
                        "the required design-review artifact or implements against "
                        "an already approved design artifact in admitted Work Reality."
                    ),
                    "created_at": datetime.now(UTC),
                })
                uow.commit()
        return True

    def _admit_semantic_attention(
        self,
        work_id: UUID,
        result: SemanticStepResultRecord,
    ) -> SteeringDecisionRecord:
        fresh = self.frames.assemble(work_id)
        current = fresh.reconstruction.current_step
        assert current is not None
        refs = tuple(item.reference for item in fresh.basis.resolved_reality)
        reason = (
            SteeringAttentionReason.SCOPE_OR_AUTHORITY_EXPANSION
            if result.authority_assessment
            is SteeringAuthorityAssessment.EXPANDS_AUTHORITY
            else SteeringAttentionReason.MOTIVE_OR_OUTCOME_AMBIGUITY
            if current.type is SteeringStepType.REFINE
            else SteeringAttentionReason.MAJOR_PRODUCT_OR_ARCHITECTURE_DECISION
        )
        return self.decisions.admit(
            work_id,
            NextStepCandidate(
                type=SteeringStepType.HUMAN_DECISION,
                objective="Resolve the material semantic Steering question",
                reason=result.bounded_summary,
                reality_refs=refs,
                human_required=True,
                completion_condition=(
                    "Human Authority resolves the semantic question before continuation"
                ),
                proposed_outcome=SteeringOutcome.HUMAN_ATTENTION,
                basis_fingerprint=fresh.basis.fingerprint,
                authority_assessment=result.authority_assessment,
                proposed_engineering_scope_fingerprint=(
                    fresh.engineering_scope_fingerprint
                ),
                attention_reason=reason,
                recommendation=result.human_attention_recommendation,
                expected_impact=(
                    "No semantic Step transition or SPG production occurs before resolution"
                ),
                reasoning_provider_identity=result.reasoning_provider_identity,
            ),
        )

    def _transition_iteration(
        self,
        frame: PlanFrame,
        before: str,
        *,
        decision: SteeringDecisionRecord | None = None,
    ) -> SteeringIterationResult:
        current = frame.reconstruction.current_step
        next_step = frame.reconstruction.next_step
        assert current is not None
        decision = decision or self._admit_or_reuse(frame)
        if decision.steering_outcome is SteeringOutcome.HUMAN_ATTENTION:
            return self._result(
                frame.work_id,
                before,
                action=SteeringActionType.HUMAN_ATTENTION,
                stop=SteeringDriverStopReason.HUMAN_ATTENTION,
            )
        if next_step is None:
            return self._result(
                frame.work_id,
                before,
                action=None,
                stop=SteeringDriverStopReason.BLOCKED,
            )
        self.steering.transition_step(
            TransitionSteeringStepRequest(
                steering_plan_revision_id=(
                    frame.reconstruction.active_revision.revision.id
                ),
                current_step_id=current.id,
                next_step_id=next_step.id,
                steering_decision_id=decision.id,
            )
        )
        stop = (
            SteeringDriverStopReason.COMPLETE
            if decision.steering_outcome is SteeringOutcome.COMPLETE
            else None
        )
        return self._result(
            frame.work_id,
            before,
            action=(
                SteeringActionType.COMPLETE
                if stop is SteeringDriverStopReason.COMPLETE
                else SteeringActionType.STEP_TRANSITION
            ),
            stop=stop,
        )

    def _admit_or_reuse(self, frame: PlanFrame) -> SteeringDecisionRecord:
        current = frame.reconstruction.current_step
        existing = frame.reconstruction.latest_decision
        expected_refs = tuple(item.reference for item in frame.basis.resolved_reality)
        if (
            current is not None
            and existing is not None
            and existing.current_step_id == current.id
            and existing.basis_fingerprint == frame.basis.fingerprint
            and existing.reality_refs == expected_refs
            and not (
                existing.attention_reason
                is SteeringAttentionReason.PRODUCTION_PROPOSAL_REVIEW_REQUIRED
                and (semantic_result := self.semantic.result_for_step(current.id))
                is not None
                and self._production_proposal_reviewed(
                    frame.work_id,
                    semantic_result.id,
                )
            )
        ):
            return existing
        _fresh_frame, candidate = self.decisions.evaluate(frame.work_id)
        return self.decisions.admit(frame.work_id, candidate)

    def _result(
        self,
        work_id: UUID,
        before: str,
        *,
        action: SteeringActionType | None,
        stop: SteeringDriverStopReason | None,
    ) -> SteeringIterationResult:
        after = self.reality_fingerprint(work_id)
        progressed = before != after
        if not progressed and stop is None:
            stop = SteeringDriverStopReason.NO_PROGRESS
        return SteeringIterationResult(
            work_id=work_id,
            action=action,
            progressed=progressed,
            before_fingerprint=before,
            after_fingerprint=after,
            stop_reason=stop,
        )

    def _production_stopped(self, outcome: OrchestrationOutcome) -> None:
        if (
            not self._stopping.is_set()
            and self.work_service.get_work(outcome.work_id).steering_enabled
        ):
            self.schedule(outcome.work_id)

    def _restart_eligible(self, work_id: UUID) -> bool:
        """Prove restart safety without evaluating or admitting a new decision."""

        try:
            reconstruction = self.steering.reconstruct(work_id)
            if reconstruction.current_step is None:
                return False
            frame = self.frames.assemble(work_id)
        except (SteeringInvariantViolation, ProductInvariantViolation):
            return False
        return not any(
            blocker.kind is not PlanFrameBlockerKind.CURRENT_RESULT_MAY_BE_INSUFFICIENT
            for blocker in frame.open_blocking_reality
        )

    def _run_scheduled(self, work_id: UUID) -> None:
        try:
            outcome = self.activate(work_id)
        except Exception:
            LOGGER.exception("Steering activation failed Work=%s", work_id)
            outcome = SteeringActivationResult(
                work_id=work_id,
                iterations_executed=0,
                stop_reason=SteeringDriverStopReason.BLOCKED,
            )
        rerun = False
        with self._condition:
            self._last_outcomes[work_id] = outcome
            self._threads.pop(work_id, None)
            self._active_work_ids.discard(work_id)
            rerun = work_id in self._pending_work_ids and not self._stopping.is_set()
            self._pending_work_ids.discard(work_id)
            self._condition.notify_all()
        if (
            outcome.stop_reason is SteeringDriverStopReason.CAPABILITY_UNAVAILABLE
            and self._provider_failure_is_retryable(work_id)
        ):
            self._schedule_provider_retry(work_id)
        elif rerun:
            self.schedule(work_id)

    def _record_provider_failure(
        self, work_id: UUID, error: ModelProviderError
    ) -> None:
        now = datetime.now(UTC)
        family = f"PROVIDER_{error.kind.value}"
        signature = sha256(f"{family}:{error.retryable}".encode("utf-8")).hexdigest()
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            revision = ProductStore(uow.session).current_work_reality_revision(work_id)
            revision_id = None if revision is None else str(revision.id)
            event = store.open_self_refine_event(work_id)
            if event is None:
                event_id = uuid4()
                event = SelfRefineEventRecord(
                    id=event_id, work_id=work_id, operation_id=work_id,
                    created_at=now, failure_family=family,
                    failure_signature=signature, affected_component="steering/provider",
                    expected_reality={"outcome": "GOVERNED_STEERING_PROGRESSION", "work_revision_id": revision_id},
                    observed_reality={"provider_kind": error.kind.value, "retryable": error.retryable},
                    diagnosis_summary="Steering Provider did not return an admissible result.",
                    root_cause_classification=family,
                    repair_hypothesis="Retry the same governed semantic basis after bounded backoff without changing Human authority.",
                    evidence_references=(f"work:{work_id}",),
                    known_failure_match=store.prior_self_refine_matches(signature, before_event_id=event_id) > 0,
                    updated_at=now,
                )
                store.insert_self_refine_event(event)
            actions = store.self_refine_actions(event.id)
            same = sum(
                action.observed_reality.get("failure_signature") == signature
                for action in actions
            ) + 1
            exhausted = (
                not error.retryable
                or len(actions) + 1 > self.provider_retry_attempt_budget
                or same >= self.provider_retry_same_failure_threshold
                or (now - event.created_at).total_seconds() >= self.provider_retry_time_budget_seconds
            )
            store.append_self_refine_action(SelfRefineActionRecord(
                id=uuid4(), event_id=event.id, sequence=len(actions) + 1,
                created_at=now,
                repair_action=(
                    "Escalate Provider failure; current evidence does not justify another retry"
                    if exhausted else "Retry governed Steering against the same persisted Work Reality"
                ),
                observed_reality={"failure_signature": signature, "work_revision_id": revision_id},
                evidence_references=(f"work:{work_id}",),
                outcome="ESCALATED" if exhausted else "RETRY_SCHEDULED",
            ))
            if exhausted:
                store.complete_self_refine_event(
                    event.id, result="ESCALATED", resume_result="NOT_RESUMED",
                    status="MITIGATED", elapsed_seconds=max(0, int((now - event.created_at).total_seconds())),
                    updated_at=now, compute_overhead={"provider_attempts": len(actions) + 1},
                )
            uow.commit()
        with self._condition:
            if error.retryable and not exhausted:
                self._retryable_provider_failures.add(work_id)
                self._provider_retry_attempts[work_id] = len(actions) + 1
            else:
                self._retryable_provider_failures.discard(work_id)

    def _clear_provider_failure(self, work_id: UUID) -> None:
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            event = store.open_self_refine_event(work_id)
            if event is not None and event.affected_component == "steering/provider":
                now = datetime.now(UTC)
                actions = store.self_refine_actions(event.id)
                store.append_self_refine_action(SelfRefineActionRecord(
                    id=uuid4(), event_id=event.id, sequence=len(actions) + 1,
                    created_at=now,
                    repair_action="Re-observe governed Steering progression after Provider recovery",
                    observed_reality={"provider_result": "ADMITTED"},
                    evidence_references=(f"work:{work_id}",),
                    outcome="RECOVERED",
                ))
                store.complete_self_refine_event(
                    event.id, result="RECOVERED", resume_result="RESUMED",
                    status="VERIFIED", elapsed_seconds=max(0, int((now - event.created_at).total_seconds())),
                    updated_at=now, compute_overhead={"provider_attempts": len(actions) + 1},
                )
                uow.commit()
        with self._condition:
            self._retryable_provider_failures.discard(work_id)
            self._provider_retry_attempts.pop(work_id, None)

    def _provider_failure_escalated(self, work_id: UUID) -> bool:
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            latest = store.list_self_refine_events(
                work_id=work_id, component="steering/provider", limit=1,
            )
            if not latest or latest[0].final_result != "ESCALATED":
                return False
            revision = ProductStore(uow.session).current_work_reality_revision(work_id)
            return latest[0].expected_reality.get("work_revision_id") == (
                None if revision is None else str(revision.id)
            )

    def _provider_failure_is_retryable(self, work_id: UUID) -> bool:
        with self._condition:
            return work_id in self._retryable_provider_failures

    def _schedule_provider_retry(self, work_id: UUID) -> None:
        with self._condition:
            if self._stopping.is_set() or work_id in self._provider_retry_timers:
                return
            attempt = self._provider_retry_attempts.get(work_id, 1)
            delay = min(
                self.provider_retry_base_delay_seconds * (2 ** min(attempt - 1, 10)),
                self.provider_retry_max_delay_seconds,
            )
            timer = Timer(delay, self._resume_after_provider_wait, args=(work_id,))
            timer.daemon = True
            self._provider_retry_timers[work_id] = timer
        LOGGER.info(
            "Steering Provider retry scheduled Work=%s attempt=%s delay_seconds=%s",
            work_id,
            attempt,
            delay,
        )
        timer.start()

    def _resume_after_provider_wait(self, work_id: UUID) -> None:
        with self._condition:
            self._provider_retry_timers.pop(work_id, None)
            if self._stopping.is_set():
                return
        self.schedule(work_id)
