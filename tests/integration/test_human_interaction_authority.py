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
from spg.domain.human_visible import HumanVisibleProjection, HumanVisibleWording
from spg.domain.interaction import InteractionAssessmentCandidate
from spg.domain.intent_realization import (SemanticKind,ProductionIntent,HumanDecisionBoundary,
    SemanticArgument,SemanticProvenance,SemanticOrigin,SemanticItem,ProductionSufficiency)
from spg.infrastructure.persistence.human_visible_schema import wic_human_realizations

pytestmark=pytest.mark.postgresql

class DeclaredCompiler:
    """An oracle supplies typed meaning; production contains no phrase routing."""
    def __init__(self,positive=None,paths=(),systemic=None):self.positive=positive;self.paths=paths;self.systemic=systemic
    def interpret(self,basis):
        record=basis.records[-1]
        source=SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,
            source_record_id=record.id,source_text=record.content)
        if self.positive is None:
            optional=SemanticItem(item_id='optional',kind=SemanticKind.QUESTION,
                statement='可逆的视觉细节可以稍后完善',confidence=.6,requires_human=False,
                provenance=(SemanticProvenance(origin=SemanticOrigin.MODEL_CANDIDATE,evidence_reference='compiler:optional'),))
            raw=semantic_candidate(record,production=ProductionIntent(objective=record.content,
                primary_change=record.content,target_paths=tuple(SemanticArgument(value=p,provenance=source) for p in self.paths),current=True,new_work=True,bounded_change=not (self.systemic if self.systemic is not None else record.content == ROUTINE[0][1]),systemic_design=self.systemic if self.systemic is not None else record.content == ROUTINE[0][1]),extra_items=(optional,),
                questions=(question('可逆内容细节',blocking=False,human=False,reversible=True),))
        else:
            effect,options=self.positive
            raw=semantic_candidate(record,kind=SemanticKind.ANALYSIS).model_copy(update={
                'human_decisions':(HumanDecisionBoundary(subject='官网首版范围或数据权限边界',question=record.content,
                    effect=effect,options=tuple(SemanticArgument(value=o,provenance=source) for o in options),
                    material_effects=('保持当前最小范围，保留可逆的实施路径。','扩展能力或数据权限，需要额外验证和运维责任。'),
                    authority_provenance=source,required_before_production=True,
                    why_now='用户明确保留最终选择，未作选择前不得确定生产范围。'),)})
        if self.positive is None and record.content == ROUTINE[0][1]:
            from tests.test_guided_interaction_calibration import guidance
            raw=raw.model_copy(update={'production_sufficiency':guidance()})
        elif self.positive is None and basis.governed_semantic_history and basis.governed_semantic_history[-1].production_sufficiency:
            previous=basis.governed_semantic_history[-1]
            raw=raw.model_copy(update={'items':(raw.items[0].model_copy(update={'production':
                raw.items[0].production.model_copy(update={'objective':previous.current_production[0].objective,
                    'primary_change':previous.current_production[0].primary_change,
                    'scope':(previous.production_sufficiency.proposal,)})}),*raw.items[1:]),
                'production_sufficiency':ProductionSufficiency(status='READY',
                    reason='当前 Human 明确接受上一轮有界建议，首版范围已足够确定',
                    recommendation_acceptance=SemanticArgument(value=str(previous.id),provenance=source))})
        return InteractionAssessmentCandidate(interpreted_motive=record.content,desired_outcome=record.content,
            semantic_intent=raw,natural_response='将依据已明确的目标推进，并保留真实授权边界。',
            provider_identity='test:declared-human-interaction')


@pytest.mark.parametrize('identity,text',ROUTINE,ids=[r[0] for r in ROUTINE])
def test_persisted_routine_advances_without_schema_attention(postgres_database,tmp_path,identity,text):
    work,_=_services_for_resource(postgres_database,tmp_path,'test://'+identity)
    interaction=WorkInteractionService(postgres_database,capability=DeclaredCompiler())
    origin=interaction.create_interaction(human_identity='human:test')
    ready=interaction.append_and_assess(origin.id,text,human_identity='human:test')
    if identity=='REG-HI-001':
        assert ready.readiness.status.value=='NOT_READY'
        assert ready.latest_assessment.progressive_semantics.selected_question
        assert ready.latest_assessment.semantic_ir.current_production[0].objective==text
        # Preserve the original invariant (no generic design/risk gate), while
        # accepting one concrete outcome recommendation before production.
        ready=interaction.append_and_assess(origin.id,'按你的建议来',human_identity='human:test')
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


