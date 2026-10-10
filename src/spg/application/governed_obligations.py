"""Route admitted IR constraints to existing execution and Verification owners."""

from __future__ import annotations

import re
from dataclasses import asdict
from hashlib import sha256
import json
from time import monotonic
from uuid import NAMESPACE_URL, uuid5

from spg.domain.governed_obligation import (
    FulfillmentBinding, FulfillmentOwner, FulfillmentPhase,
    FulfillmentSourceKind, canonical_fingerprint,
    bind_admitted_fact, bind_admitted_constraint,
    FulfillmentProjectionCandidate, fulfillment_source_ref, exact_file_scope_paths,
    FulfillmentSemanticReviewCandidate, fulfillment_candidate_fingerprint,
    fulfillment_components_fingerprint, fulfillment_source_semantic_text,
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


def admitted_fulfillment_bindings(revision, assessment, *, provider=None,
                                  database=None, source_revision=None,
                                  exact_target_paths=()):
    """Project immutable admitted meaning once at the production boundary."""
    if revision is None or revision.source_assessment_id is None:
        return ()
    if assessment is None or assessment.id != revision.source_assessment_id:
        raise ValueError("OBLIGATION_ADMITTED_SOURCE_UNAVAILABLE")
    ir = assessment.semantic_ir
    if ir is None or getattr(ir, "legacy_typed_projection", False):
        return materialize_continuous_gates(revision, ir)
    inventory = fulfillment_inventory(revision, ir, source_revision=source_revision,
                                      exact_target_paths=exact_target_paths)
    source_failure = admitted_clause_source_failure(revision, ir, database=database)
    if source_failure is not None:
        return unresolved_projection(revision, ir, inventory, reason=source_failure)
    typed = deterministic_fulfillment_projection(revision, ir, inventory)
    if not any(binding.state == "UNRESOLVED" for binding in typed):
        return typed
    if provider is None:
        # Typed capabilities are retained; only actually unknown dispositions
        # remain unresolved. One known route never conceals the other sources.
        return typed
    return form_fulfillment_projection(revision, ir, provider=provider,
        database=database, source_revision=source_revision,
        exact_target_paths=exact_target_paths)


def validate_continuous_gates(bindings, revision, ir, *, source_revision=None, exact_target_paths=()) -> None:
    """Reject stale or injected routes before dispatch and Verification."""
    projected = tuple(item for item in bindings if item.projection_inventory_fingerprint)
    if projected:
        if len(projected) != len(bindings):
            raise ValueError("OBLIGATION_PROJECTION_MIXED_BASIS")
        validate_fulfillment_projection(bindings, revision, ir, source_revision=source_revision, exact_target_paths=exact_target_paths)
        return
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
        typed = materialize_continuous_gates(revision, assessment.semantic_ir)
        if any(item.component == component and item.phase is FulfillmentPhase.CONTINUOUS_FROM_ADMISSION for item in typed):
            raise ValueError("OBLIGATION_DELIVERY_PROHIBITED")
        if getattr(assessment.semantic_ir, "legacy_typed_projection", False):
            return
        product = ProductStore(uow.session)
        runtime_binding = product.runtime_binding(work_id)
        if runtime_binding is None or runtime_binding.work_reality_revision_id != revision.id:
            raise ValueError("OBLIGATION_DELIVERY_PROJECTION_MISSING_OR_STALE")
        from spg.infrastructure.persistence.runtime_store import RuntimeStore
        unit = RuntimeStore(uow.session).work_unit(runtime_binding.work_unit_id)
        if unit is None:
            raise ValueError("OBLIGATION_DELIVERY_PROJECTION_MISSING_OR_STALE")
        contract = unit.completion_contract
        bindings = contract.fulfillment_bindings
        if not bindings or not all(item.projection_inventory_fingerprint for item in bindings):
            raise ValueError("OBLIGATION_DELIVERY_PROJECTION_MISSING_OR_STALE")
        change = contract.change_contract
        artifact = contract.artifact_contract
        source = (change.source_revision if change else artifact.source_revision if artifact else revision.source_revision)
        paths = tuple(target.path for target in change.exact_targets) if change else (() if artifact is None else (artifact.artifact_path,))
        validate_continuous_gates(bindings, revision, assessment.semantic_ir,
                                  source_revision=source, exact_target_paths=paths)
        if any(item.component == component and item.phase is FulfillmentPhase.CONTINUOUS_FROM_ADMISSION for item in bindings):
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
        if item.source_kind not in {FulfillmentSourceKind.IR_CONSTRAINT, FulfillmentSourceKind.IR_CLAUSE, FulfillmentSourceKind.WORK_CONSTRAINT}:
            continue
        # Other current methods and future/context dispositions have their own
        # typed consumers. No permission result is invented for them here.
        if item.evidence_method not in {"EXACT_GIT_DIFF_SCOPE", "EXACT_PERMISSION_GATE"}:
            continue
        exact = bool(native is not None and context is not None
                     and native_record.attempt_id == native.attempt_id
                     and context.work_reality_revision_id == item.work_reality_revision_id
                     and item.source_revision == source_revision
                     and any(member.source_commit_oid == source_revision
                             for member in native.source_vector.members)
                     and fulfillment_source_ref(item) in native.obligation_references)
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
            "semantic_ir_id": None if item.semantic_ir_id is None else str(item.semantic_ir_id),
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
        if (not relevant or check["disposition"] != "UNVERIFIABLE_CURRENT" or not all(
                item.phase is FulfillmentPhase.CONTINUOUS_FROM_ADMISSION
                and item.evidence_method == "EXACT_PERMISSION_GATE" for item in relevant)):
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
                                source_revision: str, exact_target_paths: tuple[str, ...],
                                fulfillment_bindings=()):
    """Split a mixed acceptance assertion without claiming a seal already exists.

    New projections require the assertion's own current check to pass. Future
    sealing/permission remains pending at its actual owner. Pre-IRK legacy
    projections retain their historical compatibility path; they do not qualify
    a new open plan or create a missing seal/Human decision.
    """
    from spg.domain.engineering_semantics import SemanticRelation
    by_id = {str(item.fact_id): item for item in references}
    output = []
    for check in checks:
        fact = by_id[check["fact_id"]]
        admitted = admitted_facts.get(check["fact_id"])
        projected = tuple(binding for binding in fulfillment_bindings
            if str(binding.fact_id) == check["fact_id"] and binding.projection_inventory_fingerprint)
        if projected:
            current = tuple(binding for binding in projected if binding.phase is FulfillmentPhase.CURRENT_VERIFICATION)
            future = tuple(binding for binding in projected if binding.phase in {
                FulfillmentPhase.CANDIDATE_SEAL, FulfillmentPhase.HUMAN_INTEGRATION})
            exact = bool(admitted is not None and fact.relation is SemanticRelation.ACCEPTANCE_ASSERTION
                and current and future and exact_target_paths and ir is not None
                and all(goal.acceptance_required for goal in ir.current_production)
                and all(binding.source_revision == source_revision
                        and tuple(binding.target_paths) == tuple(exact_target_paths) for binding in current)
                and check["passed"] is True)
            output.append({**check,
                "disposition": "CURRENT_VERIFIED_FUTURE_GATE_PENDING",
                "fulfillment_bindings": [binding.model_dump(mode="json") for binding in projected],
                "future_evidence_status": "PENDING_FUTURE_OWNER_GATE"} if exact else check)
            continue
        if (ir is not None and not getattr(ir, "legacy_typed_projection", True)):
            output.append(check)
            continue
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


# Qualified evidence/permission capabilities, never Human phrase aliases.
FULFILLMENT_CAPABILITIES = {
    "ARTIFACT_CONTENT": ("artifact-content", FulfillmentOwner.VERIFICATION,
        FulfillmentPhase.CURRENT_VERIFICATION, "EXACT_CANDIDATE_CONTENT", "code-verification:semantic-facts"),
    "GIT_DIFF_SCOPE": ("git-diff-scope", FulfillmentOwner.VERIFICATION,
        FulfillmentPhase.CURRENT_VERIFICATION, "EXACT_GIT_DIFF_SCOPE", "code-verification:path-scope"),
    "PRODUCT_SOURCE_IDENTITY": ("source-identity", FulfillmentOwner.PRODUCT_SOURCE,
        FulfillmentPhase.CURRENT_VERIFICATION, "EXACT_PRODUCT_SOURCE_IDENTITY", "product-source:accepted-source"),
    "DENY_PREVIEW": ("preview", *_GATES["preview"], FulfillmentPhase.CONTINUOUS_FROM_ADMISSION, "EXACT_PERMISSION_GATE"),
    "DENY_DEPLOY": ("deploy", *_GATES["deploy"], FulfillmentPhase.CONTINUOUS_FROM_ADMISSION, "EXACT_PERMISSION_GATE"),
    "DENY_PUBLISH": ("publish", *_GATES["publish"], FulfillmentPhase.CONTINUOUS_FROM_ADMISSION, "EXACT_PERMISSION_GATE"),
    "CANDIDATE_SEAL": ("reviewable-candidate", FulfillmentOwner.CANDIDATE,
        FulfillmentPhase.CANDIDATE_SEAL, "EXACT_SEALED_CANDIDATE", "candidate-owner:sealed-after-verification"),
    "HUMAN_INTEGRATION": ("human-integration", FulfillmentOwner.HUMAN_GATE,
        FulfillmentPhase.HUMAN_INTEGRATION, "EXACT_HUMAN_AUTHORIZATION", "candidate-governance:human-integration"),
    "HUMAN_DELIVERY_DEPLOY": ("deploy", FulfillmentOwner.DELIVERY_GATE,
        FulfillmentPhase.DELIVERY, "EXACT_HUMAN_AUTHORIZATION", "cloud-delivery:human-authorization-required"),
    "HUMAN_DELIVERY_PUBLISH": ("publish", FulfillmentOwner.DELIVERY_GATE,
        FulfillmentPhase.DELIVERY, "EXACT_HUMAN_AUTHORIZATION", "remote-delivery:human-authorization-required"),
    "RETAIN_CONTEXT": ("retained-context", FulfillmentOwner.PRODUCT_SOURCE,
        FulfillmentPhase.CONTEXT_RETENTION, "RETAIN_AUTHORITATIVE_CONTEXT", "work-reality:retained"),
    "UNRESOLVED": ("unresolved", FulfillmentOwner.UNRESOLVED,
        FulfillmentPhase.UNRESOLVED, "UNRESOLVED", "unresolved:owner-binding"),
}
# Keep the same tuple order as all content routes above.
for _name in ("DENY_PREVIEW", "DENY_DEPLOY", "DENY_PUBLISH"):
    _component, _owner, _gate, _phase, _method = FULFILLMENT_CAPABILITIES[_name]
    FULFILLMENT_CAPABILITIES[_name] = (_component, _owner, _phase, _method, _gate)


def is_context_only_clause(revision, ir, item_id, clause_id, *, bindings=()):
    """Retain a typed descriptive assertion, never hide a current requirement."""
    item = next((item for item in ir.items if item.item_id == item_id), None)
    clause = next((clause for clause in ir.clauses if clause.clause_id == clause_id), None)
    if (item is not None and clause is not None and item.kind is SemanticKind.PRODUCTION_INTENT
            and bindings and _reviewed_background_clause_retained(revision, ir, item_id, clause_id, bindings)):
        return True
    if (item is None or clause is None or item.kind is not SemanticKind.FACT
            or item.action is not None or item.production is not None
            or clause.modality != "ASSERTION" or clause.polarity != "AFFIRMATIVE"
            or clause.requested_effects or item.requires_human):
        return False
    return not any(fact.is_current and (
        fact.provenance.source_text.strip() in clause.source_text
        or clause.source_text.strip() in fact.provenance.source_text)
        for fact in revision.engineering_semantic_facts)


def _current_fact_source_overlaps_clause(revision, quote):
    # Both the primary extraction and original governed provenance may carry a
    # current contribution. An unrelated primary span never erases its sources.
    for fact in revision.engineering_semantic_facts:
        if not fact.is_current:
            continue
        spans = (fact.provenance.source_text, *(source.source_text
            for source in fact.provenance.governed_provenance))
        if any(isinstance(span, str) and span.strip() and (
                span.strip() in quote or quote in span) for span in spans):
            return True
    return False


def _reviewed_background_context_refs(candidate, revision, ir, inventory):
    """Only a reviewed exact background contribution may be retained.

    CURRENT is a source time, not proof that every descriptive span is an
    artifact requirement. The same original production Item must still have
    a different current request bound to its existing current consumer.
    """
    from spg.domain.interaction_actions import ActionSpeechAct
    by_ref = {source["source_ref"]: source for source in inventory["sources"]}
    allowed = set()
    for route in candidate.routes:
        source = by_ref.get(route.source_ref)
        if route.capability != "RETAIN_CONTEXT" or source is None or source["kind"] != "IR_CLAUSE":
            continue
        item = next(item for item in ir.items if item.item_id == source["item_id"])
        clause = next(clause for clause in ir.clauses if clause.clause_id == source["clause_id"])
        basis = route.component_basis
        if (item.kind is not SemanticKind.PRODUCTION_INTENT or item.production is None
                or not item.production.current or item.action is not None or item.requires_human
                or clause.modality != "ASSERTION" or clause.polarity != "AFFIRMATIVE"
                or clause.temporal_scope != "CURRENT" or clause.speech_act is not ActionSpeechAct.DISCUSSION
                or clause.requested_effects or basis is None or basis.linked_fact_refs
                or basis.source_span_start != 0 or basis.source_span_end != len(clause.source_text)
                or basis.source_component_quote != clause.source_text):
            continue
        if _current_fact_source_overlaps_clause(revision, clause.source_text):
            continue
        for current in candidate.routes:
            sibling = by_ref.get(current.source_ref)
            if (current.capability not in {"ARTIFACT_CONTENT", "GIT_DIFF_SCOPE", "PRODUCT_SOURCE_IDENTITY"}
                    or sibling is None or sibling["kind"] not in {"IR_CLAUSE", "IR_CONSTRAINT"}
                    or sibling["item_id"] != item.item_id or sibling["clause_id"] == clause.clause_id):
                continue
            request = next(c for c in ir.clauses if c.clause_id == sibling["clause_id"])
            if (request.temporal_scope == "CURRENT" and request.modality == "REQUEST"
                    and request.polarity == "AFFIRMATIVE"
                    and request.speech_act is ActionSpeechAct.EXPLICIT_REQUEST):
                allowed.add(route.source_ref)
                break
    return frozenset(allowed)


def _reviewed_background_clause_retained(revision, ir, item_id, clause_id, bindings):
    """Consumer recheck of the already admitted full plan; never model Assurance."""
    try:
        first = bindings[0]
        receipt = first.formation_receipt or {}
        if receipt.get("capabilities_fingerprint") != canonical_fingerprint(fulfillment_capability_contracts()):
            return False
        inventory = fulfillment_inventory(revision, ir, source_revision=first.source_revision,
            exact_target_paths=tuple(receipt.get("exact_target_paths", ())))
        inverse = {value: key for key, value in FULFILLMENT_CAPABILITIES.items()}
        from spg.domain.governed_obligation import FulfillmentRouteCandidate
        routes = tuple(FulfillmentRouteCandidate(source_ref=fulfillment_source_ref(binding),
            capability=inverse[(binding.component, binding.owner, binding.phase, binding.evidence_method, binding.gate_ref)],
            work_constraint_indices=binding.work_constraint_indices, target_paths=binding.target_paths,
            supporting_source_refs=binding.supporting_source_refs, component_basis=binding.component_basis,
            rationale="Actual admitted derived plan") for binding in bindings)
        plan = FulfillmentProjectionCandidate(inventory_fingerprint=first.projection_inventory_fingerprint, routes=routes)
        if ({route.source_ref for route in routes} != {source["source_ref"] for source in inventory["sources"]}
                or plan.inventory_fingerprint != inventory["inventory_fingerprint"]):
            return False
        validate_projection_components(plan, inventory, semantic_review=receipt.get("semantic_review"))
        return f"ir-clause:{ir.id}:{item_id}:{clause_id}" in _reviewed_background_context_refs(plan, revision, ir, inventory)
    except (KeyError, ValueError, TypeError, IndexError):
        return False


