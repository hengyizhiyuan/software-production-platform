"""Candidate applicability is not original Fact admission or performed evidence."""
from copy import deepcopy
import pytest
from spg.application import governed_obligations as a
from spg.domain.engineering_semantics import SemanticRelation
from spg.domain.governed_obligation import literal_file_scope_value_paths
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case, controlled_model_provider
from tests.test_c3_semantic_contract_calibration import review
from tests.test_c3_source_consumption_proof import fixture_consumption_checks


def preconditions(rev, ir, inv):
    return a._owner_source_preconditions(rev, ir, inv, a.fulfillment_capability_contracts(),
        review_input_contract='existing-admission-source-comparison-input-v5',
        review_source_consumption_contract='existing-source-consumption-proof-v2',
        fact_method_applicability_contract=a._FACT_METHOD_APPLICABILITY)


def case(relation=SemanticRelation.BOUND, mixed=False):
    rev, ir, inv, plan = controlled_capacity_case()
    scope = next(f for f in rev.engineering_semantic_facts if f.relation is SemanticRelation.SCOPE)
    rev.engineering_semantic_facts = tuple(f.model_copy(update={'relation': relation}) if f.id == scope.id else f
        for f in rev.engineering_semantic_facts)
    if mixed:
        original = rev.engineering_semantic_facts[0]
        text = 'Produce the requested visible content as a reviewable Candidate.'
        changed = original.model_copy(update={'relation': SemanticRelation.SCOPE,
            'value': text, 'provenance': original.provenance.model_copy(update={'source_text': text})})
        rev.engineering_semantic_facts = (changed, *rev.engineering_semantic_facts[1:])
        routes = list(plan.routes)
        routes[0] = routes[0].model_copy(update={'component_basis': routes[0].component_basis.model_copy(update={
            'source_span_end': len(text), 'source_component_quote': text, 'linked_fact_refs': ()})})
        routes.insert(1, routes[0].model_copy(update={'capability': 'CANDIDATE_SEAL', 'target_paths': ()}))
        plan = plan.model_copy(update={'routes': tuple(routes)})
    inv = a.fulfillment_inventory(rev, ir, exact_target_paths=inv['exact_target_paths'])
    plan = plan.model_copy(update={'inventory_fingerprint': inv['inventory_fingerprint']})
    return rev, ir, inv, plan


def verdict(inv, plan):
    raw = review(inv, plan).model_dump(mode='json')
    for row in raw['source_results']:
        row['consumption_checks'] = fixture_consumption_checks(inv, plan, row['source_ref'])
    return raw


@pytest.mark.parametrize('relation', (SemanticRelation.BOUND, SemanticRelation.EQUALITY, SemanticRelation.SCOPE))
def test_original_relation_survives_candidate_method_review_and_actual_evidence_is_still_pending(relation):
    rev, ir, inv, plan = case(relation)
    before = deepcopy(rev.engineering_semantic_facts)
    own = preconditions(rev, ir, inv)
    bindings = a.validate_projection_candidate(plan, rev, ir, inv, source_contract='v3',
        owner_preconditions=own, semantic_review=verdict(inv, plan))
    assert before == rev.engineering_semantic_facts
    diff = next(b for b in bindings if b.evidence_method == 'EXACT_GIT_DIFF_SCOPE')
    assert diff.state == 'BOUND_PENDING_EVIDENCE'
    assert diff.target_paths == tuple(inv['exact_target_paths'])
    assert not diff.formation_receipt
    if relation is not SemanticRelation.SCOPE:
        with pytest.raises(ValueError, match='FACT_EVIDENCE_METHOD_MISMATCH'):
            a.validate_projection_candidate(plan, rev, ir, inv, source_contract='v3',
                allow_review_pending=True)


def test_literal_operand_observation_cannot_retype_fact_or_make_numeric_bound_a_path():
    rev, _, _, _ = case()
    boundary = next(f for f in rev.engineering_semantic_facts if f.relation is SemanticRelation.BOUND)
    assert literal_file_scope_value_paths(boundary) is None
    assert literal_file_scope_value_paths(boundary, proposed_method=True)
    for change in ({'value': 3}, {'value': '../escape'}, {'unit': 'pages'}, {'value': ('a', 'a')}):
        assert literal_file_scope_value_paths(boundary.model_copy(update=change), proposed_method=True) is None


