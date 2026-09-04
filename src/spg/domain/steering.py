"""Provider-neutral contracts for long-lived Reality-driven Plan Steering truth."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class RealityReference(BaseModel):
    """Stable identity of Reality owned outside the Steering Plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: RealityReferenceKind
    identity: UUID


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
        return self


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


class SteeringDomainError(RuntimeError):
    """Base error for long-lived Steering truth operations."""


class SteeringInvariantViolation(SteeringDomainError):
    """Raised when admitted Steering truth would violate its lineage."""


class SteeringRecordNotFound(SteeringDomainError):
    """Raised when a required Steering record does not exist."""
