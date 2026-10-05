"""Typed independent Product Work changes focus without changing the prior Work."""
from uuid import UUID
import pytest
from sqlalchemy import select
from spg.application.product_assets import ProductAssetService
from spg.application.interaction import WorkInteractionService
from spg.domain.interaction import WorkTransitionChoice, InteractionAssessmentCandidate
from spg.domain.intent_realization import ProductionIntent
from spg.infrastructure.persistence.product_schema import product_works
from tests.irk_test_fixtures import semantic_candidate
from tests.integration.test_wic_governed_work_admission import clean_schema, _services_for_resource

class TypedIntent:
    def __init__(self, new_work):
        self.new_work = new_work
    def interpret(self, basis):
        return InteractionAssessmentCandidate(provider_identity='test:typed-independent',
            semantic_intent=semantic_candidate(basis.records[-1], production=ProductionIntent(
                objective='Create an independent contact page' if self.new_work else 'Improve this current contact page',
                primary_change='Create contact.html' if self.new_work else 'Improve contact.html',
                current=True, new_work=self.new_work, bounded_change=True)),
            natural_response='Current governed request recorded')

@pytest.mark.parametrize('independent', [True, False])
def test_typed_new_work_preserves_prior_product_work(postgres_database, tmp_path, independent):
    work, interactions = _services_for_resource(postgres_database, tmp_path, 'test://independent')
    p = ProductAssetService(postgres_database).create('human:test', 'Long-lived qualification Product', provision_source=False)
    interaction = interactions.create_interaction(human_identity='human:test', product_id=UUID(p['id']), start_work_context=False)
    first = interactions.append_and_assess(interaction.id, 'Improve current Product', human_identity='human:test')
    a = work.admit_interaction_work(interaction.id, assessment_id=first.latest_assessment.id,
        basis_fingerprint=first.latest_assessment.basis_fingerprint, authority_identity='human:test')
    with postgres_database.unit_of_work() as u:
        before = dict(u.session.execute(select(product_works).where(product_works.c.id == a.work_id)).mappings().one())
    current = WorkInteractionService(postgres_database, capability=TypedIntent(independent))
    received = current.append_and_assess(interaction.id,
        'Start a distinct bounded Work' if independent else 'Change the current Work', human_identity='human:test')
    if independent:
        assert received.interaction.current_work_id != a.work_id
        assert received.latest_work_transition.choice is WorkTransitionChoice.START_NEW_WORK
        assert received.latest_work_transition.originating_work_id == a.work_id
        assert received.latest_work_transition.decided_by == 'human:test'
        assert received.latest_assessment.basis_work_revision_id is None
        b = work.admit_interaction_work(interaction.id, assessment_id=received.latest_assessment.id,
            basis_fingerprint=received.latest_assessment.basis_fingerprint, authority_identity='human:test')
        assert b.work_id != a.work_id and b.desired_outcome == 'Create contact.html'
    else:
        assert received.interaction.current_work_id == a.work_id
        assert received.latest_work_transition is None
        assert received.latest_assessment.basis_work_revision_id == a.current_work_reality_revision_id
    with postgres_database.unit_of_work() as u:
        after = dict(u.session.execute(select(product_works).where(product_works.c.id == a.work_id)).mappings().one())
        assert before == after