def test_current_content_and_future_seal_are_joint_and_require_independent_review():
    rev, ir, inv, plan = case(mixed=True)
    own = preconditions(rev, ir, inv)
    bindings = a.validate_projection_candidate(plan, rev, ir, inv, source_contract='v3',
        owner_preconditions=own, semantic_review=verdict(inv, plan))
    assert bindings[0].phase.value == 'CURRENT_VERIFICATION'
    assert bindings[1].phase.value == 'CANDIDATE_SEAL'
    assert bindings[0].fact_id == bindings[1].fact_id
    assert bindings[1].gate_ref == 'candidate-owner:sealed-after-verification'
    with pytest.raises(ValueError, match='COMPONENT_REVIEW_REQUIRED'):
        a.validate_projection_candidate(plan, rev, ir, inv, source_contract='v3', owner_preconditions=own)
    future_only = plan.model_copy(update={'routes': plan.routes[1:]})
    with pytest.raises(ValueError, match='SEAL_CURRENT_CONTRIBUTION_MISSING'):
        a.validate_projection_candidate(future_only, rev, ir, inv, source_contract='v3',
            owner_preconditions=own, allow_review_pending=True)


@pytest.mark.parametrize('change', ('wrong-target', 'stale-inventory', 'forged-review', 'semantic-rejection',
    'missing-consumption', 'human-authority', 'negated-future'))
def test_candidate_applicability_never_promotes_bad_semantics_or_governance(change):
    rev, ir, inv, plan = case(mixed=True)
    own = preconditions(rev, ir, inv)
    raw = verdict(inv, plan)
    if change == 'wrong-target':
        plan = plan.model_copy(update={'routes': (plan.routes[0].model_copy(update={'target_paths': ('outside.html',)}), *plan.routes[1:])})
    elif change == 'stale-inventory': plan = plan.model_copy(update={'inventory_fingerprint': '0'*64})
    elif change == 'forged-review': raw['candidate_fingerprint'] = '0'*64
    elif change == 'semantic-rejection': raw['source_results'][0]['complete_and_equivalent'] = False
    elif change == 'missing-consumption': raw['source_results'][0].pop('consumption_checks')
    elif change == 'human-authority':
        plan = plan.model_copy(update={'routes': (plan.routes[0], plan.routes[1].model_copy(update={'capability': 'HUMAN_INTEGRATION'}), *plan.routes[2:])})
        raw = verdict(inv, plan)
    elif change == 'negated-future':
        rev.engineering_semantic_facts = (rev.engineering_semantic_facts[0].model_copy(update={'qualifiers': {'negated': True}}), *rev.engineering_semantic_facts[1:])
        inv = a.fulfillment_inventory(rev, ir, exact_target_paths=inv['exact_target_paths'])
        plan = plan.model_copy(update={'inventory_fingerprint': inv['inventory_fingerprint']})
        own, raw = preconditions(rev, ir, inv), verdict(inv, plan)
    with pytest.raises(ValueError, match='OBLIGATION_'):
        a.validate_projection_candidate(plan, rev, ir, inv, source_contract='v3', owner_preconditions=own, semantic_review=raw)


def test_existing_model_boundary_negotiates_persists_and_replays_same_contract_without_new_calls():
    rev, ir, inv, plan = case(mixed=True)
    provider, calls = controlled_model_provider(inv, plan)
    result = a.form_fulfillment_projection(rev, ir, provider=provider,
        source_revision=inv['source_revision'], exact_target_paths=inv['exact_target_paths'])
    assert all(b.state != 'UNRESOLVED' for b in result)
    pending = next(r for r in provider._fulfillment_receipts if r['stage'] == 'MODEL_REQUEST_PENDING')
    assert pending['owner_source_preconditions']['fact_method_applicability_contract'] == a._FACT_METHOD_APPLICABILITY
    frozen = deepcopy(provider._fulfillment_receipts)
    again = a.form_fulfillment_projection(rev, ir, provider=provider,
        source_revision=inv['source_revision'], exact_target_paths=inv['exact_target_paths'])
    assert provider._fulfillment_receipts == frozen and len(calls) == 2
    for original, restored in zip(result, again):
        left, right = original.model_dump(), restored.model_dump()
        # This aggregate observation is recomputed on each read, not a durable
        # receipt or budget reset. All identities and original rows stay exact.
        if left['formation_receipt'] is not None:
            left['formation_receipt'].pop('elapsed_seconds')
            right['formation_receipt'].pop('elapsed_seconds')
        assert left == right