def state_for_capability(name):
    if name == "UNRESOLVED":
        return "UNRESOLVED"
    if name == "RETAIN_CONTEXT":
        return "RETAINED_CONTEXT"
    return "BOUND_PENDING_EVIDENCE"


def _observed_context_item(item):
    return (item.kind is SemanticKind.FACT and item.action is None
        and item.production is None and not item.requires_human and bool(item.provenance)
        and bool(item.observed_facts)
        and all(p.origin is SemanticOrigin.REPOSITORY_OBSERVED for p in item.provenance))


def _human_clause_item(item, clause):
    # IRK admits each exact Human clause and each Item provenance independently.
    # A shared Item can realize several distinct spans from that same record.
    return any(p.source_record_id == clause.source_record_id and p.source_text
        and p.origin in {SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION}
        for p in item.provenance)


def admitted_clause_source_failure(revision, ir, *, database=None, records=None):
    """Recheck durable Human identity at production, without reinterpreting IRK."""
    if records is None and database is None:
        # Pure contract callers still enforce exact admitted identities below;
        # actual production supplies the existing Interaction Owner database.
        return None
    if records is None:
        from spg.infrastructure.persistence.interaction_store import InteractionStore
        with database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            records = tuple(store.record(record_id) for record_id in revision.source_record_ids)
    by_id = {record.id: record for record in records if record is not None}
    interaction_id = getattr(revision, "source_interaction_id", None)
    if (interaction_id is None or getattr(ir, "interaction_id", None) != interaction_id
            or getattr(ir, "source_record_id", None) not in revision.source_record_ids):
        return "OBLIGATION_ADMITTED_CLAUSE_SOURCE_IDENTITY_INVALID"
    for clause in ir.clauses:
        record = by_id.get(clause.source_record_id)
        if (clause.source_record_id != ir.source_record_id
                or clause.source_record_id not in revision.source_record_ids
                or record is None or record.interaction_id != interaction_id
                or str(record.actor) != "HUMAN" or clause.source_text not in record.content
                or record.content_fingerprint != sha256(record.content.encode()).hexdigest()):
            return "OBLIGATION_ADMITTED_CLAUSE_HUMAN_SOURCE_INVALID"
    for item in ir.items:
        for source in item.provenance:
            if source.origin not in {SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION}:
                continue
            record = by_id.get(source.source_record_id)
            if (record is None or record.interaction_id != interaction_id
                    or str(record.actor) != "HUMAN" or not source.source_text
                    or source.source_text not in record.content
                    or record.content_fingerprint != sha256(record.content.encode()).hexdigest()):
                return "OBLIGATION_ADMITTED_ITEM_HUMAN_SOURCE_INVALID"
    return None


def fulfillment_inventory(revision, ir, *, source_revision=None, exact_target_paths=()):
    """Full immutable source basis; the model only proposes how it is consumed."""
    sources = []
    for fact in revision.engineering_semantic_facts:
        if not fact.is_current:
            continue
        reference = semantic_fact_reference(fact, work_revision_id=revision.id)
        sources.append({"source_ref": f"semantic-fact:{fact.id}", "kind": "FACT",
            "fact_id": str(fact.id), "payload": reference.model_dump(mode="json"),
            "provenance": fact.provenance.model_dump(mode="json")})
    for clause in ir.clauses:
        clause_items = tuple(next((item for item in ir.items if item.item_id == item_id), None)
                             for item_id in clause.semantic_item_ids)
        if any(item is None for item in clause_items):
            raise ValueError("OBLIGATION_SOURCE_ITEM_MISSING")
        human_companion = any(_human_clause_item(item, clause) for item in clause_items)
        for item in clause_items:
            # Observed context is an independent Owner facet, not Human authority.
            # The exact Clause remains represented by its Human companion(s).
            # With no companion its original Clause stays explicitly unresolved.
            if _observed_context_item(item) and human_companion:
                continue
            sources.append({"source_ref": (f"ir-constraint:{item.item_id}:{clause.clause_id}"
                if item.kind is SemanticKind.CONSTRAINT else f"ir-clause:{ir.id}:{item.item_id}:{clause.clause_id}"),
                "kind": "IR_CONSTRAINT" if item.kind is SemanticKind.CONSTRAINT else "IR_CLAUSE", "item_id": item.item_id,
                "clause_id": clause.clause_id,
                "payload": {"ir_id": str(ir.id), "item": item.model_dump(mode="json"),
                            "clause": clause.model_dump(mode="json")}})
    linked_items = {item_id for clause in ir.clauses for item_id in clause.semantic_item_ids}
    for item in ir.items:
        if item.item_id not in linked_items or _observed_context_item(item):
            sources.append({"source_ref": f"ir-item:{ir.id}:{item.item_id}", "kind": "IR_ITEM",
                "item_id": item.item_id, "payload": {"ir_id": str(ir.id), "item": item.model_dump(mode="json")}})
    for kind, values, prefix in (("WORK_CONSTRAINT", revision.constraints, "work-constraint"),
            ("WORK_CONTEXT", getattr(revision, "context_facts", ()), "work-context")):
        for index, content in enumerate(values):
            sources.append({"source_ref": f"{prefix}:{revision.id}:{index}", "kind": kind,
                "index": index, "payload": {"work_reality_revision_id": str(revision.id),
                    "index": index, "content": content, "content_digest": sha256(content.encode()).hexdigest()}})
    refs = tuple(item["source_ref"] for item in sources)
    if not refs or len(refs) != len(set(refs)):
        raise ValueError("OBLIGATION_SOURCE_INVENTORY_INVALID")
    target_paths = tuple(exact_target_paths) or tuple(dict.fromkeys(
        arg.value for goal in ir.current_production for arg in goal.target_paths))
    from spg.domain.change import safe_repository_path
    for path in target_paths:
        safe_repository_path(path)
    basis = {"work_id": str(revision.work_id), "work_reality_revision_id": str(revision.id),
        "work_revision_fingerprint": revision.revision_fingerprint,
        "semantic_ir_id": str(ir.id),
        "source_revision": source_revision or revision.source_revision or revision.revision_fingerprint,
        "source_record_ids": [str(value) for value in revision.source_record_ids],
        "sources": sources,
        "work_constraints": [{"index": index, "content": content,
                              "content_digest": sha256(content.encode()).hexdigest()}
                             for index, content in enumerate(revision.constraints)],
        "context_facts": list(getattr(revision, "context_facts", ())),
        "exact_target_paths": list(target_paths),
        "production_intents": [goal.model_dump(mode="json") for goal in ir.current_production]}
    return {**basis, "inventory_fingerprint": canonical_fingerprint(basis)}


def _capability_tuple(name):
    route = FULFILLMENT_CAPABILITIES.get(name)
    if route is None:
        raise ValueError("OBLIGATION_OWNER_CAPABILITY_UNSUPPORTED")
    return route


def _projection_binding(revision, ir, inventory, route, *, reviewed_background_refs=(),
                        allow_calibrated=False, background_components=()):
    source = next((item for item in inventory["sources"] if item["source_ref"] == route.source_ref), None)
    if source is None:
        raise ValueError("OBLIGATION_SOURCE_REFERENCE_SUBSTITUTED")
    component, owner, phase, method, gate = _capability_tuple(route.capability)
    from spg.domain.governed_obligation import fulfillment_component_id
    partial_background = fulfillment_component_id(route, inventory["inventory_fingerprint"]) in background_components
    if len(set(route.work_constraint_indices)) != len(route.work_constraint_indices) or any(
            index < 0 or index >= len(revision.constraints) for index in route.work_constraint_indices):
        raise ValueError("OBLIGATION_WORK_CONSTRAINT_REFERENCE_INVALID")
    if len(set(route.target_paths)) != len(route.target_paths) or set(route.target_paths) - set(inventory["exact_target_paths"]):
        raise ValueError("OBLIGATION_SCOPE_EXPANSION")
    if method == "EXACT_GIT_DIFF_SCOPE" and tuple(route.target_paths) != tuple(inventory["exact_target_paths"]):
        raise ValueError("OBLIGATION_DIFF_SCOPE_INCOMPLETE")
    if source["kind"] == "WORK_CONSTRAINT":
        if route.work_constraint_indices != (source["index"],):
            raise ValueError("OBLIGATION_WORK_CONSTRAINT_SOURCE_MISMATCH")
    elif route.work_constraint_indices:
        raise ValueError("OBLIGATION_WORK_CONSTRAINT_SOURCE_MISMATCH")
    if len(set(route.supporting_source_refs)) != len(route.supporting_source_refs) or any(
            ref not in {entry["source_ref"] for entry in inventory["sources"]}
            for ref in route.supporting_source_refs):
        raise ValueError("OBLIGATION_SUPPORTING_SOURCE_SUBSTITUTED")
    if method == "EXACT_CANDIDATE_CONTENT" and not route.target_paths:
        raise ValueError("OBLIGATION_CONTENT_TARGET_UNRESOLVED")
    state = "UNRESOLVED" if owner is FulfillmentOwner.UNRESOLVED else (
        "RETAINED_CONTEXT" if phase is FulfillmentPhase.CONTEXT_RETENTION else "BOUND_PENDING_EVIDENCE")
    common = dict(component=component, owner=owner, phase=phase, evidence_method=method,
        gate_ref=gate, source_revision=inventory["source_revision"], target_paths=route.target_paths,
        projection_inventory_fingerprint=inventory["inventory_fingerprint"],
        work_constraint_indices=route.work_constraint_indices,
        supporting_source_refs=route.supporting_source_refs, state=state,
        component_basis=route.component_basis)
    if source["kind"] in {"WORK_CONSTRAINT", "WORK_CONTEXT", "IR_ITEM"}:
        if source["kind"] == "IR_ITEM":
            item = next(item for item in ir.items if item.item_id == source["item_id"])
            origins = {p.origin for p in item.provenance}
            if state == "RETAINED_CONTEXT" and (item.kind is not SemanticKind.FACT
                    or item.action is not None or item.production is not None
                    or item.requires_human or origins != {SemanticOrigin.REPOSITORY_OBSERVED}):
                raise ValueError("OBLIGATION_UNLINKED_ITEM_NOT_OBSERVED_CONTEXT")
            if state not in {"UNRESOLVED", "RETAINED_CONTEXT"}:
                raise ValueError("OBLIGATION_UNLINKED_ITEM_CAPABILITY_UNRESOLVED")
            records = tuple(dict.fromkeys(p.source_record_id for p in item.provenance if p.source_record_id is not None))
            quote = item.statement
            provenance = [p.model_dump(mode="json") for p in item.provenance]
            item_id = item.item_id
        else:
            records = tuple(revision.source_record_ids)
            quote = source["payload"]["content"]
            provenance = {"work_reality_revision_id": str(revision.id),
                          "source_record_ids": [str(value) for value in records]}
            item_id = str(source["index"])
            if source["kind"] == "WORK_CONTEXT" and state not in {"UNRESOLVED", "RETAINED_CONTEXT"}:
                raise ValueError("OBLIGATION_CONTEXT_CANNOT_AUTHORIZE_EFFECT")
            if source["kind"] == "WORK_CONSTRAINT":
                supporting = [entry for entry in inventory["sources"] if entry["source_ref"] in route.supporting_source_refs]
                clauses = [next(c for c in ir.clauses if c.clause_id == entry["clause_id"])
                           for entry in supporting if entry["kind"] in {"IR_CLAUSE", "IR_CONSTRAINT"}]
                if state != "UNRESOLVED" and not work_constraint_sources_correspond(ir, quote, supporting, component=component,
                        phase=phase, semantic_component_declared=route.component_basis is not None,
                        calibrated=allow_calibrated):
                    raise ValueError("OBLIGATION_SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN")
                if state == "RETAINED_CONTEXT":
                    if not partial_background and (not supporting or not all(entry["kind"] == "IR_CLAUSE" and is_context_only_clause(
                            revision, ir, entry["item_id"], entry["clause_id"]) for entry in supporting)):
                        raise ValueError("OBLIGATION_REQUIRED_CONSTRAINT_CANNOT_BE_CONTEXT_ONLY")
                if phase is FulfillmentPhase.CONTINUOUS_FROM_ADMISSION:
                    if not clauses or not any(c.polarity == "NEGATED" and c.temporal_scope == "CURRENT" for c in clauses):
                        raise ValueError("OBLIGATION_PERMISSION_REQUIRES_EXACT_CLAUSE")
                if phase in {FulfillmentPhase.CANDIDATE_SEAL, FulfillmentPhase.HUMAN_INTEGRATION, FulfillmentPhase.DELIVERY}:
                    if not clauses or any(c.polarity != "AFFIRMATIVE" for c in clauses):
                        raise ValueError("OBLIGATION_FUTURE_PHASE_SOURCE_UNPROVEN")
                if method == "EXACT_PRODUCT_SOURCE_IDENTITY":
                    raise ValueError("OBLIGATION_SOURCE_IDENTITY_RELATION_MISMATCH")
        return FulfillmentBinding(source_kind=FulfillmentSourceKind(source["kind"]),
            semantic_ir_id=ir.id, constraint_item_id=item_id, constraint_clause_id=None,
            constraint_fingerprint=canonical_fingerprint(source["payload"]),
            work_reality_revision_id=revision.id, provenance_fingerprint=canonical_fingerprint(provenance),
            source_record_ids=records, source_quote=quote, **common)
    if source["kind"] == "FACT":
        fact = next(fact for fact in revision.engineering_semantic_facts if str(fact.id) == source["fact_id"])
        if phase is FulfillmentPhase.CONTINUOUS_FROM_ADMISSION:
            # A Boolean Fact alone cannot invent the effect's semantic identity.
            # Bind new continuous routes to the admitted typed clause instead.
            if not (allow_calibrated and route.component_basis is not None
                    and _fact_prohibition_sources(revision, ir, inventory, fact, route)):
                raise ValueError("OBLIGATION_PERMISSION_REQUIRES_EXACT_CLAUSE")
        from spg.domain.engineering_semantics import SemanticRelation, SemanticReferenceRole
        if state == "RETAINED_CONTEXT" and not _fact_context_retention_eligible(fact):
            raise ValueError("OBLIGATION_CURRENT_FACT_CANNOT_BE_CONTEXT_ONLY")
        if phase in {FulfillmentPhase.CANDIDATE_SEAL, FulfillmentPhase.HUMAN_INTEGRATION, FulfillmentPhase.DELIVERY} and fact.relation is not SemanticRelation.ACCEPTANCE_ASSERTION:
            raise ValueError("OBLIGATION_CURRENT_FACT_CANNOT_BE_DEFERRED")
        if state != "UNRESOLVED":
            if (fact.relation is SemanticRelation.SCOPE and fact.qualifiers.get("negated") is True
                    and method not in {"EXACT_GIT_DIFF_SCOPE", "EXACT_PERMISSION_GATE"}):
                raise ValueError("OBLIGATION_NEGATED_SCOPE_EVIDENCE_OWNER_MISMATCH")
            if (fact.relation is SemanticRelation.REFERENCE
                    and fact.reference_role is SemanticReferenceRole.PROJECT_REPOSITORY
                    and method != "EXACT_PRODUCT_SOURCE_IDENTITY"):
                raise ValueError("OBLIGATION_PROJECT_SOURCE_OWNER_MISMATCH")
            original_scope_paths = exact_file_scope_paths(fact, qualified=allow_calibrated) if fact.relation is SemanticRelation.SCOPE else None
            if (original_scope_paths is not None and set(original_scope_paths) == set(inventory["exact_target_paths"])
                    and method != "EXACT_GIT_DIFF_SCOPE"):
                raise ValueError("OBLIGATION_FILE_SCOPE_OWNER_MISMATCH")
            if (fact.relation is SemanticRelation.SCOPE and original_scope_paths is None
                    and method == "EXACT_CANDIDATE_CONTENT" and route.component_basis is None):
                raise ValueError("OBLIGATION_SCOPE_COMPONENT_UNRESOLVED")
        method_failure = _fact_evidence_method_failure(fact, method)
        if method_failure:
            raise ValueError(method_failure)
        if method == "EXACT_GIT_DIFF_SCOPE":
            original_paths = exact_file_scope_paths(fact, qualified=allow_calibrated)
            negative_scope = (allow_calibrated and route.component_basis is not None
                and _fact_prohibition_sources(revision, ir, inventory, fact, route))
            if original_paths is None and not negative_scope:
                raise ValueError("OBLIGATION_FACT_SCOPE_VALUE_UNSUPPORTED")
            if original_paths is not None and set(route.target_paths) != set(original_paths):
                raise ValueError("OBLIGATION_FACT_SCOPE_VALUE_MISMATCH")
            if negative_scope:
                values = (fact.value,) if isinstance(fact.value, str) else fact.value if isinstance(fact.value, (list, tuple)) else ()
                if any(value in route.target_paths for value in values):
                    raise ValueError("OBLIGATION_NEGATED_SCOPE_TARGET_CONFLICT")
        if fact.epistemic_status.value == "UNRESOLVED" and state != "UNRESOLVED":
            raise ValueError("OBLIGATION_UNRESOLVED_FACT_PROMOTION")
        return bind_admitted_fact(reference=semantic_fact_reference(fact, work_revision_id=revision.id),
            admitted=fact, source_quote=fact.provenance.source_text,
            **{key: value for key, value in common.items() if key in {
                "component", "owner", "phase", "evidence_method", "gate_ref", "source_revision", "target_paths"}}).model_copy(update=common)
    item = next(item for item in ir.items if item.item_id == source["item_id"])
    clause = next(clause for clause in ir.clauses if clause.clause_id == source["clause_id"])
    valid_clause_source = (clause.source_record_id in revision.source_record_ids
        and item.item_id in clause.semantic_item_ids
        and (not hasattr(ir, "source_record_id") or clause.source_record_id == ir.source_record_id)
        and _human_clause_item(item, clause))
    if state != "UNRESOLVED" and not valid_clause_source:
        raise ValueError("OBLIGATION_CLAUSE_PROVENANCE_INVALID")
    # A nonpromoting unresolved representation preserves the original source IDs
    # and quote even when authority is insufficient; it grants no execution Gate.
    if (state == "RETAINED_CONTEXT" and not partial_background and route.source_ref not in reviewed_background_refs
            and not is_context_only_clause(revision, ir, item.item_id, clause.clause_id)):
        raise ValueError("OBLIGATION_CURRENT_CLAUSE_CANNOT_BE_CONTEXT_ONLY")
    if phase is FulfillmentPhase.CONTINUOUS_FROM_ADMISSION:
        if clause.polarity != "NEGATED" or clause.temporal_scope != "CURRENT":
            raise ValueError("OBLIGATION_PERMISSION_POLARITY_CONFLICT")
        if (component == "preview" and any(goal.preview_required for goal in ir.current_production)) or (
                component in {"deploy", "publish"} and any(goal.delivery_authorized for goal in ir.current_production)):
            raise ValueError("OBLIGATION_EFFECT_AUTHORITY_CONFLICT")
    if phase in {FulfillmentPhase.CANDIDATE_SEAL, FulfillmentPhase.HUMAN_INTEGRATION} and (
            not ir.current_production or not all(goal.acceptance_required for goal in ir.current_production)):
        raise ValueError("OBLIGATION_CANDIDATE_GATE_NOT_REQUIRED")
    if phase in {FulfillmentPhase.CANDIDATE_SEAL, FulfillmentPhase.HUMAN_INTEGRATION, FulfillmentPhase.DELIVERY} and clause.polarity == "NEGATED":
        raise ValueError("OBLIGATION_PROHIBITION_CANNOT_BE_FUTURE_PERMISSION")
    if item.requires_human and state not in {"UNRESOLVED", "RETAINED_CONTEXT"}:
        raise ValueError("OBLIGATION_UNRESOLVED_AUTHORITY_PROMOTION")
    return FulfillmentBinding(source_kind=(FulfillmentSourceKind.IR_CONSTRAINT
            if item.kind is SemanticKind.CONSTRAINT else FulfillmentSourceKind.IR_CLAUSE),
        semantic_ir_id=ir.id, constraint_item_id=item.item_id, constraint_clause_id=clause.clause_id,
        constraint_fingerprint=canonical_fingerprint(source["payload"]),
        work_reality_revision_id=revision.id,
        provenance_fingerprint=canonical_fingerprint([p.model_dump(mode="json") for p in item.provenance]),
        source_record_ids=(clause.source_record_id,), source_quote=clause.source_text, **common)


