"""Independent critic recovery shares the round's original two Review slots."""
from copy import deepcopy
import json
import pytest
from spg.application import governed_obligations as a
from spg.providers import fulfillment_candidate as p
from tests.test_c3_reviewer_contract_feedback import run_case
from tests.test_c3_fulfillment_wire_feedback import Checkpoint
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case
from tests.test_c3_semantic_contract_calibration import review
from tests.test_c3_source_consumption_proof import fixture_review_proof


def test_bad_critic_repairs_same_candidate_without_second_formation():
    rev, ir, inv, provider, calls, execute = run_case(same_candidate=True,empty_operands=True)
    result = execute()
    receipt = result[0].formation_receipt
    assert all(b.state != 'UNRESOLVED' for b in result), receipt['terminal_reason']
    assert len(calls) == 3 and receipt['attempt_count'] == 1
    assert receipt['provider_call_count'] == 3
    bound = calls[2]['existing_bound_reviewer_feedback']
    assert bound['same_candidate'] is True and bound['review_slot'] == 2
    assert bound['current_formation_wire_binding'] == bound['previous_formation_wire_binding']
    assert len([r for r in provider._fulfillment_receipts if r['stage']=='MODEL_RESPONSE_OBSERVED']) == 1
    a.validate_fulfillment_projection(result, rev, ir, source_revision=inv['source_revision'], exact_target_paths=inv['exact_target_paths'])
    execute()
    assert len(calls) == 3


@pytest.mark.parametrize('second_invalid,second_semantic', [(True,False),(False,True)])
def test_second_review_failure_truthfully_stops_without_third_review(second_invalid, second_semantic):
    rev, ir, inv, provider, calls, execute = run_case(same_candidate=True,
        second_invalid=second_invalid,second_semantic=second_semantic)
    result = execute()
    assert any(b.state=='UNRESOLVED' for b in result)
    assert len(calls)==3
    assert result[0].formation_receipt['attempt_count']==1
    execute()
    assert len(calls)==3


def test_observed_repair_resumes_without_repeating_inference():
    rev, ir, inv, provider, calls, execute = run_case(same_candidate=True,checkpoint=True)
    with pytest.raises(Checkpoint): execute()
    assert len(calls)==3
    result=execute()
    assert all(b.state!='UNRESOLVED' for b in result), result[0].formation_receipt['terminal_reason']
    assert len(calls)==3


@pytest.mark.parametrize('change',['candidate','context','wire','request','budget'])
def test_repair_rejects_identity_drift_without_new_call(change):
    rev, ir, inv, provider, calls, execute = run_case(same_candidate=True,checkpoint=True)
    with pytest.raises(Checkpoint): execute()
    rows=provider._fulfillment_receipts
    pending=next(r for r in rows if r['stage']=='SEMANTIC_REVIEW_REPAIR_PENDING')
    observed=next(r for r in rows if r['stage']=='SEMANTIC_REVIEW_REPAIR_OBSERVED')
    if change=='candidate': pending['candidate_fingerprint']='0'*64
    elif change=='context': pending['review_repair_context']['formation_attempt']=2
    elif change=='wire': observed['review_output']+=' '
    elif change=='request': observed['model']['request_id']='other-request'
    else: rows.append({**deepcopy(pending),'receipt_id':'another-pending'})
    result=execute()
    assert all(b.state=='UNRESOLVED' for b in result)
    assert len(calls)==3


def test_null_operands_are_exact_observations_and_do_not_supply_verdicts():
    rev, ir, inv, candidate=controlled_capacity_case()
    raw=fixture_review_proof(inv,candidate,review(inv,candidate), {"existing_owner_source_preconditions":{"review_source_consumption_contract":"existing-source-consumption-proof-v2"}}).model_dump(mode='json')
    row,check=next((r,c) for r in raw['source_results'] for c in r['consumption_checks'] if c['target_paths'])
    expected=list(candidate.routes[check['route_indices'][0]].target_paths)
    check['target_paths']=None
    row['complete_and_equivalent']=False
    output=json.dumps(raw)
    binding=p._review_identity_binding(inv,candidate,output,'request-one',consumer_references=True)
    resolved=p._resolve_review_identities(output,inv,candidate,binding,'request-one')
    resolved_row=next(r for r in resolved['source_results'] if r['source_ref']==row['source_ref'])
    assert resolved_row['consumption_checks'][0]['target_paths']==expected
    assert resolved_row['complete_and_equivalent'] is False
    with pytest.raises(p._FulfillmentWireReceiptIdentityError):
        p._resolve_review_identities(output,inv,candidate,binding,'other-request')


