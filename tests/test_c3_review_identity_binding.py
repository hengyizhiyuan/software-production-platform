"""Request-bound identity reuse, independent verdicts and durable replay."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
import pytest
from spg.application import governed_obligations as a
from spg.providers import fulfillment_candidate as p
from tests.test_c3_reviewer_contract_feedback import run_case
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case
from tests.test_c3_semantic_contract_calibration import review
from tests.test_c3_fulfillment_wire_feedback import Checkpoint


def null_identities(raw):
    raw = deepcopy(raw)
    for field in ('inventory_fingerprint', 'candidate_fingerprint', 'components_fingerprint'):
        raw[field] = None
    for row in raw['source_results']: row['source_ref'] = None
    for row in raw['component_results']:
        row['component_id'] = row['capability'] = None
    return raw


def bound_case(**kwargs):
    rev, ir, inv, provider, calls, execute = run_case(**kwargs)
    old = provider.runtime_factory
    def factory():
        runtime = old()
        generate = runtime.generate
        def wrapped(**request):
            result = generate(**request)
            if 'untrusted_fulfillment_candidate' in json.loads(request['input_text']):
                assert request['output_schema']['properties']['inventory_fingerprint']['type'] == 'null'
                return replace(result, output_text=json.dumps(null_identities(json.loads(result.output_text))))
            return result
        runtime.generate = wrapped
        return runtime
    provider.runtime_factory = factory
    return rev, ir, inv, provider, calls, execute


def test_bound_slots_preserve_negative_verdict_feedback_and_replay_without_new_call():
    rev, ir, inv, provider, calls, execute = bound_case(checkpoint=True)
    with pytest.raises(Checkpoint): execute()
    rows = provider._fulfillment_receipts
    observed = next(r for r in rows if r['stage'] == 'SEMANTIC_REVIEW_OBSERVED')
    assert json.loads(observed['review_output'])['component_results'][0]['component_id'] is None
    assert observed['review_output_sha256'] == sha256(observed['review_output'].encode()).hexdigest()
    rejected = next(r for r in rows if r['stage'] == 'SEMANTIC_REVIEW_VALIDATED')
    assert rejected['validation_passed'] is False
    result = execute()
    assert all(b.state != 'UNRESOLVED' for b in result)
    a.validate_fulfillment_projection(result, rev, ir, source_revision=inv['source_revision'], exact_target_paths=inv['exact_target_paths'])
    assert len(calls) == 4


@pytest.mark.parametrize('change', ('inventory', 'candidate', 'components', 'slots', 'request', 'digest', 'length', 'missing', 'wrong-id', 'wrong-source', 'wrong-capability', 'duplicate', 'omitted-identity', 'no-binding'))
def test_invalid_identity_basis_is_never_repaired(change):
    _, _, inv, plan = controlled_capacity_case()
    raw = null_identities(review(inv, plan).model_dump(mode='json'))
    if change == 'missing': raw['component_results'].pop()
    if change == 'wrong-id': raw['component_results'][0]['component_id'] = '0'*64
    if change == 'wrong-source': raw['source_results'][0]['source_ref'] = 'unknown-source'
    if change == 'wrong-capability': raw['component_results'][0]['capability'] = 'DENY_PREVIEW'
    if change == 'duplicate': raw['component_results'].append(deepcopy(raw['component_results'][0]))
    if change == 'omitted-identity': raw['component_results'][0].pop('component_id')
    output = json.dumps(raw)
    binding = p._review_identity_binding(inv, plan, output, 'controlled-request')
    keys = {'inventory':'inventory_fingerprint', 'candidate':'candidate_fingerprint', 'components':'components_fingerprint',
        'slots':'result_slots_fingerprint', 'request':'model_request_id', 'digest':'review_output_sha256', 'length':'review_output_bytes'}
    if change in keys: binding[keys[change]] = 0 if change == 'length' else '0'*64
    if change == 'no-binding': binding = None
    with pytest.raises((ValueError, p._FulfillmentWireReceiptIdentityError)):
        p.FulfillmentSemanticReviewCandidate.model_validate(p._resolve_review_identities(output, inv, plan, binding, 'controlled-request'))


def test_exact_explicit_legacy_response_is_unchanged_and_semantic_rejection_stays_false():
    _, _, inv, plan = controlled_capacity_case()
    raw = review(inv, plan).model_dump(mode='json')
    output = json.dumps(raw)
    assert p._resolve_review_identities(output, inv, plan) == raw
    raw['component_results'][0]['complete_and_equivalent'] = False
    output = json.dumps(null_identities(raw))
    bound = p._resolve_review_identities(output, inv, plan, p._review_identity_binding(inv, plan, output, 'r'), 'r')
    assert bound['component_results'][0]['complete_and_equivalent'] is False
    with pytest.raises(ValueError, match='SEMANTIC_COMPONENT_MISMATCH'):
        a.validate_projection_components(plan, inv, semantic_review=bound)


@pytest.mark.parametrize('change', ('digest', 'request', 'slots', 'missing-binding', 'pending-table'))
def test_durable_binding_corruption_stops_replay_without_dispatch(change):
    _, _, _, provider, calls, execute = bound_case(checkpoint=True)
    with pytest.raises(Checkpoint): execute()
    observed = next(r for r in provider._fulfillment_receipts if r['stage'] == 'SEMANTIC_REVIEW_OBSERVED' and r['attempt'] == 2)
    if change == 'pending-table':
        pending = next(r for r in provider._fulfillment_receipts if r['stage'] == 'SEMANTIC_REVIEW_PENDING' and r['attempt'] == 2)
        pending['review_result_identity_slots']['component_results'][0]['component_id'] = '0'*64
    elif change == 'missing-binding': observed.pop('review_identity_binding')
    else:
        key = {'digest':'review_output_sha256','request':'model_request_id','slots':'result_slots_fingerprint'}[change]
        observed['review_identity_binding'][key] = '0'*64
    result = execute()
    assert all(b.state == 'UNRESOLVED' for b in result)
    assert len(calls) == 4


def test_full_identity_legacy_order_is_not_silently_reinterpreted_as_positional():
    _, _, inv, plan = controlled_capacity_case()
    raw = review(inv, plan).model_dump(mode='json')
    raw['source_results'].reverse(); raw['component_results'].reverse()
    output = json.dumps(raw)
    actual = p._resolve_review_identities(output, inv, plan, p._review_identity_binding(inv, plan, output, 'legacy'), 'legacy')
    assert actual == raw
    a.validate_projection_components(plan, inv, semantic_review=actual)


def test_malformed_wire_still_requires_the_original_request_binding():
    _, _, inv, plan = controlled_capacity_case()
    binding = p._review_identity_binding(inv, plan, '{', 'original')
    binding['model_request_id'] = 'other'
    with pytest.raises(p._FulfillmentWireReceiptIdentityError, match='IDENTITY_BINDING_DRIFT'):
        p._resolve_review_identities('{', inv, plan, binding, 'original')
