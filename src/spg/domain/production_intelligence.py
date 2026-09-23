"""Provider-neutral contracts for Watt production intelligence foundations.

These immutable contracts carry guidance and lineage.  They deliberately do not
own Work truth, execution authority, Steering progression, or Assurance results.
"""

from __future__ import annotations

from enum import StrEnum
from hashlib import sha256
import json
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from spg.domain.design_intent import DesignObjectType
from spg.domain.connectors import ExecutableCapability
from spg.domain.engineering_semantics import SemanticFactReference, SemanticRelation


class EngineeringActivity(StrEnum):
    DISCOVERY = "DISCOVERY"
    FEATURE_DELIVERY = "FEATURE_DELIVERY"
    BUG_RESOLUTION = "BUG_RESOLUTION"
    INCIDENT_RESPONSE = "INCIDENT_RESPONSE"
    ARCHITECTURE_DECISION = "ARCHITECTURE_DECISION"
    REFACTORING = "REFACTORING"
    INVESTIGATION = "INVESTIGATION"
    MIGRATION = "MIGRATION"
    OPTIMIZATION = "OPTIMIZATION"
    RELEASE = "RELEASE"


class TaskMode(StrEnum):
    GENERAL = "GENERAL"
    DESIGN_ARTIFACT = "DESIGN_ARTIFACT"
    IMPLEMENTATION = "IMPLEMENTATION"


class EvidenceCategory(StrEnum):
    HUMAN = "HUMAN"
    ENGINEERING = "ENGINEERING"
    ASSURANCE = "ASSURANCE"


class ContextSource(StrEnum):
    RESPONSE_CONTRACT = "RESPONSE_CONTRACT"
    SYSTEM_CAPABILITY_REALITY = "SYSTEM_CAPABILITY_REALITY"
    SEMANTIC_TRUTH = "SEMANTIC_TRUTH"
    WORK_REALITY = "WORK_REALITY"
    ECF_REALITY = "ECF_REALITY"
    DECISION_MEMORY = "DECISION_MEMORY"
    DOMAIN_PATTERN = "DOMAIN_PATTERN"
    SOP = "SOP"
    GUARDIAN_EVIDENCE = "GUARDIAN_EVIDENCE"


class SystemCapabilityReality(BaseModel):
    """Versioned truth about Watt's own role and evidenced capability boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: Literal["Watt"] = "Watt"
    system_type: Literal["AI_NATIVE_SOFTWARE_PRODUCTION_SYSTEM"] = (
        "AI_NATIVE_SOFTWARE_PRODUCTION_SYSTEM"
    )
    version: str = Field(min_length=1)
    capabilities: tuple[str, ...] = Field(min_length=1)
    production_object_types: tuple[DesignObjectType, ...] = Field(min_length=1)
    boundaries: tuple[str, ...] = Field(min_length=1)
    authority: Literal["SYSTEM_CAPABILITY_REALITY"] = "SYSTEM_CAPABILITY_REALITY"
    provenance: tuple[str, ...] = Field(min_length=1)
    executable_capabilities: tuple[ExecutableCapability, ...] = ()

    @property
    def content_fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class DecisionTraceStatus(StrEnum):
    PROPOSED = "PROPOSED"
    ADMITTED = "ADMITTED"
    SUPERSEDED = "SUPERSEDED"


class PatternEvidenceDirection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    statement: str = Field(min_length=1)
    provenance_reference: str = Field(min_length=1)


class PatternOption(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str = Field(min_length=1)
    benefits: tuple[str, ...] = ()
    costs_and_risks: tuple[str, ...] = ()
    applicability: tuple[str, ...] = ()


class PatternDimension(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    consideration: str = Field(min_length=1)
    options: tuple[PatternOption, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_distinct_options(self) -> Self:
        keys = tuple(option.key for option in self.options)
        if len(keys) != len(set(keys)):
            raise ValueError("Pattern option keys must be unique within a dimension")
        return self


class PatternActivationMetadata(BaseModel):
    """Structured applicability metadata, never phrase matching or authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    activities: tuple[EngineeringActivity, ...] = Field(min_length=1)
    semantic_relations: tuple[SemanticRelation, ...] = ()
    subject_prefixes: tuple[str, ...] = ()
    requires_semantic_truth: bool = False


class EngineeringPattern(BaseModel):
    """Reusable decision-space guidance, separate from current project truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    pattern_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    version: str = Field(min_length=1)
    title: str = Field(min_length=1)
    decision_space: str = Field(min_length=1)
    activation: PatternActivationMetadata
    dimensions: tuple[PatternDimension, ...] = Field(min_length=1)
    evidence_direction: tuple[PatternEvidenceDirection, ...] = ()
    provenance_references: tuple[str, ...] = Field(min_length=1)
    authority: Literal["ADVISORY_ONLY"] = "ADVISORY_ONLY"


class EvidenceExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expectation_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    category: EvidenceCategory
    statement: str = Field(min_length=1)
    owner_boundary: str = Field(min_length=1)


class SopCheckpoint(BaseModel):
    """An evidence expectation point, never an implicit approval gate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    checkpoint_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    purpose: str = Field(min_length=1)
    evidence_expectations: tuple[EvidenceExpectation, ...] = Field(min_length=1)
    authority_effect: Literal["NONE"] = "NONE"


class SopActivityGuidance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    activity: EngineeringActivity
    applicability: str = Field(min_length=1)
    checkpoints: tuple[SopCheckpoint, ...] = Field(min_length=1)


