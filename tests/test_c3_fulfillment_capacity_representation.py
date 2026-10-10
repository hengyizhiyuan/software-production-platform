"""Controlled C3 capacity protection; no model runtime, database or live Work."""
from __future__ import annotations

from copy import deepcopy
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.application.governed_obligations import (
    form_fulfillment_projection,
    FulfillmentFormationReceipts,
    fulfillment_capability_contracts,
    fulfillment_inventory,
    locate_projection_components,
    validate_fulfillment_projection,
    validate_projection_candidate,
)
from spg.domain.engineering_semantics import SemanticReferenceRole, SemanticRelation
from spg.domain.governed_obligation import (
    FulfillmentComponentBasis,
    FulfillmentProjectionCandidate,
    FulfillmentRouteCandidate,
    FulfillmentSemanticReviewCandidate,
    FulfillmentSemanticSourceReview,
    fulfillment_candidate_fingerprint,
    fulfillment_components_fingerprint,
    fulfillment_source_ref,
    fulfillment_source_semantic_text,
)
from spg.domain.intent_realization import SemanticClause, SemanticItem, SemanticKind
from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
from spg.domain.semantic_provenance import SemanticArgument, SemanticOrigin, SemanticProvenance
from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
from tests.test_c3_fulfillment_components import ReviewedOracle
from tests.test_fulfillment_projection import basis, candidate
from tests.test_governed_obligation_fulfillment import fact


def controlled_capacity_case(scale="small"):
    """Original typed test sources, never synthetic production approvals."""
    count, path_count = {"small": (1, 1), "medium": (5, 2), "complex": (16, 3)}[scale]
    revision, ir = basis(observed=True)
    paths = ("index.html", "notes.html", "details.html")[:path_count]
    ir.clauses = (ir.clauses[0].model_copy(update={
        "requested_effects": ("PROHIBIT_DEPLOY", "PROHIBIT_PUBLISH"),
    }),)
    future_text = "后续集成必须等待 Human 明确授权；现在仅准备可审查的候选。"
    future_source = uuid4()
    provenance = SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,
        source_record_id=future_source, source_text=future_text)
    future_item = SemanticItem(item_id="independent-future-approval", kind=SemanticKind.CONSTRAINT,
        statement=future_text, provenance=(provenance,), confidence=1)
    future_clause = SemanticClause(clause_id="future-approval-clause", source_record_id=future_source,
        source_text=future_text, semantic_item_ids=(future_item.item_id,), polarity="AFFIRMATIVE",
        modality="REQUEST", temporal_scope="FUTURE", requested_effects=())
    ir.items = (*ir.items, future_item)
    ir.clauses = (*ir.clauses, future_clause)
    ir.current_production = (ir.current_production[0].model_copy(update={
        "acceptance_required": True,
        "target_paths": tuple(SemanticArgument(value=path, provenance=provenance) for path in paths),
    }),)
    content = tuple(fact(
        f"unlisted-content-{index}", SemanticRelation.EQUALITY,
        f"原值 {index}: Preserve the exact visible contribution 👩‍💻",
        f"第 {index} 项必须保留原值 {index}: Preserve the exact visible contribution 👩‍💻。",
        qualifiers={"original_ordinal": index, "case_sensitive": True},
    ).model_copy(update={"scope": paths[index % len(paths)]}) for index in range(count))
    scope = fact("original-edit-boundary", SemanticRelation.SCOPE, list(paths),
        "Only these exact files may change: " + ", ".join(paths)).model_copy(update={"scope": None})
    source_identity = fact("original-product-source", SemanticRelation.REFERENCE,
        "Controlled accepted Product source", "Use the exact accepted Product source.").model_copy(update={
            "reference_role": SemanticReferenceRole.PROJECT_REPOSITORY,
        })
    revision.engineering_semantic_facts = (*content, scope, source_identity)
    revision.constraints = (*revision.constraints, future_text)
    revision.context_facts = ("原始上下文仅保留；不产生效果许可。",)
    revision.source_record_ids = tuple(dict.fromkeys((
        *revision.source_record_ids, future_source,
        *(record for item in revision.engineering_semantic_facts for record in item.provenance.source_record_ids),
    )))
    inventory = fulfillment_inventory(revision, ir, exact_target_paths=paths)
    original_clause_ref = next(source["source_ref"] for source in inventory["sources"]
        if source["kind"] == "IR_CONSTRAINT" and source["clause_id"] == "original-clause")
    future_ref = next(source["source_ref"] for source in inventory["sources"]
        if source["kind"] == "IR_CONSTRAINT" and source["clause_id"] == future_clause.clause_id)
    routes = []
    facts = {str(item.id): item for item in revision.engineering_semantic_facts}
    for source in inventory["sources"]:
        text = fulfillment_source_semantic_text(source)
        kind = source["kind"]
        support = ()
        if kind == "FACT":
            original = facts[source["fact_id"]]
            capabilities = (("GIT_DIFF_SCOPE",) if original.relation is SemanticRelation.SCOPE else
                ("PRODUCT_SOURCE_IDENTITY",) if original.relation is SemanticRelation.REFERENCE else ("ARTIFACT_CONTENT",))
        elif kind in {"IR_ITEM", "WORK_CONTEXT"}:
            capabilities = ("RETAIN_CONTEXT",)
        elif kind == "WORK_CONSTRAINT":
            capabilities = ("DENY_DEPLOY", "DENY_PUBLISH") if source["index"] == 0 else ("HUMAN_INTEGRATION",)
            support = (original_clause_ref,) if source["index"] == 0 else (future_ref,)
        else:
            capabilities = ("DENY_DEPLOY", "DENY_PUBLISH") if source["clause_id"] == "original-clause" else ("HUMAN_INTEGRATION",)
        for capability in capabilities:
            targets = paths if capability == "GIT_DIFF_SCOPE" else (
                (facts[source["fact_id"]].scope,) if capability == "ARTIFACT_CONTENT" else ())
            routes.append(FulfillmentRouteCandidate(source_ref=source["source_ref"], capability=capability,
                work_constraint_indices=(source["index"],) if kind == "WORK_CONSTRAINT" else (),
                supporting_source_refs=support, target_paths=targets,
                rationale="Controlled independent test oracle; not live semantic qualification",
                component_basis=FulfillmentComponentBasis(source_span_start=0, source_span_end=len(text),
                    source_component_quote=text,
                    linked_fact_refs=(source["source_ref"],) if kind == "FACT" else ())))
    plan = FulfillmentProjectionCandidate(inventory_fingerprint=inventory["inventory_fingerprint"], routes=tuple(routes))
    return revision, ir, inventory, plan


