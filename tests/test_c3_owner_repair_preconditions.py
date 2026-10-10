"""Exact-source coverage and existing Owner prerequisites; no live success."""
from copy import deepcopy
from tests.test_c3_fulfillment_capacity_representation import decode_review_input
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from spg.application.governed_obligations import (
    _owner_repair_context, _owner_source_preconditions, _projection_binding, fulfillment_capability_contracts,
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


def invalid_proposal(inventory, plan, feedback=None, owner_preconditions=None):
    wire, _ = controlled_wire(inventory, plan, feedback=feedback, owner_preconditions=owner_preconditions)
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
            candidate=decode_review_input(payload)
            output=review(inventory,candidate).model_dump_json()
        else:
            feedback=payload.get('same_basis_validation_feedback')
            if feedback is None: wire,*_=invalid_proposal(inventory,plan,owner_preconditions=payload.get("owner_source_preconditions"))
            else:
                data=json.loads(feedback)
                if tamper!='legacy-feedback':
                    assert data['owner_repair_context']['inventory_fingerprint']==inventory['inventory_fingerprint']
                assert data['repair_feedback_binding']['wire_output_fingerprint']==sha256(data['untrusted_previous_wire'].encode()).hexdigest()
                wire,_=controlled_wire(inventory,plan,feedback=feedback,owner_preconditions=payload.get("owner_source_preconditions"))
            output=json.dumps(wire,ensure_ascii=False)
        return StructuredModelResult(output_text=output,provider=ModelProvider.DEEPSEEK,requested_model='controlled-owner-repair',
            effective_model='controlled-owner-repair',request_id=str(len(calls)),usage=ModelUsage(),timing=ModelTiming(),retry_count=0)
    provider=ModelFulfillmentCandidateProvider(lambda:SimpleNamespace(generate=generate,close=lambda:None))
    if tamper=='legacy-feedback':
        original_form=provider.form
        def legacy_form(inventory,capabilities,*,validation_feedback=None,receipt_callback=None):
            return original_form(inventory,capabilities,validation_feedback=validation_feedback,receipt_callback=receipt_callback)
        provider.form=legacy_form
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


@pytest.mark.parametrize('scale', ('small','medium','complex'))
def test_initial_source_proofs_match_existing_owner_and_keep_future_gate(scale):
    revision,ir,inventory,plan=controlled_capacity_case(scale)
    before=deepcopy(inventory)
    context=_owner_source_preconditions(revision,ir,inventory,fulfillment_capability_contracts())
    for row in context['sources']:
        for proof in row.get('necessary_source_proofs',[]):
            capability=fulfillment_capability_contracts()[proof['capability']]['capability']
            route=next((r for r in plan.routes if r.source_ref==row['source_ref'] and r.capability==capability),None)
            if route is None:continue  # structural eligibility is NOT a semantic proposal
            for indices in proof['minimal_support_sets']:
                supported=route.model_copy(update={'supporting_source_refs':tuple(inventory['sources'][i]['source_ref'] for i in indices)})
                binding=_projection_binding(revision,ir,inventory,supported,allow_calibrated=True)
                assert binding.state=='BOUND_PENDING_EVIDENCE'
                if capability=='HUMAN_INTEGRATION':assert binding.phase.value=='HUMAN_INTEGRATION'
    assert inventory==before and 'NO_PERMISSION_OR_EVIDENCE_PASS' in context['meaning']


@pytest.mark.parametrize('bad', ('missing','fact-instead-of-clause','affirmative','future','wrong-record'))
def test_negative_fact_proofs_do_not_license_missing_or_ineligible_origin(bad):
    from tests.test_c3_semantic_contract_calibration import negative_fact_plan
    revision,ir,inventory,plan=negative_fact_plan()
    source=next(s for s in inventory['sources'] if s['kind']=='FACT')
    route=next(r for r in plan.routes if r.source_ref==source['source_ref'])
    if bad=='missing':route=route.model_copy(update={'supporting_source_refs':()})
    elif bad=='fact-instead-of-clause':route=route.model_copy(update={'supporting_source_refs':(source['source_ref'],)})
    else:
        changes={'affirmative':{'polarity':'AFFIRMATIVE'},'future':{'temporal_scope':'FUTURE'},
            'wrong-record':{'source_record_id':revision.work_id}}
        ir.clauses=(ir.clauses[0].model_copy(update=changes[bad]),)
    with pytest.raises(ValueError,match='PERMISSION_REQUIRES_EXACT_CLAUSE'):
        _projection_binding(revision,ir,inventory,route,allow_calibrated=True)
    context=_owner_source_preconditions(revision,ir,inventory,fulfillment_capability_contracts())
    row=next(r for r in context['sources'] if r['source_ref']==source['source_ref'])
    deploy=next(i for i,c in enumerate(fulfillment_capability_contracts()) if c['capability']=='DENY_DEPLOY')
    proofs=[p for p in row.get('necessary_source_proofs',[]) if p['capability']==deploy]
    assert bool(proofs)==(bad in ('missing','fact-instead-of-clause'))


@pytest.mark.parametrize('tamper', ('contents','remove-one','remove-both','operands','unknown-operands'))
def test_initial_preconditions_are_bound_to_wire_attempt_and_replay(tamper):
    from tests.test_c3_fulfillment_capacity_representation import controlled_model_provider
    revision,ir,inventory,plan=controlled_capacity_case()
    provider,calls=controlled_model_provider(inventory,plan)
    original=provider.form
    class Checkpoint(BaseException):pass
    def interrupted(*args,receipt_callback=None,**kwargs):
        def observed(**values):
            receipt_callback(**values)
            raise Checkpoint()
        return original(*args,receipt_callback=observed,**kwargs)
    provider.form=interrupted
    def run():return form_fulfillment_projection(revision,ir,provider=provider,
        source_revision=inventory['source_revision'],exact_target_paths=inventory['exact_target_paths'])
    with pytest.raises(Checkpoint):run()
    assert calls[0]['owner_source_preconditions']['inventory_fingerprint']==inventory['inventory_fingerprint']
    for row in provider._fulfillment_receipts:
        if row['stage'] not in ('MODEL_REQUEST_PENDING','MODEL_RESPONSE_OBSERVED'):continue
        if tamper=='contents':row['owner_source_preconditions']['sources'][0]['source']=999
        elif tamper=='operands':row['owner_source_preconditions']['capability_operand_requirements'][0]['target_operand']['required_ordinals']=[]
        elif tamper=='unknown-operands':row['owner_source_preconditions']['operand_observation_contract']='unknown'
        elif tamper=='remove-both' or row['stage']=='MODEL_RESPONSE_OBSERVED':row.pop('owner_source_preconditions')
    result=run()
    assert len(calls)==1 and all(b.state=='UNRESOLVED' for b in result)
    assert result[0].formation_receipt['terminal_reason']=='OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'


@pytest.mark.parametrize('scale', ('small','medium','complex'))
def test_diff_operands_report_complete_allowlist_not_prohibition_rationale(scale):
    revision,ir,inventory,plan=controlled_capacity_case(scale)
    caps=fulfillment_capability_contracts()
    prerequisites=_owner_source_preconditions(revision,ir,inventory,caps)
    wire,_=controlled_wire(inventory,plan,owner_preconditions=prerequisites)
    ordinal=next(i for i,r in enumerate(wire['routes']) if caps[r['c']]['capability']=='GIT_DIFF_SCOPE')
    wire['routes'][ordinal]['t']=[]
    wire['routes'][ordinal]['r']='The explanation refers to the correct paths but supplies no operands.'
    raw=json.dumps(wire)
    context=_owner_repair_context(raw,revision,ir,inventory,caps,validation_feedback=None,owner_preconditions=prerequisites)
    failure=next(v for v in context['violations'] if v.get('route')==ordinal)
    assert failure['code']=='OBLIGATION_DIFF_SCOPE_INCOMPLETE'
    operands=failure['owner_operand_observations']['target_operand']
    expected=list(range(len(inventory['exact_target_paths'])))
    assert operands['required_ordinals']==operands['missing_ordinals']==expected
    assert operands['observed_ordinals']==[] and not operands['matches']
    assert json.loads(raw)==wire  # diagnostic did not repair the untrusted proposal
    route=plan.routes[ordinal].model_copy(update={'target_paths':()})
    with pytest.raises(ValueError,match='DIFF_SCOPE_INCOMPLETE'):
        _projection_binding(revision,ir,inventory,route,allow_calibrated=True)


@pytest.mark.parametrize('capability', ('DENY_DEPLOY','GIT_DIFF_SCOPE'))
def test_derived_exclusion_requires_production_origin_and_current_negative_clause(capability):
    from spg.domain.intent_realization import SemanticKind
    from spg.domain.governed_obligation import FulfillmentRouteCandidate, FulfillmentComponentBasis
    from tests.test_c3_semantic_contract_calibration import negative_fact_plan
    revision,ir,_,_=negative_fact_plan()
    production=ir.items[0].model_copy(update={'item_id':'novel-production','kind':SemanticKind.PRODUCTION_INTENT,
        'production':ir.current_production[0].model_copy(update={'exclusions':('a protected external effect',)})})
    production_clause=ir.clauses[0].model_copy(update={'clause_id':'novel-production-request',
        'semantic_item_ids':(production.item_id,),'polarity':'AFFIRMATIVE'})
    ir.items=(*ir.items,production);ir.clauses=(*ir.clauses,production_clause)
    quote='Excluded from this Work: a protected external effect'
    revision.constraints=(quote,)
    inventory=fulfillment_inventory(revision,ir)
    sources=inventory['sources'];caps=fulfillment_capability_contracts()
    primary=next(s for s in sources if s['kind']=='WORK_CONSTRAINT')
    negative=next(s for s in sources if s['kind']=='IR_CONSTRAINT' and s['clause_id']==ir.clauses[0].clause_id)
    origin=next(s for s in sources if s['kind']=='IR_CLAUSE' and s['clause_id']==production_clause.clause_id)
    route=FulfillmentRouteCandidate(source_ref=primary['source_ref'],capability=capability,
        work_constraint_indices=(0,),target_paths=tuple(inventory['exact_target_paths']) if capability=='GIT_DIFF_SCOPE' else (),
        supporting_source_refs=(negative['source_ref'],),rationale='The prohibition alone is not the derivation proof.',
        component_basis=FulfillmentComponentBasis(source_span_start=0,source_span_end=len(quote),source_component_quote=quote,linked_fact_refs=()))
    plan=FulfillmentProjectionCandidate(inventory_fingerprint=inventory['inventory_fingerprint'],routes=(route,))
    prerequisites=_owner_source_preconditions(revision,ir,inventory,caps)
    wire,_=controlled_wire(inventory,plan,owner_preconditions=prerequisites)
    context=_owner_repair_context(json.dumps(wire),revision,ir,inventory,caps,validation_feedback=None,owner_preconditions=prerequisites)
    failure=next(v for v in context['violations'] if v.get('route')==0)
    assert failure['code']=='OBLIGATION_SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN'
    missing=failure['owner_operand_observations']['support_operand']['missing_members_by_alternative']
    origin_ordinal=sources.index(origin)
    assert missing and all(origin_ordinal in alternative for alternative in missing)
    with pytest.raises(ValueError,match='CORRESPONDENCE_UNPROVEN'):
        _projection_binding(revision,ir,inventory,route,allow_calibrated=True)
    corrected=route.model_copy(update={'supporting_source_refs':(origin['source_ref'],negative['source_ref'])})
    assert _projection_binding(revision,ir,inventory,corrected,allow_calibrated=True).state=='BOUND_PENDING_EVIDENCE'


def test_old_operandless_receipts_replay_without_feedback_identity_drift(monkeypatch):
    import spg.application.governed_obligations as owner
    from tests.test_c3_fulfillment_capacity_representation import controlled_model_provider
    revision,ir,inventory,plan=controlled_capacity_case()
    original=owner._owner_source_preconditions
    def legacy(*args,**kwargs):
        kwargs['include_operand_observations']=False
        return original(*args,**kwargs)
    provider,calls=controlled_model_provider(inventory,plan)
    def run():return form_fulfillment_projection(revision,ir,provider=provider,
        source_revision=inventory['source_revision'],exact_target_paths=inventory['exact_target_paths'])
    with monkeypatch.context() as patch:
        patch.setattr(owner,'_owner_source_preconditions',legacy)
        assert all(b.state!='UNRESOLVED' for b in run())
    before=deepcopy(provider._fulfillment_receipts)
    assert all(b.state!='UNRESOLVED' for b in run()) and len(calls)==2
    assert provider._fulfillment_receipts==before


def test_fact_gate_correspondence_is_visible_before_unrelated_route_errors_are_fixed():
    from tests.test_c3_semantic_contract_calibration import negative_git_plan
    revision,ir,inventory,plan=negative_git_plan()
    caps=fulfillment_capability_contracts()
    fact=next(i for i,r in enumerate(plan.routes) if r.source_ref.startswith('semantic-fact:'))
    routes=tuple(r.model_copy(update={'target_paths':()}) if i==fact else
        r.model_copy(update={'capability':'DENY_DEPLOY','target_paths':()}) if r.capability=='GIT_DIFF_SCOPE' else r
        for i,r in enumerate(plan.routes))
    plan=plan.model_copy(update={'routes':routes})
    preconditions=_owner_source_preconditions(revision,ir,inventory,caps)
    wire,_=controlled_wire(inventory,plan,owner_preconditions=preconditions)
    context=_owner_repair_context(json.dumps(wire),revision,ir,inventory,caps,validation_feedback=None,owner_preconditions=preconditions)
    codes={v['code'] for v in context['violations'] if v.get('route')==fact}
    assert {'OBLIGATION_DIFF_SCOPE_INCOMPLETE','OBLIGATION_FACT_GATE_CORRESPONDENCE_UNPROVEN'}<=codes
    failure=next(v for v in context['violations'] if v['code']=='OBLIGATION_FACT_GATE_CORRESPONDENCE_UNPROVEN')
    assert failure['missing_same_capability_source_ordinals']
    assert 'ACTUAL_OWNER_EVIDENCE' in context['not_evaluable']


def test_successful_terminal_replay_cannot_drop_initial_proof_context():
    from tests.test_c3_fulfillment_capacity_representation import controlled_model_provider
    revision,ir,inventory,plan=controlled_capacity_case()
    provider,calls=controlled_model_provider(inventory,plan)
    def run():return form_fulfillment_projection(revision,ir,provider=provider,
        source_revision=inventory['source_revision'],exact_target_paths=inventory['exact_target_paths'])
    assert all(b.state!='UNRESOLVED' for b in run()) and len(calls)==2
    for row in provider._fulfillment_receipts:row.pop('owner_source_preconditions',None)
    result=run()
    assert len(calls)==2 and all(b.state=='UNRESOLVED' for b in result)
    assert result[0].formation_receipt['terminal_reason']=='OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'


@pytest.mark.parametrize('contract', ('complete-value-owner-observations-v1','complete-value-observations-v1'))
def test_complete_value_owner_observations_are_negotiated_and_never_admitted(contract):
    revision,ir,inventory,plan=controlled_capacity_case()
    prerequisites=_owner_source_preconditions(revision,ir,inventory,fulfillment_capability_contracts(),syntax_observation_contract=contract)
    wire,_=controlled_wire(inventory,plan,owner_preconditions=prerequisites)
    scope=next(r for r in wire['routes'] if fulfillment_capability_contracts()[r['c']]['capability']=='GIT_DIFF_SCOPE')
    scope['c']=next(i for i,c in enumerate(fulfillment_capability_contracts()) if c['capability']=='ARTIFACT_CONTENT')
    raw=json.dumps(wire)+'}'
    with pytest.raises(_FulfillmentWireValidationError,match='WIRE_JSON_INVALID'):
        _decode_fulfillment_candidate_wire(raw,inventory,fulfillment_capability_contracts(),owner_preconditions=prerequisites)
    context=_owner_repair_context(raw,revision,ir,inventory,fulfillment_capability_contracts(),validation_feedback=None,owner_preconditions=prerequisites)
    codes={r['code'] for r in context['violations']}
    assert ('OBLIGATION_FILE_SCOPE_OWNER_MISMATCH' in codes)==(contract=='complete-value-owner-observations-v1')
    assert context['raw_routes_not_evaluable'] and 'COMPLETE_PLAN_ADMISSION' in context['not_evaluable']
    assert context['status']=='UNADMITTED_OWNER_PRECONDITION_OBSERVATIONS'