def _fact_context_retention_eligible(fact):
    from spg.domain.engineering_semantics import SemanticRelation, SemanticReferenceRole
    return (bool(fact.provenance.governed_provenance) and all(
        p.origin is SemanticOrigin.REPOSITORY_OBSERVED for p in fact.provenance.governed_provenance)) or (
        fact.relation is SemanticRelation.REFERENCE
        and fact.reference_role is SemanticReferenceRole.EXTERNAL_REFERENCE)


def _fact_evidence_method_failure(fact, method):
    """Typed Owner prerequisites shared by admission and repair observations."""
    from spg.domain.engineering_semantics import SemanticRelation, SemanticReferenceRole
    if method == "EXACT_GIT_DIFF_SCOPE" and fact.relation is not SemanticRelation.SCOPE:
        return "OBLIGATION_FACT_EVIDENCE_METHOD_MISMATCH"
    if method == "EXACT_PRODUCT_SOURCE_IDENTITY" and (
            fact.relation is not SemanticRelation.REFERENCE
            or fact.reference_role is not SemanticReferenceRole.PROJECT_REPOSITORY):
        return "OBLIGATION_SOURCE_IDENTITY_RELATION_MISMATCH"
    return None


def _work_constraint_direct_source(ir, quote, entry):
    """Existing exact correspondence predicate, shared with repair diagnostics."""
    if entry["kind"] not in {"IR_CLAUSE", "IR_CONSTRAINT"}:
        return False
    item = next(i for i in ir.items if i.item_id == entry["item_id"])
    return quote == item.statement or quote == entry["payload"]["clause"]["source_text"] or (
        item.production is not None and quote in item.production.scope)


def _work_constraint_exclusion_sources(ir, quote, entries):
    return [(entry, value) for entry in entries if entry["kind"] in {"IR_CLAUSE", "IR_CONSTRAINT"}
        for item in ir.items if item.item_id == entry["item_id"] and item.production is not None
        for value in item.production.exclusions if quote == f"Excluded from this Work: {value}"]


def work_constraint_sources_correspond(ir, quote, entries, *, component, phase, semantic_component_declared=False, calibrated=False):
    """Prove exact original source support, never classify wrapper vocabulary."""
    if entries and all(_work_constraint_direct_source(ir, quote, entry) for entry in entries):
        return True
    production_values = _work_constraint_exclusion_sources(ir, quote, entries)
    if not production_values:
        return False
    values = {value for _, value in production_values}
    production_refs = {entry["source_ref"] for entry, _ in production_values}
    others = [entry for entry in entries if entry["source_ref"] not in production_refs]
    if (phase is not FulfillmentPhase.CONTINUOUS_FROM_ADMISSION
            and not (calibrated and semantic_component_declared and phase is FulfillmentPhase.CURRENT_VERIFICATION
                     and component == "git-diff-scope")) or not others:
        return False
    for entry in others:
        if entry["kind"] not in {"IR_CLAUSE", "IR_CONSTRAINT"}:
            return False
        clause = next(c for c in ir.clauses if c.clause_id == entry["clause_id"])
        routes = [_TYPED_EFFECT_ROUTES.get(effect) for effect in clause.requested_effects]
        if (clause.polarity != "NEGATED" or clause.temporal_scope != "CURRENT"
                or not semantic_component_declared and not all(value in clause.source_text for value in values)
                or not any(route is not None and route[0] == component for route in routes)
                   and not (calibrated and semantic_component_declared and not clause.requested_effects)):
            return False
    return True


def _fact_prohibition_sources(revision, ir, inventory, fact, route):
    """Exact Fact -> original negative clause identity; no invented typed effect."""
    if (fact.relation.value != "SCOPE" or fact.qualifiers != {"negated": True}
            or type(fact.qualifiers.get("negated")) is not bool
            or fact.epistemic_status.value != "CONFIRMED"
            or fact.authority.value != "HUMAN_EXPLICIT"
            or not route.supporting_source_refs):
        return False
    refs = {s["source_ref"]: s for s in inventory["sources"]}
    for ref in route.supporting_source_refs:
        entry = refs.get(ref)
        if entry is None or entry["kind"] not in {"IR_CONSTRAINT", "IR_CLAUSE"}:
            return False
        clause = next(c for c in ir.clauses if c.clause_id == entry["clause_id"])
        item = next(i for i in ir.items if i.item_id == entry["item_id"])
        if (clause.polarity != "NEGATED" or clause.temporal_scope != "CURRENT"
                or clause.source_record_id not in fact.provenance.source_record_ids
                or not _human_clause_item(item, clause)):
            return False
        if route.capability != "GIT_DIFF_SCOPE" and clause.requested_effects and not any(
                (_TYPED_EFFECT_ROUTES.get(effect) or (None,))[0] == _capability_tuple(route.capability)[0]
                for effect in clause.requested_effects):
            return False
    if (route.capability == "DENY_PREVIEW" and any(g.preview_required for g in ir.current_production)
            or route.capability in {"DENY_DEPLOY", "DENY_PUBLISH"} and any(g.delivery_authorized for g in ir.current_production)):
        return False
    return True


def locate_projection_components(candidate, inventory):
    """Locate a unique exact quote; repair offsets only, never source meaning."""
    sources = {source["source_ref"]: source for source in inventory["sources"]}
    routes, adjustments = [], []
    for route in candidate.routes:
        basis = route.component_basis
        if basis is None or route.source_ref not in sources:
            routes.append(route)
            continue
        text = fulfillment_source_semantic_text(sources[route.source_ref])
        start, end = basis.source_span_start, basis.source_span_end
        if 0 <= start < end <= len(text) and text[start:end] == basis.source_component_quote:
            routes.append(route)
            continue
        quote = basis.source_component_quote
        located = text.find(quote)
        if located < 0:
            raise ValueError("OBLIGATION_COMPONENT_SOURCE_QUOTE_DRIFT")
        if text.find(quote, located + 1) >= 0:
            raise ValueError("OBLIGATION_COMPONENT_SOURCE_LOCATION_AMBIGUOUS")
        canonical = basis.model_copy(update={"source_span_start": located, "source_span_end": located + len(quote)})
        routes.append(route.model_copy(update={"component_basis": canonical}))
        adjustments.append({"source_ref": route.source_ref, "capability": route.capability,
            "raw_span": [start, end], "canonical_span": [located, located + len(quote)],
            "quote_sha256": sha256(quote.encode()).hexdigest(), "method": "UNIQUE_EXACT_SOURCE_QUOTE"})
    return candidate.model_copy(update={"routes": tuple(routes)}), tuple(adjustments)


def validate_projection_components(candidate, inventory, *, semantic_review=None, allow_review_pending=False):
    if not any(route.component_basis is not None for route in candidate.routes):
        return
    if any(route.component_basis is None for route in candidate.routes):
        raise ValueError("OBLIGATION_COMPONENT_INVENTORY_INCOMPLETE")
    facts = {source["source_ref"] for source in inventory["sources"] if source["kind"] == "FACT"}
    for source in inventory["sources"]:
        text = fulfillment_source_semantic_text(source)
        covered = set()
        for route in candidate.routes:
            if route.source_ref != source["source_ref"]:
                continue
            basis = route.component_basis
            if (basis.source_span_start < 0 or basis.source_span_end > len(text) or basis.source_span_start >= basis.source_span_end
                    or text[basis.source_span_start:basis.source_span_end] != basis.source_component_quote):
                raise ValueError("OBLIGATION_COMPONENT_SOURCE_QUOTE_DRIFT")
            if len(set(basis.linked_fact_refs)) != len(basis.linked_fact_refs) or set(basis.linked_fact_refs) - facts:
                raise ValueError("OBLIGATION_COMPONENT_FACT_REFERENCE_SUBSTITUTED")
            covered.update(range(basis.source_span_start, basis.source_span_end))
        if any(not char.isspace() and index not in covered for index, char in enumerate(text)):
            raise ValueError("OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST")
    if semantic_review is None:
        if allow_review_pending:
            return
        raise ValueError("OBLIGATION_SEMANTIC_REVIEW_REQUIRED")
    result = FulfillmentSemanticReviewCandidate.model_validate(semantic_review)
    refs = [row.source_ref for row in result.source_results]
    if (result.inventory_fingerprint != inventory["inventory_fingerprint"]
            or result.candidate_fingerprint != fulfillment_candidate_fingerprint(candidate)
            or result.components_fingerprint != fulfillment_components_fingerprint(candidate)
            or len(refs) != len(set(refs)) or set(refs) != {s["source_ref"] for s in inventory["sources"]}):
        raise ValueError("OBLIGATION_SEMANTIC_REVIEW_IDENTITY_DRIFT")
    if not all(row.complete_and_equivalent for row in result.source_results):
        raise ValueError("OBLIGATION_SEMANTIC_COMPONENT_MISMATCH")
    if result.component_results is not None:
        from spg.domain.governed_obligation import fulfillment_component_id
        expected = {(fulfillment_component_id(route, inventory["inventory_fingerprint"]), route.capability)
                    for route in candidate.routes}
        keys = [(row.component_id, row.capability) for row in result.component_results]
        if len(keys) != len(set(keys)) or set(keys) != expected:
            raise ValueError("OBLIGATION_COMPONENT_REVIEW_IDENTITY_DRIFT")
        if not all(row.complete_and_equivalent and row.nonredundant and row.owner_phase_evidence_valid
                   and row.context_only == (row.capability == "RETAIN_CONTEXT") for row in result.component_results):
            raise ValueError("OBLIGATION_SEMANTIC_COMPONENT_MISMATCH")


def _partial_background_components(candidate, revision, ir, inventory):
    """Only distinct non-Fact background with a still-present required component.

    This structural eligibility is not semantic approval. New mixed dispositions
    additionally require the independent per-component review before admission.
    """
    from spg.domain.governed_obligation import fulfillment_component_id
    result = set()
    by_ref = {s["source_ref"]: s for s in inventory["sources"]}
    for route in candidate.routes:
        source = by_ref.get(route.source_ref)
        basis = route.component_basis
        if (route.capability != "RETAIN_CONTEXT" or basis is None or source is None
                or source["kind"] not in {"IR_CLAUSE", "IR_CONSTRAINT", "WORK_CONSTRAINT"}
                or basis.linked_fact_refs or basis.source_component_quote == fulfillment_source_semantic_text(source)
                or _current_fact_source_overlaps_clause(revision, basis.source_component_quote)):
            continue
        if any(other.source_ref == route.source_ref and other.capability not in {"RETAIN_CONTEXT", "UNRESOLVED"}
               and other.component_basis is not None and other.component_basis != basis for other in candidate.routes):
            result.add(fulfillment_component_id(route, inventory["inventory_fingerprint"]))
    return frozenset(result)


def _fact_gate_correspondence_missing(route, candidate, inventory):
    """Same predicate for admission and unadmitted Owner observations."""
    source = next(s for s in inventory["sources"] if s["source_ref"] == route.source_ref)
    negative_git = (source["kind"] == "FACT" and route.capability == "GIT_DIFF_SCOPE"
        and source["payload"]["qualifiers"].get("negated") is True)
    if source["kind"] != "FACT" or not (route.capability in {"DENY_PREVIEW", "DENY_DEPLOY", "DENY_PUBLISH"} or negative_git):
        return ()
    return tuple(ref for ref in route.supporting_source_refs if not any(
        other.source_ref == ref and other.capability == route.capability for other in candidate.routes))