def controlled_wire(inventory, plan, *, feedback=None, owner_preconditions=None):
    """Mechanical test encoder, not an alternative runtime formation path."""
    from spg.providers.fulfillment_candidate import _fulfillment_wire_context
    capabilities = fulfillment_capability_contracts()
    context = _fulfillment_wire_context(inventory, capabilities, validation_feedback=feedback, owner_preconditions=owner_preconditions)
    sources = {source["source_ref"]: index for index, source in enumerate(inventory["sources"])}
    capability_indices = {entry["capability"]: index for index, entry in enumerate(capabilities)}
    paths = {path: index for index, path in enumerate(inventory["exact_target_paths"])}
    wire = {"v": 1, "h": context["wire_request_fingerprint"], "d": context["wire_table_fingerprint"],
        "routes": [{"s": sources[route.source_ref], "c": capability_indices[route.capability],
            "a": route.component_basis.source_span_start, "z": route.component_basis.source_span_end,
            "q": None, "f": [sources[ref] for ref in route.component_basis.linked_fact_refs],
            "t": [paths[path] for path in route.target_paths],
            "u": [sources[ref] for ref in route.supporting_source_refs], "r": route.rationale}
            for route in plan.routes]}
    return wire, context


def controlled_review(inventory, plan, *, equivalent=True):
    return FulfillmentSemanticReviewCandidate(inventory_fingerprint=inventory["inventory_fingerprint"],
        candidate_fingerprint=fulfillment_candidate_fingerprint(plan),
        components_fingerprint=fulfillment_components_fingerprint(plan),
        source_results=tuple(FulfillmentSemanticSourceReview(source_ref=source["source_ref"],
            complete_and_equivalent=equivalent, reason="Controlled separate review, not Assurance PASS")
            for source in inventory["sources"]))


def decode_review_input(payload):
    """The controlled reviewer consumes the same exact representation as live."""
    inventory = payload['immutable_inventory']
    if 'existing_ir_item_table' in payload:
        from spg.providers.fulfillment_candidate import _restore_formation_inventory_view
        inventory = _restore_formation_inventory_view(inventory, payload['existing_ir_item_table'])
    if payload.get('candidate_representation') == 'fulfillment-compact-v1':
        from spg.providers.fulfillment_candidate import _decode_fulfillment_candidate_wire
        return _decode_fulfillment_candidate_wire(json.dumps(payload['untrusted_fulfillment_candidate']),
            inventory,payload['existing_capability_contracts'])
    return FulfillmentProjectionCandidate.model_validate(payload['untrusted_fulfillment_candidate'])


@pytest.mark.parametrize('scale', ('small','medium','complex'))
def test_independent_review_reuses_wire_without_losing_any_component(scale,record_property):
    from spg.providers.fulfillment_candidate import _review_candidate_representation
    revision,ir,inventory,plan=controlled_capacity_case(scale)
    before=deepcopy(plan.model_dump(mode='json'))
    caps=fulfillment_capability_contracts()
    compact=_review_candidate_representation(inventory,plan,caps)
    payload={'immutable_inventory':inventory,'existing_capability_contracts':caps,**compact}
    restored=decode_review_input(payload)
    assert restored==plan and plan.model_dump(mode='json')==before
    assert fulfillment_candidate_fingerprint(restored)==fulfillment_candidate_fingerprint(plan)
    assert fulfillment_components_fingerprint(restored)==fulfillment_components_fingerprint(plan)
    assert len(json.dumps(compact,ensure_ascii=False).encode())<len(plan.model_dump_json().encode())
    record_property('review_representation_scale',scale)
    record_property('review_canonical_bytes',len(plan.model_dump_json().encode()))
    record_property('review_compact_bytes',len(json.dumps(compact,ensure_ascii=False).encode()))


