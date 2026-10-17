"""Complete retained request, phase ownership and permissions, no case aliases."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from spg.application.governed_obligations import admitted_fulfillment_bindings, validate_fulfillment_projection
from spg.application.production_brief import STAGED_CONTRACT, REVIEW_METHOD
from spg.domain.intent_realization import GovernedSemanticIR
from spg.infrastructure.persistence.product_store import ProductStore
from spg.providers.managed_context_fulfillment import _review_readiness_pending


def basis(fixture="mixed-preview-admitted-source.json.gz"):
    x = json.loads(gzip.decompress((Path(__file__).parent / 'fixtures/usability' / fixture).read_bytes()))
    row = x['revision']
    for k in ('id', 'work_id', 'previous_revision_id', 'source_interaction_id', 'source_assessment_id',
              'engineering_scope_id', 'engineering_resource_id', 'source_baseline_id', 'governance_record_id'):
        if row.get(k): row[k] = UUID(row[k])
    return ProductStore._work_reality_revision(row), GovernedSemanticIR.model_validate(x['ir'])


def admit(revision, ir):
    class NoModel:
        def form(self, *a, **kw): raise AssertionError('Unchanged source requires no pre-review')
    return admitted_fulfillment_bindings(revision, SimpleNamespace(id=revision.source_assessment_id, semantic_ir=ir),
        source_revision=revision.source_revision, exact_target_paths=('index.html',), provider=NoModel())


@pytest.mark.parametrize('fixture', ['mixed-preview-admitted-source.json.gz', 'mixed-preview-assertion-source.json.gz'])
def test_complete_unchanged_failed_input_is_admitted_with_later_readiness_pending(fixture):
    revision, ir = basis(fixture)
    original = deepcopy(ir.model_dump())
    bindings = admit(revision, ir)
    assert bindings[0].formation_receipt['source_role_contract'] == STAGED_CONTRACT
    assert bindings[0].formation_receipt['provider_call_count'] == 0
    assert ir.model_dump() == original
    future = [b for b in bindings if b.evidence_method == REVIEW_METHOD]
    assert future and all(b.state == 'BOUND_PENDING_EVIDENCE' for b in future)
    assert any(b.source_quote == '不部署到公网' for b in future)
    for i, text in enumerate(revision.constraints):
        assert any(b.work_constraint_indices == (i,) and b.source_quote == text for b in bindings)
    validate_fulfillment_projection(bindings, revision, ir, source_revision=revision.source_revision, exact_target_paths=('index.html',))


@pytest.mark.parametrize('change', ['drop-future', 'wrong-future-owner', 'wrong-gate', 'fake-pass', 'different-source', 'changed-target'])
def test_staged_routes_are_recomputed_instead_of_trusting_receipt(change):
    revision, ir = basis(); bindings = list(admit(revision, ir))
    i = next(i for i,b in enumerate(bindings) if b.evidence_method == REVIEW_METHOD)
    if change == 'drop-future': bindings.pop(i)
    elif change == 'wrong-future-owner': bindings[i] = bindings[i].model_copy(update={'owner':'VERIFICATION'})
    elif change == 'wrong-gate': bindings[i] = bindings[i].model_copy(update={'gate_ref':'delivery:authorized'})
    elif change == 'fake-pass': bindings[i] = bindings[i].model_copy(update={'state':'PASS'})
    elif change == 'different-source': bindings[i] = bindings[i].model_copy(update={'source_quote':'authorized deployment'})
    else: bindings[i] = bindings[i].model_copy(update={'target_paths':('other.html',)})
    with pytest.raises(ValueError): validate_fulfillment_projection(bindings, revision, ir,
        source_revision=revision.source_revision, exact_target_paths=('index.html',))


@pytest.mark.parametrize('permission', [None, 'file.read', 'cloud.deploy', 'remote.publish', 'repository.integrate', 'human.authorize'])
def test_pending_review_checks_actual_armed_envelope_without_claiming_preview_exists(permission):
    revision, ir = basis(); bindings = admit(revision, ir)
    binding = next(b for b in bindings if b.evidence_method == REVIEW_METHOD)
    from spg.domain.governed_obligation import fulfillment_source_ref
    native = SimpleNamespace(binding=SimpleNamespace(obligation_references=(fulfillment_source_ref(binding),),
        capability_grants=() if permission is None else (SimpleNamespace(identity=permission),)))
    assert _review_readiness_pending(binding, revision, ir, bindings, native) is (permission == 'file.read')


def test_safe_compiler_question_remains_advisory_without_becoming_a_human_obligation():
    from spg.application.production_brief import advisory_question_ids
    from spg.domain.governed_obligation import fulfillment_source_ref
    revision, ir = basis('multifile-advisory-source.json.gz')
    before=ir.model_dump()
    optional=advisory_question_ids(ir)
    assert optional==('q_default_view',)
    class NoModel:
        def form(self,*a,**kw):raise AssertionError('Optional default is no production blocker')
    bindings=admitted_fulfillment_bindings(revision,SimpleNamespace(id=revision.source_assessment_id,semantic_ir=ir),
        source_revision=revision.source_revision,exact_target_paths=('index.html','styles.css','app.js'),provider=NoModel())
    assert bindings[0].formation_receipt['advisory_context_item_ids']==list(optional)
    assert not any(b.constraint_item_id in optional for b in bindings)
    assert any(b.constraint_clause_id=='c3' and b.evidence_method=='EXACT_CANDIDATE_CONTENT' for b in bindings)
    assert ir.model_dump()==before
    validate_fulfillment_projection(bindings,revision,ir,source_revision=revision.source_revision,
        exact_target_paths=('index.html','styles.css','app.js'))
    # A real current Human decision cannot be hidden by retaining its annotation.
    changed=ir.model_copy(update={'questions':tuple(q.model_copy(update={'requires_human':True}) for q in ir.questions)})
    assert advisory_question_ids(changed)==()
    with pytest.raises(ValueError):validate_fulfillment_projection(bindings,revision,changed,
        source_revision=revision.source_revision,exact_target_paths=('index.html','styles.css','app.js'))


def test_existing_behavior_acceptance_and_inferred_repository_note_keep_real_owners():
    from spg.application.production_brief import observed_repository_annotation
    from spg.providers.managed_context_fulfillment import _retained_binding_proof
    revision,ir=basis('existing-admitted-source.json.gz')
    bindings=admit(revision,ir)
    assert bindings[0].formation_receipt['source_role_contract']==STAGED_CONTRACT
    assertion=next(f for f in revision.engineering_semantic_facts if f.relation.value=='ACCEPTANCE_ASSERTION')
    assert any(b.fact_id==assertion.id and b.evidence_method=='EXACT_CANDIDATE_CONTENT' for b in bindings)
    annotation=next(f for f in revision.engineering_semantic_facts if f.relation.value=='REFERENCE')
    assert observed_repository_annotation(annotation,ir)
    route=next(b for b in bindings if b.fact_id==annotation.id)
    assert route.state=='RETAINED_CONTEXT' and route.evidence_method=='RETAIN_AUTHORITATIVE_CONTEXT'
    assert _retained_binding_proof(route,revision,ir,bindings)
    changed=annotation.model_copy(update={'value':'unobserved-repository'})
    assert not observed_repository_annotation(changed,ir)
    changed=annotation.model_copy(update={'authority':type(annotation.authority).HUMAN_EXPLICIT})
    assert not observed_repository_annotation(changed,ir)
    validate_fulfillment_projection(bindings,revision,ir,source_revision=revision.source_revision,exact_target_paths=('index.html',))


def test_retained_annotation_revalidates_the_actual_later_formation_episode():
    from spg.application.production_brief import production_brief_bindings
    from spg.application.governed_obligations import fulfillment_inventory
    from spg.providers.managed_context_fulfillment import _retained_context_route
    revision,ir=basis('existing-admitted-source.json.gz')
    inventory=fulfillment_inventory(revision,ir,source_revision=revision.source_revision,
        exact_target_paths=('index.html',),formation_round=3,formation_episode='durable-retry-episode')
    bindings=production_brief_bindings(revision,ir,inventory)
    route=next(b for b in bindings if b.evidence_method=='RETAIN_AUTHORITATIVE_CONTEXT')
    assert _retained_context_route(route,revision,ir,bindings)


def test_current_acceptance_cannot_hide_a_reserved_preview_or_human_gate():
    from spg.application.production_brief import production_brief_bindings
    from spg.application.governed_obligations import fulfillment_inventory
    revision,ir=basis('existing-admitted-source.json.gz')
    ir=ir.model_copy(update={'items':tuple(i.model_copy(update={'production':i.production.model_copy(update={'acceptance_required':True})})
        if i.production else i for i in ir.items)})
    inventory=fulfillment_inventory(revision,ir,source_revision=revision.source_revision,exact_target_paths=('index.html',))
    assert production_brief_bindings(revision,ir,inventory) is None
