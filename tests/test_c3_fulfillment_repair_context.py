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


def incomplete_case(*, remains_unresolved=False, authority_unknown=False, interrupt=False):
    from spg.application.governed_obligations import fulfillment_inventory
    from spg.domain.engineering_semantics import SemanticEpistemicStatus
    revision, ir, inventory, plan = controlled_capacity_case('small')
    if authority_unknown:
        revision.engineering_semantic_facts = tuple(f.model_copy(update={
            'epistemic_status': SemanticEpistemicStatus.UNRESOLVED}) for f in revision.engineering_semantic_facts)
        inventory = fulfillment_inventory(revision, ir, source_revision=inventory['source_revision'],
            exact_target_paths=inventory['exact_target_paths'])
        plan = plan.model_copy(update={'inventory_fingerprint': inventory['inventory_fingerprint']})
    pending = plan.model_copy(update={'routes': tuple(r.model_copy(update={
        'capability': 'UNRESOLVED', 'target_paths': (), 'supporting_source_refs': ()})
        if r.source_ref.startswith('semantic-fact:') else r for r in plan.routes)})
    calls, wires = [], []
    def generate(**request):
        payload = json.loads(request['input_text']);calls.append(payload)
        if 'untrusted_fulfillment_candidate' in payload:
            output = review(inventory, decode_review_input(payload)).model_dump_json()
        else:
            feedback = payload.get('same_basis_validation_feedback')
            selected = pending if feedback is None or remains_unresolved else plan
            if feedback is not None:
                data = json.loads(feedback)
                assert data['completion_observation_contract'] == 'existing-bounded-completion-feedback-v1'
                assert any(v['code'] == 'OBLIGATION_PROJECTION_UNRESOLVED' for v in data['violations'])
                assert data['repair_feedback_binding']['wire_output_fingerprint'] == sha256(wires[0].encode()).hexdigest()
                assert data['repair_feedback_binding']['completion_feedback_contract'] == 'existing-bounded-completion-feedback-v1'
            wire, _ = controlled_wire(inventory, selected, feedback=feedback,
                owner_preconditions=payload.get('owner_source_preconditions'))
            output = json.dumps(wire);wires.append(output)
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model='controlled-incomplete-plan', effective_model='controlled-incomplete-plan',
            request_id=f'controlled-incomplete-{len(calls)}', usage=ModelUsage(), timing=ModelTiming(), retry_count=0)
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
    return provider, calls, wires, run


def test_incomplete_legal_candidate_can_use_one_existing_feedback_and_replay_never_reexecutes():
    provider, calls, wires, run = incomplete_case()
    result = run()
    assert all(b.state != 'UNRESOLVED' for b in result)
    assert len(wires) == 2 and len(calls) == 4
    assert result[0].formation_receipt['attempt_count'] == 2
    frozen = deepcopy(provider._fulfillment_receipts)
    run()
    assert provider._fulfillment_receipts == frozen and len(calls) == 4


def test_second_incomplete_candidate_stops_without_budget_reset():
    provider, calls, wires, run = incomplete_case(remains_unresolved=True)
    result = run()
    assert all(b.state == 'UNRESOLVED' for b in result)
    assert result[0].formation_receipt['terminal_reason'] == 'OBLIGATION_PROJECTION_UNRESOLVED'
    assert len(wires) == 2 and len(calls) == 4
    frozen = deepcopy(provider._fulfillment_receipts)
    run();assert len(calls) == 4 and provider._fulfillment_receipts == frozen


def test_real_unknown_authority_does_not_open_probability_repair_slot():
    provider, calls, wires, run = incomplete_case(authority_unknown=True)
    result = run()
    assert all(b.state == 'UNRESOLVED' for b in result)
    assert result[0].formation_receipt['terminal_reason'] == 'UNRESOLVED_BINDING'
    assert len(wires) == 1 and len(calls) == 2


@pytest.mark.parametrize('tamper', ('pending-only', 'both-records', 'feedback-policy', 'wire-output'))
def test_incomplete_feedback_contract_drift_stops_before_repair_call(tamper):
    provider, calls, wires, run = incomplete_case(interrupt=True)
    with pytest.raises(Checkpoint):run()
    provider._fulfillment_receipts = list(provider._fulfillment_receipts)
    start = next(r for r in provider._fulfillment_receipts if r['stage'] == 'MODEL_REQUEST_PENDING')
    if tamper in ('pending-only', 'both-records'):
        del start['completion_feedback_contract']
        if tamper == 'both-records':
            next(r for r in provider._fulfillment_receipts if r['stage'] == 'MODEL_RESPONSE_OBSERVED').pop('completion_feedback_contract')
    elif tamper == 'wire-output':
        next(r for r in provider._fulfillment_receipts if r['stage'] == 'MODEL_RESPONSE_OBSERVED')['candidate_output'] += ' '
    else:
        row = next(r for r in provider._fulfillment_receipts if r['stage'] == 'CANDIDATE_VALIDATED')
        feedback = json.loads(row['validation_feedback'])
        feedback.pop('completion_observation_contract')
        row['validation_feedback'] = json.dumps(feedback)
    result = run()
    assert all(b.state == 'UNRESOLVED' for b in result)
    assert result[0].formation_receipt['terminal_reason'] == 'OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'
    assert len(wires) == 1 and len(calls) == 2


