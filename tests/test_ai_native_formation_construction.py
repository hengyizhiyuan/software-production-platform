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


def local_edit_case(scale="small", outcome="repair", first="source-proof", *, semantic_edits=False):
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
                if first in {"source-proof", "semantic-source-proof"}:
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
                elif first == "semantic-coverage":
                    wire["routes"].pop(touched)
                elif first == "semantic-quote":
                    wire["routes"][touched]["q"] = "a quote that was never in the immutable source"
                old_wire = deepcopy(wire)
                proposal = ({"routes":[{k:v for k,v in row.items() if k not in {"a","z"}}
                    for row in wire["routes"]]} if first.startswith("semantic-") else wire)
                if semantic_edits and first.startswith("semantic-"):
                    old_wire["routes"] = deepcopy(proposal["routes"])
                output = json.dumps(proposal, ensure_ascii=False)
            else:
                assert state["convergence"]["action"] == "REPAIR"
                basis = state["repair_basis"]
                assert basis["original_wire"] == old_wire
                replacement = deepcopy(wire["routes"][touched])
                if basis.get("representation") == "UNLOCATED_SEMANTIC_PROPOSAL":
                    replacement = {k:v for k,v in replacement.items() if k not in {"a","z"}}
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
                elif first == "semantic-coverage":
                    assert state["convergence"]["repair_family"] == "SOURCE_CORRESPONDENCE"
                    feedback = json.loads(payload["same_basis_validation_feedback"])
                    missing = [s for s in feedback["owner_repair_context"]["source_component_observations"]["sources"]
                        if s["coverage_status"] == "MISSING"]
                    assert missing and missing[0]["uncovered_codepoint_ranges"]
                    edit["replace"] = []
                    edit["append"] = [replacement]
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
        lambda: SimpleNamespace(generate=generate, close=lambda: None), candidate_construction=True,
        candidate_construction_contract="owner-local-semantic-candidate-edits-v2" if semantic_edits else
            "owner-local-wire-candidate-edits-v1")
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


def test_semantic_proposal_uses_owner_identity_and_geometry_then_local_source_repair():
    bindings,provider,calls,args,_touched,_original = local_edit_case(first="semantic-source-proof")
    assert all(b.state != "UNRESOLVED" for b in bindings) and len(calls) == 3
    first = next(r for r in provider._fulfillment_receipts
        if r["stage"] == "MODEL_RESPONSE_OBSERVED" and r["attempt"] == 1)
    raw = json.loads(first["candidate_output"])
    assert set(raw) == {"routes"}
    assert all("a" not in r and "z" not in r for r in raw["routes"])
    assert first["wire_presentation"]["candidate_construction"]["representation"] == "SEMANTIC_QUOTE_PROPOSAL"
    assert first["candidate_output_sha256"] == sha256(first["candidate_output"].encode()).hexdigest()
    rev,ir,kwargs = args
    replay = app.form_fulfillment_projection(rev,ir,**kwargs)
    assert all(b.state != "UNRESOLVED" for b in replay) and len(calls) == 3


def test_semantic_quote_compiler_refuses_ambiguous_or_invented_text():
    from spg.providers.fulfillment_candidate import _construct_semantic_proposal
    _rev,_ir,inventory,_plan = controlled_capacity_case()
    source = next(i for i,s in enumerate(inventory["sources"]) if s["kind"] == "FACT")
    sketch = {"routes":[{"s":source,"c":0,"q":"this text was never observed", "f":[],"t":[],"u":[],"r":"proposal only"}]}
    with pytest.raises(ValueError,match="QUOTE_NOT_OBSERVED"):
        _construct_semantic_proposal(sketch,inventory,{"wire_request_fingerprint":"0"*64,"wire_table_fingerprint":"1"*64})
    from collections import Counter
    from spg.domain.governed_obligation import fulfillment_source_semantic_text
    text = fulfillment_source_semantic_text(inventory["sources"][source])
    sketch["routes"][0]["q"] = next(ch for ch,n in Counter(text).items() if n > 1 and not ch.isspace())
    with pytest.raises(ValueError,match="LOCATOR_AMBIGUOUS"):
        _construct_semantic_proposal(sketch,inventory,{"wire_request_fingerprint":"0"*64,"wire_table_fingerprint":"1"*64})


@pytest.mark.parametrize("scale", ("small", "medium", "complex"))
def test_temporary_schemas_reuse_exact_original_operand_domains(scale):
    from spg.providers.fulfillment_candidate import _formation_output_schema
    _bindings,_provider,calls,_args,_touched,_original = local_edit_case(scale, first="semantic-source-proof")
    first = json.loads(calls[0][0]["input_text"])
    _rev,_ir,inventory,_plan = controlled_capacity_case(scale)
    capabilities = first["existing_capability_contracts"]
    expected = {
        "s": list(range(len(inventory["sources"]))),
        "c": list(range(len(capabilities))),
        "f": [i for i,s in enumerate(inventory["sources"]) if s["kind"] == "FACT"],
        "u": list(range(len(inventory["sources"]))),
        "t": list(range(len(inventory["exact_target_paths"]))),
    }
    legacy = _formation_output_schema(inventory, capabilities)
    for request,_input in calls[:2]:
        schema = request["output_schema"]
        name = "_FulfillmentSemanticRoute" if request is calls[0][0] else "_FulfillmentCompactRoute"
        properties = schema["$defs"][name]["properties"]
        for field,domain in expected.items():
            part = properties[field] if field in {"s","c"} else properties[field]["items"]
            assert part["enum"] == domain
            original = legacy["$defs"]["_FulfillmentCompactRoute"]["properties"][field]
            assert part["enum"] == (original if field in {"s","c"} else original["items"])["enum"]
        assert "do not discharge" in properties["u"]["description"]
        assert "FACT" in properties["f"]["description"]
    empty = deepcopy(inventory)
    empty["sources"] = [s for s in empty["sources"] if s["kind"] != "FACT"]
    empty["exact_target_paths"] = []
    schema = _formation_output_schema(empty, capabilities,
        owner_preconditions={"candidate_construction_contract":"owner-local-wire-candidate-edits-v1"})
    properties = schema["$defs"]["_FulfillmentSemanticRoute"]["properties"]
    assert properties["f"]["maxItems"] == properties["t"]["maxItems"] == 0


