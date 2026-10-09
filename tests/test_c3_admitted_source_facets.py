"""Exact admitted IRK source facets, not phrase or Subject qualification cases."""
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.application.governed_obligations import (
    admitted_clause_source_failure, admitted_fulfillment_bindings,
    deterministic_fulfillment_projection, fulfillment_inventory,
    validate_projection_candidate, unresolved_projection)
from spg.application.intent_realization import validate_semantic_candidate
from spg.domain.engineering_semantics import SemanticRelation
from spg.domain.governed_obligation import (
    FulfillmentProjectionCandidate, FulfillmentRouteCandidate, FulfillmentSourceKind,
    fulfillment_source_ref)
from spg.domain.intent_realization import (
    ObservedEffect, SemanticClause, SemanticItem, SemanticKind, TurnSemanticCandidate)
from spg.domain.semantic_provenance import SemanticArgument, SemanticOrigin, SemanticProvenance
from tests.test_fulfillment_projection import basis, Oracle
from tests.test_governed_obligation_fulfillment import fact


def shared_source_basis(*, observed=True):
    revision, ir = basis(with_fact=False)
    human_id = revision.source_record_ids[0]
    interaction_id = uuid4()
    first = "Create index.html."
    second = "Keep the external release forbidden."
    content = first + " " + second
    record = SimpleNamespace(id=human_id, interaction_id=interaction_id, actor="HUMAN",
        content=content, content_fingerprint=sha256(content.encode()).hexdigest())
    original = ir.items[0]
    human = original.provenance[0].model_copy(update={"source_text": first})
    item = original.model_copy(update={"provenance": (human,)})
    first_clause = ir.clauses[0].model_copy(update={"clause_id": "first", "source_text": first,
        "requested_effects": (), "polarity": "AFFIRMATIVE"})
    second_clause = ir.clauses[0].model_copy(update={"clause_id": "second", "source_text": second})
    items = [item]
    if observed:
        owner = SemanticProvenance(origin=SemanticOrigin.REPOSITORY_OBSERVED,
            source_record_id=None, source_text=None, evidence_reference="repository-observation:exact")
        observed_item = SemanticItem(item_id="observed-source", kind=SemanticKind.FACT,
            statement="An exact repository version was observed", confidence=1,
            provenance=(owner,), observed_facts={"revision": SemanticArgument(value="a" * 40, provenance=owner)})
        items.append(observed_item)
        first_clause = first_clause.model_copy(update={"semantic_item_ids": (item.item_id, observed_item.item_id)})
    ir.items, ir.clauses = tuple(items), (first_clause, second_clause)
    ir.source_record_id, ir.interaction_id = human_id, interaction_id
    revision.source_interaction_id = interaction_id
    revision.constraints, revision.context_facts = (), ()
    return revision, ir, record


def test_authoritative_irk_admits_shared_item_distinct_clause_spans_and_owner_fact():
    revision, ir, record = shared_source_basis()
    raw = TurnSemanticCandidate(items=ir.items, clauses=ir.clauses)
    owner = ObservedEffect(owner="repository", evidence_references=("repository-observation:exact",),
        facts={"revision": "a" * 40})
    admitted = validate_semantic_candidate(raw, SimpleNamespace(records=(record,), observed_reality=(owner,)))
    assert admitted == ir.items
    assert ir.items[0].provenance[0].source_text not in ir.clauses[1].source_text
    assert ir.clauses[1].source_text not in ir.items[0].provenance[0].source_text
    assert admitted_clause_source_failure(revision, ir, records=(record,)) is None


def test_distinct_human_clause_span_can_keep_its_exact_continuous_gate():
    revision, ir, record = shared_source_basis(observed=False)
    inventory = fulfillment_inventory(revision, ir)
    routes = tuple(FulfillmentRouteCandidate(source_ref=s["source_ref"],
        capability="DENY_DEPLOY" if s["clause_id"] == "second" else "UNRESOLVED",
        rationale="Exact original typed effect") for s in inventory["sources"])
    bindings = validate_projection_candidate(FulfillmentProjectionCandidate(
        inventory_fingerprint=inventory["inventory_fingerprint"], routes=routes), revision, ir, inventory)
    gate = next(b for b in bindings if b.constraint_clause_id == "second")
    assert gate.state == "BOUND_PENDING_EVIDENCE"
    assert gate.source_record_ids == (record.id,)
    assert gate.source_quote == ir.clauses[1].source_text
    assert gate.provenance_fingerprint


