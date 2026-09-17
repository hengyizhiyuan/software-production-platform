"""Provider-neutral contracts for long-lived Reality-driven Plan Steering truth."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
from typing import Annotated, Protocol, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from spg.domain.change import (
    ProductionTargetKind,
    safe_repository_area,
    safe_repository_path,
    safe_repository_scope,
)
from spg.domain.planning import ProductionPlanArtifactTarget


class SteeringPlanRevisionCondition(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"


class SteeringStepType(StrEnum):
    REFINE = "REFINE"
    HUMAN_DECISION = "HUMAN_DECISION"
    DESIGN = "DESIGN"
    PRODUCE = "PRODUCE"
    VERIFY_ACCEPT = "VERIFY_ACCEPT"
    COMPLETE = "COMPLETE"


class SteeringStepState(StrEnum):
    KNOWN = "KNOWN"
    CURRENT = "CURRENT"
    CLOSED = "CLOSED"
    SUPERSEDED = "SUPERSEDED"


class SteeringOutcome(StrEnum):
    AUTO_CONTINUE = "AUTO_CONTINUE"
    HUMAN_ATTENTION = "HUMAN_ATTENTION"
    COMPLETE = "COMPLETE"


class SteeringDriverStopReason(StrEnum):
    HUMAN_ATTENTION = "HUMAN_ATTENTION"
    COMPLETE = "COMPLETE"
    PRODUCTION_RUNNING = "PRODUCTION_RUNNING"
    BLOCKED = "BLOCKED"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    NO_PROGRESS = "NO_PROGRESS"
    TRANSITION_BOUND = "TRANSITION_BOUND"
    SHUTDOWN = "SHUTDOWN"


class SteeringActionType(StrEnum):
    SEMANTIC_RESULT_ADMISSION = "SEMANTIC_RESULT_ADMISSION"
    STEP_TRANSITION = "STEP_TRANSITION"
    PRODUCTION_CYCLE_ADMISSION = "PRODUCTION_CYCLE_ADMISSION"
    PRODUCTION_SCHEDULE = "PRODUCTION_SCHEDULE"
    HUMAN_ATTENTION = "HUMAN_ATTENTION"
    COMPLETE = "COMPLETE"


class SteeringAutomaticProgressionState(StrEnum):
    ACTIVE = "ACTIVE"
    WAITING_PRODUCTION = "WAITING_PRODUCTION"
    STOPPED = "STOPPED"


class SteeringHistoryEventType(StrEnum):
    STEP_TRANSITION = "STEP_TRANSITION"
    STEP_ELABORATION = "STEP_ELABORATION"
    PLAN_REVISION = "PLAN_REVISION"


class RealityReferenceKind(StrEnum):
    WORK = "WORK"
    WORK_REALITY_REVISION = "WORK_REALITY_REVISION"
    GOVERNANCE_DECISION = "GOVERNANCE_DECISION"
    TRUSTED_BASELINE = "TRUSTED_BASELINE"
    REPOSITORY_OBSERVATION = "REPOSITORY_OBSERVATION"
    VERIFICATION = "VERIFICATION"
    COMPLETION = "COMPLETION"
    CANDIDATE = "CANDIDATE"
    AUTHORIZATION = "AUTHORIZATION"
    INTEGRATION_EFFECT = "INTEGRATION_EFFECT"
    RUNTIME_COMMIT = "RUNTIME_COMMIT"
    RECOVERY_ASSESSMENT = "RECOVERY_ASSESSMENT"
    SEMANTIC_RESULT = "SEMANTIC_RESULT"
    DESIGN_PROCESS = "DESIGN_PROCESS"
    DESIGN_AGENDA_REVISION = "DESIGN_AGENDA_REVISION"


class SteeringAttentionReason(StrEnum):
    MOTIVE_OR_OUTCOME_AMBIGUITY = "MOTIVE_OR_OUTCOME_AMBIGUITY"
    MAJOR_PRODUCT_OR_ARCHITECTURE_DECISION = (
        "MAJOR_PRODUCT_OR_ARCHITECTURE_DECISION"
    )
    SCOPE_OR_AUTHORITY_EXPANSION = "SCOPE_OR_AUTHORITY_EXPANSION"
    MATERIAL_RISK_OR_COST_DECISION = "MATERIAL_RISK_OR_COST_DECISION"
    PRODUCT_ACCEPTANCE_REQUIRED = "PRODUCT_ACCEPTANCE_REQUIRED"
    PRODUCTION_PROPOSAL_REVIEW_REQUIRED = "PRODUCTION_PROPOSAL_REVIEW_REQUIRED"


class SteeringAuthorityAssessment(StrEnum):
    WITHIN_AUTHORITY = "WITHIN_AUTHORITY"
    UNCERTAIN = "UNCERTAIN"
    EXPANDS_AUTHORITY = "EXPANDS_AUTHORITY"


class SemanticResultKind(StrEnum):
    DESIGN_DIRECTION = "DESIGN_DIRECTION"
    WORK_REFINEMENT = "WORK_REFINEMENT"


class PlanFrameBlockerKind(StrEnum):
    PRODUCTION_NOT_PRODUCED = "PRODUCTION_NOT_PRODUCED"
    VERIFICATION_NOT_PASSING = "VERIFICATION_NOT_PASSING"
    REPOSITORY_INTEGRATION_NOT_CONVERGED = "REPOSITORY_INTEGRATION_NOT_CONVERGED"
    CURRENT_RESULT_MAY_BE_INSUFFICIENT = "CURRENT_RESULT_MAY_BE_INSUFFICIENT"


class RealityReference(BaseModel):
    """Stable identity of Reality owned outside the Steering Plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: RealityReferenceKind
    identity: UUID