def test_incomplete_feedback_checkpoint_resumes_only_remaining_calls_on_original_basis():
    provider, calls, wires, run = incomplete_case(interrupt=True)
    with pytest.raises(Checkpoint): run()
    frozen = deepcopy(list(provider._fulfillment_receipts))
    provider._fulfillment_receipts = list(provider._fulfillment_receipts)
    result = run()
    assert all(b.state != 'UNRESOLVED' for b in result)
    assert len(wires) == 2 and len(calls) == 4
    assert provider._fulfillment_receipts[:len(frozen)] == frozen
    assert result[0].formation_receipt['attempt_count'] == 2


def repair_case(scale='small', interrupt=False, coverage_failure=False, predecode_coverage_failure=False):
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
                if coverage_failure:
                    ordinal = next(i for i, s in enumerate(inventory['sources'])
                        if s.get('clause_id') == 'original-clause')
                    from spg.domain.governed_obligation import fulfillment_source_semantic_text
                    original = fulfillment_source_semantic_text(inventory['sources'][ordinal])
                    for row in wire['routes']:
                        if row['s'] == ordinal:
                            # Raw geometry differs: the existing unique-quote
                            # locator must run before coverage is evaluable.
                            row['a'] = 1 if predecode_coverage_failure else 0
                            row['q'] = original[1:]
                else:
                    wire['routes'].append(deepcopy(wire['routes'][0]))
            else:
                data = json.loads(feedback)
                assert data['untrusted_previous_wire'] == wires[0]
                if coverage_failure:
                    if not predecode_coverage_failure:
                        assert data['coverage_observation_contract'] == 'existing-located-coverage-feedback-v1'
                    gap = next(v for v in data['violations'] if 'uncovered_codepoint_ranges' in v)
                    assert gap['uncovered_codepoint_ranges'] == [[0, 1]]
                    assert data['primary_error'] == 'OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST'
                else:
                    assert json.loads(wires[0])['routes'][-1] == json.loads(wires[0])['routes'][0]
                    assert data['primary_error'] == 'OBLIGATION_PROJECTION_DUPLICATE_ROUTE'
                binding = data['repair_feedback_binding']
                assert binding['wire_output_fingerprint'] == sha256(wires[0].encode()).hexdigest()
                assert binding['inventory_fingerprint'] == inventory['inventory_fingerprint']
                assert (binding['candidate_fingerprint'] is None) == predecode_coverage_failure
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


def test_located_gap_checkpoint_resumes_only_remaining_calls_and_preserves_original_receipts():
    provider, calls, wires, run = repair_case(interrupt=True, coverage_failure=True)
    with pytest.raises(Checkpoint): run()
    frozen = deepcopy(list(provider._fulfillment_receipts))
    provider._fulfillment_receipts = list(provider._fulfillment_receipts)
    result = run()
    assert all(b.state != 'UNRESOLVED' for b in result)
    assert len(calls) == 3 and len(wires) == 2
    assert provider._fulfillment_receipts[:len(frozen)] == frozen
    run()
    assert len(calls) == 3


def test_predecode_coverage_feedback_observes_full_wire_without_admitting_candidate():
    provider, calls, wires, run = repair_case(interrupt=True,coverage_failure=True,predecode_coverage_failure=True)
    with pytest.raises(Checkpoint): run()
    provider._fulfillment_receipts = list(provider._fulfillment_receipts)
    failed = next(r for r in provider._fulfillment_receipts if r['stage']=='CANDIDATE_VALIDATED')
    assert failed['candidate'] is None and failed['validation_passed'] is False
    feedback=json.loads(failed['validation_feedback'])
    observed=feedback['owner_repair_context']
    assert observed['raw_routes_not_evaluable']==[]
    assert 'ADMISSION_NOT_GRANTED' in observed['location_status']
    assert 'COMPLETE_PLAN_ADMISSION' in observed['not_evaluable']
    assert 'INDEPENDENT_SEMANTIC_REVIEW' in observed['not_evaluable']
    assert 'coverage_observation_contract' not in feedback
    original=deepcopy(provider._fulfillment_receipts)
    result=run()
    assert all(b.state!='UNRESOLVED' for b in result) and len(calls)==3
    assert provider._fulfillment_receipts[:len(original)]==original


