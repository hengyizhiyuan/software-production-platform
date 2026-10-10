"""Generation restrictions reuse Owner predicates; they cannot grant a PASS."""
import json
from copy import deepcopy
from hashlib import sha256

import pytest

from spg.application.governed_obligations import (
    _owner_source_preconditions, fulfillment_capability_contracts,
)
from spg.providers.fulfillment_candidate import (
    _formation_binding_choices, _formation_output_schema, _fulfillment_wire_schema,
    _fulfillment_wire_context, _decode_fulfillment_candidate_wire,
    _FulfillmentWireValidationError, _FulfillmentWireReceiptIdentityError,
)
from tests.test_c3_source_role_contract import shared_item_case


def case():
    revision, ir, inventory, plan = shared_item_case()
    capabilities = fulfillment_capability_contracts()
    preconditions = _owner_source_preconditions(revision, ir, inventory, capabilities)
    return revision, ir, inventory, plan, capabilities, preconditions


def test_point_of_use_provenance_does_not_import_derived_constraints_or_select_supports():
    from spg.providers.fulfillment_candidate import _formation_provenance_operands
    from spg.application.governed_obligations import validate_projection_candidate
    revision, ir, inventory, plan, capabilities, preconditions = case()
    before = deepcopy(preconditions)
    index = next(i for i,s in enumerate(inventory["sources"]) if s["kind"] == "WORK_CONSTRAINT")
    choices = _formation_binding_choices(inventory, capabilities, preconditions)[index]
    operands = _formation_provenance_operands(choices, capabilities)
    assert operands
    for observed, original in zip(operands, choices["necessary_source_proofs"], strict=True):
        assert observed["u_required_alternatives"] == original["minimal_support_sets"]
        assert observed["u_allowed_original_source_ordinals"] == sorted({i for p in original["minimal_support_sets"] for i in p})
        assert index not in observed["u_allowed_original_source_ordinals"]
        assert "NO_PERMISSION_OR_SEMANTIC_APPROVAL" in observed["selection_rule"]
    substituted = plan.model_copy(update={"routes": tuple(r.model_copy(update={
        "supporting_source_refs": (inventory["sources"][index]["source_ref"],)})
        if r.source_ref == inventory["sources"][index]["source_ref"] else r for r in plan.routes)})
    with pytest.raises(ValueError, match="SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN"):
        validate_projection_candidate(substituted, revision, ir, inventory, allow_review_pending=True)
    assert preconditions == before


def test_future_provenance_domain_excludes_negative_sibling_and_owner_rejects_it():
    from spg.application.governed_obligations import fulfillment_inventory, validate_projection_candidate
    from spg.providers.fulfillment_candidate import _formation_provenance_operands
    revision, ir, _, plan, capabilities, _ = case()
    original = "Leave a reviewable artifact for the Candidate gate."
    goal = ir.current_production[0].model_copy(update={"scope": (original,)})
    ir.current_production = (goal,)
    ir.items = tuple(i.model_copy(update={"production": goal}) if i.production else i for i in ir.items)
    revision.constraints = (original,)
    inventory = fulfillment_inventory(revision, ir)
    preconditions = _owner_source_preconditions(revision, ir, inventory, capabilities)
    index = next(i for i,s in enumerate(inventory["sources"]) if s["kind"] == "WORK_CONSTRAINT")
    negative = next(i for i,s in enumerate(inventory["sources"]) if s.get("clause_id") == "original-clause")
    rows = _formation_provenance_operands(_formation_binding_choices(inventory, capabilities, preconditions)[index], capabilities)
    seal = next(r for r in rows if r["capability"] == "CANDIDATE_SEAL")
    assert negative not in seal["u_allowed_original_source_ordinals"]
    from spg.domain.governed_obligation import FulfillmentRouteCandidate, FulfillmentComponentBasis
    from spg.application.governed_obligations import _projection_binding
    route = FulfillmentRouteCandidate(source_ref=inventory["sources"][index]["source_ref"],
        capability="CANDIDATE_SEAL", work_constraint_indices=(0,),
        supporting_source_refs=tuple(inventory["sources"][i]["source_ref"] for i in [*seal["u_required_alternatives"][0], negative]),
        component_basis=FulfillmentComponentBasis(source_span_start=0, source_span_end=len(original), source_component_quote=original),
        rationale="Negative sibling deliberately supplied as invalid future proof.")
    with pytest.raises(ValueError, match="FUTURE_PHASE_SOURCE_UNPROVEN"):
        _projection_binding(revision, ir, inventory, route, allow_calibrated=True, source_contract="v2")


def test_whole_context_preconditions_apply_to_clauses_and_constraints_without_business_aliases():
    _, _, inventory, _, capabilities, preconditions = case()
    schema = _formation_output_schema(inventory, capabilities, owner_preconditions=preconditions)
    context = next(i for i,c in enumerate(capabilities) if c['capability'] == 'RETAIN_CONTEXT')
    negative = next(row for row in preconditions['sources'] if row.get('polarity') == 'NEGATED')
    source = inventory['sources'][negative['source']]
    from spg.domain.governed_obligation import fulfillment_source_semantic_text
    length = len(fulfillment_source_semantic_text(source))
    branch = next(b for b in schema['properties']['routes']['items']['anyOf']
        if negative['source'] in b['properties']['s']['enum'] and context in b['properties']['c']['enum'])
    assert branch['anyOf'] == [{'properties': {'q': {'type': 'string', 'minLength': 1, 'maxLength': length - 1}}}]
    # Partial background stays only a proposal; the complete current source
    # cannot be retained to evade its required gates.
    assert negative['whole_source_context_only'] is False
    assert _formation_binding_choices(inventory, capabilities, preconditions)[negative['source']]['whole_source_context_only'] is False


def test_request_schema_only_excludes_existing_owner_rejections_and_preserves_unresolved():
    _, _, inventory, _, capabilities, preconditions = case()
    original = deepcopy(_fulfillment_wire_schema())
    schema = _formation_output_schema(inventory, capabilities, owner_preconditions=preconditions)
    branches = schema["properties"]["routes"]["items"]["anyOf"]
    unresolved = next(i for i,c in enumerate(capabilities) if c["capability"] == "UNRESOLVED")
    observed, pairs = {}, set()
    for branch in branches:
        assert branch["additionalProperties"] is False
        assert branch["required"] == original["$defs"]["_FulfillmentCompactRoute"]["required"]
        for source in branch["properties"]["s"]["enum"]:
            for capability in branch["properties"]["c"]["enum"]:
                assert (source, capability) not in pairs
                pairs.add((source, capability))
            observed.setdefault(source, []).extend(branch["properties"]["c"]["enum"])
    assert set(observed) == set(range(len(inventory["sources"])))
    for row in preconditions["sources"]:
        rejected = {r["capability"] for r in row["ineligible_binding_prerequisites"]}
        assert sorted(observed[row["source"]]) == [i for i in range(len(capabilities)) if i not in rejected]
        assert unresolved in observed[row["source"]]
    assert _fulfillment_wire_schema() == original
    assert schema["properties"]["v"] == original["properties"]["v"]
    negative = next(r for r in preconditions["sources"] if r.get("polarity") == "NEGATED")
    for i,c in enumerate(capabilities):
        if c["phase"] in {"CANDIDATE_SEAL", "HUMAN_INTEGRATION", "DELIVERY"}:
            assert i not in observed[negative["source"]]


