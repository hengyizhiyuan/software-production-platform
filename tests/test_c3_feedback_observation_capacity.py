"""Repeated rejections retain exact peers without consuming repair capacity."""
from copy import deepcopy
import json
import pytest

from spg.application import governed_obligations as app
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case, controlled_model_provider


def test_conflict_groups_preserve_every_peer_and_other_failure():
    failures = []
    for peer in range(40):
        failures.append({'code':'OBLIGATION_PROJECTION_CONFLICTING_DISPOSITION',
            'source':3,'route':40,'predicate':'SAME_ORIGINAL_COMPONENT',
            'conflicting_routes':[{'route':peer,'capability':'ARTIFACT_CONTENT','component_id':str(peer)},
                {'route':40,'capability':'UNRESOLVED','component_id':'40'}]})
    failures.append({'code':'OBLIGATION_SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN','source':4,'route':41})
    original=deepcopy(failures)
    grouped=app._group_repeated_feedback_predicates(failures)
    assert failures == original and len(grouped)==2
    assert [r['route'] for r in grouped[0]['conflicting_routes']] == list(range(41))
    assert grouped[1] == failures[-1]
    assert len(json.dumps(grouped)) < len(json.dumps(failures)) / 3
    bad=deepcopy(failures)
    bad[1]['conflicting_routes'][-1]['component_id']='substituted'
    with pytest.raises(ValueError,match='FEEDBACK_IDENTITY_DRIFT'):
        app._group_repeated_feedback_predicates(bad)


def test_wire_bound_capacity_stop_keeps_original_reason_and_never_reopens(monkeypatch):
    revision,ir,inventory,plan=controlled_capacity_case()
    def conflict(wire):
        route=deepcopy(wire['routes'][0])
        route.update(c=next(i for i,c in enumerate(app.fulfillment_capability_contracts()) if c['capability']=='UNRESOLVED'),f=[],t=[],u=[])
        wire['routes'].append(route)
    provider,calls=controlled_model_provider(inventory,plan,wire_change=conflict)
    bind=app._bind_repair_feedback
    def large_feedback(*args,**kwargs):
        data=json.loads(bind(*args,**kwargs))
        data['controlled_observation_padding']='x'*140000
        return json.dumps(data,separators=(',',':'))
    monkeypatch.setattr(app,'_bind_repair_feedback',large_feedback)
    kwargs={'provider':provider,'exact_target_paths':inventory['exact_target_paths']}
    result=app.form_fulfillment_projection(revision,ir,**kwargs)
    assert result[0].formation_receipt['terminal_reason']=='OBLIGATION_FORMATION_RECEIPT_LIMIT'
    assert all(b.state=='UNRESOLVED' for b in result) and len(calls)==1
    before=deepcopy(provider._fulfillment_receipts)
    replay=app.form_fulfillment_projection(revision,ir,**kwargs)
    assert replay[0].formation_receipt['terminal_reason']=='OBLIGATION_FORMATION_RECEIPT_LIMIT'
    assert provider._fulfillment_receipts==before and len(calls)==1
    terminal=next(r for r in provider._fulfillment_receipts if r.get('terminal'))
    assert terminal.get('candidate') is None and terminal['validation_passed'] is False
    assert 'validation_feedback' not in terminal
    assert len(json.dumps(terminal,ensure_ascii=False).encode()) <= 131072
    assert 'validation_feedback' in {r['field'] for r in terminal['capacity_observation']['dropped_fields']}
    terminal['capacity_observation']['original_row_sha256']='invalid'
    rejected=app.form_fulfillment_projection(revision,ir,**kwargs)
    assert rejected[0].formation_receipt['terminal_reason']=='OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'
    assert len(calls)==1


@pytest.mark.parametrize('legacy,tamper',[(True,None)]+[(False,key) for key in ('response_receipt_id','request_receipt_id','attempt','wire_output_fingerprint','inventory_fingerprint','candidate_fingerprint','components_fingerprint')])
def test_rejected_candidate_reference_retains_exact_wire_and_attempt(monkeypatch,legacy,tamper):
    revision,ir,inventory,plan=controlled_capacity_case()
    attempts=0
    def first_conflict(wire):
        nonlocal attempts
        attempts+=1
        if attempts==1:
            route=deepcopy(wire['routes'][0])
            route.update(c=next(i for i,c in enumerate(app.fulfillment_capability_contracts()) if c['capability']=='UNRESOLVED'),f=[],t=[],u=[])
            wire['routes'].append(route)
    provider,calls=controlled_model_provider(inventory,plan,wire_change=first_conflict)
    if legacy:
        preconditions=app._owner_source_preconditions
        def old_view(*args,**kwargs):
            kwargs['generation_view_contract']='existing-lossless-source-consumer-input-v1'
            kwargs['semantic_selection_input_contract']=None
            return preconditions(*args,**kwargs)
        monkeypatch.setattr(app,'_owner_source_preconditions',old_view)
    kwargs={'provider':provider,'exact_target_paths':inventory['exact_target_paths']}
    result=app.form_fulfillment_projection(revision,ir,**kwargs)
    assert result[0].formation_receipt['terminal_reason']=='VALIDATED_PROJECTION'
    assert len(calls)==3 and all(b.state!='UNRESOLVED' for b in result)
    rows=provider._fulfillment_receipts
    failed=next(r for r in rows if r['stage']=='CANDIDATE_VALIDATED' and r['attempt']==1)
    assert (failed.get('candidate') is None) is (not legacy)
    assert ('candidate_observation_reference' in failed) is (not legacy)
    before=deepcopy(rows)
    app.form_fulfillment_projection(revision,ir,**kwargs)
    assert rows==before and len(calls)==3
    if not legacy:
        assert tamper in failed['candidate_observation_reference']
        failed['candidate_observation_reference'][tamper]='another-attempt'
        rejected=app.form_fulfillment_projection(revision,ir,**kwargs)
        assert rejected[0].formation_receipt['terminal_reason']=='OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'
        assert len(calls)==3
