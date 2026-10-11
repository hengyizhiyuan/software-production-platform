"""Existing bounded repair requests; fixtures do not establish live convergence."""
from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from spg.application import governed_obligations as app
from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
from tests.test_c3_fulfillment_capacity_representation import (
    controlled_capacity_case, controlled_wire, decode_review_input,
)
from tests.test_c3_semantic_contract_calibration import review
from tests.test_c3_source_consumption_proof import fixture_review_proof


@pytest.mark.parametrize('seal', (False, True))
@pytest.mark.parametrize('second', ('repaired', 'repeat', 'invalid-source', 'unauthorized-path'))
def test_existing_feedback_reaches_repair_request_without_rewriting_candidate(second, seal):
    rev, ir, inventory, plan = controlled_capacity_case()
    if seal:
        # The same original future clause explicitly preserves both Human
        # integration and a reviewable Candidate; never replace either gate.
        plan = plan.model_copy(update={'routes': (*plan.routes, *(route.model_copy(
            update={'capability': 'CANDIDATE_SEAL'}) for route in plan.routes
            if route.capability == 'HUMAN_INTEGRATION'))})
    original = deepcopy((rev, ir, inventory, plan))
    requests = []
    caps = app.fulfillment_capability_contracts()
    contexts = {i for i, source in enumerate(inventory['sources']) if source['kind'] == 'WORK_CONTEXT'}
    future = next(i for i, source in enumerate(inventory['sources'])
        if source['kind'] == 'WORK_CONSTRAINT' and source['index'] == 1)

    def generate(**request):
        payload = json.loads(request['input_text'])
        requests.append((request, payload))
        if 'untrusted_fulfillment_candidate' in payload:
            candidate = decode_review_input(payload)
            output = fixture_review_proof(inventory, candidate, review(inventory, candidate), payload).model_dump_json()
        else:
            feedback = payload['same_basis_validation_feedback']
            wire, _ = controlled_wire(inventory, plan, feedback=feedback,
                owner_preconditions=payload['owner_source_preconditions'])
            if feedback is None:
                assert not request['instructions'].startswith('This is the existing bounded REPAIR request')
            else:
                assert request['instructions'].startswith('This is the existing bounded REPAIR request')
                data = json.loads(feedback)
                all_errors = json.dumps(data)
                assert 'OBLIGATION_SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN' in all_errors
                assert 'OBLIGATION_CONTEXT_CANNOT_AUTHORIZE_EFFECT' in all_errors
                assert data['repair_feedback_binding']['inventory_fingerprint'] == inventory['inventory_fingerprint']
                # The complete original feedback remains a string, not a new view,
                # a selected repair operand, or an automatically patched response.
                assert isinstance(feedback, str)
            if feedback is None or second == 'repeat':
                for route in wire['routes']:
                    if route['s'] == future:
                        route['u'] = []
                    if route['s'] in contexts:
                        route['c'] = next(i for i, c in enumerate(caps) if c['capability'] == 'ARTIFACT_CONTENT')
                        route['t'] = [0]
            elif second == 'invalid-source':
                wire['routes'][0]['u'] = [len(inventory['sources'])]
            elif second == 'unauthorized-path':
                wire['routes'][0]['t'] = [len(inventory['exact_target_paths'])]
            output = json.dumps(wire, ensure_ascii=False)
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model='controlled-repair', effective_model='controlled-repair',
            request_id=f'controlled-repair-{len(requests)}', usage=ModelUsage(unknown=True),
            timing=ModelTiming(), retry_count=0)

    provider = ModelFulfillmentCandidateProvider(lambda: SimpleNamespace(generate=generate, close=lambda: None))
    kwargs = dict(provider=provider, exact_target_paths=inventory['exact_target_paths'])
    bindings = app.form_fulfillment_projection(rev, ir, **kwargs)
    assert len(requests) == (3 if second == 'repaired' else 2)
    assert all(b.state != 'UNRESOLVED' for b in bindings) == (second == 'repaired')
    failed = next(r for r in provider._fulfillment_receipts
        if r['stage'] == 'CANDIDATE_VALIDATED' and r['attempt'] == 1)
    assert requests[1][1]['same_basis_validation_feedback'] == failed['validation_feedback']
    assert requests[0][0]['output_schema'] != requests[1][0]['output_schema']  # exact new request header
    for row in provider._fulfillment_receipts:
        if row['stage'] != 'MODEL_RESPONSE_OBSERVED':
            continue
        request, payload = requests[row['attempt'] - 1]
        assert row['model']['generation_input_sha256'] == sha256(request['input_text'].encode()).hexdigest()
        assert row['model']['generation_instructions_sha256'] == sha256(request['instructions'].encode()).hexdigest()
        feedback = payload['same_basis_validation_feedback']
        assert row['model']['validation_feedback_sha256'] == (
            sha256(feedback.encode()).hexdigest() if feedback is not None else None)
    assert (rev, ir, inventory, plan) == original
    receipts = deepcopy(provider._fulfillment_receipts)
    app.form_fulfillment_projection(rev, ir, **kwargs)
    assert len(requests) == (3 if second == 'repaired' else 2)
    assert provider._fulfillment_receipts == receipts
