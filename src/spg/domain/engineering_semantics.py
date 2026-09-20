"""Governed software-production semantic facts and neutral extraction contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


SemanticScalar: TypeAlias = str | int | float | bool
SemanticValue: TypeAlias = SemanticScalar | tuple[SemanticScalar, ...]


class NeutralExtractionKind(StrEnum):
    ORDERED_VALUES = "ORDERED_VALUES"
    QUANTITY = "QUANTITY"
    RANGE = "RANGE"
    COMPARISON = "COMPARISON"
    REFERENCE = "REFERENCE"
    BEHAVIOR = "BEHAVIOR"
    STATE_CHANGE = "STATE_CHANGE"
    SCOPE = "SCOPE"


class SemanticRelation(StrEnum):
    CARDINALITY = "CARDINALITY"
    EQUALITY = "EQUALITY"
    ORDERED_COMPONENT = "ORDERED_COMPONENT"
    BOUND = "BOUND"
    COMPARISON = "COMPARISON"
    MAPPING = "MAPPING"
    REFERENCE = "REFERENCE"
    PRECEDENCE = "PRECEDENCE"
    BEHAVIOR = "BEHAVIOR"
    STATE_TRANSITION = "STATE_TRANSITION"
    SCOPE = "SCOPE"
    ACCEPTANCE_ASSERTION = "ACCEPTANCE_ASSERTION"


class SemanticFactAuthority(StrEnum):
    HUMAN_EXPLICIT = "HUMAN_EXPLICIT"
    SYSTEM_INFERRED = "SYSTEM_INFERRED"


class SemanticEpistemicStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    WORKING_ASSUMPTION = "WORKING_ASSUMPTION"
    UNRESOLVED = "UNRESOLVED"
    SUPERSEDED = "SUPERSEDED"


class SemanticRoleOrigin(StrEnum):
    EXPLICIT = "EXPLICIT"
    INFERRED = "INFERRED"


class SemanticCandidateOperation(StrEnum):
    UPSERT = "UPSERT"
    REMOVE = "REMOVE"


class NeutralSemanticExtractionCandidate(BaseModel):
    """Provider-neutral syntax extraction before contextual role binding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    extraction_id: str = Field(min_length=1, max_length=64)
    kind: NeutralExtractionKind
    values: tuple[SemanticScalar, ...] = Field(min_length=1)
    unit: str | None = Field(default=None, max_length=64)
    source_record_id: UUID
    source_text: str = Field(min_length=1)
    explicit_roles: tuple[str | None, ...]

    @model_validator(mode="before")
    @classmethod
    def pad_unassigned_roles(cls, value):
        """Canonicalize omitted advisory roles without inventing product meaning."""

        if not isinstance(value, dict):
            return value
        values = value.get("values")
        roles = value.get("explicit_roles", ())
        if (
            isinstance(values, (list, tuple))
            and isinstance(roles, (list, tuple))
            and len(roles) < len(values)
        ):
            return {
                **value,
                "explicit_roles": (*roles, *((None,) * (len(values) - len(roles)))),
            }
        return value

    @model_validator(mode="after")
    def roles_align_with_values(self) -> "NeutralSemanticExtractionCandidate":
        if len(self.explicit_roles) != len(self.values):
            raise ValueError("Neutral extraction roles must align with ordered values")
        return self


