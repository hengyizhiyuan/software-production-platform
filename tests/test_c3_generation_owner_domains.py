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
        props = branch["properties"]
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