def test_pending_repair_has_unknown_outcome_and_is_never_dispatched_twice(monkeypatch):
    rev, ir, inv, provider, calls, execute = run_case(same_candidate=True)
    append=a.FulfillmentFormationReceipts.append
    def checkpoint(self,stage,*args,**kw):
        row=append(self,stage,*args,**kw)
        if stage=='SEMANTIC_REVIEW_REPAIR_PENDING': raise Checkpoint()
        return row
    monkeypatch.setattr(a.FulfillmentFormationReceipts,'append',checkpoint)
    with pytest.raises(Checkpoint): execute()
    assert len(calls)==2
    monkeypatch.setattr(a.FulfillmentFormationReceipts,'append',append)
    result=execute()
    assert all(b.state=='UNRESOLVED' for b in result)
    assert 'Unknown' in result[0].formation_receipt['terminal_reason'] or 'UNKNOWN' in result[0].formation_receipt['terminal_reason']
    assert len(calls)==2


def test_new_review_schema_requires_explicit_operand_reference():
    rev,ir,inv,candidate=controlled_capacity_case()
    schema=p._review_generation_schema(inv,candidate,route_scoped=True,
        source_consumption=True,consumer_operand_checks=True,consumer_references=True)
    for entry in schema['properties']['source_results']['prefixItems']:
        check=entry['properties']['consumption_checks']['items']
        assert 'target_paths' in check['required']
        assert {'type':'null'} in check['properties']['target_paths']['anyOf']


def test_omitted_operand_is_rejected_in_new_binding_and_legacy_stays_legacy():
    rev,ir,inv,candidate=controlled_capacity_case()
    payload={'existing_owner_source_preconditions':{'review_source_consumption_contract':'existing-source-consumption-proof-v2'}}
    raw=fixture_review_proof(inv,candidate,review(inv,candidate),payload).model_dump(mode='json')
    del raw['source_results'][0]['consumption_checks'][0]['target_paths']
    output=json.dumps(raw)
    binding=p._review_identity_binding(inv,candidate,output,'request-one',consumer_references=True)
    with pytest.raises(ValueError,match='CONSUMER_REFERENCE_MISSING'):
        p._resolve_review_identities(output,inv,candidate,binding,'request-one')
    legacy=p._review_identity_binding(inv,candidate,output,'legacy-request')
    restored=p._resolve_review_identities(output,inv,candidate,legacy,'legacy-request')
    assert 'target_paths' not in restored['source_results'][0]['consumption_checks'][0]


def test_reference_schema_prevents_mixed_consumer_claim_and_preserves_missing_method():
    from jsonschema import Draft202012Validator
    rev,ir,inv,candidate=controlled_capacity_case()
    schema=p._review_generation_schema(inv,candidate,route_scoped=True,
        source_consumption=True,consumer_operand_checks=True,consumer_references=True)
    index=next(i for i,s in enumerate(inv['sources']) if s['kind']=='IR_CONSTRAINT' and s['item_id']=='governed-boundary')
    source=inv['sources'][index]
    checks=fixture_review_proof(inv,candidate,review(inv,candidate),
        {'existing_owner_source_preconditions':{'review_source_consumption_contract':'existing-source-consumption-proof-v2'}})
    raw=checks.model_dump(mode='json')['source_results'][index]['consumption_checks'][0]
    raw['target_paths']=None
    node=schema['properties']['source_results']['prefixItems'][index]['properties']['consumption_checks']['items']
    validator=Draft202012Validator({'$defs':schema['$defs'],**node})
    assert validator.is_valid(raw)
    other=next(i for i,r in enumerate(candidate.routes) if r.source_ref==source['source_ref'] and r.capability!=raw['required_capability'])
    raw['route_indices'].append(other)
    assert not validator.is_valid(raw)
    raw.update(route_indices=[],target_paths=[])
    assert validator.is_valid(raw)  # Missing consumer remains a critic-proposed requirement, never approval.
