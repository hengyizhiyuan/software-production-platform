"""Persisted IRK -> Work -> applicability -> WIC regressions on the canonical owners."""
from uuid import UUID, uuid4
from types import SimpleNamespace
from sqlalchemy import select
import pytest
from tests.integration.test_wic_governed_work_admission import (
    clean_schema, _services_for_resource, _admit)
from tests.test_human_interaction_authority import ROUTINE, POSITIVE
from tests.irk_test_fixtures import semantic_candidate, question
from spg.application.interaction import WorkInteractionService
from spg.application.steering_bootstrap import SteeringBootstrapService
from spg.application.guided_design import GuidedDesignApplicationService
from spg.application.human_attention import attention_from_semantic_decisions
from spg.application.human_visible import HumanVisibleRealizationService, validate_wording, safe_wording
from spg.application.human_language import language_leaks
from spg.domain.human_visible import HumanVisibleProjection
from spg.domain.interaction import InteractionAssessmentCandidate
from spg.domain.intent_realization import (SemanticKind,ProductionIntent,HumanDecisionBoundary,
    SemanticArgument,SemanticProvenance,SemanticOrigin,SemanticItem)
from spg.infrastructure.persistence.human_visible_schema import wic_human_realizations

pytestmark=pytest.mark.postgresql

class DeclaredCompiler:
    """An oracle supplies typed meaning; production contains no phrase routing."""
    def __init__(self,positive=None):self.positive=positive
    def interpret(self,basis):
        record=basis.records[-1]
        source=SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,
            source_record_id=record.id,source_text=record.content)
        if self.positive is None:
            optional=SemanticItem(item_id='optional',kind=SemanticKind.QUESTION,
                statement='可逆的视觉细节可以稍后完善',confidence=.6,requires_human=False,
                provenance=(SemanticProvenance(origin=SemanticOrigin.MODEL_CANDIDATE,evidence_reference='compiler:optional'),))
            raw=semantic_candidate(record,production=ProductionIntent(objective=record.content,
                primary_change=record.content,current=True,new_work=True,bounded_change=record.content != ROUTINE[0][1],systemic_design=record.content == ROUTINE[0][1]),extra_items=(optional,),
                questions=(question('可逆内容细节',blocking=False,human=False,reversible=True),))
        else:
            effect,options=self.positive
            raw=semantic_candidate(record,kind=SemanticKind.ANALYSIS).model_copy(update={
                'human_decisions':(HumanDecisionBoundary(subject='官网首版范围或数据权限边界',question=record.content,
                    effect=effect,options=tuple(SemanticArgument(value=o,provenance=source) for o in options),
                    material_effects=('保持当前最小范围，保留可逆的实施路径。','扩展能力或数据权限，需要额外验证和运维责任。'),
                    authority_provenance=source,required_before_production=True,
                    why_now='用户明确保留最终选择，未作选择前不得确定生产范围。'),)})
        return InteractionAssessmentCandidate(interpreted_motive=record.content,desired_outcome=record.content,
            semantic_intent=raw,natural_response='将依据已明确的目标推进，并保留真实授权边界。',
            provider_identity='test:declared-human-interaction')


@pytest.mark.parametrize('identity,text',ROUTINE,ids=[r[0] for r in ROUTINE])
def test_persisted_routine_advances_without_schema_attention(postgres_database,tmp_path,identity,text):
    work,_=_services_for_resource(postgres_database,tmp_path,'test://'+identity)
    interaction=WorkInteractionService(postgres_database,capability=DeclaredCompiler())
    origin=interaction.create_interaction(human_identity='human:test')
    ready=interaction.append_and_assess(origin.id,text,human_identity='human:test')
    admitted=_admit(work,ready)
    rebuilt=interaction.get_shared_understanding(origin.id)
    ir=rebuilt.latest_assessment.semantic_ir
    assert ir.current_production[0].objective==text
    reconstruction=SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)
    guided=GuidedDesignApplicationService(postgres_database)
    projection=guided.get_optional(admitted.work_id)
    if projection is not None:assert projection.readiness.state.value=='READY'
    from spg.infrastructure.persistence.product_store import ProductStore
    with postgres_database.unit_of_work() as u:
        record=ProductStore(u.session).work(admitted.work_id)
    assert all(i.qualification and not i.qualification.blocking for i in guided.qualified_issues(record))
    assert not any(s.design_issue_key for s in reconstruction.active_revision.steps)
    assert reconstruction.current_step.type.value=='DESIGN'
    assert work.list_attention(work_id=admitted.work_id)==()
    assert ir.items[1].requires_human is False  # preserved compiler meaning, not deleted
    assert rebuilt.governed_work_id is not None


@pytest.mark.parametrize('identity,text,effect,options',POSITIVE,ids=[r[0] for r in POSITIVE])
def test_persisted_reserved_choice_has_exact_useful_action(postgres_database,tmp_path,identity,text,effect,options):
    _services_for_resource(postgres_database,tmp_path,'test://'+identity)
    service=WorkInteractionService(postgres_database,capability=DeclaredCompiler((effect,options)))
    interaction=service.create_interaction(human_identity='human:test')
    observed=service.append_and_assess(interaction.id,text,human_identity='human:test')
    rebuilt=service.get_shared_understanding(interaction.id)
    ir=rebuilt.latest_assessment.semantic_ir
    assert ir.human_decisions[0].authority_provenance.source_record_id==rebuilt.records[0].id
    assert ir.current_production==() and rebuilt.governed_work_id is None
    assert rebuilt.latest_assessment.progressive_semantics.selected_question==text
    actions=attention_from_semantic_decisions(ir,product_id=uuid4(),product_name='独立资格产品')
    assert len(actions)==1 and actions[0]['conversation_prompt']==text
    assert tuple(o['label'] for o in actions[0]['human_decision_need']['supported_options'])==options
    assert rebuilt.latest_assessment.progressive_semantics.governance_candidate.value=='HUMAN_DECISION_REQUIRED'


def test_one_realization_per_basis_bounded_repair_never_changes_owner_facts(postgres_database):
    from copy import deepcopy
    from tests.test_human_interaction_authority import declared_ir,presentation
    ir,_=declared_ir(ROUTINE[0][1]);projection,_=presentation(ir)
    projection=projection.model_copy(update={'owner_facts':{'work':{'status':'BLOCKED','current_production_step':'DESIGN'},
        'guardian':{'status':'FINDINGS_PRESENT','gate':'FAIL'},'candidate':None}})
    before=deepcopy(projection.owner_facts)
    class LeakingRealizer:
        calls=0
        def realize_human_projection(self,p,feedback=None):
            self.calls+=1
            return safe_wording(p).model_copy(update={'summary':'MATERIAL_RISK_OR_COST_DECISION'})
    provider=LeakingRealizer();service=HumanVisibleRealizationService(postgres_database,provider)
    first=service.realize(projection);second=service.realize(projection)
    assert first==second and provider.calls==2
    assert first['owner_facts']==before==projection.owner_facts
    assert not language_leaks(first['wording']['summary'])
    assert first['facts']['guardian']=='质量检查发现问题'
    assert first['expression_finding']=='HUMAN_LANGUAGE_LEAKAGE'
    with postgres_database.unit_of_work() as u:
        row=u.session.execute(select(wic_human_realizations).where(
            wic_human_realizations.c.basis_fingerprint==projection.basis_fingerprint)).mappings().one()
        assert row['projection']['owner_facts']==before
