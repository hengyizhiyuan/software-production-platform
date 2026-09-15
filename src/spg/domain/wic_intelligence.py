"""Progressive WIC semantics and policy-attributed governance candidates."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


SEMANTIC_POLICY_REVISION = "wic-semantic-policy-v1"
QUESTION_POLICY_REVISION = "wic-question-value-v1"
READINESS_PROFILE_REVISION = "wic-transition-readiness-v1"


class SemanticCategory(StrEnum):
    MOTIVE = "MOTIVE"
    DESIRED_OUTCOME = "DESIRED_OUTCOME"
    FACT = "FACT"
    CONSTRAINT = "CONSTRAINT"
    REQUEST = "REQUEST"
    DESIGN_FRAME = "DESIGN_FRAME"
    HUMAN_DECISION = "HUMAN_DECISION"
    WORK_CANDIDATE = "WORK_CANDIDATE"


class SemanticDeltaOperation(StrEnum):
    ADDED = "ADDED"
    REVISED = "REVISED"
    SUPERSEDED = "SUPERSEDED"
    REMOVED = "REMOVED"
    NO_CHANGE = "NO_CHANGE"


class SemanticAuthority(StrEnum):
    ADVISORY = "ADVISORY"
    HUMAN_OWNED = "HUMAN_OWNED"
    GOVERNED_REALITY = "GOVERNED_REALITY"


class GovernanceCandidateKind(StrEnum):
    NO_GOVERNED_CHANGE = "NO_GOVERNED_CHANGE"
    WORK_FORMATION_PROPOSAL = "WORK_FORMATION_PROPOSAL"
    WORK_REVISION_PROPOSAL = "WORK_REVISION_PROPOSAL"
    NEW_MOTIVE_CANDIDATE = "NEW_MOTIVE_CANDIDATE"
    HUMAN_DECISION_REQUIRED = "HUMAN_DECISION_REQUIRED"
    CONVERSATION_ONLY = "CONVERSATION_ONLY"


class PatternSignal(StrEnum):
    EXPLICIT_CORRECTION = "EXPLICIT_CORRECTION"
    BOUNDED_CHANGE = "BOUNDED_CHANGE"
    CONSTRAINT_ADDITION = "CONSTRAINT_ADDITION"
    DIRECT_QUESTION = "DIRECT_QUESTION"
    RECOMMENDATION_REQUEST = "RECOMMENDATION_REQUEST"
    NEW_LONG_LIVED_OBJECT = "NEW_LONG_LIVED_OBJECT"
    HIGH_IMPACT_AMBIGUITY = "HIGH_IMPACT_AMBIGUITY"
    BROWNFIELD_REALITY_CONFLICT = "BROWNFIELD_REALITY_CONFLICT"


class InferenceDisposition(StrEnum):
    SAFE_REVERSIBLE_INFERENCE = "SAFE_REVERSIBLE_INFERENCE"
    HUMAN_OWNED_DECISION = "HUMAN_OWNED_DECISION"
    NO_INFERENCE = "NO_INFERENCE"


class QuestionDisposition(StrEnum):
    ASK_HUMAN_NOW = "ASK_HUMAN_NOW"
    CARRY_AS_EXPLICIT_ASSUMPTION = "CARRY_AS_EXPLICIT_ASSUMPTION"
    INFER_REVERSIBLY = "INFER_REVERSIBLY"
    DEFER_UNTIL_RELEVANT = "DEFER_UNTIL_RELEVANT"
    ALREADY_RESOLVED = "ALREADY_RESOLVED"
    NOT_MATERIAL = "NOT_MATERIAL"


class ReadinessTarget(StrEnum):
    WORK_FORMATION = "WORK_FORMATION"
    WORK_REVISION = "WORK_REVISION"
    DESIGN_PROGRESSION = "DESIGN_PROGRESSION"


class TransitionReadinessStatus(StrEnum):
    READY = "READY"
    NOT_READY = "NOT_READY"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SemanticDelta(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    category: SemanticCategory
    operation: SemanticDeltaOperation
    value: str | None = None
    prior_value: str | None = None
    source_record_ids: tuple[UUID, ...] = Field(min_length=1)
    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    prior_assessment_id: UUID | None = None
    supersedes_delta_ids: tuple[UUID, ...] = ()
    confidence: float = Field(ge=0, le=1)
    rationale: str
    authority: SemanticAuthority = SemanticAuthority.ADVISORY


class QuestionEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    question: str
    affected_dimensions: tuple[str, ...]
    answer_already_available: bool
    safe_reversible_assumption_available: bool
    watt_authorized_to_choose: bool
    blocks_next_governed_step: bool
    cognitive_cost: Literal["LOW", "MEDIUM", "HIGH"]
    decision_value: int = Field(ge=0, le=100)
    disposition: QuestionDisposition
    rationale: str


class TransitionReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target: ReadinessTarget
    status: TransitionReadinessStatus
    satisfied_evidence: tuple[str, ...] = ()
    missing_material_evidence: tuple[str, ...] = ()
    unresolved_human_decisions: tuple[str, ...] = ()
    explicit_assumptions: tuple[str, ...] = ()
    material_risks: tuple[str, ...] = ()
    useful_work_may_continue: bool
    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    profile_revision: str = READINESS_PROFILE_REVISION
    authority: Literal["ADVISORY_ONLY"] = "ADVISORY_ONLY"


class ArtifactRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_kind: str
    intended_consumer: str
    protected_obligation: str
    required_now: bool
    rationale: str


class ProgressiveSemanticStructure(BaseModel):
    """One basis, increasingly committed interpretations; never separate truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_record_ids: tuple[UUID, ...] = Field(min_length=1)
    reception_meanings: tuple[str, ...]
    working_motive: str | None = None
    working_desired_outcome: str | None = None
    working_facts: tuple[str, ...] = ()
    working_constraints: tuple[str, ...] = ()
    working_requests: tuple[str, ...] = ()
    explicit_assumptions: tuple[str, ...] = ()
    unresolved_human_decisions: tuple[str, ...] = ()
    deltas: tuple[SemanticDelta, ...]
    pattern_signals: tuple[PatternSignal, ...]
    inference_disposition: InferenceDisposition
    questions: tuple[QuestionEvaluation, ...]
    selected_question: str | None = None
    governance_candidate: GovernanceCandidateKind
    readiness: tuple[TransitionReadiness, ...]
    artifact_recommendation: ArtifactRecommendation | None = None
    factual_contradictions: tuple[str, ...] = ()
    semantic_policy_revision: str = SEMANTIC_POLICY_REVISION
    question_policy_revision: str = QUESTION_POLICY_REVISION

    @model_validator(mode="after")
    def selected_question_is_askable(self) -> "ProgressiveSemanticStructure":
        askable = [item.question for item in self.questions if item.disposition is QuestionDisposition.ASK_HUMAN_NOW]
        if self.selected_question is not None and self.selected_question not in askable:
            raise ValueError("Selected question must be ASK_HUMAN_NOW")
        if len(askable) > 1:
            raise ValueError("v1 policy may surface at most one highest-value question")
        return self
