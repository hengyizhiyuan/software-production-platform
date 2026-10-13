"""Non-holdout candidate editing and invariant protection at the existing Owner."""
from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from spg.application import governed_obligations as app
from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
from tests.test_c3_fulfillment_capacity_representation import (
    controlled_capacity_case, controlled_wire, decode_review_input,
)
from tests.test_c3_semantic_contract_calibration import review
from tests.test_c3_source_consumption_proof import fixture_review_proof


def local_edit_case(scale="small", outcome="repair", first="source-proof"):
    rev, ir, inventory, plan = controlled_capacity_case(scale)
    snapshots = deepcopy((rev, ir, inventory, plan))
    calls = []
    old_wire = None
    touched = None
    review_calls = 0

    def generate(**request):
        nonlocal old_wire, touched, review_calls
        payload = json.loads(request["input_text"])
        calls.append((request, payload))
        if "untrusted_fulfillment_candidate" in payload:
            review_calls += 1
            if first == "critic-format" and review_calls == 1:
                return result("{")
            candidate = decode_review_input(payload)
            output = fixture_review_proof(inventory, candidate, review(inventory, candidate), payload).model_dump_json()
        else:
            owner = payload["owner_source_preconditions"]
            state = owner["candidate_construction_state"]
            assert state["understanding"]["authority"] == "DERIVED_CANDIDATE_ONLY"
            assert state["understanding"]["confidence"] is None
            assert state["evidence"]["evidence_refs"] == []
            assert "ACTUAL_OWNER_EVIDENCE" in state["understanding"]["unknowns"]
            wire, _ = controlled_wire(inventory, plan,
                feedback=payload["same_basis_validation_feedback"], owner_preconditions=owner)
            if payload["same_basis_validation_feedback"] is None:
                assert state["convergence"]["action"] == "CONTINUE"
                future = next(i for i,s in enumerate(inventory["sources"])
                    if s["kind"] == "WORK_CONSTRAINT" and s["index"] == 1)
                touched = next(i for i,r in enumerate(wire["routes"]) if r["s"] == future)
                if first == "source-proof":
                    wire["routes"][touched]["u"] = []
                elif first == "format":
                    wire["routes"][touched]["c"] = "not-an-ordinal"
                elif first == "unsafe":
                    return result(json.dumps(wire) + " trailing")
                elif first == "conflict":
                    duplicate = deepcopy(wire["routes"][touched])
                    duplicate.update(c=next(i for i,c in enumerate(payload["existing_capability_contracts"])
                        if c["capability"] == "UNRESOLVED"), f=[], u=[], t=[])
                    wire["routes"].append(duplicate)
                old_wire = deepcopy(wire)
                output = json.dumps(wire, ensure_ascii=False)
            else:
                assert state["convergence"]["action"] == "REPAIR"
                basis = state["repair_basis"]
                assert basis["original_wire"] == old_wire
                replacement = deepcopy(wire["routes"][touched])
                edit = {"v":1,"h":wire["h"],"d":wire["d"],"basis":basis["raw_sha256"],
                    "replace":[{"index":touched,"route":replacement}],"remove":[],"append":[]}
                if outcome == "repeat":
                    edit["replace"][0]["route"] = deepcopy(old_wire["routes"][touched])
                elif outcome == "basis":
                    edit["basis"] = "0" * 64
                elif outcome == "duplicate":
                    edit["remove"] = [touched]
                elif outcome == "drop":
                    edit["replace"] = []
                    edit["remove"] = [touched]
                elif outcome == "path":
                    edit["replace"][0]["route"]["t"] = [len(inventory["exact_target_paths"])]
                elif outcome == "wrong-header":
                    edit["h"] = "0" * 64
                output = json.dumps(edit, ensure_ascii=False)
                if first == "critic-format":
                    assert state["convergence"]["repair_strategy"] == "RETAIN_VALID_CANDIDATE_REPAIR_REVIEW_OUTPUT"
                    edit["replace"] = []
                    output = json.dumps(edit)
                elif first == "conflict":
                    edit["replace"] = []
                    edit["remove"] = [len(old_wire["routes"]) - 1]
                    output = json.dumps(edit)
                if outcome == "duplicate-key":
                    output = '{"basis":"' + "0" * 64 + '",' + output[1:]
        return result(output)

    def result(output):
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model="controlled-local-edit", effective_model="controlled-local-edit",
            request_id=f"fixture-{len(calls)}", usage=ModelUsage(unknown=True),
            timing=ModelTiming(), retry_count=0)

    provider = ModelFulfillmentCandidateProvider(
        lambda: SimpleNamespace(generate=generate, close=lambda: None), candidate_construction=True)
    kwargs = dict(provider=provider, exact_target_paths=inventory["exact_target_paths"])
    bindings = app.form_fulfillment_projection(rev, ir, **kwargs)
    assert (rev, ir, inventory, plan) == snapshots
    return bindings, provider, calls, (rev,ir,kwargs), touched, old_wire


