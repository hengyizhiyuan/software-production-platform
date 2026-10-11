"""Derived fulfillment bindings for admitted engineering facts.

These values are a Work/Verification projection.  They do not amend a Fact,
grant an effect, or record that a future Human decision has occurred.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal
from hashlib import sha256
import json
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator, model_serializer


class FulfillmentOwner(StrEnum):
    VERIFICATION = "VERIFICATION"
    PRODUCT_SOURCE = "PRODUCT_SOURCE"
    CANDIDATE = "CANDIDATE"
    HUMAN_GATE = "HUMAN_GATE"
    DELIVERY_GATE = "DELIVERY_GATE"
    EXECUTION_GATE = "EXECUTION_GATE"
    UNRESOLVED = "UNRESOLVED"


class FulfillmentPhase(StrEnum):
    CURRENT_VERIFICATION = "CURRENT_VERIFICATION"
    CONTINUOUS_FROM_ADMISSION = "CONTINUOUS_FROM_ADMISSION"
    CANDIDATE_SEAL = "CANDIDATE_SEAL"
    HUMAN_INTEGRATION = "HUMAN_INTEGRATION"
    DELIVERY = "DELIVERY"
    CONTEXT_RETENTION = "CONTEXT_RETENTION"
    UNRESOLVED = "UNRESOLVED"


class FulfillmentSourceKind(StrEnum):
    FACT = "FACT"
    IR_CONSTRAINT = "IR_CONSTRAINT"
    IR_CLAUSE = "IR_CLAUSE"
    WORK_CONSTRAINT = "WORK_CONSTRAINT"
    IR_ITEM = "IR_ITEM"
    WORK_CONTEXT = "WORK_CONTEXT"


class FulfillmentComponentBasis(BaseModel):
    """Exact source contribution to a derived consumer, never a new fact."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    # Raw candidates may carry inaccurate offsets; the exact locator repairs
    # only a unique immutable quote before admission to a binding.
    source_span_start: StrictInt
    source_span_end: StrictInt
    source_component_quote: str = Field(min_length=1, max_length=65536)
    linked_fact_refs: tuple[str, ...] = ()


