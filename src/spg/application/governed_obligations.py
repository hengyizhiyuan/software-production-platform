"""Bound current execution permissions from admitted Work facts and typed IR.

This is an owner adapter, not another semantic authority.  It only creates a
derived route when an exact Fact, its Human source, the admitted Production
Intent, and an already implemented permission gate agree.  Other facts remain
for Verification to materialize or explicitly fail as unresolved.
"""

from __future__ import annotations

import re

from spg.domain.engineering_semantics import SemanticRelation, semantic_fact_reference
from spg.domain.governed_obligation import (
    FulfillmentBinding, FulfillmentOwner, FulfillmentPhase, bind_admitted_fact,
)


# These are stable effect capabilities enforced by existing owners, not a
# vocabulary of WIC Subject aliases or product fields.
_EFFECT_WORDS = {
    "preview": ("preview",),
    "deploy": ("deploy", "deployment"),
    "publish": ("publish", "publishing", "publication"),
}
_GATES = {
    "preview": (FulfillmentOwner.EXECUTION_GATE,
                "execution-capability:preview.inspect:denied"),
    "deploy": (FulfillmentOwner.DELIVERY_GATE,
               "cloud-delivery:human-authorization-required"),
    "publish": (FulfillmentOwner.DELIVERY_GATE,
                "remote-delivery:human-authorization-required"),
}


def _mentions(value: str, effect: str) -> bool:
    return any(re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])",
                         value.casefold()) for word in _EFFECT_WORDS[effect])


def _negative_fact(fact) -> bool:
    return (fact.relation is SemanticRelation.EQUALITY and fact.value is False
            or fact.relation is SemanticRelation.SCOPE
            and (isinstance(fact.value, str) and fact.value.casefold().startswith("no ")
                 or any(value is False for value in fact.qualifiers.values())))


def materialize_continuous_gates(revision, ir) -> tuple[FulfillmentBinding, ...]:
    """Bind only prohibitions supported by a typed intent and an actual gate.

    A default ``delivery_authorized=False`` alone never becomes a prohibition;
    the exact source and an explicit admitted exclusion must also identify the
    effect.  An unrelated negative content Fact therefore cannot inherit a
    deployment or preview route.  Unclear expressions remain unresolved.
    """
    if ir is None or not ir.current_production:
        return ()
    goals = ir.current_production
    bindings: list[FulfillmentBinding] = []
    for fact in revision.engineering_semantic_facts:
        if not fact.is_current or not _negative_fact(fact):
            continue
        quote = fact.provenance.source_text
        reference = semantic_fact_reference(fact, work_revision_id=revision.id)
        for effect, (owner, gate) in _GATES.items():
            if not _mentions(quote, effect):
                continue
            if not all(any(_mentions(exclusion, effect) for exclusion in goal.exclusions)
                       for goal in goals):
                continue
            if effect == "preview" and any(goal.preview_required for goal in goals):
                continue
            if effect in {"deploy", "publish"} and any(
                    goal.delivery_authorized for goal in goals):
                continue
            # The component must also be expressed in the admitted Fact, not
            # merely in its broad source paragraph.
            if not (_mentions(fact.subject, effect)
                    or _mentions(str(fact.value), effect)
                    or any(_mentions(key, effect) and value is False
                           for key, value in fact.qualifiers.items())):
                continue
            bindings.append(bind_admitted_fact(
                reference=reference, admitted=fact, component=effect,
                owner=owner, phase=FulfillmentPhase.CONTINUOUS_FROM_ADMISSION,
                evidence_method="EXACT_PERMISSION_GATE",
                gate_ref=gate, source_quote=quote,
                source_revision=revision.source_revision or revision.revision_fingerprint,
            ))
    return tuple(bindings)


def validate_continuous_gates(bindings, revision, ir) -> None:
    """Reject stale or injected routes before dispatch and Verification."""
    expected = materialize_continuous_gates(revision, ir)
    if tuple(bindings) != expected:
        raise ValueError("OBLIGATION_GATE_BINDING_DRIFT")


def denied_execution_capabilities(bindings) -> frozenset[str]:
    return frozenset("preview.inspect" for item in bindings
                    if item.component == "preview"
                    and item.gate_ref == _GATES["preview"][1]
                    and item.phase is FulfillmentPhase.CONTINUOUS_FROM_ADMISSION)


