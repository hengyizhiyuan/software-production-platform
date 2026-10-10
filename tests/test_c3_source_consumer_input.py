"""Lossless existing request join; controlled plans are not model qualification."""
from copy import deepcopy
import json

import pytest

from spg.application.governed_obligations import (
    _owner_source_preconditions, fulfillment_capability_contracts,
    form_fulfillment_projection, validate_projection_candidate,
)
from spg.providers.fulfillment_candidate import (
    _SOURCE_CONSUMER_INPUT_CONTRACT, _SOURCE_CONSUMER_INSTRUCTIONS,
    _source_consumer_input, _formation_inventory_view,
    _restore_formation_inventory_view, _fulfillment_wire_context,
    _decode_fulfillment_candidate_wire, _FulfillmentWireReceiptIdentityError,
)
from tests.test_c3_fulfillment_capacity_representation import (
    controlled_capacity_case, controlled_wire, controlled_model_provider,
)
from tests.test_c3_source_role_contract import shared_item_case
from tests.test_c3_semantic_contract_calibration import review


@pytest.mark.parametrize("scale", ["small", "medium", "complex"])
def test_join_retains_exact_inventory_and_each_owner_predicate_once(scale):
    revision, ir, inventory, _ = controlled_capacity_case(scale)
    caps = fulfillment_capability_contracts()
    owner = _owner_source_preconditions(revision, ir, inventory, caps,
        generation_view_contract=_SOURCE_CONSUMER_INPUT_CONTRACT)
    context = _fulfillment_wire_context(inventory, caps, owner_preconditions=owner)
    original = deepcopy((inventory, owner))
    payload = _source_consumer_input(inventory, caps, context, owner)
    assert _restore_formation_inventory_view(payload["immutable_inventory"],
        payload["existing_ir_item_table"]) == inventory
    rows = payload["temporary_wire"]["source_index_table"]
    assert [r["index"] for r in rows] == list(range(len(inventory["sources"])))
    assert {**payload["owner_source_preconditions"],
        "sources": [payload["owner_source_preconditions"]["sources"][r["owner_prerequisites_ref"]] for r in rows]} == owner
    assert payload["existing_capability_contracts"] == caps
    assert (inventory, owner) == original
    assert payload["owner_source_preconditions"] == owner
    # Actual metadata sharing, not shortening/removing any original requirement.
    redundant = deepcopy(payload)
    for r in redundant["temporary_wire"]["source_index_table"]:
        r["owner_prerequisites"] = owner["sources"][r["owner_prerequisites_ref"]]
    assert len(json.dumps(payload)) < len(json.dumps(redundant))
    assert all("owner_prerequisites" not in row for row in rows)


@pytest.mark.parametrize("change", ["inventory", "capabilities", "source-identity", "request-view"])
def test_input_join_rejects_owner_identity_drift_without_repair(change):
    revision, ir, inventory, _ = controlled_capacity_case()
    caps = fulfillment_capability_contracts()
    owner = _owner_source_preconditions(revision, ir, inventory, caps,
        generation_view_contract=_SOURCE_CONSUMER_INPUT_CONTRACT)
    if change == "inventory": owner["inventory_fingerprint"] = "0" * 64
    elif change == "capabilities": owner["capabilities_fingerprint"] = "0" * 64
    elif change == "source-identity": owner["sources"][0]["source_ref"] = "forged"
    else: owner["generation_view_contract"] = "forged"
    before = deepcopy(owner)
    context = _fulfillment_wire_context(inventory, caps, owner_preconditions=owner)
    with pytest.raises(_FulfillmentWireReceiptIdentityError):
        _source_consumer_input(inventory, caps, context, owner)
    assert owner == before


