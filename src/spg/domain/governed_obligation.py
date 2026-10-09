"""Derived fulfillment bindings for admitted engineering facts.

These values are a Work/Verification projection.  They do not amend a Fact,
grant an effect, or record that a future Human decision has occurred.
"""

from __future__ import annotations

from enum import StrEnum
from hashlib import sha256
import json
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FulfillmentOwner(StrEnum):
    VERIFICATION = "VERIFICATION"
    PRODUCT_SOURCE = "PRODUCT_SOURCE"
    CANDIDATE = "CANDIDATE"
    HUMAN_GATE = "HUMAN_GATE"
    DELIVERY_GATE = "DELIVERY_GATE"
    EXECUTION_GATE = "EXECUTION_GATE"


class FulfillmentPhase(StrEnum):
    CURRENT_VERIFICATION = "CURRENT_VERIFICATION"
    CONTINUOUS_FROM_ADMISSION = "CONTINUOUS_FROM_ADMISSION"
    CANDIDATE_SEAL = "CANDIDATE_SEAL"
    HUMAN_INTEGRATION = "HUMAN_INTEGRATION"
    DELIVERY = "DELIVERY"


class FulfillmentBinding(BaseModel):
    """An exact, immutable route to an existing owner and evidence method."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: UUID
    work_reality_revision_id: UUID
    fact_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    provenance_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_record_ids: tuple[UUID, ...] = Field(min_length=1)
    component: str = Field(min_length=1)
    owner: FulfillmentOwner
    phase: FulfillmentPhase
    evidence_method: str = Field(min_length=1)
    gate_ref: str = Field(min_length=1)
    source_quote: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    target_paths: tuple[str, ...] = ()
    # This is deliberately not a satisfaction or Assurance verdict.
    state: str = "BOUND_PENDING_EVIDENCE"

    @model_validator(mode="after")
    def no_unowned_handoff(self):
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