def test_formation_identity_echo_is_exact_and_invalid_echo_is_never_recovered():
    _, _, inventory, _, capabilities, preconditions = case()
    context = _fulfillment_wire_context(inventory, capabilities, owner_preconditions=preconditions)
    metadata = {k: context[k] for k in ("wire_request_fingerprint", "wire_table_fingerprint")}
    schema = _formation_output_schema(inventory, capabilities, owner_preconditions=preconditions, wire_metadata=metadata)
    assert schema["properties"]["h"]["enum"] == [context["wire_request_fingerprint"]]
    assert schema["properties"]["d"]["enum"] == [context["wire_table_fingerprint"]]
    _, _, _, wire = wire_case(preconditions)
    for bad in (wire["d"][:20] + wire["d"], "0" * 64):
        changed = deepcopy(wire);changed["d"] = bad
        with pytest.raises(ValueError, match="WIRE_SCHEMA_INVALID|WIRE_BASIS_DRIFT"):
            _decode_fulfillment_candidate_wire(json.dumps(changed), inventory, capabilities, owner_preconditions=preconditions)
        assert changed["d"] == bad
    assert "enum" not in _fulfillment_wire_schema()["properties"]["d"]


@pytest.mark.parametrize("field", ["inventory", "capabilities", "source_identity", "source_ordinal", "unresolved"])
def test_request_constraints_cannot_change_their_original_identity_or_hide_unresolved(field):
    _, _, inventory, _, capabilities, preconditions = case()
    changed = deepcopy(preconditions)
    if field == "inventory": changed["inventory_fingerprint"] = "0" * 64
    elif field == "capabilities": changed["capabilities_fingerprint"] = "0" * 64
    elif field == "source_identity": changed["sources"][0]["source_ref"] = "invented"
    elif field == "source_ordinal": changed["sources"][0]["source"] = 1
    else:
        unresolved = next(i for i,c in enumerate(capabilities) if c["capability"] == "UNRESOLVED")
        changed["sources"][0]["ineligible_binding_prerequisites"].append({"capability": unresolved, "codes": ["invented"]})
    with pytest.raises(_FulfillmentWireReceiptIdentityError, match="IDENTITY_DRIFT"):
        _formation_binding_choices(inventory, capabilities, changed)


def wire_case(preconditions):
    _, _, inventory, _, capabilities, _ = case()
    context = _fulfillment_wire_context(inventory, capabilities, owner_preconditions=preconditions)
    routes = [{"s": i, "c": 11, "a": 0, "z": len(text), "q": None,
        "f": [], "t": [], "u": [], "r": "Controlled unadmitted diagnostic observation."}
        for i,text in enumerate(context["source_texts"])]
    return inventory, capabilities, context, {"v": 1, "h": context["wire_request_fingerprint"],
        "d": context["wire_table_fingerprint"], "routes": routes}


def test_coverage_observation_reports_exact_missing_ranges_but_never_repairs_original_wire():
    _, _, _, _, _, preconditions = case()
    inventory, capabilities, context, wire = wire_case(preconditions)
    wire["routes"][0]["z"] -= 2
    raw = json.dumps(wire)
    with pytest.raises(_FulfillmentWireValidationError) as failure:
        _decode_fulfillment_candidate_wire(raw, inventory, capabilities, owner_preconditions=preconditions)
    d = failure.value.diagnostics
    row = next(v for v in d["violations"] if v["code"] == "OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST")
    text = context["source_texts"][0]
    expected = {i for i in range(wire["routes"][0]["z"], len(text)) if not text[i].isspace()}
    assert {i for a,z in row["uncovered_codepoint_ranges"] for i in range(a,z)} == expected
    assert d["wire_output_fingerprint"] == sha256(raw.encode()).hexdigest()
    assert d["inventory_fingerprint"] == inventory["inventory_fingerprint"]
    assert row["observed_source_route_indices"] == [0]
    assert "NO_SPAN_REPAIR" in row["disposition"]
    assert json.dumps(wire) == raw
    assert "INDEPENDENT_SEMANTIC_REVIEW" in d["not_evaluable"]


@pytest.mark.parametrize("contract", ["complete-value-owner-observations-v1", "complete-value-owner-observations-v2"])
def test_schema_feedback_is_version_bound_private_values_are_not_recorded(contract):
    _, _, _, _, _, preconditions = case()
    preconditions["syntax_observation_contract"] = contract
    inventory, capabilities, _, wire = wire_case(preconditions)
    wire["routes"][0]["private-arbitrary-field"] = "DO_NOT_RECORD_THIS_PRIVATE_VALUE"
    raw = json.dumps(wire)
    with pytest.raises(_FulfillmentWireValidationError) as failure:
        _decode_fulfillment_candidate_wire(raw, inventory, capabilities, owner_preconditions=preconditions)
    d = failure.value.diagnostics
    assert d["wire_output_fingerprint"] == sha256(raw.encode()).hexdigest()
    assert "DO_NOT_RECORD_THIS_PRIVATE_VALUE" not in json.dumps(d)
    assert "private-arbitrary-field" not in json.dumps(d)
    row = d["violations"][0]
    assert row["code"] == "OBLIGATION_FORMATION_WIRE_SCHEMA_INVALID"
    if contract.endswith("v2"):
        assert row["schema_observations"] == [{"predicate": "extra_forbidden", "location": ["routes", 0, "UNKNOWN_FIELD"]}]
    else:
        assert "schema_observations" not in row


def test_legacy_request_without_preconditions_keeps_generation_schema_unchanged():
    _, _, inventory, _, capabilities, _ = case()
    schema = _formation_output_schema(inventory, capabilities)
    assert schema["properties"]["routes"]["items"] == {"$ref": "#/$defs/_FulfillmentCompactRoute"}


@pytest.mark.parametrize("contract", ["complete-value-owner-observations-v1", "complete-value-owner-observations-v2"])
def test_complete_original_value_can_only_supply_unadmitted_owner_observations(contract):
    from spg.providers.fulfillment_candidate import _fulfillment_wire_route_observations
    _, _, _, _, _, preconditions = case()
    preconditions["syntax_observation_contract"] = contract
    inventory, capabilities, _, wire = wire_case(preconditions)
    raw = json.dumps(wire) + "}"
    with pytest.raises(_FulfillmentWireValidationError, match="WIRE_JSON_INVALID"):
        _decode_fulfillment_candidate_wire(raw, inventory, capabilities, owner_preconditions=preconditions)
    observations, unavailable = _fulfillment_wire_route_observations(raw, inventory, capabilities,
        owner_preconditions=preconditions)
    assert len(observations) == len(wire["routes"])
    assert unavailable == ["COMPLETE_WIRE_SYNTAX"]


def test_v2_feedback_replay_preserves_original_attempt_and_does_not_call_model_again():
    from tests.test_c3_fulfillment_repair_context import repair_case
    provider, calls, wires, run = repair_case()
    assert all(b.state != "UNRESOLVED" for b in run())
    rows = deepcopy(provider._fulfillment_receipts)
    pending = next(r for r in rows if r["stage"] == "MODEL_REQUEST_PENDING")
    assert pending["owner_source_preconditions"]["syntax_observation_contract"] == "complete-value-owner-observations-v2"
    count = len(calls)
    run()
    assert len(calls) == count and provider._fulfillment_receipts == rows