class FulfillmentBinding(BaseModel):
    """An exact, immutable route to an existing owner and evidence method."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: UUID | None = None
    source_kind: FulfillmentSourceKind = FulfillmentSourceKind.FACT
    semantic_ir_id: UUID | None = None
    constraint_item_id: str | None = None
    constraint_clause_id: str | None = None
    constraint_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    work_reality_revision_id: UUID
    fact_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    provenance_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_record_ids: tuple[UUID, ...] = ()
    component: str = Field(min_length=1)
    owner: FulfillmentOwner
    phase: FulfillmentPhase
    evidence_method: str = Field(min_length=1)
    gate_ref: str = Field(min_length=1)
    source_quote: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    target_paths: tuple[str, ...] = ()
    # Projection identity is independently recomputed by the consuming Owner.
    projection_inventory_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    work_constraint_indices: tuple[int, ...] = ()
    supporting_source_refs: tuple[str, ...] = ()
    formation_receipt: dict | None = None
    component_basis: FulfillmentComponentBasis | None = None
    # These states do not record satisfaction, Assurance or Human authority.
    state: Literal["BOUND_PENDING_EVIDENCE", "UNRESOLVED", "RETAINED_CONTEXT"] = "BOUND_PENDING_EVIDENCE"

    @model_validator(mode="after")
    def no_unowned_handoff(self):
        if self.component_basis is not None and (self.component_basis.source_span_start < 0
                or self.component_basis.source_span_end <= self.component_basis.source_span_start):
            raise ValueError("A binding requires a canonical nonempty source span")
        if not self.source_record_ids and self.source_kind is not FulfillmentSourceKind.IR_ITEM:
            raise ValueError("Human/Work binding requires exact admitted source records")
        if self.source_kind is FulfillmentSourceKind.FACT:
            if self.fact_id is None or self.fact_fingerprint is None or any((
                    self.constraint_item_id, self.constraint_clause_id,
                    self.constraint_fingerprint)):
                raise ValueError("Fact binding requires only exact Fact identity")
        elif self.source_kind in {FulfillmentSourceKind.WORK_CONSTRAINT, FulfillmentSourceKind.IR_ITEM, FulfillmentSourceKind.WORK_CONTEXT}:
            if self.fact_id is not None or self.fact_fingerprint is not None or not self.constraint_item_id or not self.constraint_fingerprint or self.constraint_clause_id is not None:
                raise ValueError("Work/item binding requires its own exact source identity")
            if self.source_kind is FulfillmentSourceKind.WORK_CONSTRAINT and self.work_constraint_indices != (int(self.constraint_item_id),):
                raise ValueError("Work constraint binding must preserve its own index")
        elif (self.fact_id is not None or self.fact_fingerprint is not None
                or not all((self.constraint_item_id, self.constraint_clause_id,
                            self.constraint_fingerprint))):
            raise ValueError("Constraint binding requires only exact IR identity")
        if self.source_kind is FulfillmentSourceKind.IR_CLAUSE and self.semantic_ir_id is None:
            raise ValueError("Clause binding requires exact Semantic IR identity")
        if any(index < 0 for index in self.work_constraint_indices) or len(set(self.work_constraint_indices)) != len(self.work_constraint_indices):
            raise ValueError("Work constraint references must be unique nonnegative indices")
        if self.state == "UNRESOLVED" and (self.owner is not FulfillmentOwner.UNRESOLVED or self.phase is not FulfillmentPhase.UNRESOLVED):
            raise ValueError("An unresolved projection cannot declare a fulfillment owner")
        if self.state == "RETAINED_CONTEXT" and (self.owner is not FulfillmentOwner.PRODUCT_SOURCE or self.phase is not FulfillmentPhase.CONTEXT_RETENTION):
            raise ValueError("Retained context is not a fulfilled execution obligation")
        if self.phase is FulfillmentPhase.CURRENT_VERIFICATION and self.owner not in {
            FulfillmentOwner.VERIFICATION, FulfillmentOwner.PRODUCT_SOURCE,
        }:
            raise ValueError("A current check needs a current evidence owner")
        if self.phase is FulfillmentPhase.CONTINUOUS_FROM_ADMISSION and self.owner not in {
            FulfillmentOwner.DELIVERY_GATE, FulfillmentOwner.EXECUTION_GATE,
        }:
            raise ValueError("A continuous prohibition needs an execution gate")
        return self


def canonical_fingerprint(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), default=str).encode()).hexdigest()


def bind_admitted_fact(*, reference, admitted, component: str,
                       owner: FulfillmentOwner, phase: FulfillmentPhase,
                       evidence_method: str, gate_ref: str, source_quote: str,
                       source_revision: str, target_paths: tuple[str, ...] = ()) -> FulfillmentBinding:
    """Validate a proposed route against the exact admitted, source-owned Fact.

    The caller still has to prove the proposed method is permitted by the
    relevant owner.  Matching a quote is provenance, not a semantic verdict.
    """
    from spg.domain.engineering_semantics import semantic_fact_reference

    if semantic_fact_reference(admitted, work_revision_id=reference.source_work_revision_id) != reference:
        raise ValueError("OBLIGATION_FACT_IDENTITY_MISMATCH")
    if source_quote not in admitted.provenance.source_text:
        raise ValueError("OBLIGATION_SOURCE_QUOTE_NOT_OBSERVED")
    if not admitted.provenance.source_record_ids:
        raise ValueError("OBLIGATION_SOURCE_RECORD_MISSING")
    return FulfillmentBinding(
        fact_id=reference.fact_id,
        work_reality_revision_id=reference.source_work_revision_id,
        fact_fingerprint=canonical_fingerprint(reference.model_dump(mode="json")),
        provenance_fingerprint=canonical_fingerprint(
            admitted.provenance.model_dump(mode="json")),
        source_record_ids=admitted.provenance.source_record_ids,
        component=component, owner=owner, phase=phase,
        evidence_method=evidence_method, gate_ref=gate_ref,
        source_quote=source_quote, source_revision=source_revision,
        target_paths=target_paths,
    )


def bind_admitted_constraint(*, revision, ir, item, clause, component: str,
                             owner: FulfillmentOwner, phase: FulfillmentPhase,
                             evidence_method: str, gate_ref: str,
                             expected_polarity: str,
                             target_paths: tuple[str, ...] = ()) -> FulfillmentBinding:
    """Bind a typed prohibition to its exact admitted IR and Work revision."""
    from spg.domain.intent_realization import SemanticKind
    from spg.domain.semantic_provenance import SemanticOrigin

    if (revision.source_assessment_id is None or ir is None
            or item.kind is not SemanticKind.CONSTRAINT
            or item.item_id not in clause.semantic_item_ids
            or clause.polarity != expected_polarity
            or item.statement not in revision.constraints
            or clause not in ir.clauses or item not in ir.items
            or not item.provenance
            or any(source.origin is not SemanticOrigin.HUMAN_EXPLICIT
                   or source.source_record_id != clause.source_record_id
                   or source.source_record_id not in revision.source_record_ids
                   or source.source_text not in clause.source_text
                   for source in item.provenance)):
        raise ValueError("OBLIGATION_CONSTRAINT_SOURCE_MISMATCH")
    return FulfillmentBinding(
        source_kind=FulfillmentSourceKind.IR_CONSTRAINT,
        constraint_item_id=item.item_id,
        constraint_clause_id=clause.clause_id,
        constraint_fingerprint=canonical_fingerprint({
            "ir_id": str(ir.id), "item": item.model_dump(mode="json"),
            "clause": clause.model_dump(mode="json"),
        }),
        work_reality_revision_id=revision.id,
        provenance_fingerprint=canonical_fingerprint(
            [source.model_dump(mode="json") for source in item.provenance]),
        source_record_ids=tuple(dict.fromkeys(
            source.source_record_id for source in item.provenance)),
        component=component, owner=owner,
        phase=phase,
        evidence_method=evidence_method, gate_ref=gate_ref,
        source_quote=clause.source_text,
        source_revision=revision.source_revision or revision.revision_fingerprint,
        target_paths=target_paths,
    )


def fulfillment_source_ref(binding: FulfillmentBinding) -> str:
    """Canonical source identity shared by Native, Verification and Guardian."""
    if binding.source_kind is FulfillmentSourceKind.FACT:
        return f"semantic-fact:{binding.fact_id}"
    if binding.source_kind is FulfillmentSourceKind.WORK_CONSTRAINT:
        return f"work-constraint:{binding.work_reality_revision_id}:{binding.constraint_item_id}"
    if binding.source_kind is FulfillmentSourceKind.WORK_CONTEXT:
        return f"work-context:{binding.work_reality_revision_id}:{binding.constraint_item_id}"
    if binding.source_kind is FulfillmentSourceKind.IR_ITEM:
        return f"ir-item:{binding.semantic_ir_id}:{binding.constraint_item_id}"
    if binding.source_kind is FulfillmentSourceKind.IR_CLAUSE:
        return f"ir-clause:{binding.semantic_ir_id}:{binding.constraint_item_id}:{binding.constraint_clause_id}"
    return f"ir-constraint:{binding.constraint_item_id}:{binding.constraint_clause_id}"


class FulfillmentRouteCandidate(BaseModel):
    """A model-proposed method, never an admitted Fact or evidence verdict."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_ref: str = Field(min_length=1)
    capability: str = Field(min_length=1)
    work_constraint_indices: tuple[int, ...] = ()
    target_paths: tuple[str, ...] = ()
    supporting_source_refs: tuple[str, ...] = ()
    rationale: str = Field(min_length=1, max_length=1000)
    component_basis: FulfillmentComponentBasis | None = None


class FulfillmentProjectionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    inventory_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    routes: tuple[FulfillmentRouteCandidate, ...] = Field(min_length=1, max_length=1024)


class FulfillmentSourceConsumptionCheck(BaseModel):
    """Critic-proposed consumption witness, never a Fact or performed evidence."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_span_start: StrictInt = Field(ge=0)
    source_span_end: StrictInt = Field(gt=0)
    source_component_quote: str | None = Field(default=None, min_length=1)
    required_capability: str = Field(min_length=1)
    required_evidence_method: str = Field(min_length=1)
    required_phase: FulfillmentPhase
    target_paths: tuple[str, ...] = ()
    route_indices: tuple[StrictInt, ...] = Field(max_length=1024)


class FulfillmentSemanticSourceReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_ref: str = Field(min_length=1)
    complete_and_equivalent: bool
    reason: str = Field(min_length=1, max_length=1000)
    consumption_checks: tuple[FulfillmentSourceConsumptionCheck, ...] | None = Field(default=None, max_length=1024)

    @model_serializer(mode="wrap")
    def preserve_historical_shape(self, handler):
        result = handler(self)
        if self.consumption_checks is None:
            result.pop("consumption_checks", None)
        return result


class FulfillmentSemanticComponentReview(BaseModel):
    """Independent interpretation check, never Owner evidence or authority."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    component_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    capability: str = Field(min_length=1)
    complete_and_equivalent: StrictBool
    nonredundant: StrictBool
    owner_phase_evidence_valid: StrictBool
    context_only: StrictBool
    reason: str = Field(min_length=1, max_length=1000)


