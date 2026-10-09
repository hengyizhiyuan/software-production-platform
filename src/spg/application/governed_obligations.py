"""Route admitted IR constraints to existing execution and Verification owners."""

from __future__ import annotations

import re

from spg.domain.governed_obligation import (
    FulfillmentBinding, FulfillmentOwner, FulfillmentPhase,
    FulfillmentSourceKind, canonical_fingerprint,
    bind_admitted_fact, bind_admitted_constraint,
)
from spg.domain.engineering_semantics import semantic_fact_reference
from spg.domain.intent_realization import SemanticKind
from spg.domain.semantic_provenance import SemanticOrigin


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

# IRK proposes typed effects; these entries are existing owner capabilities and
# evidence methods, not prose/Subject aliases. Unknown effects stay unresolved.
_TYPED_EFFECT_ROUTES = {
    "PROHIBIT_PREVIEW": ("preview", *_GATES["preview"],
                         FulfillmentPhase.CONTINUOUS_FROM_ADMISSION,
                         "EXACT_PERMISSION_GATE", "NEGATED"),
    "PROHIBIT_DEPLOY": ("deploy", *_GATES["deploy"],
                        FulfillmentPhase.CONTINUOUS_FROM_ADMISSION,
                        "EXACT_PERMISSION_GATE", "NEGATED"),
    "PROHIBIT_PUBLISH": ("publish", *_GATES["publish"],
                         FulfillmentPhase.CONTINUOUS_FROM_ADMISSION,
                         "EXACT_PERMISSION_GATE", "NEGATED"),
    "RESTRICT_CHANGE_SCOPE": ("git-diff-scope", FulfillmentOwner.VERIFICATION,
                              "code-verification:path-scope",
                              FulfillmentPhase.CURRENT_VERIFICATION,
                              "EXACT_GIT_DIFF_SCOPE", "AFFIRMATIVE"),
    "PROHIBIT_ADDITIONAL_PAGES": ("git-diff-scope", FulfillmentOwner.VERIFICATION,
                                  "code-verification:path-scope",
                                  FulfillmentPhase.CURRENT_VERIFICATION,
                                  "EXACT_GIT_DIFF_SCOPE", "NEGATED"),
    "PROHIBIT_README_CHANGE": ("git-diff-scope", FulfillmentOwner.VERIFICATION,
                               "code-verification:path-scope",
                               FulfillmentPhase.CURRENT_VERIFICATION,
                               "EXACT_GIT_DIFF_SCOPE", "NEGATED"),
}


def _mentions(value: str, effect: str) -> bool:
    return any(re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])",
                         value.casefold()) for word in _EFFECT_WORDS[effect])


def materialize_continuous_gates(revision, ir) -> tuple[FulfillmentBinding, ...]:
    """Bind admitted typed constraints to existing permission and diff owners."""
    if ir is None or not ir.current_production:
        return ()
    exact_targets = tuple(dict.fromkeys(
        arg.value for goal in ir.current_production for arg in goal.target_paths))
    valid_targets = bool(exact_targets) and all(
        arg.provenance.origin is SemanticOrigin.HUMAN_EXPLICIT
        and arg.provenance.source_record_id in revision.source_record_ids
        for goal in ir.current_production for arg in goal.target_paths)
    bindings: list[FulfillmentBinding] = []
    for item in ir.items:
        if item.kind is not SemanticKind.CONSTRAINT:
            continue
        clauses = tuple(clause for clause in ir.clauses
                        if item.item_id in clause.semantic_item_ids)
        if not clauses:
            raise ValueError("OBLIGATION_CONSTRAINT_CLAUSE_MISSING")
        for clause in clauses:
            for effect in clause.requested_effects:
                route = _TYPED_EFFECT_ROUTES.get(effect)
                if route is None:
                    if effect.startswith(("PROHIBIT_", "RESTRICT_")):
                        raise ValueError("OBLIGATION_EFFECT_ROUTE_UNRESOLVED")
                    continue
                component, owner, gate, phase, method, polarity = route
                if method == "EXACT_GIT_DIFF_SCOPE" and not valid_targets:
                    raise ValueError("OBLIGATION_SCOPE_TARGET_UNRESOLVED")
                if (component == "preview" and any(goal.preview_required
                        for goal in ir.current_production)) or (
                        component in {"deploy", "publish"} and any(
                            goal.delivery_authorized for goal in ir.current_production)):
                    raise ValueError("OBLIGATION_EFFECT_AUTHORITY_CONFLICT")
                bindings.append(bind_admitted_constraint(
                    revision=revision, ir=ir, item=item, clause=clause,
                    component=component, owner=owner, phase=phase,
                    evidence_method=method, gate_ref=gate,
                    expected_polarity=polarity,
                    target_paths=(exact_targets if method == "EXACT_GIT_DIFF_SCOPE"
                                  else ())))
    return tuple(bindings)


def admitted_fulfillment_bindings(revision, assessment):
    """Use the same persisted authority basis at every production entry point."""
    if revision is None or revision.source_assessment_id is None:
        # Preserve the existing no-local-assessment path and downstream gates.
        # This does not qualify revisions that inherit IR from an earlier basis.
        return ()
    if assessment is None or assessment.id != revision.source_assessment_id:
        raise ValueError("OBLIGATION_ADMITTED_SOURCE_UNAVAILABLE")
    return materialize_continuous_gates(revision, assessment.semantic_ir)