def validate_projection_candidate(candidate, revision, ir, inventory, *, semantic_review=None, allow_review_pending=False):
    if candidate.inventory_fingerprint != inventory["inventory_fingerprint"]:
        raise ValueError("OBLIGATION_PROJECTION_STALE_BASIS")
    from spg.domain.governed_obligation import fulfillment_component_id
    identities = [(fulfillment_component_id(route, inventory["inventory_fingerprint"]), route.capability) for route in candidate.routes]
    if len(identities) != len(set(identities)):
        raise ValueError("OBLIGATION_PROJECTION_DUPLICATE_ROUTE")
    if {route.source_ref for route in candidate.routes} != {source["source_ref"] for source in inventory["sources"]}:
        raise ValueError("OBLIGATION_SOURCE_INVENTORY_INCOMPLETE")
    if {index for route in candidate.routes for index in route.work_constraint_indices} != set(range(len(revision.constraints))):
        raise ValueError("OBLIGATION_WORK_CONSTRAINT_INVENTORY_INCOMPLETE")
    # Disposition belongs to the component, not an entire mixed source. Identical
    # physical contribution cannot evade a conflict by changing supporting links.
    for ref in {route.source_ref for route in candidate.routes}:
        routes = [route for route in candidate.routes if route.source_ref == ref]
        for index, route in enumerate(routes):
            for other in routes[index + 1:]:
                same = (route.component_basis is None or other.component_basis is None or
                    (route.component_basis.source_span_start, route.component_basis.source_span_end, route.component_basis.source_component_quote)
                    == (other.component_basis.source_span_start, other.component_basis.source_span_end, other.component_basis.source_component_quote))
                if same and route.capability != other.capability and {route.capability, other.capability} & {"UNRESOLVED", "RETAIN_CONTEXT"}:
                    raise ValueError("OBLIGATION_PROJECTION_CONFLICTING_DISPOSITION")
    for source in inventory["sources"]:
        if source["kind"] not in {"IR_CONSTRAINT", "IR_CLAUSE"}:
            continue
        clause = next(clause for clause in ir.clauses if clause.clause_id == source["clause_id"])
        proposed = {route.capability for route in candidate.routes if route.source_ref == source["source_ref"]}
        for effect in clause.requested_effects:
            typed = _TYPED_EFFECT_ROUTES.get(effect)
            if typed is None:
                if effect.startswith(("PROHIBIT_", "RESTRICT_")) and proposed != {"UNRESOLVED"}:
                    raise ValueError("OBLIGATION_TYPED_EFFECT_ROUTE_UNRESOLVED")
                continue
            component, owner, gate, phase, method, _polarity = typed
            required = next(key for key, value in FULFILLMENT_CAPABILITIES.items()
                if value == (component, owner, phase, method, gate))
            if required not in proposed and proposed != {"UNRESOLVED"}:
                raise ValueError("OBLIGATION_TYPED_EFFECT_LOST")
    from spg.domain.engineering_semantics import SemanticRelation
    for source in inventory["sources"]:
        if source["kind"] in {"IR_ITEM", "WORK_CONTEXT"}:
            continue
        methods = {route.capability for route in candidate.routes if route.source_ref == source["source_ref"]}
        if methods & {"CANDIDATE_SEAL", "HUMAN_INTEGRATION", "HUMAN_DELIVERY_DEPLOY", "HUMAN_DELIVERY_PUBLISH"}:
            # A mixed acceptance assertion may defer only its future component.
            future_only = (source["kind"] in {"IR_CLAUSE", "IR_CONSTRAINT"}
                and next(c for c in ir.clauses if c.clause_id == source["clause_id"]).temporal_scope == "FUTURE")
            if source["kind"] == "WORK_CONSTRAINT":
                supports = {ref for route in candidate.routes if route.source_ref == source["source_ref"]
                            for ref in route.supporting_source_refs}
                entries = [entry for entry in inventory["sources"] if entry["source_ref"] in supports]
                future_only = bool(entries) and all(entry["kind"] in {"IR_CLAUSE", "IR_CONSTRAINT"}
                    and next(c for c in ir.clauses if c.clause_id == entry["clause_id"]).temporal_scope == "FUTURE"
                    for entry in entries)
            component_declared = all(route.component_basis is not None for route in candidate.routes
                if route.source_ref == source["source_ref"])
            if not future_only and not component_declared and "ARTIFACT_CONTENT" not in methods:
                raise ValueError("OBLIGATION_MIXED_FACT_CURRENT_COMPONENT_LOST")
    validate_projection_components(candidate, inventory, semantic_review=semantic_review, allow_review_pending=allow_review_pending)
    reviewed_background_refs = _reviewed_background_context_refs(candidate, revision, ir, inventory)
    partial_background = _partial_background_components(candidate, revision, ir, inventory)
    bindings = tuple(_projection_binding(revision, ir, inventory, route,
        reviewed_background_refs=reviewed_background_refs, allow_calibrated=route.component_basis is not None,
        background_components=partial_background) for route in candidate.routes)
    legacy_ids = [(route.source_ref, route.capability) for route in candidate.routes]
    calibrated = len(set(legacy_ids)) != len(legacy_ids) or bool(partial_background)
    for route in candidate.routes:
        methods = {r.capability for r in candidate.routes if r.source_ref == route.source_ref}
        calibrated |= bool(methods & {"UNRESOLVED", "RETAIN_CONTEXT"} and len(methods) > 1)
        try:
            _projection_binding(revision, ir, inventory, route, reviewed_background_refs=reviewed_background_refs)
        except ValueError:
            calibrated = True
    if calibrated and not allow_review_pending and (
            semantic_review is None or FulfillmentSemanticReviewCandidate.model_validate(semantic_review).component_results is None):
        raise ValueError("OBLIGATION_COMPONENT_REVIEW_REQUIRED")
    # A Fact prohibition cites an actual clause route with the same Owner/Gate.
    for route in candidate.routes:
        if _fact_gate_correspondence_missing(route, candidate, inventory):
            raise ValueError("OBLIGATION_FACT_GATE_CORRESPONDENCE_UNPROVEN")
    return bindings


def validate_fulfillment_projection(bindings, revision, ir, *, source_revision=None, exact_target_paths=()):
    first = bindings[0]
    expected_source = source_revision or revision.source_revision or revision.revision_fingerprint
    if first.source_revision != expected_source:
        raise ValueError("OBLIGATION_PROJECTION_SOURCE_REVISION_DRIFT")
    inventory = fulfillment_inventory(revision, ir, source_revision=expected_source,
                                     exact_target_paths=exact_target_paths)
    inverse = {route: key for key, route in FULFILLMENT_CAPABILITIES.items()}
    from spg.domain.governed_obligation import FulfillmentRouteCandidate
    routes = []
    for binding in bindings:
        key = inverse.get((binding.component, binding.owner, binding.phase, binding.evidence_method, binding.gate_ref))
        if key is None:
            raise ValueError("OBLIGATION_OWNER_CAPABILITY_UNSUPPORTED")
        routes.append(FulfillmentRouteCandidate(source_ref=fulfillment_source_ref(binding), capability=key,
            work_constraint_indices=binding.work_constraint_indices, target_paths=binding.target_paths,
            supporting_source_refs=binding.supporting_source_refs, component_basis=binding.component_basis,
            rationale="Revalidate persisted projection against immutable owner sources."))
    if any(route.component_basis is not None for route in routes) and (
            first.formation_receipt is None or first.formation_receipt.get("capabilities_fingerprint") != canonical_fingerprint(fulfillment_capability_contracts())):
        raise ValueError("OBLIGATION_SEMANTIC_REVIEW_CAPABILITIES_DRIFT")
    expected = validate_projection_candidate(FulfillmentProjectionCandidate(
        inventory_fingerprint=first.projection_inventory_fingerprint, routes=tuple(routes)), revision, ir, inventory,
        semantic_review=None if first.formation_receipt is None else first.formation_receipt.get("semantic_review"))
    for actual, wanted in zip(bindings, expected):
        if actual.model_dump(exclude={"formation_receipt"}) != wanted.model_dump(exclude={"formation_receipt"}):
            raise ValueError("OBLIGATION_GATE_BINDING_DRIFT")
    if any(binding.state == "UNRESOLVED" for binding in bindings):
        raise ValueError("OBLIGATION_PROJECTION_UNRESOLVED")


def projection_validation_feedback(candidate, revision, ir, inventory, primary_error, *, wire_diagnostics=None):
    """Bounded observations on one immutable candidate, never a patched plan.

    Only independently evaluable predicates are collected; consumer execution
    and independent review cannot be inferred from structural checks.
    """
    from spg.domain.governed_obligation import fulfillment_component_id
    def stable(error):
        match = re.search(r"\bOBLIGATION_[A-Z0-9_]+\b", str(error))
        return match.group() if match else "OBLIGATION_CANDIDATE_SCHEMA_INVALID"
    primary = stable(primary_error)
    if wire_diagnostics is not None:
        return json.dumps({"schema": "fulfillment-validation-feedback-v2",
            "inventory_fingerprint": inventory["inventory_fingerprint"], "primary_error": primary,
            "violations": wire_diagnostics["violations"],
            "additional_violation_count": wire_diagnostics["additional_violation_count"],
            "not_evaluable": wire_diagnostics["not_evaluable"],
            "coverage_not_evaluable_sources": wire_diagnostics.get("coverage_not_evaluable_sources", []),
            "wire_diagnostic_binding": {**wire_diagnostics["binding"],
                "diagnostic_fingerprint": wire_diagnostics["diagnostic_fingerprint"]}}, separators=(",", ":"))
    failures = []
    refs = {s["source_ref"]: index for index, s in enumerate(inventory["sources"])}
    seen = set()
    def add(code, route=None, source=None):
        row = {"code": code}
        if source is not None: row["source"] = source
        if route is not None:
            r = candidate.routes[route]
            row.update(route=route, source=refs.get(r.source_ref),
                component_id=fulfillment_component_id(r, inventory["inventory_fingerprint"]))
        if row not in failures: failures.append(row)
    if candidate is not None:
        background = _reviewed_background_context_refs(candidate, revision, ir, inventory)
        partial = _partial_background_components(candidate, revision, ir, inventory)
        for index, route in enumerate(candidate.routes):
            key = (fulfillment_component_id(route, inventory["inventory_fingerprint"]), route.capability)
            if key in seen: add("OBLIGATION_PROJECTION_DUPLICATE_ROUTE", index)
            seen.add(key)
            if route.source_ref not in refs:
                add("OBLIGATION_SOURCE_REFERENCE_SUBSTITUTED", index)
                continue
            try:
                _projection_binding(revision, ir, inventory, route, reviewed_background_refs=background,
                    allow_calibrated=route.component_basis is not None, background_components=partial)
            except ValueError as error:
                add(stable(error), index)
            basis = route.component_basis
            if basis is not None:
                text = fulfillment_source_semantic_text(inventory["sources"][refs[route.source_ref]])
                if not 0 <= basis.source_span_start < basis.source_span_end <= len(text) or text[basis.source_span_start:basis.source_span_end] != basis.source_component_quote:
                    add("OBLIGATION_COMPONENT_SOURCE_QUOTE_DRIFT", index)
                facts = {s["source_ref"] for s in inventory["sources"] if s["kind"] == "FACT"}
                if len(set(basis.linked_fact_refs)) != len(basis.linked_fact_refs) or set(basis.linked_fact_refs) - facts:
                    add("OBLIGATION_COMPONENT_FACT_REFERENCE_SUBSTITUTED", index)
            for other in candidate.routes[:index]:
                if other.source_ref != route.source_ref or other.capability == route.capability: continue
                if {route.capability, other.capability} & {"UNRESOLVED", "RETAIN_CONTEXT"} and (
                        route.component_basis is None or other.component_basis is None or (
                        route.component_basis.source_span_start, route.component_basis.source_span_end, route.component_basis.source_component_quote) == (
                        other.component_basis.source_span_start, other.component_basis.source_span_end, other.component_basis.source_component_quote)):
                    add("OBLIGATION_PROJECTION_CONFLICTING_DISPOSITION", index)
        for source, entry in enumerate(inventory["sources"]):
            routes = [r for r in candidate.routes if r.source_ref == entry["source_ref"]]
            if not routes:
                add("OBLIGATION_SOURCE_INVENTORY_INCOMPLETE", source=source)
            elif any(r.component_basis is not None for r in candidate.routes):
                text = fulfillment_source_semantic_text(entry)
                covered = set()
                for route in routes:
                    if route.component_basis is not None:
                        covered.update(range(max(0, route.component_basis.source_span_start), min(len(text), route.component_basis.source_span_end)))
                if any(not char.isspace() and index not in covered for index, char in enumerate(text)):
                    add("OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST", source=source)
    return json.dumps({"schema": "fulfillment-validation-feedback-v2", "inventory_fingerprint": inventory["inventory_fingerprint"],
        "primary_error": primary, "violations": failures[:64], "additional_violation_count": max(0, len(failures)-64),
        "not_evaluable": ["INDEPENDENT_SEMANTIC_REVIEW", "ACTUAL_OWNER_EVIDENCE", "ASSURANCE"]}, separators=(",", ":"))


def calibrated_background_binding_permitted(binding, revision, ir, bindings):
    """Consumer revalidates the complete admitted plan before retaining a part."""
    from spg.domain.governed_obligation import fulfillment_component_id
    if (not bindings or binding.source_kind.value not in {"IR_CLAUSE", "IR_CONSTRAINT", "WORK_CONSTRAINT"}
            or binding.component_basis is None or binding.component_basis.source_component_quote == binding.source_quote):
        return False
    receipt = bindings[0].formation_receipt or {}
    try:
        validate_fulfillment_projection(bindings, revision, ir, source_revision=binding.source_revision,
            exact_target_paths=tuple(receipt.get("exact_target_paths", ())))
        review = FulfillmentSemanticReviewCandidate.model_validate(receipt.get("semantic_review"))
        return review.component_results is not None and any(row.component_id == fulfillment_component_id(
            binding, binding.projection_inventory_fingerprint) and row.capability == "RETAIN_CONTEXT"
            and row.context_only for row in review.component_results)
    except (ValueError, TypeError, KeyError):
        return False


def deterministic_fulfillment_projection(revision, ir, inventory):
    """Reuse only existing typed relation/effect contracts, never classify prose."""
    from spg.domain.governed_obligation import FulfillmentRouteCandidate
    from spg.domain.engineering_semantics import SemanticRelation, SemanticReferenceRole
    routes = []
    by_source = {}
    for source in inventory["sources"]:
        methods = ["UNRESOLVED"]
        supporting = ()
        if source["kind"] == "FACT":
            fact = next(fact for fact in revision.engineering_semantic_facts if str(fact.id) == source["fact_id"])
            if fact.epistemic_status.value != "UNRESOLVED":
                if fact.relation is SemanticRelation.REFERENCE:
                    if fact.reference_role is SemanticReferenceRole.PROJECT_REPOSITORY:
                        methods = ["PRODUCT_SOURCE_IDENTITY"]
                    elif (fact.reference_role is SemanticReferenceRole.EXTERNAL_REFERENCE
                            or (fact.provenance.governed_provenance and all(p.origin is SemanticOrigin.REPOSITORY_OBSERVED
                                for p in fact.provenance.governed_provenance))):
                        methods = ["RETAIN_CONTEXT"]
                elif fact.relation is SemanticRelation.SCOPE and exact_file_scope_paths(fact) is not None and set(exact_file_scope_paths(fact)) == set(inventory["exact_target_paths"]):
                    methods = ["GIT_DIFF_SCOPE"]
                elif fact.relation in {SemanticRelation.EQUALITY, SemanticRelation.CARDINALITY,
                        SemanticRelation.ORDERED_COMPONENT, SemanticRelation.BOUND, SemanticRelation.COMPARISON,
                        SemanticRelation.MAPPING, SemanticRelation.PRECEDENCE} and inventory["exact_target_paths"]:
                    methods = ["ARTIFACT_CONTENT"]
        elif source["kind"] in {"IR_CONSTRAINT", "IR_CLAUSE"}:
            clause = next(clause for clause in ir.clauses if clause.clause_id == source["clause_id"])
            if clause.requested_effects and all(effect in _TYPED_EFFECT_ROUTES for effect in clause.requested_effects):
                methods = []
                for effect in clause.requested_effects:
                    component, owner, gate, phase, method, _ = _TYPED_EFFECT_ROUTES[effect]
                    methods.append(next(key for key, value in FULFILLMENT_CAPABILITIES.items()
                        if value == (component, owner, phase, method, gate)))
                methods = list(dict.fromkeys(methods))
            elif is_context_only_clause(revision, ir, source["item_id"], source["clause_id"]):
                methods = ["RETAIN_CONTEXT"]
        elif source["kind"] == "IR_ITEM":
            item = next(item for item in ir.items if item.item_id == source["item_id"])
            if item.kind is SemanticKind.FACT and item.action is None and item.production is None and not item.requires_human and all(
                    p.origin is SemanticOrigin.REPOSITORY_OBSERVED for p in item.provenance):
                methods = ["RETAIN_CONTEXT"]
        elif source["kind"] == "WORK_CONTEXT":
            methods = ["RETAIN_CONTEXT"]
        elif source["kind"] == "WORK_CONSTRAINT":
            matches = [entry for entry in inventory["sources"] if entry["kind"] in {"IR_CONSTRAINT", "IR_CLAUSE"}
                and entry["payload"]["item"]["statement"] == source["payload"]["content"]]
            if matches and all(by_source.get(entry["source_ref"], ["UNRESOLVED"]) != ["UNRESOLVED"] for entry in matches):
                methods = list(dict.fromkeys(method for entry in matches for method in by_source[entry["source_ref"]]))
                supporting = tuple(entry["source_ref"] for entry in matches)
        by_source[source["source_ref"]] = methods
        routes.extend(FulfillmentRouteCandidate(source_ref=source["source_ref"], capability=method,
            work_constraint_indices=(source["index"],) if source["kind"] == "WORK_CONSTRAINT" else (),
            target_paths=tuple(inventory["exact_target_paths"]) if method in {"ARTIFACT_CONTENT", "GIT_DIFF_SCOPE"} else (),
            supporting_source_refs=supporting,
            rationale="Existing typed relation/effect contract; unsupported meaning retained unresolved.") for method in methods)
    candidate = FulfillmentProjectionCandidate(inventory_fingerprint=inventory["inventory_fingerprint"], routes=tuple(routes))
    try:
        return validate_projection_candidate(candidate, revision, ir, inventory)
    except ValueError:
        # Deterministic capability reuse never overrides a source/authority guard.
        return unresolved_projection(revision, ir, inventory, reason="OBLIGATION_TYPED_CONTRACT_NOT_COMPLETE")


