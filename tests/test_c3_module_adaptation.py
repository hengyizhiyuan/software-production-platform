"""Development-only joint consumption controls; no Holdout or live model."""
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator

from spg.application.governed_obligations import (
    _owner_source_preconditions, _source_component_observations,
    fulfillment_capability_contracts, validate_projection_candidate,
    evaluate_constraint_routes,
)
from spg.domain.governed_obligation import fulfillment_source_semantic_text
from spg.providers.fulfillment_candidate import (
    _formation_output_schema, _decode_fulfillment_candidate_wire,
)
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case, controlled_wire
from tests.test_c3_semantic_contract_calibration import split_content, review


MARKER = "existing-source-component-convergence-v1"


def owner_for(revision, ir, inventory, *, adapted=True):
    return _owner_source_preconditions(revision, ir, inventory, fulfillment_capability_contracts(),
        generation_view_contract="existing-lossless-source-consumer-input-v3",
        semantic_selection_input_contract="existing-primary-meaning-owner-reference-v2",
        generation_prerequisite_contract="existing-owner-binding-generation-v2",
        module_adaptation_contract=MARKER if adapted else None)


@pytest.mark.parametrize("quote", [None, "full"])
@pytest.mark.parametrize("disposition", ["UNRESOLVED", "RETAIN_CONTEXT"])
def test_current_generation_projects_existing_whole_component_invariant(quote, disposition):
    revision, ir, inventory, plan = controlled_capacity_case()
    caps = fulfillment_capability_contracts()
    owner = owner_for(revision, ir, inventory)
    wire, _ = controlled_wire(inventory, plan, owner_preconditions=owner)
    schema = _formation_output_schema(inventory, caps, owner_preconditions=owner)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(wire)
    row = deepcopy(wire["routes"][0])
    row.update(c=next(i for i,c in enumerate(caps) if c["capability"]==disposition), f=[], t=[], u=[])
    if quote == "full":
        row["q"] = fulfillment_source_semantic_text(inventory["sources"][row["s"]])
    bad = deepcopy(wire); bad["routes"].append(row)
    assert list(Draft202012Validator(schema).iter_errors(bad))
    # A Provider ignoring generation restrictions is still rejected by the
    # same canonical Owner. Generation compliance is never assurance.
    candidate = _decode_fulfillment_candidate_wire(json.dumps(bad), inventory, caps, owner_preconditions=owner)
    with pytest.raises(ValueError, match="CONFLICTING_DISPOSITION|CONTEXT_NOT_ELIGIBLE"):
        validate_projection_candidate(candidate, revision, ir, inventory, allow_review_pending=True,
            source_contract="v3", owner_preconditions=owner)


def test_historical_qualified_generation_is_not_silently_upgraded():
    revision, ir, inventory, _ = controlled_capacity_case()
    owner = owner_for(revision, ir, inventory, adapted=False)
    schema = _formation_output_schema(inventory, fulfillment_capability_contracts(), owner_preconditions=owner)
    assert "module_adaptation_contract" not in owner
    assert "allOf" not in schema["properties"]["routes"]


@pytest.mark.parametrize("alternative", ["split", "shared-full-basis"])
def test_same_goal_allows_distinct_legal_component_compositions(alternative):
    revision, ir, inventory, plan = split_content()
    if alternative == "shared-full-basis":
        first, second = plan.routes[:2]
        text = fulfillment_source_semantic_text(inventory["sources"][0])
        whole = first.model_copy(update={"component_basis": first.component_basis.model_copy(update={
            "source_span_start":0, "source_span_end":len(text), "source_component_quote":text,
            "linked_fact_refs":(*first.component_basis.linked_fact_refs, *second.component_basis.linked_fact_refs)})})
        plan = plan.model_copy(update={"routes":(whole, *plan.routes[2:])})
    original = deepcopy(plan.model_dump(mode="json"))
    bindings = validate_projection_candidate(plan, revision, ir, inventory, semantic_review=review(inventory, plan),
        source_contract="v3")
    assert all(b.state!="UNRESOLVED" for b in bindings)
    assert any(b.state=="BOUND_PENDING_EVIDENCE" for b in bindings)
    assert plan.model_dump(mode="json")==original
    caps=fulfillment_capability_contracts();owner=owner_for(revision,ir,inventory)
    wire,_=controlled_wire(inventory,plan,owner_preconditions=owner)
    # The historical fixture serializer uses numeric spans with q=null.
    # Current generation explicitly chooses exact quotes for proper parts.
    for row, route in zip(wire['routes'],plan.routes,strict=True):
        if row['a']!=0 or row['z']!=len(fulfillment_source_semantic_text(inventory['sources'][row['s']])):
            row['q']=route.component_basis.source_component_quote
    Draft202012Validator(_formation_output_schema(inventory,caps,owner_preconditions=owner)).validate(wire)


@pytest.mark.parametrize("missing", [False, True])
def test_joint_coverage_is_not_a_semantic_or_evidence_verdict(missing):
    _, _, inventory, plan = split_content()
    observed = [(i, {}, r) for i,r in enumerate(plan.routes) if not(missing and i==1)]
    before=deepcopy(plan.model_dump(mode="json"))
    result=_source_component_observations(inventory,observed,[])
    first=result["sources"][0]
    assert first["coverage_status"] == ("MISSING" if missing else "COMPLETE")
    assert first["semantic_fulfillment"] == "UNKNOWN"
    assert first["actual_evidence"] == "NEED_EVIDENCE"
    assert bool(first["uncovered_codepoint_ranges"]) == missing
    assert plan.model_dump(mode="json")==before