def test_generation_bounds_and_support_domains_reuse_exact_original_owner_operands():
    from spg.domain.governed_obligation import fulfillment_source_semantic_text
    _, _, inventory, _, capabilities, preconditions = case()
    schema = _formation_output_schema(inventory, capabilities, owner_preconditions=preconditions)
    for branch in schema["properties"]["routes"]["items"]["anyOf"]:
        props = {}
        for field, value in branch["properties"].items():
            if "$ref" in value:
                original = schema
                for key in value["$ref"][2:].split("/"): original = original[key]
                props[field] = original
            else:
                props[field] = value
        for source_index in props["s"]["enum"]:
            length = len(fulfillment_source_semantic_text(inventory["sources"][source_index]))
            assert props["a"]["minimum"] == 0 and props["a"]["maximum"] == length - 1
            assert props["z"]["minimum"] == 1 and props["z"]["maximum"] == length
            row = preconditions["sources"][source_index]
            for capability in props["c"]["enum"]:
                proof = next((p for p in row.get("necessary_source_proofs", []) if p["capability"] == capability), None)
                if proof:
                    assert props["u"]["items"]["enum"] == sorted({i for alternative in proof["minimal_support_sets"] for i in alternative})
                    assert props["u"]["minItems"] == min(len(alternative) for alternative in proof["minimal_support_sets"])
                else:
                    assert "minItems" not in props["u"]
    # No fabricated witness, source or span is emitted by request constraints.
    assert not {"approved", "covered", "passed"} & schema.keys()


def test_fact_semantic_reference_is_distinct_from_broad_provenance_for_proposer_and_critic():
    from spg.providers.fulfillment_candidate import _formation_source_table, _review_component_table
    _, _, inventory, plan, capabilities, preconditions = case()
    before = deepcopy(inventory)
    context = _fulfillment_wire_context(inventory, capabilities, owner_preconditions=preconditions)
    table = _formation_source_table(context, inventory=inventory)
    comparison = _review_component_table(inventory, plan, capabilities)
    for source, row in zip(inventory["sources"], table, strict=True):
        if source["kind"] != "FACT":
            assert "authoritative_semantic_fact" not in row
            continue
        assert row["authoritative_semantic_fact"] == source["payload"]
        assert row["primary_semantic_text"] == source["provenance"]["source_text"]
        assert "NOT_A_NEW_PARENT_INTENT" in row["original_text_role"]
        # A broad parent quote is kept exactly; no synthetic Fact text replaces it.
        assert "internal review exercise" in row["primary_semantic_text"]
        critic = [r for r in comparison if r["source_ref"] == source["source_ref"]]
        assert critic and all(r["authoritative_semantic_fact"] == source["payload"] for r in critic)
        row["authoritative_semantic_fact"]["value"] = "untrusted change to derived view"
    assert inventory == before


def test_invented_source_kind_in_original_fact_view_is_rejected():
    from spg.providers.fulfillment_candidate import _formation_source_table
    _, _, inventory, _, capabilities, preconditions = case()
    context = _fulfillment_wire_context(inventory, capabilities, owner_preconditions=preconditions)
    substituted = deepcopy(inventory)
    substituted["sources"][0]["kind"] = "WORK_CONSTRAINT"
    with pytest.raises(_FulfillmentWireReceiptIdentityError, match="SOURCE_TABLE_IDENTITY_DRIFT"):
        _formation_source_table(context, inventory=substituted)


def test_review_generation_identity_domains_do_not_supply_or_repair_semantic_verdicts():
    from spg.providers.fulfillment_candidate import _review_output_schema
    from spg.domain.governed_obligation import fulfillment_candidate_fingerprint, fulfillment_components_fingerprint, fulfillment_component_id
    _, _, inventory, plan, _, _ = case()
    schema = _review_output_schema(inventory, plan)
    from spg.domain.governed_obligation import FulfillmentSemanticReviewCandidate
    canonical = FulfillmentSemanticReviewCandidate.model_json_schema()
    for name in ('FulfillmentSemanticSourceReview', 'FulfillmentSemanticComponentReview'):
        assert schema['$defs'][name]['properties']['reason']['maxLength'] == 512
        assert canonical['$defs'][name]['properties']['reason']['maxLength'] == 1000
    assert schema["properties"]["candidate_fingerprint"]["enum"] == [fulfillment_candidate_fingerprint(plan)]
    assert schema["properties"]["components_fingerprint"]["enum"] == [fulfillment_components_fingerprint(plan)]
    expected = {(fulfillment_component_id(r, inventory["inventory_fingerprint"]), r.capability) for r in plan.routes}
    observed = set()
    for branch in schema["properties"]["component_results"]["items"]["anyOf"]:
        props = branch["properties"]
        capability, = props["capability"]["enum"]
        observed.update((c, capability) for c in props["component_id"]["enum"])
        assert props["context_only"]["enum"] == [capability == "RETAIN_CONTEXT"]
        for field in ("complete_and_equivalent", "nonredundant", "owner_phase_evidence_valid"):
            assert props[field]["type"] == "boolean" and "enum" not in props[field]
    assert observed == expected
    assert schema["properties"]["component_results"]["minItems"] == len(plan.routes)
    assert schema["properties"]["source_results"]["maxItems"] == len(inventory["sources"])


def test_wrong_review_identity_and_real_semantic_rejection_still_fail_without_backfill():
    from tests.test_c3_semantic_contract_calibration import review
    from spg.application.governed_obligations import validate_projection_candidate
    from spg.domain.governed_obligation import FulfillmentSemanticReviewCandidate
    revision, ir, inventory, plan, _, _ = case()
    verdict = review(inventory, plan)
    raw = verdict.model_dump(mode="json")
    raw["component_results"][0]["component_id"] = raw["component_results"][0]["component_id"][:-2]
    with pytest.raises(ValueError): FulfillmentSemanticReviewCandidate.model_validate(raw)
    rejected = verdict.model_copy(update={"component_results": tuple(r.model_copy(update={
        "complete_and_equivalent": False, "reason": "Controlled independent rejection of unsupported meaning."})
        if r.capability == "RETAIN_CONTEXT" else r for r in verdict.component_results)})
    with pytest.raises(ValueError, match="SEMANTIC_COMPONENT_MISMATCH"):
        validate_projection_candidate(plan, revision, ir, inventory, semantic_review=rejected)


def test_review_identity_skeleton_contains_no_verdict_and_duplicates_still_fail():
    from spg.providers.fulfillment_candidate import _review_result_identity_slots
    from spg.domain.governed_obligation import fulfillment_component_id
    from spg.application.governed_obligations import validate_projection_candidate
    from tests.test_c3_semantic_contract_calibration import review
    revision, ir, inventory, plan, _, _ = case()
    original = deepcopy(plan.model_dump(mode="json"))
    slots = _review_result_identity_slots(inventory, plan)
    assert slots["source_results"] == [{"source_ref": s["source_ref"]} for s in inventory["sources"]]
    assert slots["component_results"] == [{"component_id": fulfillment_component_id(r, inventory["inventory_fingerprint"]),
                                         "capability": r.capability} for r in plan.routes]
    assert slots["source_result_count"] == len(inventory["sources"])
    assert slots["component_result_count"] == len(plan.routes)
    verdict = review(inventory, plan)
    duplicated = verdict.model_copy(update={"component_results": (*verdict.component_results, verdict.component_results[0])})
    with pytest.raises(ValueError, match="COMPONENT_REVIEW_IDENTITY_DRIFT"):
        validate_projection_candidate(plan, revision, ir, inventory, semantic_review=duplicated)
    assert plan.model_dump(mode="json") == original


