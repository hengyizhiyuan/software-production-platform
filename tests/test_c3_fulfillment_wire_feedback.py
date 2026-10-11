"""Predecode feedback identity; controlled adapters, no live model or Work."""
from tests.test_c3_source_consumption_proof import fixture_review_proof
from copy import deepcopy
from tests.test_c3_fulfillment_capacity_representation import decode_review_input
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from spg.application.governed_obligations import form_fulfillment_projection, fulfillment_capability_contracts
from spg.domain.governed_obligation import FulfillmentProjectionCandidate, canonical_fingerprint
from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
from spg.providers.fulfillment_candidate import (
    ModelFulfillmentCandidateProvider, _decode_fulfillment_candidate_wire,
    _FulfillmentWireValidationError, _fulfillment_wire_schema,
)
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case, controlled_wire
from tests.test_c3_semantic_contract_calibration import review


class Checkpoint(BaseException):
    pass


@pytest.mark.parametrize('tail', ('}', ' trailing text', '\n{"second":1}'))
def test_complete_original_json_value_exposes_fields_without_admitting_prefix(tail):
    from spg.application.governed_obligations import _owner_source_preconditions
    rev,ir,inventory,plan=controlled_capacity_case()
    prerequisites=_owner_source_preconditions(rev,ir,inventory,fulfillment_capability_contracts())
    wire,_=controlled_wire(inventory,plan,owner_preconditions=prerequisites)
    invalid_references(wire,inventory)
    value=json.dumps(wire);raw=' \n'+value+tail
    with pytest.raises(_FulfillmentWireValidationError,match='WIRE_JSON_INVALID') as captured:
        _decode_fulfillment_candidate_wire(raw,inventory,fulfillment_capability_contracts(),owner_preconditions=prerequisites)
    d=captured.value.diagnostics
    assert d['wire_output_fingerprint']==sha256(raw.encode()).hexdigest()
    assert d['violations'][0]['code']=='OBLIGATION_FORMATION_WIRE_JSON_INVALID'
    observed=d['violations'][0]['json_parse_observation']
    assert observed['complete_value_range']==[2,2+len(value)]
    assert observed['complete_value_sha256']==sha256(value.encode()).hexdigest()
    assert observed['disposition']=='UNADMITTED_SYNTAX_OBSERVATION'
    assert any(r['code']=='OBLIGATION_FORMATION_WIRE_FACT_KIND_INVALID' for r in d['violations'])
    assert 'CANONICAL_COMPONENT_VALIDATION' in d['not_evaluable']
    assert 'component_id' not in json.dumps(d)


@pytest.mark.parametrize('malformed', ('incomplete','identity','duplicate-key','schema'))
def test_syntax_observation_cannot_infer_fields_from_invalid_basis(malformed):
    from spg.application.governed_obligations import _owner_source_preconditions
    rev,ir,inventory,plan=controlled_capacity_case()
    prerequisites=_owner_source_preconditions(rev,ir,inventory,fulfillment_capability_contracts())
    wire,_=controlled_wire(inventory,plan,owner_preconditions=prerequisites)
    if malformed=='identity':wire['h']='0'*64
    if malformed=='schema':wire['routes'][0]['f']=['not an ordinal']
    raw=json.dumps(wire)
    if malformed=='incomplete':raw=raw[:-10]
    elif malformed=='duplicate-key':raw='{"v":1,'+raw[1:]+'}'
    else:raw+='}'
    with pytest.raises(_FulfillmentWireValidationError) as captured:
        _decode_fulfillment_candidate_wire(raw,inventory,fulfillment_capability_contracts(),owner_preconditions=prerequisites)
    d=captured.value.diagnostics
    assert not any(r['code']=='OBLIGATION_FORMATION_WIRE_FACT_KIND_INVALID' for r in d['violations'])
    assert 'ACTUAL_OWNER_EVIDENCE' in d['not_evaluable']