class SoftwareProductionSop(BaseModel):
    """Engineering-activity guidance; Steering remains the progression owner."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sop_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    version: str = Field(min_length=1)
    title: str = Field(min_length=1)
    activities: tuple[SopActivityGuidance, ...] = Field(min_length=1)
    authority: Literal["GUIDANCE_ONLY"] = "GUIDANCE_ONLY"

    @model_validator(mode="after")
    def require_distinct_activity_guidance(self) -> Self:
        activities = tuple(item.activity for item in self.activities)
        if len(activities) != len(set(activities)):
            raise ValueError("SOP may define each Engineering Activity only once")
        return self


class EvidenceReference(BaseModel):
    """Attributable evidence link; its category does not grant authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: EvidenceCategory
    source_reference: str = Field(min_length=1)
    subject_reference: str = Field(min_length=1)
    basis_reference: str = Field(min_length=1)
    assertion: str = Field(min_length=1)
    authority_domain: str = Field(min_length=1)


class ReasoningSummary(BaseModel):
    """Useful bounded rationale; raw chain-of-thought is intentionally absent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str = Field(min_length=1)
    considered_factors: tuple[str, ...] = Field(min_length=1)
    uncertainty: tuple[str, ...] = ()
    raw_chain_of_thought_stored: Literal[False] = False


class DecisionTrace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: UUID
    context_reference: str = Field(min_length=1)
    considered_options: tuple[str, ...] = Field(min_length=1)
    selected_direction: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    authority_reference: str = Field(min_length=1)
    evidence_references: tuple[EvidenceReference, ...] = ()
    status: DecisionTraceStatus


class ContextCandidate(BaseModel):
    """A source-owned candidate presented to the Context Orchestrator."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str = Field(min_length=1)
    source: ContextSource
    content: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    authority: str = Field(min_length=1)
    provenance: tuple[str, ...] = Field(min_length=1)
    priority: int = Field(ge=0, le=100)
    authoritative: bool = False
    required: bool = False

    @model_validator(mode="after")
    def guidance_cannot_become_truth(self) -> Self:
        if self.source in {ContextSource.DOMAIN_PATTERN, ContextSource.SOP} and (
            self.authoritative or self.required
        ):
            raise ValueError("Pattern and SOP context must remain optional guidance")
        return self


class ContextBudget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_items: int = Field(default=12, ge=1, le=64)
    max_characters: int = Field(default=6000, ge=256, le=50000)
    max_items_per_source: int = Field(default=4, ge=1, le=16)


class CognitiveContextItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str = Field(min_length=1)
    source: ContextSource
    content: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    authority: str = Field(min_length=1)
    provenance: tuple[str, ...] = Field(min_length=1)
    priority: int = Field(ge=0, le=100)
    authoritative: bool


class CognitiveContextPackage(BaseModel):
    """Bounded selection for one interaction/task, not a new Reality owner."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    purpose: str = Field(min_length=1)
    activity: EngineeringActivity
    budget: ContextBudget
    items: tuple[CognitiveContextItem, ...]
    omitted_candidate_count: int = Field(ge=0)
    selected_pattern_ids: tuple[str, ...] = ()
    sop_reference: str | None = None

    @model_validator(mode="after")
    def obey_budget(self) -> Self:
        if len(self.items) > self.budget.max_items:
            raise ValueError("Cognitive context item budget exceeded")
        if sum(len(item.content) for item in self.items) > self.budget.max_characters:
            raise ValueError("Cognitive context character budget exceeded")
        ids = tuple(item.item_id for item in self.items)
        if len(ids) != len(set(ids)):
            raise ValueError("Cognitive context item identities must be unique")
        return self

    @property
    def content_fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class TaskContextReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: ContextSource
    reference: str = Field(min_length=1)
    authority: str = Field(min_length=1)


class TaskContract(BaseModel):
    """Explicit execution obligation projected into a PWU Completion Contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_contract_id: UUID
    activity: EngineeringActivity
    task_mode: TaskMode = TaskMode.GENERAL
    objective: str = Field(min_length=1)
    relevant_context: tuple[TaskContextReference, ...] = Field(min_length=1)
    scope: tuple[str, ...] = Field(min_length=1)
    constraints: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    acceptance_meaning: tuple[str, ...] = Field(min_length=1)
    evidence_requirements: tuple[EvidenceExpectation, ...] = Field(min_length=1)
    out_of_scope: tuple[str, ...] = Field(min_length=1)
    authority_lineage: tuple[str, ...] = Field(min_length=1)
    required_prerequisites: tuple[str, ...] = ()
    prerequisite_evidence: tuple[str, ...] = ()
    semantic_fact_references: tuple[SemanticFactReference, ...] = ()
    sop_reference: str | None = None
    reasoning_summary: ReasoningSummary
    decision_trace: DecisionTrace
    evidence_lineage: tuple[EvidenceReference, ...] = ()

    @model_validator(mode="after")
    def preserve_semantic_lineage(self) -> Self:
        fact_ids = {item.fact_id for item in self.semantic_fact_references}
        evidence_fact_ids = {
            item.subject_reference.removeprefix("semantic-fact:")
            for item in self.evidence_lineage
            if item.subject_reference.startswith("semantic-fact:")
        }
        if fact_ids and not {str(item) for item in fact_ids}.issubset(evidence_fact_ids):
            raise ValueError("Task Contract must preserve evidence lineage for semantic facts")
        if self.required_prerequisites and not self.prerequisite_evidence:
            raise ValueError(
                "Task Contract prerequisites require exact persisted evidence"
            )
        return self

    @property
    def content_fingerprint(self) -> str:
        return _fingerprint(
            self.model_dump(mode="json", exclude={"task_contract_id"})
        )


def _fingerprint(value: object) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return sha256(canonical).hexdigest()
