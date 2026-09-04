"""MVP product contracts for goal-centric governed software work."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from spg.domain.preparation import ContextSemanticRole
from spg.domain.planning import ProductionPlanProposal


class GoalCondition(StrEnum):
    ACTIVE = "ACTIVE"


class WorkCondition(StrEnum):
    DRAFT = "DRAFT"
    NEEDS_REFINEMENT = "NEEDS_REFINEMENT"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    READY = "READY"
    REJECTED = "REJECTED"


class WorkStatus(StrEnum):
    DRAFT = "DRAFT"
    NEEDS_REFINEMENT = "NEEDS_REFINEMENT"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    READY = "READY"
    RUNNING = "RUNNING"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"


class ArtifactTargetConfidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ArtifactTargetOperation(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"


class ArtifactTargetProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    operation: ArtifactTargetOperation
    placement_rationale: str
    confidence: ArtifactTargetConfidence
    source_baseline_id: UUID
    source_revision: str


class EngineeringResourceKind(StrEnum):
    REPOSITORY = "REPOSITORY"


class EngineeringScopeCondition(StrEnum):
    PROPOSED = "PROPOSED"
    ADMITTED = "ADMITTED"


class ResourceBindingCondition(StrEnum):
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"


class AttentionKind(StrEnum):
    WORK_DRAFT_APPROVAL = "WORK_DRAFT_APPROVAL"
    WORK_REFINEMENT_REQUIRED = "WORK_REFINEMENT_REQUIRED"
    CANDIDATE_AUTHORIZATION = "CANDIDATE_AUTHORIZATION"
    PRODUCTION_BLOCKED = "PRODUCTION_BLOCKED"


class AttentionAction(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_REFINEMENT = "REQUEST_REFINEMENT"
    AUTHORIZE = "AUTHORIZE"


class GoalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    title: str
    description: str | None
    condition: GoalCondition
    created_at: datetime
    updated_at: datetime


class EngineeringContextReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    semantic_role: ContextSemanticRole
    repository_relative_path: str = Field(min_length=1)


class EngineeringResourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    kind: EngineeringResourceKind
    repository_identity: str
    location_ref: str
    authoritative_ref: str
    context_references: tuple[EngineeringContextReference, ...]
    is_default: bool
    created_at: datetime
    updated_at: datetime


class ResourceBindingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    engineering_scope_id: UUID
    resource_id: UUID
    condition: ResourceBindingCondition
    created_at: datetime


class EngineeringScopeRecord(BaseModel):
    """Structural 1..N representation; MVP execution policy is validated elsewhere."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    work_id: UUID
    summary: str
    fingerprint: str
    condition: EngineeringScopeCondition
    bindings: tuple[ResourceBindingRecord, ...]
    created_at: datetime
    updated_at: datetime


class WorkRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    goal_id: UUID | None
    raw_user_requirement: str
    refined_title: str | None
    desired_outcome: str | None
    constraints: tuple[str, ...]
    tags: tuple[str, ...]
    condition: WorkCondition
    engineering_scope_id: UUID | None
    scope_summary: str | None
    production_objective: str | None
    expected_artifact_path: str | None
    artifact_operation: ArtifactTargetOperation | None = None
    artifact_placement_rationale: str | None = None
    artifact_target_confidence: ArtifactTargetConfidence | None = None
    artifact_source_baseline_id: UUID | None = None
    artifact_source_revision: str | None = None
    verification_expectation: str | None
    production_plan: ProductionPlanProposal | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("tags")
    @classmethod
    def tags_are_normalized(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(sorted({item.strip() for item in value if item.strip()}))
        if len(normalized) > 20:
            raise ValueError("MVP Work supports at most 20 tags")
        return normalized


class WorkRuntimeBindingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    work_id: UUID
    engineering_scope_id: UUID
    resource_id: UUID
    production_run_id: UUID
    plan_revision_id: UUID
    work_unit_id: UUID
    governance_record_id: UUID
    admitted_by: str
    created_at: datetime


class WorkProjection(BaseModel):
    """User-facing projection; never an authority for Runtime transitions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    work_id: UUID
    goal_id: UUID | None
    raw_user_requirement: str
    title: str | None
    desired_outcome: str | None
    constraints: tuple[str, ...]
    artifact_target: ArtifactTargetProposal | None = None
    production_plan: ProductionPlanProposal | None = None
    tags: tuple[str, ...]
    engineering_scope: EngineeringScopeRecord | None
    status: WorkStatus
    current_production_step: str
    most_recent_meaningful_event: str
    what_happens_next: str
    human_attention_required: bool
    result_summary: str | None


class GoalProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    goal: GoalRecord
    work_count: int
    works_by_status: dict[WorkStatus, int]
    recent_works: tuple[WorkProjection, ...]
    needs_attention_count: int


class AttentionItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    work_id: UUID
    kind: AttentionKind
    decision: str
    reason: str
    available_actions: tuple[AttentionAction, ...]
    recommended_action: AttentionAction | None
    governed_subject_ref: str


class WorkResultProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    work_id: UUID
    status: WorkStatus
    desired_outcome: str | None
    produced_artifacts: tuple[str, ...]
    verification_summary: tuple[str, ...]
    repository_state: str | None
    trusted_result: bool
    remaining_blocker_or_risk: str | None
    human_attention_required: bool


class WorkRefinementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str | None = None
    desired_outcome: str | None = None
    constraints: tuple[str, ...] = ()
    scope_summary: str | None = None
    production_objective: str | None = None
    expected_artifact_path: str | None = None
    verification_expectation: str | None = None


class AttentionResolutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action: AttentionAction
    authority_identity: str = Field(min_length=1)
    rationale: str | None = None


class RuntimeFactSummary(BaseModel):
    """Read-only identifiers from Runtime Source of Truth used by projections."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: UUID | None = None
    dispatch_id: UUID | None = None
    provider_outcome: str | None = None
    observation_id: UUID | None = None
    completion_id: UUID | None = None
    completion_outcome: str | None = None
    proposed_snapshot_id: UUID | None = None
    verification_obligations: tuple[str, ...] = ()
    verification_results: tuple[str, ...] = ()
    admissibility_id: UUID | None = None
    admissibility_outcome: str | None = None
    candidate_id: UUID | None = None
    candidate_fingerprint: str | None = None
    authorization_id: UUID | None = None
    integration_effect_id: UUID | None = None
    integration_state: str | None = None
    runtime_commit_id: UUID | None = None
    artifact_paths: tuple[str, ...] = ()
    completion_requires_production_result: bool = False
    latest_event: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ProductDomainError(RuntimeError):
    """Base error for rejected product-layer operations."""


class ProductRecordNotFound(ProductDomainError):
    pass


class ProductInvariantViolation(ProductDomainError):
    pass