def test_legacy_json_failure_diagnostics_are_not_rewritten():
    rev,ir,inventory,plan=controlled_capacity_case()
    from spg.application.governed_obligations import _owner_source_preconditions
    prerequisites=_owner_source_preconditions(rev,ir,inventory,fulfillment_capability_contracts(),include_syntax_observations=False)
    wire,_=controlled_wire(inventory,plan,owner_preconditions=prerequisites)
    with pytest.raises(_FulfillmentWireValidationError) as captured:
        _decode_fulfillment_candidate_wire(json.dumps(wire)+'}',inventory,fulfillment_capability_contracts(),owner_preconditions=prerequisites)
    assert captured.value.diagnostics['violations']==[{'code':'OBLIGATION_FORMATION_WIRE_JSON_INVALID'}]


def invalid_references(wire, inventory):
    """Same failure category as retained outputs, no fixed source ordinals."""
    route = next(r for r in wire['routes'] if inventory['sources'][r['s']]['kind'] == 'WORK_CONTEXT')
    refs = [i for i, s in enumerate(inventory['sources']) if s['kind'] in {'IR_CLAUSE', 'IR_CONSTRAINT'}][:2]
    assert len(refs) == 2
    route['f'] = refs
    return route, refs


def provider_for_case(inventory, plan, *, checkpoint=None, repeat=False):
    calls = []
    def generate(**request):
        payload = json.loads(request['input_text'])
        calls.append(payload)
        if 'untrusted_fulfillment_candidate' in payload:
            restored = decode_review_input(payload)
            output = fixture_review_proof(inventory, restored, review(inventory, restored), payload).model_dump_json()
        else:
            wire, _ = controlled_wire(inventory, plan, feedback=payload.get('same_basis_validation_feedback'), owner_preconditions=payload.get('owner_source_preconditions'))
            if len(calls) == 1 or repeat:
                invalid_references(wire, inventory)
            output = json.dumps(wire, ensure_ascii=False)
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model='controlled-wire-feedback', effective_model='controlled-wire-feedback',
            request_id=f'controlled-wire-feedback-{len(calls)}',
            usage=ModelUsage(input_tokens=100, output_tokens=20, total_tokens=120, unknown=False),
            timing=ModelTiming(), retry_count=0)

    class Provider(ModelFulfillmentCandidateProvider):
        def form(self, *args, receipt_callback=None, **kwargs):
            def observed(**row):
                receipt_callback(**row)
                if checkpoint == 'first-observation' and len(calls) == 1:
                    raise Checkpoint()
                if checkpoint == 'second-observation' and len(calls) == 2:
                    raise Checkpoint()
            return super().form(*args, receipt_callback=observed, **kwargs)
    p = Provider(lambda: SimpleNamespace(generate=generate, close=lambda: None))
    if checkpoint == 'first-validation':
        class Memory(list):
            def append(self, row):
                super().append(row)
                if row['stage'] == 'CANDIDATE_VALIDATED' and row['attempt'] == 1:
                    raise Checkpoint()
        p._fulfillment_receipts = Memory()
    return p, calls


def run_case(revision, ir, inventory, provider):
    return form_fulfillment_projection(revision, ir, provider=provider,
        source_revision=inventory['source_revision'], exact_target_paths=inventory['exact_target_paths'])