def test_join_does_not_replace_conditional_background_with_a_verdict():
    revision, ir, inventory, plan = shared_item_case()
    caps = fulfillment_capability_contracts()
    owner = _owner_source_preconditions(revision, ir, inventory, caps,
        generation_view_contract=_SOURCE_CONSUMER_INPUT_CONTRACT)
    payload = _source_consumer_input(inventory, caps,
        _fulfillment_wire_context(inventory, caps, owner_preconditions=owner), owner)
    row = next(r for r in payload["temporary_wire"]["source_index_table"]
        if inventory["sources"][r["index"]].get("clause_id") == "description")
    original = payload["owner_source_preconditions"]["sources"][row["owner_prerequisites_ref"]]
    assert original["whole_source_context_only"] is False
    assert original["reviewed_background_prerequisites"]["conditional_source_eligible"] is True
    assert original["reviewed_background_prerequisites"]["independent_full_plan_and_component_review_required"] is True
    validate_projection_candidate(plan, revision, ir, inventory, allow_review_pending=True,
        source_contract="v3", owner_preconditions=owner)
    with pytest.raises(ValueError, match="COMPONENT_REVIEW_REQUIRED"):
        validate_projection_candidate(plan, revision, ir, inventory,
            source_contract="v3", owner_preconditions=owner)
    missing = plan.model_copy(update={"routes": tuple(r for r in plan.routes
        if not r.source_ref.startswith("semantic-fact:"))})
    with pytest.raises(ValueError):
        validate_projection_candidate(missing, revision, ir, inventory, allow_review_pending=True,
            source_contract="v3", owner_preconditions=owner)


def test_existing_whole_negative_basis_has_complementary_gates_not_background():
    revision, ir, inventory, plan = controlled_capacity_case()
    caps = fulfillment_capability_contracts()
    owner = _owner_source_preconditions(revision, ir, inventory, caps,
        generation_view_contract=_SOURCE_CONSUMER_INPUT_CONTRACT)
    wire, context = controlled_wire(inventory, plan, owner_preconditions=owner)
    decoded = _decode_fulfillment_candidate_wire(json.dumps(wire), inventory, caps,
        wire_metadata=context, owner_preconditions=owner)
    assert decoded == plan
    validate_projection_candidate(plan, revision, ir, inventory, allow_review_pending=True,
        source_contract="v3", owner_preconditions=owner)
    negative = next(s for s in inventory["sources"] if s.get("clause_id") == "original-clause")
    routes = [r for r in plan.routes if r.source_ref == negative["source_ref"]]
    assert {r.capability for r in routes} == {"DENY_DEPLOY", "DENY_PUBLISH"}
    assert len({r.component_basis.source_component_quote for r in routes}) == 1
    bad = plan.model_copy(update={"routes": tuple(r.model_copy(update={"capability":"RETAIN_CONTEXT"})
        if r == routes[0] else r for r in plan.routes)})
    with pytest.raises(ValueError):
        validate_projection_candidate(bad, revision, ir, inventory, allow_review_pending=True,
            source_contract="v3", owner_preconditions=owner)


def test_new_view_is_receipt_bound_and_replay_does_not_generate_again():
    revision, ir, inventory, plan = controlled_capacity_case()
    provider, calls = controlled_model_provider(inventory, plan)
    kwargs = {"provider":provider, "exact_target_paths":inventory["exact_target_paths"]}
    result = form_fulfillment_projection(revision, ir, **kwargs)
    assert all(b.state != "UNRESOLVED" for b in result)
    assert len(calls) == 2
    rows = provider._fulfillment_receipts
    start = next(r for r in rows if r["stage"] == "MODEL_REQUEST_PENDING")
    assert start["owner_source_preconditions"]["generation_view_contract"] == _SOURCE_CONSUMER_INPUT_CONTRACT
    payload = calls[0]
    assert payload["owner_rows_location"] == "owner_source_preconditions.sources[owner_prerequisites_ref]"
    original = deepcopy(rows)
    form_fulfillment_projection(revision, ir, **kwargs)
    assert len(calls) == 2 and rows == original
    start["owner_source_preconditions"]["generation_view_contract"] = "forged"
    stopped = form_fulfillment_projection(revision, ir, **kwargs)
    assert stopped[0].formation_receipt["terminal_reason"] == "OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT"
    assert len(calls) == 2