class FulfillmentSemanticReviewCandidate(BaseModel):
    """Independent derived-plan semantic validation; no Assurance/authority."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    inventory_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    components_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_results: tuple[FulfillmentSemanticSourceReview, ...] = Field(min_length=1, max_length=1024)
    # Absent for historical v1 receipts. Serialization must preserve their shape.
    component_results: tuple[FulfillmentSemanticComponentReview, ...] | None = Field(default=None, min_length=1, max_length=1024)

    @model_serializer(mode="wrap")
    def preserve_historical_shape(self, handler):
        result = handler(self)
        if self.component_results is None:
            result.pop("component_results", None)
        return result


def fulfillment_component_id(route, inventory_fingerprint):
    return canonical_fingerprint({"inventory_fingerprint": inventory_fingerprint,
        "source_ref": getattr(route, "source_ref", None) or fulfillment_source_ref(route),
        "component_basis": None if route.component_basis is None else route.component_basis.model_dump(mode="json")})


def fulfillment_candidate_fingerprint(candidate) -> str:
    return canonical_fingerprint({"inventory_fingerprint": candidate.inventory_fingerprint,
        "routes": [route.model_dump(mode="json", exclude={"rationale"}) for route in candidate.routes]})


def fulfillment_components_fingerprint(candidate) -> str:
    return canonical_fingerprint([{ "source_ref": route.source_ref, "capability": route.capability,
        "component_basis": None if route.component_basis is None else route.component_basis.model_dump(mode="json")}
        for route in candidate.routes])


def fulfillment_source_semantic_text(source) -> str:
    if source["kind"] == "FACT":
        return source["provenance"]["source_text"]
    if source["kind"] in {"IR_CONSTRAINT", "IR_CLAUSE"}:
        return source["payload"]["clause"]["source_text"]
    if source["kind"] == "IR_ITEM":
        return source["payload"]["item"]["statement"]
    return source["payload"]["content"]


def exact_file_scope_paths(fact_or_reference, *, qualified=False) -> tuple[str, ...] | None:
    """Reuse literal file Scope, optionally preserving typed exclusivity."""
    if getattr(fact_or_reference.relation, "value", fact_or_reference.relation) != "SCOPE":
        return None
    qualifiers = fact_or_reference.qualifiers
    # This checker proves exclusive repository-file scope, not arbitrary qualifiers.
    # Preserve the original qualifier in Fact fingerprints and Owner evidence.
    if qualifiers and not (qualified and qualifiers == {"exclusive": True}
            and type(qualifiers["exclusive"]) is bool):
        return None
    paths = literal_file_scope_value_paths(fact_or_reference)
    if paths is None or not qualified and fact_or_reference.scope is not None and fact_or_reference.scope not in paths:
        return None
    return paths


def literal_file_scope_value_paths(fact_or_reference, *, proposed_method=False) -> tuple[str, ...] | None:
    """Observe literal Scope values, without judging any qualifier semantics.

    This is not exclusive-scope evidence or authority. A calibrated consumer
    must independently review the unchanged qualifiers before admitting its
    proposed exclusive-diff meaning.
    """
    # A reviewed method proposal may observe original literal operands without
    # changing the admitted relation. This is not a semantic file-scope grant.
    # Unmarked historical callers retain the original typed SCOPE contract.
    if not proposed_method and getattr(fact_or_reference.relation, "value", fact_or_reference.relation) != "SCOPE":
        return None
    value = fact_or_reference.value
    values = (value,) if isinstance(value, str) else tuple(value) if isinstance(value, (tuple, list)) else None
    if not values or not all(isinstance(path, str) for path in values) or len(set(values)) != len(values):
        return None
    if getattr(fact_or_reference, "reference_role", None) is not None or getattr(fact_or_reference, "unit", None) is not None:
        return None
    from spg.domain.change import safe_repository_path
    try:
        for path in values:
            if safe_repository_path(path) != path:
                return None
    except ValueError:
        return None
    return values
