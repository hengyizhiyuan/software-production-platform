"""Original exclusion origin is not a choice of evidence method or a verdict."""
from copy import deepcopy
import pytest
from spg.application import governed_obligations as a
from spg.domain.governed_obligation import FulfillmentRouteCandidate, FulfillmentComponentBasis
from spg.domain.intent_realization import SemanticClause, SemanticItem, SemanticKind
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case

CONTRACT = 'existing-current-exclusion-content-correspondence-v1'


def case(value='additional interactive surfaces'):
    rev, ir, _, _ = controlled_capacity_case()
    goal = ir.current_production[0].model_copy(update={'exclusions': (value,)})
    original = SemanticItem(item_id='controlled-original-production', kind=SemanticKind.PRODUCTION_INTENT,
        statement='Build the requested artifact within its original exclusions.',
        provenance=ir.items[0].provenance, confidence=1, production=goal)
    ir.items = (*ir.items, original)
    ir.current_production = (goal, *ir.current_production[1:])
    record = original.provenance[0].source_record_id
    clauses = tuple(SemanticClause(clause_id=label, source_record_id=record,
        source_text=text, semantic_item_ids=(original.item_id,), polarity=polarity,
        modality='REQUEST', temporal_scope='CURRENT', requested_effects=())
        for label, text, polarity in [('controlled-origin', 'Build the requested artifact.', 'AFFIRMATIVE'),
            ('controlled-exclusion', 'Do not create '+value+'.', 'NEGATED')])
    ir.clauses = (*ir.clauses, *clauses)
    quote = 'Excluded from this Work: '+value
    rev.constraints = (*rev.constraints, quote)
    inv = a.fulfillment_inventory(rev, ir, exact_target_paths=('index.html',))
    source = next(s for s in inv['sources'] if s['kind'] == 'WORK_CONSTRAINT' and s['payload']['content'] == quote)
    refs = tuple(s['source_ref'] for s in inv['sources'] if s.get('clause_id') in {c.clause_id for c in clauses})
    route = FulfillmentRouteCandidate(source_ref=source['source_ref'], capability='ARTIFACT_CONTENT',
        target_paths=('index.html',), work_constraint_indices=(source['index'],), supporting_source_refs=refs,
        component_basis=FulfillmentComponentBasis(source_span_start=0, source_span_end=len(quote), source_component_quote=quote),
        rationale='Controlled necessary consumer; independent Review and actual Verification still pending.')
    return rev, ir, inv, route


@pytest.mark.parametrize('value', ('additional interactive surfaces', 'hidden navigation states', '额外交互页面'))
def test_exact_exclusion_source_can_support_content_without_becoming_file_or_effect_authority(value):
    rev, ir, inv, route = case(value)
    before = deepcopy((rev.constraints, vars(ir), route.model_dump(mode='json')))
    with pytest.raises(ValueError, match='CORRESPONDENCE_UNPROVEN'):
        a._projection_binding(rev, ir, inv, route, allow_calibrated=True, source_contract='v3')
    result = a._projection_binding(rev, ir, inv, route, allow_calibrated=True,
        source_contract='v3', exclusion_content_contract=CONTRACT)
    assert result.state == 'BOUND_PENDING_EVIDENCE'
    assert result.evidence_method == 'EXACT_CANDIDATE_CONTENT'
    assert result.supporting_source_refs == route.supporting_source_refs
    assert result.target_paths == ('index.html',)
    assert before == (rev.constraints, vars(ir), route.model_dump(mode='json'))


@pytest.mark.parametrize('change', ('no-origin', 'no-negative', 'future-negative', 'affirmative',
    'different-value', 'typed-effect', 'outside-target', 'legacy', 'future-human'))
def test_missing_original_proof_or_wrong_authority_remains_rejected(change):
    rev, ir, inv, route = case()
    contract = CONTRACT
    if change == 'no-origin': route = route.model_copy(update={'supporting_source_refs': ()})
    elif change == 'no-negative':
        route = route.model_copy(update={'supporting_source_refs': (route.supporting_source_refs[0],)})
    elif change in ('future-negative', 'affirmative', 'typed-effect'):
        changes = {'future-negative': {'temporal_scope': 'FUTURE'},
            'affirmative': {'polarity': 'AFFIRMATIVE'}, 'typed-effect': {'requested_effects': ('PROHIBIT_DEPLOY',)}}[change]
        ir.clauses = tuple(c.model_copy(update=changes) if c.clause_id == 'controlled-exclusion' else c for c in ir.clauses)
        inv = a.fulfillment_inventory(rev, ir, exact_target_paths=('index.html',))
    elif change == 'different-value':
        ir.items = tuple(i.model_copy(update={'production': i.production.model_copy(update={'exclusions': ()})})
            if i.production is not None else i for i in ir.items)
    elif change == 'outside-target': route = route.model_copy(update={'target_paths': ('other.html',)})
    elif change == 'legacy': contract = None
    elif change == 'future-human': route = route.model_copy(update={'capability': 'HUMAN_INTEGRATION', 'target_paths': ()})
    with pytest.raises(ValueError, match='OBLIGATION_'):
        a._projection_binding(rev, ir, inv, route, allow_calibrated=True,
            source_contract='v3', exclusion_content_contract=contract)


def test_generation_uses_the_same_source_predicate_but_does_not_select_a_method():
    rev, ir, inv, route = case()
    caps = a.fulfillment_capability_contracts()
    common = dict(review_input_contract='existing-admission-source-comparison-input-v5',
        review_source_consumption_contract='existing-source-consumption-proof-v2')
    previous = a._owner_source_preconditions(rev, ir, inv, caps, **common)
    current = a._owner_source_preconditions(rev, ir, inv, caps, **common, exclusion_content_contract=CONTRACT)
    index = next(i for i,s in enumerate(inv['sources']) if s['source_ref'] == route.source_ref)
    content = next(i for i,c in enumerate(caps) if c['capability'] == 'ARTIFACT_CONTENT')
    assert not any(p['capability'] == content for p in previous['sources'][index].get('necessary_source_proofs', []))
    proof = next(p for p in current['sources'][index]['necessary_source_proofs'] if p['capability'] == content)
    assert proof['minimal_support_sets']
    assert current['exclusion_content_contract'] == CONTRACT
    assert 'selected_capability' not in current['sources'][index]