@pytest.mark.parametrize('scale', ('small', 'medium', 'complex'))
def test_predecode_feedback_can_reach_a_new_valid_candidate_and_independent_review(scale):
    revision, ir, inventory, plan = controlled_capacity_case(scale)
    frozen = deepcopy(inventory)
    provider, calls = provider_for_case(inventory, plan)
    bindings = run_case(revision, ir, inventory, provider)
    assert len(calls) == 3 and 'untrusted_fulfillment_candidate' in calls[-1]
    assert all(b.state != 'UNRESOLVED' for b in bindings)
    rows = provider._fulfillment_receipts
    failed = next(r for r in rows if r['stage'] == 'CANDIDATE_VALIDATED' and r['attempt'] == 1)
    response = next(r for r in rows if r['stage'] == 'MODEL_RESPONSE_OBSERVED' and r['attempt'] == 1)
    start = next(r for r in rows if r['stage'] == 'MODEL_REQUEST_PENDING' and r['attempt'] == 1)
    next_start = next(r for r in rows if r['stage'] == 'MODEL_REQUEST_PENDING' and r['attempt'] == 2)
    feedback = json.loads(calls[1]['same_basis_validation_feedback'])
    bound = feedback['wire_diagnostic_binding']
    assert failed['candidate'] is None and not failed['validation_passed']
    assert bound['wire_output_fingerprint'] == sha256(response['candidate_output'].encode()).hexdigest()
    assert bound['inventory_fingerprint'] == inventory['inventory_fingerprint'] and bound['attempt'] == 1
    assert bound['request_receipt_id'] == start['receipt_id'] and bound['response_receipt_id'] == response['receipt_id']
    assert next_start['feedback_receipt_id'] == failed['receipt_id']
    assert next_start['feedback'] == failed['validation_feedback'] == calls[1]['same_basis_validation_feedback']
    assert len(feedback['violations']) == 2
    assert all(v['field'] == 'f' and v['expected_kind'] == 'FACT' and v['actual_kind'] in {'IR_CLAUSE','IR_CONSTRAINT'}
               and 'component_id' not in v and 'raw_route_fingerprint' in v for v in feedback['violations'])
    assert inventory == frozen
    before = deepcopy(rows)
    run_case(revision, ir, inventory, provider)
    assert len(calls) == 3 and provider._fulfillment_receipts == before


@pytest.mark.parametrize('checkpoint', ('first-observation', 'first-validation', 'second-observation'))
def test_checkpoint_recovery_reuses_original_output_and_feedback_without_extra_calls(checkpoint):
    revision, ir, inventory, plan = controlled_capacity_case()
    provider, calls = provider_for_case(inventory, plan, checkpoint=checkpoint)
    with pytest.raises(Checkpoint):
        run_case(revision, ir, inventory, provider)
    retained = deepcopy(list(provider._fulfillment_receipts))
    result = run_case(revision, ir, inventory, provider)
    assert all(b.state != 'UNRESOLVED' for b in result) and len(calls) == 3
    for row in retained:
        assert row in provider._fulfillment_receipts
    first_failed = next(r for r in provider._fulfillment_receipts if r['stage'] == 'CANDIDATE_VALIDATED' and r['attempt'] == 1)
    assert calls[1]['same_basis_validation_feedback'] == first_failed['validation_feedback']


@pytest.mark.parametrize('change', ('raw', 'raw-sha', 'raw-bytes', 'inventory', 'attempt',
    'request-receipt', 'response-receipt', 'diagnostic-hash', 'violation', 'feedback',
    'row-work', 'row-revision', 'row-source', 'row-paths', 'missing-diagnostics', 'duplicate-response', 'duplicate-validation',
    'feedback-reorder', 'feedback-sha', 'feedback-bytes', 'missing-feedback-identity'))