@pytest.mark.parametrize("legacy", [False, True, "v1", "v2"])
def test_interrupted_feedback_retains_initial_request_view_and_original_receipts(monkeypatch, legacy):
    import spg.application.governed_obligations as app
    revision, ir, inventory, plan = controlled_capacity_case()
    attempts = 0
    def one_bad_wire(wire):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            wire["routes"].pop(0)
    provider, calls = controlled_model_provider(inventory, plan, wire_change=one_bad_wire)
    source_preconditions = app._owner_source_preconditions
    if legacy:
        def frozen_view(*args, **kwargs):
            kwargs["generation_view_contract"] = "existing-lossless-source-consumer-input-" + legacy if legacy in ("v1", "v2") else None
            kwargs["semantic_selection_input_contract"] = None
            return source_preconditions(*args, **kwargs)
        monkeypatch.setattr(app, "_owner_source_preconditions", frozen_view)
    append = app.FulfillmentFormationReceipts.append
    def interrupted(self, stage, attempt, **values):
        append(self, stage, attempt, **values)
        if stage == "CANDIDATE_VALIDATED" and attempt == 1:
            raise KeyboardInterrupt("Controlled checkpoint; no external request")
    monkeypatch.setattr(app.FulfillmentFormationReceipts, "append", interrupted)
    kwargs = {"provider":provider, "exact_target_paths":inventory["exact_target_paths"]}
    with pytest.raises(KeyboardInterrupt):
        app.form_fulfillment_projection(revision, ir, **kwargs)
    rows = provider._fulfillment_receipts
    original = deepcopy(rows)
    assert len(calls) == 1
    monkeypatch.setattr(app, "_owner_source_preconditions", source_preconditions)
    monkeypatch.setattr(app.FulfillmentFormationReceipts, "append", append)
    result = app.form_fulfillment_projection(revision, ir, **kwargs)
    assert all(b.state != "UNRESOLVED" for b in result) and len(calls) == 3
    assert rows[:len(original)] == original
    starts = [r for r in rows if r["stage"] == "MODEL_REQUEST_PENDING"]
    assert len(starts) == 2
    for entry in starts:
        assert entry["owner_source_preconditions"].get("generation_view_contract") == (
            "existing-lossless-source-consumer-input-" + legacy if legacy in ("v1", "v2") else None if legacy else _SOURCE_CONSUMER_INPUT_CONTRACT)
    assert ("owner_rows_location" in calls[1]) is (not legacy or legacy in ("v1", "v2"))
    assert calls[1]["owner_source_preconditions"] == calls[0]["owner_source_preconditions"]
    assert starts[1]["feedback_receipt_id"] == next(r["receipt_id"] for r in original
        if r["stage"] == "CANDIDATE_VALIDATED")
    before = deepcopy(rows)
    app.form_fulfillment_projection(revision, ir, **kwargs)
    assert rows == before and len(calls) == 3


def test_invalid_request_view_stops_before_inference_and_replays_without_calls(monkeypatch):
    import spg.application.governed_obligations as app
    revision, ir, inventory, plan = controlled_capacity_case()
    provider, calls = controlled_model_provider(inventory, plan)
    preconditions = app._owner_source_preconditions
    def invalid_view(*args, **kwargs):
        kwargs["generation_view_contract"] = "existing-lossless-source-consumer-input-v1"
        return preconditions(*args, **kwargs)
    monkeypatch.setattr(app, "_owner_source_preconditions", invalid_view)
    kwargs = {"provider": provider, "exact_target_paths": inventory["exact_target_paths"]}
    result = app.form_fulfillment_projection(revision, ir, **kwargs)
    assert all(binding.state == "UNRESOLVED" for binding in result)
    assert result[0].formation_receipt["terminal_reason"] == "OBLIGATION_FORMATION_REQUEST_VIEW_CONTRACT_INVALID"
    assert calls == []
    rows = provider._fulfillment_receipts
    assert len(rows) == 1 and rows[0]["stage"] == "FORMATION_STOPPED"
    assert rows[0]["failure_stage"] == "MODEL_REQUEST"
    original = deepcopy(rows)
    monkeypatch.setattr(app, "_owner_source_preconditions", preconditions)
    replay = app.form_fulfillment_projection(revision, ir, **kwargs)
    assert replay[0].formation_receipt["terminal_reason"] == "OBLIGATION_FORMATION_REQUEST_VIEW_CONTRACT_INVALID"
    assert rows == original and calls == []