@pytest.mark.parametrize('change', ('quote','inventory','constraint-index','path','fact-link'))
def test_review_representation_does_not_repair_invalid_or_drifting_identity(change):
    from spg.providers.fulfillment_candidate import _review_candidate_representation
    _,_,inventory,plan=controlled_capacity_case()
    routes=list(plan.routes);route=routes[0]
    if change=='quote':route=route.model_copy(update={'component_basis':route.component_basis.model_copy(update={'source_component_quote':'invented quotation'})})
    elif change=='inventory':plan=plan.model_copy(update={'inventory_fingerprint':'0'*64})
    elif change=='constraint-index':
        index=next(i for i,r in enumerate(routes) if r.work_constraint_indices)
        routes[index]=routes[index].model_copy(update={'work_constraint_indices':(999,)})
    elif change=='path':route=route.model_copy(update={'target_paths':('unadmitted/path.html',)})
    else:route=route.model_copy(update={'component_basis':route.component_basis.model_copy(update={'linked_fact_refs':('semantic-fact:missing',)})})
    routes[0]=route;plan=plan.model_copy(update={'routes':tuple(routes)})
    with pytest.raises((ValueError,RuntimeError,KeyError)):
        _review_candidate_representation(inventory,plan,fulfillment_capability_contracts())


def controlled_model_provider(inventory, plan, *, equivalent=True, review_change=None, wire_change=None):
    """Actual Provider methods with a deterministic, network-free runtime stub."""
    calls = []
    def generate(**request):
        payload = json.loads(request["input_text"])
        calls.append(payload)
        if "untrusted_fulfillment_candidate" in payload:
            restored = decode_review_input(payload)
            review = controlled_review(inventory, restored, equivalent=equivalent).model_dump(mode="json")
            if (payload.get("existing_owner_source_preconditions") or {}).get(
                    "typed_prerequisite_contract") in {"existing-owner-typed-prerequisites-v9", "existing-owner-typed-prerequisites-v10", "existing-owner-typed-prerequisites-v11"}:
                from tests.test_c3_semantic_contract_calibration import review as component_review
                components = component_review(inventory, restored).component_results
                review["component_results"] = [row.model_copy(update={"complete_and_equivalent": equivalent}).model_dump(mode="json")
                    for row in components]
            if review_change:
                review_change(review)
            output = json.dumps(review, ensure_ascii=False)
        else:
            wire, _ = controlled_wire(inventory, plan, feedback=payload.get("same_basis_validation_feedback"), owner_preconditions=payload.get("owner_source_preconditions"))
            if wire_change:
                wire_change(wire)
            output = json.dumps(wire, ensure_ascii=False)
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model="controlled-no-network", effective_model="controlled-no-network",
            request_id=f"controlled-capacity-{len(calls)}", usage=ModelUsage(), timing=ModelTiming(), retry_count=0)
    runtime = SimpleNamespace(generate=generate, close=lambda: None)
    return ModelFulfillmentCandidateProvider(lambda: runtime), calls


@pytest.mark.parametrize("scale", ("small", "medium", "complex"))
def test_compact_representation_preserves_complete_inventory_and_existing_owners(scale, record_property):
    from spg.providers.fulfillment_candidate import _decode_fulfillment_candidate_wire
    revision, ir, inventory, plan = controlled_capacity_case(scale)
    original = tuple(item.model_dump(mode="json") for item in revision.engineering_semantic_facts)
    wire, context = controlled_wire(inventory, plan)
    decoded = _decode_fulfillment_candidate_wire(json.dumps(wire, ensure_ascii=False), inventory,
        fulfillment_capability_contracts(), wire_metadata=context)
    assert decoded == plan
    canonical_bytes = len(plan.model_dump_json().encode())
    wire_bytes = len(json.dumps(wire, ensure_ascii=False, separators=(",", ":")).encode())
    assert wire_bytes < canonical_bytes < 65536
    record_property("controlled_fixture_scale", scale)
    record_property("inventory_sources", len(inventory["sources"]))
    record_property("canonical_candidate_bytes", canonical_bytes)
    record_property("compact_candidate_bytes", wire_bytes)
    provider, calls = controlled_model_provider(inventory, plan)
    result = form_fulfillment_projection(revision, ir, provider=provider,
        exact_target_paths=inventory["exact_target_paths"])
    assert len(calls) == 2
    assert set(map(fulfillment_source_ref, result)) == {source["source_ref"] for source in inventory["sources"]}
    assert all(binding.state != "UNRESOLVED" for binding in result)
    assert {binding.component for binding in result if binding.phase.value == "CONTINUOUS_FROM_ADMISSION"} == {"deploy", "publish"}
    future = [binding for binding in result if binding.phase.value == "HUMAN_INTEGRATION"]
    assert future and all(binding.state == "BOUND_PENDING_EVIDENCE" and binding.gate_ref for binding in future)
    assert next(binding for binding in result if binding.evidence_method == "EXACT_GIT_DIFF_SCOPE").target_paths == tuple(inventory["exact_target_paths"])
    assert next(binding for binding in result if binding.evidence_method == "EXACT_PRODUCT_SOURCE_IDENTITY").owner.value == "PRODUCT_SOURCE"
    assert tuple(item.model_dump(mode="json") for item in revision.engineering_semantic_facts) == original
    validate_fulfillment_projection(result, revision, ir, exact_target_paths=inventory["exact_target_paths"])
    replay = form_fulfillment_projection(revision, ir, provider=provider,
        exact_target_paths=inventory["exact_target_paths"])
    assert len(calls) == 2
    assert [binding.model_dump(exclude={"formation_receipt"}) for binding in replay] == [binding.model_dump(exclude={"formation_receipt"}) for binding in result]


