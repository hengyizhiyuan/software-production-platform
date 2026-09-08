"""Provider-neutral contracts for reconstructable guided product/system design."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from spg.domain.steering import RealityReference


class DesignProcessCondition(StrEnum):
    ACTIVE = "ACTIVE"
    READY = "READY"
    COMPLETE = "COMPLETE"


class DesignAgendaRevisionCondition(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"


class DesignIssueState(StrEnum):
    OPEN = "OPEN"
    SATISFIED = "SATISFIED"
    SKIPPED = "SKIPPED"
    REOPENED = "REOPENED"


class DesignAuthorityRelevance(StrEnum):
    ROUTINE = "ROUTINE"
    MATERIAL_HUMAN_DECISION = "MATERIAL_HUMAN_DECISION"
    AUTHORITY_BOUNDARY = "AUTHORITY_BOUNDARY"


class DesignOutputClass(StrEnum):
    SHARED_UNDERSTANDING = "SHARED_UNDERSTANDING"
    GOVERNED_DESIGN_DIRECTION = "GOVERNED_DESIGN_DIRECTION"
    GOVERNED_HUMAN_DECISION = "GOVERNED_HUMAN_DECISION"
    REVIEWABLE_PRODUCTION_PROPOSAL = "REVIEWABLE_PRODUCTION_PROPOSAL"


class DesignReadinessState(StrEnum):
    READY = "READY"
    NOT_READY = "NOT_READY"


class DesignFacilitationStrategy(StrEnum):
    CLARIFY = "CLARIFY"
    SUMMARIZE_UNDERSTANDING = "SUMMARIZE_UNDERSTANDING"
    PRESENT_ALTERNATIVES = "PRESENT_ALTERNATIVES"
    EXPLAIN_TRADE_OFFS = "EXPLAIN_TRADE_OFFS"
    PROPOSE_NEXT_DESIGN_STEP = "PROPOSE_NEXT_DESIGN_STEP"
    REQUEST_HUMAN_DECISION = "REQUEST_HUMAN_DECISION"


class DesignSchemaDefinition(BaseModel):
    """Versioned built-in methodology asset, independent of any process instance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: str = Field(min_length=1)
    version: str = Field(min_length=1)
    title: str = Field(min_length=1)
    applicability: str = Field(min_length=1)
    issues: tuple["DesignIssue", ...] = Field(min_length=1)


class DesignIssue(BaseModel):
    """One semantic issue in an agenda revision; current focus remains Plan truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    applicability: str = Field(min_length=1)
    prerequisite_keys: tuple[str, ...] = ()
    completion_condition: str = Field(min_length=1)
    authority_relevance: DesignAuthorityRelevance
    required_output: DesignOutputClass
    critical: bool = True
    state: DesignIssueState = DesignIssueState.OPEN
    skip_rationale: str | None = None
    reopen_rationale: str | None = None
    steering_step_id: UUID | None = None
    admitted_semantic_result_id: UUID | None = None
    provenance_refs: tuple[RealityReference, ...] = ()

    @field_validator("prerequisite_keys")
    @classmethod
    def normalize_prerequisites(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value))

    @model_validator(mode="after")
    def require_state_rationale(self) -> Self:
        if self.key in self.prerequisite_keys:
            raise ValueError("A design issue cannot depend on itself")
        if self.state is DesignIssueState.SKIPPED and not self.skip_rationale:
            raise ValueError("A skipped design issue requires rationale")
        if self.state is DesignIssueState.REOPENED and not self.reopen_rationale:
            raise ValueError("A reopened design issue requires rationale")
        if self.state is DesignIssueState.SATISFIED and (
            self.admitted_semantic_result_id is None
        ):
            raise ValueError("A satisfied design issue requires governed result evidence")
        return self


class GuidedDesignProcessRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    work_id: UUID
    schema_identity: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    schema_selection_rationale: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    condition: DesignProcessCondition
    basis_work_reality_revision_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class DesignAgendaRevisionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    process_id: UUID
    work_id: UUID
    revision_number: int = Field(ge=1)
    condition: DesignAgendaRevisionCondition
    supersedes_revision_id: UUID | None = None
    basis_work_reality_revision_id: UUID | None = None
    rationale: str = Field(min_length=1)
    reality_refs: tuple[RealityReference, ...]
    issues: tuple[DesignIssue, ...] = Field(min_length=1)
    created_at: datetime

    @model_validator(mode="after")
    def require_coherent_issue_graph(self) -> Self:
        keys = tuple(issue.key for issue in self.issues)
        if len(keys) != len(set(keys)):
            raise ValueError("Design agenda issue keys must be unique")
        known = set(keys)
        for issue in self.issues:
            if not set(issue.prerequisite_keys) <= known:
                raise ValueError("Design issue prerequisites must exist in the agenda")
        return self


class DesignReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: DesignReadinessState
    blockers: tuple[str, ...]
    basis_refs: tuple[RealityReference, ...]


class GuidedDesignProjection(BaseModel):
    """Product-facing view derived from persisted process, agenda, and Plan truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    work_id: UUID
    process_id: UUID
    process_objective: str
    schema_identity: str
    schema_version: str
    schema_selection_rationale: str
    agenda_revision_id: UUID
    agenda_revision_number: int
    current_focus_key: str | None
    current_focus: DesignIssue | None
    focus_rationale: str | None
    current_stage: str
    completed_areas: tuple[str, ...]
    unresolved_areas: tuple[str, ...]
    dependency_blockers: tuple[str, ...]
    facilitation_strategy: DesignFacilitationStrategy
    facilitation_guidance: str
    progress_narrative: str
    issues: tuple[DesignIssue, ...]
    resolved_count: int = Field(ge=0)
    total_applicable_count: int = Field(ge=1)
    readiness: DesignReadiness
    upcoming_transition: str | None = None


class GuidedDesignInvariantViolation(RuntimeError):
    """Raised when design process truth would diverge from governed Reality."""


class GuidedDesignRecordNotFound(LookupError):
    """Raised when an expected guided design record does not exist."""
