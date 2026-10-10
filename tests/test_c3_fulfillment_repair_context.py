"""Repair sees the original untrusted proposal; no intelligent success claim."""
from copy import deepcopy
from tests.test_c3_fulfillment_capacity_representation import decode_review_input
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
            candidate = decode_review_input(payload)
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


def semantic_repair_case(interrupt=False):
    from tests.test_c3_semantic_contract_calibration import negative_fact_plan
    revision, ir, inventory, plan = negative_fact_plan()
    extra = tuple(r.model_copy(update={'capability': 'DENY_PREVIEW'}) for r in plan.routes
        if r.capability == 'DENY_DEPLOY')
    bad = plan.model_copy(update={'routes': (*plan.routes, *extra)})
    from spg.application.governed_obligations import validate_projection_candidate
    validate_projection_candidate(bad, revision, ir, inventory, allow_review_pending=True)
    calls = []
    def generate(**request):
        payload = json.loads(request['input_text']); calls.append(payload)
        if 'untrusted_fulfillment_candidate' in payload:
            candidate = decode_review_input(payload)
            verdict = review(inventory, candidate)
            verdict = verdict.model_copy(update={'component_results': tuple(row.model_copy(update={
                'complete_and_equivalent': False, 'owner_phase_evidence_valid': False,
                'reason': 'External release prohibition does not entail denying local artifact inspection.'})
                if row.capability == 'DENY_PREVIEW' else row for row in verdict.component_results)})
            output = verdict.model_dump_json()
        else:
            feedback = payload.get('same_basis_validation_feedback')
            if feedback:
                feedback = json.loads(feedback)
                rejected = [v for v in feedback['violations'] if v.get('capability') == 'DENY_PREVIEW']
                assert len(rejected) == len(extra) and all(v['review_reason'] for v in rejected)
                assert 'INDEPENDENT_SEMANTIC_REVIEW' not in feedback['not_evaluable']
                assert feedback['semantic_review_feedback_binding']['attempt'] == 1
            wire, _ = controlled_wire(inventory, plan if feedback else bad,
                feedback=payload.get('same_basis_validation_feedback'), owner_preconditions=payload.get('owner_source_preconditions'))
            output = json.dumps(wire)
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model='controlled-semantic-repair', effective_model='controlled-semantic-repair',
            request_id=f'controlled-semantic-{len(calls)}', usage=ModelUsage(), timing=ModelTiming(), retry_count=0)
    provider = ModelFulfillmentCandidateProvider(lambda: SimpleNamespace(generate=generate, close=lambda: None))
    if interrupt:
        class Memory(list):
            def append(self, row):
                super().append(row)
                if row['stage'] == 'CANDIDATE_VALIDATED' and row['attempt'] == 1: raise Checkpoint()
        provider._fulfillment_receipts = Memory()
    def run():
        return form_fulfillment_projection(revision, ir, provider=provider,
            source_revision=inventory['source_revision'], exact_target_paths=inventory['exact_target_paths'])
    return provider, calls, run


def test_independent_semantic_rejection_reaches_bound_feedback_and_replay():
    provider, calls, run = semantic_repair_case()
    result = run()
    assert len(calls) == 4 and all(b.state != 'UNRESOLVED' for b in result)
    assert not any(b.component == 'preview' for b in result)
    rows = deepcopy(provider._fulfillment_receipts)
    run()
    assert len(calls) == 4 and provider._fulfillment_receipts == rows


@pytest.mark.parametrize('tamper', ('review-output', 'review-verdict', 'review-parent', 'review-identity', 'remove-marker', 'reason'))
def test_semantic_review_feedback_identity_drift_stops_without_new_call(tamper):
    provider, calls, run = semantic_repair_case(interrupt=True)
    with pytest.raises(Checkpoint): run()
    provider._fulfillment_receipts = list(provider._fulfillment_receipts)
    rows = provider._fulfillment_receipts
    failed = next(r for r in rows if r['stage'] == 'CANDIDATE_VALIDATED')
    feedback = json.loads(failed['validation_feedback'])
    if tamper == 'review-output': next(r for r in rows if r['stage'] == 'SEMANTIC_REVIEW_OBSERVED')['review_output'] += ' '
    elif tamper == 'review-verdict': next(r for r in rows if r['stage'] == 'SEMANTIC_REVIEW_VALIDATED')['semantic_review']['component_results'][0]['reason'] = 'drift'
    elif tamper == 'review-identity': next(r for r in rows if r['stage'] == 'SEMANTIC_REVIEW_PENDING')['candidate_fingerprint'] = '0'*64
    elif tamper == 'review-parent': feedback['semantic_review_feedback_binding']['observed_receipt_id'] = 'wrong-review'
    elif tamper == 'remove-marker': failed.pop('semantic_feedback_contract'); feedback.pop('semantic_review_feedback_binding')
    else: next(v for v in feedback['violations'] if 'review_reason' in v)['review_reason'] = 'different feedback'
    failed['validation_feedback'] = json.dumps(feedback, separators=(',',':'))
    result = run()
    assert len(calls) == 2 and all(b.state == 'UNRESOLVED' for b in result)
    assert result[0].formation_receipt['terminal_reason'] == 'OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'


