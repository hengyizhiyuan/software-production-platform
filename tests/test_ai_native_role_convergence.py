"""Preserve the existing repair slot and bind feedback to exact source roles."""
import json

import pytest

from spg.application import governed_obligations as app
from tests.test_ai_native_formation_construction import local_edit_case
from tests.test_ai_native_interpretation_binding import interpretation_case


@pytest.mark.parametrize('first,outcome', (('none','repair'),('semantic-span','repair'),
    ('semantic-span','repeat'),('semantic-span','drop'),('semantic-span','basis'),
    ('source-proof','repair')))
def test_complete_initial_candidate_keeps_actual_bounded_repair_and_independent_review(first,outcome):
    bindings,provider,calls,args,touched,original = local_edit_case(first=first,outcome=outcome,
        role_refs=True,role_convergence=True)
    passed=outcome=='repair'
    assert all(b.state!='UNRESOLVED' for b in bindings)==passed, bindings[0].formation_receipt['terminal_reason']
    assert len(calls)==(2 if first=='none' else 3 if passed else 2)
    initial,payload=calls[0]
    assert 'routes' in initial['output_schema']['properties'] and 'components' not in initial['output_schema']['properties']
    assert payload['owner_source_preconditions']['candidate_construction_state']['repair_targets']==[]
    if first=='semantic-span':
        _request,payload=calls[1];state=payload['owner_source_preconditions']['candidate_construction_state']
        target=next(t for t in state['repair_targets'] if t['status']=='OBSERVED')
        assert target['original_route_indices']==[touched]
        assert target['source_ref']==original['routes'][touched]['source_ref']
        assert target['uncovered_codepoint_ranges']
        assert state['repair_basis']['original_wire']['routes']==original['routes']
        assert state['repair_basis']['original_wire']['routes'][touched]['component_quote'] is not None
        if passed:
            # Only the MODEL's explicit second edit selects the complete basis.
            observed=next(r for r in provider._fulfillment_receipts if r['stage']=='MODEL_RESPONSE_OBSERVED' and r['attempt']==2)
            edit=json.loads(observed['candidate_output'])
            assert edit['replace'][0]['route']['component_quote'] is None
    rev,ir,kwargs=args
    provider.supports_role_convergence=False
    app.form_fulfillment_projection(rev,ir,**kwargs)
    assert len(calls)==(2 if first=='none' else 3 if passed else 2)


def test_role_repair_target_drift_cannot_change_accepted_plan_or_issue_calls():
    _bindings,provider,calls,args,_touched,_original=local_edit_case(first='semantic-span',role_refs=True,role_convergence=True)
    row=next(r for r in provider._fulfillment_receipts if r['stage']=='MODEL_REQUEST_PENDING' and r['attempt']==2)
    row['owner_source_preconditions']['candidate_construction_state']['repair_targets'][0]['source_ref']='different-source'
    rev,ir,kwargs=args
    result=app.form_fulfillment_projection(rev,ir,**kwargs)
    assert all(b.state=='UNRESOLVED' for b in result) and len(calls)==3


def test_unknown_repair_source_is_not_guessed():
    from spg.providers.fulfillment_candidate import _coverage_repair_targets
    assert _coverage_repair_targets({'violations':[{'code':'OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST','source':99}]},
        {'original_wire':{'routes':[]}}, {'sources':[]})==[
            {'status':'NOT_EVALUABLE','predicate':'OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST'}]


def test_legacy_requests_do_not_acquire_new_candidate_or_target_policy():
    _bindings,provider,calls,args,_touched,_original=local_edit_case(role_refs=True)
    assert 'role_convergence_contract' not in calls[0][1]['owner_source_preconditions']
    provider.supports_role_convergence=True
    rev,ir,kwargs=args
    app.form_fulfillment_projection(rev,ir,**kwargs)
    assert len(calls)==3


def test_preferred_complete_proposal_still_consumes_legal_interpretation_variance():
    bindings,_provider,calls,_args=interpretation_case(role_convergence=True,consumer_instructions=True)
    assert 'routes' in calls[0][0]['output_schema']['properties']
    assert all(b.state!='UNRESOLVED' for b in bindings)
    assert len(calls)==3  # Claim fallback remains bounded, not a new stage.


@pytest.mark.parametrize('encoding,passed', (('object',True),('string',False),('extra',False),('range',False)))
def test_explicit_remove_targets_have_same_identity_and_no_coercion(encoding,passed):
    bindings,provider,calls,_args,_touched,original=local_edit_case(first='conflict',role_refs=True,
        role_convergence=True,removal_encoding=encoding)
    assert all(b.state!='UNRESOLVED' for b in bindings)==passed
    assert len(calls)==(3 if passed else 2)
    if passed:
        request=calls[1][0]
        assert request['output_schema']['properties']['remove']['items']['$ref'].endswith('/_FulfillmentRoleRemoval')
        observed=next(r for r in provider._fulfillment_receipts if r['stage']=='MODEL_RESPONSE_OBSERVED' and r['attempt']==2)
        assert json.loads(observed['candidate_output'])['remove']==[{'index':len(original['routes'])-1}]
        assert observed['wire_presentation']['candidate_construction']['removed_original_ordinals']==[len(original['routes'])-1]


def test_v1_negotiation_is_not_upgraded_to_v2_on_resume():
    from spg.providers import fulfillment_candidate as provider_module
    _bindings,provider,calls,args,_touched,_original=local_edit_case(first='conflict',role_refs=True,role_convergence=True,
        role_contract=provider_module._ROLE_CONVERGENCE_LEGACY_CONTRACT)
    before=len(calls)
    rev,ir,kwargs=args
    provider.role_convergence_contract=provider_module._ROLE_CONVERGENCE_CONTRACT
    bindings=app.form_fulfillment_projection(rev,ir,**kwargs)
    assert all(b.state!='UNRESOLVED' for b in bindings)
    assert len(calls)==before
    assert all(r.get('owner_source_preconditions',{}).get('role_convergence_contract') in {None,provider_module._ROLE_CONVERGENCE_LEGACY_CONTRACT}
        for r in provider._fulfillment_receipts)


def test_v1_object_removal_stays_rejected_after_new_provider_default():
    from spg.providers.fulfillment_candidate import _ROLE_CONVERGENCE_LEGACY_CONTRACT
    bindings,provider,calls,args,_touched,_original=local_edit_case(first='conflict',role_refs=True,role_convergence=True,
        role_contract=_ROLE_CONVERGENCE_LEGACY_CONTRACT,removal_encoding='object')
    assert all(b.state=='UNRESOLVED' for b in bindings) and len(calls)==2
    rev,ir,kwargs=args
    app.form_fulfillment_projection(rev,ir,**kwargs)
    assert len(calls)==2
