"""Pass an admitted brief to its existing evidence owners without rewriting it.

This is the non-generative path of Work fulfillment admission. Full source
contributions remain pending until the actual candidate is independently checked.
It supplies neither a semantic verdict nor an effect/write permission.
"""
from __future__ import annotations

from types import SimpleNamespace

from spg.domain.governed_obligation import (
    FulfillmentBinding, FulfillmentComponentBasis, FulfillmentRouteCandidate,
    FulfillmentSourceKind, canonical_fingerprint, exact_file_scope_paths,
    fulfillment_source_semantic_text,
)
from spg.domain.engineering_semantics import SemanticRelation, SemanticReferenceRole
from spg.domain.intent_realization import SemanticKind
from spg.domain.semantic_provenance import SemanticOrigin


CONTRACT = "source-preserving-production-brief-v1"
STAGED_CONTRACT = "source-preserving-production-brief-v2"
CONTINUITY_CONTRACT = "source-preserving-production-brief-v3"
REVISED_WORK_CONTRACT = "source-preserving-production-brief-v4"
STAGED_CONTRACTS = {STAGED_CONTRACT, CONTINUITY_CONTRACT, REVISED_WORK_CONTRACT}
CONTRACTS = {CONTRACT, *STAGED_CONTRACTS}
REVIEW_METHOD = "EXACT_CANDIDATE_REVIEW_READINESS"


def production_brief_bindings(revision, ir, inventory, *, contract=None):
    if contract is not None:
        return _production_brief_bindings(revision, ir, inventory, contract=contract)
    return (_production_brief_bindings(revision, ir, inventory, contract=CONTRACT)
        or _production_brief_bindings(revision, ir, inventory, contract=STAGED_CONTRACT)
        or _production_brief_bindings(revision, ir, inventory, contract=CONTINUITY_CONTRACT)
        or _production_brief_bindings(revision, ir, inventory, contract=REVISED_WORK_CONTRACT))


def current_assertion_source(fact, revision):
    """An admitted Human fact survives a later turn that only supplies a delta."""
    return (fact.is_current and fact.relation is SemanticRelation.ACCEPTANCE_ASSERTION
        and fact.authority.value == "HUMAN_EXPLICIT" and fact.epistemic_status.value == "CONFIRMED"
        and fact.qualifiers.get("negated") is not True and bool(fact.provenance.source_text)
        and bool(fact.provenance.source_record_ids)
        and set(fact.provenance.source_record_ids) <= set(revision.source_record_ids))


def advisory_question_ids(ir):
    """Compiler questions explicitly marked safe/nonblocking are context only.

    Every linked Human clause still has its own full production contribution.
    The original IR and question remain intact; this is no permission or answer.
    """
    from spg.application.governed_obligations import _human_clause_item
    items = {i.item_id: i for i in ir.items}
    result = []
    for item in ir.items:
        if (item.kind is not SemanticKind.QUESTION or item.requires_human or item.action or item.production
                or not item.provenance or any(p.origin is not SemanticOrigin.MODEL_CANDIDATE for p in item.provenance)):
            continue
        questions = [q for q in ir.questions if not q.requires_human and not q.blocks_current_step
            and q.safe_reversible_assumption and q.provenance in item.provenance]
        clauses = [c for c in ir.clauses if item.item_id in c.semantic_item_ids]
        if questions and clauses and all(any(other != item.item_id and other in items
                and _human_clause_item(items[other], c) for other in c.semantic_item_ids) for c in clauses):
            result.append(item.item_id)
    return tuple(result)


def observed_repository_annotation(fact, ir):
    """An inferred label may retain context, never assert repository identity.

    Its exact value must already occur in a repository-observed current goal.
    Actual Source/Baseline and original Human contributions remain checked.
    """
    return (fact.relation is SemanticRelation.REFERENCE and fact.reference_role is None
        and fact.authority.value == "SYSTEM_INFERRED" and fact.epistemic_status.value == "WORKING_ASSUMPTION"
        and any(g.repository_reference is not None and g.repository_reference.value == fact.value
            and g.repository_reference.provenance.origin is SemanticOrigin.REPOSITORY_OBSERVED
            for g in ir.current_production))


def staged_inventory(ir, inventory):
    ids = advisory_question_ids(ir)
    if not ids:
        return inventory
    basis = {k:v for k,v in inventory.items() if k != "inventory_fingerprint"}
    basis["sources"] = [s for s in inventory["sources"] if s.get("item_id") not in ids]
    basis["advisory_context"] = [i.model_dump(mode="json") for i in ir.items if i.item_id in ids]
    return {**basis, "inventory_fingerprint": canonical_fingerprint(basis)}