def evaluate_continuous_gates(checks, bindings, native_record, *, source_revision: str):
    """Attest an armed permission gate; never assert historical no-effect.

    The admission route alone is insufficient.  Verification reads the exact
    persisted Native binding for this attempt and checks that the restricted
    capability was not granted.  Human delivery gates remain independent.
    """
    grouped: dict[str, list[FulfillmentBinding]] = {}
    for item in bindings:
        grouped.setdefault(str(item.fact_id), []).append(item)
    binding = None if native_record is None else native_record.binding
    grants = set() if binding is None else {item.identity for item in binding.capability_grants}
    output = []
    for check in checks:
        relevant = grouped.get(check["fact_id"], ())
        if not relevant or check["disposition"] != "UNVERIFIABLE_CURRENT":
            output.append(check)
            continue
        context = None if binding is None else binding.production_context
        exact = bool(binding is not None and context is not None
            and binding.attempt_id == native_record.attempt_id
            and context.work_reality_revision_id == relevant[0].work_reality_revision_id
            and "semantic-fact:" + check["fact_id"] in binding.obligation_references
            and any(member.source_commit_oid == source_revision
                    for member in binding.source_vector.members)
            and all(item.source_revision == source_revision for item in relevant))
        no_forbidden_grant = all(
            item.component != "preview" or "preview.inspect" not in grants
            for item in relevant)
        no_delivery_grant = all(
            item.component not in {"deploy", "publish"} or not any(
                grant in grants for grant in (
                    "cloud.deploy", "cloud.delivery", "remote.publish",
                    "remote.delivery", "github.publish"))
            for item in relevant)
        passed = exact and no_forbidden_grant and no_delivery_grant
        output.append({**check,
            "passed": passed,
            "disposition": "GATED_CONTINUOUS" if passed else "UNVERIFIABLE_CURRENT",
            "reason": "EXACT_PERMISSION_GATE_ARMED" if passed else
                      "CONTINUOUS_GATE_EVIDENCE_MISSING",
            "fulfillment_bindings": [item.model_dump(mode="json") for item in relevant],
            "gate_evidence": {
                "attempt_id": None if binding is None else str(binding.attempt_id),
                "pwu_id": None if binding is None else str(binding.pwu_id),
                "source_revision": source_revision,
                "native_binding_digest": None if native_record is None else native_record.binding_digest,
                "restricted_capabilities_absent": no_forbidden_grant and no_delivery_grant,
                "meaning": "current execution permission only; no historical no-effect attestation",
            }})
    return tuple(output)


def evaluate_candidate_handoffs(checks, *, references, admitted_facts, ir,
                                source_revision: str, exact_target_paths: tuple[str, ...]):
    """Split a mixed acceptance assertion without claiming a seal already exists.

    Its current content/scope component is supported only by *all* the other
    admitted checks.  The remaining Candidate component is carried to the
    Candidate Owner.  If either half cannot be established the assertion stays
    unresolved; no model can create the missing seal or Human decision.
    """
    from spg.domain.engineering_semantics import SemanticRelation
    by_id = {str(item.fact_id): item for item in references}
    output = []
    for check in checks:
        fact = by_id[check["fact_id"]]
        admitted = admitted_facts.get(check["fact_id"])
        if (check["disposition"] != "UNVERIFIABLE_CURRENT"
                or fact.relation is not SemanticRelation.ACCEPTANCE_ASSERTION
                or not isinstance(fact.value, str)
                or admitted is None or ir is None
                or not ir.current_production
                or not all(goal.acceptance_required for goal in ir.current_production)
                or not _mentions_candidate(fact.value)
                or not _mentions_candidate(admitted.provenance.source_text)):
            output.append(check)
            continue
        other = [item for item in checks if item["fact_id"] != check["fact_id"]]
        current_pass = bool(other) and all(item["passed"] is True for item in other)
        target_match = (len(exact_target_paths) == 1 and
            exact_target_paths[0] in admitted.provenance.source_text)
        if not current_pass or not target_match:
            output.append(check)
            continue
        binding = bind_admitted_fact(
            reference=fact, admitted=admitted, component="reviewable-candidate",
            owner=FulfillmentOwner.CANDIDATE,
            phase=FulfillmentPhase.CANDIDATE_SEAL,
            evidence_method="EXACT_SEALED_CANDIDATE",
            gate_ref="candidate-owner:sealed-after-verification",
            source_quote=admitted.provenance.source_text,
            source_revision=source_revision, target_paths=exact_target_paths)
        output.append({**check, "passed": True,
            "reason": "CURRENT_FACTS_VERIFIED_CANDIDATE_SEAL_PENDING",
            "disposition": "CURRENT_VERIFIED_FUTURE_GATE_PENDING",
            "linked_current_fact_ids": [item["fact_id"] for item in other],
            "fulfillment_bindings": [binding.model_dump(mode="json")],
            "future_evidence_status": "PENDING_CANDIDATE_SEAL"})
    return tuple(output)


def _mentions_candidate(value: str) -> bool:
    return bool(re.search(r"(?<![a-z])candidate(?![a-z])", value.casefold()))