@pytest.mark.parametrize('seal', (True, False))
@pytest.mark.parametrize('content', ('correct', 'wrong', 'missing-consumer', 'missing-source'))
def test_reviewed_mixed_fact_uses_exact_current_component_without_claiming_future_seal(tmp_path, content, seal):
    import subprocess
    from types import SimpleNamespace
    from uuid import uuid4
    from spg.domain.engineering_semantics import semantic_fact_reference
    from spg.providers.managed_context_fulfillment import verify_fulfillment_fact_routes
    from spg.providers.protected_context_verifier import StaticProtectedContextVerifier
    from spg.infrastructure.model_runtime import StructuredModelResult, ModelProvider, ModelUsage, ModelTiming
    rev, ir, inv, plan = case(mixed=True)
    if not seal:
        plan = plan.model_copy(update={'routes': tuple(r for r in plan.routes if r.capability != 'CANDIDATE_SEAL')})
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), *args], text=True).strip()
    git('init', '-q')
    git('-c', 'user.name=Qualification', '-c', 'user.email=qualification@example.invalid',
        'commit', '--allow-empty', '-qm', 'baseline')
    baseline_revision = git('rev-parse', 'HEAD')
    rev.source_revision = baseline_revision
    inv = a.fulfillment_inventory(rev, ir, source_revision=baseline_revision, exact_target_paths=inv['exact_target_paths'])
    plan = plan.model_copy(update={'inventory_fingerprint': inv['inventory_fingerprint']})
    provider, formation_calls = controlled_model_provider(inv, plan)
    bindings = a.form_fulfillment_projection(rev, ir, provider=provider,
        source_revision=baseline_revision, exact_target_paths=inv['exact_target_paths'])
    (tmp_path/'index.html').write_text('<h1>Exact requested visible content</h1>' if content == 'correct'
        else '<h1>Different actual content</h1>', encoding='utf-8')
    git('add', 'index.html')
    git('-c', 'user.name=Qualification', '-c', 'user.email=qualification@example.invalid', 'commit', '-qm', 'candidate')
    candidate = git('rev-parse', 'HEAD'); tree = git('rev-parse', 'HEAD^{tree}')
    ref = semantic_fact_reference(rev.engineering_semantic_facts[0], work_revision_id=rev.id)
    request = SimpleNamespace(proposed_commit_identity=candidate, tree_identity=tree,
        verification_identity=uuid4(), snapshot_id=uuid4(), source_baseline_id=uuid4(),
        decision_context_fingerprint='a'*64, semantic_fact_obligations=(ref,),
        fulfillment_bindings=bindings, protected_context_obligations=())
    task = SimpleNamespace(task_contract_id=uuid4(), objective='controlled goal', scope='controlled scope',
        constraints=(), out_of_scope=(), decision_context=SimpleNamespace(
            package_fingerprint=request.decision_context_fingerprint, protected_obligations=()))
    contract = SimpleNamespace(source_revision=baseline_revision, allowed_areas=(),
        exact_targets=(SimpleNamespace(path='index.html'),))
    verification_calls=[]
    def runtime_factory():
        def generate(**kwargs):
            import json
            payload=json.loads(kwargs['input_text']); verification_calls.append(payload)
            checks=[{'context_class': o['context_class'], 'semantic_key':o['semantic_key'],
                'disposition': 'SATISFIED' if content == 'correct' else 'CONTRADICTED',
                'reason':'Controlled actual blob judgment',
                'witnesses':[{'path':'index.html','quote':payload['candidate_sources']['index.html']}]}
                for o in payload['protected_obligations']]
            return StructuredModelResult(output_text=json.dumps({'checks':checks}), provider=ModelProvider.DEEPSEEK,
                requested_model='controlled',effective_model='controlled',request_id='controlled-component',
                usage=ModelUsage(unknown=True),timing=ModelTiming())
        return SimpleNamespace(generate=generate, registry=SimpleNamespace(close=lambda:None))
    before=deepcopy(rev.engineering_semantic_facts)
    if content == 'missing-source':
        request.semantic_fact_obligations = ()
        with pytest.raises(ValueError, match='OBLIGATION_DERIVED_FACT_SOURCE_MISSING'):
            verify_fulfillment_fact_routes(repository=tmp_path, request=request, contract=contract,
                references=(ref,), admitted_facts={str(ref.fact_id):rev.engineering_semantic_facts[0]},
                revision=rev, ir=ir, baseline=SimpleNamespace(repository_revision=baseline_revision),
                bindings=bindings, plan_repair=None, static_verifier=StaticProtectedContextVerifier(runtime_factory), task=task)
        assert verification_calls == []
        return
    result=verify_fulfillment_fact_routes(repository=tmp_path, request=request, contract=contract,
        references=(ref,), admitted_facts={str(ref.fact_id):rev.engineering_semantic_facts[0]},
        revision=rev, ir=ir, baseline=SimpleNamespace(repository_revision=baseline_revision),
        bindings=bindings, plan_repair=None,
        static_verifier=None if content == 'missing-consumer' else StaticProtectedContextVerifier(runtime_factory), task=task)
    assert result[0]['passed'] is (content == 'correct')
    assert result[0]['future_evidence_status'] == ('PENDING_FUTURE_OWNER_GATE' if seal else None)
    assert rev.engineering_semantic_facts == before and len(formation_calls)==2
    if content != 'missing-consumer':
        assert len(verification_calls)==1
        assert verification_calls[0]['immutable_fact_references'] == [ref.model_dump(mode='json')]
        assert len(result[0]['current_component_evidence'])==1
        assert result[0]['current_component_evidence'][0]['candidate_revision']==candidate
        assert all(b['phase']=='CURRENT_VERIFICATION' for b in verification_calls[0]['assigned_fulfillment_bindings'])