def test_observed_facet_is_retained_without_human_ids_and_current_clause_is_not_lost():
    revision, ir, record = shared_source_basis()
    before = [item.model_dump(mode="json") for item in ir.items]
    inventory = fulfillment_inventory(revision, ir)
    clauses = [s for s in inventory["sources"] if s["kind"] == "IR_CONSTRAINT"]
    assert {s["clause_id"] for s in clauses} == {"first", "second"}
    assert all(s["item_id"] != "observed-source" for s in clauses)
    observed = next(s for s in inventory["sources"] if s["kind"] == "IR_ITEM")
    assert observed["item_id"] == "observed-source"
    assert observed["payload"]["item"]["provenance"][0]["source_record_id"] is None
    bindings = deterministic_fulfillment_projection(revision, ir, inventory)
    retained = next(b for b in bindings if b.source_kind is FulfillmentSourceKind.IR_ITEM)
    assert retained.state == "RETAINED_CONTEXT" and retained.source_record_ids == ()
    assert next(b for b in bindings if b.constraint_clause_id == "first").state == "UNRESOLVED"
    assert set(map(fulfillment_source_ref, bindings)) == {s["source_ref"] for s in inventory["sources"]}
    assert [item.model_dump(mode="json") for item in ir.items] == before


def test_only_observed_clause_keeps_unresolved_human_requirement_and_cannot_gain_authority():
    revision, ir, _ = shared_source_basis()
    observed = ir.items[-1]
    ir.items = (observed,)
    ir.clauses = (ir.clauses[0].model_copy(update={"semantic_item_ids": (observed.item_id,),
        "requested_effects": ("PROHIBIT_DEPLOY",), "polarity": "NEGATED"}),)
    inventory = fulfillment_inventory(revision, ir)
    assert {s["kind"] for s in inventory["sources"]} == {"IR_CLAUSE", "IR_ITEM"}
    result = deterministic_fulfillment_projection(revision, ir, inventory)
    assert all(b.state == "UNRESOLVED" for b in result)
    assert any(b.constraint_clause_id == "first" for b in result)
    routes = tuple(FulfillmentRouteCandidate(source_ref=s["source_ref"],
        capability="DENY_DEPLOY" if s["kind"] == "IR_CLAUSE" else "RETAIN_CONTEXT",
        rationale="Observed evidence cannot grant Human effects") for s in inventory["sources"])
    with pytest.raises(ValueError, match="CLAUSE_PROVENANCE_INVALID"):
        validate_projection_candidate(FulfillmentProjectionCandidate(
            inventory_fingerprint=inventory["inventory_fingerprint"], routes=routes), revision, ir, inventory)


@pytest.mark.parametrize("change", ["missing", "actor", "span", "fingerprint", "interaction", "revision", "item_span"])
def test_production_source_recheck_rejects_missing_or_wrong_exact_human_owner(change):
    revision, ir, record = shared_source_basis()
    records = (record,)
    if change == "missing": records = ()
    elif change == "actor": record.actor = "MODEL"
    elif change == "span": ir.clauses = (ir.clauses[0].model_copy(update={"source_text": "Invented original input"}), *ir.clauses[1:])
    elif change == "fingerprint": record.content_fingerprint = "0" * 64
    elif change == "interaction": record.interaction_id = uuid4()
    elif change == "revision": revision.source_record_ids = (uuid4(),)
    else: ir.items = (ir.items[0].model_copy(update={"provenance": (ir.items[0].provenance[0].model_copy(update={"source_text": "Invented item input"}),)}), *ir.items[1:])
    assert admitted_clause_source_failure(revision, ir, records=records).startswith("OBLIGATION_ADMITTED_")