@pytest.mark.parametrize("change", (
    "version", "request", "table", "boolean-source", "negative-capability", "outside-path",
    "non-fact-link", "boolean-span", "missing-source", "duplicate-route", "partial-content",
    "lost-prohibition", "wrong-support", "context-effect", "scope-subset", "scope-expansion",
    "future-current-fact", "source-as-content",
    "qualified-scope",
))
def test_compact_metadata_does_not_bypass_wire_or_original_contract_rejection(change):
    from spg.providers.fulfillment_candidate import _decode_fulfillment_candidate_wire, _FulfillmentWireReceiptIdentityError
    revision, ir, inventory, plan = controlled_capacity_case("medium")
    if change == "qualified-scope":
        revision.engineering_semantic_facts = tuple(item.model_copy(update={"qualifiers": {"complete": True}})
            if item.relation is SemanticRelation.SCOPE else item for item in revision.engineering_semantic_facts)
        inventory = fulfillment_inventory(revision, ir, exact_target_paths=inventory["exact_target_paths"])
        plan = plan.model_copy(update={"inventory_fingerprint": inventory["inventory_fingerprint"]})
    wire, context = controlled_wire(inventory, plan)
    refs = inventory["sources"]
    caps = fulfillment_capability_contracts()
    cap = {entry["capability"]: index for index, entry in enumerate(caps)}
    fact_route = next(route for route in wire["routes"] if refs[route["s"]]["kind"] == "FACT" and route["c"] == cap["ARTIFACT_CONTENT"])
    context_index = next(index for index, source in enumerate(refs) if source["kind"] == "WORK_CONTEXT")
    if change == "version": wire["v"] = 2
    elif change == "request": wire["h"] = "0" * 64
    elif change == "table": wire["d"] = "0" * 64
    elif change == "boolean-source": wire["routes"][0]["s"] = True
    elif change == "negative-capability": wire["routes"][0]["c"] = -1
    elif change == "outside-path": fact_route["t"] = [len(inventory["exact_target_paths"])]
    elif change == "non-fact-link": fact_route["f"] = [context_index]
    elif change == "boolean-span": fact_route["a"] = False
    elif change == "missing-source": wire["routes"] = [route for route in wire["routes"] if route["s"] != context_index]
    elif change == "duplicate-route": wire["routes"].append(deepcopy(wire["routes"][0]))
    elif change == "partial-content": fact_route["z"] -= 1
    elif change == "lost-prohibition": wire["routes"] = [route for route in wire["routes"] if route["c"] != cap["DENY_PUBLISH"]]
    elif change == "wrong-support":
        future = next(route for route in wire["routes"] if refs[route["s"]]["kind"] == "WORK_CONSTRAINT" and route["c"] == cap["HUMAN_INTEGRATION"])
        future["u"] = [next(index for index, source in enumerate(refs) if source.get("clause_id") == "original-clause")]
    elif change == "context-effect": next(route for route in wire["routes"] if route["s"] == context_index)["c"] = cap["DENY_DEPLOY"]
    elif change == "scope-subset": next(route for route in wire["routes"] if route["c"] == cap["GIT_DIFF_SCOPE"])["t"] = [0]
    elif change == "scope-expansion":
        inventory = deepcopy(inventory)
        inventory["exact_target_paths"].append("outside-authorized-scope.html")
    elif change == "future-current-fact": fact_route["c"], fact_route["t"] = cap["HUMAN_INTEGRATION"], []
    elif change == "source-as-content":
        source_route = next(route for route in wire["routes"] if route["c"] == cap["PRODUCT_SOURCE_IDENTITY"])
        source_route["c"], source_route["t"] = cap["ARTIFACT_CONTENT"], [0]
    expected_error = _FulfillmentWireReceiptIdentityError if change == "scope-expansion" else ValueError
    with pytest.raises(expected_error):
        restored = _decode_fulfillment_candidate_wire(json.dumps(wire, ensure_ascii=False), inventory, caps, wire_metadata=context)
        validate_projection_candidate(restored, revision, ir, inventory,
            semantic_review=controlled_review(inventory, restored))