class ResolvedRealityReference(BaseModel):
    """In-memory proof that a typed external Reality identity was resolved."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reference: RealityReference
    material_fingerprint: str = Field(min_length=64, max_length=64)


class PlanFrameBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: PlanFrameBlockerKind
    reason: str = Field(min_length=1)
    reality_refs: tuple[RealityReference, ...] = Field(min_length=1)


class SemanticContextMaterial(BaseModel):
    """Bounded exact-baseline repository material admitted for semantic reasoning."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_relative_path: str = Field(min_length=1)
    content: str
    content_fingerprint: str = Field(min_length=64, max_length=64)


class SemanticGovernanceDecision(BaseModel):
    """Minimum Human/governance fact projected into a semantic input."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    decision_type: str = Field(min_length=1)
    authority_identity: str = Field(min_length=1)
    scope: dict[str, object]
    rationale: str | None = None


SemanticBoundedRepositoryArea = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^[^/]+/[^/]+(?:/[^/]+)*/\*\*$",
    ),
]


class SemanticProductionProposal(BaseModel):
    """Advisory bounded production proposal; never production authority itself."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_kind: ProductionTargetKind = Field(
        description="Existing Watt production target kind; no provider-defined aliases.",
    )
    objective: str = Field(min_length=1)
    artifact_targets: tuple[ProductionPlanArtifactTarget, ...] = Field(
        default=(),
        description=(
            "Typed documentation artifact targets; CODE_WORK must leave this empty."
        ),
    )
    code_targets: tuple[str, ...] = Field(
        default=(),
        description="Exact repository-relative code paths without wildcards.",
    )
    allowed_areas: tuple[SemanticBoundedRepositoryArea, ...] = Field(
        default=(),
        description=(
            "Repository-relative bounded subdirectories ending with /**; "
            "root-wide areas such as src/** or tests/** are invalid."
        ),
    )
    forbidden_areas: tuple[str, ...] = Field(
        default=(),
        description="Repository-relative exact paths or bounded areas ending with /**.",
    )
    verification_expectation: str = Field(min_length=1)

    @field_validator("code_targets")
    @classmethod
    def normalize_code_targets(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(safe_repository_path(value) for value in values))

    @field_validator("allowed_areas")
    @classmethod
    def normalize_allowed_areas(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(safe_repository_area(value) for value in values))

    @field_validator("forbidden_areas")
    @classmethod
    def normalize_forbidden_areas(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(safe_repository_scope(value) for value in values))

    @model_validator(mode="after")
    def require_one_bounded_target_form(self) -> Self:
        if self.target_kind is ProductionTargetKind.DOCUMENTATION_WORK:
            if len(self.artifact_targets) != 1 or any(
                (self.code_targets, self.allowed_areas, self.forbidden_areas)
            ):
                raise ValueError(
                    "documentation semantic production requires one artifact target"
                )
        elif self.artifact_targets or not (self.code_targets or self.allowed_areas):
            raise ValueError(
                "code semantic production requires exact targets or bounded areas"
            )
        if set(self.code_targets) & set(self.forbidden_areas):
            raise ValueError("semantic production target conflicts with a forbidden path")
        return self