def test_legacy_review_shape_is_not_rewritten_by_generation_constraints():
    from spg.providers.fulfillment_candidate import _review_output_schema
    from spg.domain.governed_obligation import FulfillmentSemanticReviewCandidate
    _, _, inventory, plan, _, _ = case()
    legacy = plan.model_copy(update={"routes": tuple(r.model_copy(update={"component_basis": None}) for r in plan.routes)})
    schema = _review_output_schema(inventory, legacy)
    assert "anyOf" in schema["properties"]["component_results"]
    original = FulfillmentSemanticReviewCandidate(inventory_fingerprint=inventory["inventory_fingerprint"],
        candidate_fingerprint="a" * 64, components_fingerprint="b" * 64,
        source_results=({"source_ref": inventory["sources"][0]["source_ref"], "complete_and_equivalent": True, "reason": "Legacy receipt retained."},))
    assert "component_results" not in original.model_dump(mode="json")


def test_review_request_judges_fixed_plan_after_source_consumer_comparison():
    from spg.providers.fulfillment_candidate import _review_output_schema
    _, _, inventory, plan, _, _ = case()
    schema = _review_output_schema(inventory, plan)
    for name in ("FulfillmentSemanticSourceReview", "FulfillmentSemanticComponentReview"):
        fields = schema["$defs"][name]["properties"]
        assert list(fields).index("reason") < list(fields).index("complete_and_equivalent")
        assert "unchanged fingerprinted plan" in fields["complete_and_equivalent"]["description"]
        assert fields["complete_and_equivalent"]["type"] == "boolean"
        assert "enum" not in fields["complete_and_equivalent"]
    # This describes an independent verdict; no new repair or admission output.
    assert set(schema["properties"]) == {"inventory_fingerprint", "candidate_fingerprint",
        "components_fingerprint", "source_results", "component_results"}


def test_source_geometry_view_cannot_change_components_or_relax_lost_operators():
    from spg.providers.fulfillment_candidate import _formation_source_table
    from spg.domain.governed_obligation import fulfillment_source_semantic_text
    _, _, inventory, _, capabilities, preconditions = case()
    before = deepcopy(inventory)
    context = _fulfillment_wire_context(inventory, capabilities, owner_preconditions=preconditions)
    rows = _formation_source_table(context, inventory=inventory)
    for source, row in zip(inventory["sources"], rows, strict=True):
        assert row["whole_source_basis"] == {"a": 0, "z": len(fulfillment_source_semantic_text(source)), "q": None}
        assert "NOT_A_COMPONENT" in row["basis_role"]
        assert "capability" not in row["whole_source_basis"]
    assert inventory == before
    # Geometry is a read-only view, not an automatic extension of a model span.
    inv, caps, _, wire = wire_case(preconditions)
    wire["routes"][0]["a"] = 1
    with pytest.raises(_FulfillmentWireValidationError, match="SOURCE_CONTRIBUTION_LOST"):
        _decode_fulfillment_candidate_wire(json.dumps(wire), inv, caps, owner_preconditions=preconditions)


def test_generation_requires_original_quote_for_partial_components_without_changing_wire_v1():
    _, _, inventory, _, capabilities, preconditions = case()
    schema = _formation_output_schema(inventory, capabilities, owner_preconditions=preconditions)
    for branch in schema["properties"]["routes"]["items"]["anyOf"]:
        guards = branch["anyOf"]
        if len(guards) == 1:
            assert guards[0]["properties"]["q"]["type"] == "string"
            assert guards[0]["properties"]["q"]["maxLength"] == branch["properties"]["z"]["maximum"] - 1
            continue
        assert guards[0]["properties"]["a"]["enum"] == [0]
        length, = guards[0]["properties"]["z"]["enum"]
        assert guards == [
            {"properties": {"q": {"type": "null"}, "a": {"enum": [0]}, "z": {"enum": [length]}}},
            {"properties": {"q": {"type": "string", "minLength": 1}}},
        ]
    # This request guard cannot supply text, extend spans, or admit a route.
    inv, caps, _, wire = wire_case(preconditions)
    wire["routes"][0]["a"] = 1
    with pytest.raises(_FulfillmentWireValidationError, match="SOURCE_CONTRIBUTION_LOST"):
        _decode_fulfillment_candidate_wire(json.dumps(wire), inv, caps, owner_preconditions=preconditions)
    # An explicit original quote can be located by the existing Owner; this
    # does not invent the missing character in the numeric-only proposal.
    from spg.application.governed_obligations import locate_projection_components
    inv, caps, _, wire = wire_case(preconditions)
    plan = _decode_fulfillment_candidate_wire(json.dumps(wire), inv, caps, owner_preconditions=preconditions)
    wire["routes"][0].update(a=1, q=plan.routes[0].component_basis.source_component_quote)
    raw = _decode_fulfillment_candidate_wire(json.dumps(wire), inv, caps, owner_preconditions=preconditions)
    located, adjustments = locate_projection_components(raw, inv)
    assert adjustments and located.routes[0].component_basis == plan.routes[0].component_basis


def test_shared_existing_ir_items_round_trip_every_admitted_semantic_field():
    from spg.providers.fulfillment_candidate import _formation_inventory_view, _restore_formation_inventory_view
    _, _, inventory, _, _, _ = case()
    original = deepcopy(inventory)
    view, items = _formation_inventory_view(inventory)
    assert items and len(items) < sum("item" in s["payload"] for s in inventory["sources"])
    assert _restore_formation_inventory_view(view, items) == original
    assert inventory == original
    assert [s["source_ref"] for s in view["sources"]] == [s["source_ref"] for s in original["sources"]]
    assert view["inventory_fingerprint"] == original["inventory_fingerprint"]
    # Original clause text/polarity/scope and Fact payloads are unchanged.
    for before, after in zip(original["sources"], view["sources"], strict=True):
        if "clause" in before["payload"]:
            assert after["payload"]["clause"] == before["payload"]["clause"]
        if before["kind"] == "FACT": assert after == before
    changed = deepcopy(items)
    key = next(iter(changed));changed[key]["item_id"] = "invented-new-item"
    with pytest.raises(_FulfillmentWireReceiptIdentityError, match="IR_ITEM_IDENTITY_DRIFT"):
        _restore_formation_inventory_view(view, changed)
    with pytest.raises(_FulfillmentWireReceiptIdentityError, match="IR_ITEM_IDENTITY_DRIFT"):
        _restore_formation_inventory_view(view, {})


def test_conflicting_existing_ir_item_records_fail_before_model_call():
    from spg.providers.fulfillment_candidate import _formation_inventory_view
    _, _, inventory, _, _, _ = case()
    changed = deepcopy(inventory)
    items = [s["payload"]["item"] for s in changed["sources"] if "item" in s["payload"]]
    assert len(items) > 1
    items[-1]["statement"] = "Different original authority under the same identity"
    with pytest.raises(_FulfillmentWireReceiptIdentityError, match="IR_ITEM_IDENTITY_DRIFT"):
        _formation_inventory_view(changed)