@pytest.mark.parametrize("field", (
    "provider_wire_version", "wire_request_fingerprint", "wire_table_fingerprint", "wire_schema_fingerprint",
))
def test_compact_observation_metadata_cannot_replay_another_request_or_schema(field):
    from spg.providers.fulfillment_candidate import _decode_fulfillment_candidate_wire, _FulfillmentWireReceiptIdentityError
    _, _, inventory, plan = controlled_capacity_case()
    wire, context = controlled_wire(inventory, plan)
    metadata = deepcopy(context)
    metadata[field] = "wrong-version" if field == "provider_wire_version" else "0" * 64
    with pytest.raises(_FulfillmentWireReceiptIdentityError, match="WIRE_RECEIPT_IDENTITY_DRIFT"):
        _decode_fulfillment_candidate_wire(json.dumps(wire), inventory,
            fulfillment_capability_contracts(), wire_metadata=metadata)


@pytest.mark.parametrize("change", ("work-revision", "source-revision", "original-value", "original-qualifiers"))
def test_compact_source_metadata_cannot_restore_another_owner_version(change):
    from spg.providers.fulfillment_candidate import _decode_fulfillment_candidate_wire, _FulfillmentWireReceiptIdentityError
    revision, ir, inventory, plan = controlled_capacity_case()
    wire, context = controlled_wire(inventory, plan)
    if change == "work-revision": revision.id = uuid4()
    elif change == "source-revision": revision.source_revision = "c" * 40
    else:
        original = revision.engineering_semantic_facts[0]
        changed = original.model_copy(update={"value": "Wrong original value"} if change == "original-value" else
            {"qualifiers": {"original_ordinal": 99, "case_sensitive": False}})
        revision.engineering_semantic_facts = (changed, *revision.engineering_semantic_facts[1:])
    current = fulfillment_inventory(revision, ir, exact_target_paths=inventory["exact_target_paths"])
    with pytest.raises(_FulfillmentWireReceiptIdentityError):
        _decode_fulfillment_candidate_wire(json.dumps(wire), current,
            fulfillment_capability_contracts(), wire_metadata=context)


@pytest.mark.parametrize("change", ("missing-metadata", "changed-feedback", "reordered-source-table"))
def test_compact_receipt_replay_drift_cannot_be_treated_as_a_new_model_candidate(change):
    from spg.providers.fulfillment_candidate import _decode_fulfillment_candidate_wire, _FulfillmentWireReceiptIdentityError
    _, _, inventory, plan = controlled_capacity_case()
    wire, context = controlled_wire(inventory, plan)
    metadata, feedback = deepcopy(context), None
    if change == "missing-metadata": metadata.pop("provider_wire_version")
    elif change == "changed-feedback": feedback = "A different exact failed predicate"
    else:
        inventory = deepcopy(inventory)
        inventory["sources"] = list(reversed(inventory["sources"]))
    with pytest.raises(_FulfillmentWireReceiptIdentityError):
        _decode_fulfillment_candidate_wire(json.dumps(wire), inventory,
            fulfillment_capability_contracts(), validation_feedback=feedback, wire_metadata=metadata)


def test_compact_nonoverlapping_current_and_future_components_keep_their_original_contributions():
    from spg.providers.fulfillment_candidate import _decode_fulfillment_candidate_wire
    revision, ir, _, base = controlled_capacity_case()
    current = "The current artifact retains exact value 🧪-77."
    future = "Later integration remains pending Human authorization."
    text = current + "\n" + future
    original = fact("unlisted-mixed-contribution", SemanticRelation.ACCEPTANCE_ASSERTION, "🧪-77", text)
    revision.engineering_semantic_facts = (*revision.engineering_semantic_facts, original)
    revision.source_record_ids = (*revision.source_record_ids, *original.provenance.source_record_ids)
    inventory = fulfillment_inventory(revision, ir, exact_target_paths=("index.html",))
    source = next(source for source in inventory["sources"] if source.get("fact_id") == str(original.id))
    ref = source["source_ref"]
    routes = (*base.routes, *(
        FulfillmentRouteCandidate(source_ref=ref, capability=capability,
            target_paths=("index.html",) if capability == "ARTIFACT_CONTENT" else (),
            rationale="Controlled source component, never an approval",
            component_basis=FulfillmentComponentBasis(source_span_start=start, source_span_end=end,
                source_component_quote=quote, linked_fact_refs=(ref,)))
        for capability, start, end, quote in (
            ("ARTIFACT_CONTENT", 0, len(current), current),
            ("HUMAN_INTEGRATION", len(current) + 1, len(text), future),
        )
    ))
    plan = base.model_copy(update={"inventory_fingerprint": inventory["inventory_fingerprint"], "routes": routes})
    wire, context = controlled_wire(inventory, plan)
    restored = _decode_fulfillment_candidate_wire(json.dumps(wire), inventory,
        fulfillment_capability_contracts(), wire_metadata=context)
    assert restored == plan
    provider, calls = controlled_model_provider(inventory, plan)
    bindings = form_fulfillment_projection(revision, ir, provider=provider,
        source_revision=inventory["source_revision"], exact_target_paths=inventory["exact_target_paths"])
    mixed = [binding for binding in bindings if binding.fact_id == original.id]
    assert len(calls) == 2 and len(mixed) == 2
    assert {binding.phase.value for binding in mixed} == {"CURRENT_VERIFICATION", "HUMAN_INTEGRATION"}
    assert {binding.component_basis.source_component_quote for binding in mixed} == {current, future}
    assert all(binding.source_quote == text for binding in mixed)
    assert next(binding for binding in mixed if binding.phase.value == "HUMAN_INTEGRATION").state == "BOUND_PENDING_EVIDENCE"


