"""Exact-source coverage and existing Owner prerequisites; no live success."""
from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from spg.application.governed_obligations import (
    _owner_repair_context, _projection_binding, fulfillment_capability_contracts,
    form_fulfillment_projection, fulfillment_inventory, work_constraint_sources_correspond,
)
from spg.domain.governed_obligation import FulfillmentProjectionCandidate
from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
from spg.providers.fulfillment_candidate import (
    ModelFulfillmentCandidateProvider, _decode_fulfillment_candidate_wire,
    _FulfillmentWireValidationError, _fulfillment_wire_route_observations,
)
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case, controlled_wire
from tests.test_c3_semantic_contract_calibration import review


def invalid_proposal(inventory, plan, feedback=None):
    wire, _ = controlled_wire(inventory, plan, feedback=feedback)
    refs = {s['source_ref']: i for i, s in enumerate(inventory['sources'])}
    removed = next(i for i,s in enumerate(inventory['sources']) if s['kind']=='IR_CONSTRAINT')
    # The source remains cited as supporting provenance but has no own route.
    wire['routes'] = [r for r in wire['routes'] if r['s'] != removed]
    scope = next(r for r in wire['routes'] if r['c'] == next(i for i,c in enumerate(
        fulfillment_capability_contracts()) if c['capability']=='GIT_DIFF_SCOPE'))
    scope['c'] = next(i for i,c in enumerate(fulfillment_capability_contracts()) if c['capability']=='ARTIFACT_CONTENT')
    constraint = next(r for r in wire['routes'] if inventory['sources'][r['s']]['kind']=='WORK_CONSTRAINT')
    unrelated = next(i for i,s in enumerate(inventory['sources']) if s['kind']=='IR_CONSTRAINT' and i!=removed)
    constraint['u'].append(unrelated)
    return wire, removed, scope['s'], constraint['s']


@pytest.mark.parametrize('scale', ('small','medium','complex'))
def test_support_does_not_cover_source_and_one_feedback_exposes_owner_failures(scale):
    revision, ir, inventory, plan = controlled_capacity_case(scale)
    wire, missing, scope, constraint = invalid_proposal(inventory, plan)
    original = deepcopy(wire)
    raw = json.dumps(wire, ensure_ascii=False)
    with pytest.raises(_FulfillmentWireValidationError, match='SOURCE_CONTRIBUTION_LOST'):
        _decode_fulfillment_candidate_wire(raw, inventory, fulfillment_capability_contracts())
    ctx = _owner_repair_context(raw, revision, ir, inventory, fulfillment_capability_contracts(), validation_feedback=None)
    by_source = {(r['source'],r['code']) for r in ctx['violations']}
    assert (missing,'OBLIGATION_SOURCE_INVENTORY_INCOMPLETE') in by_source
    assert (scope,'OBLIGATION_FILE_SCOPE_OWNER_MISMATCH') in by_source
    assert (constraint,'OBLIGATION_SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN') in by_source
    prerequisites = {s['source']:s for s in ctx['source_preconditions']}
    assert prerequisites[missing]['primary_component_required']
    assert prerequisites[missing]['supporting_reference_does_not_cover_source']
    assert prerequisites[scope]['necessary_evidence_method']=='EXACT_GIT_DIFF_SCOPE'
    assert missing in prerequisites[constraint]['exact_corresponding_source_ordinals']
    assert ctx['status']=='UNADMITTED_OWNER_PRECONDITION_OBSERVATIONS'
    assert 'ACTUAL_OWNER_EVIDENCE' in ctx['not_evaluable']
    assert wire == original


@pytest.mark.parametrize('bad', ('identity','fact-index','span','quote','duplicate-key'))
def test_bad_raw_route_or_identity_cannot_supply_owner_evidence(bad):
    revision, ir, inventory, plan = controlled_capacity_case()
    wire, _ = controlled_wire(inventory, plan)
    if bad=='identity': wire['h']='0'*64
    elif bad=='fact-index': wire['routes'][0]['f']=[len(inventory['sources'])]
    elif bad=='span': wire['routes'][0]['z']=999999
    elif bad=='quote': wire['routes'][0]['q']='fabricated source quotation'
    raw=json.dumps(wire)
    if bad=='duplicate-key': raw=raw.replace('"v": 1','"v": 1, "v": 1',1)
    observed, unavailable=_fulfillment_wire_route_observations(raw, inventory, fulfillment_capability_contracts())
    assert unavailable
    assert not observed if bad in ('identity','duplicate-key') else all(index != 0 for index,_,_ in observed)
    ctx=_owner_repair_context(raw, revision, ir, inventory, fulfillment_capability_contracts(),validation_feedback=None)
    assert 'ASSURANCE' in ctx['not_evaluable'] and ctx['raw_routes_not_evaluable']


