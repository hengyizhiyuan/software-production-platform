"""Bounded process-local driver over authoritative Steering and SPG Reality."""

from __future__ import annotations

from hashlib import sha256
import json
import logging
from threading import Condition, Event, RLock, Thread
from time import monotonic
from uuid import UUID

from spg.application.orchestration import (
    OrchestrationOutcome,
    OrchestrationStopReason,
    ProductionOrchestrator,
)
from spg.application.assets import RepositoryAssetService
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
from spg.domain.steering import (
    NextStepCandidate,
    PlanFrame,
    PlanSteeringCapability,
    SemanticStepCapability,
    SemanticStepResultRecord,
    SteeringActionType,
    SteeringActivationResult,
    SteeringAttentionReason,
    SteeringAuthorityAssessment,
    SteeringAutomaticProgressionState,
    SteeringDecisionRecord,
    SteeringDriverStopReason,
    SteeringInvariantViolation,
    SteeringIterationResult,
    SteeringOutcome,
    SteeringPlanProjection,
    SteeringStepType,
    TransitionSteeringStepRequest,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.guided_design_store import GuidedDesignStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore


LOGGER = logging.getLogger(__name__)
DEFAULT_MAX_STEERING_TRANSITIONS = 32


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
        max_automatic_transitions: int = DEFAULT_MAX_STEERING_TRANSITIONS,
    ) -> None:
        if max_automatic_transitions < 1:
            raise ValueError("Steering transition bound must be positive")
        self.database = database
        self.work_service = work_service
        self.production_orchestrator = production_orchestrator
        self.max_automatic_transitions = max_automatic_transitions
        self.steering = SteeringApplicationService(database)
        self.frames = PlanFrameAssembler(database)
        self.decisions = SteeringDecisionApplicationService(
            database,
            capability or DeterministicPlanSteeringCapability(),
        )
        self.production = SteeringProductionService(database)
        repository_assets = RepositoryAssetService(
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
        self._stopping = Event()
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
        if work.status is WorkStatus.BLOCKED or frame.open_blocking_reality:
            return self._result(
                work_id,
                before,
                action=None,
                stop=SteeringDriverStopReason.BLOCKED,
            )
        if work.status is WorkStatus.NEEDS_ATTENTION:
            return self._result(
                work_id,
                before,
                action=None,
                stop=SteeringDriverStopReason.HUMAN_ATTENTION,
            )

        if current.type is SteeringStepType.PRODUCE:
            return self._produce_iteration(frame, before)
        if current.type in {SteeringStepType.DESIGN, SteeringStepType.REFINE}:
            return self._semantic_iteration(frame, before)
        return self._decision_iteration(frame, before)

    def activate(self, work_id: UUID) -> SteeringActivationResult:
        """Continue bounded stepwise actions until a typed stop is reached."""

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
            if (
                work.steering_enabled
                and work.status in {WorkStatus.READY, WorkStatus.RUNNING}
                and not self.production_orchestrator.is_active(work.work_id)
                and self._restart_eligible(work.work_id)
                and self.schedule(work.work_id)
            ):
                scheduled.append(work.work_id)
        return tuple(scheduled)

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
            last = self._last_outcomes.get(work_id)
        production_active = self.production_orchestrator.is_active(work_id)
        state = (
            SteeringAutomaticProgressionState.ACTIVE
            if active
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
        for thread in threads:
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            thread.join(remaining)

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
                stop=SteeringDriverStopReason.NO_PROGRESS,
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
        design = self.guided_design.record_semantic_result(frame.work_id, result)
        fresh = self.frames.assemble(frame.work_id)
        if (
            design is not None
            and design.readiness.state is DesignReadinessState.READY
            and result.proposed_production is not None
            and not self._production_proposal_reviewed(frame.work_id, result.id)
        ):
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
            record.decision_type == "APPROVE_GUIDED_PRODUCTION_PROPOSAL"
            and record.scope.get("semantic_result_id") == str(result_id)
            for record in records
        )

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
        return not frame.open_blocking_reality

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
        if rerun:
            self.schedule(work_id)
