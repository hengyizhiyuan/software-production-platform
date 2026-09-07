"""Explicit product HTTP DTOs; no persistence or Runtime rows cross this boundary."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from spg.domain.change import CodeChangeContract, CodeVerificationObligation
from spg.domain.interaction import SharedUnderstanding
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
from spg.domain.steering import (
    RealityReference,
    SteeringAttentionReason,
    SteeringDecisionRecord,
    SteeringPlanProjection,
    SteeringStepRecord,
)


class ApiDto(BaseModel):
    model_config = ConfigDict(extra="forbid")


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


class InteractionRecordResponse(ApiDto):
    record_id: UUID
    sequence: int
    actor: str
    source: str
    content: str
    work_focus_id: UUID | None
    supporting_references: tuple[str, ...]
    created_at: datetime


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


class InteractionAssessmentResponse(ApiDto):
    assessment_id: UUID
    basis_fingerprint: str
    basis_last_sequence: int
    interpreted_motive: str | None
    desired_outcome: str | None
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
    source_assessment_id: UUID
    source_record_ids: tuple[UUID, ...]
    motive: str
    desired_outcome: str
    context_facts: tuple[str, ...]
    constraints: tuple[str, ...]
    requests: tuple[str, ...]
    engineering_scope_id: UUID
    engineering_resource_id: UUID
    scope_basis_fingerprint: str
    repository_identity: str
    repository_ref: str
    source_baseline_id: UUID
    source_revision: str
    governance_record_id: UUID
    supporting_references: tuple[str, ...]
    change_set: tuple[str, ...]
    rationale: str
    admitted_by: str
    schema_version: str
    created_at: datetime


class SharedUnderstandingResponse(ApiDto):
    interaction_id: UUID
    condition: str
    current_work_id: UUID | None
    created_at: datetime
    updated_at: datetime
    records: tuple[InteractionRecordResponse, ...]
    human_said: tuple[str, ...]
    latest_assessment: InteractionAssessmentResponse | None
    latest_assessment_current: bool
    interpreted_motive: str | None
    desired_outcome: str | None
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
                    provider_identity=assessment.provider_identity,
                    model_identity=assessment.model_identity,
                    schema_version=assessment.schema_version,
                    created_at=assessment.created_at,
                )
            ),
            latest_assessment_current=projection.latest_assessment_current,
            interpreted_motive=projection.interpreted_motive,
            desired_outcome=projection.desired_outcome,
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

    @classmethod
    def from_record(cls, step: SteeringStepRecord) -> Self:
        return cls(
            step_id=step.id,
            type=step.type.value,
            objective=step.objective,
            completion_condition=step.completion_condition,
            position=step.position,
            state=step.state.value,
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
