"""Repair sees the original untrusted proposal; no intelligent success claim."""
from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from spg.application.governed_obligations import form_fulfillment_projection
from spg.domain.governed_obligation import FulfillmentProjectionCandidate
from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case, controlled_wire
from tests.test_c3_semantic_contract_calibration import review


class Checkpoint(BaseException):
    pass


def repair_case(scale='small', interrupt=False):
    revision, ir, inventory, plan = controlled_capacity_case(scale)
    calls, wires = [], []
    def generate(**request):
        payload = json.loads(request['input_text'])
        calls.append(payload)
        if 'untrusted_fulfillment_candidate' in payload:
            candidate = FulfillmentProjectionCandidate.model_validate(payload['untrusted_fulfillment_candidate'])
            output = review(inventory, candidate).model_dump_json()
        else:
            domains = payload['temporary_wire']['f_allowed_source_ordinals']
            assert domains == [i for i, s in enumerate(inventory['sources']) if s['kind'] == 'FACT']
            feedback = payload.get('same_basis_validation_feedback')
            wire, _ = controlled_wire(inventory, plan, feedback=feedback, owner_preconditions=payload.get("owner_source_preconditions"))
            if feedback is None:
                wire['routes'].append(deepcopy(wire['routes'][0]))
            else:
                data = json.loads(feedback)
                assert data['untrusted_previous_wire'] == wires[0]
                assert json.loads(wires[0])['routes'][-1] == json.loads(wires[0])['routes'][0]
                binding = data['repair_feedback_binding']
                assert binding['wire_output_fingerprint'] == sha256(wires[0].encode()).hexdigest()
                assert binding['inventory_fingerprint'] == inventory['inventory_fingerprint']
                assert binding['candidate_fingerprint'] is not None
                assert data['primary_error'] == 'OBLIGATION_PROJECTION_DUPLICATE_ROUTE'
            output = json.dumps(wire, ensure_ascii=False)
            wires.append(output)
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model='controlled-repair-context', effective_model='controlled-repair-context',
            request_id=f'controlled-repair-{len(calls)}', usage=ModelUsage(), timing=ModelTiming(), retry_count=0)
    provider = ModelFulfillmentCandidateProvider(lambda: SimpleNamespace(generate=generate, close=lambda: None))
    if interrupt:
        class Memory(list):
            def append(self, row):
                super().append(row)
                if row['stage'] == 'CANDIDATE_VALIDATED' and row['attempt'] == 1:
                    raise Checkpoint()
        provider._fulfillment_receipts = Memory()
    def run():
        return form_fulfillment_projection(revision, ir, provider=provider,
            source_revision=inventory['source_revision'], exact_target_paths=inventory['exact_target_paths'])
    return provider, calls, wires, run


@pytest.mark.parametrize('scale', ('small','medium','complex'))
def test_bound_original_proposal_is_available_to_one_repair_and_independent_review(scale):
    provider, calls, wires, run = repair_case(scale)
    result = run()
    assert len(calls) == 3 and all(b.state != 'UNRESOLVED' for b in result)
    rows = provider._fulfillment_receipts
    failed = next(r for r in rows if r['stage'] == 'CANDIDATE_VALIDATED' and r['attempt'] == 1)
    start = next(r for r in rows if r['stage'] == 'MODEL_REQUEST_PENDING' and r['attempt'] == 2)
    assert start['feedback_receipt_id'] == failed['receipt_id']
    frozen = deepcopy(rows)
    run()
    assert len(calls) == 3 and rows == frozen


@pytest.mark.parametrize('tamper', ('wire','binding','candidate','feedback-parent','remove-context','invalid-json','predicate'))
def test_original_proposal_or_feedback_identity_drift_stops_before_another_request(tamper):
    provider, calls, wires, run = repair_case(interrupt=True)
    with pytest.raises(Checkpoint): run()
    provider._fulfillment_receipts = list(provider._fulfillment_receipts)
    rows = provider._fulfillment_receipts
    failed = next(r for r in rows if r['stage'] == 'CANDIDATE_VALIDATED')
    payload = json.loads(failed['validation_feedback'])
    if tamper == 'wire': payload['untrusted_previous_wire'] += ' '
    elif tamper == 'binding': payload['repair_feedback_binding']['response_receipt_id'] = 'wrong-original'
    elif tamper == 'candidate': failed['candidate']['routes'][0]['rationale'] = 'substituted'
    elif tamper == 'remove-context':
        payload.pop('repair_feedback_binding');payload.pop('untrusted_previous_wire')
    elif tamper == 'predicate': failed['failed_predicate'] = 'OBLIGATION_DIFF_SCOPE_INCOMPLETE'
    elif tamper == 'feedback-parent': payload.pop('repair_feedback_binding')
    failed['validation_feedback'] = '{' if tamper == 'invalid-json' else json.dumps(payload, separators=(',',':'))
    result = run()
    assert len(calls) == 1 and all(b.state == 'UNRESOLVED' for b in result)
    assert result[0].formation_receipt['terminal_reason'] == 'OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'
