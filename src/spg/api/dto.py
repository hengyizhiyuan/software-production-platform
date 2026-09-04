"""Explicit product HTTP DTOs; no persistence or Runtime rows cross this boundary."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from spg.domain.change import CodeChangeContract, CodeVerificationObligation
from spg.domain.product import (
    AttentionAction,
    AttentionItem,
    AttentionKind,
    EngineeringScopeRecord,
    GoalProjection,
    GoalRecord,
    WorkProjection,
    WorkResultProjection,
    WorkStatus,
)
from spg.domain.planning import ProductionPlanProposal
from spg.domain.refinement import RepositoryChangeProposal


class ApiDto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GoalCreateRequest(ApiDto):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None


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


class WorkResponse(ApiDto):
    work_id: UUID
    goal_id: UUID | None
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

    @classmethod
    def from_projection(cls, work: WorkProjection) -> Self:
        return cls(
            work_id=work.work_id,
            goal_id=work.goal_id,
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
        )


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

    @classmethod
    def from_projection(cls, result: WorkResultProjection) -> Self:
        return cls(**result.model_dump())


class HealthResponse(ApiDto):
    service: str
    database: str
    application_initialized: bool


class ErrorResponse(ApiDto):
    code: str
    message: str
