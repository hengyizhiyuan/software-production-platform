"""Provider-neutral contracts for long-lived Reality-driven Plan Steering truth."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
from typing import Protocol, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class SteeringHistoryEventType(StrEnum):
    STEP_TRANSITION = "STEP_TRANSITION"
    STEP_ELABORATION = "STEP_ELABORATION"
    PLAN_REVISION = "PLAN_REVISION"


class RealityReferenceKind(StrEnum):
    WORK = "WORK"
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


class SteeringAttentionReason(StrEnum):
    MOTIVE_OR_OUTCOME_AMBIGUITY = "MOTIVE_OR_OUTCOME_AMBIGUITY"
    MAJOR_PRODUCT_OR_ARCHITECTURE_DECISION = (
        "MAJOR_PRODUCT_OR_ARCHITECTURE_DECISION"
    )
    SCOPE_OR_AUTHORITY_EXPANSION = "SCOPE_OR_AUTHORITY_EXPANSION"
    MATERIAL_RISK_OR_COST_DECISION = "MATERIAL_RISK_OR_COST_DECISION"
    PRODUCT_ACCEPTANCE_REQUIRED = "PRODUCT_ACCEPTANCE_REQUIRED"


class SteeringAuthorityAssessment(StrEnum):
    WITHIN_AUTHORITY = "WITHIN_AUTHORITY"
    UNCERTAIN = "UNCERTAIN"
    EXPANDS_AUTHORITY = "EXPANDS_AUTHORITY"


class PlanFrameBlockerKind(StrEnum):
    PRODUCTION_NOT_PRODUCED = "PRODUCTION_NOT_PRODUCED"
    VERIFICATION_NOT_PASSING = "VERIFICATION_NOT_PASSING"
    REPOSITORY_INTEGRATION_NOT_CONVERGED = "REPOSITORY_INTEGRATION_NOT_CONVERGED"


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


class SteeringStepSpec(BaseModel):
    """Already-governed input for one ordered Steering Step."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: SteeringStepType
    objective: str = Field(min_length=1)
    completion_condition: str = Field(min_length=1)
    state: SteeringStepState = SteeringStepState.KNOWN


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
    has_material_revision: bool


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


class SteeringRecordNotFound(SteeringDomainError):
    """Raised when a required Steering record does not exist."""