def validate_continuous_gates(bindings, revision, ir) -> None:
    """Reject stale or injected routes before dispatch and Verification."""
    expected = materialize_continuous_gates(revision, ir)
    constraints = tuple(item for item in bindings
                        if item.source_kind is FulfillmentSourceKind.IR_CONSTRAINT)
    if constraints != expected:
        raise ValueError("OBLIGATION_GATE_BINDING_DRIFT")
    # Existing sealed Fact bindings remain readable and enforceable. New
    # bindings are constructed from typed IR; no prose rematching is allowed.
    for item in bindings:
        if item.source_kind is not FulfillmentSourceKind.FACT:
            continue
        fact = next((fact for fact in revision.engineering_semantic_facts
                     if fact.id == item.fact_id and fact.is_current), None)
        if (fact is None or item.work_reality_revision_id != revision.id
                or item.fact_fingerprint != canonical_fingerprint(
                    semantic_fact_reference(fact,
                        work_revision_id=revision.id).model_dump(mode="json"))
                or item.provenance_fingerprint != canonical_fingerprint(
                    fact.provenance.model_dump(mode="json"))
                or item.source_record_ids != fact.provenance.source_record_ids
                or item.source_quote not in fact.provenance.source_text
                or item.source_revision != (
                    revision.source_revision or revision.revision_fingerprint)
                or item.component not in _GATES
                or (item.owner, item.gate_ref) != _GATES[item.component]):
            raise ValueError("OBLIGATION_GATE_BINDING_DRIFT")


def assert_delivery_effect_permitted(database, work_id, component: str) -> None:
    """Recheck current Work truth before a Human gate creates an external effect."""
    if component not in {"deploy", "publish"}:
        raise ValueError("OBLIGATION_DELIVERY_COMPONENT_UNSUPPORTED")
    from spg.infrastructure.persistence.product_store import ProductStore
    from spg.infrastructure.persistence.interaction_store import InteractionStore

    with database.unit_of_work() as uow:
        revision = ProductStore(uow.session).current_work_reality_revision(work_id)
        if revision is None or revision.source_assessment_id is None:
            return
        assessment = InteractionStore(uow.session).assessment(
            revision.source_assessment_id)
        if assessment is None:
            raise ValueError("OBLIGATION_DELIVERY_SOURCE_UNAVAILABLE")
        if assessment.semantic_ir is None:
            # Pre-IRK historical Work remains under the existing Human gates.
            return
        bindings = materialize_continuous_gates(revision, assessment.semantic_ir)
        if any(item.component == component and
               item.phase is FulfillmentPhase.CONTINUOUS_FROM_ADMISSION
               for item in bindings):
            raise ValueError("OBLIGATION_DELIVERY_PROHIBITED")


def denied_execution_capabilities(bindings) -> frozenset[str]:
    return frozenset("preview.inspect" for item in bindings
                    if item.component == "preview"
                    and item.gate_ref == _GATES["preview"][1]
                    and item.phase is FulfillmentPhase.CONTINUOUS_FROM_ADMISSION)


def evaluate_constraint_routes(bindings, native_record, *, source_revision: str,
                               path_scope_passed: bool,
                               exact_target_paths: tuple[str, ...] = ()) -> tuple[dict, ...]:
    """Report one current result per constraint route, without claiming no-effect history."""
    native = None if native_record is None else native_record.binding
    context = None if native is None else native.production_context
    grants = set() if native is None else {item.identity for item in native.capability_grants}
    results = []
    for item in bindings:
        if item.source_kind is not FulfillmentSourceKind.IR_CONSTRAINT:
            continue
        exact = bool(native is not None and context is not None
                     and native_record.attempt_id == native.attempt_id
                     and context.work_reality_revision_id == item.work_reality_revision_id
                     and item.source_revision == source_revision
                     and any(member.source_commit_oid == source_revision
                             for member in native.source_vector.members)
                     and f"ir-constraint:{item.constraint_item_id}:{item.constraint_clause_id}"
                     in native.obligation_references)
        if item.evidence_method == "EXACT_GIT_DIFF_SCOPE":
            member = None if native is None else next((member for member in
                native.source_vector.members if member.source_commit_oid == source_revision), None)
            passed = (exact and path_scope_passed
                      and bool(item.target_paths)
                      and set(item.target_paths) == set(exact_target_paths)
                      and member is not None
                      and set(item.target_paths) == set(member.write_scope)
                      and set(item.target_paths).isdisjoint(member.forbidden_paths))
        else:
            forbidden = ({"preview.inspect"} if item.component == "preview" else
                         {"cloud.deploy", "cloud.delivery"} if item.component == "deploy" else
                         {"remote.publish", "remote.delivery", "github.publish"})
            passed = exact and grants.isdisjoint(forbidden)
        results.append({
            "source_kind": item.source_kind.value,
            "work_reality_revision_id": str(item.work_reality_revision_id),
            "constraint_item_id": item.constraint_item_id,
            "constraint_clause_id": item.constraint_clause_id,
            "component": item.component, "passed": passed,
            "disposition": ("VERIFIED_CURRENT" if passed and
                            item.phase is FulfillmentPhase.CURRENT_VERIFICATION else
                            "GATED_CONTINUOUS" if passed else "UNVERIFIABLE_CURRENT"),
            "reason": ("EXACT_OWNER_EVIDENCE" if passed else
                       "CONSTRAINT_OWNER_EVIDENCE_MISSING"),
            "fulfillment_bindings": [item.model_dump(mode="json")],
            "gate_evidence": {
                "attempt_id": None if native is None else str(native.attempt_id),
                "native_binding_digest": None if native_record is None else native_record.binding_digest,
                "source_revision": source_revision,
                "meaning": "current attempt and scoped verification only",
            },
        })
    return tuple(results)


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
