"""Request economy cannot replace canonical or Owner verification."""
from copy import deepcopy
import json
import pytest
from spg.application import governed_obligations as a
from spg.providers import fulfillment_candidate as p
from spg.providers.verification_receipts import MAX_CANDIDATE_BYTES
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case, controlled_model_provider

@pytest.mark.parametrize("scale", ["small", "medium", "complex"])
def test_new_request_reuses_canonical_domains_and_full_owner_proofs(scale, record_property):
    revision,ir,inventory,plan=controlled_capacity_case(scale)
    caps=a.fulfillment_capability_contracts()
    old=a._owner_source_preconditions(revision,ir,inventory,caps,generation_view_contract="existing-lossless-source-consumer-input-v2")
    new=a._owner_source_preconditions(revision,ir,inventory,caps,generation_view_contract=p._SOURCE_CONSUMER_INPUT_CONTRACT)
    before=deepcopy((inventory,new))
    schema=p._formation_output_schema(inventory,caps,owner_preconditions=new)
    legacy=p._formation_output_schema(inventory,caps,owner_preconditions=old)
    assert "anyOf" not in schema["properties"]["routes"]["items"]
    assert "anyOf" in legacy["properties"]["routes"]["items"]
    assert len(json.dumps(schema)) < len(json.dumps(legacy))/2
    record_property("previous_request_schema_bytes",len(json.dumps(legacy).encode()))
    record_property("current_request_schema_bytes",len(json.dumps(schema).encode()))
    payload=p._source_consumer_input(inventory,caps,p._fulfillment_wire_context(inventory,caps,owner_preconditions=new),new)
    assert payload["owner_source_preconditions"]==new
    for row,choice in zip(payload["temporary_wire"]["source_index_table"],p._formation_binding_choices(inventory,caps,new),strict=True):
        assert row["conditional_provenance_operands"]==p._formation_provenance_operands(choice,caps)
    assert (inventory,new)==before
    a.validate_projection_candidate(plan,revision,ir,inventory,allow_review_pending=True,source_contract="v3",owner_preconditions=new)
    with pytest.raises(ValueError):a.validate_projection_candidate(plan,revision,ir,inventory,source_contract="v3",owner_preconditions=new)
    wrong=plan.model_copy(update={"routes":tuple(r.model_copy(update={"target_paths":("unauthorized.html",)}) if r.target_paths else r for r in plan.routes)})
    with pytest.raises(ValueError):a.validate_projection_candidate(wrong,revision,ir,inventory,allow_review_pending=True,source_contract="v3",owner_preconditions=new)
    drift=deepcopy(new);drift["sources"][0]["source_ref"]="substituted"
    with pytest.raises(p._FulfillmentWireReceiptIdentityError):p._formation_output_schema(inventory,caps,owner_preconditions=drift)