def test_unknown_reference_reaches_bounded_candidate_provider_without_context_promotion():
    revision, ir, _ = shared_source_basis(observed=False)
    unclassified = fact("artifact.reference", SemanticRelation.REFERENCE, "index.html", "Create index.html.").model_copy(update={"reference_role": None})
    revision.engineering_semantic_facts = (unclassified,)
    revision.source_record_ids = (*revision.source_record_ids, *unclassified.provenance.source_record_ids)
    inventory = fulfillment_inventory(revision, ir)
    typed = deterministic_fulfillment_projection(revision, ir, inventory)
    assert next(b for b in typed if b.fact_id == unclassified.id).state == "UNRESOLVED"
    oracle = Oracle([RuntimeError("Scoped transport failure, no retry")])
    assessment = SimpleNamespace(id=revision.source_assessment_id, semantic_ir=ir)
    result = admitted_fulfillment_bindings(revision, assessment, provider=oracle)
    assert len(oracle.calls) == 1
    assert all(b.state == "UNRESOLVED" for b in result)
    assert result[0].formation_receipt["terminal_reason"] == "OBLIGATION_FORMATION_TRANSPORT_RuntimeError"


def test_invalid_authority_can_be_represented_unresolved_but_never_bound():
    revision, ir, _ = shared_source_basis(observed=False)
    ir.clauses = (ir.clauses[1].model_copy(update={"source_record_id": uuid4()}),)
    inventory = fulfillment_inventory(revision, ir)
    result = unresolved_projection(revision, ir, inventory, reason="Exact source unavailable")
    assert all(b.state == "UNRESOLVED" for b in result)
    assert result[0].source_record_ids == (ir.clauses[0].source_record_id,)
    route = FulfillmentRouteCandidate(source_ref=inventory["sources"][0]["source_ref"],
        capability="DENY_DEPLOY", rationale="Cannot promote a phantom Human record")
    with pytest.raises(ValueError, match="CLAUSE_PROVENANCE_INVALID"):
        validate_projection_candidate(FulfillmentProjectionCandidate(
            inventory_fingerprint=inventory["inventory_fingerprint"], routes=(route,)), revision, ir, inventory)


def reviewed_background_basis(background, request):
    from spg.domain.interaction_actions import ActionSpeechAct
    from spg.domain.governed_obligation import FulfillmentComponentBasis, fulfillment_source_semantic_text
    revision, ir, record = shared_source_basis(observed=False)
    provenance = ir.items[0].provenance[0].model_copy(update={"source_text": request})
    goal = ir.current_production[0].model_copy(update={"target_paths": (
        SemanticArgument(value="index.html", provenance=provenance),)})
    item = ir.items[0].model_copy(update={"kind": SemanticKind.PRODUCTION_INTENT,
        "production": goal, "provenance": (provenance,)})
    background_clause = ir.clauses[0].model_copy(update={"clause_id": "background",
        "source_text": background, "modality": "ASSERTION", "polarity": "AFFIRMATIVE",
        "temporal_scope": "CURRENT", "speech_act": ActionSpeechAct.DISCUSSION,
        "requested_effects": (), "semantic_item_ids": (item.item_id,)})
    request_clause = ir.clauses[1].model_copy(update={"clause_id": "actual-request",
        "source_text": request, "modality": "REQUEST", "polarity": "AFFIRMATIVE",
        "temporal_scope": "CURRENT", "speech_act": ActionSpeechAct.EXPLICIT_REQUEST,
        "requested_effects": (), "semantic_item_ids": (item.item_id,)})
    ir.items, ir.clauses, ir.current_production = (item,), (background_clause, request_clause), (goal,)
    record.content = background + " " + request
    record.content_fingerprint = sha256(record.content.encode()).hexdigest()
    inventory = fulfillment_inventory(revision, ir)
    routes = tuple(FulfillmentRouteCandidate(source_ref=source["source_ref"],
        capability="RETAIN_CONTEXT" if source.get("clause_id") == "background" else "ARTIFACT_CONTENT",
        target_paths=() if source.get("clause_id") == "background" else ("index.html",),
        rationale="Controlled semantic oracle; no authority or evidence PASS",
        component_basis=FulfillmentComponentBasis(source_span_start=0,
            source_span_end=len(fulfillment_source_semantic_text(source)),
            source_component_quote=fulfillment_source_semantic_text(source))) for source in inventory["sources"])
    plan = FulfillmentProjectionCandidate(inventory_fingerprint=inventory["inventory_fingerprint"], routes=routes)
    return revision, ir, record, inventory, plan