@pytest.mark.parametrize("scale", ("small", "medium", "complex"))
@pytest.mark.parametrize("first", ("source-proof", "format"))
def test_local_candidate_repair_preserves_other_routes_and_replays_without_calls(scale, first):
    bindings, provider, calls, args, touched, original = local_edit_case(scale, first=first)
    assert all(b.state != "UNRESOLVED" for b in bindings)
    assert len(calls) == 3  # two Formation proposals, one independent Review
    observed = next(r for r in provider._fulfillment_receipts
        if r["stage"] == "MODEL_RESPONSE_OBSERVED" and r["attempt"] == 2)
    construction = observed["wire_presentation"]["candidate_construction"]
    assert construction["replaced_original_ordinals"] == [touched]
    assert construction["retained_original_ordinals"] == [i for i in range(len(original["routes"])) if i != touched]
    assert observed["candidate_output_sha256"] == sha256(observed["candidate_output"].encode()).hexdigest()
    assert construction["constructed_wire_sha256"] != observed["candidate_output_sha256"]
    receipts = deepcopy(provider._fulfillment_receipts)
    rev,ir,kwargs = args
    replayed = app.form_fulfillment_projection(rev, ir, **kwargs)
    assert [b.model_dump(exclude={"formation_receipt"}) for b in replayed] == [
        b.model_dump(exclude={"formation_receipt"}) for b in bindings]
    # Each invocation reports its own elapsed observation, not a durable fact.
    assert {k:v for k,v in replayed[0].formation_receipt.items() if k != "elapsed_seconds"} == {
        k:v for k,v in bindings[0].formation_receipt.items() if k != "elapsed_seconds"}
    assert len(calls) == 3
    assert provider._fulfillment_receipts == receipts


@pytest.mark.parametrize("outcome", ("repeat", "basis", "duplicate", "drop", "path", "wrong-header", "duplicate-key"))
def test_local_edits_cannot_erase_requirements_repeat_or_grant_authority(outcome):
    bindings, provider, calls, _args, _touched, _original = local_edit_case(outcome=outcome)
    assert all(b.state == "UNRESOLVED" for b in bindings)
    assert len(calls) == 2
    assert not any(r["stage"] == "SEMANTIC_REVIEW_PENDING" for r in provider._fulfillment_receipts)
    assert any(r.get("terminal") for r in provider._fulfillment_receipts)


def test_unsafe_observation_does_not_buy_another_model_request():
    bindings,provider,calls,_args,_touched,_original = local_edit_case(first="unsafe")
    assert all(b.state == "UNRESOLVED" for b in bindings)
    assert len(calls) == 1
    assert bindings[0].formation_receipt["terminal_reason"] == "OBLIGATION_FORMATION_LOCAL_REPAIR_BASIS_UNAVAILABLE"


def test_replayed_construction_state_is_bound_to_original_feedback_and_inventory():
    bindings,provider,calls,args,_touched,_original = local_edit_case()
    starts = [r for r in provider._fulfillment_receipts if r["stage"] == "MODEL_REQUEST_PENDING" and r["attempt"] == 2]
    starts[0]["owner_source_preconditions"]["candidate_construction_state"]["evidence"]["evidence_refs"] = ["fabricated"]
    rev,ir,kwargs = args
    replayed = app.form_fulfillment_projection(rev,ir,**kwargs)
    assert all(b.state == "UNRESOLVED" for b in replayed)
    assert len(calls) == 3


def test_critic_output_repair_does_not_force_changes_to_a_valid_candidate():
    bindings,provider,calls,args,_touched,_original = local_edit_case(first="critic-format")
    assert all(b.state != "UNRESOLVED" for b in bindings)
    assert len(calls) == 4  # original allowance, no added reviewer or retry
    observed = next(r for r in provider._fulfillment_receipts
        if r["stage"] == "MODEL_RESPONSE_OBSERVED" and r["attempt"] == 2)
    construction = observed["wire_presentation"]["candidate_construction"]
    assert construction["replaced_original_ordinals"] == []
    assert construction["removed_original_ordinals"] == []
    assert construction["appended_count"] == 0
    rev,ir,kwargs = args
    replay = app.form_fulfillment_projection(rev,ir,**kwargs)
    assert all(b.state != "UNRESOLVED" for b in replay) and len(calls) == 4


def test_explicit_conflict_repair_keeps_the_existing_human_gate_and_all_other_contributions():
    bindings,provider,calls,_args,_touched,original = local_edit_case(first="conflict")
    assert all(b.state != "UNRESOLVED" for b in bindings) and len(calls) == 3
    assert any(b.owner.value == "HUMAN_GATE" and b.phase.value == "HUMAN_INTEGRATION"
        and b.state == "BOUND_PENDING_EVIDENCE" for b in bindings)
    observed = next(r for r in provider._fulfillment_receipts
        if r["stage"] == "MODEL_RESPONSE_OBSERVED" and r["attempt"] == 2)
    construction = observed["wire_presentation"]["candidate_construction"]
    assert construction["removed_original_ordinals"] == [len(original["routes"]) - 1]
    assert construction["retained_original_ordinals"] == list(range(len(original["routes"]) - 1))
    assert bindings[0].formation_receipt["commit_scope"].startswith("DERIVED_PLAN_ONLY")


def test_record_existence_does_not_promote_an_unconfirmed_fact_or_supply_evidence():
    from spg.providers.fulfillment_candidate import candidate_construction_preconditions
    _rev,_ir,inventory,_plan = controlled_capacity_case()
    inventory = deepcopy(inventory)
    source = next(s for s in inventory["sources"] if s["kind"] == "FACT")
    source["payload"]["epistemic_status"] = "UNRESOLVED"
    state = candidate_construction_preconditions({},inventory,None)["candidate_construction_state"]
    assert source["source_ref"] not in state["evidence"]["fact_refs"]
    assert source["source_ref"] in state["evidence"]["observation_refs"]
    assert state["evidence"]["evidence_refs"] == []
