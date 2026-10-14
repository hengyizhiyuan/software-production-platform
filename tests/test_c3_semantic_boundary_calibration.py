"""Current derived file scope has a lawful Owner entry, not a fulfilled verdict."""
from copy import deepcopy

import pytest

from spg.application import governed_obligations as owner
from spg.domain.governed_obligation import FulfillmentPhase
from spg.domain.intent_realization import SemanticClause, SemanticItem, SemanticKind
from spg.domain.semantic_provenance import SemanticOrigin, SemanticProvenance
from tests.test_c3_exclusion_content_correspondence import case


def file_exclusion_case(exclusion, boundary):
    revision, ir, _, route = case(exclusion)
    record = ir.items[0].provenance[0].source_record_id
    provenance = SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,
        source_record_id=record, source_text=boundary)
    item = SemanticItem(item_id='separate-current-file-boundary', kind=SemanticKind.CONSTRAINT,
        statement=boundary, provenance=(provenance,), confidence=1)
    clause = SemanticClause(clause_id='current-file-boundary', source_record_id=record,
        source_text=boundary, semantic_item_ids=(item.item_id,), polarity='AFFIRMATIVE',
        modality='REQUEST', temporal_scope='CURRENT', requested_effects=())
    ir.items = (*ir.items, item)
    ir.clauses = (*ir.clauses, clause)
    scope = next(f for f in revision.engineering_semantic_facts if f.relation.value == 'SCOPE')
    revision.engineering_semantic_facts = tuple(f.model_copy(update={
        'scope': None, 'qualifiers': {}, 'provenance': f.provenance.model_copy(update={
            'source_record_ids': (record,), 'source_text': boundary})}) if f.id == scope.id else f
        for f in revision.engineering_semantic_facts)
    inventory = owner.fulfillment_inventory(revision, ir, exact_target_paths=('index.html',))
    source = next(s for s in inventory['sources'] if s['kind'] == 'WORK_CONSTRAINT'
        and s['payload']['content'] == route.component_basis.source_component_quote)
    origin = next(s for s in inventory['sources'] if s.get('clause_id') == 'controlled-origin')
    current_scope = next(s for s in inventory['sources'] if s.get('clause_id') == clause.clause_id)
    route = route.model_copy(update={'source_ref': source['source_ref'], 'capability': 'GIT_DIFF_SCOPE',
        'supporting_source_refs': (origin['source_ref'], current_scope['source_ref'])})
    return revision, ir, inventory, route, origin, current_scope


@pytest.mark.parametrize('exclusion,boundary', [
    ('No file other than index.html may change.', 'Only index.html may change.'),
    ('目标文件以外不得变更。', '仅允许变更 index.html。'),
])
def test_current_positive_scope_is_eligible_with_exact_derivation_and_still_pending(exclusion, boundary):
    revision, ir, inventory, route, origin, scope = file_exclusion_case(exclusion, boundary)
    before = deepcopy((revision.engineering_semantic_facts, revision.constraints, ir.clauses))
    entries = [origin, scope]
    args = dict(component='git-diff-scope', phase=FulfillmentPhase.CURRENT_VERIFICATION,
        semantic_component_declared=True, calibrated=True, source_contract='v3',
        revision=revision, exact_target_paths=inventory['exact_target_paths'])
    assert owner.work_constraint_sources_correspond(ir, route.component_basis.source_component_quote,
        entries, **args)
    capabilities = owner.fulfillment_capability_contracts()
    preconditions = owner._owner_source_preconditions(revision, ir, inventory, capabilities)
    ordinal = {s['source_ref']: i for i, s in enumerate(inventory['sources'])}
    source_index = ordinal[route.source_ref]
    diff_capability = next(i for i, c in enumerate(capabilities) if c['capability'] == 'GIT_DIFF_SCOPE')
    proofs = next(p['minimal_support_sets'] for p in preconditions['sources'][source_index]['necessary_source_proofs']
        if p['capability'] == diff_capability)
    assert sorted([ordinal[origin['source_ref']], ordinal[scope['source_ref']]]) in proofs
    assert owner._projection_binding(revision, ir, inventory, route, allow_calibrated=True,
        source_contract='v3').state == 'BOUND_PENDING_EVIDENCE'
    assert before == (revision.engineering_semantic_facts, revision.constraints, ir.clauses)


@pytest.mark.parametrize('change', ('no-origin', 'no-scope', 'wrong-record', 'wrong-value',
    'wrong-clause-record', 'not-current-origin', 'future-scope', 'extra-source',
    'old-contract', 'effect-gate', 'content-method', 'wrong-target'))
def test_scope_entry_does_not_create_source_authority_or_execution_evidence(change):
    revision, ir, inventory, route, origin, scope = file_exclusion_case(
        'No file other than index.html may change.', 'Only index.html may change.')
    if change == 'no-origin':
        route = route.model_copy(update={'supporting_source_refs': (scope['source_ref'],)})
    elif change == 'no-scope':
        route = route.model_copy(update={'supporting_source_refs': (origin['source_ref'],)})
    elif change in {'wrong-record', 'wrong-value'}:
        original = next(f for f in revision.engineering_semantic_facts if f.relation.value == 'SCOPE')
        amended = (original.model_copy(update={'provenance': original.provenance.model_copy(update={
            'source_record_ids': ()})}) if change == 'wrong-record' else
            original.model_copy(update={'value': ['other.html']}))
        revision.engineering_semantic_facts = tuple(amended if f.id == original.id else f
            for f in revision.engineering_semantic_facts)
    elif change == 'future-scope':
        ir.clauses = tuple(c.model_copy(update={'temporal_scope': 'FUTURE'})
            if c.clause_id == scope['clause_id'] else c for c in ir.clauses)
    elif change == 'wrong-clause-record':
        from uuid import uuid4
        ir.clauses = tuple(c.model_copy(update={'source_record_id': uuid4()})
            if c.clause_id == scope['clause_id'] else c for c in ir.clauses)
    elif change == 'not-current-origin':
        ir.current_production = ()
    elif change == 'extra-source':
        unrelated = next(s for s in inventory['sources'] if s.get('clause_id') == 'future-approval-clause')
        route = route.model_copy(update={'supporting_source_refs': (*route.supporting_source_refs,
            unrelated['source_ref'])})
    elif change == 'effect-gate':
        route = route.model_copy(update={'capability': 'DENY_DEPLOY', 'target_paths': ()})
    elif change == 'content-method':
        route = route.model_copy(update={'capability': 'ARTIFACT_CONTENT'})
    elif change == 'wrong-target':
        route = route.model_copy(update={'target_paths': ('other.html',)})
    args = dict(allow_calibrated=True, source_contract='v2' if change == 'old-contract' else 'v3')
    with pytest.raises(ValueError, match='OBLIGATION_'):
        owner._projection_binding(revision, ir, inventory, route, **args)
