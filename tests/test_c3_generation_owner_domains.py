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
    observed = {}
    for branch in branches:
        assert branch["additionalProperties"] is False
        assert branch["required"] == original["$defs"]["_FulfillmentCompactRoute"]["required"]
        for source in branch["properties"]["s"]["enum"]:
            assert source not in observed
            observed[source] = branch["properties"]["c"]["enum"]
    assert set(observed) == set(range(len(inventory["sources"])))
    for row in preconditions["sources"]:
        rejected = {r["capability"] for r in row["ineligible_binding_prerequisites"]}
        assert observed[row["source"]] == [i for i in range(len(capabilities)) if i not in rejected]
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