class SemanticStepInput(BaseModel):
    """Reconstructable governed input for one current semantic Steering Step."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    work_id: UUID
    desired_outcome: str = Field(min_length=1)
    constraints: tuple[str, ...]
    work_context_facts: tuple[str, ...] = ()
    work_requests: tuple[str, ...] = ()
    steering_plan_revision_id: UUID
    step: "SteeringStepRecord"
    basis_fingerprint: str = Field(min_length=64, max_length=64)
    engineering_resource_id: UUID | None
    engineering_scope_id: UUID
    engineering_scope_summary: str = Field(min_length=1)
    engineering_scope_fingerprint: str = Field(min_length=64, max_length=64)
    repository_identity: str | None = Field(default=None, min_length=1)
    repository_location: str | None = Field(default=None, min_length=1)
    repository_ref: str | None = Field(default=None, min_length=1)
    source_baseline_id: UUID | None
    source_revision: str | None = Field(default=None, min_length=1)
    source_tree: str | None = Field(default=None, min_length=1)
    reality_refs: tuple[RealityReference, ...] = Field(min_length=1)
    governance_decisions: tuple[SemanticGovernanceDecision, ...]
    repository_tree_paths: tuple[str, ...]
    context_materials: tuple[SemanticContextMaterial, ...]
    design_context: dict[str, object] | None = None

    @model_validator(mode="after")
    def require_semantic_step(self) -> Self:
        if self.step.type not in {SteeringStepType.DESIGN, SteeringStepType.REFINE}:
            raise ValueError("Semantic Step input supports only DESIGN and REFINE")
        if self.step.steering_plan_revision_id != self.steering_plan_revision_id:
            raise ValueError("Semantic Step input revision and Step do not match")
        return self


class SemanticStepResultCandidate(BaseModel):
    """Advisory provider output bound to one exact semantic input."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    work_id: UUID
    steering_plan_revision_id: UUID
    step_id: UUID
    step_type: SteeringStepType
    basis_fingerprint: str = Field(min_length=64, max_length=64)
    result_kind: SemanticResultKind
    bounded_summary: str = Field(min_length=20)
    decisions: tuple[str, ...] = Field(min_length=1)
    derived_constraints: tuple[str, ...] = ()
    evidence_refs: tuple[RealityReference, ...] = Field(min_length=1)
    unresolved_questions: tuple[str, ...] = ()
    authority_assessment: SteeringAuthorityAssessment
    human_attention_recommendation: str | None = None
    proposed_production: SemanticProductionProposal | None = None
    reasoning_provider_identity: str | None = None
    completion_claimed: bool

    @model_validator(mode="after")
    def require_coherent_semantic_result(self) -> Self:
        expected_kind = (
            SemanticResultKind.DESIGN_DIRECTION
            if self.step_type is SteeringStepType.DESIGN
            else SemanticResultKind.WORK_REFINEMENT
            if self.step_type is SteeringStepType.REFINE
            else None
        )
        if expected_kind is None or self.result_kind is not expected_kind:
            raise ValueError("semantic result kind must match DESIGN or REFINE")
        if self.step_type is SteeringStepType.REFINE and self.proposed_production:
            raise ValueError("REFINE cannot directly propose production")
        lacks_watt_authority = (
            self.authority_assessment
            is not SteeringAuthorityAssessment.WITHIN_AUTHORITY
        )
        materially_changes_current_step = bool(self.unresolved_questions)
        if lacks_watt_authority != materially_changes_current_step:
            raise ValueError(
                "blocking Human Attention requires both missing Watt authority and "
                "a material unresolved current-Step decision"
            )
        attention_required = (
            lacks_watt_authority and materially_changes_current_step
        )
        if attention_required != bool(self.human_attention_recommendation):
            raise ValueError(
                "a material Human-owned current-Step decision requires Human Attention"
            )
        if self.completion_claimed and attention_required:
            raise ValueError("an unresolved semantic result cannot claim completion")
        return self

    @property
    def material_direction_fingerprint(self) -> str:
        payload = {
            "step_type": self.step_type.value,
            "result_kind": self.result_kind.value,
            "decisions": [" ".join(item.casefold().split()) for item in self.decisions],
            "derived_constraints": [
                " ".join(item.casefold().split()) for item in self.derived_constraints
            ],
            "authority_assessment": self.authority_assessment.value,
            "proposed_production": (
                None
                if self.proposed_production is None
                else self.proposed_production.model_dump(mode="json")
            ),
            "completion_claimed": self.completion_claimed,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()


class SemanticStepResultRecord(BaseModel):
    """Immutable governed Reality admitted from a validated semantic candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    work_id: UUID
    steering_plan_revision_id: UUID
    step_id: UUID
    step_type: SteeringStepType
    basis_fingerprint: str = Field(min_length=64, max_length=64)
    result_kind: SemanticResultKind
    bounded_summary: str
    decisions: tuple[str, ...]
    derived_constraints: tuple[str, ...]
    evidence_refs: tuple[RealityReference, ...]
    unresolved_questions: tuple[str, ...]
    authority_assessment: SteeringAuthorityAssessment
    human_attention_recommendation: str | None
    proposed_production: SemanticProductionProposal | None
    reasoning_provider_identity: str | None
    completion_satisfied: bool
    material_direction_fingerprint: str = Field(min_length=64, max_length=64)
    created_at: datetime


class SemanticStepCapability(Protocol):
    """Replaceable semantic reasoning seam; output remains advisory."""

    def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
        ...


class SteeringStepSpec(BaseModel):
    """Already-governed input for one ordered Steering Step."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: SteeringStepType
    objective: str = Field(min_length=1)
    completion_condition: str = Field(min_length=1)
    state: SteeringStepState = SteeringStepState.KNOWN
    design_issue_key: str | None = Field(
        default=None,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )


class SteeringPlanRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    work_id: UUID
    created_at: datetime


class SteeringPlanRevisionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    steering_plan_id: UUID
    work_id: UUID
    revision_number: int = Field(ge=1)
    condition: SteeringPlanRevisionCondition
    supersedes_revision_id: UUID | None
    rationale: str = Field(min_length=1)
    reality_refs: tuple[RealityReference, ...]
    created_at: datetime


class SteeringStepRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    steering_plan_revision_id: UUID
    type: SteeringStepType
    objective: str
    completion_condition: str
    position: int = Field(ge=1)
    state: SteeringStepState
    elaborates_step_id: UUID | None
    design_issue_key: str | None = None
    created_at: datetime


class SteeringDecisionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    steering_plan_revision_id: UUID
    current_step_id: UUID
    next_step_type: SteeringStepType
    objective: str
    reason: str
    reality_refs: tuple[RealityReference, ...]
    human_required: bool
    completion_condition: str
    steering_outcome: SteeringOutcome
    basis_fingerprint: str = Field(min_length=64, max_length=64)
    reasoning_provider_identity: str | None
    attention_reason: SteeringAttentionReason | None = None
    recommendation: str | None = None
    alternatives: tuple[str, ...] = ()
    trade_offs: tuple[str, ...] = ()
    expected_impact: str | None = None
    authority_assessment: SteeringAuthorityAssessment | None = None
    proposed_engineering_scope_fingerprint: str | None = None
    created_at: datetime

    @model_validator(mode="after")
    def require_consistent_outcome(self) -> Self:
        if self.steering_outcome is SteeringOutcome.HUMAN_ATTENTION:
            if not self.human_required:
                raise ValueError("HUMAN_ATTENTION requires human_required")
        elif self.human_required:
            raise ValueError("only HUMAN_ATTENTION may require a Human")
        if (self.steering_outcome is SteeringOutcome.COMPLETE) != (
            self.next_step_type is SteeringStepType.COMPLETE
        ):
            raise ValueError("COMPLETE outcome and COMPLETE Next Step must agree")
        self._validate_optional_attention_detail()
        return self

    def _validate_optional_attention_detail(self) -> None:
        has_attention_detail = any(
            (
                self.attention_reason is not None,
                self.recommendation is not None,
                self.alternatives,
                self.trade_offs,
                self.expected_impact is not None,
            )
        )
        if has_attention_detail:
            if (
                self.steering_outcome is not SteeringOutcome.HUMAN_ATTENTION
                or self.attention_reason is None
                or not self.recommendation
                or not self.recommendation.strip()
                or not self.expected_impact
                or not self.expected_impact.strip()
            ):
                raise ValueError("Typed Attention detail requires meaningful Human Attention")
        if (
            self.authority_assessment
            in {
                SteeringAuthorityAssessment.UNCERTAIN,
                SteeringAuthorityAssessment.EXPANDS_AUTHORITY,
            }
            and self.steering_outcome is not SteeringOutcome.HUMAN_ATTENTION
        ):
            raise ValueError("Authority uncertainty or expansion requires Human Attention")


class SteeringHistoryEventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    steering_plan_id: UUID
    steering_plan_revision_id: UUID
    event_type: SteeringHistoryEventType
    from_revision_id: UUID | None
    to_revision_id: UUID | None
    from_step_id: UUID | None
    to_step_id: UUID | None
    steering_decision_id: UUID | None
    related_step_ids: tuple[UUID, ...]
    rationale: str
    reality_refs: tuple[RealityReference, ...]
    created_at: datetime


class CreateSteeringPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    work_id: UUID
    rationale: str = Field(min_length=1)
    reality_refs: tuple[RealityReference, ...] = ()
    steps: tuple[SteeringStepSpec, ...] = Field(min_length=1)


class AdmitSteeringDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    steering_plan_revision_id: UUID
    current_step_id: UUID
    next_step_type: SteeringStepType
    objective: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    reality_refs: tuple[RealityReference, ...] = Field(min_length=1)
    human_required: bool
    completion_condition: str = Field(min_length=1)
    steering_outcome: SteeringOutcome
    expected_basis_fingerprint: str = Field(min_length=64, max_length=64)
    reasoning_provider_identity: str | None = None
    attention_reason: SteeringAttentionReason | None = None
    recommendation: str | None = None
    alternatives: tuple[str, ...] = Field(default=(), max_length=3)
    trade_offs: tuple[str, ...] = Field(default=(), max_length=3)
    expected_impact: str | None = None
    authority_assessment: SteeringAuthorityAssessment | None = None
    proposed_engineering_scope_fingerprint: str | None = None

    @field_validator("objective", "reason", "completion_condition")
    @classmethod
    def require_meaningful_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Steering decision text must not be blank")
        return value

    @model_validator(mode="after")
    def require_optional_attention_consistency(self) -> Self:
        has_attention_detail = any(
            (
                self.attention_reason is not None,
                self.recommendation is not None,
                self.alternatives,
                self.trade_offs,
                self.expected_impact is not None,
            )
        )
        if has_attention_detail and (
            self.steering_outcome is not SteeringOutcome.HUMAN_ATTENTION
            or self.attention_reason is None
            or not self.recommendation
            or not self.recommendation.strip()
            or not self.expected_impact
            or not self.expected_impact.strip()
        ):
            raise ValueError("Typed Attention detail requires meaningful Human Attention")
        if (
            self.authority_assessment
            in {
                SteeringAuthorityAssessment.UNCERTAIN,
                SteeringAuthorityAssessment.EXPANDS_AUTHORITY,
            }
            and self.steering_outcome is not SteeringOutcome.HUMAN_ATTENTION
        ):
            raise ValueError("Authority uncertainty or expansion requires Human Attention")
        return self


class TransitionSteeringStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    steering_plan_revision_id: UUID
    current_step_id: UUID
    next_step_id: UUID
    steering_decision_id: UUID


class ElaborateSteeringStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    steering_plan_revision_id: UUID
    step_id: UUID
    replacements: tuple[SteeringStepSpec, ...] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    reality_refs: tuple[RealityReference, ...] = Field(min_length=1)


class ReviseSteeringPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    steering_plan_id: UUID
    superseded_revision_id: UUID
    rationale: str = Field(min_length=1)
    reality_refs: tuple[RealityReference, ...] = Field(min_length=1)
    steps: tuple[SteeringStepSpec, ...] = Field(min_length=1)


class SteeringPlanRevisionView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    revision: SteeringPlanRevisionRecord
    steps: tuple[SteeringStepRecord, ...]


class SteeringPlanReconstruction(BaseModel):
    """Provider-free reconstruction from persisted Work, Plan, and history facts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    work_id: UUID
    work_objective: str
    steering_plan_id: UUID
    active_revision: SteeringPlanRevisionView
    revision_lineage: tuple[SteeringPlanRevisionView, ...]
    completed_steps: tuple[SteeringStepRecord, ...]
    current_step: SteeringStepRecord | None
    known_future_steps: tuple[SteeringStepRecord, ...]
    next_step: SteeringStepRecord | None
    latest_decision: SteeringDecisionRecord | None
    history: tuple[SteeringHistoryEventRecord, ...]
    semantic_results: tuple[SemanticStepResultRecord, ...] = ()
    has_material_revision: bool


class SteeringIterationResult(BaseModel):
    """Ephemeral driver result; authoritative progression remains persisted elsewhere."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    work_id: UUID
    action: SteeringActionType | None
    progressed: bool
    before_fingerprint: str = Field(min_length=64, max_length=64)
    after_fingerprint: str = Field(min_length=64, max_length=64)
    stop_reason: SteeringDriverStopReason | None = None


class SteeringActivationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    work_id: UUID
    iterations_executed: int = Field(ge=0)
    stop_reason: SteeringDriverStopReason
    last_action: SteeringActionType | None = None


class SteeringPlanProjection(BaseModel):
    """Read-only Plan-level view composed from persisted truth and driver activity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    work_id: UUID
    work_objective: str
    steering_enabled: bool
    steering_plan_id: UUID
    active_revision_id: UUID
    active_revision_number: int
    completed_steps: tuple[SteeringStepRecord, ...]
    current_step: SteeringStepRecord | None
    known_next_steps: tuple[SteeringStepRecord, ...]
    latest_decision: SteeringDecisionRecord | None
    selection_rationale: str | None
    steering_outcome: SteeringOutcome | None
    automatic_progression_state: SteeringAutomaticProgressionState
    current_production_cycle_number: int | None
    current_production_run_id: UUID | None
    current_production_cycle_trusted: bool
    human_attention_required: bool
    last_stop_reason: SteeringDriverStopReason | None


class SteeringDecisionBasis(BaseModel):
    """Canonical, provider-free basis used to detect stale Steering output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    canonical_representation: str = Field(min_length=1)
    fingerprint: str = Field(min_length=64, max_length=64)
    resolved_reality: tuple[ResolvedRealityReference, ...]


class PlanFrame(BaseModel):
    """Ephemeral reasoning input assembled from authoritative persisted Reality."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    work_id: UUID
    work_reality_revision_id: UUID | None = None
    work_objective: str = Field(min_length=1)
    work_condition: str = Field(min_length=1)
    constraints: tuple[str, ...]
    engineering_scope_id: UUID | None
    engineering_scope_condition: str | None
    engineering_scope_fingerprint: str | None
    reconstruction: SteeringPlanReconstruction
    governance_decision_refs: tuple[RealityReference, ...]
    trusted_baseline_ref: RealityReference | None
    runtime_reality_refs: tuple[RealityReference, ...]
    open_blocking_reality: tuple[PlanFrameBlocker, ...]
    completion_evidence_sufficient: bool
    basis: SteeringDecisionBasis


class NextStepCandidate(BaseModel):
    """Advisory provider-neutral Steering output; never authority by itself."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: SteeringStepType
    objective: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    reality_refs: tuple[RealityReference, ...] = Field(min_length=1)
    human_required: bool
    completion_condition: str = Field(min_length=1)
    proposed_outcome: SteeringOutcome
    basis_fingerprint: str = Field(min_length=64, max_length=64)
    authority_assessment: SteeringAuthorityAssessment
    proposed_engineering_scope_fingerprint: str | None = None
    attention_reason: SteeringAttentionReason | None = None
    recommendation: str | None = None
    alternatives: tuple[str, ...] = Field(default=(), max_length=3)
    trade_offs: tuple[str, ...] = Field(default=(), max_length=3)
    expected_impact: str | None = None
    reasoning_provider_identity: str | None = None

    @field_validator("objective", "reason", "completion_condition")
    @classmethod
    def require_meaningful_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Steering candidate text must not be blank")
        return value

    @model_validator(mode="after")
    def require_coherent_direction(self) -> Self:
        human_attention = self.proposed_outcome is SteeringOutcome.HUMAN_ATTENTION
        if human_attention != self.human_required:
            raise ValueError("Human requirement must match the Steering outcome")
        if (self.proposed_outcome is SteeringOutcome.COMPLETE) != (
            self.type is SteeringStepType.COMPLETE
        ):
            raise ValueError("COMPLETE outcome and COMPLETE Next Step must agree")
        if human_attention:
            if self.type is not SteeringStepType.HUMAN_DECISION:
                raise ValueError("HUMAN_ATTENTION requires a HUMAN_DECISION Next Step")
            if self.attention_reason is None:
                raise ValueError("Steering Human Attention requires a typed reason")
            if (
                not self.recommendation
                or not self.recommendation.strip()
                or not self.expected_impact
                or not self.expected_impact.strip()
            ):
                raise ValueError(
                    "Steering Human Attention requires recommendation and expected impact"
                )
            if self.objective.strip().casefold() in {
                "continue",
                "continue?",
                "继续",
                "继续吗",
                "是否继续",
            }:
                raise ValueError("Steering Human Attention requires a material decision")
        elif any(
            (
                self.attention_reason is not None,
                self.recommendation is not None,
                self.alternatives,
                self.trade_offs,
                self.expected_impact is not None,
            )
        ):
            raise ValueError("Attention detail is valid only for HUMAN_ATTENTION")
        if (
            self.authority_assessment is not SteeringAuthorityAssessment.WITHIN_AUTHORITY
            and not human_attention
        ):
            raise ValueError("Authority uncertainty or expansion requires Human Attention")
        return self

    @property
    def material_direction_fingerprint(self) -> str:
        payload = {
            "type": self.type.value,
            "objective": " ".join(self.objective.casefold().split()),
            "outcome": self.proposed_outcome.value,
            "human_required": self.human_required,
            "attention_reason": (
                None if self.attention_reason is None else self.attention_reason.value
            ),
            "authority_assessment": self.authority_assessment.value,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()


class PlanSteeringCapability(Protocol):
    """Replaceable reasoning seam; returned candidates remain advisory."""

    def evaluate(self, plan_frame: PlanFrame) -> NextStepCandidate:
        ...


class SteeringDomainError(RuntimeError):
    """Base error for long-lived Steering truth operations."""


class SteeringInvariantViolation(SteeringDomainError):
    """Raised when admitted Steering truth would violate its lineage."""


class StaleSteeringCandidate(SteeringInvariantViolation):
    """A candidate no longer matches the exact current governed basis."""


class StaleSemanticStepCandidate(SteeringInvariantViolation):
    """A semantic candidate no longer matches the current governed input."""


class SteeringRecordNotFound(SteeringDomainError):
    """Raised when a required Steering record does not exist."""
