"""Explicit Human production requests trigger the existing admission chain."""

from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5
from time import monotonic, sleep

from spg.application.assets import RepositoryAssetService
from spg.application.product_assets import ProductAssetService
from spg.application.interaction import WorkInteractionService
from spg.application.post_admission import WorkPostAdmissionService
from spg.application.repository_branch_authority import (
    BRANCH_FACT_SUBJECTS,
    governed_branch_creation_target,
)
from spg.application.work import WorkApplicationService
from spg.domain.assets import (
    AssetScopeAdmissionRequest,
    RepositoryAcquisitionFailureCategory,
    RepositoryIntakeRequest,
)
from spg.domain.interaction import (
    InteractionAssessment,
    InteractionRecord,
    InteractionActor,
    InterpretationMeaningKind,
    WorkFocusClassification,
    ProductionAdmissionExecutionState,
    RepositoryAcquisitionState,
    WorkAdmissionReadinessStatus,
)
from spg.domain.product import AttentionAction
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.interaction_store import InteractionStore
from spg.infrastructure.persistence.steering_store import SteeringStore
from spg.domain.steering import SteeringStepType, SteeringAttentionReason
from spg.domain.intent_realization import SemanticKind
from spg.domain.engineering_semantics import SemanticRelation, current_semantic_facts
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.domain.refinement_contract import RefinementSignalKind
from spg.domain.interaction_actions import CanonicalOperation
from spg.application.intent_realization import executable_semantic_actions, current_step_semantic_items, latest_assessment_revision