def test_feedback_drift_stops_before_another_model_request(change):
    revision, ir, inventory, plan = controlled_capacity_case()
    provider, calls = provider_for_case(inventory, plan, checkpoint='first-validation')
    with pytest.raises(Checkpoint): run_case(revision, ir, inventory, provider)
    rows = provider._fulfillment_receipts
    failed = next(r for r in rows if r['stage'] == 'CANDIDATE_VALIDATED')
    response = next(r for r in rows if r['stage'] == 'MODEL_RESPONSE_OBSERVED')
    diagnostics = failed['predecode_diagnostics']
    if change == 'raw': response['candidate_output'] += ' '
    elif change == 'raw-sha': response['candidate_output_sha256'] = '0'*64
    elif change == 'raw-bytes': response['candidate_output_bytes'] += 1
    elif change == 'inventory': diagnostics['binding']['inventory_fingerprint'] = '0'*64
    elif change == 'attempt': diagnostics['binding']['attempt'] = 2
    elif change == 'request-receipt': diagnostics['binding']['request_receipt_id'] = 'different-request'
    elif change == 'response-receipt': diagnostics['binding']['response_receipt_id'] = 'different-response'
    elif change == 'diagnostic-hash': diagnostics['diagnostic_fingerprint'] = '0'*64
    elif change == 'violation': diagnostics['violations'][0]['referenced_source'] = 0
    elif change == 'feedback': failed['validation_feedback'] += ' '
    elif change == 'feedback-reorder': failed['validation_feedback'] = json.dumps(json.loads(failed['validation_feedback']),sort_keys=True)
    elif change == 'feedback-sha': failed['validation_feedback_sha256']='0'*64
    elif change == 'feedback-bytes': failed['validation_feedback_bytes']+=1
    elif change == 'missing-feedback-identity':
        failed.pop('validation_feedback_sha256'); failed.pop('validation_feedback_bytes')
    elif change == 'missing-diagnostics': failed.pop('predecode_diagnostics')
    elif change == 'duplicate-response': list.append(rows, deepcopy(response))
    elif change == 'duplicate-validation': list.append(rows, deepcopy(failed))
    else:
        field = {'row-work':'work_id','row-revision':'work_reality_revision_id',
                 'row-source':'source_revision','row-paths':'exact_target_paths'}[change]
        failed[field] = ['wrong.html'] if field == 'exact_target_paths' else 'different-owner'
    result = run_case(revision, ir, inventory, provider)
    assert len(calls) == 1 and all(b.state == 'UNRESOLVED' for b in result)
    assert result[0].formation_receipt['terminal_reason'] == 'OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'
    run_case(revision, ir, inventory, provider)
    assert len(calls) == 1


@pytest.mark.parametrize('field', ('feedback', 'feedback_receipt_id'))
def test_second_attempt_cannot_consume_another_feedback_or_receipt(field):
    revision, ir, inventory, plan = controlled_capacity_case()
    provider, calls = provider_for_case(inventory, plan, checkpoint='second-observation')
    with pytest.raises(Checkpoint): run_case(revision, ir, inventory, provider)
    next_start = next(r for r in provider._fulfillment_receipts if r['stage'] == 'MODEL_REQUEST_PENDING' and r['attempt'] == 2)
    next_start[field] += '-different'
    result = run_case(revision, ir, inventory, provider)
    assert len(calls) == 2 and all(b.state == 'UNRESOLVED' for b in result)
    assert result[0].formation_receipt['terminal_reason'] == 'OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'


def test_repeated_invalid_wire_exhausts_existing_budget_and_replay_cannot_reset_it():
    revision, ir, inventory, plan = controlled_capacity_case()
    provider, calls = provider_for_case(inventory, plan, repeat=True)
    result = run_case(revision, ir, inventory, provider)
    assert len(calls) == 2 and all(b.state == 'UNRESOLVED' for b in result)
    rows = provider._fulfillment_receipts
    failed = [r for r in rows if r['stage'] == 'CANDIDATE_VALIDATED']
    assert len(failed) == 2 and failed[-1]['terminal']
    assert failed[0]['predecode_diagnostics']['binding']['attempt'] == 1
    assert failed[1]['predecode_diagnostics']['binding']['attempt'] == 2
    before = deepcopy(rows)
    run_case(revision, ir, inventory, provider)
    assert rows == before and len(calls) == 2
    failed[0]['predecode_diagnostics']['binding']['attempt'] = 2
    replay = run_case(revision, ir, inventory, provider)
    assert len(calls) == 2 and all(b.state == 'UNRESOLVED' for b in replay)
    assert replay[0].formation_receipt['terminal_reason'] == 'OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'