def test_compact_explicit_unique_quote_uses_existing_offset_repair_without_semantic_rewrite():
    from spg.providers.fulfillment_candidate import _decode_fulfillment_candidate_wire
    revision, ir, inventory, plan = controlled_capacity_case()
    wire, context = controlled_wire(inventory, plan)
    quote = plan.routes[0].component_basis.source_component_quote
    wire["routes"][0].update(a=1, z=len(quote) + 1, q=quote)
    restored = _decode_fulfillment_candidate_wire(json.dumps(wire), inventory,
        fulfillment_capability_contracts(), wire_metadata=context)
    located, adjustments = locate_projection_components(restored, inventory)
    assert adjustments and located == plan
    validate_projection_candidate(located, revision, ir, inventory,
        semantic_review=controlled_review(inventory, located))


def test_compact_explicit_ambiguous_quote_stops_in_the_existing_locator():
    from spg.providers.fulfillment_candidate import _decode_fulfillment_candidate_wire
    revision, ir, _, _ = controlled_capacity_case()
    original = revision.engineering_semantic_facts[0]
    revision.engineering_semantic_facts = (original.model_copy(update={
        "provenance": original.provenance.model_copy(update={"source_text": "Repeat. Repeat."}),
    }), *revision.engineering_semantic_facts[1:])
    inventory = fulfillment_inventory(revision, ir, exact_target_paths=("index.html",))
    canonical = candidate(revision, ir, inventory)
    by_ref = {source["source_ref"]: source for source in inventory["sources"]}
    canonical = canonical.model_copy(update={"routes": tuple(route.model_copy(update={
        "component_basis": FulfillmentComponentBasis(source_span_start=0,
            source_span_end=len(fulfillment_source_semantic_text(by_ref[route.source_ref])),
            source_component_quote=fulfillment_source_semantic_text(by_ref[route.source_ref]))
    }) for route in canonical.routes)})
    wire, context = controlled_wire(inventory, canonical)
    wire["routes"][0].update(a=1, z=8, q="Repeat.")
    restored = _decode_fulfillment_candidate_wire(json.dumps(wire), inventory,
        fulfillment_capability_contracts(), wire_metadata=context)
    with pytest.raises(ValueError, match="SOURCE_LOCATION_AMBIGUOUS"):
        locate_projection_components(restored, inventory)


def test_compact_wire_size_does_not_hide_expanded_payload_capacity_failure():
    from spg.providers.fulfillment_candidate import _decode_fulfillment_candidate_wire
    revision, ir = basis()
    revision.context_facts = tuple(f"Controlled context {index}: " + chr(65 + index) * 60000 for index in range(3))
    inventory = fulfillment_inventory(revision, ir)
    canonical = candidate(revision, ir, inventory)
    sources = {source["source_ref"]: source for source in inventory["sources"]}
    canonical = canonical.model_copy(update={"routes": tuple(route.model_copy(update={
        "component_basis": FulfillmentComponentBasis(source_span_start=0,
            source_span_end=len(fulfillment_source_semantic_text(sources[route.source_ref])),
            source_component_quote=fulfillment_source_semantic_text(sources[route.source_ref]))
    }) for route in canonical.routes)})
    wire, context = controlled_wire(inventory, canonical)
    assert len(json.dumps(wire).encode()) < 65536 < len(canonical.model_dump_json().encode())
    with pytest.raises(ValueError, match="EXPANDED_RECEIPT_LIMIT"):
        _decode_fulfillment_candidate_wire(json.dumps(wire), inventory,
            fulfillment_capability_contracts(), wire_metadata=context)
    provider, calls = controlled_model_provider(inventory, canonical)
    result = form_fulfillment_projection(revision, ir, provider=provider,
        source_revision=inventory["source_revision"], exact_target_paths=inventory["exact_target_paths"])
    assert len(calls) == 2 and all("untrusted_fulfillment_candidate" not in call for call in calls)
    assert all(binding.state == "UNRESOLVED" for binding in result)
    assert "EXPANDED_RECEIPT_LIMIT" in result[0].formation_receipt["terminal_reason"]
    form_fulfillment_projection(revision, ir, provider=provider,
        source_revision=inventory["source_revision"], exact_target_paths=inventory["exact_target_paths"])
    assert len(calls) == 2