def _production_brief_bindings(revision, ir, inventory, *, contract):
    """Return a complete pending assignment, or None for interpretive formation.

    Selection uses admitted types and exact field derivations. It does not
    classify words, split meaning, or ask a critic to approve a copied request.
    """
    if contract in STAGED_CONTRACTS:
        inventory = staged_inventory(ir, inventory)
    from spg.application.governed_obligations import (
        FULFILLMENT_CAPABILITIES, _TYPED_EFFECT_ROUTES, _human_clause_item,
        _projection_binding, _work_constraint_direct_source,
        _work_constraint_exclusion_sources, is_context_only_clause,
    )

    if not inventory["exact_target_paths"] or not ir.current_production:
        return None
    if not any(item.production is not None and item.production in ir.current_production
               for item in ir.items):
        return None
    from spg.providers.protected_context_verifier import StaticProtectedContextVerifier
    if not StaticProtectedContextVerifier.supports(SimpleNamespace(allowed_areas=(), exact_targets=tuple(
            SimpleNamespace(path=p) for p in inventory["exact_target_paths"]))):
        return None
    # The inspected exact targets above are the implementation boundary.
    # WIC's earlier sizing assessment is not another authority prerequisite
    # for copying an admitted brief to actual artifact verification.
    if any(goal.systemic_design or goal.unresolved_arguments for goal in ir.current_production):
        return None
    staged = contract in STAGED_CONTRACTS
    continuity = contract in {CONTINUITY_CONTRACT, REVISED_WORK_CONTRACT}
    revised_work = contract == REVISED_WORK_CONTRACT
    if revised_work and (getattr(revision, "revision_number", 1) < 2
            or not getattr(revision, "previous_revision_id", None)):
        return None
    items = {item.item_id: item for item in ir.items}
    clauses = {clause.clause_id: clause for clause in ir.clauses}
    future = tuple(c for c in ir.clauses if staged and c.temporal_scope == "FUTURE"
        and c.modality == "REQUEST" and c.polarity == "AFFIRMATIVE"
        and c.requested_effects and set(c.requested_effects) <= {"REQUEST_PREVIEW"})
    if future and (not all(g.preview_required for g in ir.current_production)
            or any(g.delivery_authorized for g in ir.current_production)):
        return None
    def future_source(fact):
        quote = fact.provenance.source_text
        return bool(quote) and any(c.source_record_id in fact.provenance.source_record_ids
            and (quote in c.source_text or c.source_text in quote) for c in future)
    assignments = {}
    sources = inventory["sources"]
    routes = []
    for source in sources:
        methods, supports = (), ()
        kind = source["kind"]
        if kind == "FACT":
            fact = next(f for f in revision.engineering_semantic_facts if str(f.id) == source["fact_id"])
            if fact.epistemic_status.value == "UNRESOLVED":
                return None
            if staged and future_source(fact) and (fact.relation is SemanticRelation.ACCEPTANCE_ASSERTION
                    or fact.value is False):
                methods = ("REVIEW_READINESS",)
            elif fact.relation is SemanticRelation.REFERENCE:
                if fact.reference_role is SemanticReferenceRole.PROJECT_REPOSITORY:
                    methods = ("PRODUCT_SOURCE_IDENTITY",)
                elif fact.reference_role is SemanticReferenceRole.EXTERNAL_REFERENCE:
                    methods = ("RETAIN_CONTEXT",)
                elif staged and observed_repository_annotation(fact, ir):
                    methods = ("RETAIN_CONTEXT",)
                elif staged and fact.reference_role is None and isinstance(fact.value, str) and fact.value in inventory["exact_target_paths"]:
                    methods = ("ARTIFACT_CONTENT",)
            elif (continuity and current_assertion_source(fact, revision)
                    and all(g.preview_required for g in ir.current_production)
                    and not any(g.delivery_authorized for g in ir.current_production)):
                # Copy the entire source to both real owners. The current
                # content check cannot stand in for later Preview or Human
                # decisions; neither has happened at this admission boundary.
                methods = ("ARTIFACT_CONTENT", "REVIEW_READINESS")
            elif (staged and fact.relation is SemanticRelation.ACCEPTANCE_ASSERTION
                    and not any(g.acceptance_required or g.preview_required for g in ir.current_production) and any(
                    c.temporal_scope == "CURRENT" and c.source_record_id in fact.provenance.source_record_ids
                    and fact.provenance.source_text and fact.provenance.source_text in c.source_text
                    and any(i in items and _human_clause_item(items[i], c) for i in c.semantic_item_ids)
                    for c in ir.clauses)):
                methods = ("ARTIFACT_CONTENT",)
            elif fact.relation is not SemanticRelation.ACCEPTANCE_ASSERTION:
                if staged and fact.qualifiers.get("negated") is True:
                    return None
                paths = exact_file_scope_paths(fact, qualified=True)
                methods = (("GIT_DIFF_SCOPE",) if paths and set(paths) == set(inventory["exact_target_paths"])
                           else ("ARTIFACT_CONTENT",))
        elif kind in {"IR_CLAUSE", "IR_CONSTRAINT"}:
            item, clause = items[source["item_id"]], clauses[source["clause_id"]]
            if item.requires_human:
                return None
            production_source = item.production is not None and item.production in ir.current_production
            # Production annotations need no second interpretation to copy the
            # whole request. Typed prohibitions/restrictions still select their
            # gate, and an unknown prohibition cannot become a content promise.
            effects = tuple(e for e in clause.requested_effects
                if e in _TYPED_EFFECT_ROUTES or e.startswith(("PROHIBIT_", "RESTRICT_")))
            if effects:
                if not all(effect in _TYPED_EFFECT_ROUTES for effect in effects):
                    return None
                methods = tuple(dict.fromkeys(next(name for name, value in FULFILLMENT_CAPABILITIES.items()
                    if value == (route[0], route[1], route[3], route[4], route[2]))
                    for route in (_TYPED_EFFECT_ROUTES[e] for e in effects)))
            elif staged and clause in future and _human_clause_item(item, clause) and item.action is None:
                methods = ("REVIEW_READINESS",)
            elif is_context_only_clause(revision, ir, item.item_id, clause.clause_id):
                methods = ("RETAIN_CONTEXT",)
            elif ((production_source or item.kind in {SemanticKind.FACT, SemanticKind.CONSTRAINT} and item.action is None)
                    and clause.temporal_scope == "CURRENT" and (clause.modality == "REQUEST"
                        or staged and clause.modality == "ASSERTION")
                    and clause.polarity in {"AFFIRMATIVE", "NEGATED"} and _human_clause_item(item, clause)):
                methods = ("ARTIFACT_CONTENT",)
        elif kind == "IR_ITEM":
            item = items[source["item_id"]]
            if (item.kind is SemanticKind.FACT and item.action is None and item.production is None
                    and not item.requires_human and all(p.origin is SemanticOrigin.REPOSITORY_OBSERVED
                        for p in item.provenance)):
                methods = ("RETAIN_CONTEXT",)
        elif kind == "WORK_CONTEXT":
            methods = ("RETAIN_CONTEXT",)
        elif kind == "WORK_CONSTRAINT":
            text = source["payload"]["content"]
            direct = [s for s in sources if _work_constraint_direct_source(ir, text, s)]
            exclusions = [s for s, _ in _work_constraint_exclusion_sources(ir, text, sources)
                          if items[s["item_id"]].production in ir.current_production]
            origins = direct or exclusions
            if origins and all(s["source_ref"] in assignments for s in origins):
                supports = tuple(s["source_ref"] for s in origins)
                # An exclusion is already an admitted production field. Its
                # provenance needs no invented second negative Human clause.
                methods = (("ARTIFACT_CONTENT", "REVIEW_READINESS") if staged and future and not direct else ("ARTIFACT_CONTENT",) if not direct else tuple(dict.fromkeys(
                    method for s in origins for method in assignments[s["source_ref"]])))
            elif revised_work:
                # The exact admitted Work revision owns the complete retained
                # requirement, even when the current IR contains only a delta.
                # Copy it whole to actual content Verification, not to an effect
                # gate or a semantic PASS. Typed current prohibitions/facts above
                # keep their independent mandatory routes and refusal checks.
                methods = ("ARTIFACT_CONTENT",)
        if not methods:
            return None
        assignments[source["source_ref"]] = methods
        text = fulfillment_source_semantic_text(source)
        routes.extend(FulfillmentRouteCandidate(
            source_ref=source["source_ref"], capability=method,
            work_constraint_indices=(source["index"],) if kind == "WORK_CONSTRAINT" else (),
            target_paths=tuple(inventory["exact_target_paths"]) if method in {"ARTIFACT_CONTENT", "GIT_DIFF_SCOPE"} else (),
            supporting_source_refs=supports,
            component_basis=FulfillmentComponentBasis(source_span_start=0,
                source_span_end=len(text), source_component_quote=text),
            rationale="Unchanged admitted source; actual evidence remains pending.",
        ) for method in methods)

    bindings = []
    try:
        for route in routes:
            source = next(s for s in sources if s["source_ref"] == route.source_ref)
            if staged:
                # Reuse the source constructor only for immutable identity. All
                # eligibility above is rederived from original typed sources;
                # no reviewed meaning or successful evidence is manufactured.
                from spg.domain.governed_obligation import FulfillmentOwner, FulfillmentPhase
                identity = _projection_binding(revision, ir, inventory,
                    route.model_copy(update={"capability": "UNRESOLVED", "target_paths": ()}),
                    source_contract="v3")
                spec = (("review-readiness", FulfillmentOwner.CANDIDATE,
                    FulfillmentPhase.CANDIDATE_SEAL, REVIEW_METHOD, "candidate-owner:review-readiness")
                    if route.capability == "REVIEW_READINESS" else FULFILLMENT_CAPABILITIES[route.capability])
                component, owner, phase, method, gate = spec
                binding = identity.model_copy(update={"component": component, "owner": owner,
                    "phase": phase, "evidence_method": method, "gate_ref": gate,
                    "target_paths": route.target_paths, "state": "RETAINED_CONTEXT"
                        if route.capability == "RETAIN_CONTEXT" else "BOUND_PENDING_EVIDENCE"})
            elif source["kind"] != "WORK_CONSTRAINT":
                binding = _projection_binding(revision, ir, inventory, route,
                    allow_calibrated=True, source_contract="v3")
            else:
                # This exact Work-owned source was derived above from an
                # admitted statement/scope/exclusion; methods copy its origin
                # or assign the entire exclusion to actual content verification.
                component, owner, phase, method, gate = FULFILLMENT_CAPABILITIES[route.capability]
                records = tuple(revision.source_record_ids)
                binding = FulfillmentBinding(source_kind=FulfillmentSourceKind.WORK_CONSTRAINT,
                    semantic_ir_id=ir.id, constraint_item_id=str(source["index"]),
                    constraint_fingerprint=canonical_fingerprint(source["payload"]),
                    work_reality_revision_id=revision.id,
                    provenance_fingerprint=canonical_fingerprint({"work_reality_revision_id": str(revision.id),
                        "source_record_ids": [str(r) for r in records]}),
                    source_record_ids=records, source_quote=source["payload"]["content"],
                    source_revision=inventory["source_revision"],
                    component=component, owner=owner, phase=phase, evidence_method=method, gate_ref=gate,
                    target_paths=route.target_paths, projection_inventory_fingerprint=inventory["inventory_fingerprint"],
                    work_constraint_indices=route.work_constraint_indices, supporting_source_refs=route.supporting_source_refs,
                    component_basis=route.component_basis,
                    state="RETAINED_CONTEXT" if route.capability == "RETAIN_CONTEXT" else "BOUND_PENDING_EVIDENCE")
            bindings.append(binding)
    except ValueError:
        # A required authority/typed consumer still needs its existing Owner.
        # Never partially simplify a brief or drop an unsupported contribution.
        return None
    receipt = {"source_role_contract": contract, "inventory_fingerprint": inventory["inventory_fingerprint"],
        "exact_target_paths": inventory["exact_target_paths"],
        "formation_round": inventory.get("formation_round", 1),
        "formation_episode": inventory.get("formation_episode"),
        "provider_call_count": 0, "evidence_status": "PENDING_ACTUAL_CANDIDATE_VERIFICATION"}
    if staged and inventory.get("advisory_context"):
        receipt["advisory_context_item_ids"] = [i["item_id"] for i in inventory["advisory_context"]]
    return (bindings[0].model_copy(update={"formation_receipt": receipt}), *bindings[1:])


def validate_production_brief(bindings, revision, ir, inventory):
    """Recompute the whole handoff, rather than trusting a marker or verdict."""
    contract = (bindings[0].formation_receipt or {}).get("source_role_contract") if bindings else None
    expected = production_brief_bindings(revision, ir, inventory, contract=contract)
    if expected is None or tuple(bindings) != tuple(expected):
        raise ValueError("OBLIGATION_PRODUCTION_BRIEF_DRIFT")
