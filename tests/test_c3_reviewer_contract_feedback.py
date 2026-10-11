"""Existing second critic consumes only bound, recomputed contract failures."""
from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from spg.application import governed_obligations as a
from spg.providers import fulfillment_candidate as p
from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
from tests.test_c3_fulfillment_capacity_representation import (
    controlled_capacity_case, controlled_wire, decode_review_input)
from tests.test_c3_semantic_contract_calibration import review
from tests.test_c3_source_consumption_proof import fixture_review_proof
from tests.test_c3_fulfillment_wire_feedback import Checkpoint


def run_case(*, checkpoint=False, semantic_only=False):
    rev, ir, inv, plan = controlled_capacity_case()
    calls = []
    def generate(**request):
        payload = json.loads(request['input_text'])
        calls.append(payload)
        if 'untrusted_fulfillment_candidate' in payload:
            current = decode_review_input(payload)
            result = fixture_review_proof(inv, current, review(inv, current), payload).model_dump(mode='json')
            if len(calls) == 2:
                if semantic_only:
                    result['source_results'][0]['complete_and_equivalent'] = False
                else:
                    result['source_results'][0]['consumption_checks'].append(
                        deepcopy(result['source_results'][0]['consumption_checks'][0]))
            output = json.dumps(result)
        else:
            wire, _ = controlled_wire(inv, plan,
                feedback=payload.get('same_basis_validation_feedback'),
                owner_preconditions=payload.get('owner_source_preconditions'))
            output = json.dumps(wire)
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model='controlled-critic', effective_model='controlled-critic',
            request_id='controlled-critic-'+str(len(calls)),
            usage=ModelUsage(input_tokens=100, output_tokens=20, total_tokens=120, unknown=False),
            timing=ModelTiming(), retry_count=0)
    class Provider(p.ModelFulfillmentCandidateProvider):
        def review(self, *args, capabilities, receipt_callback=None, review_feedback=None,
                   owner_preconditions=None, **kwargs):
            def observed(**row):
                receipt_callback(**row)
                if checkpoint and len(calls) == 4:
                    raise Checkpoint()
            return super().review(*args, receipt_callback=observed,
                review_feedback=review_feedback, capabilities=capabilities,
                owner_preconditions=owner_preconditions, **kwargs)
    provider = Provider(lambda: SimpleNamespace(generate=generate, close=lambda: None))
    def execute():
        return a.form_fulfillment_projection(rev, ir, provider=provider,
            source_revision=inv['source_revision'], exact_target_paths=inv['exact_target_paths'])
    return rev, ir, inv, provider, calls, execute


def test_existing_second_critic_receives_rejected_checks_with_both_exact_identities():
    rev, ir, inv, provider, calls, execute = run_case()
    result = execute()
    assert all(b.state != 'UNRESOLVED' for b in result), result[0].formation_receipt.get('terminal_reason')
    assert len(calls) == 4  # Two Formation, two independent Review, no new slot.
    bound = calls[3]['existing_bound_reviewer_feedback']
    assert bound['previous_formation_wire_binding']['attempt'] == 1
    assert bound['current_formation_wire_binding']['attempt'] == 2
    assert bound['previous_review_binding']['review_output_sha256']
    assert {r['code'] for r in bound['rejected_previous_mechanical_checks']} == {
        'OBLIGATION_SOURCE_CONSUMPTION_DUPLICATE'}
    assert 'review' not in bound['previous_review_binding']
    rows = provider._fulfillment_receipts
    pending = next(r for r in rows if r['stage'] == 'SEMANTIC_REVIEW_PENDING' and r['attempt'] == 2)
    observed = next(r for r in rows if r['stage'] == 'SEMANTIC_REVIEW_OBSERVED' and r['attempt'] == 2)
    assert pending['review_repair_context'] == bound
    assert observed['model']['review_repair_context_fingerprint'] == pending['review_repair_context_fingerprint']
    a._validate_review_repair_receipts(rows, rev, inv, a.fulfillment_capability_contracts())