def test_missing_primary_source_is_locally_added_not_silently_covered_by_support():
    bindings,provider,calls,_args,_touched,original = local_edit_case(first="semantic-coverage")
    assert all(b.state != "UNRESOLVED" for b in bindings) and len(calls) == 3
    observed = next(r for r in provider._fulfillment_receipts
        if r["stage"] == "MODEL_RESPONSE_OBSERVED" and r["attempt"] == 2)
    construction = observed["wire_presentation"]["candidate_construction"]
    assert construction["appended_count"] == 1
    assert construction["replaced_original_ordinals"] == construction["removed_original_ordinals"] == []
    assert construction["retained_original_ordinals"] == list(range(len(original["routes"])))


def test_semantic_and_edit_schemas_keep_existing_conditional_owner_proofs():
    from jsonschema import Draft202012Validator
    _bindings,_provider,calls,_args,_touched,_original = local_edit_case(first="semantic-source-proof")
    first_request,first_input = calls[0]
    second_request,second_input = calls[1]
    original = second_input["owner_source_preconditions"]["candidate_construction_state"]["repair_basis"]["original_wire"]
    semantic = {"routes":[{k:v for k,v in r.items() if k not in {"a","z"}}
        for r in original["routes"]]}
    schema = first_request["output_schema"]
    Draft202012Validator.check_schema(schema)
    assert not Draft202012Validator(schema).is_valid(semantic)  # required u was removed
    edit_schema = second_request["output_schema"]
    Draft202012Validator.check_schema(edit_schema)
    replacement = json.loads(second_input["same_basis_validation_feedback"])
    assert replacement["violations"]  # exact bound feedback, not a model repair
    # A source cannot disappear merely because another source cites it as u.
    coverage_only = {"type":"object","properties":{"routes":{
        "type":"array","allOf":schema["properties"]["routes"]["allOf"]}}}
    assert Draft202012Validator(coverage_only).is_valid(semantic)
    removed = semantic["routes"][0]["s"]
    semantic["routes"] = [r for r in semantic["routes"] if r["s"] != removed]
    assert not Draft202012Validator(coverage_only).is_valid(semantic)
    operand = edit_schema["properties"]["append"]["items"]
    assert operand == edit_schema["$defs"]["_FulfillmentRouteReplacement"]["properties"]["route"]
    assert operand["allOf"][0]["$ref"] == "#/$defs/_FulfillmentCompactRoute"


def test_unlocated_semantic_quote_is_repairable_with_exact_raw_lineage_and_no_span_backfill():
    bindings,provider,calls,args,touched,original = local_edit_case(first="semantic-quote",semantic_edits=True)
    assert all(b.state!='UNRESOLVED' for b in bindings) and len(calls)==3
    rejected = next(r for r in provider._fulfillment_receipts if r['stage']=='CANDIDATE_VALIDATED' and r['attempt']==1)
    feedback = json.loads(rejected['validation_feedback'])
    failure = next(v for v in feedback['violations'] if v['code']=='OBLIGATION_COMPONENT_QUOTE_NOT_OBSERVED')
    assert failure['route']==touched and failure['source']==original['routes'][touched]['s']
    assert failure['location_status'].startswith('UNKNOWN')
    observed = next(r for r in provider._fulfillment_receipts if r['stage']=='MODEL_RESPONSE_OBSERVED' and r['attempt']==2)
    edit = json.loads(observed['candidate_output'])
    assert 'a' not in edit['replace'][0]['route'] and 'z' not in edit['replace'][0]['route']
    state=calls[1][1]['owner_source_preconditions']['candidate_construction_state']
    assert state['repair_basis']['representation']=='UNLOCATED_SEMANTIC_PROPOSAL'
    assert state['repair_basis']['raw_sha256']==feedback['repair_feedback_binding']['wire_output_fingerprint']
    assert state['convergence']['repair_family']=='SOURCE_CORRESPONDENCE'
    rev,ir,kwargs=args
    assert all(b.state!='UNRESOLVED' for b in app.form_fulfillment_projection(rev,ir,**kwargs))
    assert len(calls)==3


@pytest.mark.parametrize('outcome',('repeat','drop','basis','wrong-header','duplicate-key'))
def test_unlocated_semantic_edits_do_not_admit_unknown_quotes_or_erase_requirements(outcome):
    bindings,provider,calls,_args,_touched,_original = local_edit_case(
        first='semantic-quote',semantic_edits=True,outcome=outcome)
    assert all(b.state=='UNRESOLVED' for b in bindings) and len(calls)==2
    assert not any(r['stage']=='SEMANTIC_REVIEW_PENDING' for r in provider._fulfillment_receipts)


def test_old_construction_receipt_replays_under_new_provider_without_protocol_upgrade():
    bindings,provider,calls,args,_touched,_original = local_edit_case(first='semantic-source-proof')
    provider.candidate_construction_contract='owner-local-semantic-candidate-edits-v2'
    rev,ir,kwargs=args
    replay=app.form_fulfillment_projection(rev,ir,**kwargs)
    assert all(b.state!='UNRESOLVED' for b in replay) and len(calls)==3
    assert replay[0].formation_receipt['candidate_attempts']==bindings[0].formation_receipt['candidate_attempts']