class EngineeringSemanticFactCandidate(BaseModel):
    """Contextual product-semantic proposal; admission happens separately."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str = Field(min_length=1, max_length=64)
    operation: SemanticCandidateOperation = SemanticCandidateOperation.UPSERT
    subject: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,127}$")
    relation: SemanticRelation
    value: SemanticValue
    unit: str | None = Field(default=None, max_length=64)
    scope: str | None = Field(default=None, max_length=255)
    qualifiers: dict[str, SemanticScalar] = Field(default_factory=dict)
    authority: SemanticFactAuthority
    epistemic_status: SemanticEpistemicStatus
    source_record_ids: tuple[UUID, ...] = Field(min_length=1)
    source_text: str = Field(min_length=1)
    source_extraction_ids: tuple[str, ...] = ()
    role_origin: SemanticRoleOrigin
    supersedes_fact_ids: tuple[UUID, ...] = ()

    @model_validator(mode="after")
    def candidate_authority_is_observable(self) -> "EngineeringSemanticFactCandidate":
        if self.epistemic_status is SemanticEpistemicStatus.SUPERSEDED:
            raise ValueError("Provider candidates cannot directly assert SUPERSEDED status")
        if (
            self.authority is SemanticFactAuthority.SYSTEM_INFERRED
            and self.epistemic_status is SemanticEpistemicStatus.CONFIRMED
        ):
            raise ValueError("System inference cannot assert Human-confirmed truth")
        if self.operation is SemanticCandidateOperation.REMOVE and not self.supersedes_fact_ids:
            raise ValueError("Semantic removal must identify the facts it supersedes")
        return self


class SemanticFactProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_record_ids: tuple[UUID, ...] = Field(min_length=1)
    source_text: str = Field(min_length=1)
    source_extraction_ids: tuple[str, ...] = ()
    role_origin: SemanticRoleOrigin


class EngineeringSemanticFact(BaseModel):
    """Stable Work-scoped semantic truth with observable provenance and lineage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    subject: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,127}$")
    relation: SemanticRelation
    value: SemanticValue
    unit: str | None = Field(default=None, max_length=64)
    scope: str | None = Field(default=None, max_length=255)
    qualifiers: dict[str, SemanticScalar] = Field(default_factory=dict)
    authority: SemanticFactAuthority
    epistemic_status: SemanticEpistemicStatus
    provenance: SemanticFactProvenance
    supersedes_fact_ids: tuple[UUID, ...] = ()
    admitted_work_revision_id: UUID | None = None

    @property
    def is_current(self) -> bool:
        return self.epistemic_status is not SemanticEpistemicStatus.SUPERSEDED

    @property
    def semantic_key(self) -> tuple[str, SemanticRelation, str | None]:
        return (self.subject, self.relation, self.scope)


class SemanticFactReference(BaseModel):
    """Exact fact projection carried into Production and Verification contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: UUID
    subject: str
    relation: SemanticRelation
    value: SemanticValue
    unit: str | None = None
    scope: str | None = None
    qualifiers: dict[str, SemanticScalar] = Field(default_factory=dict)
    authority: SemanticFactAuthority
    epistemic_status: SemanticEpistemicStatus
    source_work_revision_id: UUID


def current_semantic_facts(
    facts: tuple[EngineeringSemanticFact, ...],
) -> tuple[EngineeringSemanticFact, ...]:
    return tuple(fact for fact in facts if fact.is_current)


def semantic_fact_reference(
    fact: EngineeringSemanticFact, *, work_revision_id: UUID
) -> SemanticFactReference:
    if not fact.is_current:
        raise ValueError("Superseded semantic facts cannot become current obligations")
    return SemanticFactReference(
        fact_id=fact.id,
        subject=fact.subject,
        relation=fact.relation,
        value=fact.value,
        unit=fact.unit,
        scope=fact.scope,
        qualifiers=fact.qualifiers,
        authority=fact.authority,
        epistemic_status=fact.epistemic_status,
        source_work_revision_id=work_revision_id,
    )


def semantic_fact_statement(fact: EngineeringSemanticFact | SemanticFactReference) -> str:
    value = " × ".join(str(item) for item in fact.value) if isinstance(fact.value, tuple) else str(fact.value)
    unit = f" {fact.unit}" if fact.unit else ""
    scope = f" within {fact.scope}" if fact.scope else ""
    return f"{fact.subject} {fact.relation.value.casefold()} {value}{unit}{scope}"