def test_persisted_nonblocking_design_allows_actual_production_cycle(postgres_database,tmp_path):
    from tests.integration.test_wic_governed_work_admission import _UnguidedSemanticCapability,_SchedulingOrchestrator
    from spg.application.steering_driver import PlanSteeringDriver
    from spg.infrastructure.persistence.product_store import ProductStore
    work,_=_services_for_resource(postgres_database,tmp_path,'watt://repositories/hi-production-gate')
    interaction=WorkInteractionService(postgres_database,capability=DeclaredCompiler(paths=('index.html',),systemic=True))
    origin=interaction.create_interaction(human_identity='human:test')
    ready=interaction.append_and_assess(origin.id,'开发工律官网，创建 index.html 首页',human_identity='human:test')
    admitted=_admit(work,ready)
    SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)
    governed=GuidedDesignApplicationService(postgres_database)
    assert governed.get_optional(admitted.work_id) is not None
    assert not governed.requires_design_artifact(admitted.work_id)
    assert governed.approved_design_artifact_references(admitted.work_id)==()
    class RoutineProposal(_UnguidedSemanticCapability):
        def execute(self,input):
            candidate=super().execute(input)
            if candidate.proposed_production:
                candidate=candidate.model_copy(update={'proposed_production':candidate.proposed_production.model_copy(update={
                    'objective':input.desired_outcome,'code_targets':('index.html',),
                    'verification_expectation':'Verify the exact admitted homepage exists and git diff --check passes'})})
            return candidate
    runtime=_SchedulingOrchestrator()
    driver=PlanSteeringDriver(postgres_database,work,runtime,semantic_capability=RoutineProposal(),max_automatic_transitions=8)
    try:
        result=driver.activate(admitted.work_id)
        assert result.stop_reason.value=='PRODUCTION_RUNNING'
        assert runtime.scheduled==[admitted.work_id]
        with postgres_database.unit_of_work() as u:
            binding=ProductStore(u.session).runtime_binding(admitted.work_id)
            assert binding is not None
            summary=ProductStore(u.session).runtime_summary(binding)
            assert summary.extra.get('task_contract_mode')!='DESIGN_ARTIFACT'
        assert work.list_attention(work_id=admitted.work_id)==()
    finally:driver.shutdown()


def test_cached_expression_is_requalified_without_changing_owner_basis(postgres_database):
    from sqlalchemy import update
    from tests.test_human_interaction_authority import declared_ir,presentation
    ir,_=declared_ir(ROUTINE[0][1]);projection,_=presentation(ir)
    first=HumanVisibleRealizationService(postgres_database).realize(projection)
    invalid={**first,'wording':{**first['wording'],'summary':'继续推进 Steering'}}
    with postgres_database.unit_of_work() as u:
        u.session.execute(update(wic_human_realizations).where(
            wic_human_realizations.c.basis_fingerprint==projection.basis_fingerprint).values(realization=invalid))
        u.commit()
    class Renderer:
        calls=0
        def realize_human_projection(self,p,feedback=None):
            self.calls+=1
            return safe_wording(p)
    provider=Renderer();service=HumanVisibleRealizationService(postgres_database,provider)
    corrected=service.realize(projection)
    assert corrected['owner_facts']==first['owner_facts']
    assert corrected['source_references']==first['source_references']
    assert not language_leaks(corrected['wording']['summary'])
    assert service.realize(projection)==corrected and provider.calls==1


def test_workspace_read_never_waits_for_wording_or_uses_an_old_owner_basis(postgres_database):
    from threading import Event
    from tests.test_human_interaction_authority import declared_ir, presentation
    ir,_=declared_ir(ROUTINE[0][1]);projection,_=presentation(ir)
    started=Event();release=Event()
    class SlowWording:
        def realize_human_projection(self,p,feedback=None):
            started.set()
            assert release.wait(10), 'test did not release background wording'
            return safe_wording(p)
    service=HumanVisibleRealizationService(postgres_database,SlowWording())
    try:
        first=service.read(projection)
        assert not release.is_set() and started.wait(2)
        assert first['expression_state']=='PENDING'
        assert first['owner_facts']==projection.owner_facts
        assert first['basis_fingerprint']==projection.basis_fingerprint
        validate_wording(projection,HumanVisibleWording.model_validate(first['wording']))
        # A new exact basis must render its current blocker while the older
        # expression remains in flight. It must never borrow the older wording.
        changed=projection.model_copy(update={'basis_fingerprint':'f'*64,
            'owner_facts':{'work':{'status':'BLOCKED','current_production_step':'PRODUCE'},
                'admission_context':{'status':'NOT_READY','missing_classes':['PRODUCT_INTENT']}}})
        second=service.read(changed)
        assert second['owner_facts']==changed.owner_facts
        assert second['basis_fingerprint']=='f'*64
        assert '生产准备受阻' in second['wording']['summary']
        validate_wording(changed,HumanVisibleWording.model_validate(second['wording']))
    finally:
        release.set();service.shutdown()
    final=service.read(changed)
    assert final['expression_state']=='READY' and final['owner_facts']==second['owner_facts']