def unresolved_projection(revision, ir, inventory, *, reason, receipt=None):
    from spg.domain.governed_obligation import FulfillmentRouteCandidate
    routes = tuple(FulfillmentRouteCandidate(source_ref=source["source_ref"], capability="UNRESOLVED",
        work_constraint_indices=(source["index"],) if source["kind"] == "WORK_CONSTRAINT" else (),
        rationale=reason) for index, source in enumerate(inventory["sources"]))
    bindings = validate_projection_candidate(FulfillmentProjectionCandidate(
        inventory_fingerprint=inventory["inventory_fingerprint"], routes=routes), revision, ir, inventory)
    return (bindings[0].model_copy(update={"formation_receipt": receipt or {
        "terminal_reason": reason, "exact_target_paths": inventory["exact_target_paths"]}}), *bindings[1:])



class FulfillmentReceiptCapacityStop(RuntimeError):
    """The existing receipt Owner has already persisted a terminal limit."""


class FulfillmentFormationReceipts:
    """Append derived observations to the existing Work plan JSON Owner record."""
    def __init__(self, revision, inventory, *, database=None, memory=None):
        self.revision, self.inventory, self.database = revision, inventory, database
        self.memory = memory if memory is not None else []

    def records(self):
        rows = self.memory
        if self.database is not None:
            from spg.infrastructure.persistence.runtime_store import RuntimeStore
            with self.database.unit_of_work() as uow:
                rows = tuple(record.scope for record in RuntimeStore(uow.session).governance_for_subject(
                    self.inventory["inventory_fingerprint"])
                    if record.decision_type == "WORK_FULFILLMENT_OBSERVATION"
                    and record.authority_identity == "work-governance:derived-candidate-observation"
                    and record.subject_type == "WORK_FULFILLMENT_BASIS")
            # The authoritative query already scoped the subject. A corrupt
            # scope fingerprint must remain visible to identity validation,
            # not disappear and reopen a model/budget slot.
            return rows
        return tuple(row for row in rows if row.get("inventory_fingerprint") == self.inventory["inventory_fingerprint"])

    def append(self, stage, attempt, **values):
        from datetime import UTC, datetime
        from uuid import uuid4
        from spg.providers.verification_receipts import _safe_value
        row = {"schema": "work-fulfillment-formation-receipt-v1", "receipt_id": str(uuid4()),
            "owner": "WORK_FULFILLMENT_PROJECTION", "stage": stage, "attempt": attempt,
            "work_id": str(self.revision.work_id), "work_reality_revision_id": str(self.revision.id),
            "inventory_fingerprint": self.inventory["inventory_fingerprint"],
            "source_revision": self.inventory["source_revision"],
            "exact_target_paths": self.inventory["exact_target_paths"],
            "recorded_at_utc": datetime.now(UTC).isoformat(), "budget_limit": 2,
            "candidate_is_authority": False, **_safe_value(values)}
        if row.get("terminal") and not row.get("validation_passed"):
            row["unresolved_source_refs"] = [source["source_ref"] for source in self.inventory["sources"]]
        if len(json.dumps(row, ensure_ascii=False, default=str).encode()) > 131072:
            row = {key: value for key, value in row.items() if key not in {"candidate", "candidate_output", "feedback"}}
            row.update(terminal=True, validation_passed=False, terminal_reason="OBLIGATION_FORMATION_RECEIPT_LIMIT",
                unresolved_source_refs=[source["source_ref"] for source in self.inventory["sources"]])
        if self.database is None:
            prior = self.records()
            self._check_append(prior, stage, attempt)
            self.memory.append(row)
        else:
            from spg.infrastructure.persistence.product_store import ProductStore
            with self.database.unit_of_work() as uow:
                store = ProductStore(uow.session)
                work = store.work(self.revision.work_id, for_update=True)
                if (work is None or work.current_work_reality_revision_id != self.revision.id):
                    raise ValueError("OBLIGATION_FORMATION_RECEIPT_OWNER_CHANGED")
                from spg.infrastructure.persistence.runtime_store import RuntimeStore
                runtime = RuntimeStore(uow.session)
                prior = tuple(record.scope for record in runtime.governance_for_subject(self.inventory["inventory_fingerprint"])
                    if record.decision_type == "WORK_FULFILLMENT_OBSERVATION"
                    and record.authority_identity == "work-governance:derived-candidate-observation"
                    and record.subject_type == "WORK_FULFILLMENT_BASIS")
                self._check_append(prior, stage, attempt)
                runtime.insert_governance({"id": uuid4(), "decision_type": "WORK_FULFILLMENT_OBSERVATION",
                    "authority_identity": "work-governance:derived-candidate-observation",
                    "subject_type": "WORK_FULFILLMENT_BASIS", "subject_identity": self.inventory["inventory_fingerprint"],
                    "scope": row, "rationale": "Derived candidate observation; grants no Human authority, PASS or effect.",
                    "created_at": datetime.now(UTC)})
                if work.production_plan is not None:
                    all_rows = work.production_plan.fulfillment_formation_receipts
                    plan = work.production_plan.model_copy(update={"fulfillment_formation_receipts": (*all_rows, row)})
                    store.update_work(work.id, {"production_plan_proposal": plan.model_dump(mode="json")})
                uow.commit()
        if row.get("terminal_reason") == "OBLIGATION_FORMATION_RECEIPT_LIMIT":
            # Stop before any further model/review or receipt append. The row is
            # durable first, so the ordinary terminal replay remains authoritative.
            raise FulfillmentReceiptCapacityStop("OBLIGATION_FORMATION_RECEIPT_LIMIT")
        return row

    @staticmethod
    def _check_append(prior, stage, attempt):
        if any(row.get("terminal") for row in prior):
            raise ValueError("OBLIGATION_FORMATION_PENDING_OR_TERMINAL")
        if stage == "SEMANTIC_REVIEW_PENDING":
            if (any(row["stage"] == stage and row["attempt"] == attempt for row in prior)
                    or not any(row["stage"] == "MODEL_RESPONSE_OBSERVED" and row["attempt"] == attempt for row in prior)):
                raise ValueError("OBLIGATION_SEMANTIC_REVIEW_BUDGET_EXHAUSTED")
        if stage != "MODEL_REQUEST_PENDING":
            return
        pending = [row for row in prior if row["stage"] == stage]
        validated = {row["attempt"] for row in prior if row["stage"] == "CANDIDATE_VALIDATED"}
        if any(row.get("terminal") for row in prior) or any(row["attempt"] not in validated for row in pending):
            raise ValueError("OBLIGATION_FORMATION_PENDING_OR_TERMINAL")
        if len(pending) >= 2 or attempt != len(pending) + 1:
            raise ValueError("OBLIGATION_FORMATION_BUDGET_EXHAUSTED")


def _wire_response_basis(rows, attempt, revision, inventory, capabilities):
    """Bind unadmitted wire to existing durable request/response observations."""
    from spg.providers.fulfillment_candidate import (
        _FULFILLMENT_WIRE_METADATA_KEYS, _fulfillment_wire_context, _FulfillmentWireReceiptIdentityError)
    def drift():
        raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
    starts = [row for row in rows if row.get("stage") == "MODEL_REQUEST_PENDING" and row.get("attempt") == attempt]
    observed = [row for row in rows if row.get("stage") == "MODEL_RESPONSE_OBSERVED" and row.get("attempt") == attempt]
    if len(starts) != 1 or len(observed) != 1 or type(attempt) is not int or attempt not in (1, 2):
        drift()
    start, response = starts[0], observed[0]
    owner_contract = start.get("owner_repair_context_contract")
    if (response.get("owner_repair_context_contract") != owner_contract
            or owner_contract not in (None, "existing-owner-preconditions-v1")):
        drift()
    basis = {"work_id": str(revision.work_id), "work_reality_revision_id": str(revision.id),
        "inventory_fingerprint": inventory["inventory_fingerprint"],
        "source_revision": inventory["source_revision"], "exact_target_paths": inventory["exact_target_paths"]}
    if (any(row.get(key) != value for row in (start, response) for key, value in basis.items())
            or any(type(row.get("attempt")) is not int or row["attempt"] != attempt for row in (start, response))):
        drift()
    ids = [row.get("receipt_id") for row in rows]
    if (not isinstance(start.get("receipt_id"), str) or not isinstance(response.get("receipt_id"), str)
            or ids.count(start["receipt_id"]) != 1 or ids.count(response["receipt_id"]) != 1):
        drift()
    preconditions = start.get("owner_source_preconditions")
    if response.get("owner_source_preconditions") != preconditions:
        drift()
    context = _fulfillment_wire_context(inventory, capabilities, validation_feedback=start.get("feedback"),
        owner_preconditions=preconditions)
    if any(row.get(key) != context[key] for row in (start, response) for key in _FULFILLMENT_WIRE_METADATA_KEYS):
        drift()
    raw = response.get("candidate_output")
    if not isinstance(raw, str) or response.get("candidate_retained") is not True:
        drift()
    raw_bytes = raw.encode("utf-8")
    output_fingerprint = sha256(raw_bytes).hexdigest()
    if response.get("candidate_output_sha256") != output_fingerprint or response.get("candidate_output_bytes") != len(raw_bytes):
        drift()
    model = response.get("model")
    if isinstance(model, dict) and any(model.get(key, wanted) != wanted for key, wanted in
            (("output_sha256", output_fingerprint), ("output_bytes", len(raw_bytes)))):
        drift()
    return raw, {**basis, "attempt": attempt, "wire_output_fingerprint": output_fingerprint,
        "request_receipt_id": start["receipt_id"], "response_receipt_id": response["receipt_id"],
        **({"owner_repair_context_contract": owner_contract} if owner_contract is not None else {}),
        **({"owner_source_preconditions_fingerprint": canonical_fingerprint(preconditions)} if preconditions is not None else {}),
        **{key: context[key] for key in _FULFILLMENT_WIRE_METADATA_KEYS}}


def _bind_wire_diagnostics(error, rows, attempt, revision, inventory, capabilities):
    from spg.providers.fulfillment_candidate import _FULFILLMENT_WIRE_METADATA_KEYS, _FulfillmentWireReceiptIdentityError
    from spg.providers.verification_receipts import _safe_value
    _, binding = _wire_response_basis(rows, attempt, revision, inventory, capabilities)
    diagnostics = error.diagnostics
    if (any(diagnostics.get(key) != binding[key] for key in
            ("wire_output_fingerprint", "inventory_fingerprint", *_FULFILLMENT_WIRE_METADATA_KEYS))
            or _safe_value(diagnostics) != diagnostics):
        raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
    bound = {**diagnostics, "binding": binding}
    return {**bound, "diagnostic_fingerprint": canonical_fingerprint(bound)}


