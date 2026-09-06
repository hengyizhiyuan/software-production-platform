"""Provider-neutral Work Interaction and pre-Work understanding contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InteractionCondition(StrEnum):
    OPEN = "OPEN"
    ARCHIVED = "ARCHIVED"


class InteractionActor(StrEnum):
    HUMAN = "HUMAN"
    WATT = "WATT"


class InterpretationMeaningKind(StrEnum):
    CONTEXT = "CONTEXT"
    FACT = "FACT"
    CORRECTION = "CORRECTION"
    CONSTRAINT = "CONSTRAINT"
    REQUEST = "REQUEST"
    PREFERENCE = "PREFERENCE"
    QUESTION = "QUESTION"
    DECISION_INPUT = "DECISION_INPUT"
    FEEDBACK = "FEEDBACK"
    OBJECTIVE_OR_SCOPE_CHANGE = "OBJECTIVE_OR_SCOPE_CHANGE"
    NEW_WORK_CANDIDATE = "NEW_WORK_CANDIDATE"


class WorkAdmissionReadinessStatus(StrEnum):
    NOT_READY = "NOT_READY"
    READY = "READY"
    BLOCKED = "BLOCKED"


class InteractionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    interaction_id: UUID
    sequence: int = Field(ge=1)
    actor: InteractionActor
    source: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    work_focus_id: UUID | None = None
    created_at: datetime


class Interaction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    condition: InteractionCondition
    current_work_id: UUID | None = None
    created_by: str = Field(min_length=1, max_length=255)
    updated_by: str = Field(min_length=1, max_length=255)
    created_at: datetime
    updated_at: datetime


class InterpretationMeaning(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: InterpretationMeaningKind
    statement: str = Field(min_length=1)
    source_record_ids: tuple[UUID, ...] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1)
    clarification_required: bool = False


class WorkAdmissionReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: WorkAdmissionReadinessStatus
    profile: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    satisfied_requirements: tuple[str, ...]
    missing_information: tuple[str, ...]
    unresolved_material_questions: tuple[str, ...]
    reasons: tuple[str, ...] = Field(min_length=1)
    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def ready_has_no_blockers(self) -> "WorkAdmissionReadiness":
        if self.status is WorkAdmissionReadinessStatus.READY and (
            self.missing_information or self.unresolved_material_questions
        ):
            raise ValueError("READY assessment cannot retain material blockers")
        return self


class InteractionInterpretationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    interaction: Interaction
    records: tuple[InteractionRecord, ...] = Field(min_length=1)
    prior_assessment: "InteractionAssessment | None" = None
    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class InteractionAssessmentCandidate(BaseModel):
    """Advisory interpretation; application admission establishes persisted truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    interpreted_motive: str | None = None
    desired_outcome: str | None = None
    candidate_context: tuple[str, ...] = ()
    candidate_constraints: tuple[str, ...] = ()
    current_requests: tuple[str, ...] = ()
    unresolved_material_questions: tuple[str, ...] = ()
    meanings: tuple[InterpretationMeaning, ...] = ()
    natural_response: str = Field(min_length=1)
    provider_identity: str = Field(min_length=1, max_length=255)
    model_identity: str | None = Field(default=None, max_length=255)


class InteractionAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    interaction_id: UUID
    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    basis_last_sequence: int = Field(ge=1)
    interpreted_motive: str | None = None
    desired_outcome: str | None = None
    candidate_context: tuple[str, ...]
    candidate_constraints: tuple[str, ...]
    current_requests: tuple[str, ...]
    unresolved_material_questions: tuple[str, ...]
    meanings: tuple[InterpretationMeaning, ...]
    natural_response: str
    readiness: WorkAdmissionReadiness
    provider_identity: str
    model_identity: str | None = None
    schema_version: str
    created_at: datetime


class WorkRealityRevision(BaseModel):
    """Immutable governed Work truth admitted from one exact Interaction basis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    work_id: UUID
    revision_number: int = Field(ge=1)
    previous_revision_id: UUID | None = None
    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    revision_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_interaction_id: UUID
    source_assessment_id: UUID
    motive: str = Field(min_length=1)
    desired_outcome: str = Field(min_length=1)
    context_facts: tuple[str, ...]
    constraints: tuple[str, ...]
    requests: tuple[str, ...]
    engineering_scope_id: UUID
    engineering_resource_id: UUID
    scope_basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    repository_identity: str = Field(min_length=1)
    repository_ref: str = Field(min_length=1)
    source_baseline_id: UUID
    source_revision: str = Field(min_length=1)
    governance_record_id: UUID
    supporting_references: tuple[str, ...]
    change_set: tuple[str, ...]
    rationale: str = Field(min_length=1)
    admitted_by: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    created_at: datetime


class SharedUnderstanding(BaseModel):
    """Rebuildable projection; never a separately persisted source of truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    interaction: Interaction
    records: tuple[InteractionRecord, ...]
    latest_assessment: InteractionAssessment | None
    human_said: tuple[str, ...]
    interpreted_motive: str | None
    desired_outcome: str | None
    candidate_context: tuple[str, ...]
    candidate_constraints: tuple[str, ...]
    current_requests: tuple[str, ...]
    unresolved_material_questions: tuple[str, ...]
    readiness: WorkAdmissionReadiness | None
    candidate_engineering_resource_id: UUID | None = None
    candidate_repository_identity: str | None = None
    candidate_repository_ref: str | None = None
    candidate_scope_summary: str | None = None
    governed_work_id: UUID | None
    governed_revision: WorkRealityRevision | None = None


class WorkInteractionCapability(Protocol):
    def interpret(
        self, basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate: ...


class InteractionInvariantViolation(RuntimeError):
    """Raised when persisted interaction Reality does not permit an operation."""


class InteractionRecordNotFound(LookupError):
    """Raised when an Interaction identity is absent."""