def test_same_text_from_different_item_does_not_prove_work_correspondence():
    revision, ir, inventory, plan=controlled_capacity_case()
    target=next(s for s in inventory['sources'] if s['kind']=='WORK_CONSTRAINT' and s['index']==0)
    origin=next(s for s in inventory['sources'] if s['kind']=='IR_CONSTRAINT' and s['clause_id']=='original-clause')
    foreign=deepcopy(origin)
    foreign['payload']['clause']['source_text']='This source does not establish the Work constraint.'
    # An extra support invalidates the whole correspondence proof; one good
    # support cannot license arbitrary additions.
    from spg.domain.governed_obligation import FulfillmentPhase
    args=dict(component='deploy', phase=FulfillmentPhase.CONTINUOUS_FROM_ADMISSION,
              semantic_component_declared=True,calibrated=True)
    assert work_constraint_sources_correspond(ir,target['payload']['content'],[origin],**args)
    ir.items=tuple(item.model_copy(update={'statement':'Foreign meaning'}) if item.item_id==origin['item_id'] else item for item in ir.items)
    assert not work_constraint_sources_correspond(ir,target['payload']['content'],[foreign],**args)


@pytest.mark.parametrize('tamper', (None,'owner-source','owner-errors','remove-owner-context','owner-marker','remove-both','legacy-feedback'))
def test_bound_feedback_repairs_once_or_stops_drift_without_review(tamper):
    revision,ir,inventory,plan=controlled_capacity_case()
    calls=[]
    class Checkpoint(BaseException): pass
    class Memory(list):
        def append(self,row):
            super().append(row)
            if row['stage']=='CANDIDATE_VALIDATED' and row['attempt']==1: raise Checkpoint()
    def generate(**request):
        payload=json.loads(request['input_text']);calls.append(payload)
        if 'untrusted_fulfillment_candidate' in payload:
            candidate=FulfillmentProjectionCandidate.model_validate(payload['untrusted_fulfillment_candidate'])
            output=review(inventory,candidate).model_dump_json()
        else:
            feedback=payload.get('same_basis_validation_feedback')
            if feedback is None: wire,*_=invalid_proposal(inventory,plan)
            else:
                data=json.loads(feedback)
                if tamper!='legacy-feedback':
                    assert data['owner_repair_context']['inventory_fingerprint']==inventory['inventory_fingerprint']
                assert data['repair_feedback_binding']['wire_output_fingerprint']==sha256(data['untrusted_previous_wire'].encode()).hexdigest()
                wire,_=controlled_wire(inventory,plan,feedback=feedback)
            output=json.dumps(wire,ensure_ascii=False)
        return StructuredModelResult(output_text=output,provider=ModelProvider.DEEPSEEK,requested_model='controlled-owner-repair',
            effective_model='controlled-owner-repair',request_id=str(len(calls)),usage=ModelUsage(),timing=ModelTiming(),retry_count=0)
    provider=ModelFulfillmentCandidateProvider(lambda:SimpleNamespace(generate=generate,close=lambda:None))
    provider._fulfillment_receipts=Memory()
    def run(): return form_fulfillment_projection(revision,ir,provider=provider,
        source_revision=inventory['source_revision'],exact_target_paths=inventory['exact_target_paths'])
    with pytest.raises(Checkpoint):run()
    provider._fulfillment_receipts=list(provider._fulfillment_receipts)
    failed=next(r for r in provider._fulfillment_receipts if r['stage']=='CANDIDATE_VALIDATED')
    feedback=json.loads(failed['validation_feedback'])
    assert failed['candidate'] is None and failed['owner_repair_context_bound']
    if tamper=='owner-source': feedback['owner_repair_context']['source_preconditions'][0]['source']=99
    elif tamper=='owner-errors': feedback['owner_repair_context']['violations']=[]
    elif tamper=='remove-owner-context': feedback.pop('owner_repair_context')
    elif tamper=='owner-marker': failed.pop('owner_repair_context_bound')
    elif tamper=='remove-both':
        feedback.pop('owner_repair_context');failed.pop('owner_repair_context_bound')
    elif tamper=='legacy-feedback':
        # Simulate the previously supported receipt shape, without rewriting
        # any actual historical receipt or introducing a new request slot.
        failed.pop('owner_repair_context_bound')
        for row in provider._fulfillment_receipts:
            row.pop('owner_repair_context_contract', None)
        from spg.application.governed_obligations import (
            _bind_wire_diagnostics, _bind_repair_feedback, projection_validation_feedback,
        )
        raw=feedback['untrusted_previous_wire']
        try:_decode_fulfillment_candidate_wire(raw,inventory,fulfillment_capability_contracts())
        except _FulfillmentWireValidationError as error:
            bound=_bind_wire_diagnostics(error,provider._fulfillment_receipts,1,revision,inventory,fulfillment_capability_contracts())
            failed['predecode_diagnostics']=bound
            legacy=projection_validation_feedback(None,revision,ir,inventory,error,wire_diagnostics=bound)
            feedback=json.loads(_bind_repair_feedback(legacy,provider._fulfillment_receipts,1,revision,inventory,fulfillment_capability_contracts(),None))
    if tamper:failed['validation_feedback']=json.dumps(feedback,separators=(',',':'))
    result=run()
    if tamper and tamper!='legacy-feedback':
        assert len(calls)==1 and all(b.state=='UNRESOLVED' for b in result)
        assert result[0].formation_receipt['terminal_reason']=='OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'
    else:
        assert len(calls)==3 and all(b.state!='UNRESOLVED' for b in result)
        before=deepcopy(provider._fulfillment_receipts)
        run()
        assert len(calls)==3 and provider._fulfillment_receipts==before
