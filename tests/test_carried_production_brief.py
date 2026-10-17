"""Original Human facts remain pending across supplements, with both real owners."""
import gzip
import json
from pathlib import Path

import pytest

from spg.application.governed_obligations import fulfillment_inventory, validate_fulfillment_projection
from spg.application.production_brief import CONTINUITY_CONTRACT, REVIEW_METHOD, production_brief_bindings
from spg.domain.engineering_semantics import SemanticRelation
from tests.test_production_brief_admission import admit, brief_case
from tests.test_staged_production_brief import basis


def real_case():
    revision, ir = basis('carried-assertion-source.json.gz')
    raw = json.loads(gzip.decompress((Path(__file__).parent / 'fixtures/usability/carried-assertion-source.json.gz').read_bytes()))
    return revision, ir, tuple(raw['exact_target_paths'])


def test_unchanged_failed_work_keeps_all_original_requirements_and_no_preproduction_model():
    revision, ir, paths = real_case()
    before = revision.model_dump(), ir.model_dump()
    bindings = admit(revision, ir, paths)
    assert bindings[0].formation_receipt['source_role_contract'] == CONTINUITY_CONTRACT
    assert bindings[0].formation_receipt['provider_call_count'] == 0
    assertion = next(f for f in revision.engineering_semantic_facts if f.relation is SemanticRelation.ACCEPTANCE_ASSERTION)
    assert all(assertion.provenance.source_text not in c.source_text for c in ir.clauses)
    selected = [b for b in bindings if b.fact_id == assertion.id]
    assert {b.evidence_method for b in selected} == {'EXACT_CANDIDATE_CONTENT', REVIEW_METHOD}
    assert all(b.source_quote == assertion.provenance.source_text and b.state == 'BOUND_PENDING_EVIDENCE' for b in selected)
    assert all(any(b.work_constraint_indices == (i,) and b.source_quote == text for b in bindings) for i, text in enumerate(revision.constraints))
    assert before == (revision.model_dump(), ir.model_dump())
    validate_fulfillment_projection(bindings, revision, ir, source_revision=revision.source_revision, exact_target_paths=paths)


@pytest.mark.parametrize('quality', ['细腻的庭院平面图', 'Readable labels at narrow viewport widths', 'Clear instrument separation'])
def test_unrelated_carried_human_assertion_reaches_actual_content_and_later_review(quality):
    revision, ir = brief_case()
    original = revision.engineering_semantic_facts[0]
    revision.engineering_semantic_facts = (original.model_copy(update={
        'relation': SemanticRelation.ACCEPTANCE_ASSERTION, 'value': quality,
        'provenance': original.provenance.model_copy(update={'source_text': quality})}),)
    ir.items = tuple(i.model_copy(update={'production': i.production.model_copy(update={'preview_required': True, 'acceptance_required': True})}) if i.production else i for i in ir.items)
    ir.current_production = tuple(i.production for i in ir.items if i.production)
    bindings = admit(revision, ir)
    assert {b.evidence_method for b in bindings if b.fact_id == original.id} == {'EXACT_CANDIDATE_CONTENT', REVIEW_METHOD}


@pytest.mark.parametrize('corruption', ['drop-content', 'drop-readiness', 'pass', 'new-source', 'new-path'])
def test_same_source_cannot_lose_an_owner_or_claim_pending_evidence_passed(corruption):
    revision, ir, paths = real_case(); bindings = list(admit(revision, ir, paths))
    i = next(i for i, b in enumerate(bindings) if b.evidence_method == REVIEW_METHOD)
    fact_id = bindings[i].fact_id
    if corruption == 'drop-content': bindings = [b for b in bindings if not (b.fact_id == fact_id and b.evidence_method == 'EXACT_CANDIDATE_CONTENT')]
    elif corruption == 'drop-readiness': bindings.pop(i)
    else: bindings[i] = bindings[i].model_copy(update={
        'pass': {'state': 'PASS'}, 'new-source': {'source_quote': 'The original condition was removed'},
        'new-path': {'target_paths': ('other.html',)}}[corruption])
    with pytest.raises(ValueError): validate_fulfillment_projection(bindings, revision, ir,
        source_revision=revision.source_revision, exact_target_paths=paths)


@pytest.mark.parametrize('change', ['unresolved', 'inferred', 'negated', 'foreign-record', 'delivery'])
def test_continuity_does_not_resolve_unknown_facts_or_authority(change):
    revision, ir, paths = real_case()
    f = next(f for f in revision.engineering_semantic_facts if f.relation is SemanticRelation.ACCEPTANCE_ASSERTION)
    update = {'unresolved': {'epistemic_status': type(f.epistemic_status).UNRESOLVED},
        'inferred': {'authority': type(f.authority).SYSTEM_INFERRED}, 'negated': {'qualifiers': {'negated': True}},
        'foreign-record': {'provenance': f.provenance.model_copy(update={'source_record_ids': (revision.work_id,)})}}
    if change == 'delivery':
        ir = ir.model_copy(update={'items': tuple(i.model_copy(update={'production': i.production.model_copy(update={'delivery_authorized': True})}) if i.production else i for i in ir.items)})
    else: revision = revision.model_copy(update={'engineering_semantic_facts': tuple(x.model_copy(update=update[change]) if x.id == f.id else x for x in revision.engineering_semantic_facts)})
    inventory = fulfillment_inventory(revision, ir, source_revision=revision.source_revision, exact_target_paths=paths)
    assert production_brief_bindings(revision, ir, inventory, contract=CONTINUITY_CONTRACT) is None