def test_shared_schema_fields_preserve_exact_original_wire_restrictions():
    _, _, inventory, _, capabilities, preconditions = case()
    schema = _formation_output_schema(inventory, capabilities, owner_preconditions=preconditions)
    canonical = schema["$defs"]["_FulfillmentCompactRoute"]["properties"]
    for branch in schema["properties"]["routes"]["items"]["anyOf"]:
        for field in ("q", "f", "t", "r"):
            ref = branch["properties"][field]["$ref"]
            target = schema
            for key in ref[2:].split("/"): target = target[key]
            assert target == canonical[field]
    # Fact-only ordinals, exact paths, quote limits and schema closure survive.
    assert canonical["f"]["items"]["enum"] == [i for i,s in enumerate(inventory["sources"]) if s["kind"] == "FACT"]
    assert canonical["t"]["items"]["enum"] == list(range(len(inventory["exact_target_paths"])))
    assert schema["$defs"]["_FulfillmentCompactRoute"]["additionalProperties"] is False


def test_whole_required_constraint_retention_observes_owner_without_discarding_partial_background():
    from spg.application.governed_obligations import _projection_binding
    revision, ir, inventory, plan, capabilities, preconditions = case()
    source = next(s for s in inventory["sources"] if s["kind"] == "WORK_CONSTRAINT")
    ordinal = inventory["sources"].index(source)
    row = preconditions["sources"][ordinal]["whole_source_context_retention"]
    assert not row["whole_source_eligible"] and row["required_support_alternatives"] == []
    original = next(r for r in plan.routes if r.source_ref == source["source_ref"])
    with pytest.raises(ValueError, match="SOURCE_CORRESPONDENCE_UNPROVEN"):
        _projection_binding(revision, ir, inventory, original.model_copy(update={"capability": "RETAIN_CONTEXT"}), allow_calibrated=True)
    branches = _formation_output_schema(inventory, capabilities, owner_preconditions=preconditions)["properties"]["routes"]["items"]["anyOf"]
    retained = next(b for b in branches if ordinal in b["properties"]["s"]["enum"] and row["capability"] in b["properties"]["c"]["enum"])
    assert retained["anyOf"] == [{"properties": {"q": {"type": "string", "minLength": 1, "maxLength": len(source["payload"]["content"]) - 1}}}]
    # Historical v4 requests still recompute exactly their original fields.
    historical = _owner_source_preconditions(revision, ir, inventory, capabilities, typed_prerequisite_contract="existing-owner-typed-prerequisites-v4")
    assert all("whole_source_context_retention" not in r for r in historical["sources"])


def test_corresponding_observed_context_constraint_keeps_legal_whole_retention():
    from spg.application.governed_obligations import fulfillment_inventory, _projection_binding
    from spg.domain.governed_obligation import FulfillmentRouteCandidate
    from spg.domain.intent_realization import SemanticKind
    from spg.domain.interaction_actions import ActionSpeechAct
    revision, ir, _, _, capabilities, _ = case()
    text = "The repository owner recorded an observational background convention."
    item = ir.items[0].model_copy(update={"item_id": "observed-background", "kind": SemanticKind.FACT,
        "statement": text, "production": None, "action": None, "requires_human": False})
    clause = ir.clauses[0].model_copy(update={"semantic_item_ids": (item.item_id,), "clause_id": "observed-background-clause",
        "source_text": text, "modality": "ASSERTION", "polarity": "AFFIRMATIVE", "requested_effects": (),
        "speech_act": ActionSpeechAct.DISCUSSION})
    ir.items = (*ir.items, item); ir.clauses = (*ir.clauses, clause)
    revision.constraints = (*revision.constraints, text)
    inventory = fulfillment_inventory(revision, ir)
    preconditions = _owner_source_preconditions(revision, ir, inventory, capabilities)
    source = next(s for s in inventory["sources"] if s["kind"] == "WORK_CONSTRAINT" and s["payload"]["content"] == text)
    row = preconditions["sources"][inventory["sources"].index(source)]["whole_source_context_retention"]
    assert row["whole_source_eligible"] and row["required_support_alternatives"]
    refs = tuple(inventory["sources"][i]["source_ref"] for i in row["required_support_alternatives"][0])
    route = FulfillmentRouteCandidate(source_ref=source["source_ref"], capability="RETAIN_CONTEXT",
        work_constraint_indices=(source["index"],), supporting_source_refs=refs,
        component_basis={"source_span_start": 0, "source_span_end": len(text), "source_component_quote": text},
        rationale="Controlled Owner context prerequisite, not a real admission.")
    assert _projection_binding(revision, ir, inventory, route, allow_calibrated=True).state == "RETAINED_CONTEXT"


@pytest.mark.parametrize("qualifiers", [{"only_artifact": True}, {"only_artifact": False}, {"permitted_paths_only": "yes"}])
def test_v3_literal_scope_claim_keeps_qualifiers_and_requires_independent_component_review(qualifiers):
    from tests.test_c3_fulfillment_components import current_lifecycle_candidate, ReviewedOracle
    from tests.test_c3_semantic_contract_calibration import review
    from spg.domain.engineering_semantics import SemanticRelation
    from spg.application.governed_obligations import fulfillment_inventory, validate_projection_candidate
    from spg.domain.governed_obligation import exact_file_scope_paths, literal_file_scope_value_paths
    revision, ir, _, plan = current_lifecycle_candidate()
    fact = revision.engineering_semantic_facts[0].model_copy(update={"relation": SemanticRelation.SCOPE,
        "value": ["index.html"], "scope": "permitted changed artifacts", "qualifiers": qualifiers})
    before = deepcopy(fact.model_dump(mode="json"))
    revision.engineering_semantic_facts = (fact,)
    inventory = fulfillment_inventory(revision, ir)
    plan = plan.model_copy(update={"inventory_fingerprint": inventory["inventory_fingerprint"],
        "routes": (plan.routes[0].model_copy(update={"capability": "GIT_DIFF_SCOPE"}), *plan.routes[1:])})
    assert exact_file_scope_paths(fact, qualified=True) is None
    assert literal_file_scope_value_paths(fact) == ("index.html",)
    with pytest.raises(ValueError, match="SCOPE_VALUE_UNSUPPORTED"):
        validate_projection_candidate(plan, revision, ir, inventory, semantic_review=review(inventory, plan), source_contract="v2")
    with pytest.raises(ValueError, match="COMPONENT_REVIEW_REQUIRED"):
        validate_projection_candidate(plan, revision, ir, inventory, semantic_review=ReviewedOracle([]).review(inventory, plan), source_contract="v3")
    verdict = review(inventory, plan)
    rejected = verdict.model_copy(update={"component_results": tuple(r.model_copy(update={"complete_and_equivalent": False})
        if r.capability == "GIT_DIFF_SCOPE" else r for r in verdict.component_results)})
    with pytest.raises(ValueError, match="SEMANTIC_COMPONENT_MISMATCH"):
        validate_projection_candidate(plan, revision, ir, inventory, semantic_review=rejected, source_contract="v3")
    # Controlled affirmative review proves contract expressibility only; the
    # false qualifier variant is deliberately NOT a live semantic qualification.
    if qualifiers == {"only_artifact": True}:
        bindings = validate_projection_candidate(plan, revision, ir, inventory, semantic_review=verdict, source_contract="v3")
        assert all(b.state != "UNRESOLVED" for b in bindings)
    content = plan.model_copy(update={"routes": (plan.routes[0].model_copy(update={"capability": "ARTIFACT_CONTENT"}), *plan.routes[1:])})
    with pytest.raises(ValueError, match="FILE_SCOPE_OWNER_MISMATCH"):
        validate_projection_candidate(content, revision, ir, inventory, semantic_review=review(inventory, content), source_contract="v3")
    assert fact.model_dump(mode="json") == before