def _owner_source_preconditions(revision, ir, inventory, capabilities, *, include_syntax_observations=True,
                                syntax_observation_contract="complete-value-owner-observations-v1",
                                include_operand_observations=True, include_typed_observations=True,
                                typed_prerequisite_contract="existing-owner-typed-prerequisites-v3"):
    """Necessary proof sets from existing Owner predicates, never route proposals.

    The semantic boundary still chooses components and which eligible origin
    actually proves their meaning. Structural eligibility is not equivalence,
    evidence satisfaction, independent review or authority.
    """
    from types import SimpleNamespace
    sources = inventory["sources"]
    clauses = {c.clause_id: c for c in ir.clauses}
    rows = []
    for index, source in enumerate(sources):
        row = {"source": index, "source_ref": source["source_ref"],
            "primary_component_required": True, "supporting_reference_does_not_cover_source": True}
        if source["kind"] in {"IR_CLAUSE", "IR_CONSTRAINT"}:
            clause = clauses[source["clause_id"]]
            row.update(polarity=clause.polarity, temporal_scope=clause.temporal_scope,
                speech_act=clause.speech_act,
                whole_source_context_only=is_context_only_clause(revision, ir, source["item_id"], source["clause_id"]),
                partial_context_rule="DISTINCT_CURRENT_COMPONENT_AND_INDEPENDENT_SEMANTIC_REVIEW_REQUIRED")
        proofs = []
        for cap_index, contract in enumerate(capabilities):
            capability = contract["capability"]
            component, _, phase, method, _ = _capability_tuple(capability)
            supports = []
            if source["kind"] == "FACT":
                fact = next(f for f in revision.engineering_semantic_facts if str(f.id) == source["fact_id"])
                if (phase is FulfillmentPhase.CONTINUOUS_FROM_ADMISSION
                        or method == "EXACT_GIT_DIFF_SCOPE" and fact.qualifiers.get("negated") is True):
                    supports = [[j] for j, entry in enumerate(sources)
                        if _fact_prohibition_sources(revision, ir, inventory, fact,
                            SimpleNamespace(capability=capability, supporting_source_refs=(entry["source_ref"],)))]
            elif source["kind"] == "WORK_CONSTRAINT" and phase not in {
                    FulfillmentPhase.CONTEXT_RETENTION} and method not in {
                    "EXACT_PRODUCT_SOURCE_IDENTITY", "UNRESOLVED"} and capability != "UNRESOLVED":
                quote = source["payload"]["content"]
                direct = [[j] for j, entry in enumerate(sources) if _work_constraint_direct_source(ir, quote, entry)]
                origins = {entry["source_ref"] for entry, _ in _work_constraint_exclusion_sources(ir, quote, sources)}
                proposed_sets = direct + [[j,k] for j,entry in enumerate(sources) if entry["source_ref"] in origins
                    for k,other in enumerate(sources) if other["source_ref"] not in origins
                    and other["kind"] in {"IR_CLAUSE", "IR_CONSTRAINT"}]
                for indices in proposed_sets:
                    entries = [sources[j] for j in indices]
                    original_clauses = [clauses[e["clause_id"]] for e in entries if e["kind"] in {"IR_CLAUSE", "IR_CONSTRAINT"}]
                    if not work_constraint_sources_correspond(ir, quote, entries, component=component, phase=phase,
                            semantic_component_declared=True, calibrated=True):
                        continue
                    if (phase is FulfillmentPhase.CONTINUOUS_FROM_ADMISSION
                            and not any(c.polarity == "NEGATED" and c.temporal_scope == "CURRENT" for c in original_clauses)):
                        continue
                    if phase in {FulfillmentPhase.CANDIDATE_SEAL, FulfillmentPhase.HUMAN_INTEGRATION, FulfillmentPhase.DELIVERY} and (
                            not original_clauses or any(c.polarity != "AFFIRMATIVE" for c in original_clauses)):
                        continue
                    supports.append(sorted(indices))
            if supports:
                proofs.append({"capability": cap_index, "minimal_support_sets": sorted({tuple(s) for s in supports})})
        if proofs:
            # JSON lists make durable recomputation identical across restarts.
            row["necessary_source_proofs"] = [{**p,"minimal_support_sets":[list(s) for s in p["minimal_support_sets"]]} for p in proofs]
        if source["kind"] == "FACT":
            paths = exact_file_scope_paths(fact, qualified=True) if fact.relation.value == "SCOPE" else None
            if paths is not None and set(paths) == set(inventory["exact_target_paths"]):
                row["necessary_evidence_method"] = "EXACT_GIT_DIFF_SCOPE"
        if include_typed_observations:
            rejected = []
            for cap_index, contract in enumerate(capabilities):
                _, _, phase, method, _ = _capability_tuple(contract["capability"])
                codes = []
                if source["kind"] == "FACT":
                    row["original_fact_type"] = {"relation": fact.relation.value,
                        "reference_role": fact.reference_role.value if fact.reference_role else None}
                    failure = _fact_evidence_method_failure(fact, method)
                    if failure:
                        codes.append(failure)
                    if (typed_prerequisite_contract in {"existing-owner-typed-prerequisites-v2", "existing-owner-typed-prerequisites-v3"}
                            and method == "RETAIN_AUTHORITATIVE_CONTEXT" and not _fact_context_retention_eligible(fact)):
                        codes.append("OBLIGATION_CURRENT_FACT_CANNOT_BE_CONTEXT_ONLY")
                    if (phase in {FulfillmentPhase.CANDIDATE_SEAL, FulfillmentPhase.HUMAN_INTEGRATION,
                                  FulfillmentPhase.DELIVERY} and fact.relation.value != "ACCEPTANCE_ASSERTION"):
                        codes.append("OBLIGATION_CURRENT_FACT_CANNOT_BE_DEFERRED")
                if (source["kind"] == "WORK_CONSTRAINT"
                        and not any(p["capability"] == cap_index for p in proofs)
                        and contract["capability"] not in {"RETAIN_CONTEXT", "UNRESOLVED"}):
                    codes.append("OBLIGATION_SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN")
                if source["kind"] in {"IR_CLAUSE", "IR_CONSTRAINT"}:
                    if phase is FulfillmentPhase.CONTINUOUS_FROM_ADMISSION and (
                            clause.polarity != "NEGATED" or clause.temporal_scope != "CURRENT"):
                        codes.append("OBLIGATION_PERMISSION_POLARITY_CONFLICT")
                    if phase in {FulfillmentPhase.CANDIDATE_SEAL, FulfillmentPhase.HUMAN_INTEGRATION,
                                 FulfillmentPhase.DELIVERY} and clause.polarity == "NEGATED":
                        codes.append("OBLIGATION_PROHIBITION_CANNOT_BE_FUTURE_PERMISSION")
                if codes:
                    rejected.append({"capability": cap_index, "codes": codes})
            row["ineligible_binding_prerequisites"] = rejected
            if source["kind"] == "FACT" and typed_prerequisite_contract == "existing-owner-typed-prerequisites-v3":
                # Observe the actual side-effect-free Fact consumer rather than
                # maintain a second, incomplete list of its typed restrictions.
                # Probe operands establish only necessary structural eligibility.
                # These temporary routes are never returned, admitted or stored.
                from spg.domain.governed_obligation import FulfillmentRouteCandidate, FulfillmentComponentBasis
                text = fulfillment_source_semantic_text(source)
                rejected = []
                for cap_index, contract in enumerate(capabilities):
                    method = _capability_tuple(contract["capability"])[3]
                    alternatives = next((p["minimal_support_sets"] for p in proofs if p["capability"] == cap_index), [[]])
                    errors = []
                    for indices in alternatives:
                        probe = FulfillmentRouteCandidate(source_ref=source["source_ref"], capability=contract["capability"],
                            target_paths=tuple(inventory["exact_target_paths"]) if method in {
                                "EXACT_GIT_DIFF_SCOPE", "EXACT_CANDIDATE_CONTENT"} else (),
                            supporting_source_refs=tuple(sources[j]["source_ref"] for j in indices),
                            component_basis=FulfillmentComponentBasis(source_span_start=0, source_span_end=len(text),
                                source_component_quote=text, linked_fact_refs=(source["source_ref"],)),
                            rationale="Necessary existing Owner predicate observation; not a semantic proposal or admission.")
                        try:
                            _projection_binding(revision, ir, inventory, probe, allow_calibrated=True)
                            break
                        except ValueError as error:
                            code = re.search(r"\bOBLIGATION_[A-Z0-9_]+\b", str(error))
                            errors.append(code.group() if code else "OBLIGATION_OWNER_PREREQUISITE_NOT_EVALUABLE")
                    else:
                        rejected.append({"capability": cap_index, "codes": sorted(set(errors))})
                row["ineligible_binding_prerequisites"] = rejected
        rows.append(row)
    return {"contract": "existing-owner-source-prerequisites-v1", "inventory_fingerprint": inventory["inventory_fingerprint"],
        **({"syntax_observation_contract": syntax_observation_contract} if include_syntax_observations else {}),
        **({"typed_prerequisite_contract": typed_prerequisite_contract,
            "typed_prerequisite_rule": "These are necessary restrictions of the existing Owner, not semantic "
                "route proposals or a complete eligibility list. Absence of a rejection does not prove permission. "
                "A Fact's CARDINALITY or other relation cannot become SCOPE through a file qualifier, "
                "support citation or rationale. A current prohibition cannot become a future permission. "
                "Choose a legal semantic treatment; never rewrite the admitted Fact or borrow authority."}
           if include_typed_observations else {}),
        **({"operand_observation_contract": "existing-owner-operands-v1",
            "fact_support_route_rule": "A negative Fact bound to a permission gate or Git Diff must cite "
                "original supporting clauses whose own primary routes include the SAME capability. "
                "A supporting citation alone does not bind that clause to the gate.",
            "capability_operand_requirements": [
                {"capability": index, "evidence_method": _capability_tuple(contract["capability"])[3],
                 "target_operand": {"field": "t", "relation": "EXACT_ORDERED_SET",
                    "required_ordinals": list(range(len(inventory["exact_target_paths"]))),
                    "meaning": "COMPLETE_ADMITTED_CHANGE_ALLOWLIST; NOT_EXCLUDED_PATHS_OR_EFFECTS"}}
                for index, contract in enumerate(capabilities)
                if _capability_tuple(contract["capability"])[3] == "EXACT_GIT_DIFF_SCOPE"] + ([
                {"capability": index, "evidence_method": "EXACT_CANDIDATE_CONTENT",
                 "target_operand": {"field": "t", "relation": "NONEMPTY_ADMITTED_SUBSET",
                    "allowed_ordinals": list(range(len(inventory["exact_target_paths"]))),
                    "minimum_count": 1, "meaning": "SEMANTICALLY_APPLICABLE_ADMITTED_CONTENT_TARGETS"}}
                for index, contract in enumerate(capabilities)
                if _capability_tuple(contract["capability"])[3] == "EXACT_CANDIDATE_CONTENT"]
                if include_typed_observations and typed_prerequisite_contract in {
                    "existing-owner-typed-prerequisites-v2", "existing-owner-typed-prerequisites-v3"} else []),
            "support_operand_rule": "EACH_MINIMAL_SUPPORT_SET_IS_A_CONJUNCTION; SETS_ARE_ALTERNATIVES. "
                "For a derived Work constraint, the production origin proves derivation and the current "
                "negative clause proves the prohibition. One cannot substitute for the other. "
                "An eligible proof does not establish semantic equivalence or allow unrelated extra supports. "
                "Select meaning and components yourself; rationale does not supply missing wire operands."}
           if include_operand_observations else {}),
        "work_reality_revision_id": str(revision.id), "source_revision": inventory["source_revision"],
        "capabilities_fingerprint": canonical_fingerprint(capabilities), "sources": rows,
        "component_rule": "COMPLETE_OWN_SOURCE_SPANS; NO_CONFLICTING_DISPOSITION_FOR_SAME_COMPONENT",
        "meaning": "NECESSARY_PROVENANCE_ONLY; SEMANTIC_MATCH_AND_COMPLETE_PLAN_UNPROVEN; NO_PERMISSION_OR_EVIDENCE_PASS"}


def _owner_repair_context(raw, revision, ir, inventory, capabilities, *, validation_feedback, owner_preconditions=None):
    """Expose existing Owner prerequisites on the exact unadmitted proposal.

    Supporting provenance is not primary-source component coverage. These
    observations neither propose routes nor grant evidence, review or authority.
    Invalid/unlocated raw routes stay non-evaluable instead of being repaired.
    """
    from types import SimpleNamespace
    from spg.providers.fulfillment_candidate import _fulfillment_wire_route_observations
    observations, unavailable = _fulfillment_wire_route_observations(raw, inventory, capabilities,
        validation_feedback=validation_feedback, owner_preconditions=owner_preconditions)
    diagnostic_view = SimpleNamespace(routes=tuple(route for _, _, route in observations))
    evaluated = json.loads(projection_validation_feedback(diagnostic_view, revision, ir, inventory,
        "OBLIGATION_OWNER_PRECONDITIONS_UNPROVEN"))
    if ((owner_preconditions or {}).get("operand_observation_contract") == "existing-owner-operands-v1"
            and not unavailable):
        from spg.domain.governed_obligation import fulfillment_component_id
        for ordinal, (_, _, route) in enumerate(observations):
            missing = _fact_gate_correspondence_missing(route, diagnostic_view, inventory)
            if missing:
                evaluated["violations"].append({"code": "OBLIGATION_FACT_GATE_CORRESPONDENCE_UNPROVEN",
                    "route": ordinal, "source": next(i for i,s in enumerate(inventory["sources"]) if s["source_ref"] == route.source_ref),
                    "component_id": fulfillment_component_id(route, inventory["inventory_fingerprint"]),
                    "missing_same_capability_source_ordinals": [next(i for i,s in enumerate(inventory["sources"]) if s["source_ref"] == ref) for ref in missing]})
    failures = []
    for failure in evaluated["violations"]:
        if unavailable and failure["code"] in {
                "OBLIGATION_CURRENT_CLAUSE_CANNOT_BE_CONTEXT_ONLY",
                "OBLIGATION_REQUIRED_CONSTRAINT_CANNOT_BE_CONTEXT_ONLY"}:
            # A malformed sibling cannot prove or disprove mixed background
            # eligibility. The full plan must be evaluated after valid decode.
            continue
        if "route" in failure:
            index, wire_route, route = observations[failure["route"]]
            failure.update(route=index, raw_route_fingerprint=canonical_fingerprint(wire_route))
            if (owner_preconditions or {}).get("operand_observation_contract") == "existing-owner-operands-v1":
                requirements = owner_preconditions["capability_operand_requirements"]
                cap_index = next(i for i,c in enumerate(capabilities) if c["capability"] == route.capability)
                required = next((r for r in requirements if r["capability"] == cap_index), None)
                details = {"capability": cap_index, "evidence_method": _capability_tuple(route.capability)[3],
                    "disposition": "NECESSARY_OPERANDS_ONLY; SEMANTIC_MATCH_AND_EVIDENCE_NOT_EVALUATED"}
                if required is not None:
                    target = required["target_operand"]
                    if target["relation"] == "EXACT_ORDERED_SET":
                        expected = target["required_ordinals"]
                        details["target_operand"] = {**target,
                            "observed_ordinals": wire_route["t"],
                            "missing_ordinals": [i for i in expected if i not in wire_route["t"]],
                            "unexpected_ordinals": [i for i in wire_route["t"] if i not in expected],
                            "matches": wire_route["t"] == expected}
                    else:
                        details["target_operand"] = {**target,"observed_ordinals": wire_route["t"],
                            "observed_count": len(wire_route["t"]),
                            "matches": bool(wire_route["t"]) and set(wire_route["t"]).issubset(target["allowed_ordinals"]),
                            "semantic_target_selection": "NOT_EVALUATED"}
                primary = next(r for r in owner_preconditions["sources"] if r["source_ref"] == route.source_ref)
                if owner_preconditions.get("typed_prerequisite_contract") in {
                        "existing-owner-typed-prerequisites-v1", "existing-owner-typed-prerequisites-v2", "existing-owner-typed-prerequisites-v3"}:
                    details["typed_prerequisites"] = {
                        "source_kind": next(s["kind"] for s in inventory["sources"] if s["source_ref"] == route.source_ref),
                        "original_fact_type": primary.get("original_fact_type"),
                        "rejected_binding": next((r for r in primary["ineligible_binding_prerequisites"]
                            if r["capability"] == cap_index), None),
                        "scope_method_requirement": "EXACT_GIT_DIFF_SCOPE_REQUIRES_FACT_RELATION_SCOPE",
                        "meaning": "EXISTING_OWNER_PREREQUISITES; NOT_SEMANTIC_CLASSIFICATION_OR_EVIDENCE"}
                proof = next((p for p in primary.get("necessary_source_proofs", []) if p["capability"] == cap_index), None)
                if proof is not None:
                    selected = wire_route["u"]
                    details["support_operand"] = {"field": "u", "observed_ordinals": selected,
                        "relation": "ALL_REQUIRED_PROOF_MEMBERS; ALTERNATIVE_PROOF_SETS",
                        "minimal_support_sets": proof["minimal_support_sets"],
                        "missing_members_by_alternative": [[i for i in s if i not in selected]
                            for s in proof["minimal_support_sets"]],
                        "semantic_equivalence": "NOT_EVALUATED"}
                failure["owner_operand_observations"] = details
        # Invalid raw routes must not be reported as absent sources: the
        # authoritative raw coverage diagnostics already identify that boundary.
        elif unavailable:
            continue
        failures.append(failure)
    additional_count = evaluated["additional_violation_count"] + max(0, len(failures) - 64)
    sources = inventory["sources"]
    refs = {entry["source_ref"]: index for index, entry in enumerate(sources)}
    prerequisites = []
    for index, source in enumerate(sources):
        row = {"source": index, "source_ref": source["source_ref"],
            "primary_component_required": True,
            "supporting_reference_does_not_cover_source": True}
        if source["kind"] == "WORK_CONSTRAINT":
            quote = source["payload"]["content"]
            row.update(exact_corresponding_source_ordinals=[refs[e["source_ref"]] for e in sources
                    if _work_constraint_direct_source(ir, quote, e)],
                exact_exclusion_derivation_source_ordinals=sorted({refs[e["source_ref"]]
                    for e, _ in _work_constraint_exclusion_sources(ir, quote, sources)}),
                correspondence_rule="ALL_SELECTED_SUPPORTS_MUST_PROVE_EXACT_CORRESPONDENCE_OR_EXISTING_EXCLUSION_DERIVATION",
                exclusion_rule="ORIGINAL_PRODUCTION_EXCLUSION_AND_CURRENT_NEGATIVE_CLAUSE_WITH_COMPATIBLE_COMPONENT_AND_PHASE",
                permission_rule="CURRENT_NEGATIVE_ORIGINAL_CLAUSE_REQUIRED",
                future_gate_rule="AFFIRMATIVE_ORIGINAL_CLAUSE_AND_EXISTING_LIFECYCLE_GATE_REQUIRED")
        if source["kind"] == "FACT":
            fact = next(f for f in revision.engineering_semantic_facts if str(f.id) == source["fact_id"])
            paths = exact_file_scope_paths(fact, qualified=True) if fact.relation.value == "SCOPE" else None
            if paths is not None and set(paths) == set(inventory["exact_target_paths"]):
                row["necessary_evidence_method"] = "EXACT_GIT_DIFF_SCOPE"
            if fact.relation.value == "SCOPE" and fact.qualifiers.get("negated") is True:
                row["necessary_evidence_methods"] = ["EXACT_GIT_DIFF_SCOPE", "EXACT_PERMISSION_GATE"]
                row["permission_rule"] = "EXACT_HUMAN_NEGATIVE_CURRENT_CLAUSE_WITH_FACT_PROVENANCE_AND_COMPATIBLE_GATE_REQUIRED"
        prerequisites.append(row)
    return {"inventory_fingerprint": inventory["inventory_fingerprint"],
        "status": "UNADMITTED_OWNER_PRECONDITION_OBSERVATIONS",
        "violations": failures[:64], "additional_violation_count": additional_count,
        "raw_routes_not_evaluable": unavailable, "source_preconditions": prerequisites,
        "not_evaluable": ["COMPLETE_PLAN_ADMISSION", "INDEPENDENT_SEMANTIC_REVIEW", "ACTUAL_OWNER_EVIDENCE", "ASSURANCE"]
            + (["OWNER_BACKGROUND_CROSS_ROUTE_PRECONDITIONS"] if unavailable else []),
        "instruction": "Select semantic components yourself. Every source needs its own complete component spans even when cited in u. Exact text equality does not merge source identities. The listed origins are necessary correspondence prerequisites, not evidence or permission. Do not add unrelated supports; do not change meaning or copy another source's scope. Revalidate the complete new proposal through existing gates."}