def test_compact_duplicate_json_keys_and_canonical_live_downgrade_are_rejected():
    from spg.providers.fulfillment_candidate import _decode_fulfillment_candidate_wire
    _, _, inventory, plan = controlled_capacity_case()
    wire, context = controlled_wire(inventory, plan)
    repeated = '{"v":1,' + json.dumps(wire)[1:]
    with pytest.raises(ValueError):
        _decode_fulfillment_candidate_wire(repeated, inventory, fulfillment_capability_contracts(), wire_metadata=context)
    calls = []
    def generate(**request):
        calls.append(request)
        return StructuredModelResult(output_text=plan.model_dump_json(), provider=ModelProvider.DEEPSEEK,
            requested_model="controlled-no-network", effective_model="controlled-no-network",
            request_id="controlled-downgrade", usage=ModelUsage(), timing=ModelTiming(), retry_count=0)
    provider = ModelFulfillmentCandidateProvider(lambda: SimpleNamespace(generate=generate, close=lambda: None))
    observations = []
    with pytest.raises(ValueError):
        provider.form(inventory, fulfillment_capability_contracts(), receipt_callback=lambda **row: observations.append(row))
    assert len(calls) == 1 and len(observations) == 1
    assert observations[0]["provider_wire_version"] == "fulfillment-compact-v1"


@pytest.mark.parametrize("failure", ("false-review", "stale-review"))
def test_compact_restore_never_grants_its_own_semantic_review_or_resets_budget(failure):
    revision, ir, inventory, plan = controlled_capacity_case()
    review_change = (lambda review: review.update(candidate_fingerprint="0" * 64)) if failure == "stale-review" else None
    provider, calls = controlled_model_provider(inventory, plan,
        equivalent=failure != "false-review", review_change=review_change)
    result = form_fulfillment_projection(revision, ir, provider=provider,
        exact_target_paths=inventory["exact_target_paths"])
    assert all(binding.state == "UNRESOLVED" for binding in result)
    # A different candidate's Review cannot justify feedback or another request.
    expected_calls = 2 if failure == "stale-review" else 4
    assert len(calls) == expected_calls
    assert result[0].formation_receipt["provider_call_count"] == expected_calls
    assert result[0].formation_receipt["attempt_count"] == expected_calls // 2
    form_fulfillment_projection(revision, ir, provider=provider,
        exact_target_paths=inventory["exact_target_paths"])
    assert len(calls) == expected_calls


def test_compact_owner_quote_restoration_cannot_reintroduce_a_synthetic_secret(monkeypatch):
    from spg.providers.fulfillment_candidate import _decode_fulfillment_candidate_wire
    revision, ir, _, _ = controlled_capacity_case()
    sentinel = "synthetic-private-capacity-token"
    monkeypatch.setenv("SPG_OPERATOR_TOKEN", sentinel)
    revision.context_facts = ("Retained source contains " + sentinel,)
    inventory = fulfillment_inventory(revision, ir, exact_target_paths=("index.html",))
    canonical = candidate(revision, ir, inventory)
    # The compact wire only restores context; other routes need not be validated.
    routes = []
    for route in canonical.routes:
        source = next(source for source in inventory["sources"] if source["source_ref"] == route.source_ref)
        text = fulfillment_source_semantic_text(source)
        routes.append(route.model_copy(update={"component_basis": FulfillmentComponentBasis(
            source_span_start=0, source_span_end=len(text), source_component_quote=text)}))
    wire, context = controlled_wire(inventory, canonical.model_copy(update={"routes": tuple(routes)}))
    with pytest.raises(ValueError):
        _decode_fulfillment_candidate_wire(json.dumps(wire), inventory,
            fulfillment_capability_contracts(), wire_metadata=context)


@pytest.mark.parametrize("method", ("form", "review"))
def test_actual_provider_observation_never_retains_decodable_unicode_escaped_synthetic_secret(monkeypatch, method):
    from hashlib import sha256
    _, _, inventory, plan = controlled_capacity_case()
    sentinel = "synthetic-private-测试-capacity-token"
    monkeypatch.setenv("SPG_OPERATOR_TOKEN", sentinel)
    if method == "form":
        payload, _ = controlled_wire(inventory, plan)
        payload["routes"][0].update(q=sentinel, r=sentinel)
    else:
        payload = controlled_review(inventory, plan).model_dump(mode="json")
        payload["source_results"][0]["reason"] = sentinel
    raw = json.dumps(payload, ensure_ascii=True)
    assert sentinel not in raw
    assert sentinel in json.dumps(json.loads(raw), ensure_ascii=False)
    calls = []
    def generate(**request):
        calls.append(request)
        return StructuredModelResult(output_text=raw, provider=ModelProvider.DEEPSEEK,
            requested_model="controlled-no-network", effective_model="controlled-no-network",
            request_id="controlled-escaped-secret", usage=ModelUsage(), timing=ModelTiming(), retry_count=0)
    provider = ModelFulfillmentCandidateProvider(lambda: SimpleNamespace(generate=generate, close=lambda: None))
    observations = []
    failure = None
    try:
        if method == "form":
            provider.form(inventory, fulfillment_capability_contracts(), receipt_callback=lambda **row: observations.append(row))
        else:
            provider.review(inventory, plan, capabilities=fulfillment_capability_contracts(),
                receipt_callback=lambda **row: observations.append(row))
    except ValueError as error:
        failure = error
    assert len(calls) == 1 and len(observations) == 1
    observed = observations[0]
    prefix = "candidate" if method == "form" else "review"
    assert observed[f"{prefix}_retained"] is False
    assert observed[f"{prefix}_output"] is None
    assert observed[f"{prefix}_output_sha256"] == sha256(raw.encode()).hexdigest()
    assert observed[f"{prefix}_output_bytes"] == len(raw.encode())
    assert failure is not None


