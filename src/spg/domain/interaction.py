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


class InteractionTurnStatus(StrEnum):
    """Durable user-experience state for one Human-to-Watt exchange."""

    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


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


class WorkFocusClassification(StrEnum):
    ON_TOPIC = "ON_TOPIC"
    RELEVANT_EXPLORATION = "RELEVANT_EXPLORATION"
    SIDE_QUESTION = "SIDE_QUESTION"
    MATERIAL_BRANCH = "MATERIAL_BRANCH"
    UNRELATED_NEW_DEMAND = "UNRELATED_NEW_DEMAND"


class WorkImpactDisposition(StrEnum):
    NO_GOVERNED_CHANGE = "NO_GOVERNED_CHANGE"
    CURRENT_CYCLE_REMAINS_VALID = "CURRENT_CYCLE_REMAINS_VALID"
    DEFER_TO_PRODUCTION_BOUNDARY = "DEFER_TO_PRODUCTION_BOUNDARY"
    CURRENT_RESULT_MAY_BE_INSUFFICIENT = "CURRENT_RESULT_MAY_BE_INSUFFICIENT"
    HUMAN_GOVERNANCE_REQUIRED = "HUMAN_GOVERNANCE_REQUIRED"
    NEW_WORK_RECOMMENDED = "NEW_WORK_RECOMMENDED"