def _bind_repair_feedback(feedback, rows, attempt, revision, inventory, capabilities, candidate, *, ir=None,
                          include_owner_preconditions=False):
    """Return the exact untrusted proposal with feedback, never a repaired plan.

    A route ordinal/hash without its original proposal is not actionable repair
    context. Reuse the retained Owner observation; do not duplicate the inventory
    or manufacture a second source identity space.
    """
    from spg.providers.verification_receipts import _safe_value
    from spg.providers.fulfillment_candidate import _FulfillmentWireReceiptIdentityError
    raw, binding = _wire_response_basis(rows, attempt, revision, inventory, capabilities)
    payload = json.loads(feedback)
    payload.update(untrusted_previous_wire=raw, repair_feedback_binding={**binding,
        "candidate_fingerprint": None if candidate is None else fulfillment_candidate_fingerprint(candidate)})
    if include_owner_preconditions:
        start = next(row for row in rows if row["stage"] == "MODEL_REQUEST_PENDING" and row["attempt"] == attempt)
        payload["owner_repair_context"] = _owner_repair_context(raw, revision, ir, inventory, capabilities,
            validation_feedback=start.get("feedback"), owner_preconditions=start.get("owner_source_preconditions"))
    if _safe_value(payload) != payload:
        raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
    return json.dumps(payload, separators=(",", ":"))


def _validate_wire_feedback_lineage(rows, revision, ir, inventory, capabilities):
    """Recompute new diagnostics; legacy sealed receipts remain historical.

    No wire repair or request is performed. Both terminal replay and a next
    candidate consume the same bound feedback, never another attempt's output.
    """
    from spg.providers.fulfillment_candidate import (
        _decode_fulfillment_candidate_wire, _FulfillmentWireValidationError, _FulfillmentWireReceiptIdentityError,
        _FULFILLMENT_WIRE_METADATA_KEYS)
    for row in rows:
        preconditions = row.get("owner_source_preconditions")
        if preconditions is not None and (not isinstance(preconditions, dict)
                or preconditions.get("syntax_observation_contract") not in (
                    None, "complete-value-observations-v1", "complete-value-owner-observations-v1")
                or preconditions.get("operand_observation_contract") not in (None, "existing-owner-operands-v1")
                or preconditions.get("typed_prerequisite_contract") not in (None, "existing-owner-typed-prerequisites-v1", "existing-owner-typed-prerequisites-v2", "existing-owner-typed-prerequisites-v3")):
            raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
        if row.get("owner_source_preconditions") is not None and (
                row.get("stage") not in {"MODEL_REQUEST_PENDING", "MODEL_RESPONSE_OBSERVED"}
                or preconditions != _owner_source_preconditions(revision, ir, inventory, capabilities,
                    include_syntax_observations=preconditions.get("syntax_observation_contract") is not None,
                    syntax_observation_contract=preconditions.get("syntax_observation_contract"),
                    include_operand_observations=preconditions.get("operand_observation_contract") is not None,
                    include_typed_observations=preconditions.get("typed_prerequisite_contract") is not None,
                    typed_prerequisite_contract=preconditions.get("typed_prerequisite_contract"))):
            raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
        if (row.get("stage") == "MODEL_RESPONSE_OBSERVED" and row.get("candidate_retained") is True
                and any(key in row for key in _FULFILLMENT_WIRE_METADATA_KEYS)):
            # Successful terminal replay must check the original request too,
            # including removal of preconditions from BOTH durable records.
            _wire_response_basis(rows, row["attempt"], revision, inventory, capabilities)
    expected = {"work_id": str(revision.work_id), "work_reality_revision_id": str(revision.id),
        "inventory_fingerprint": inventory["inventory_fingerprint"],
        "source_revision": inventory["source_revision"], "exact_target_paths": inventory["exact_target_paths"],
        "owner": "WORK_FULFILLMENT_PROJECTION", "schema": "work-fulfillment-formation-receipt-v1"}
    if (any(row.get(key) != value for row in rows for key, value in expected.items())
            or any(type(row.get("attempt")) is not int or row["attempt"] not in (1, 2) for row in rows)):
        raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
    receipt_ids = [row.get("receipt_id") for row in rows]
    if any(not isinstance(value, str) or not value for value in receipt_ids) or len(set(receipt_ids)) != len(receipt_ids):
        raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
    for row in rows:
        if row.get("repair_feedback_bound") is True:
            try:
                bound_feedback = json.loads(row.get("validation_feedback") or "null")
            except ValueError as error:
                raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT") from error
            if (not isinstance(bound_feedback, dict) or "repair_feedback_binding" not in bound_feedback
                    or "untrusted_previous_wire" not in bound_feedback):
                raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
            if (row.get("owner_repair_context_bound") is True) != ("owner_repair_context" in bound_feedback):
                raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
            start = next((r for r in rows if r.get("stage") == "MODEL_REQUEST_PENDING"
                and r.get("attempt") == row.get("attempt")), {})
            if start.get("owner_repair_context_contract") is not None and row.get("owner_repair_context_bound") is not True:
                raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
        diagnostics = row.get("predecode_diagnostics")
        if diagnostics is None:
            if row.get("validation_feedback") is not None and not isinstance(row["validation_feedback"], str):
                raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
            try:
                feedback = json.loads(row.get("validation_feedback") or "null")
            except ValueError:
                feedback = None
            if isinstance(feedback, dict) and "wire_diagnostic_binding" in feedback:
                raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
            if isinstance(feedback, dict) and "repair_feedback_binding" in feedback:
                attempt = row.get("attempt")
                if (row.get("stage") != "CANDIDATE_VALIDATED" or row.get("validation_passed") is not False
                        or sum(r.get("stage") == "CANDIDATE_VALIDATED" and r.get("attempt") == attempt for r in rows) != 1):
                    raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
                raw, _ = _wire_response_basis(rows, attempt, revision, inventory, capabilities)
                start = next(r for r in rows if r.get("stage") == "MODEL_REQUEST_PENDING" and r.get("attempt") == attempt)
                response = next(r for r in rows if r.get("stage") == "MODEL_RESPONSE_OBSERVED" and r.get("attempt") == attempt)
                try:
                    original = _decode_fulfillment_candidate_wire(raw, inventory, capabilities,
                        validation_feedback=start.get("feedback"), wire_metadata=response,
                        owner_preconditions=start.get("owner_source_preconditions"))
                    deterministic_error = None
                    try:
                        original, _ = locate_projection_components(original, inventory)
                        validate_projection_candidate(original, revision, ir, inventory, allow_review_pending=True)
                    except ValueError as error:
                        deterministic_error = json.loads(projection_validation_feedback(
                            original, revision, ir, inventory, error))["primary_error"]
                    if deterministic_error is not None and row.get("failed_predicate") != deterministic_error:
                        raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
                    if row.get("candidate") != original.model_dump(mode="json"):
                        raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
                    expected_feedback = projection_validation_feedback(original, revision, ir, inventory, row.get("failed_predicate"))
                    expected_feedback = _bind_repair_feedback(expected_feedback, rows, attempt,
                        revision, inventory, capabilities, original, ir=ir,
                        include_owner_preconditions=row.get("owner_repair_context_bound") is True)
                    if row.get("validation_feedback") != expected_feedback:
                        raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
                except ValueError as error:
                    raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT") from error
            elif isinstance(feedback, dict) and "untrusted_previous_wire" in feedback:
                raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
            continue
        attempt = row.get("attempt")
        if (row.get("stage") != "CANDIDATE_VALIDATED" or row.get("candidate") is not None
                or row.get("validation_passed") is not False
                or sum(r.get("stage") == "CANDIDATE_VALIDATED" and r.get("attempt") == attempt for r in rows) != 1):
            raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
        raw, _ = _wire_response_basis(rows, attempt, revision, inventory, capabilities)
        start = next(r for r in rows if r.get("stage") == "MODEL_REQUEST_PENDING" and r.get("attempt") == attempt)
        response = next(r for r in rows if r.get("stage") == "MODEL_RESPONSE_OBSERVED" and r.get("attempt") == attempt)
        try:
            _decode_fulfillment_candidate_wire(raw, inventory, capabilities,
                validation_feedback=start.get("feedback"), wire_metadata=response,
                owner_preconditions=start.get("owner_source_preconditions"))
        except _FulfillmentWireValidationError as error:
            bound = _bind_wire_diagnostics(error, rows, attempt, revision, inventory, capabilities)
            feedback = projection_validation_feedback(None, revision, ir, inventory, error, wire_diagnostics=bound)
            try:
                retained_feedback = json.loads(row.get("validation_feedback") or "null")
            except ValueError as drift:
                raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT") from drift
            if isinstance(retained_feedback, dict) and "repair_feedback_binding" in retained_feedback:
                feedback = _bind_repair_feedback(feedback, rows, attempt, revision, inventory, capabilities, None,
                    ir=ir, include_owner_preconditions=row.get("owner_repair_context_bound") is True)
            if (diagnostics != bound or row.get("validation_feedback") != feedback
                    or row.get("failed_predicate") != str(error)
                    or any(row.get(key) != bound["binding"][key] for key in
                        ("work_id", "work_reality_revision_id", "source_revision", "inventory_fingerprint", "exact_target_paths"))):
                raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
        except ValueError as error:
            raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT") from error
        else:
            raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
        for next_start in rows:
            if next_start.get("stage") == "MODEL_REQUEST_PENDING" and next_start.get("attempt") == attempt + 1:
                if (next_start.get("feedback") != feedback
                        or next_start.get("feedback_receipt_id") != row.get("receipt_id")):
                    raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")
    for start in rows:
        if start.get("stage") != "MODEL_REQUEST_PENDING" or not isinstance(start.get("feedback"), str):
            continue
        try:
            feedback = json.loads(start["feedback"])
        except ValueError:
            continue  # Existing canonical/legacy feedback may be an error code.
        if isinstance(feedback, dict) and ("wire_diagnostic_binding" in feedback or "repair_feedback_binding" in feedback):
            parents = [r for r in rows if r.get("stage") == "CANDIDATE_VALIDATED"
                and r.get("attempt") == start.get("attempt", 0) - 1
                and r.get("validation_feedback") == start["feedback"]]
            if len(parents) != 1 or start.get("feedback_receipt_id") != parents[0].get("receipt_id"):
                raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT")


def plan_with_formation_receipts(database, work_id, plan, *, inventory_fingerprint=None):
    from spg.infrastructure.persistence.product_store import ProductStore
    from spg.infrastructure.persistence.runtime_store import RuntimeStore
    with database.unit_of_work() as uow:
        work = ProductStore(uow.session).work(work_id)
        records = (() if inventory_fingerprint is None else tuple(record.scope for record in
            RuntimeStore(uow.session).governance_for_subject(inventory_fingerprint)
            if record.decision_type == "WORK_FULFILLMENT_OBSERVATION"
            and record.authority_identity == "work-governance:derived-candidate-observation"
            and record.subject_type == "WORK_FULFILLMENT_BASIS"
            and record.scope.get("work_id") == str(work_id)))
    cached = () if work is None or work.production_plan is None else work.production_plan.fulfillment_formation_receipts
    by_id = {row["receipt_id"]: row for row in (*cached, *records)}
    return plan.model_copy(update={"fulfillment_formation_receipts": tuple(by_id.values())})


def fulfillment_capability_contracts():
    return [{"capability": key, "component": value[0], "owner": value[1].value,
        "phase": value[2].value, "evidence_method": value[3], "gate_ref": value[4]}
        for key, value in FULFILLMENT_CAPABILITIES.items()]


class FulfillmentReviewOutcomeUnknown(RuntimeError):
    pass


def _review_fulfillment_candidate(provider, candidate, inventory, recorder, attempt, capabilities):
    if not any(route.component_basis is not None for route in candidate.routes):
        return None
    if not hasattr(provider, "review"):
        raise ValueError("OBLIGATION_SEMANTIC_REVIEW_UNAVAILABLE")
    rows = recorder.records()
    validated = next((row for row in reversed(rows) if row["attempt"] == attempt
        and row["stage"] == "SEMANTIC_REVIEW_VALIDATED"), None)
    if validated is not None:
        if validated.get("capabilities_fingerprint") != canonical_fingerprint(capabilities):
            raise ValueError("OBLIGATION_SEMANTIC_REVIEW_CAPABILITIES_DRIFT")
        if not validated.get("validation_passed"):
            raise ValueError(validated.get("failed_predicate", "OBLIGATION_SEMANTIC_COMPONENT_MISMATCH"))
        result = FulfillmentSemanticReviewCandidate.model_validate(validated["semantic_review"])
        validate_projection_components(candidate, inventory, semantic_review=result)
        return result.model_dump(mode="json")
    observed = next((row for row in reversed(rows) if row["attempt"] == attempt
        and row["stage"] == "SEMANTIC_REVIEW_OBSERVED"), None)
    if observed is None:
        if any(row["attempt"] == attempt and row["stage"] == "SEMANTIC_REVIEW_PENDING" for row in rows):
            raise FulfillmentReviewOutcomeUnknown("OBLIGATION_SEMANTIC_REVIEW_PENDING_OUTCOME_UNKNOWN")
        recorder.append("SEMANTIC_REVIEW_PENDING", attempt,
            capabilities_fingerprint=canonical_fingerprint(capabilities),
            candidate_fingerprint=fulfillment_candidate_fingerprint(candidate),
            components_fingerprint=fulfillment_components_fingerprint(candidate))
        import inspect
        parameters = inspect.signature(provider.review).parameters
        callback = "receipt_callback" in parameters
        def observed_callback(**values):
            recorder.append("SEMANTIC_REVIEW_OBSERVED", attempt, capabilities_fingerprint=canonical_fingerprint(capabilities), **values)
        kwargs = {"receipt_callback": observed_callback} if callback else {}
        if "capabilities" in parameters:
            kwargs["capabilities"] = capabilities
        response = provider.review(inventory, candidate, **kwargs)
        if not callback:
            recorder.append("SEMANTIC_REVIEW_OBSERVED", attempt,
                capabilities_fingerprint=canonical_fingerprint(capabilities),
                semantic_review=response.model_dump(mode="json") if isinstance(response, FulfillmentSemanticReviewCandidate) else response,
                model=getattr(provider, "last_observation", None))
    else:
        if observed.get("capabilities_fingerprint") != canonical_fingerprint(capabilities):
            raise ValueError("OBLIGATION_SEMANTIC_REVIEW_CAPABILITIES_DRIFT")
        response = observed.get("semantic_review")
        if response is None and observed.get("review_output") is not None:
            response = json.loads(observed["review_output"])
        if response is None:
            raise ValueError("OBLIGATION_SEMANTIC_REVIEW_NOT_RETAINED")
    result = response if isinstance(response, FulfillmentSemanticReviewCandidate) else FulfillmentSemanticReviewCandidate.model_validate(response)
    try:
        validate_projection_components(candidate, inventory, semantic_review=result)
    except ValueError as error:
        recorder.append("SEMANTIC_REVIEW_VALIDATED", attempt, capabilities_fingerprint=canonical_fingerprint(capabilities), semantic_review=result.model_dump(mode="json"),
            validation_passed=False, failed_predicate=str(error))
        raise
    recorder.append("SEMANTIC_REVIEW_VALIDATED", attempt, capabilities_fingerprint=canonical_fingerprint(capabilities), semantic_review=result.model_dump(mode="json"),
        validation_passed=True, failed_predicate=None)
    return result.model_dump(mode="json")