def test_complete_pending_wire_metadata_cannot_replay_a_fully_unmarked_observation():
    revision, ir, inventory, plan = controlled_capacity_case()
    provider, calls = controlled_model_provider(inventory, plan)
    provider._fulfillment_receipts = []
    recorder = FulfillmentFormationReceipts(revision, inventory, memory=provider._fulfillment_receipts)
    metadata = provider.form_wire_metadata(inventory, fulfillment_capability_contracts())
    recorder.append("MODEL_REQUEST_PENDING", 1, feedback=None, **metadata)
    wire, _ = controlled_wire(inventory, plan)
    recorder.append("MODEL_RESPONSE_OBSERVED", 1, candidate_output=json.dumps(wire),
        model={"request_id": "controlled-marker-loss", "fixture": True})
    assert not any(key in recorder.records()[-1] for key in metadata)
    result = form_fulfillment_projection(revision, ir, provider=provider,
        source_revision=inventory["source_revision"], exact_target_paths=inventory["exact_target_paths"])
    assert all(binding.state == "UNRESOLVED" for binding in result)
    assert calls == []
    terminal = next(row for row in recorder.records() if row.get("terminal"))
    assert terminal["validation_passed"] is False
    assert terminal["terminal_reason"] in {
        "OBLIGATION_FORMATION_TRANSPORT__FulfillmentWireReceiptIdentityError",
        "OBLIGATION_FORMATION_WIRE_RECEIPT_IDENTITY_DRIFT",
    }
    before_replay = tuple(dict(row) for row in recorder.records())
    form_fulfillment_projection(revision, ir, provider=provider,
        source_revision=inventory["source_revision"], exact_target_paths=inventory["exact_target_paths"])
    assert calls == [] and recorder.records() == before_replay


def test_expanded_observation_capacity_stop_returns_unresolved_and_replays_without_calls():
    revision, ir = basis()
    # Each immutable synthetic source fits the existing component quote bound.
    # Their full canonical candidate together exceeds the Owner receipt bound.
    revision.context_facts = tuple(
        f"Controlled retained context {index}: " + chr(65 + index) * 60000
        for index in range(3)
    )
    inventory = fulfillment_inventory(revision, ir)
    plan = candidate(revision, ir, inventory)
    by_ref = {source["source_ref"]: source for source in inventory["sources"]}
    plan = plan.model_copy(update={
        "routes": tuple(
            route.model_copy(update={
                "component_basis": FulfillmentComponentBasis(
                    source_span_start=0,
                    source_span_end=len(fulfillment_source_semantic_text(by_ref[route.source_ref])),
                    source_component_quote=fulfillment_source_semantic_text(by_ref[route.source_ref]),
                )
            })
            for route in plan.routes
        )
    })
    assert len(json.dumps(plan.model_dump(mode="json"), ensure_ascii=False).encode()) > 131072
    original_facts = tuple(f.model_dump(mode="json") for f in revision.engineering_semantic_facts)
    oracle = ReviewedOracle([plan])
    first_error = None
    first_result = None
    try:
        first_result = form_fulfillment_projection(revision, ir, provider=oracle)
    except ValueError as error:
        first_error = str(error)

    rows = oracle._fulfillment_receipts
    terminal = next(row for row in rows if row.get("terminal"))
    assert terminal["stage"] == "MODEL_RESPONSE_OBSERVED"
    assert terminal["terminal_reason"] == "OBLIGATION_FORMATION_RECEIPT_LIMIT"
    assert terminal["validation_passed"] is False
    assert "candidate" not in terminal and "candidate_output" not in terminal
    assert len(oracle.calls) == 1 and oracle.review_calls == 0
    before_replay = tuple(dict(row) for row in rows)
    replay = form_fulfillment_projection(revision, ir, provider=oracle)
    assert len(oracle.calls) == 1 and oracle.review_calls == 0
    assert tuple(rows) == before_replay
    assert all(binding.state == "UNRESOLVED" for binding in replay)
    assert replay[0].formation_receipt["terminal_reason"] == "OBLIGATION_FORMATION_RECEIPT_LIMIT"
    assert tuple(f.model_dump(mode="json") for f in revision.engineering_semantic_facts) == original_facts
    # A durable capacity stop must finish the current call truthfully too.
    # The unmodified implementation escapes while appending after terminal.
    assert first_error is None, f"Capacity stop escaped instead of returning UNRESOLVED: {first_error}"
    assert first_result is not None
    assert all(binding.state == "UNRESOLVED" for binding in first_result)