@pytest.mark.parametrize("case", ["feedback_fits", "row_limit", "next_request_limit"])
def test_expanded_capacity_reject_provides_same_wire_bound_owner_feedback_without_relaxation(case):
    revision,ir,inventory,plan=controlled_capacity_case()
    if case=="feedback_fits":
        # Legitimate long original source, kept losslessly; only its unadmitted
        # repeated proposal exceeds the expanded Candidate limit.
        first=revision.engineering_semantic_facts[0]
        text=first.provenance.source_text+" Original controlled provenance."*800
        first=first.model_copy(update={"provenance":first.provenance.model_copy(update={"source_text":text})})
        revision.engineering_semantic_facts=(first,*revision.engineering_semantic_facts[1:])
        inventory=a.fulfillment_inventory(revision,ir,exact_target_paths=inventory["exact_target_paths"])
        changed=plan.routes[0].model_copy(update={"component_basis":plan.routes[0].component_basis.model_copy(update={"source_span_end":len(text),"source_component_quote":text})})
        plan=plan.model_copy(update={"inventory_fingerprint":inventory["inventory_fingerprint"],"routes":(changed,*plan.routes[1:])})
    attempts=0
    def oversized(wire):
        nonlocal attempts
        attempts+=1
        if attempts==1:
            if case=="feedback_fits":
                wire["routes"].extend([deepcopy(wire["routes"][0]),deepcopy(wire["routes"][0])])
                return
            count=64 if case=="next_request_limit" else 130
            wire["routes"]=[deepcopy(wire["routes"][i%len(wire["routes"])]) for i in range(count)]
            if case=="next_request_limit":
                # Reach the real expanded limit using untrusted rationale, while
                # retaining an affordable number of source/route observations.
                base=plan.model_copy(update={"routes":tuple(plan.routes[i%len(plan.routes)].model_copy(update={"rationale":""}) for i in range(count))})
                size=(MAX_CANDIDATE_BYTES+128-len(base.model_dump_json().encode()))//count+1
                assert 0<size<=1000
                for route in wire["routes"]:route["r"]="x"*size
            else:
                for route in wire["routes"]:route["r"]="Unadmitted controlled repeated proposal. "*6
    provider,calls=controlled_model_provider(inventory,plan,wire_change=oversized)
    result=a.form_fulfillment_projection(revision,ir,provider=provider,exact_target_paths=inventory["exact_target_paths"])
    failed=next(r for r in provider._fulfillment_receipts if r["stage"]=="CANDIDATE_VALIDATED" and r["attempt"]==1)
    assert failed["failed_predicate"]=="OBLIGATION_FORMATION_EXPANDED_RECEIPT_LIMIT"
    assert failed.get("candidate") is None and failed["validation_passed"] is False
    if case in {"row_limit", "next_request_limit"}:
        assert result[0].formation_receipt["terminal_reason"]=="OBLIGATION_FORMATION_RECEIPT_LIMIT"
        assert all(b.state=="UNRESOLVED" for b in result) and len(calls)==1
        terminal=next(r for r in reversed(provider._fulfillment_receipts) if r.get("terminal"))
        assert "validation_feedback" not in terminal
        assert terminal["capacity_observation"]["original_row_bytes"]>131072
        if case=="next_request_limit":
            assert failed["repair_feedback_bound"] and failed["owner_repair_context_bound"]
            assert terminal["stage"]=="MODEL_REQUEST_PENDING"
        before=deepcopy(provider._fulfillment_receipts)
        a.form_fulfillment_projection(revision,ir,provider=provider,exact_target_paths=inventory["exact_target_paths"])
        assert provider._fulfillment_receipts==before and len(calls)==1
        if case=="next_request_limit":
            dropped=next(d for d in terminal["capacity_observation"]["dropped_fields"] if d["field"]=="feedback")
            dropped["sha256"]="0"*64
            rejected=a.form_fulfillment_projection(revision,ir,provider=provider,exact_target_paths=inventory["exact_target_paths"])
            assert rejected[0].formation_receipt["terminal_reason"]=="OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT"
            assert len(calls)==1
        return
    assert failed["repair_feedback_bound"] and failed["owner_repair_context_bound"]
    assert "validation_feedback" in failed, failed.get("capacity_observation")
    feedback=json.loads(failed["validation_feedback"])
    assert feedback["violations"][0]["limit_bytes"]==MAX_CANDIDATE_BYTES==65536
    assert feedback["violations"][0]["expanded_bytes"]>65536
    assert feedback["owner_repair_context"]["violations"]
    assert len(feedback["untrusted_previous_wire"].encode())<=65536
    assert len(calls)==3 and result[0].formation_receipt["terminal_reason"]=="VALIDATED_PROJECTION", {"reason":result[0].formation_receipt["terminal_reason"],"stages":[(r["stage"],r.get("failed_predicate"),r.get("terminal_reason")) for r in provider._fulfillment_receipts]}
    before=deepcopy(provider._fulfillment_receipts)
    a.form_fulfillment_projection(revision,ir,provider=provider,exact_target_paths=inventory["exact_target_paths"])
    assert provider._fulfillment_receipts==before and len(calls)==3
