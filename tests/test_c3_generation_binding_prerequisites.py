"""An independent JSON Schema validator checks existing Owner request limits.

Generation eligibility is not fulfillment, semantic Review or authority.
"""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from spg.application import governed_obligations as a
from spg.providers import fulfillment_candidate as p
from spg.domain.governed_obligation import fulfillment_source_semantic_text
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case


def generation_case(scale="medium", enabled=True):
    revision, ir, inventory, plan = controlled_capacity_case(scale)
    caps = a.fulfillment_capability_contracts()
    owner = a._owner_source_preconditions(revision, ir, inventory, caps,
        generation_view_contract=p._SOURCE_CONSUMER_INPUT_CONTRACT,
        semantic_selection_input_contract=p._PRIMARY_MEANING_INPUT_CONTRACT,
        **({"generation_prerequisite_contract": "existing-owner-binding-generation-v1"} if enabled else {}))
    schema = p._formation_output_schema(inventory, caps, owner_preconditions=owner)
    Draft202012Validator.check_schema(schema)
    route_schema = {"$defs": schema["$defs"], **schema["properties"]["routes"]["items"]}
    return revision, ir, inventory, plan, caps, owner, Draft202012Validator(route_schema)


@pytest.mark.parametrize("scale", ("small", "medium", "complex"))
def test_generation_rejects_actual_owner_exclusions_without_selecting_a_route(scale):
    revision, ir, inventory, plan, caps, owner, validator = generation_case(scale)
    before = deepcopy((inventory, owner, plan.model_dump(mode="json")))
    for index, source in enumerate(inventory["sources"]):
        text = fulfillment_source_semantic_text(source)
        for failure in owner["sources"][index]["ineligible_binding_prerequisites"]:
            cap = failure["capability"]
            assert not validator.is_valid({"s": index, "c": cap, "a": 0, "z": len(text),
                "q": None, "f": [], "t": [], "u": [], "r": "Controlled unadmitted request."})
    # Both unresolved and multiple distinct legal consumers remain available.
    unresolved = next(i for i,c in enumerate(caps) if c["capability"] == "UNRESOLVED")
    for index, source in enumerate(inventory["sources"]):
        assert validator.is_valid({"s": index, "c": unresolved, "a": 0,
            "z": len(fulfillment_source_semantic_text(source)), "q": None,
            "f": [], "t": [], "u": [], "r": "No mapping proven; no permission granted."})
    assert (inventory, owner, plan.model_dump(mode="json")) == before


@pytest.mark.parametrize("basis", ("null-whole", "string-whole", "partial"))
def test_required_whole_source_cannot_be_generated_as_background_but_partial_remains_open(basis):
    _, _, inventory, _, caps, owner, validator = generation_case()
    choices = p._formation_binding_choices(inventory, caps, owner)
    index = next(i for i, row in enumerate(choices)
        if p._whole_source_retention_prerequisite(row) is False
        and inventory["sources"][i]["kind"] in {"IR_CLAUSE", "IR_CONSTRAINT"})
    text = fulfillment_source_semantic_text(inventory["sources"][index])
    retained = next(i for i,c in enumerate(caps) if c["capability"] == "RETAIN_CONTEXT")
    route = {"s":index, "c":retained, "a":0, "z":len(text),
        "q":None if basis == "null-whole" else text if basis == "string-whole" else text[:-1],
        "f":[], "t":[], "u":[], "r":"Unadmitted disposition; semantic Review still required."}
    assert validator.is_valid(route) == (basis == "partial")