@pytest.mark.parametrize('version', ('existing-owner-typed-prerequisites-v6','existing-owner-typed-prerequisites-v7'))
def test_historical_located_feedback_replays_exact_bytes_without_new_calls(monkeypatch,version):
    import spg.application.governed_obligations as owner
    original_builder=owner._owner_source_preconditions
    def historical_builder(*args,**kwargs):
        kwargs['typed_prerequisite_contract']=version
        return original_builder(*args,**kwargs)
    provider,calls,wires,run=repair_case(coverage_failure=True)
    with monkeypatch.context() as legacy:
        legacy.setattr(owner,'_owner_source_preconditions',historical_builder)
        assert all(b.state!='UNRESOLVED' for b in run())
    frozen=deepcopy(provider._fulfillment_receipts)
    failed=next(r for r in frozen if r['stage']=='CANDIDATE_VALIDATED' and r['attempt']==1)
    feedback=json.loads(failed['validation_feedback'])
    assert 'location_status' not in feedback['owner_repair_context']
    result=run()
    assert all(b.state!='UNRESOLVED' for b in result)
    assert len(calls)==3 and len(wires)==2 and provider._fulfillment_receipts==frozen


@pytest.mark.parametrize('tamper', ('range', 'source-hash', 'contract', 'located-span'))
def test_located_gap_feedback_drift_is_rejected_before_any_repair_request(tamper):
    provider, calls, wires, run = repair_case(interrupt=True, coverage_failure=True)
    with pytest.raises(Checkpoint): run()
    provider._fulfillment_receipts = list(provider._fulfillment_receipts)
    failed = next(r for r in provider._fulfillment_receipts if r['stage'] == 'CANDIDATE_VALIDATED')
    payload = json.loads(failed['validation_feedback'])
    gap = next(v for v in payload['violations'] if 'uncovered_codepoint_ranges' in v)
    if tamper == 'range': gap['uncovered_codepoint_ranges'] = [[0, 2]]
    elif tamper == 'source-hash': gap['original_text_sha256'] = '0' * 64
    elif tamper == 'contract': payload.pop('coverage_observation_contract')
    else: payload['owner_repair_context']['located_components'][0]['located_span'] = [0, 1]
    failed['validation_feedback'] = json.dumps(payload, separators=(',', ':'))
    result = run()
    assert all(b.state == 'UNRESOLVED' for b in result)
    assert len(calls) == 1 and len(wires) == 1
    assert result[0].formation_receipt['terminal_reason'] == 'OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'


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
    native = [c for c in contracts if 'tool_contract' in c]
    assert len(native) == 1
    tool = next(t for t in PUBLIC_NATIVE_TOOL_CONTRACTS if t['identity'] == 'preview.inspect')
    assert native[0]['tool_contract'] == tool


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


@pytest.mark.parametrize('scale', ('small', 'medium', 'complex'))
def test_formation_primary_meaning_projection_preserves_shared_identity_and_original_text(scale):
    from spg.providers.fulfillment_candidate import _formation_source_table, _fulfillment_wire_context
    from spg.application.governed_obligations import fulfillment_capability_contracts
    from spg.domain.governed_obligation import fulfillment_source_semantic_text
    _, _, inventory, _ = controlled_capacity_case(scale)
    context = _fulfillment_wire_context(inventory, fulfillment_capability_contracts())
    original = deepcopy(context)
    rows = _formation_source_table(context)
    assert context == original
    assert len(rows) == len(inventory['sources'])
    for index, (row, source) in enumerate(zip(rows, inventory['sources'], strict=True)):
        assert row['index'] == index and row['source_ref'] == source['source_ref']
        assert row['primary_semantic_text'] == fulfillment_source_semantic_text(source)
        assert row['text_sha256'] == sha256(row['primary_semantic_text'].encode()).hexdigest()
        assert 'capability' not in row and 'permission' not in row


def test_formation_primary_text_identity_drift_is_not_silently_restored():
    from spg.providers.fulfillment_candidate import _formation_source_table, _fulfillment_wire_context, _FulfillmentWireReceiptIdentityError
    from spg.application.governed_obligations import fulfillment_capability_contracts
    _, _, inventory, _ = controlled_capacity_case()
    context = _fulfillment_wire_context(inventory, fulfillment_capability_contracts())
    context['source_texts'] = ('substituted', *context['source_texts'][1:])
    with pytest.raises(_FulfillmentWireReceiptIdentityError, match='SOURCE_TABLE_IDENTITY_DRIFT'):
        _formation_source_table(context)
