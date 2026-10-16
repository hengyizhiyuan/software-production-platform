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


def production_brief_bindings(revision, ir, inventory):
    """Return a complete pending assignment, or None for interpretive formation.

    Selection uses admitted types and exact field derivations. It does not
    classify words, split meaning, or ask a critic to approve a copied request.
    """
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
    if any(not goal.bounded_change or goal.unresolved_arguments for goal in ir.current_production):
        return None
    items = {item.item_id: item for item in ir.items}
    clauses = {clause.clause_id: clause for clause in ir.clauses}
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
            if fact.relation is SemanticRelation.REFERENCE:
                if fact.reference_role is SemanticReferenceRole.PROJECT_REPOSITORY:
                    methods = ("PRODUCT_SOURCE_IDENTITY",)
                elif fact.reference_role is SemanticReferenceRole.EXTERNAL_REFERENCE:
                    methods = ("RETAIN_CONTEXT",)
            elif fact.relation is not SemanticRelation.ACCEPTANCE_ASSERTION:
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
            elif is_context_only_clause(revision, ir, item.item_id, clause.clause_id):
                methods = ("RETAIN_CONTEXT",)
            elif ((production_source or item.kind in {SemanticKind.FACT, SemanticKind.CONSTRAINT} and item.action is None)
                    and clause.temporal_scope == "CURRENT" and clause.modality == "REQUEST"
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
                methods = (("ARTIFACT_CONTENT",) if not direct else tuple(dict.fromkeys(
                    method for s in origins for method in assignments[s["source_ref"]])))
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
            if source["kind"] != "WORK_CONSTRAINT":
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
    receipt = {"source_role_contract": CONTRACT, "inventory_fingerprint": inventory["inventory_fingerprint"],
        "exact_target_paths": inventory["exact_target_paths"],
        "formation_round": inventory.get("formation_round", 1),
        "formation_episode": inventory.get("formation_episode"),
        "provider_call_count": 0, "evidence_status": "PENDING_ACTUAL_CANDIDATE_VERIFICATION"}
    return (bindings[0].model_copy(update={"formation_receipt": receipt}), *bindings[1:])


def validate_production_brief(bindings, revision, ir, inventory):
    """Recompute the whole handoff, rather than trusting a marker or verdict."""
    expected = production_brief_bindings(revision, ir, inventory)
    if expected is None or tuple(bindings) != tuple(expected):
        raise ValueError("OBLIGATION_PRODUCTION_BRIEF_DRIFT")