class ProductionAdmissionTrigger:
    """Translate explicit Human authority into existing Work admission actions.

    The Human request authorizes Work formation and read-only acquisition of an
    explicitly supplied repository source. It does not grant private repository
    access, delivery authority, or Human acceptance.
    """

    def __init__(
        self,
        interactions: WorkInteractionService,
        work: WorkApplicationService,
        assets: RepositoryAssetService,
        post_admission: WorkPostAdmissionService,
    ) -> None:
        self.interactions = interactions
        self.work = work
        self.assets = assets
        self.post_admission = post_admission

    @staticmethod
    def _repository_state(observation: dict | None) -> RepositoryAcquisitionState:
        condition = None if observation is None else observation.get("condition")
        return {
            "REQUESTED": RepositoryAcquisitionState.REQUESTED,
            "RUNNING": RepositoryAcquisitionState.RUNNING,
            "READY": RepositoryAcquisitionState.READY,
            "WAITING_FOR_AUTHORIZATION": (
                RepositoryAcquisitionState.WAITING_FOR_AUTHORIZATION
            ),
            "FAILED_RETRYABLE": RepositoryAcquisitionState.FAILED_RETRYABLE,
            "BLOCKED": RepositoryAcquisitionState.FAILED_RETRYABLE,
            "FAILED_TERMINAL": RepositoryAcquisitionState.FAILED_TERMINAL,
            "WAITING_FOR_REPOSITORY_SOURCE": (
                RepositoryAcquisitionState.WAITING_FOR_REPOSITORY_SOURCE
            ),
            # Historical unresolved observations represented unknown access.
            "UNRESOLVED": RepositoryAcquisitionState.WAITING_FOR_AUTHORIZATION,
        }.get(condition, RepositoryAcquisitionState.NOT_STARTED)

    @classmethod
    def _next_step(cls, observation: dict | None) -> str:
        state = cls._repository_state(observation)
        if state is RepositoryAcquisitionState.REQUESTED:
            if observation is not None and observation.get("operation_kind") == "CREATE_BRANCH":
                return f"Create local branch {observation.get('target_branch')} from the bound baseline."
            return "Start the persisted repository acquisition operation."
        if state is RepositoryAcquisitionState.RUNNING:
            if observation is not None and observation.get("operation_kind") == "CREATE_BRANCH":
                return f"Creating local branch {observation.get('target_branch')}."
            return "Acquire the selected repository branch and exact revision."
        if state is RepositoryAcquisitionState.READY:
            if observation is not None and observation.get("operation_kind") == "CREATE_BRANCH":
                return f"Local branch {observation.get('target_branch')} is ready for this Work."
            return "Continue Steering against the acquired repository Reality."
        if state is RepositoryAcquisitionState.WAITING_FOR_AUTHORIZATION:
            return "Authorize repository read access, then retry this acquisition."
        if state is RepositoryAcquisitionState.FAILED_RETRYABLE:
            return "Retry repository acquisition from the preserved source."
        if state is RepositoryAcquisitionState.FAILED_TERMINAL:
            return "Correct the repository source or branch before retrying."
        return "Bind the repository source before Steering begins."

    def projection(
        self, interaction_id: UUID, work_id: UUID | None
    ) -> tuple[
        ProductionAdmissionExecutionState,
        RepositoryAcquisitionState,
        str,
        str | None,
    ] | None:
        if work_id is None:
            return None
        observation = self.assets.latest_attempt_for_work(work_id)
        if observation is None:
            return (
                ProductionAdmissionExecutionState.WORK_CREATED,
                RepositoryAcquisitionState.WAITING_FOR_REPOSITORY_SOURCE,
                "Bind the referenced repository source before Steering begins.",
                None,
            )
        state = self._repository_state(observation)
        if state is RepositoryAcquisitionState.READY:
            with self.work.database.unit_of_work() as uow:
                selected = ProductStore(uow.session).resource_for_work(work_id)
                revision = ProductStore(uow.session).current_work_reality_revision(work_id)
            if (
                selected is None
                or str(selected.id) != observation.get("resource_id")
                or revision is None or revision.repository_identity != selected.repository_identity
                or revision.repository_ref != observation.get("repository_ref")
                or revision.source_revision != observation.get("revision")
            ):
                state = RepositoryAcquisitionState.RUNNING
                next_step = "Bind acquired repository Reality to this Work."
            else:
                next_step = self._next_step(observation)
        else:
            next_step = self._next_step(observation)
        return (
            ProductionAdmissionExecutionState.WORK_CREATED,
            state,
            next_step,
            observation.get("source"),
        )

    def _start_attempt(
        self,
        *,
        interaction_id: UUID,
        work_id: UUID,
        source: str,
        title: str,
        description: str,
        authority_identity: str,
    ) -> dict:
        previous = self.assets.latest_attempt_for_work(work_id)
        attempt_number = self.assets.next_attempt_number(work_id)
        attempt_id = uuid5(
            NAMESPACE_URL,
            f"watt:repository-acquisition:{work_id}:{attempt_number}:{source}",
        )
        return self.assets.start_intake(
            RepositoryIntakeRequest(
                request_id=attempt_id,
                source=source,
                title=title[:200],
                description=description[:4000],
                authority_identity=authority_identity,
                interaction_id=interaction_id,
                work_id=work_id,
                attempt_number=attempt_number,
                previous_attempt_id=(
                    None
                    if previous is None
                    else UUID(previous["intake_request_id"])
                ),
            )
        )

    def _start_branch_attempt(
        self,
        *,
        interaction_id: UUID,
        work_id: UUID,
        source: str,
        base_resource_id: UUID,
        target_branch: str,
        authority_identity: str,
    ) -> dict:
        previous = self.assets.latest_attempt_for_work(work_id)
        attempt_number = self.assets.next_attempt_number(work_id)
        return self.assets.start_intake(
            RepositoryIntakeRequest(
                request_id=uuid5(
                    NAMESPACE_URL,
                    f"watt:work-branch:{work_id}:{attempt_number}:{target_branch}",
                ),
                source=source,
                title=f"Create local branch {target_branch}"[:200],
                description=(
                    "Create an isolated Work branch from the bound repository baseline."
                ),
                authority_identity=authority_identity,
                interaction_id=interaction_id,
                work_id=work_id,
                attempt_number=attempt_number,
                previous_attempt_id=(
                    None if previous is None else UUID(previous["intake_request_id"])
                ),
                operation_kind="CREATE_BRANCH",
                base_resource_id=base_resource_id,
                target_branch=target_branch,
            )
        )

    def _bind_and_activate(
        self,
        *,
        work_id: UUID,
        observation: dict,
        authority_identity: str,
        rationale: str,
    ) -> dict:
        """Bind acquired Reality and activate only after the binding is durable."""

        if observation.get("condition") != "READY" or not observation.get(
            "resource_id"
        ):
            return observation
        try:
            current = self.work.get_work(work_id)
            with self.work.database.unit_of_work() as uow:
                selected = ProductStore(uow.session).resource_for_work(work_id)
                revision = ProductStore(uow.session).current_work_reality_revision(work_id)
            if (selected is None or str(selected.id) != observation["resource_id"]
                    or revision is None or revision.repository_identity != selected.repository_identity
                    or revision.repository_ref != observation.get("repository_ref")
                    or revision.source_revision != observation.get("revision")):
                current = self.work.admit_asset_scope(
                    work_id,
                    AssetScopeAdmissionRequest(
                        resource_id=UUID(observation["resource_id"]),
                        expected_work_revision_id=(
                            current.current_work_reality_revision_id
                        ),
                        observation_fingerprint=observation["fingerprint"],
                        authority_identity=authority_identity,
                        rationale=rationale,
                    ),
                    observation,
                )
            ProductAssetService(self.work.database).ensure_repository_work(
                work_id, UUID(observation["resource_id"]), authority_identity,
                revision=observation["revision"],
                repository_ref=observation["repository_ref"],
                tree=observation.get("tree"),
            )
            if not current.steering_enabled:
                self.post_admission.activate(work_id)
            return observation
        except Exception as error:
            return self.assets.mark_attempt_failure(
                UUID(observation["intake_request_id"]),
                category=(
                    RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE
                ),
                human_message=(
                    "The repository was acquired, but it could not be bound to this "
                    "Work. The governed acquisition can be retried."
                ),
                technical_evidence={
                    "phase": "WORK_REALITY_BINDING",
                    "error_type": type(error).__name__,
                    "message": str(error)[:2000],
                },
                retryable=True,
            )

    def reconcile_governed_branch(
        self,
        work_id: UUID,
        *,
        interaction_id: UUID,
        authority_identity: str,
    ) -> dict | None:
        """Execute only a Human-admitted branch fact against bound repository Reality."""

        with self.work.database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            revision = product.current_work_reality_revision(work_id)
            base = product.resource_for_work(work_id)
            branch_name = (
                None if revision is None else governed_branch_creation_target(
                    revision.engineering_semantic_facts,
                    record_for_id=InteractionStore(uow.session).record,
                )
            )
        if revision is None or base is None:
            return None
        if not branch_name:
            return None
        if revision.repository_ref == f"refs/heads/{branch_name}":
            return self.assets.latest_attempt_for_work(work_id)
        latest = self.assets.latest_attempt_for_work(work_id)
        if (
            latest is not None
            and latest.get("operation_kind") == "CREATE_BRANCH"
            and latest.get("target_branch") == branch_name
        ):
            if latest.get("condition") in {"FAILED_RETRYABLE", "FAILED_TERMINAL"}:
                return latest
            if latest.get("condition") == "READY":
                return self._bind_and_activate(
                    work_id=work_id,
                    observation=latest,
                    authority_identity=authority_identity,
                    rationale="Bind the Human-requested branch to current Work Reality.",
                )
            observation = self.assets.execute_intake(
                UUID(latest["intake_request_id"])
            )
            return self._bind_and_activate(
                work_id=work_id,
                observation=observation,
                authority_identity=authority_identity,
                rationale="Bind the Human-requested branch to current Work Reality.",
            )
        source = (
            latest.get("source") if latest is not None else revision.repository_identity
        )
        started = self._start_branch_attempt(
            interaction_id=interaction_id,
            work_id=work_id,
            source=source,
            base_resource_id=base.id,
            target_branch=branch_name,
            authority_identity=authority_identity,
        )
        observation = self.assets.execute_intake(UUID(started["intake_request_id"]))
        return self._bind_and_activate(
            work_id=work_id,
            observation=observation,
            authority_identity=authority_identity,
            rationale="Bind the Human-requested branch to current Work Reality.",
        )

    def execute_governed_turn(self, interaction_id: UUID,
        assessment: InteractionAssessment, request_record: InteractionRecord) -> str | None:
        branch_items = tuple(item for item in executable_semantic_actions(assessment.semantic_ir)
            if item.action.operation in {CanonicalOperation.CREATE_BRANCH.value, CanonicalOperation.SWITCH_BRANCH.value,
                CanonicalOperation.CREATE_AND_SWITCH_BRANCH.value, CanonicalOperation.ACQUIRE_REPOSITORY.value})
        if branch_items:
            # The Asset owner realizes Git; the Work owner decides whether its
            # exact observed branch can become the current engineering scope.
            with self.work.database.unit_of_work() as uow:
                interaction = InteractionStore(uow.session).interaction(interaction_id)
                work_id = None if interaction is None else interaction.current_work_id
                current = None if work_id is None else ProductStore(uow.session).current_work_reality_revision(work_id)
                if current is None:
                    # The UI's provisional PRE-WORK focus is not an admitted
                    # Work scope. Preparatory effects remain Interaction-owned.
                    work_id = None
            if (assessment.candidate_change is not None and current is not None
                    and assessment.basis_work_revision_id == current.id):
                self.work.decide_interaction_work_revision(interaction_id, assessment_id=assessment.id,
                    basis_fingerprint=assessment.basis_fingerprint, expected_previous_revision_id=current.id,
                    action=AttentionAction.APPROVE, authority_identity=request_record.source,
                    rationale=f"Current typed operational intent: semantic-ir:{assessment.semantic_ir.id}")
            if not callable(getattr(self.assets, "execute_interaction_actions", None)):
                # Historical adapter ports still use their qualified acquisition
                # lifecycle; they never interpret the current Human wording.
                self.prepare(interaction_id, assessment, request_record)
                self.execute(interaction_id, assessment, request_record)
                return None
            answer = self.assets.execute_interaction_actions(interaction_id, assessment, request_record, work_id=work_id)
            if any(item.action.operation in {CanonicalOperation.CREATE_BRANCH.value, CanonicalOperation.SWITCH_BRANCH.value,
                    CanonicalOperation.CREATE_AND_SWITCH_BRANCH.value, CanonicalOperation.ACQUIRE_REPOSITORY.value} for item in branch_items):
                observation = self.assets.interaction_observation(interaction_id)
                if work_id is not None and observation is not None:
                    bound = self._bind_and_activate(work_id=work_id, observation=observation,
                        authority_identity=request_record.source,
                        rationale=f"Bind the observed current branch without adding a switch: semantic-ir:{assessment.semantic_ir.id}")
                    if bound.get("condition") != "READY":
                        return "分支已由 Git owner 检查，但当前 Work 尚未完成精确绑定。"
            return answer
        branch_answer = self.execute_explicit_branch_turn(interaction_id, assessment, request_record)
        if branch_answer is not None:
            return branch_answer
        return self.execute_governed_work_turn(interaction_id, assessment, request_record)

    def execute_governed_work_turn(self, interaction_id: UUID,
        assessment: InteractionAssessment, request_record: InteractionRecord) -> str | None:
        """Realize current Work decisions without replaying Action obligations."""
        ir = assessment.semantic_ir
        explicit_goals = () if ir is None else ir.current_production
        if (explicit_goals and assessment.candidate_change is not None
                and assessment.basis_work_revision_id is not None
                and assessment.focus_classification is WorkFocusClassification.ON_TOPIC
                and request_record.id == ir.source_record_id
                and request_record.actor is InteractionActor.HUMAN
                and all(goal.bounded_change and not goal.systemic_design for goal in explicit_goals)
                and not any(item.requires_human for item in current_step_semantic_items(ir))):
            with self.work.database.unit_of_work() as uow:
                product = ProductStore(uow.session)
                focus = InteractionStore(uow.session).interaction(interaction_id)
                current = None if focus is None or focus.current_work_id is None else product.current_work_reality_revision(focus.current_work_id)
                admitted = None if current is None else latest_assessment_revision(
                    current, product.work_reality_revision)
                if admitted is not None and admitted.source_assessment_id == assessment.id:
                    # A preceding Action owner can already admit this same
                    # assessment while binding its exact engineering scope.
                    # The ledger observes that admission; do not schedule twice.
                    return None
            # The current Human Turn is the decision; exact basis, scope and
            # immutable active-cycle checks remain in the existing Work owner.
            updated = self.work.decide_interaction_work_revision(interaction_id,
                assessment_id=assessment.id, basis_fingerprint=assessment.basis_fingerprint,
                expected_previous_revision_id=assessment.basis_work_revision_id,
                action=AttentionAction.APPROVE, authority_identity=request_record.source,
                rationale=f"Explicit current bounded production intent: semantic-ir:{ir.id}")
            self.post_admission.steering_bootstrap.bootstrap(updated.work_id)
            self.post_admission.steering_driver.schedule(updated.work_id)
            return "当前请求已准入 Work，并保留原有范围与交付权限边界。"
        decision_input = any(meaning.kind is InterpretationMeaningKind.DECISION_INPUT
            and request_record.id in meaning.source_record_ids for meaning in assessment.meanings)
        typed_scope_answer = bool(assessment.candidate_change is not None
            and assessment.semantic_ir
            and assessment.semantic_ir.items
            and all(item.kind in {SemanticKind.CONSTRAINT, SemanticKind.FACT}
                for item in assessment.semantic_ir.items)
            and any(item.kind is SemanticKind.CONSTRAINT and any(
                source.source_record_id == request_record.id for source in item.provenance)
                for item in assessment.semantic_ir.items)
            and (any(fact.relation is SemanticRelation.SCOPE
                and request_record.id in fact.provenance.source_record_ids
                for fact in current_semantic_facts(assessment.engineering_semantic_facts))
                or assessment.semantic_ir.work_question_step_id is not None)
            and "constraints" in assessment.candidate_change.changed_fields)
        if (request_record.actor is not InteractionActor.HUMAN
            or assessment.candidate_change is None
            or assessment.basis_work_revision_id is None
            or assessment.focus_classification is not WorkFocusClassification.ON_TOPIC
            or assessment.semantic_ir is None or assessment.semantic_ir.source_record_id != request_record.id
            or not (decision_input or typed_scope_answer)):
            return None
        with self.work.database.unit_of_work() as uow:
            interaction = InteractionStore(uow.session).interaction(interaction_id)
            if interaction is None or interaction.current_work_id is None:
                return None
            work_id = interaction.current_work_id
            current = ProductStore(uow.session).current_work_reality_revision(work_id)
            steering = SteeringStore(uow.session)
            plan = steering.plan_for_work(work_id)
            revision = None if plan is None else steering.active_revision(plan.id)
            decision = None if revision is None else steering.latest_decision(revision.id)
            step = next((item for item in steering.steps(revision.id)
                if item.state.value == "CURRENT"), None) if revision else None
            if (current is None or current.id != assessment.basis_work_revision_id
                or decision is None or not decision.human_required or step is None
                or decision.current_step_id != step.id
                or step.type not in {SteeringStepType.DESIGN, SteeringStepType.REFINE}
                or decision.attention_reason is not SteeringAttentionReason.MAJOR_PRODUCT_OR_ARCHITECTURE_DECISION):
                return None
            if (assessment.semantic_ir.work_question_step_id is not None
                    and assessment.semantic_ir.work_question_step_id != step.id):
                return None
        self.work.decide_interaction_work_revision(interaction_id,
            assessment_id=assessment.id, basis_fingerprint=assessment.basis_fingerprint,
            expected_previous_revision_id=assessment.basis_work_revision_id,
            action=AttentionAction.APPROVE, authority_identity=request_record.source,
            rationale=f"Human answered the current governed question: steering-decision:{decision.id}")
        self.post_admission.steering_driver.schedule(work_id)
        return "你的选择已写入当前 Work，Watt 将按这项决定继续推进。"

    def execute_explicit_branch_turn(
        self,
        interaction_id: UUID,
        assessment: InteractionAssessment,
        request_record: InteractionRecord,
    ) -> str | None:
        """Admit and execute a branch-only Work change from its Human command."""

        if assessment.candidate_change is None or assessment.basis_work_revision_id is None:
            return None
        with self.work.database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            interactions = InteractionStore(uow.session)
            focused = interactions.interaction(interaction_id)
            work_id = None if focused is None else focused.current_work_id
            revision = (
                None if work_id is None
                else product.current_work_reality_revision(work_id)
            )
            target = governed_branch_creation_target(
                assessment.engineering_semantic_facts,
                record_for_id=interactions.record,
            )
            if revision is None or target is None:
                return None
            admitted_revision = latest_assessment_revision(revision,product.work_reality_revision)
            resumed = admitted_revision is not None and admitted_revision.source_assessment_id == assessment.id
            prior_ids = {fact.id for fact in revision.engineering_semantic_facts}
            branch_facts = tuple(
                fact for fact in assessment.engineering_semantic_facts
                if fact.id not in prior_ids
                and fact.subject in BRANCH_FACT_SUBJECTS
                and fact.value == target
                and request_record.id in fact.provenance.source_record_ids
            )
            if (
                not resumed and (assessment.basis_work_revision_id != revision.id
                or revision.repository_ref == f"refs/heads/{target}"
                or len(branch_facts) != 1)
            ):
                return None
        if not resumed:
            self.work.decide_interaction_work_revision(
                interaction_id,
                assessment_id=assessment.id,
                basis_fingerprint=assessment.basis_fingerprint,
                expected_previous_revision_id=assessment.basis_work_revision_id,
                action=AttentionAction.APPROVE,
                authority_identity=request_record.source,
                rationale="The Human explicitly requested creation of this exact branch.",
                branch_only=True,
            )
        self.post_admission.steering_bootstrap.bootstrap(work_id)
        observation = self.reconcile_governed_branch(
            work_id,
            interaction_id=interaction_id,
            authority_identity=request_record.source,
        )
        self.post_admission.steering_driver.schedule(work_id)
        if observation is not None and observation.get("condition") == "READY":
            return (
                f"已从当前仓库基线创建并绑定本地分支 {target}。"
                "后续开发会在该分支上进行；这不表示分支已推送到远端。"
            )
        condition = "未知" if observation is None else observation.get("condition", "未知")
        return (
            f"已记录创建本地分支 {target} 的请求，但操作尚未成功"
            f"（{condition}）。当前 Work 的分支未切换。"
        )

    def governed_branch_work_ids(self) -> tuple[UUID, ...]:
        """Identify persisted branch obligations for Steering restart recovery."""

        pending: list[UUID] = []
        for interaction in self.interactions.list_interactions():
            work_id = interaction.governed_work_id
            if work_id is None:
                continue
            with self.work.database.unit_of_work() as uow:
                revision = ProductStore(uow.session).current_work_reality_revision(work_id)
                target = (
                    None if revision is None else governed_branch_creation_target(
                        revision.engineering_semantic_facts,
                        record_for_id=InteractionStore(uow.session).record,
                    )
                )
            if revision is None:
                continue
            if target and revision.repository_ref != f"refs/heads/{target}":
                pending.append(work_id)
        return tuple(dict.fromkeys(pending))

    def prepare(
        self,
        interaction_id: UUID,
        assessment: InteractionAssessment,
        request_record: InteractionRecord,
    ) -> None:
        """Persist Work and operation Reality before Human-facing action claims."""

        from spg.application.intent_realization import production_evidence, executable_semantic_actions
        evidence = production_evidence(assessment.semantic_ir)
        projection = self.interactions.get_shared_understanding(interaction_id)
        if projection.governed_work_id is not None:
            latest = self.assets.latest_attempt_for_work(projection.governed_work_id)
            recovery_requested = any(item.action.operation == "ACQUIRE_REPOSITORY"
                for item in executable_semantic_actions(assessment.semantic_ir))
            if not recovery_requested:
                return
            if latest is not None and self._repository_state(latest) not in {
                RepositoryAcquisitionState.WAITING_FOR_AUTHORIZATION,
                RepositoryAcquisitionState.FAILED_RETRYABLE,
                RepositoryAcquisitionState.FAILED_TERMINAL,
            }:
                return
            # A Work admitted by an older runtime may predate repository-attempt
            # persistence. Recover the source from durable Interaction / Semantic
            # Reality instead of requiring the Human to repeat the URL or creating
            # a duplicate Work.
            source = (
                latest.get("source")
                if latest is not None
                else (
                    projection.repository_source
                )
            )
            if not source:
                return
            if latest is not None and latest.get("operation_kind") == "CREATE_BRANCH":
                started = self._start_branch_attempt(
                    interaction_id=interaction_id,
                    work_id=projection.governed_work_id,
                    source=source,
                    base_resource_id=UUID(latest["base_resource_id"]),
                    target_branch=latest["target_branch"],
                    authority_identity=request_record.source,
                )
            else:
                started = self._start_attempt(
                    interaction_id=interaction_id,
                    work_id=projection.governed_work_id,
                    source=source,
                    title=projection.interpreted_motive or "Repository production Work",
                    description=(
                        projection.desired_outcome
                        or "Retry repository Reality acquisition for the governed Work."
                    ),
                    authority_identity=request_record.source,
                )
            self.interactions.record_production_admission_progress(
                interaction_id,
                admission_state=ProductionAdmissionExecutionState.WORK_CREATED,
                repository_state=self._repository_state(started),
                next_step=self._next_step(started),
            )
            return
        if (
            not evidence.production_request
            or not evidence.repository_relevant
            or not evidence.action_requested
            or assessment.readiness.status is not WorkAdmissionReadinessStatus.READY
            or projection.latest_assessment is None
            or not projection.latest_assessment_current
            or projection.latest_assessment.id != assessment.id
            or projection.latest_assessment.basis_fingerprint
            != assessment.basis_fingerprint
        ):
            self.interactions.clear_production_admission_progress(interaction_id)
            return
        admitted = self.work.admit_interaction_work(
            interaction_id,
            engineering_resource_id=None,
            use_default_resource=False,
            assessment_id=assessment.id,
            basis_fingerprint=assessment.basis_fingerprint,
            authority_identity=request_record.source,
            rationale=(
                "The Human explicitly requested repository acquisition and software "
                "production. That request authorizes Work formation and read-only "
                "baseline acquisition; private access, delivery, and final acceptance "
                "remain separately governed."
            ),
        )
        if evidence.repository_source is None and not any(
                goal.repository_reference or goal.repository_required for goal in assessment.semantic_ir.current_production):
            self.assets.ensure_managed_execution_workspace(self.work, admitted.work_id)
            self.post_admission.activate(admitted.work_id)
            self.interactions.record_production_admission_progress(interaction_id,
                admission_state=ProductionAdmissionExecutionState.WORK_CREATED,
                repository_state=RepositoryAcquisitionState.READY,
                next_step="Continue Steering in the admitted managed workspace.")
            return
        if evidence.repository_source is None:
            request = RepositoryIntakeRequest(
                request_id=uuid5(
                    NAMESPACE_URL,
                    f"watt:repository-acquisition:{admitted.work_id}:1:source-pending",
                ),
                source=None,
                title=(projection.interpreted_motive or "Repository production Work")[:200],
                description=(
                    projection.desired_outcome
                    or "Wait for the referenced repository source before acquisition."
                )[:4000],
                authority_identity=request_record.source,
                interaction_id=interaction_id,
                work_id=admitted.work_id,
                attempt_number=1,
            )
            if hasattr(self.assets, "record_waiting_source"):
                self.assets.record_waiting_source(request)
            self.interactions.record_production_admission_progress(
                interaction_id,
                admission_state=ProductionAdmissionExecutionState.WORK_CREATED,
                repository_state=RepositoryAcquisitionState.WAITING_FOR_REPOSITORY_SOURCE,
                next_step="Bind the referenced repository source before Steering begins.",
            )
            return
        started = self._start_attempt(
            interaction_id=interaction_id,
            work_id=admitted.work_id,
            source=evidence.repository_source,
            title=projection.interpreted_motive or "Repository production Work",
            description=(
                projection.desired_outcome
                or "Acquire repository Reality for the requested production Work."
            ),
            authority_identity=request_record.source,
        )
        self.interactions.record_production_admission_progress(
            interaction_id,
            admission_state=ProductionAdmissionExecutionState.WORK_CREATED,
            repository_state=self._repository_state(started),
            next_step=self._next_step(started),
        )

    def _execute_acquisition_attempt(self, attempt_id: UUID) -> dict:
        try:
            return self.assets.execute_intake(attempt_id)
        except Exception as error:
            return self.assets.mark_attempt_failure(
                attempt_id,
                category=RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE,
                human_message="Repository acquisition could not be completed and can be retried.",
                technical_evidence={
                    "phase": "REPOSITORY_ACQUISITION",
                    "error_type": type(error).__name__,
                    "message": str(error)[:2000],
                },
                retryable=True,
            )

    def execute(
        self,
        interaction_id: UUID,
        assessment: InteractionAssessment,
        request_record: InteractionRecord,
    ) -> dict | None:
        """Complete the persisted Attempt and activate only bound Reality."""

        projection = self.interactions.get_shared_understanding(interaction_id)
        work_id = projection.governed_work_id
        if work_id is None:
            self.prepare(interaction_id, assessment, request_record)
            projection = self.interactions.get_shared_understanding(interaction_id)
            work_id = projection.governed_work_id
        if work_id is None:
            return None
        latest = self.assets.latest_attempt_for_work(work_id)
        if latest is None or latest.get("condition") not in {
            "REQUESTED",
            "RUNNING",
            "FAILED_RETRYABLE",
        }:
            return latest
        started_at = monotonic()
        observation = (latest if latest.get("condition") == "FAILED_RETRYABLE"
            else self._execute_acquisition_attempt(UUID(latest["intake_request_id"])))
        attempted_retry = False
        while (
            observation.get("condition") == "FAILED_RETRYABLE"
            and observation.get("failure_category")
            == RepositoryAcquisitionFailureCategory.NETWORK_FAILURE.value
            and latest.get("operation_kind") != "CREATE_BRANCH"
            and latest.get("source")
            and sum(item.get("source") == latest["source"]
                for item in self.assets.attempts_for_work(work_id)) < 3
            and monotonic() - started_at < 120
        ):
            # Persisted lineage survives process restart. Permanent access and
            # not-found failures do not enter this bounded network-only loop.
            count = sum(item.get("source") == latest["source"]
                for item in self.assets.attempts_for_work(work_id))
            sleep(min(2 ** max(0, count - 1), 4))
            attempted_retry = True
            retry = self._start_attempt(
                interaction_id=interaction_id,
                work_id=work_id,
                source=latest["source"],
                title=projection.interpreted_motive or "Repository production Work",
                description=(
                    projection.desired_outcome
                    or "Retry the public repository baseline acquisition."
                ),
                authority_identity=request_record.source,
            )
            observation = self._execute_acquisition_attempt(
                UUID(retry["intake_request_id"])
            )
        if attempted_retry:
            history = self.assets.attempts_for_work(work_id)
            with self.work.database.unit_of_work() as uow:
                NativeExecutionStore(uow.session).record_bounded_refinement(
                    work_id=work_id, operation_id=UUID(latest["intake_request_id"]),
                    component="repository/acquisition", signal_kind=RefinementSignalKind.REALITY_MISMATCH,
                    signature_basis="ACQUISITION_RETRYABLE_NO_AUTOMATIC_RETRY:NETWORK_FAILURE",
                    evidence_references=tuple(f"repository-intake:{item['intake_request_id']}"
                        for item in history), converged=observation.get("condition") == "READY",
                    attempt_count=max(2, len(history)), elapsed_seconds=int(monotonic() - started_at),
                    diagnostic_evidence={"signal": "TRANSIENT_INFRASTRUCTURE_FAILURE",
                        "attempt_budget": 3, "time_budget_seconds": 120,
                        "final_condition": observation.get("condition"),
                        "failure_category": observation.get("failure_category")})
                uow.commit()
        observation = self._bind_and_activate(
            work_id=work_id,
            observation=observation,
            authority_identity=request_record.source,
            rationale=(
                "Bind the exact repository Reality acquired from the Human-supplied "
                "source before Steering begins."
            ),
        )
        self.interactions.record_production_admission_progress(
            interaction_id,
            admission_state=ProductionAdmissionExecutionState.WORK_CREATED,
            repository_state=self._repository_state(observation),
            next_step=self._next_step(observation),
        )
        return observation

    def retry_work(self, work_id: UUID, *, authority_identity: str) -> dict:
        latest = self.assets.latest_attempt_for_work(work_id)
        if latest is None or not latest.get("source"):
            raise ValueError("This Work has no repository acquisition to retry")
        if self._repository_state(latest) not in {
            RepositoryAcquisitionState.WAITING_FOR_AUTHORIZATION,
            RepositoryAcquisitionState.FAILED_RETRYABLE,
            RepositoryAcquisitionState.FAILED_TERMINAL,
        }:
            return latest
        interaction_id = UUID(latest["interaction_id"])
        work_projection = self.work.get_work(work_id)
        if latest.get("operation_kind") == "CREATE_BRANCH":
            started = self._start_branch_attempt(
                interaction_id=interaction_id,
                work_id=work_id,
                source=latest["source"],
                base_resource_id=UUID(latest["base_resource_id"]),
                target_branch=latest["target_branch"],
                authority_identity=authority_identity,
            )
        else:
            started = self._start_attempt(
                interaction_id=interaction_id,
                work_id=work_id,
                source=latest["source"],
                title=work_projection.title or "Repository production Work",
                description=(
                    work_projection.desired_outcome
                    or "Retry repository Reality acquisition for the governed Work."
                ),
                authority_identity=authority_identity,
            )
        observation = self.assets.execute_intake(UUID(started["intake_request_id"]))
        return self._bind_and_activate(
            work_id=work_id,
            observation=observation,
            authority_identity=authority_identity,
            rationale="Bind repository Reality after an explicit Human retry.",
        )