@pytest.mark.parametrize("background,request_text", [
    ("This is a private study of artifact production.", "Create the required document at index.html."),
    ("This exercise concerns a static software artifact.", "Produce the original requested content at index.html."),
    ("这是隔离环境里的软件生产说明。", "请在 index.html 生成已确认的页面。")])
def test_reviewed_background_same_item_keeps_all_current_request_evidence(background, request_text):
    from tests.test_c3_fulfillment_components import ReviewedOracle
    from spg.application.governed_obligations import form_fulfillment_projection, is_context_only_clause, validate_fulfillment_projection
    revision, ir, record, inventory, plan = reviewed_background_basis(background, request_text)
    assert admitted_clause_source_failure(revision, ir, records=(record,)) is None
    typed = deterministic_fulfillment_projection(revision, ir, inventory)
    assert all(binding.state == "UNRESOLVED" for binding in typed)
    with pytest.raises(ValueError, match="SEMANTIC_REVIEW_REQUIRED"):
        validate_projection_candidate(plan, revision, ir, inventory)
    oracle = ReviewedOracle([plan])
    bindings = form_fulfillment_projection(revision, ir, provider=oracle)
    assert len(oracle.calls) == 1 and oracle.review_calls == 1
    background_binding = next(binding for binding in bindings if binding.constraint_clause_id == "background")
    current_binding = next(binding for binding in bindings if binding.constraint_clause_id == "actual-request")
    assert background_binding.state == "RETAINED_CONTEXT" and background_binding.source_quote == background
    assert current_binding.phase.value == "CURRENT_VERIFICATION" and current_binding.evidence_method == "EXACT_CANDIDATE_CONTENT"
    assert set(map(fulfillment_source_ref, bindings)) == {source["source_ref"] for source in inventory["sources"]}
    assert not is_context_only_clause(revision, ir, ir.items[0].item_id, "background")
    assert is_context_only_clause(revision, ir, ir.items[0].item_id, "background", bindings=bindings)
    from spg.providers.managed_context_fulfillment import _retained_binding_proof
    assert _retained_binding_proof(background_binding, revision, ir, bindings)
    without_review = (bindings[0].model_copy(update={"formation_receipt": None}), *bindings[1:])
    assert not _retained_binding_proof(background_binding, revision, ir, without_review)
    validate_fulfillment_projection(bindings, revision, ir, exact_target_paths=("index.html",))


@pytest.mark.parametrize("change", ["request", "negated", "effect", "human", "fact", "sibling_unknown", "sibling_context", "sibling_past", "partial_quote", "linked_fact"])
def test_reviewed_background_cannot_hide_current_request_fact_or_authority(change):
    from spg.domain.interaction_actions import ActionSpeechAct
    from spg.domain.governed_obligation import FulfillmentComponentBasis
    revision, ir, _, inventory, plan = reviewed_background_basis(
        "The surrounding discussion concerns an isolated exercise.", "Create the required output at index.html.")
    if change == "request": ir.clauses = (ir.clauses[0].model_copy(update={"modality": "REQUEST", "speech_act": ActionSpeechAct.EXPLICIT_REQUEST}), ir.clauses[1])
    elif change == "negated": ir.clauses = (ir.clauses[0].model_copy(update={"polarity": "NEGATED"}), ir.clauses[1])
    elif change == "effect": ir.clauses = (ir.clauses[0].model_copy(update={"requested_effects": ("PROHIBIT_DEPLOY",)}), ir.clauses[1])
    elif change == "human": ir.items = (ir.items[0].model_copy(update={"requires_human": True}),)
    elif change == "fact": revision.engineering_semantic_facts = (fact("original.background.literal", SemanticRelation.EQUALITY,
        "Exact original", ir.clauses[0].source_text),)
    elif change == "sibling_past": ir.clauses = (ir.clauses[0], ir.clauses[1].model_copy(update={"temporal_scope": "PAST"}))
    changed = fulfillment_inventory(revision, ir)
    old = {route.source_ref: route for route in plan.routes}
    routes = []
    for source in changed["sources"]:
        if source["kind"] == "FACT":
            text = source["provenance"]["source_text"]
            route = FulfillmentRouteCandidate(source_ref=source["source_ref"], capability="ARTIFACT_CONTENT", target_paths=("index.html",),
                rationale="Every original Fact remains current", component_basis=FulfillmentComponentBasis(source_span_start=0, source_span_end=len(text), source_component_quote=text))
        else: route = old[source["source_ref"]]
        if change in {"sibling_unknown", "sibling_context"} and source.get("clause_id") == "actual-request":
            route = route.model_copy(update={"capability": "UNRESOLVED" if change == "sibling_unknown" else "RETAIN_CONTEXT", "target_paths": ()})
        if change == "partial_quote" and source.get("clause_id") == "background":
            route = route.model_copy(update={"component_basis": route.component_basis.model_copy(update={"source_span_end": 5, "source_component_quote": route.component_basis.source_component_quote[:5]})})
        if change == "linked_fact" and source.get("clause_id") == "background":
            route = route.model_copy(update={"component_basis": route.component_basis.model_copy(update={"linked_fact_refs": ("semantic-fact:unowned",)})})
        routes.append(route)
    plan = plan.model_copy(update={"inventory_fingerprint": changed["inventory_fingerprint"], "routes": tuple(routes)})
    with pytest.raises(ValueError, match="OBLIGATION_"):
        validate_projection_candidate(plan, revision, ir, changed, allow_review_pending=True)


