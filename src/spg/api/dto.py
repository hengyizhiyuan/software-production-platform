"""Explicit product HTTP DTOs; no persistence or Runtime rows cross this boundary."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from spg.domain.change import CodeChangeContract, CodeVerificationObligation
from spg.domain.guided_design import GuidedDesignProjection
from spg.domain.interaction import InteractionTurn, SharedUnderstanding, WorkTransitionChoice
from spg.domain.product import (
    AttentionAction,
    AttentionItem,
    AttentionKind,
    EngineeringScopeRecord,
    GoalProjection,
    GoalRecord,
    WorkProjection,
    WorkMode,
    WorkResultProjection,
    WorkStatus,
)
from spg.domain.planning import ProductionPlanProposal
from spg.domain.refinement import RepositoryChangeProposal
from spg.domain.runtime_activation import RuntimeActivationProjection
from spg.domain.native_execution import ControlAction, ExecutionQueueEntryRecord
from spg.domain.steering import (
    RealityReference,
    SteeringAttentionReason,
    SteeringDecisionRecord,
    SteeringPlanProjection,
    SteeringStepRecord,
)


class ApiDto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkingAgreementCreateRequest(ApiDto):
    content: str = Field(min_length=3, max_length=500)
    agreement_type: str
    actor_identity: str = Field(default="human:local-operator", min_length=1, max_length=255)


class WorkingAgreementAbandonRequest(ApiDto):
    actor_identity: str = Field(default="human:local-operator", min_length=1, max_length=255)


class GoalCreateRequest(ApiDto):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None


class InteractionCreateRequest(ApiDto):
    human_identity: str = Field(default="human:local-operator", min_length=1, max_length=255)


class InteractionMessageRequest(ApiDto):
    content: str = Field(min_length=1)
    human_identity: str = Field(default="human:local-operator", min_length=1, max_length=255)
    supporting_references: tuple[str, ...] = ()


class InteractionWorkAdmissionRequest(ApiDto):
    engineering_resource_id: UUID | None = None
    assessment_id: UUID
    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_identity: str = Field(
        default="human:local-operator", min_length=1, max_length=255
    )
    rationale: str | None = None


class InteractionWorkRevisionDecisionRequest(ApiDto):
    assessment_id: UUID
    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_previous_revision_id: UUID
    action: AttentionAction
    authority_identity: str = Field(
        default="human:local-operator", min_length=1, max_length=255
    )
    rationale: str | None = None


class InteractionWorkTransitionDecisionRequest(ApiDto):
    transition_id: UUID
    expected_originating_work_id: UUID
    choice: WorkTransitionChoice
    authority_identity: str = Field(
        default="human:local-operator", min_length=1, max_length=255
    )
    rationale: str | None = None


class InteractionRecordResponse(ApiDto):
    record_id: UUID
    sequence: int
    actor: str
    source: str
    content: str
    work_focus_id: UUID | None
    supporting_references: tuple[str, ...]
    created_at: datetime


class ConversationMessageResponse(ApiDto):
    message_id: UUID
    turn_id: UUID | None
    sequence: int
    actor: str
    content: str
    processing_status: str
    interaction_record_id: UUID | None
    interpretation_assessment_id: UUID | None
    design_result_references: tuple[str, ...]
    governance_event_references: tuple[str, ...]
    supporting_references: tuple[str, ...]
    created_at: datetime
    updated_at: datetime


class InteractionTurnResponse(ApiDto):
    turn_id: UUID
    interaction_id: UUID
    request_record_id: UUID
    assessment_id: UUID | None
    wic_mode: str
    status: str
    failure_code: str | None
    failure_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime

    @classmethod
    def from_turn(cls, turn: InteractionTurn) -> Self:
        return cls(
            turn_id=turn.id,
            interaction_id=turn.interaction_id,
            request_record_id=turn.request_record_id,
            assessment_id=turn.assessment_id,
            wic_mode=turn.wic_mode.value,
            status=turn.status.value,
            failure_code=turn.failure_code,
            failure_message=turn.failure_message,
            created_at=turn.created_at,
            started_at=turn.started_at,
            completed_at=turn.completed_at,
            updated_at=turn.updated_at,
        )


class InteractionMeaningResponse(ApiDto):
    kind: str
    statement: str
    source_record_ids: tuple[UUID, ...]
    confidence: float
    rationale: str
    clarification_required: bool


class InteractionReadinessResponse(ApiDto):
    status: str
    profile: str
    profile_version: str
    satisfied_requirements: tuple[str, ...]
    missing_information: tuple[str, ...]
    unresolved_material_questions: tuple[str, ...]
    reasons: tuple[str, ...]
    basis_fingerprint: str


class DesignIntentFrameResponse(ApiDto):
    design_subject: str
    object_type: str
    business_context: str | None
    desired_outcome: str | None
    scope_level: str
    collaboration_mode: str
    candidate_assumptions: tuple[str, ...]
    ambiguities: tuple[str, ...]
    confidence: float


class InteractionAssessmentResponse(ApiDto):
    assessment_id: UUID
    basis_fingerprint: str
    basis_last_sequence: int
    interpreted_motive: str | None
    desired_outcome: str | None
    design_intent_frame: DesignIntentFrameResponse | None
    candidate_context: tuple[str, ...]
    candidate_constraints: tuple[str, ...]
    current_requests: tuple[str, ...]
    unresolved_material_questions: tuple[str, ...]
    meanings: tuple[InteractionMeaningResponse, ...]
    focus_classification: str | None
    impact_disposition: str | None
    candidate_change: dict[str, object] | None
    basis_work_revision_id: UUID | None
    basis_steering_plan_revision_id: UUID | None
    basis_steering_step_id: UUID | None
    basis_active_runtime_binding_id: UUID | None
    supporting_references: tuple[str, ...]
    natural_response: str
    readiness: InteractionReadinessResponse
    progressive_semantics: dict[str, object] | None
    provider_identity: str
    model_identity: str | None
    schema_version: str
    created_at: datetime


class WorkRealityRevisionResponse(ApiDto):
    revision_id: UUID
    work_id: UUID
    revision_number: int
    previous_revision_id: UUID | None
    basis_fingerprint: str
    revision_fingerprint: str
    source_interaction_id: UUID
    source_kind: str = "INTERACTION_ASSESSMENT"
    source_assessment_id: UUID | None
    source_record_ids: tuple[UUID, ...]
    motive: str
    desired_outcome: str
    context_facts: tuple[str, ...]
    constraints: tuple[str, ...]
    requests: tuple[str, ...]
    engineering_scope_id: UUID
    engineering_resource_id: UUID | None
    scope_basis_fingerprint: str
    repository_identity: str | None
    repository_ref: str | None
    source_baseline_id: UUID | None
    source_revision: str | None
    governance_record_id: UUID
    supporting_references: tuple[str, ...]
    change_set: tuple[str, ...]
    rationale: str
    admitted_by: str
    schema_version: str
    created_at: datetime


class InteractionWorkTransitionResponse(ApiDto):
    transition_id: UUID
    source_record_id: UUID
    source_assessment_id: UUID
    originating_work_id: UUID
    target_work_id: UUID | None
    reason: str
    focus_classification: str
    impact_disposition: str
    choice: str
    decided_by: str | None
    decision_rationale: str | None
    decided_at: datetime | None
    created_at: datetime


class SharedUnderstandingResponse(ApiDto):
    interaction_id: UUID
    condition: str
    current_work_id: UUID | None
    created_at: datetime
    updated_at: datetime
    records: tuple[InteractionRecordResponse, ...]
    conversation_messages: tuple[ConversationMessageResponse, ...]
    turns: tuple[InteractionTurnResponse, ...]
    human_said: tuple[str, ...]
    latest_assessment: InteractionAssessmentResponse | None
    latest_assessment_current: bool
    interpreted_motive: str | None
    desired_outcome: str | None
    design_intent_frame: DesignIntentFrameResponse | None
    candidate_context: tuple[str, ...]
    candidate_constraints: tuple[str, ...]
    current_requests: tuple[str, ...]
    unresolved_material_questions: tuple[str, ...]
    readiness: InteractionReadinessResponse | None
    candidate_engineering_resource_id: UUID | None
    candidate_repository_identity: str | None
    candidate_repository_ref: str | None
    candidate_scope_summary: str | None
    governed_work_id: UUID | None
    governed_revision: WorkRealityRevisionResponse | None
    current_work_focus: str | None
    focus_classification: str | None
    impact_disposition: str | None
    candidate_change: dict[str, object] | None
    work_revision_admission_status: str
    active_cycle_work_revision_id: UUID | None
    active_cycle_impact_disposition: str | None
    work_satisfaction_state: str
    interaction_relationship_state: str
    work_focus_history: tuple[UUID, ...]
    latest_work_transition: InteractionWorkTransitionResponse | None
    new_work_formation_pending: bool
    selected_design_schema_identity: str | None
    selected_design_schema_version: str | None
    design_schema_selection_rationale: str | None
    design_stage: str | None
    design_next_focus: str | None
    design_focus_rationale: str | None
    design_facilitation_strategy: str | None
    design_progress_narrative: str | None

    @classmethod
    def from_projection(cls, projection: SharedUnderstanding) -> Self:
        assessment = projection.latest_assessment
        readiness = projection.readiness
        return cls(
            interaction_id=projection.interaction.id,
            condition=projection.interaction.condition.value,
            current_work_id=projection.interaction.current_work_id,
            created_at=projection.interaction.created_at,
            updated_at=projection.interaction.updated_at,
            records=tuple(
                InteractionRecordResponse(
                    record_id=item.id,
                    sequence=item.sequence,
                    actor=item.actor.value,
                    source=item.source,
                    content=item.content,
                    work_focus_id=item.work_focus_id,
                    supporting_references=item.supporting_references,
                    created_at=item.created_at,
                )
                for item in projection.records
            ),
            conversation_messages=tuple(
                ConversationMessageResponse(
                    message_id=item.id,
                    turn_id=item.turn_id,
                    sequence=item.sequence,
                    actor=item.actor.value,
                    content=item.content,
                    processing_status=item.processing_status.value,
                    interaction_record_id=item.interaction_record_id,
                    interpretation_assessment_id=item.interpretation_assessment_id,
                    design_result_references=item.design_result_references,
                    governance_event_references=item.governance_event_references,
                    supporting_references=item.supporting_references,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
                for item in projection.conversation_messages
            ),
            turns=tuple(
                InteractionTurnResponse.from_turn(item) for item in projection.turns
            ),
            human_said=projection.human_said,
            latest_assessment=(
                None
                if assessment is None
                else InteractionAssessmentResponse(
                    assessment_id=assessment.id,
                    basis_fingerprint=assessment.basis_fingerprint,
                    basis_last_sequence=assessment.basis_last_sequence,
                    interpreted_motive=assessment.interpreted_motive,
                    desired_outcome=assessment.desired_outcome,
                    design_intent_frame=(
                        None
                        if assessment.design_intent_frame is None
                        else DesignIntentFrameResponse(
                            design_subject=assessment.design_intent_frame.design_subject,
                            object_type=assessment.design_intent_frame.object_type.value,
                            business_context=assessment.design_intent_frame.business_context,
                            desired_outcome=assessment.design_intent_frame.desired_outcome,
                            scope_level=assessment.design_intent_frame.scope_level.value,
                            collaboration_mode=(
                                assessment.design_intent_frame.collaboration_mode.value
                            ),
                            candidate_assumptions=(
                                assessment.design_intent_frame.candidate_assumptions
                            ),
                            ambiguities=assessment.design_intent_frame.ambiguities,
                            confidence=assessment.design_intent_frame.confidence,
                        )
                    ),
                    candidate_context=assessment.candidate_context,
                    candidate_constraints=assessment.candidate_constraints,
                    current_requests=assessment.current_requests,
                    unresolved_material_questions=assessment.unresolved_material_questions,
                    meanings=tuple(
                        InteractionMeaningResponse(
                            kind=item.kind.value,
                            statement=item.statement,
                            source_record_ids=item.source_record_ids,
                            confidence=item.confidence,
                            rationale=item.rationale,
                            clarification_required=item.clarification_required,
                        )
                        for item in assessment.meanings
                    ),
                    focus_classification=(
                        None
                        if assessment.focus_classification is None
                        else assessment.focus_classification.value
                    ),
                    impact_disposition=(
                        None
                        if assessment.impact_disposition is None
                        else assessment.impact_disposition.value
                    ),
                    candidate_change=(
                        None
                        if assessment.candidate_change is None
                        else assessment.candidate_change.model_dump(mode="json")
                    ),
                    basis_work_revision_id=assessment.basis_work_revision_id,
                    basis_steering_plan_revision_id=(
                        assessment.basis_steering_plan_revision_id
                    ),
                    basis_steering_step_id=assessment.basis_steering_step_id,
                    basis_active_runtime_binding_id=(
                        assessment.basis_active_runtime_binding_id
                    ),
                    supporting_references=assessment.supporting_references,
                    natural_response=assessment.natural_response,
                    readiness=InteractionReadinessResponse(
                        status=assessment.readiness.status.value,
                        profile=assessment.readiness.profile,
                        profile_version=assessment.readiness.profile_version,
                        satisfied_requirements=assessment.readiness.satisfied_requirements,
                        missing_information=assessment.readiness.missing_information,
                        unresolved_material_questions=assessment.readiness.unresolved_material_questions,
                        reasons=assessment.readiness.reasons,
                        basis_fingerprint=assessment.readiness.basis_fingerprint,
                    ),
                    progressive_semantics=(
                        None
                        if assessment.progressive_semantics is None
                        else assessment.progressive_semantics.model_dump(mode="json")
                    ),
                    provider_identity=assessment.provider_identity,
                    model_identity=assessment.model_identity,
                    schema_version=assessment.schema_version,
                    created_at=assessment.created_at,
                )
            ),
            latest_assessment_current=projection.latest_assessment_current,
            interpreted_motive=projection.interpreted_motive,
            desired_outcome=projection.desired_outcome,
            design_intent_frame=(
                None
                if projection.design_intent_frame is None
                else DesignIntentFrameResponse(
                    design_subject=projection.design_intent_frame.design_subject,
                    object_type=projection.design_intent_frame.object_type.value,
                    business_context=projection.design_intent_frame.business_context,
                    desired_outcome=projection.design_intent_frame.desired_outcome,
                    scope_level=projection.design_intent_frame.scope_level.value,
                    collaboration_mode=(
                        projection.design_intent_frame.collaboration_mode.value
                    ),
                    candidate_assumptions=(
                        projection.design_intent_frame.candidate_assumptions
                    ),
                    ambiguities=projection.design_intent_frame.ambiguities,
                    confidence=projection.design_intent_frame.confidence,
                )
            ),
            candidate_context=projection.candidate_context,
            candidate_constraints=projection.candidate_constraints,
            current_requests=projection.current_requests,
            unresolved_material_questions=projection.unresolved_material_questions,
            readiness=(
                None
                if readiness is None
                else InteractionReadinessResponse(
                    status=readiness.status.value,
                    profile=readiness.profile,
                    profile_version=readiness.profile_version,
                    satisfied_requirements=readiness.satisfied_requirements,
                    missing_information=readiness.missing_information,
                    unresolved_material_questions=readiness.unresolved_material_questions,
                    reasons=readiness.reasons,
                    basis_fingerprint=readiness.basis_fingerprint,
                )
            ),
            candidate_engineering_resource_id=(
                projection.candidate_engineering_resource_id
            ),
            candidate_repository_identity=projection.candidate_repository_identity,
            candidate_repository_ref=projection.candidate_repository_ref,
            candidate_scope_summary=projection.candidate_scope_summary,
            governed_work_id=projection.governed_work_id,
            governed_revision=(
                None
                if projection.governed_revision is None
                else WorkRealityRevisionResponse(
                    revision_id=projection.governed_revision.id,
                    work_id=projection.governed_revision.work_id,
                    revision_number=projection.governed_revision.revision_number,
                    previous_revision_id=projection.governed_revision.previous_revision_id,
                    basis_fingerprint=projection.governed_revision.basis_fingerprint,
                    revision_fingerprint=projection.governed_revision.revision_fingerprint,
                    source_interaction_id=projection.governed_revision.source_interaction_id,
                    source_kind=projection.governed_revision.source_kind,
                    source_assessment_id=projection.governed_revision.source_assessment_id,
                    source_record_ids=projection.governed_revision.source_record_ids,
                    motive=projection.governed_revision.motive,
                    desired_outcome=projection.governed_revision.desired_outcome,
                    context_facts=projection.governed_revision.context_facts,
                    constraints=projection.governed_revision.constraints,
                    requests=projection.governed_revision.requests,
                    engineering_scope_id=projection.governed_revision.engineering_scope_id,
                    engineering_resource_id=projection.governed_revision.engineering_resource_id,
                    scope_basis_fingerprint=projection.governed_revision.scope_basis_fingerprint,
                    repository_identity=projection.governed_revision.repository_identity,
                    repository_ref=projection.governed_revision.repository_ref,
                    source_baseline_id=projection.governed_revision.source_baseline_id,
                    source_revision=projection.governed_revision.source_revision,
                    governance_record_id=projection.governed_revision.governance_record_id,
                    supporting_references=projection.governed_revision.supporting_references,
                    change_set=projection.governed_revision.change_set,
                    rationale=projection.governed_revision.rationale,
                    admitted_by=projection.governed_revision.admitted_by,
                    schema_version=projection.governed_revision.schema_version,
                    created_at=projection.governed_revision.created_at,
                )
            ),
            current_work_focus=projection.current_work_focus,
            focus_classification=(
                None
                if projection.focus_classification is None
                else projection.focus_classification.value
            ),
            impact_disposition=(
                None
                if projection.impact_disposition is None
                else projection.impact_disposition.value
            ),
            candidate_change=(
                None
                if projection.candidate_change is None
                else projection.candidate_change.model_dump(mode="json")
            ),
            work_revision_admission_status=(
                projection.work_revision_admission_status.value
            ),
            active_cycle_work_revision_id=projection.active_cycle_work_revision_id,
            active_cycle_impact_disposition=(
                None
                if projection.active_cycle_impact_disposition is None
                else projection.active_cycle_impact_disposition.value
            ),
            work_satisfaction_state=projection.work_satisfaction_state.value,
            interaction_relationship_state=(
                projection.interaction_relationship_state.value
            ),
            work_focus_history=projection.work_focus_history,
            latest_work_transition=(
                None
                if projection.latest_work_transition is None
                else InteractionWorkTransitionResponse(
                    transition_id=projection.latest_work_transition.id,
                    source_record_id=(
                        projection.latest_work_transition.source_record_id
                    ),
                    source_assessment_id=(
                        projection.latest_work_transition.source_assessment_id
                    ),
                    originating_work_id=(
                        projection.latest_work_transition.originating_work_id
                    ),
                    target_work_id=projection.latest_work_transition.target_work_id,
                    reason=projection.latest_work_transition.reason,
                    focus_classification=(
                        projection.latest_work_transition.focus_classification.value
                    ),
                    impact_disposition=(
                        projection.latest_work_transition.impact_disposition.value
                    ),
                    choice=projection.latest_work_transition.choice.value,
                    decided_by=projection.latest_work_transition.decided_by,
                    decision_rationale=(
                        projection.latest_work_transition.decision_rationale
                    ),
                    decided_at=projection.latest_work_transition.decided_at,
                    created_at=projection.latest_work_transition.created_at,
                )
            ),
            new_work_formation_pending=projection.new_work_formation_pending,
            selected_design_schema_identity=(
                projection.selected_design_schema_identity
            ),
            selected_design_schema_version=(
                projection.selected_design_schema_version
            ),
            design_schema_selection_rationale=(
                projection.design_schema_selection_rationale
            ),
            design_stage=projection.design_stage,
            design_next_focus=projection.design_next_focus,
            design_focus_rationale=projection.design_focus_rationale,
            design_facilitation_strategy=projection.design_facilitation_strategy,
            design_progress_narrative=projection.design_progress_narrative,
        )


class GoalResponse(ApiDto):
    goal_id: UUID
    title: str
    description: str | None
    condition: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, goal: GoalRecord) -> Self:
        return cls(
            goal_id=goal.id,
            title=goal.title,
            description=goal.description,
            condition=goal.condition.value,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        )


class ResourceBindingResponse(ApiDto):
    resource_id: UUID
    condition: str


class EngineeringScopeResponse(ApiDto):
    engineering_scope_id: UUID
    summary: str
    condition: str
    resources: tuple[ResourceBindingResponse, ...]

    @classmethod
    def from_record(cls, scope: EngineeringScopeRecord) -> Self:
        return cls(
            engineering_scope_id=scope.id,
            summary=scope.summary,
            condition=scope.condition.value,
            resources=tuple(
                ResourceBindingResponse(
                    resource_id=binding.resource_id,
                    condition=binding.condition.value,
                )
                for binding in scope.bindings
            ),
        )


class ArtifactTargetResponse(ApiDto):
    path: str
    operation: str
    placement_rationale: str
    confidence: str
    source_baseline_id: UUID
    source_revision: str


class ProductionPlanStepResponse(ApiDto):
    position: int
    instruction: str


class CodeChangeTargetResponse(ApiDto):
    path: str
    operation: str


class ChangeProposalTargetResponse(ApiDto):
    path: str
    operation: str
    disposition: str
    rationale: str
    evidence: str
    confidence: str


class ChangeProposalProvenanceResponse(ApiDto):
    provider_identity: str
    provider_version: str
    inspection_method: str


class CodeVerificationResponse(ApiDto):
    kind: str
    target: str | None
    identity: str


class CodeChangeContractResponse(ApiDto):
    target_kind: str
    target_shape: str
    engineering_resource_id: UUID
    repository_identity: str
    source_baseline_id: UUID
    source_revision: str
    desired_outcome: str
    constraints: tuple[str, ...]
    exact_targets: tuple[CodeChangeTargetResponse, ...]
    allowed_areas: tuple[str, ...]
    forbidden_areas: tuple[str, ...]
    verification_obligations: tuple[CodeVerificationResponse, ...]
    source_proposal_id: UUID | None
    source_proposal_fingerprint: str | None

    @classmethod
    def from_contract(cls, contract: CodeChangeContract) -> Self:
        return cls(
            target_kind=contract.target_kind.value,
            target_shape=contract.target_shape.value,
            engineering_resource_id=contract.engineering_resource_id,
            repository_identity=contract.repository_identity,
            source_baseline_id=contract.source_baseline_id,
            source_revision=contract.source_revision,
            desired_outcome=contract.desired_outcome,
            constraints=contract.constraints,
            exact_targets=tuple(
                CodeChangeTargetResponse(
                    path=target.path,
                    operation=target.operation.value,
                )
                for target in contract.exact_targets
            ),
            allowed_areas=contract.allowed_areas,
            forbidden_areas=contract.forbidden_areas,
            verification_obligations=tuple(
                CodeVerificationResponse(
                    kind=item.kind.value,
                    target=item.target,
                    identity=item.identity,
                )
                for item in contract.verification_obligations
            ),
            source_proposal_id=contract.source_proposal_id,
            source_proposal_fingerprint=contract.source_proposal_fingerprint,
        )


class RepositoryChangeProposalResponse(ApiDto):
    proposal_id: UUID
    target_kind: str
    engineering_resource_id: UUID
    repository_identity: str
    source_baseline_id: UUID
    source_ref: str
    source_revision: str
    proposed_targets: tuple[ChangeProposalTargetResponse, ...]
    allowed_areas: tuple[str, ...]
    forbidden_areas: tuple[str, ...]
    rationale: str
    confidence: str
    verification_obligations: tuple[CodeVerificationResponse, ...]
    provenance: ChangeProposalProvenanceResponse
    unresolved_scope_questions: tuple[str, ...]
    proposal_fingerprint: str

    @classmethod
    def from_proposal(cls, proposal: RepositoryChangeProposal) -> Self:
        return cls(
            proposal_id=proposal.proposal_id,
            target_kind=proposal.target_kind.value,
            engineering_resource_id=proposal.engineering_resource_id,
            repository_identity=proposal.repository_identity,
            source_baseline_id=proposal.source_baseline_id,
            source_ref=proposal.source_ref,
            source_revision=proposal.source_revision,
            proposed_targets=tuple(
                ChangeProposalTargetResponse(
                    path=target.path,
                    operation=target.operation.value,
                    disposition=target.disposition.value,
                    rationale=target.rationale,
                    evidence=target.evidence,
                    confidence=target.confidence.value,
                )
                for target in proposal.proposed_targets
            ),
            allowed_areas=proposal.allowed_areas,
            forbidden_areas=proposal.forbidden_areas,
            rationale=proposal.rationale,
            confidence=proposal.confidence.value,
            verification_obligations=tuple(
                CodeVerificationResponse(
                    kind=item.kind.value,
                    target=item.target,
                    identity=item.identity,
                )
                for item in proposal.verification_obligations
            ),
            provenance=ChangeProposalProvenanceResponse(
                **proposal.provenance.model_dump()
            ),
            unresolved_scope_questions=proposal.unresolved_scope_questions,
            proposal_fingerprint=proposal.proposal_fingerprint,
        )


class ProductionPlanResponse(ApiDto):
    proposal_id: UUID
    target_kind: str
    objective: str
    desired_outcome: str
    ordered_steps: tuple[ProductionPlanStepResponse, ...]
    artifact_targets: tuple[str, ...]
    change_proposal: RepositoryChangeProposalResponse | None
    change_contract: CodeChangeContractResponse | None
    inherited_constraints: tuple[str, ...]
    verification_approach: str
    assumptions: tuple[str, ...]
    unresolved_questions: tuple[str, ...]
    fit_classification: str
    engineering_resource_id: UUID
    repository_identity: str
    source_baseline_id: UUID
    source_revision: str

    @classmethod
    def from_proposal(cls, plan: ProductionPlanProposal) -> Self:
        return cls(
            proposal_id=plan.proposal_id,
            target_kind=plan.target_kind.value,
            objective=plan.objective,
            desired_outcome=plan.desired_outcome,
            ordered_steps=tuple(
                ProductionPlanStepResponse(
                    position=step.position,
                    instruction=step.instruction,
                )
                for step in plan.ordered_steps
            ),
            artifact_targets=tuple(
                f"{target.operation.value} {target.path}"
                for target in plan.artifact_targets
            ),
            change_proposal=(
                None
                if plan.change_proposal is None
                else RepositoryChangeProposalResponse.from_proposal(
                    plan.change_proposal
                )
            ),
            change_contract=(
                None
                if plan.change_contract is None
                else CodeChangeContractResponse.from_contract(plan.change_contract)
            ),
            inherited_constraints=plan.inherited_constraints,
            verification_approach=plan.verification_approach,
            assumptions=plan.assumptions,
            unresolved_questions=plan.unresolved_questions,
            fit_classification=plan.fit_classification.value,
            engineering_resource_id=plan.engineering_resource_id,
            repository_identity=plan.repository_identity,
            source_baseline_id=plan.source_baseline_id,
            source_revision=plan.source_revision,
        )


class ExecutionProgressResponse(ApiDto):
    phase: str
    activity: str
    transitions_completed: int = Field(ge=0)
    transitions_total: int | None = Field(default=None, ge=1)
    percent_complete: int | None = Field(default=None, ge=0, le=100)
    started_at: datetime | None
    updated_at: datetime
    elapsed_seconds: float = Field(ge=0)
    still_working: bool
    blocked_reason: str | None = None


class GuidedDesignIssueResponse(ApiDto):
    key: str
    title: str
    objective: str
    why_it_matters: str
    applicability: str
    prerequisite_keys: tuple[str, ...]
    completion_condition: str
    authority_relevance: str
    required_output: str
    critical: bool
    state: str
    skip_rationale: str | None
    reopen_rationale: str | None
    steering_step_id: UUID | None
    admitted_semantic_result_id: UUID | None


class GuidedDesignResponse(ApiDto):
    process_id: UUID
    process_objective: str
    schema_identity: str
    schema_version: str
    schema_selection_rationale: str
    agenda_revision_id: UUID
    agenda_revision_number: int
    current_focus_key: str | None
    current_focus: GuidedDesignIssueResponse | None
    focus_rationale: str | None
    current_stage: str
    completed_areas: tuple[str, ...]
    unresolved_areas: tuple[str, ...]
    dependency_blockers: tuple[str, ...]
    facilitation_strategy: str
    facilitation_guidance: str
    progress_narrative: str
    issues: tuple[GuidedDesignIssueResponse, ...]
    resolved_count: int
    total_applicable_count: int
    readiness: str
    readiness_blockers: tuple[str, ...]
    upcoming_transition: str | None

    @classmethod
    def from_projection(cls, projection: GuidedDesignProjection) -> Self:
        def issue_response(issue):
            return GuidedDesignIssueResponse(
                key=issue.key,
                title=issue.title,
                objective=issue.objective,
                why_it_matters=issue.why_it_matters,
                applicability=issue.applicability,
                prerequisite_keys=issue.prerequisite_keys,
                completion_condition=issue.completion_condition,
                authority_relevance=issue.authority_relevance.value,
                required_output=issue.required_output.value,
                critical=issue.critical,
                state=issue.state.value,
                skip_rationale=issue.skip_rationale,
                reopen_rationale=issue.reopen_rationale,
                steering_step_id=issue.steering_step_id,
                admitted_semantic_result_id=issue.admitted_semantic_result_id,
            )

        return cls(
            process_id=projection.process_id,
            process_objective=projection.process_objective,
            schema_identity=projection.schema_identity,
            schema_version=projection.schema_version,
            schema_selection_rationale=projection.schema_selection_rationale,
            agenda_revision_id=projection.agenda_revision_id,
            agenda_revision_number=projection.agenda_revision_number,
            current_focus_key=projection.current_focus_key,
            current_focus=(
                None
                if projection.current_focus is None
                else issue_response(projection.current_focus)
            ),
            focus_rationale=projection.focus_rationale,
            current_stage=projection.current_stage,
            completed_areas=projection.completed_areas,
            unresolved_areas=projection.unresolved_areas,
            dependency_blockers=projection.dependency_blockers,
            facilitation_strategy=projection.facilitation_strategy.value,
            facilitation_guidance=projection.facilitation_guidance,
            progress_narrative=projection.progress_narrative,
            issues=tuple(issue_response(issue) for issue in projection.issues),
            resolved_count=projection.resolved_count,
            total_applicable_count=projection.total_applicable_count,
            readiness=projection.readiness.state.value,
            readiness_blockers=projection.readiness.blockers,
            upcoming_transition=projection.upcoming_transition,
        )


class WorkResponse(ApiDto):
    work_id: UUID
    goal_id: UUID | None
    mode: WorkMode
    raw_user_requirement: str
    title: str | None
    desired_outcome: str | None
    constraints: tuple[str, ...]
    target_kind: str
    artifact_target: ArtifactTargetResponse | None
    change_proposal: RepositoryChangeProposalResponse | None
    change_contract: CodeChangeContractResponse | None
    production_plan: ProductionPlanResponse | None
    tags: tuple[str, ...]
    engineering_scope: EngineeringScopeResponse | None
    status: WorkStatus
    current_production_step: str
    most_recent_meaningful_event: str
    what_happens_next: str
    human_attention_required: bool
    result_summary: str | None
    current_work_reality_revision_id: UUID | None = None
    steering_enabled: bool = False
    current_steering_step_id: UUID | None = None
    current_steering_step_type: str | None = None
    current_production_cycle_number: int | None = None
    current_production_run_id: UUID | None = None
    current_production_cycle_trusted: bool = False
    latest_trusted_runtime_commit_id: UUID | None = None
    work_complete: bool = False
    automatic_progression_state: str | None = None
    last_stop_reason: str | None = None
    execution_progress: ExecutionProgressResponse | None = None
    guided_design: GuidedDesignResponse | None = None
    next_owner: str | None = None
    control_state_valid: bool | None = None
    control_state_violations: tuple[str, ...] = ()

    @classmethod
    def from_projection(cls, work: WorkProjection) -> Self:
        return cls(
            work_id=work.work_id,
            goal_id=work.goal_id,
            mode=work.mode,
            raw_user_requirement=work.raw_user_requirement,
            title=work.title,
            desired_outcome=work.desired_outcome,
            constraints=work.constraints,
            target_kind=work.target_kind.value,
            artifact_target=(
                None
                if work.artifact_target is None
                else ArtifactTargetResponse(
                    path=work.artifact_target.path,
                    operation=work.artifact_target.operation.value,
                    placement_rationale=work.artifact_target.placement_rationale,
                    confidence=work.artifact_target.confidence.value,
                    source_baseline_id=work.artifact_target.source_baseline_id,
                    source_revision=work.artifact_target.source_revision,
                )
            ),
            change_proposal=(
                None
                if work.change_proposal is None
                else RepositoryChangeProposalResponse.from_proposal(
                    work.change_proposal
                )
            ),
            change_contract=(
                None
                if work.change_contract is None
                else CodeChangeContractResponse.from_contract(work.change_contract)
            ),
            production_plan=(
                None
                if work.production_plan is None
                else ProductionPlanResponse.from_proposal(work.production_plan)
            ),
            tags=work.tags,
            engineering_scope=(
                None
                if work.engineering_scope is None
                else EngineeringScopeResponse.from_record(work.engineering_scope)
            ),
            status=work.status,
            current_production_step=work.current_production_step,
            most_recent_meaningful_event=work.most_recent_meaningful_event,
            what_happens_next=work.what_happens_next,
            human_attention_required=work.human_attention_required,
            result_summary=work.result_summary,
            current_work_reality_revision_id=(
                work.current_work_reality_revision_id
            ),
            steering_enabled=work.steering_enabled,
            current_steering_step_id=work.current_steering_step_id,
            current_steering_step_type=work.current_steering_step_type,
            current_production_cycle_number=work.current_production_cycle_number,
            current_production_run_id=work.current_production_run_id,
            current_production_cycle_trusted=work.current_production_cycle_trusted,
            latest_trusted_runtime_commit_id=(
                work.latest_trusted_runtime_commit_id
            ),
            work_complete=work.work_complete,
        )


class SteeringStepResponse(ApiDto):
    step_id: UUID
    type: str
    objective: str
    completion_condition: str
    position: int
    state: str
    design_issue_key: str | None = None

    @classmethod
    def from_record(cls, step: SteeringStepRecord) -> Self:
        return cls(
            step_id=step.id,
            type=step.type.value,
            objective=step.objective,
            completion_condition=step.completion_condition,
            position=step.position,
            state=step.state.value,
            design_issue_key=step.design_issue_key,
        )


class SteeringDecisionResponse(ApiDto):
    decision_id: UUID
    next_step_type: str
    objective: str
    reason: str
    outcome: str
    human_required: bool
    attention_reason: str | None
    reality_refs: tuple[RealityReference, ...]

    @classmethod
    def from_record(cls, decision: SteeringDecisionRecord) -> Self:
        return cls(
            decision_id=decision.id,
            next_step_type=decision.next_step_type.value,
            objective=decision.objective,
            reason=decision.reason,
            outcome=decision.steering_outcome.value,
            human_required=decision.human_required,
            attention_reason=(
                None
                if decision.attention_reason is None
                else decision.attention_reason.value
            ),
            reality_refs=decision.reality_refs,
        )


class SteeringPlanResponse(ApiDto):
    work_id: UUID
    work_objective: str
    steering_enabled: bool
    steering_plan_id: UUID
    active_revision_id: UUID
    active_revision_number: int
    completed_steps: tuple[SteeringStepResponse, ...]
    current_step: SteeringStepResponse | None
    known_next_steps: tuple[SteeringStepResponse, ...]
    latest_decision: SteeringDecisionResponse | None
    selection_rationale: str | None
    steering_outcome: str | None
    automatic_progression_state: str
    current_production_cycle_number: int | None
    current_production_run_id: UUID | None
    current_production_cycle_trusted: bool
    human_attention_required: bool
    last_stop_reason: str | None

    @classmethod
    def from_projection(cls, projection: SteeringPlanProjection) -> Self:
        return cls(
            work_id=projection.work_id,
            work_objective=projection.work_objective,
            steering_enabled=projection.steering_enabled,
            steering_plan_id=projection.steering_plan_id,
            active_revision_id=projection.active_revision_id,
            active_revision_number=projection.active_revision_number,
            completed_steps=tuple(
                SteeringStepResponse.from_record(step)
                for step in projection.completed_steps
            ),
            current_step=(
                None
                if projection.current_step is None
                else SteeringStepResponse.from_record(projection.current_step)
            ),
            known_next_steps=tuple(
                SteeringStepResponse.from_record(step)
                for step in projection.known_next_steps
            ),
            latest_decision=(
                None
                if projection.latest_decision is None
                else SteeringDecisionResponse.from_record(projection.latest_decision)
            ),
            selection_rationale=projection.selection_rationale,
            steering_outcome=(
                None
                if projection.steering_outcome is None
                else projection.steering_outcome.value
            ),
            automatic_progression_state=(
                projection.automatic_progression_state.value
            ),
            current_production_cycle_number=(
                projection.current_production_cycle_number
            ),
            current_production_run_id=projection.current_production_run_id,
            current_production_cycle_trusted=(
                projection.current_production_cycle_trusted
            ),
            human_attention_required=projection.human_attention_required,
            last_stop_reason=(
                None
                if projection.last_stop_reason is None
                else projection.last_stop_reason.value
            ),
        )


class GoalSummaryResponse(ApiDto):
    goal: GoalResponse
    work_count: int
    works_by_status: dict[str, int]
    recent_works: tuple[WorkResponse, ...]
    needs_attention_count: int

    @classmethod
    def from_projection(cls, projection: GoalProjection) -> Self:
        return cls(
            goal=GoalResponse.from_record(projection.goal),
            work_count=projection.work_count,
            works_by_status={
                status.value: count
                for status, count in projection.works_by_status.items()
            },
            recent_works=tuple(
                WorkResponse.from_projection(work)
                for work in projection.recent_works
            ),
            needs_attention_count=projection.needs_attention_count,
        )


class WorkSubmitRequest(ApiDto):
    requirement: str = Field(min_length=1)
    goal_id: UUID | None = None
    tags: tuple[str, ...] = ()
    mode: WorkMode = WorkMode.IMMEDIATE_PRODUCTION


class WorkRefineRequest(ApiDto):
    title: str | None = None
    desired_outcome: str | None = None
    constraints: tuple[str, ...] = ()
    scope_summary: str | None = None
    production_objective: str | None = None
    expected_artifact_path: str | None = None
    verification_expectation: str | None = None
    code_exact_targets: tuple[str, ...] | None = None
    code_allowed_areas: tuple[str, ...] | None = None
    code_forbidden_areas: tuple[str, ...] | None = None
    code_verification_obligations: tuple[CodeVerificationObligation, ...] | None = None


class HumanDecisionRequest(ApiDto):
    authority_identity: str = Field(min_length=1)
    rationale: str | None = None


class AttentionResolveRequest(ApiDto):
    action: AttentionAction
    authority_identity: str = Field(min_length=1)
    rationale: str | None = None


class AttentionResponse(ApiDto):
    attention_id: UUID
    work_id: UUID
    kind: AttentionKind
    decision: str
    reason: str
    available_actions: tuple[AttentionAction, ...]
    recommended_action: AttentionAction | None
    governed_subject_ref: str
    steering_reason: SteeringAttentionReason | None = None
    recommendation: str | None = None
    alternatives: tuple[str, ...] = ()
    trade_offs: tuple[str, ...] = ()
    expected_impact: str | None = None
    reality_refs: tuple[RealityReference, ...] = ()
    steering_plan_revision_id: UUID | None = None
    steering_step_id: UUID | None = None
    interaction_id: UUID | None = None
    interaction_assessment_id: UUID | None = None
    expected_work_reality_revision_id: UUID | None = None

    @classmethod
    def from_projection(cls, attention: AttentionItem) -> Self:
        return cls(
            attention_id=attention.id,
            work_id=attention.work_id,
            kind=attention.kind,
            decision=attention.decision,
            reason=attention.reason,
            available_actions=attention.available_actions,
            recommended_action=attention.recommended_action,
            governed_subject_ref=attention.governed_subject_ref,
            steering_reason=attention.steering_reason,
            recommendation=attention.recommendation,
            alternatives=attention.alternatives,
            trade_offs=attention.trade_offs,
            expected_impact=attention.expected_impact,
            reality_refs=attention.reality_refs,
            steering_plan_revision_id=attention.steering_plan_revision_id,
            steering_step_id=attention.steering_step_id,
            interaction_id=attention.interaction_id,
            interaction_assessment_id=attention.interaction_assessment_id,
            expected_work_reality_revision_id=(
                attention.expected_work_reality_revision_id
            ),
        )


class RuntimeActivationResponse(ApiDto):
    state: str
    active_application_revision: str | None
    active_repository_tree_identity: str | None
    active_source_package_fingerprint: str | None
    active_static_asset_fingerprint: str | None
    current_trusted_baseline_revision: str | None
    current_trusted_baseline_tree_identity: str | None
    activation_mode: str | None
    human_review_version_id: str | None
    reason: str
    image_rebuild_paths: tuple[str, ...]

    @classmethod
    def from_projection(cls, projection: RuntimeActivationProjection) -> Self:
        return cls(**projection.model_dump(mode="json"))


class WorkResultResponse(ApiDto):
    work_id: UUID
    status: WorkStatus
    desired_outcome: str | None
    produced_artifacts: tuple[str, ...]
    verification_summary: tuple[str, ...]
    repository_state: str | None
    trusted_result: bool
    remaining_blocker_or_risk: str | None
    human_attention_required: bool
    runtime_activation: RuntimeActivationResponse

    @classmethod
    def from_projection(
        cls,
        result: WorkResultProjection,
        activation: RuntimeActivationProjection,
    ) -> Self:
        return cls(
            **result.model_dump(),
            runtime_activation=RuntimeActivationResponse.from_projection(activation),
        )


class HealthResponse(ApiDto):
    service: str
    database: str
    application_initialized: bool


class ErrorResponse(ApiDto):
    code: str
    message: str


class NativeQueueEntryResponse(ApiDto):
    queue_entry_id: UUID
    work_id: UUID
    pwu_id: UUID
    attempt_id: UUID
    fairness_group: str
    condition: str
    wait_reason: str | None
    enqueued_at: datetime
    available_at: datetime
    resume_count: int

    @classmethod
    def from_record(cls, record: ExecutionQueueEntryRecord) -> Self:
        return cls(
            queue_entry_id=record.id,
            work_id=record.work_id,
            pwu_id=record.pwu_id,
            attempt_id=record.attempt_id,
            fairness_group=record.fairness_group,
            condition=record.condition.value,
            wait_reason=record.wait_reason,
            enqueued_at=record.enqueued_at,
            available_at=record.available_at,
            resume_count=record.resume_count,
        )


class NativeExecutionControlRequest(ApiDto):
    command_id: UUID
    action: ControlAction
    expected_control_version: int = Field(ge=0)
    actor_identity: str = Field(default="human:local-operator", min_length=1)
    reason: str = Field(min_length=1)