def test_semantic_disagreement_is_not_rewritten_as_a_critic_contract_defect():
    _, _, _, provider, calls, execute = run_case(semantic_only=True)
    execute()
    assert len(calls) == 4
    assert 'existing_bound_reviewer_feedback' not in calls[3]
    assert not any(r.get('review_repair_context') for r in provider._fulfillment_receipts)


@pytest.mark.parametrize('change', ('context', 'fingerprint', 'wire', 'inventory',
    'attempt', 'receipt', 'review-wire', 'observed-context', 'model-context', 'missing-context'))
def test_feedback_drift_stops_recovery_without_another_call(change):
    rev, ir, inv, provider, calls, execute = run_case(checkpoint=True)
    with pytest.raises(Checkpoint): execute()
    assert len(calls) == 4
    rows = provider._fulfillment_receipts
    pending = next(r for r in rows if r['stage'] == 'SEMANTIC_REVIEW_PENDING' and r['attempt'] == 2)
    observed = next(r for r in rows if r['stage'] == 'SEMANTIC_REVIEW_OBSERVED' and r['attempt'] == 2)
    context = pending['review_repair_context']
    if change == 'context': context['rejected_previous_mechanical_checks'][0]['code'] = 'INVENTED'
    elif change == 'fingerprint': pending['review_repair_context_fingerprint'] = '0'*64
    elif change == 'wire': context['previous_formation_wire_binding']['wire_output_fingerprint'] = '0'*64
    elif change == 'inventory': context['current_formation_wire_binding']['inventory_fingerprint'] = '0'*64
    elif change == 'attempt': context['previous_formation_wire_binding']['attempt'] = 2
    elif change == 'receipt': context['previous_feedback_receipt_id'] = 'invented'
    elif change == 'review-wire': context['previous_review_binding']['review_output_sha256'] = '0'*64
    elif change == 'observed-context': observed['review_repair_context_fingerprint'] = '0'*64
    elif change == 'model-context': observed['model']['review_repair_context_fingerprint'] = '0'*64
    elif change == 'missing-context':
        pending.pop('review_repair_context'); pending.pop('review_repair_context_fingerprint')
    with pytest.raises(p._FulfillmentWireReceiptIdentityError, match='FEEDBACK_IDENTITY_DRIFT'):
        a._validate_review_repair_receipts(rows, rev, inv, a.fulfillment_capability_contracts())
    assert len(calls) == 4
    result = execute()
    assert all(b.state == 'UNRESOLVED' for b in result)
    assert result[0].formation_receipt['terminal_reason'] == 'OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'
    assert len(calls) == 4


def test_observed_second_critic_replay_reuses_the_exact_input_without_new_call():
    _, _, _, provider, calls, execute = run_case(checkpoint=True)
    with pytest.raises(Checkpoint): execute()
    before = deepcopy(provider._fulfillment_receipts)
    result = execute()
    assert all(b.state != 'UNRESOLVED' for b in result)
    assert len(calls) == 4
    assert provider._fulfillment_receipts[:len(before)] == before


def test_content_contract_exposes_actual_consumer_without_claiming_performed_evidence():
    contracts = p._existing_consumer_contracts(a.fulfillment_capability_contracts())
    content = next(c for c in contracts if c['capability'] == 'ARTIFACT_CONTENT')
    projection = content['source_evidence_contract']
    assert projection['direct_source_without_linked_facts'] is True
    assert 'STATIC_STRUCTURE' in projection['planned_checks']
    assert 'REQUESTED_IMPLEMENTATION_OUTCOME' in projection['planned_checks']
    assert projection['page_equals_file'] == 'NOT_ASSUMED'
    assert content['actual_evidence_present'] is False
    assert any(c['callable'].endswith('StaticProtectedContextVerifier.verify') for c in content['consumer_sources'])


def test_v2_output_schema_rejects_duplicate_check_and_duplicate_route_identity():
    _, _, inv, plan = controlled_capacity_case()
    schema = p._review_output_schema(inv, plan, route_scoped=True,
        source_consumption=True, consumer_operand_checks=True)
    checks = schema['properties']['source_results']['prefixItems'][0]['properties']['consumption_checks']
    assert checks['uniqueItems'] is True
    assert checks['items']['properties']['route_indices']['uniqueItems'] is True