def test_recovery_cannot_replace_raw_output_with_a_repaired_candidate_before_review():
    revision, ir, inventory, plan = controlled_capacity_case()
    provider, calls = provider_for_case(inventory, plan, checkpoint='first-observation')
    with pytest.raises(Checkpoint): run_case(revision, ir, inventory, provider)
    response = next(r for r in provider._fulfillment_receipts if r['stage']=='MODEL_RESPONSE_OBSERVED')
    valid_wire, _ = controlled_wire(inventory, plan)
    response['candidate_output'] = json.dumps(valid_wire, ensure_ascii=False)
    result = run_case(revision, ir, inventory, provider)
    assert len(calls) == 1 and all(b.state == 'UNRESOLVED' for b in result)
    assert result[0].formation_receipt['terminal_reason'] == 'OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'


def test_predecode_collects_independent_errors_and_coverage_without_admitting_components():
    _, _, inventory, plan = controlled_capacity_case('medium')
    wire, _ = controlled_wire(inventory, plan)
    invalid_references(wire, inventory)
    wire['routes'][0]['t'] = [-1, len(inventory['exact_target_paths'])]
    wire['routes'][0]['z'] -= 1
    raw = json.dumps(wire, ensure_ascii=False)
    before = deepcopy(wire)
    with pytest.raises(_FulfillmentWireValidationError) as caught:
        _decode_fulfillment_candidate_wire(raw, inventory, fulfillment_capability_contracts())
    diag = caught.value.diagnostics
    codes = {row['code'] for row in diag['violations']}
    assert {'OBLIGATION_FORMATION_WIRE_FACT_KIND_INVALID','OBLIGATION_FORMATION_WIRE_TARGET_INDEX_INVALID',
            'OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST'} <= codes
    assert diag['wire_output_fingerprint'] == sha256(raw.encode()).hexdigest()
    assert 'OWNER_PHASE_EVIDENCE' in diag['not_evaluable']
    assert 'candidate' not in diag and 'component_id' not in json.dumps(diag)
    assert wire == before


def test_explicit_quote_needing_locator_does_not_produce_a_false_raw_coverage_failure():
    _, _, inventory, plan = controlled_capacity_case()
    wire, _ = controlled_wire(inventory, plan)
    invalid_references(wire, inventory)
    wire['routes'][0]['q'] = plan.routes[0].component_basis.source_component_quote
    wire['routes'][0]['a'] += 1
    with pytest.raises(_FulfillmentWireValidationError) as caught:
        _decode_fulfillment_candidate_wire(json.dumps(wire), inventory, fulfillment_capability_contracts())
    diag = caught.value.diagnostics
    assert wire['routes'][0]['s'] in diag['coverage_not_evaluable_sources']
    assert not any(v['code']=='OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST' and v['source']==wire['routes'][0]['s']
                   for v in diag['violations'])


def test_diagnostic_error_set_remains_bounded_and_does_not_echo_candidate_prose():
    _, _, inventory, plan = controlled_capacity_case()
    wire, _ = controlled_wire(inventory, plan)
    route, _ = invalid_references(wire, inventory)
    wire['routes'] += [deepcopy(route) for _ in range(40)]
    for r in wire['routes']: r['r'] = 'PRIVATE_CANDIDATE_PROSE'
    with pytest.raises(_FulfillmentWireValidationError) as caught:
        _decode_fulfillment_candidate_wire(json.dumps(wire), inventory, fulfillment_capability_contracts())
    diag = caught.value.diagnostics
    assert len(diag['violations']) == 64 and diag['additional_violation_count'] > 0
    assert 'PRIVATE_CANDIDATE_PROSE' not in json.dumps(diag)
    assert canonical_fingerprint(_fulfillment_wire_schema()) == '5668e226eb8d38c0f4bf9004ea8fc7aa363e9d388f64927783252f562d78ad40'