def test_conditional_background_is_not_forbidden_and_unknown_is_not_guessed():
    from tests.test_c3_source_role_contract import shared_item_case
    revision, ir, inventory, plan = shared_item_case()
    caps = a.fulfillment_capability_contracts()
    owner = a._owner_source_preconditions(revision,ir,inventory,caps,
        generation_view_contract=p._SOURCE_CONSUMER_INPUT_CONTRACT,
        semantic_selection_input_contract=p._PRIMARY_MEANING_INPUT_CONTRACT,
        generation_prerequisite_contract="existing-owner-binding-generation-v1")
    choices = p._formation_binding_choices(inventory, caps, owner)
    choice = next(row for row in choices if inventory["sources"][row["source"]].get("clause_id") == "description")
    assert choice["whole_source_context_only"] is False
    assert choice["reviewed_background_prerequisites"]["conditional_source_eligible"] is True
    schema = p._qualified_operand_generation_schema(inventory, caps, choices, enforce_owner_prerequisites=True)
    full = p._fulfillment_wire_schema()
    validator = Draft202012Validator({"$defs":full["$defs"], **schema})
    route = {"s":choice["source"], "c":next(i for i,c in enumerate(caps) if c["capability"] == "RETAIN_CONTEXT"),
        "a":0, "z":len(fulfillment_source_semantic_text(inventory["sources"][choice["source"]])),
        "q":None, "f":[], "t":[], "u":[], "r":"Conditional eligibility is not semantic approval."}
    assert validator.is_valid(route)
    a.validate_projection_candidate(plan,revision,ir,inventory,allow_review_pending=True,
        source_contract="v3",owner_preconditions=owner)
    missing = plan.model_copy(update={"routes":tuple(r.model_copy(update={"capability":"UNRESOLVED","target_paths":()})
        if r.source_ref.startswith("semantic-fact:") else r for r in plan.routes)})
    with pytest.raises(ValueError,match="CURRENT_CLAUSE_CANNOT_BE_CONTEXT_ONLY"):
        a.validate_projection_candidate(missing,revision,ir,inventory,allow_review_pending=True,
            source_contract="v3",owner_preconditions=owner)
    assert p._whole_source_retention_prerequisite({}) is None
    assert p._whole_source_retention_prerequisite({"whole_source_context_only":False}) is None
    assert p._whole_source_retention_prerequisite({"whole_source_context_only":True}) is True


def test_legacy_schema_is_unchanged_and_new_marker_is_identity_bound():
    revision, ir, inventory, _, caps, owner, _ = generation_case(enabled=False)
    choices = p._formation_binding_choices(inventory,caps,owner)
    schema = p._formation_output_schema(inventory,caps,owner_preconditions=owner)
    assert schema["properties"]["routes"]["items"] == p._qualified_operand_generation_schema(inventory,caps,choices)
    current = a._owner_source_preconditions(revision,ir,inventory,caps,
        generation_view_contract=p._SOURCE_CONSUMER_INPUT_CONTRACT,
        semantic_selection_input_contract=p._PRIMARY_MEANING_INPUT_CONTRACT,
        generation_prerequisite_contract="existing-owner-binding-generation-v1")
    before = p._fulfillment_wire_context(inventory,caps,owner_preconditions=owner)
    after = p._fulfillment_wire_context(inventory,caps,owner_preconditions=current)
    assert before["wire_request_fingerprint"] != after["wire_request_fingerprint"]
    for marker in ("invented", "existing-owner-binding-generation-v1"):
        with pytest.raises(ValueError,match="REQUEST_VIEW_CONTRACT_INVALID"):
            a._owner_source_preconditions(revision,ir,inventory,caps,generation_prerequisite_contract=marker)


@pytest.mark.parametrize("tamper", (None, "generation_prerequisite_contract", "semantic_selection_input_contract", "typed_prerequisite_contract"))
def test_new_marker_replay_cannot_change_original_request_identity_or_reopen_budget(tamper):
    from tests.test_c3_fulfillment_capacity_representation import controlled_model_provider
    revision,ir,inventory,plan = controlled_capacity_case()
    provider,calls = controlled_model_provider(inventory,plan)
    def run():return a.form_fulfillment_projection(revision,ir,provider=provider,
        source_revision=inventory["source_revision"],exact_target_paths=inventory["exact_target_paths"])
    assert all(b.state != "UNRESOLVED" for b in run()) and len(calls)==2
    original = deepcopy(provider._fulfillment_receipts)
    pending = next(r for r in original if r["stage"]=="MODEL_REQUEST_PENDING")
    assert pending["owner_source_preconditions"]["generation_prerequisite_contract"]=="existing-owner-binding-generation-v1"
    if tamper:
        for row in provider._fulfillment_receipts:
            if row["stage"] in {"MODEL_REQUEST_PENDING","MODEL_RESPONSE_OBSERVED"}:
                row["owner_source_preconditions"].pop(tamper)
        result=run()
        assert result[0].formation_receipt["terminal_reason"].endswith("IDENTITY_DRIFT")
    else:
        assert all(b.state != "UNRESOLVED" for b in run())
        assert provider._fulfillment_receipts==original
    assert len(calls)==2