def test_missing_or_unlocated_wire_does_not_fabricate_absent_obligations():
    _, _, inventory, plan=split_content()
    result=_source_component_observations(inventory,[(0,{},plan.routes[0])],["COMPLETE_WIRE_SYNTAX"])
    assert all(s["coverage_status"]=="NOT_EVALUABLE" for s in result["sources"])
    assert all(not s["uncovered_codepoint_ranges"] for s in result["sources"])
    assert result["not_evaluable"]==["COMPLETE_WIRE_SYNTAX"]


def test_joint_component_conflict_is_observed_without_selecting_a_route_to_delete():
    _,_,inventory,plan=split_content()
    bad=plan.routes[0].model_copy(update={"capability":"UNRESOLVED"})
    rows=(*plan.routes,bad)
    result=_source_component_observations(inventory,[(i,{},r) for i,r in enumerate(rows)],[])
    group=next(c for c in result["sources"][0]["components"] if c["disposition_status"]=="CONFLICT")
    assert group["route_indices"]==[0,len(rows)-1]
    assert group["proposed_capabilities"]==["ARTIFACT_CONTENT","UNRESOLVED"]
    assert result["sources"][0]["coverage_status"]=="COMPLETE"
    assert rows[-1]==bad


def test_true_missing_component_still_fails_and_missing_current_evidence_is_unverifiable():
    revision,ir,inventory,plan=split_content()
    bad=plan.model_copy(update={"routes":(plan.routes[0],*plan.routes[2:])})
    with pytest.raises(ValueError,match="SOURCE_CONTRIBUTION_LOST"):
        validate_projection_candidate(bad,revision,ir,inventory,allow_review_pending=True,source_contract="v3")
    revision,ir,inventory,plan=controlled_capacity_case()
    bindings=validate_projection_candidate(plan,revision,ir,inventory,semantic_review=review(inventory,plan))
    evidence=evaluate_constraint_routes(bindings,None,source_revision=inventory["source_revision"],
        path_scope_passed=True,exact_target_paths=tuple(inventory["exact_target_paths"]))
    assert evidence and all(not e["passed"] for e in evidence)
    assert all(e["disposition"]=="UNVERIFIABLE_CURRENT" for e in evidence)


def test_partial_owner_evidence_does_not_promote_unobserved_sibling_obligations():
    from types import SimpleNamespace
    from uuid import uuid4
    from spg.domain.governed_obligation import fulfillment_source_ref
    revision,ir,inventory,plan=controlled_capacity_case()
    bindings=validate_projection_candidate(plan,revision,ir,inventory,semantic_review=review(inventory,plan))
    route=next(b for b in bindings if b.source_kind.value=='IR_CONSTRAINT'
               and b.evidence_method=='EXACT_PERMISSION_GATE')
    attempt=uuid4()
    native=SimpleNamespace(attempt_id=attempt,
        production_context=SimpleNamespace(work_reality_revision_id=revision.id),
        obligation_references=(fulfillment_source_ref(route),),capability_grants=(),
        source_vector=SimpleNamespace(members=(SimpleNamespace(source_commit_oid=inventory['source_revision'],
            write_scope=tuple(inventory['exact_target_paths']),forbidden_paths=()),)))
    record=SimpleNamespace(attempt_id=attempt,binding=native,binding_digest='d'*64)
    evidence=evaluate_constraint_routes(bindings,record,source_revision=inventory['source_revision'],
        path_scope_passed=True,exact_target_paths=tuple(inventory['exact_target_paths']))
    assert any(e['passed'] for e in evidence) and any(not e['passed'] for e in evidence)
    assert all(e['disposition']=='UNVERIFIABLE_CURRENT' for e in evidence if not e['passed'])
    assert all(b.state in {'BOUND_PENDING_EVIDENCE','RETAINED_CONTEXT'} for b in bindings)


def test_bound_feedback_joint_observation_tamper_stops_before_another_call():
    from tests.test_c3_fulfillment_repair_context import repair_case, Checkpoint
    provider,calls,wires,run=repair_case(interrupt=True,coverage_failure=True,predecode_coverage_failure=True)
    with pytest.raises(Checkpoint):run()
    provider._fulfillment_receipts=list(provider._fulfillment_receipts)
    row=next(r for r in provider._fulfillment_receipts if r['stage']=='CANDIDATE_VALIDATED')
    feedback=json.loads(row['validation_feedback'])
    observations=feedback['owner_repair_context']['source_component_observations']
    assert observations['inventory_fingerprint']==feedback['inventory_fingerprint']
    from hashlib import sha256
    assert feedback['repair_feedback_binding']['wire_output_fingerprint']==sha256(wires[0].encode()).hexdigest()
    observations['sources'][0]['original_text_sha256']='0'*64
    row['validation_feedback']=json.dumps(feedback,separators=(',',':'))
    result=run()
    assert result[0].formation_receipt['terminal_reason']=='OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'
    assert len(wires)==1


def test_existing_feedback_recovers_without_extra_calls_and_replay_preserves_identity():
    from tests.test_c3_fulfillment_repair_context import repair_case
    provider,calls,wires,run=repair_case(coverage_failure=True,predecode_coverage_failure=True)
    result=run()
    assert all(b.state!='UNRESOLVED' for b in result)
    assert len(wires)==2 and len(calls)==3
    rows=deepcopy(provider._fulfillment_receipts)
    assert next(r for r in rows if r['stage']=='MODEL_REQUEST_PENDING')['owner_source_preconditions']['module_adaptation_contract']==MARKER
    run();assert provider._fulfillment_receipts==rows and len(calls)==3
