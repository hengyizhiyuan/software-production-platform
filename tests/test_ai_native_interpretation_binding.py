"""Owner-local understanding to role binding; no Holdout inputs or real Provider."""
from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from spg.application import governed_obligations as app
from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case, controlled_wire, decode_review_input
from tests.test_c3_semantic_contract_calibration import review
from tests.test_c3_source_consumption_proof import fixture_review_proof


def interpretation_case(scale='small', failure=None):
    rev,ir,inventory,plan=controlled_capacity_case(scale)
    snapshot=deepcopy((rev,ir,inventory,plan))
    calls=[]
    def generate(**request):
        payload=json.loads(request['input_text']);calls.append((request,payload))
        if 'untrusted_fulfillment_candidate' in payload:
            candidate=decode_review_input(payload)
            output=fixture_review_proof(inventory,candidate,review(inventory,candidate),payload).model_dump_json()
        elif payload['same_basis_validation_feedback'] is None:
            first={'components':[{'source_ref':s['source_ref'],'component_quote':None,
                'interpretation':'Unreviewed interpretation of the complete original contribution',
                'alternatives':['More than one lawful implementation may exist'],
                'unknowns':['Actual artifact evidence has not been produced']} for s in inventory['sources']]}
            if failure=='claim-source':first['components'][0]['source_ref']='unobserved-source-claim'
            elif failure=='claim-shape':first['components'][0]['unknowns']=17
            output=json.dumps(first)
        else:
            state=payload['owner_source_preconditions']['candidate_construction_state']
            assert state['convergence']['action']=='CONTINUE'
            assert state['convergence']['repair_strategy']=='INTERPRET_THEN_BIND_EXISTING_ROLES'
            assert state['evidence']['evidence_refs']==[] and state['evidence']['inference_refs']
            assert state['understanding']['alternatives'] and state['understanding']['confidence'] is None
            basis=state['repair_basis']
            assert basis['representation']=='UNREVIEWED_INTERPRETATION_CLAIMS'
            wire,_=controlled_wire(inventory,plan,feedback=payload['same_basis_validation_feedback'],
                owner_preconditions=payload['owner_source_preconditions'])
            caps=payload['existing_capability_contracts']
            routes=[{'source_ref':inventory['sources'][r['s']]['source_ref'],
                'capability':caps[r['c']]['capability'],'component_quote':r['q'],
                'current_fact_dependencies':[inventory['sources'][i]['source_ref'] for i in r['f']],
                'target_paths':[inventory['exact_target_paths'][i] for i in r['t']],
                'provenance_support_refs':[inventory['sources'][i]['source_ref'] for i in r['u']],
                'rationale':r['r']} for r in wire['routes']]
            if failure=='missing-source':routes=[r for r in routes if r['source_ref']!=inventory['sources'][0]['source_ref']]
            elif failure=='wrong-source':routes[0]['source_ref']='source-not-in-this-inventory'
            elif failure=='wrong-path':routes[0]['target_paths']=['/outside-authorized-work']
            elif failure=='unsupported-proof':
                target=next(r for r in routes if r['capability']=='HUMAN_INTEGRATION_AUTHORIZATION')
                target['provenance_support_refs']=[]
            elif failure=='fake-fact':
                routes[0]['current_fact_dependencies']=[next(s['source_ref'] for s in inventory['sources'] if s['kind']!='FACT')]
            elif failure=='duplicate':routes.append(deepcopy(routes[0]))
            elif failure=='bad-quote':routes[0]['component_quote']='unobserved invented content'
            output=json.dumps({'routes':routes})
        return StructuredModelResult(output_text=output,provider=ModelProvider.DEEPSEEK,
            requested_model='controlled-understanding',effective_model='controlled-understanding',
            request_id=f'understanding-{len(calls)}',usage=ModelUsage(unknown=True),timing=ModelTiming(),retry_count=0)
    provider=ModelFulfillmentCandidateProvider(lambda:SimpleNamespace(generate=generate,close=lambda:None),
        candidate_construction=True,candidate_construction_contract='owner-local-interpretation-role-construction-v4')
    kwargs={'provider':provider,'exact_target_paths':inventory['exact_target_paths']}
    result=app.form_fulfillment_projection(rev,ir,**kwargs)
    assert (rev,ir,inventory,plan)==snapshot
    return result,provider,calls,(rev,ir,kwargs)