def test_failed_background_semantic_review_terminates_and_consumer_cannot_invent_it():
    from tests.test_c3_fulfillment_components import ReviewedOracle
    from spg.application.governed_obligations import form_fulfillment_projection, is_context_only_clause
    revision, ir, _, inventory, plan = reviewed_background_basis(
        "This is background context only.", "Create the required output at index.html.")
    oracle = ReviewedOracle([plan, plan], reviews=(False, False))
    bindings = form_fulfillment_projection(revision, ir, provider=oracle)
    assert len(oracle.calls) == 2 and oracle.review_calls == 2
    assert all(binding.state == "UNRESOLVED" for binding in bindings)
    assert bindings[0].formation_receipt["provider_call_count"] == 4
    assert not is_context_only_clause(revision, ir, ir.items[0].item_id, "background", bindings=bindings)


def test_background_cannot_hide_current_fact_governed_span_when_main_span_is_elsewhere():
    from spg.domain.governed_obligation import FulfillmentComponentBasis
    revision, ir, record, _, original = reviewed_background_basis(
        "The stated acceptance condition remains binding.", "Create the required output at index.html.")
    governed = SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,
        source_record_id=record.id, source_text=ir.clauses[0].source_text)
    current = fact("required.original.condition", SemanticRelation.EQUALITY, "Exact original",
        ir.clauses[1].source_text)
    current = current.model_copy(update={"provenance": current.provenance.model_copy(update={
        "source_record_ids": (record.id,), "governed_provenance": (governed,)})})
    revision.engineering_semantic_facts = (current,)
    before = current.model_dump(mode="json")
    inventory = fulfillment_inventory(revision, ir)
    primary = next(source for source in inventory["sources"] if source["kind"] == "FACT")
    quote = primary["provenance"]["source_text"]
    route = FulfillmentRouteCandidate(source_ref=primary["source_ref"], capability="ARTIFACT_CONTENT",
        target_paths=("index.html",), rationale="Original Fact must retain its current verification",
        component_basis=FulfillmentComponentBasis(source_span_start=0, source_span_end=len(quote), source_component_quote=quote))
    plan = original.model_copy(update={"inventory_fingerprint": inventory["inventory_fingerprint"],
        "routes": (route, *original.routes)})
    assert current.provenance.source_text not in ir.clauses[0].source_text
    assert governed.source_text == ir.clauses[0].source_text
    with pytest.raises(ValueError, match="CURRENT_CLAUSE_CANNOT_BE_CONTEXT_ONLY"):
        validate_projection_candidate(plan, revision, ir, inventory, allow_review_pending=True)
    assert current.model_dump(mode="json") == before