class WorkRevisionAdmissionStatus(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING_HUMAN = "PENDING_HUMAN"
    ADMITTED = "ADMITTED"
    REJECTED = "REJECTED"
    REFINEMENT_REQUESTED = "REFINEMENT_REQUESTED"
    NEW_WORK_RECOMMENDED = "NEW_WORK_RECOMMENDED"


class WorkSatisfactionState(StrEnum):
    """Current truth about whether the focused Work objective is satisfied."""

    NO_FOCUSED_WORK = "NO_FOCUSED_WORK"
    IN_PROGRESS = "IN_PROGRESS"
    CURRENTLY_SATISFIED = "CURRENTLY_SATISFIED"


class WorkTransitionChoice(StrEnum):
    """Human-owned disposition of one persisted new-Work recommendation."""

    PENDING_HUMAN = "PENDING_HUMAN"
    CONTINUE_CURRENT_WORK = "CONTINUE_CURRENT_WORK"
    START_NEW_WORK = "START_NEW_WORK"
    DISMISSED = "DISMISSED"


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
    supporting_references: tuple[str, ...] = ()
    created_at: datetime


class Interaction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    condition: InteractionCondition
    current_work_id: UUID | None = None
    selected_design_schema_identity: str | None = None
    selected_design_schema_version: str | None = None
    design_schema_selection_rationale: str | None = None
    created_by: str = Field(min_length=1, max_length=255)
    updated_by: str = Field(min_length=1, max_length=255)
    created_at: datetime
    updated_at: datetime


class InteractionTurn(BaseModel):
    """One durable asynchronous exchange; future waiting states can extend it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    interaction_id: UUID
    request_record_id: UUID
    assessment_id: UUID | None = None
    status: InteractionTurnStatus
    failure_code: str | None = None
    failure_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime


class ConversationMessage(BaseModel):
    """User-experience history linked to, but never replacing, governed truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    interaction_id: UUID
    turn_id: UUID | None = None
    sequence: int = Field(ge=1)
    actor: InteractionActor
    content: str = Field(min_length=1)
    processing_status: InteractionTurnStatus
    interaction_record_id: UUID | None = None
    interpretation_assessment_id: UUID | None = None
    design_result_references: tuple[str, ...] = ()
    governance_event_references: tuple[str, ...] = ()
    supporting_references: tuple[str, ...] = ()
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
    active_work_context: "ActiveWorkInterpretationContext | None" = None
    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class ActiveWorkInterpretationContext(BaseModel):
    """Exact governed Work/Plan/production basis supplied to interpretation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    work_revision: "WorkRealityRevision"
    engineering_scope_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    steering_plan_revision_id: UUID | None = None
    steering_plan_revision_number: int | None = Field(default=None, ge=1)
    current_steering_step_id: UUID | None = None
    current_steering_step_type: str | None = None
    active_production_binding_id: UUID | None = None
    active_cycle_work_revision_id: UUID | None = None
    active_cycle_number: int | None = Field(default=None, ge=1)
    relevant_reality_references: tuple[str, ...] = ()
    satisfaction_state: WorkSatisfactionState = WorkSatisfactionState.IN_PROGRESS


class WorkEvolutionCandidateChange(BaseModel):
    """Candidate materialized Work state; never governed truth by itself."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    changed_fields: tuple[str, ...]
    motive: str
    desired_outcome: str
    context_facts: tuple[str, ...]
    constraints: tuple[str, ...]
    requests: tuple[str, ...]
    scope_change_required: bool = False


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
    focus_classification: WorkFocusClassification | None = None
    impact_disposition: WorkImpactDisposition | None = None
    supporting_references: tuple[str, ...] = ()
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
    focus_classification: WorkFocusClassification | None = None
    impact_disposition: WorkImpactDisposition | None = None
    candidate_change: WorkEvolutionCandidateChange | None = None
    basis_work_revision_id: UUID | None = None
    basis_steering_plan_revision_id: UUID | None = None
    basis_steering_step_id: UUID | None = None
    basis_active_runtime_binding_id: UUID | None = None
    supporting_references: tuple[str, ...] = ()
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
    source_record_ids: tuple[UUID, ...] = ()
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


class WorkTransitionRecord(BaseModel):
    """Append-preserving provenance for a suggested change of Work focus."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    interaction_id: UUID
    source_record_id: UUID
    source_assessment_id: UUID
    originating_work_id: UUID
    target_work_id: UUID | None = None
    reason: str = Field(min_length=1)
    focus_classification: WorkFocusClassification
    impact_disposition: WorkImpactDisposition
    choice: WorkTransitionChoice = WorkTransitionChoice.PENDING_HUMAN
    decided_by: str | None = None
    decision_rationale: str | None = None
    decided_at: datetime | None = None
    created_at: datetime


class SharedUnderstanding(BaseModel):
    """Rebuildable projection; never a separately persisted source of truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    interaction: Interaction
    records: tuple[InteractionRecord, ...]
    conversation_messages: tuple[ConversationMessage, ...] = ()
    turns: tuple[InteractionTurn, ...] = ()
    latest_assessment: InteractionAssessment | None
    latest_assessment_current: bool = True
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
    current_work_focus: str | None = None
    focus_classification: WorkFocusClassification | None = None
    impact_disposition: WorkImpactDisposition | None = None
    candidate_change: WorkEvolutionCandidateChange | None = None
    work_revision_admission_status: WorkRevisionAdmissionStatus = (
        WorkRevisionAdmissionStatus.NOT_APPLICABLE
    )
    active_cycle_work_revision_id: UUID | None = None
    active_cycle_impact_disposition: WorkImpactDisposition | None = None
    work_satisfaction_state: WorkSatisfactionState = (
        WorkSatisfactionState.NO_FOCUSED_WORK
    )
    interaction_relationship_state: InteractionCondition = InteractionCondition.OPEN
    work_focus_history: tuple[UUID, ...] = ()
    latest_work_transition: WorkTransitionRecord | None = None
    new_work_formation_pending: bool = False
    selected_design_schema_identity: str | None = None
    selected_design_schema_version: str | None = None
    design_schema_selection_rationale: str | None = None
    design_stage: str | None = None
    design_next_focus: str | None = None
    design_focus_rationale: str | None = None
    design_facilitation_strategy: str | None = None
    design_progress_narrative: str | None = None


class WorkInteractionCapability(Protocol):
    def interpret(
        self, basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate: ...


class InteractionInvariantViolation(RuntimeError):
    """Raised when persisted interaction Reality does not permit an operation."""


class InteractionRecordNotFound(LookupError):
    """Raised when an Interaction identity is absent."""