def form_fulfillment_projection(revision, ir, *, provider, database=None,
                                source_revision=None, exact_target_paths=()):
    arguments = dict(provider=provider, database=database,
        source_revision=source_revision, exact_target_paths=exact_target_paths,
        _started=monotonic())
    try:
        return _form_fulfillment_projection(revision, ir, **arguments)
    except FulfillmentReceiptCapacityStop:
        # One read of the just-persisted terminal receipt. This never opens a
        # new candidate/review slot or rewrites the immutable inventory.
        return _form_fulfillment_projection(revision, ir, **arguments)


def _form_fulfillment_projection(revision, ir, *, provider, database=None,
                                source_revision=None, exact_target_paths=(), _started=None):
    """Two cumulative candidates on one basis, with recoverable Owner receipts."""
    inventory = fulfillment_inventory(revision, ir, source_revision=source_revision,
                                      exact_target_paths=exact_target_paths)
    if not hasattr(provider, "_fulfillment_receipts"):
        provider._fulfillment_receipts = []
    recorder = FulfillmentFormationReceipts(revision, inventory, database=database,
                                           memory=provider._fulfillment_receipts)
    started = monotonic() if _started is None else _started
    capabilities = fulfillment_capability_contracts()
    def finish(candidate, reason, passed):
        rows = recorder.records()
        semantic_review = next((row.get("semantic_review") for row in reversed(rows)
            if row["stage"] == "CANDIDATE_VALIDATED" and row.get("validation_passed")), None)
        review_row = next((row for row in reversed(rows) if row["stage"] == "SEMANTIC_REVIEW_VALIDATED"
            and row.get("validation_passed") and row.get("semantic_review") == semantic_review), None)
        capability_fingerprint = canonical_fingerprint(capabilities) if semantic_review is None else (
            None if review_row is None else review_row.get("capabilities_fingerprint"))
        if semantic_review is not None and capability_fingerprint != canonical_fingerprint(capabilities):
            raise ValueError("OBLIGATION_SEMANTIC_REVIEW_CAPABILITIES_DRIFT")
        receipt = {"owner": "WORK_FULFILLMENT_PROJECTION", "inventory_fingerprint": inventory["inventory_fingerprint"],
            "source_revision": inventory["source_revision"], "work_reality_revision_id": str(revision.id),
            "exact_target_paths": inventory["exact_target_paths"], "bounded_feedback_limit": 1,
            "candidate_attempt_limit": 2, "semantic_review_calls_per_candidate_limit": 1, "maximum_model_calls": 4,
            "semantic_review": semantic_review, "capabilities_fingerprint": capability_fingerprint,
            "semantic_review_receipt_refs": [f"work-plan-receipt:{row['receipt_id']}" for row in rows if row["stage"].startswith("SEMANTIC_REVIEW_")],
            "provider_call_count": sum(row["stage"] in {"MODEL_REQUEST_PENDING", "SEMANTIC_REVIEW_PENDING"} for row in rows),
            "observed_model_call_count": sum(row["stage"] in {"MODEL_RESPONSE_OBSERVED", "SEMANTIC_REVIEW_OBSERVED"}
                and isinstance(row.get("model"), dict) and not row["model"].get("fixture", False) for row in rows),
            "attempt_count": sum(row["stage"] == "MODEL_REQUEST_PENDING" for row in rows),
            "receipt_refs": [f"work-plan-receipt:{row['receipt_id']}" for row in rows],
            "candidate_attempts": list(rows), "terminal_reason": reason,
            "unresolved_source_refs": [] if passed else [source["source_ref"] for source in inventory["sources"]],
            "elapsed_seconds": monotonic() - started,
            "meaning": "derived binding only; no evidence PASS, authority or effect"}
        if not passed or candidate is None:
            return unresolved_projection(revision, ir, inventory, reason=reason, receipt=receipt)
        bindings = validate_projection_candidate(candidate, revision, ir, inventory, semantic_review=semantic_review)
        return (bindings[0].model_copy(update={"formation_receipt": receipt}), *bindings[1:])
    def stop_identity(reason):
        current = recorder.records()
        if not any(row.get("terminal") for row in current):
            attempt = max((row["attempt"] for row in current
                if type(row.get("attempt")) is int and row["attempt"] in (1, 2)), default=1)
            recorder.append("FORMATION_STOPPED", attempt, terminal=True, validation_passed=False,
                terminal_reason=reason, failure_stage="WIRE_FEEDBACK_IDENTITY")
        return finish(None, reason, False)
    rows = recorder.records()
    from spg.providers.fulfillment_candidate import _FulfillmentWireReceiptIdentityError, _FulfillmentWireValidationError
    try:
        _validate_wire_feedback_lineage(rows, revision, ir, inventory, capabilities)
    except _FulfillmentWireReceiptIdentityError as error:
        return stop_identity(str(error))
    terminal = next((row for row in reversed(rows) if row.get("terminal")), None)
    if terminal is not None:
        candidate = None if terminal.get("candidate") is None else FulfillmentProjectionCandidate.model_validate(terminal["candidate"])
        return finish(candidate, terminal.get("terminal_reason", "OBLIGATION_FORMATION_TERMINAL"), terminal.get("validation_passed", False))
    pending = [row for row in rows if row["stage"] == "MODEL_REQUEST_PENDING"]
    validated = {row["attempt"] for row in rows if row["stage"] == "CANDIDATE_VALIDATED"}
    incomplete = next((row for row in pending if row["attempt"] not in validated), None)
    if incomplete is not None and not any(row["attempt"] == incomplete["attempt"] and row["stage"] == "MODEL_RESPONSE_OBSERVED" for row in rows):
        recorder.append("FORMATION_STOPPED", incomplete["attempt"], terminal=True,
            validation_passed=False, terminal_reason="OBLIGATION_FORMATION_PENDING_OUTCOME_UNKNOWN")
        return finish(None, "OBLIGATION_FORMATION_PENDING_OUTCOME_UNKNOWN", False)
    feedback = next((row.get("validation_feedback", row.get("failed_predicate")) for row in reversed(rows) if row["stage"] == "CANDIDATE_VALIDATED"), None)
    next_attempt = incomplete["attempt"] if incomplete is not None else len(pending) + 1
    for attempt in range(next_attempt, 3):
        candidate = None
        semantic_review = None
        failure_stage = "MODEL_REQUEST"
        try:
            _validate_wire_feedback_lineage(recorder.records(), revision, ir, inventory, capabilities)
            observed_row = next((row for row in reversed(recorder.records()) if row["attempt"] == attempt and row["stage"] == "MODEL_RESPONSE_OBSERVED"), None)
            if observed_row is not None:
                observed = observed_row.get("candidate")
                raw_output = observed_row.get("candidate_output")
                from spg.providers.fulfillment_candidate import _FULFILLMENT_WIRE_METADATA_KEYS
                starts = [row for row in recorder.records() if row["attempt"] == attempt
                    and row["stage"] == "MODEL_REQUEST_PENDING"]
                compact_receipt = (any(key in observed_row for key in _FULFILLMENT_WIRE_METADATA_KEYS)
                    or any(key in row for row in starts for key in _FULFILLMENT_WIRE_METADATA_KEYS))
                if compact_receipt:
                    from spg.providers.fulfillment_candidate import (
                        _decode_fulfillment_candidate_wire,
                        _FulfillmentWireReceiptIdentityError)
                    if len(starts) != 1 or any(starts[0].get(key) != observed_row.get(key)
                            for key in _FULFILLMENT_WIRE_METADATA_KEYS):
                        raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_RECEIPT_IDENTITY_DRIFT")
                    _wire_response_basis(recorder.records(), attempt, revision, inventory, capabilities)
                    observed = _decode_fulfillment_candidate_wire(
                        observed if observed is not None else raw_output, inventory, capabilities,
                        validation_feedback=starts[0].get("feedback"), wire_metadata=observed_row,
                        owner_preconditions=starts[0].get("owner_source_preconditions"))
                elif observed is None and raw_output is not None:
                    # Unmarked historical receipts keep their canonical contract.
                    observed = json.loads(raw_output)
                if observed is None:
                    raise ValueError("OBLIGATION_FORMATION_CANDIDATE_NOT_RETAINED")
            else:
                metadata_builder = getattr(provider, "form_wire_metadata", None)
                import inspect
                form_parameters = inspect.signature(provider.form).parameters
                supports_preconditions = ("owner_preconditions" in form_parameters
                    or any(p.kind is inspect.Parameter.VAR_KEYWORD for p in form_parameters.values()))
                precondition_arguments = ({"owner_preconditions": _owner_source_preconditions(revision, ir, inventory, capabilities)}
                    if supports_preconditions and callable(metadata_builder)
                    and "owner_preconditions" in inspect.signature(metadata_builder).parameters else {})
                wire_metadata = metadata_builder(inventory, capabilities, validation_feedback=feedback,
                    **precondition_arguments) if callable(metadata_builder) else {}
                owner_contract = {"owner_repair_context_contract": "existing-owner-preconditions-v1"} if wire_metadata else {}
                if precondition_arguments:
                    owner_contract["owner_source_preconditions"] = precondition_arguments["owner_preconditions"]
                parents = [row for row in recorder.records() if row["stage"] == "CANDIDATE_VALIDATED"
                    and row["attempt"] == attempt - 1 and row.get("validation_feedback") is not None]
                recorder.append("MODEL_REQUEST_PENDING", attempt, feedback=feedback, **wire_metadata, **owner_contract,
                    **({"feedback_receipt_id": parents[0]["receipt_id"]} if len(parents) == 1 else {}))
                accepts_callback = "receipt_callback" in inspect.signature(provider.form).parameters
                def observed_callback(**values):
                    recorder.append("MODEL_RESPONSE_OBSERVED", attempt, **values, **owner_contract)
                arguments = {"validation_feedback": feedback, **precondition_arguments}
                if accepts_callback:
                    arguments["receipt_callback"] = observed_callback
                observed = provider.form(inventory, capabilities, **arguments)
                if wire_metadata:
                    _wire_response_basis(recorder.records(), attempt, revision, inventory, capabilities)
                if not accepts_callback:
                    recorder.append("MODEL_RESPONSE_OBSERVED", attempt,
                        candidate=observed.model_dump(mode="json") if isinstance(observed, FulfillmentProjectionCandidate) else observed,
                        model=getattr(provider, "last_observation", None))
            candidate = observed if isinstance(observed, FulfillmentProjectionCandidate) else FulfillmentProjectionCandidate.model_validate(observed)
            raw_candidate = candidate
            candidate, adjustments = locate_projection_components(candidate, inventory)
            if adjustments:
                prior_location = next((row for row in reversed(recorder.records()) if row["attempt"] == attempt
                    and row["stage"] == "CANDIDATE_LOCATED"), None)
                located = {"raw_candidate_fingerprint": fulfillment_candidate_fingerprint(raw_candidate),
                    "candidate_fingerprint": fulfillment_candidate_fingerprint(candidate),
                    "locator_adjustments": list(adjustments)}
                if prior_location is None:
                    recorder.append("CANDIDATE_LOCATED", attempt, **located)
                elif any(prior_location.get(key) != value for key, value in located.items()):
                    raise ValueError("OBLIGATION_COMPONENT_LOCATOR_RECEIPT_DRIFT")
            validate_projection_candidate(candidate, revision, ir, inventory, allow_review_pending=True)
            failure_stage = "SEMANTIC_REVIEW"
            semantic_review = _review_fulfillment_candidate(provider, candidate, inventory, recorder, attempt, capabilities)
            bindings = validate_projection_candidate(candidate, revision, ir, inventory, semantic_review=semantic_review)
            passed = not any(binding.state == "UNRESOLVED" for binding in bindings)
            reason = "VALIDATED_PROJECTION" if passed else "UNRESOLVED_BINDING"
        except FulfillmentReceiptCapacityStop:
            raise
        except _FulfillmentWireReceiptIdentityError as error:
            return stop_identity(str(error))
        except ValueError as error:
            wire_diagnostics = None
            if isinstance(error, _FulfillmentWireValidationError):
                try:
                    wire_diagnostics = _bind_wire_diagnostics(error, recorder.records(), attempt,
                        revision, inventory, capabilities)
                except _FulfillmentWireReceiptIdentityError as drift:
                    return stop_identity(str(drift))
            feedback = projection_validation_feedback(candidate, revision, ir, inventory, error,
                wire_diagnostics=wire_diagnostics)
            responses = [row for row in recorder.records() if row.get("stage") == "MODEL_RESPONSE_OBSERVED"
                and row.get("attempt") == attempt]
            if (len(responses) == 1 and responses[0].get("provider_wire_version") is not None
                    and (candidate is not None or wire_diagnostics is not None)):
                try:
                    feedback = _bind_repair_feedback(feedback, recorder.records(), attempt,
                        revision, inventory, capabilities, candidate, ir=ir, include_owner_preconditions=True)
                except _FulfillmentWireReceiptIdentityError as drift:
                    return stop_identity(str(drift))
            passed, reason = False, json.loads(feedback)["primary_error"]
            recorder.append("CANDIDATE_VALIDATED", attempt, candidate=None if candidate is None else candidate.model_dump(mode="json"),
                semantic_review=semantic_review, failed_predicate=reason, validation_feedback=feedback, validation_passed=False, terminal=attempt == 2,
                terminal_reason=reason if attempt == 2 else None,
                **({"repair_feedback_bound": True} if "repair_feedback_binding" in json.loads(feedback) else {}),
                **({"owner_repair_context_bound": True} if "owner_repair_context" in json.loads(feedback) else {}),
                **({"predecode_diagnostics": wire_diagnostics} if wire_diagnostics is not None else {}))
            if attempt < 2:
                continue
        except Exception as error:
            # Transport/unknown failures cannot justify a probability retry.
            from spg.providers.fulfillment_candidate import (
                provider_failure_observation, _FulfillmentWireReceiptIdentityError)
            reason = ("OBLIGATION_FORMATION_WIRE_RECEIPT_IDENTITY_DRIFT"
                if isinstance(error, _FulfillmentWireReceiptIdentityError)
                else f"OBLIGATION_FORMATION_TRANSPORT_{type(error).__name__}")
            recorder.append("CANDIDATE_VALIDATED", attempt, candidate=None, failed_predicate=reason,
                terminal=True, validation_passed=False, terminal_reason=reason,
                failure_stage=failure_stage, model=provider_failure_observation(error))
            return finish(None, reason, False)
        else:
            recorder.append("CANDIDATE_VALIDATED", attempt, candidate=candidate.model_dump(mode="json"),
                semantic_review=semantic_review, failed_predicate=None if passed else reason, validation_passed=passed, terminal=True, terminal_reason=reason)
        if attempt == 2 and database is not None:
            from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
            from spg.domain.refinement_contract import RefinementSignalKind
            model_rows = [row.get("model", {}) for row in recorder.records() if row["stage"] in {"MODEL_RESPONSE_OBSERVED", "SEMANTIC_REVIEW_OBSERVED"}]
            usage = [row.get("usage", {}) for row in model_rows if isinstance(row, dict)]
            with database.unit_of_work() as uow:
                NativeExecutionStore(uow.session).record_bounded_refinement(work_id=revision.work_id,
                    operation_id=uuid5(NAMESPACE_URL, f"fulfillment-projection:{inventory['inventory_fingerprint']}"),
                    component="work/fulfillment-projection", signal_kind=RefinementSignalKind.CONTRACT_MISMATCH,
                    signature_basis=feedback or "UNRESOLVED_BINDING", evidence_references=(f"work-reality-revision:{revision.id}", f"semantic-ir:{ir.id}"),
                    converged=passed, attempt_count=2, elapsed_seconds=int(monotonic() - started),
                    model_token_usage={"total_tokens": None if not usage or any(row.get("unknown") or row.get("total_tokens") is None for row in usage) else sum(int(row["total_tokens"]) for row in usage),
                        "unknown": not usage or any(row.get("unknown") or row.get("total_tokens") is None for row in usage)},
                    diagnostic_evidence={"inventory_fingerprint": inventory["inventory_fingerprint"],
                        "receipt_refs": [f"work-plan-receipt:{row['receipt_id']}" for row in recorder.records()]})
                uow.commit()
        return finish(candidate, reason, passed)
    return finish(None, "OBLIGATION_FORMATION_BUDGET_EXHAUSTED", False)
