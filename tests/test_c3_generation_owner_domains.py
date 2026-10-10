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