@pytest.mark.parametrize('scale,failure',(('small',None),('medium',None),('complex',None),('small','claim-source'),('small','claim-shape')))
def test_interpretations_are_claims_until_complete_binding_and_independent_review(scale,failure):
    bindings,provider,calls,args=interpretation_case(scale,failure)
    assert all(b.state!='UNRESOLVED' for b in bindings),bindings[0].formation_receipt['terminal_reason']
    assert len(calls)==3
    responses=[r for r in provider._fulfillment_receipts if r['stage']=='MODEL_RESPONSE_OBSERVED']
    first=responses[0];second=responses[1]
    assert first['wire_presentation']['candidate_construction']['code']=='OBLIGATION_FORMATION_ROLE_MAPPING_REQUIRED'
    first_check=next(r for r in provider._fulfillment_receipts if r['stage']=='CANDIDATE_VALIDATED' and r['attempt']==1)
    assert first_check['validation_passed'] is False and first_check.get('candidate') is None
    construction=second['wire_presentation']['candidate_construction']
    assert construction['parent_wire_sha256']==sha256(first['candidate_output'].encode()).hexdigest()
    assert construction['parent_binding']['request_receipt_id']
    assert construction['parent_binding']['inventory_fingerprint']==bindings[0].formation_receipt['inventory_fingerprint']
    assert construction['disposition']=='UNREVIEWED_CLAIMS_TO_CANDIDATE_ONLY; ALL_ORIGINAL_GATES_REQUIRED'
    assert bindings[0].formation_receipt['maximum_model_calls']==4
    from jsonschema import Draft202012Validator
    for request,_payload in calls[:2]:Draft202012Validator.check_schema(request['output_schema'])
    # Restarts retain this request's negotiated pipeline, even if the new
    # process prefers an earlier construction representation.
    provider.candidate_construction_contract='owner-local-role-reference-candidates-v3'
    rev,ir,kwargs=args
    assert all(b.state!='UNRESOLVED' for b in app.form_fulfillment_projection(rev,ir,**kwargs))
    assert len(calls)==3


def test_interpretation_parent_drift_cannot_reopen_or_accept_a_projection():
    _bindings,provider,calls,args=interpretation_case()
    row=next(r for r in provider._fulfillment_receipts if r['stage']=='MODEL_REQUEST_PENDING' and r['attempt']==2)
    row['owner_source_preconditions']['candidate_construction_state']['repair_basis']['raw_sha256']='0'*64
    rev,ir,kwargs=args
    assert all(b.state=='UNRESOLVED' for b in app.form_fulfillment_projection(rev,ir,**kwargs))
    assert len(calls)==3


@pytest.mark.parametrize('failure',('missing-source','wrong-source','wrong-path','unsupported-proof','fake-fact','duplicate','bad-quote'))
def test_interpretation_does_not_supply_missing_proof_or_override_final_gates(failure):
    bindings,provider,calls,_args=interpretation_case(failure=failure)
    assert all(b.state=='UNRESOLVED' for b in bindings)
    assert len(calls)==2
    assert not any(r['stage']=='SEMANTIC_REVIEW_PENDING' for r in provider._fulfillment_receipts)


def test_interpretation_identity_and_geometry_are_observations_not_semantic_evidence():
    from spg.providers.fulfillment_candidate import _interpretation_observations
    _rev,_ir,inv,_plan=controlled_capacity_case()
    raw={'components':[{'source_ref':inv['sources'][0]['source_ref'],'component_quote':'not observed',
        'interpretation':'A speculative claim','alternatives':['another explanation'],'unknowns':['missing observation']}]}
    observed=_interpretation_observations(raw,inv)[0]
    assert observed['geometry_status']=='UNKNOWN' and observed['quote_geometry'] is None
    assert observed['interpretation_status']=='UNREVIEWED_CLAIM' and observed['evidence_status']=='NOT_PROVIDED'
    raw['components'][0]['source_ref']='wrong-inventory'
    observed=_interpretation_observations(raw,inv)[0]
    assert observed['source_identity_status']=='UNKNOWN' and observed['source'] is None
    assert observed['geometry_status']=='UNKNOWN' and observed['evidence_status']=='NOT_PROVIDED'
    raw['components'][0]['unknowns']=17
    assert _interpretation_observations(raw,inv)[0]['schema_status']=='INVALID_CLAIM_SHAPE'
    raw['components'][0]['authorized']=True
    with pytest.raises(ValueError,match='SCHEMA_INVALID'):_interpretation_observations(raw,inv)