@pytest.mark.parametrize("expression", [("PROHIBIT_EXTERNAL_RELEASE",), ("不得形成外部发布效果",)])
def test_v3_open_effect_expression_preserves_exact_negative_derivation_without_aliases(expression):
    from spg.application.governed_obligations import fulfillment_inventory, work_constraint_sources_correspond
    from spg.domain.governed_obligation import FulfillmentPhase
    revision, ir, _, _ = shared_item_case()
    ir.clauses = tuple(c.model_copy(update={"requested_effects": expression}) if c.polarity == "NEGATED" else c for c in ir.clauses)
    inventory = fulfillment_inventory(revision, ir)
    supports = [s for s in inventory["sources"] if s.get("clause_id") == next(c.clause_id for c in ir.clauses if c.polarity == "NEGATED")]
    args = dict(component="deploy", phase=FulfillmentPhase.CONTINUOUS_FROM_ADMISSION, semantic_component_declared=True, calibrated=True)
    assert not work_constraint_sources_correspond(ir, revision.constraints[0], supports, source_contract="v2", **args)
    assert work_constraint_sources_correspond(ir, revision.constraints[0], supports, source_contract="v3", **args)
    assert not work_constraint_sources_correspond(ir, "Excluded from this Work: invented effect", supports, source_contract="v3", **args)
    assert not work_constraint_sources_correspond(ir, revision.constraints[0], [], source_contract="v3", **args)
    assert next(c.requested_effects for c in ir.clauses if c.polarity == "NEGATED") == expression


def test_v3_seal_is_distinct_from_human_acceptance_and_integration():
    from tests.test_c3_fulfillment_components import current_lifecycle_candidate
    from tests.test_c3_semantic_contract_calibration import review
    from spg.application.governed_obligations import fulfillment_inventory, validate_projection_candidate
    revision, ir, _, plan = current_lifecycle_candidate()
    ir.current_production = tuple(g.model_copy(update={"acceptance_required": False}) for g in ir.current_production)
    inventory = fulfillment_inventory(revision, ir)
    plan = plan.model_copy(update={"inventory_fingerprint": inventory["inventory_fingerprint"]})
    with pytest.raises(ValueError, match="CANDIDATE_GATE_NOT_REQUIRED"):
        validate_projection_candidate(plan, revision, ir, inventory, semantic_review=review(inventory, plan), source_contract="v2")
    assert validate_projection_candidate(plan, revision, ir, inventory, semantic_review=review(inventory, plan), source_contract="v3")
    integration = plan.model_copy(update={"routes": tuple(r.model_copy(update={"capability": "HUMAN_INTEGRATION"})
        if r.capability == "CANDIDATE_SEAL" else r for r in plan.routes)})
    with pytest.raises(ValueError, match="CANDIDATE_GATE_NOT_REQUIRED"):
        validate_projection_candidate(integration, revision, ir, inventory, semantic_review=review(inventory, integration), source_contract="v3")



def _controlled_v3_binding_receipt(revision, ir, inventory, plan):
    """Controlled contract receipt; never a model or production qualification."""
    from types import SimpleNamespace
    from tests.test_c3_semantic_contract_calibration import review
    from tests.test_c3_fulfillment_capacity_representation import controlled_wire, decode_review_input
    from spg.application.governed_obligations import form_fulfillment_projection
    from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
    from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
    def generate(**request):
        payload = json.loads(request["input_text"])
        if "untrusted_fulfillment_candidate" in payload:
            output = review(inventory, decode_review_input(payload)).model_dump_json()
        else:
            wire, _ = controlled_wire(inventory, plan, feedback=payload.get("same_basis_validation_feedback"),
                owner_preconditions=payload.get("owner_source_preconditions"))
            output = json.dumps(wire)
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model="controlled-v3-contract", effective_model="controlled-v3-contract",
            request_id="controlled-v3", usage=ModelUsage(), timing=ModelTiming(), retry_count=0)
    provider = ModelFulfillmentCandidateProvider(lambda: SimpleNamespace(generate=generate, close=lambda: None))
    result = form_fulfillment_projection(revision, ir, provider=provider,
        source_revision=inventory["source_revision"], exact_target_paths=inventory["exact_target_paths"])
    assert all(b.state != "UNRESOLVED" for b in result)
    return result


def test_v9_generation_probe_matches_qualified_scope_consumer_and_keeps_v8_replay():
    from tests.test_c3_fulfillment_components import current_lifecycle_candidate
    from spg.domain.engineering_semantics import SemanticRelation
    from spg.application.governed_obligations import fulfillment_inventory
    revision, ir, _, _ = current_lifecycle_candidate()
    fact = revision.engineering_semantic_facts[0].model_copy(update={"relation": SemanticRelation.SCOPE,
        "value": ("index.html",), "scope": "permitted changed artifacts", "qualifiers": {"only_artifact": True}})
    revision.engineering_semantic_facts = (fact,)
    inv = fulfillment_inventory(revision, ir)
    caps = fulfillment_capability_contracts()
    cap = next(i for i, c in enumerate(caps) if c["capability"] == "GIT_DIFF_SCOPE")
    old = _owner_source_preconditions(revision, ir, inv, caps, typed_prerequisite_contract="existing-owner-typed-prerequisites-v8")
    new = _owner_source_preconditions(revision, ir, inv, caps)
    old_codes = next(r["codes"] for r in old["sources"][0]["ineligible_binding_prerequisites"] if r["capability"] == cap)
    assert "OBLIGATION_FACT_SCOPE_VALUE_UNSUPPORTED" in old_codes
    assert not any(r["capability"] == cap for r in new["sources"][0]["ineligible_binding_prerequisites"])
    assert _owner_source_preconditions(revision, ir, inv, caps, typed_prerequisite_contract="existing-owner-typed-prerequisites-v8") == old
    assert fact.qualifiers == {"only_artifact": True}


@pytest.mark.parametrize("expression", [("PROHIBIT_EXTERNAL_RELEASE",), ("不得形成外部发布效果",)])
def test_v3_open_negative_effect_has_complete_projection_not_only_support_probe(expression):
    from tests.test_c3_semantic_contract_calibration import review
    from spg.application.governed_obligations import fulfillment_inventory, validate_projection_candidate
    revision, ir, _, plan = shared_item_case()
    ir.clauses = tuple(c.model_copy(update={"requested_effects": expression}) if c.polarity == "NEGATED" else c for c in ir.clauses)
    inv = fulfillment_inventory(revision, ir)
    plan = plan.model_copy(update={"inventory_fingerprint": inv["inventory_fingerprint"]})
    result = validate_projection_candidate(plan, revision, ir, inv, semantic_review=review(inv, plan), source_contract="v3")
    assert result and all(b.state != "UNRESOLVED" for b in result)
    assert next(c.requested_effects for c in ir.clauses if c.polarity == "NEGATED") == expression
    changed = plan.model_copy(update={"routes": tuple(r.model_copy(update={"capability": "HUMAN_DELIVERY_DEPLOY"})
        if r.capability == "DENY_DEPLOY" else r for r in plan.routes)})
    with pytest.raises(ValueError, match="PROHIBITION_CANNOT_BE_FUTURE_PERMISSION|POLARITY_CONFLICT"):
        validate_projection_candidate(changed, revision, ir, inv, semantic_review=review(inv, changed), source_contract="v3")