def test_consumer_semantics_are_existing_tool_contracts_not_subject_aliases():
    from spg.providers.fulfillment_candidate import _existing_consumer_contracts
    from spg.application.governed_obligations import fulfillment_capability_contracts
    from spg.executor.tools import PUBLIC_NATIVE_TOOL_CONTRACTS
    contracts = _existing_consumer_contracts(fulfillment_capability_contracts())
    assert len(contracts) == 1
    tool = next(t for t in PUBLIC_NATIVE_TOOL_CONTRACTS if t['identity'] == 'preview.inspect')
    assert contracts[0]['tool_contract'] == tool


@pytest.mark.parametrize('scale', ('small', 'medium', 'complex'))
def test_critic_comparison_table_is_exact_and_does_not_infer_semantic_verdicts(scale):
    from spg.providers.fulfillment_candidate import _review_component_table
    from spg.application.governed_obligations import fulfillment_capability_contracts
    from spg.domain.governed_obligation import fulfillment_component_id
    revision, ir, inventory, plan = controlled_capacity_case(scale)
    rows = _review_component_table(inventory, plan, fulfillment_capability_contracts())
    assert len(rows) == len(plan.routes)
    for ordinal, (row, route) in enumerate(zip(rows, plan.routes, strict=True)):
        assert row['route'] == ordinal and row['source_ref'] == route.source_ref
        assert row['component_id'] == fulfillment_component_id(route, inventory['inventory_fingerprint'])
        assert row['original_component_text'] == route.component_basis.source_component_quote
        assert row['source_span'] == [route.component_basis.source_span_start, route.component_basis.source_span_end]
        assert row['target_paths'] == list(route.target_paths)
        assert 'rationale' not in row and 'passed' not in row


def test_critic_comparison_cannot_display_a_substituted_source_quote():
    from spg.providers.fulfillment_candidate import _review_component_table, _FulfillmentWireReceiptIdentityError
    from spg.application.governed_obligations import fulfillment_capability_contracts
    _, _, inventory, plan = controlled_capacity_case()
    first, *rest = plan.routes
    changed = first.model_copy(update={'component_basis': first.component_basis.model_copy(update={'source_component_quote': 'invented'})})
    with pytest.raises(_FulfillmentWireReceiptIdentityError, match='INPUT_IDENTITY_DRIFT'):
        _review_component_table(inventory, plan.model_copy(update={'routes': (changed, *rest)}), fulfillment_capability_contracts())


@pytest.mark.parametrize('scale', ('small', 'medium', 'complex'))
def test_generation_schema_enforces_original_identity_domains_without_new_wire_version(scale):
    from spg.providers.fulfillment_candidate import _formation_output_schema, _fulfillment_wire_schema
    from spg.application.governed_obligations import fulfillment_capability_contracts
    from spg.domain.governed_obligation import canonical_fingerprint
    _, _, inventory, _ = controlled_capacity_case(scale)
    contracts = fulfillment_capability_contracts()
    original = deepcopy(_fulfillment_wire_schema())
    schema = _formation_output_schema(inventory, contracts)
    props = schema['$defs']['_FulfillmentCompactRoute']['properties']
    assert props['s']['enum'] == list(range(len(inventory['sources'])))
    assert props['c']['enum'] == list(range(len(contracts)))
    assert props['f']['items']['enum'] == [i for i,s in enumerate(inventory['sources']) if s['kind'] == 'FACT']
    assert props['u']['items']['enum'] == props['s']['enum']
    assert props['t']['items']['enum'] == list(range(len(inventory['exact_target_paths'])))
    assert schema['properties']['v'] == original['properties']['v']
    assert _fulfillment_wire_schema() == original
    assert canonical_fingerprint(schema) != canonical_fingerprint(original)


def test_generation_schema_no_fact_domain_requires_empty_f_not_a_new_index_space():
    from spg.providers.fulfillment_candidate import _formation_output_schema
    from spg.application.governed_obligations import fulfillment_capability_contracts, fulfillment_inventory
    revision, ir, _, _ = controlled_capacity_case()
    revision.engineering_semantic_facts = ()
    inventory = fulfillment_inventory(revision, ir)
    props = _formation_output_schema(inventory, fulfillment_capability_contracts())['$defs']['_FulfillmentCompactRoute']['properties']
    assert props['f']['maxItems'] == 0 and 'enum' not in props['f']['items']