def test_known_typed_prohibition_still_requires_exact_gate_under_v3():
    from tests.test_c3_semantic_contract_calibration import review
    from spg.application.governed_obligations import fulfillment_inventory, validate_projection_candidate
    revision, ir, _, plan = shared_item_case()
    ir.clauses = tuple(c.model_copy(update={"requested_effects": ("PROHIBIT_DEPLOY",)}) if c.polarity == "NEGATED" else c for c in ir.clauses)
    inv = fulfillment_inventory(revision, ir)
    plan = plan.model_copy(update={"inventory_fingerprint": inv["inventory_fingerprint"], "routes": tuple(
        r.model_copy(update={"capability": "DENY_PREVIEW"}) if r.capability == "DENY_DEPLOY" else r for r in plan.routes)})
    with pytest.raises(ValueError, match="TYPED_EFFECT_LOST"):
        validate_projection_candidate(plan, revision, ir, inv, semantic_review=review(inv, plan), source_contract="v3")


@pytest.mark.parametrize("failure", [None, "missing-review", "negative-review", "wrong-capabilities", "wrong-revision", "marker-only", "wrong-diff"])
def test_v3_actual_scope_consumer_requires_full_reviewed_exact_projection(failure):
    from tests.test_c3_fulfillment_components import current_lifecycle_candidate
    from spg.domain.engineering_semantics import SemanticRelation
    from spg.application.governed_obligations import fulfillment_inventory
    from spg.providers.managed_context_fulfillment import _exact_fact_git_scope
    revision, ir, _, plan = current_lifecycle_candidate()
    fact = revision.engineering_semantic_facts[0].model_copy(update={"relation": SemanticRelation.SCOPE,
        "value": ("index.html",), "scope": "permitted changed artifacts", "qualifiers": {"only_artifact": True}})
    revision.engineering_semantic_facts = (fact,)
    inv = fulfillment_inventory(revision, ir)
    plan = plan.model_copy(update={"inventory_fingerprint": inv["inventory_fingerprint"],
        "routes": (plan.routes[0].model_copy(update={"capability": "GIT_DIFF_SCOPE"}), *plan.routes[1:])})
    bindings = _controlled_v3_binding_receipt(revision, ir, inv, plan)
    receipt = deepcopy(bindings[0].formation_receipt)
    if failure == "missing-review": receipt.pop("semantic_review")
    if failure == "negative-review": receipt["semantic_review"]["component_results"][0]["complete_and_equivalent"] = False
    if failure == "wrong-capabilities": receipt["capabilities_fingerprint"] = "0" * 64
    if failure == "marker-only": receipt = {"source_role_contract": "v3"}
    bindings = (bindings[0].model_copy(update={"formation_receipt": receipt}), *bindings[1:])
    observed_revision = deepcopy(revision)
    if failure == "wrong-revision": observed_revision.revision_fingerprint = "0" * 64
    result = _exact_fact_git_scope(fact, bindings[0], ("index.html",),
        ("unauthorized.html",) if failure == "wrong-diff" else ("index.html",),
        revision=observed_revision, ir=ir, bindings=bindings)
    assert result is (failure is None)


@pytest.mark.parametrize("failure", [None, "missing-review", "marker-only", "missing-native-gate"])
def test_v3_seal_reaches_both_actual_consumers_without_human_acceptance(failure):
    from types import SimpleNamespace
    from tests.test_c3_fulfillment_components import current_lifecycle_candidate
    from spg.application.governed_obligations import fulfillment_inventory
    from spg.providers.managed_context_fulfillment import _candidate_seal_gate_required, verify_binding_inventory
    from spg.domain.governed_obligation import fulfillment_source_ref
    revision, ir, _, plan = current_lifecycle_candidate()
    ir.current_production = tuple(g.model_copy(update={"acceptance_required": False}) for g in ir.current_production)
    inv = fulfillment_inventory(revision, ir)
    plan = plan.model_copy(update={"inventory_fingerprint": inv["inventory_fingerprint"]})
    bindings = _controlled_v3_binding_receipt(revision, ir, inv, plan)
    if failure in {"missing-review", "marker-only"}:
        receipt = deepcopy(bindings[0].formation_receipt)
        if failure == "missing-review": receipt.pop("semantic_review")
        else: receipt = {"source_role_contract": "v3"}
        bindings = (bindings[0].model_copy(update={"formation_receipt": receipt}), *bindings[1:])
    seals = [b for b in bindings if b.evidence_method == "EXACT_SEALED_CANDIDATE"]
    native = SimpleNamespace(binding=SimpleNamespace(obligation_references=tuple(fulfillment_source_ref(b) for b in bindings)))
    if failure == "missing-native-gate": native = None
    rows, _ = verify_binding_inventory(request=SimpleNamespace(proposed_commit_identity="a" * 40, tree_identity="b" * 40),
        task=None, contract=None, repository=None, baseline=None, revision=revision, ir=ir, bindings=bindings,
        semantic_checks=(), protected_checks=(), static_verifier=None, receipt_recorder=None, native_record=native)
    for seal in seals:
        assert _candidate_seal_gate_required(seal, revision, ir, bindings) is (failure not in {"missing-review", "marker-only"})
    seal_rows = [r for r in rows if r["evidence_method"] == "EXACT_SEALED_CANDIDATE"]
    assert seal_rows and all(r["disposition"] == ("PENDING_CANDIDATE_GATE" if failure is None else "UNVERIFIABLE") for r in seal_rows)


@pytest.mark.parametrize("capability", ["CANDIDATE_SEAL", "DENY_DEPLOY"])
def test_v3_marker_never_admits_componentless_legacy_route(capability):
    from tests.test_c3_semantic_contract_calibration import review
    from spg.application.governed_obligations import validate_projection_candidate
    revision, ir, inv, plan = shared_item_case()
    changed = plan.model_copy(update={"routes": tuple(r.model_copy(update={"component_basis": None}) for r in plan.routes)})
    with pytest.raises(ValueError, match="COMPONENT_INVENTORY_INCOMPLETE"):
        validate_projection_candidate(changed, revision, ir, inv, semantic_review=review(inv, plan), source_contract="v3")


@pytest.mark.parametrize("tamper", ["wire", "inventory", "attempt", "review-output", "review-row", "receipt-removal", "owner-policy", "review-pending-capabilities", "review-observed-capabilities", "review-validated-capabilities"])
def test_v3_final_consumer_revalidates_actual_formation_and_review_lineage(tamper):
    from tests.test_c3_fulfillment_components import current_lifecycle_candidate
    from spg.application.governed_obligations import fulfillment_inventory, validate_fulfillment_projection
    revision, ir, _, plan = current_lifecycle_candidate()
    ir.current_production = tuple(g.model_copy(update={"acceptance_required": False}) for g in ir.current_production)
    inv = fulfillment_inventory(revision, ir)
    plan = plan.model_copy(update={"inventory_fingerprint": inv["inventory_fingerprint"]})
    bindings = _controlled_v3_binding_receipt(revision, ir, inv, plan)
    validate_fulfillment_projection(bindings, revision, ir, exact_target_paths=inv["exact_target_paths"])
    receipt = deepcopy(bindings[0].formation_receipt)
    rows = receipt["candidate_attempts"]
    if tamper == "wire": next(r for r in rows if r["stage"] == "MODEL_RESPONSE_OBSERVED")["candidate_output"] += " "
    if tamper == "inventory": rows[0]["inventory_fingerprint"] = "0" * 64
    if tamper == "attempt": next(r for r in rows if r["stage"] == "SEMANTIC_REVIEW_PENDING")["attempt"] = 2
    if tamper == "review-output": next(r for r in rows if r["stage"] == "SEMANTIC_REVIEW_OBSERVED")["review_output"] += " "
    if tamper == "review-row": next(r for r in rows if r["stage"] == "SEMANTIC_REVIEW_VALIDATED")["semantic_review"]["component_results"][0]["nonredundant"] = False
    if tamper == "receipt-removal": receipt["candidate_attempts"] = []
    if tamper == "owner-policy": next(r for r in rows if r["stage"] == "MODEL_REQUEST_PENDING")["owner_source_preconditions"]["typed_prerequisite_contract"] = "existing-owner-typed-prerequisites-v8"
    if tamper.startswith("review-") and tamper.endswith("-capabilities"):
        stage = {"review-pending-capabilities": "SEMANTIC_REVIEW_PENDING", "review-observed-capabilities": "SEMANTIC_REVIEW_OBSERVED", "review-validated-capabilities": "SEMANTIC_REVIEW_VALIDATED"}[tamper]
        next(r for r in rows if r["stage"] == stage)["capabilities_fingerprint"] = "0" * 64
    altered = (bindings[0].model_copy(update={"formation_receipt": receipt}), *bindings[1:])
    with pytest.raises(ValueError, match="IDENTITY_DRIFT|SEMANTIC_COMPONENT_MISMATCH"):
        validate_fulfillment_projection(altered, revision, ir, exact_target_paths=inv["exact_target_paths"])


@pytest.mark.parametrize("failure", [None, "missing-revision", "missing-review", "current-fail", "mixed-delivery", "mixed-integration"])
def test_v3_mixed_fact_handoff_uses_actual_seal_not_future_acceptance(failure):
    from tests.test_c3_fulfillment_components import current_lifecycle_candidate
    from spg.domain.engineering_semantics import SemanticRelation, semantic_fact_reference
    from spg.application.governed_obligations import fulfillment_inventory, evaluate_candidate_handoffs
    revision, ir, _, plan = current_lifecycle_candidate()
    ir.current_production = tuple(g.model_copy(update={"acceptance_required": False}) for g in ir.current_production)
    fact = revision.engineering_semantic_facts[0].model_copy(update={"relation": SemanticRelation.ACCEPTANCE_ASSERTION})
    revision.engineering_semantic_facts = (fact,)
    inv = fulfillment_inventory(revision, ir)
    content = plan.routes[0]
    seal = content.model_copy(update={"capability": "CANDIDATE_SEAL", "target_paths": ()})
    plan = plan.model_copy(update={"inventory_fingerprint": inv["inventory_fingerprint"], "routes": (content, seal, *plan.routes[1:])})
    bindings = _controlled_v3_binding_receipt(revision, ir, inv, plan)
    if failure == "missing-review":
        receipt = deepcopy(bindings[0].formation_receipt);receipt.pop("semantic_review")
        bindings = (bindings[0].model_copy(update={"formation_receipt": receipt}), *bindings[1:])
    if failure in {"mixed-delivery", "mixed-integration"}:
        from spg.domain.governed_obligation import FulfillmentPhase, FulfillmentOwner
        original = next(b for b in bindings if b.fact_id == fact.id and b.phase is FulfillmentPhase.CANDIDATE_SEAL)
        extra = original.model_copy(update={"phase": FulfillmentPhase.DELIVERY if failure == "mixed-delivery" else FulfillmentPhase.HUMAN_INTEGRATION,
            "owner": FulfillmentOwner.DELIVERY_GATE if failure == "mixed-delivery" else FulfillmentOwner.HUMAN_GATE,
            "component": "deploy" if failure == "mixed-delivery" else "human-integration",
            "evidence_method": "EXACT_HUMAN_AUTHORIZATION", "gate_ref": "cloud-delivery:human-authorization-required" if failure == "mixed-delivery" else "candidate-governance:human-integration"})
        bindings = (*bindings, extra)
    check = {"fact_id": str(fact.id), "passed": failure != "current-fail", "disposition": "VERIFIED_CURRENT"}
    result = evaluate_candidate_handoffs((check,), references=(semantic_fact_reference(fact, work_revision_id=revision.id),),
        admitted_facts={str(fact.id): fact}, ir=ir, revision=None if failure == "missing-revision" else revision,
        source_revision=inv["source_revision"], exact_target_paths=inv["exact_target_paths"], fulfillment_bindings=bindings)
    assert (result[0]["disposition"] == "CURRENT_VERIFIED_FUTURE_GATE_PENDING") is (failure is None)
    assert result[0]["passed"] is (failure != "current-fail")



def test_v9_scope_does_not_inherit_negative_sibling_from_shared_human_record():
    from spg.application.governed_obligations import fulfillment_inventory, _fact_prohibition_sources, _projection_binding
    from spg.domain.engineering_semantics import SemanticRelation
    from spg.domain.governed_obligation import FulfillmentRouteCandidate
    from types import SimpleNamespace
    revision, ir, _, _ = shared_item_case()
    negative = next(c for c in ir.clauses if c.polarity == "NEGATED")
    fact = revision.engineering_semantic_facts[0].model_copy(update={"relation": SemanticRelation.SCOPE,
        "value": ("index.html",), "scope": "permitted changed artifacts", "qualifiers": {"only_artifact": True},
        "provenance": revision.engineering_semantic_facts[0].provenance.model_copy(update={
            "source_record_ids": (negative.source_record_id,), "source_text": "Only index.html may change."})})
    revision.engineering_semantic_facts = (fact, *revision.engineering_semantic_facts[1:])
    inv = fulfillment_inventory(revision, ir)
    caps = fulfillment_capability_contracts();pred = _owner_source_preconditions(revision, ir, inv, caps)
    source = next(s for s in inv["sources"] if s.get("fact_id") == str(fact.id))
    clause_source = next(s for s in inv["sources"] if s.get("clause_id") == negative.clause_id)
    cap = next(i for i,c in enumerate(caps) if c["capability"] == "GIT_DIFF_SCOPE")
    assert not any(row["capability"] == cap for row in pred['sources'][0]["ineligible_binding_prerequisites"])
    assert [] in next(row["minimal_support_sets"] for row in pred['sources'][0]["necessary_source_proofs"] if row["capability"] == cap)
    assert not _fact_prohibition_sources(revision, ir, inv, fact,
        SimpleNamespace(capability="DENY_DEPLOY", supporting_source_refs=(clause_source["source_ref"],)), source_contract="v3")
    route = FulfillmentRouteCandidate(source_ref=source["source_ref"], capability="GIT_DIFF_SCOPE", target_paths=("index.html",),
        component_basis={"source_span_start":0, "source_span_end":len(fact.provenance.source_text), "source_component_quote":fact.provenance.source_text},
        rationale="Controlled positive Scope preserves original contribution.")
    assert _projection_binding(revision, ir, inv, route, allow_calibrated=True, source_contract="v3").evidence_method == "EXACT_GIT_DIFF_SCOPE"
    assert fact.qualifiers == {"only_artifact": True}
