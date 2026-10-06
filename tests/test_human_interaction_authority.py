"""Permanent Human-visible authority regressions; no prose-to-authority routing."""
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4
import pytest
from pydantic import ValidationError
from spg.application.guided_design import (qualify_design_issues,general_product_system_design_issues,
    guided_design_step_specs,GuidedDesignApplicationService)
from spg.application.human_attention import (qualify_human_decision,attention_from_semantic_decisions,
    require_human_decision)
from spg.application.human_visible import safe_wording,validate_wording
from spg.application.human_language import language_leaks,require_human_language
from spg.application.intent_realization import IntentRealizationKernel,IntentRealizationViolation
from spg.domain.intent_realization import (GovernedSemanticIR,ProductionIntent,SemanticOrigin,
    SemanticProvenance,SemanticItem,SemanticKind,HumanDecisionBoundary,SemanticArgument)
from spg.domain.steering import (RealityReference,RealityReferenceKind,HumanDecisionNeed,
    HumanDecisionEffect,HumanDecisionOption,SteeringInvariantViolation)
from spg.domain.human_visible import HumanVisibleProjection,HumanVisibleWording
from tests.irk_test_fixtures import semantic_candidate,question

ROUTINE = (
    ('REG-HI-001','我要开发一个工律的官网'),
    ('REG-HI-002','给官网增加一个关于我们页面'),
    ('REG-HI-003','在导航栏增加联系我们'),
    ('REG-HI-004','做一个简单的公司介绍页'),
    ('REG-HI-005','把首页的公司简介改成新的介绍文字'))
POSITIVE = (
    ('REG-HI-P01','官网第一版是只做品牌展示，还是同时加入登录和客户后台？请先分析差异，再让我决定。',
     'PRODUCT_SCOPE',('只做品牌展示','同时加入登录和客户后台')),
    ('REG-HI-P02','数据应只保存在公司的私有环境，还是允许交给外部云服务？请分析权限与数据边界，再由我决定。',
     'AUTHORITY',('只保存在公司的私有环境','允许交给外部云服务')))


def declared_ir(text, *, positive=None, optional=False):
    record=SimpleNamespace(id=uuid4(),interaction_id=uuid4(),actor='HUMAN',content=text)
    provenance=SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,source_record_id=record.id,source_text=text)
    extra=()
    if optional:
        extra=(SemanticItem(item_id='optional-discovery',kind=SemanticKind.QUESTION,
            statement='可逆的内容和视觉细节可稍后完善，不阻塞首个生产步骤',confidence=.6,
            provenance=(SemanticProvenance(origin=SemanticOrigin.MODEL_CANDIDATE,evidence_reference='compiler:question'),)),)
    raw=semantic_candidate(record,production=None if positive else ProductionIntent(
        objective=text,primary_change=text,current=True,new_work=True,bounded_change=False,systemic_design=True),
        kind=SemanticKind.ANALYSIS if positive else SemanticKind.PRODUCTION_INTENT,
        extra_items=extra,questions=(question('补充素材',blocking=False,human=False,reversible=True),) if optional else ())
    if positive:
        effect,options=positive
        raw=raw.model_copy(update={'human_decisions':(HumanDecisionBoundary(
            subject='当前产品范围及数据权限边界的选择',question=text,effect=effect,
            options=tuple(SemanticArgument(value=o,provenance=provenance) for o in options),
            material_effects=('保持首版目标和权限范围，保留最小可逆生产路径。','扩大产品能力或数据授权范围，改变验证与运维责任。'),
            authority_provenance=provenance,required_before_production=True,
            why_now='Human 已明确要求先比较当前范围，在确定实现及权限之前保留最终选择。'),)})
    basis=SimpleNamespace(interaction=SimpleNamespace(id=record.interaction_id),records=(record,),
        basis_fingerprint='a'*64,observed_reality=(),governed_semantic_history=(),engineering_semantic_facts=())
    candidate=SimpleNamespace(semantic_intent=raw,provider_identity='fixture:declared-compiler')
    ir=IntentRealizationKernel().govern(candidate,basis)
    return ir,record


def presentation(ir, *, guardian=None):
    ref=RealityReference(kind=RealityReferenceKind.WORK_REALITY_REVISION,identity=uuid4())
    checks=qualify_design_issues(general_product_system_design_issues(),ir,(ref,))
    actions=attention_from_semantic_decisions(ir,product_id=uuid4(),product_name='资格产品')
    return HumanVisibleProjection(basis_fingerprint='b'*64,governed_motive=ir.items[0].statement,
        governed_semantic_ir=ir.model_dump(mode='json'),owner_facts={'work':{'status':'READY','current_production_step':'DESIGN'},
            'guardian':guardian or {'gate':'FAIL','status':'FINDINGS_PRESENT'},'candidate':None},
        agenda=({'id':'step','type':'DESIGN','state':'current','title':general_product_system_design_issues()[0].objective},),
        decision_needs=tuple(actions),production_units=(),source_references=(f'semantic-ir:{ir.id}',)),checks


@pytest.mark.parametrize('identity,text',ROUTINE,ids=[r[0] for r in ROUTINE])
def test_routine_regression(identity,text):
    ir,_=declared_ir(text,optional=True)
    assert ir.current_production[0].objective==text
    assert not any(i.requires_human for i in ir.items)
    p,checks=presentation(ir)
    assert all(not i.qualification.blocking for i in checks)
    assert checks[0].qualification.disposition.value=='SATISFIED_BY_EXISTING_REALITY'
    assert GuidedDesignApplicationService._readiness_for_issues(checks).state.value=='READY'
    assert not any(s.design_issue_key for s in guided_design_step_specs(checks))
    assert p.decision_needs==()
    words=validate_wording(p,safe_wording(p))
    assert text in words.summary and not any(language_leaks(v) for v in (words.headline,words.summary,words.current_activity,words.next_step))
    obligations=IntentRealizationKernel().obligations(ir,uuid4())
    assert len(obligations)==1 and obligations[0].plane.value=='WORK'
    assert obligations[0].state.value=='PENDING'


@pytest.mark.parametrize('identity,text,effect,options',POSITIVE,ids=[r[0] for r in POSITIVE])
def test_reserved_human_decision(identity,text,effect,options):
    ir,_=declared_ir(text,positive=(effect,options))
    p,checks=presentation(ir)
    assert sum(i.qualification.blocking for i in checks)==1
    assert len(p.decision_needs)==1
    need=HumanDecisionNeed.model_validate(p.decision_needs[0]['human_decision_need'])
    assert qualify_human_decision(need,evidence=need.evidence,semantic_ir=ir)==()
    assert tuple(o.label for o in need.supported_options)==options
    assert need.effect.value==effect and not need.safe_default_possible
    words=validate_wording(p,safe_wording(p))
    assert words.decisions[0].question==text and not any(language_leaks(v) for v in (words.headline,words.summary,words.current_activity,words.next_step))


def valid_need():
    ir,_=declared_ir(POSITIVE[0][1],positive=POSITIVE[0][2:])
    p,_=presentation(ir)
    return ir,HumanDecisionNeed.model_validate(p.decision_needs[0]['human_decision_need'])


@pytest.mark.parametrize('mutation,expected',[
    ({'safe_default_possible':True},'SAFE_AUTONOMOUS_CONTINUATION'),
    ({'required_now':False},'NOT_REQUIRED_NOW'),
    ({'question':'Choose how to handle a material risk or cost'},'GENERIC_TEMPLATE'),
    ({'governed_semantic_ir_id':uuid4()},'HUMAN_OWNERSHIP_NOT_ESTABLISHED'),
    ({'evidence':(RealityReference(kind=RealityReferenceKind.WORK,identity=uuid4()),)},'OPTIONS_NOT_GROUNDED')])
def test_decision_gate_rejects_unqualified(mutation,expected):
    ir,need=valid_need();invalid=need.model_copy(update=mutation)
    assert expected in qualify_human_decision(invalid,evidence=need.evidence,semantic_ir=ir)
    with pytest.raises(SteeringInvariantViolation,match='ATTENTION_NOT_QUALIFIED'):
        require_human_decision(invalid,evidence=need.evidence,semantic_ir=ir)


def test_generic_enum_or_model_claim_does_not_confer_human_authority():
    ir,need=valid_need()
    assert qualify_human_decision(None,evidence=need.evidence,semantic_ir=ir)==('DECISION_OBJECT_MISSING',)
    ordinary,_=declared_ir(ROUTINE[0][1])
    assert 'HUMAN_OWNERSHIP_NOT_ESTABLISHED' in qualify_human_decision(need,evidence=need.evidence,semantic_ir=ordinary)


@pytest.mark.parametrize('field,value',[('question','?'),('material_effect','risk'),('why_now','now'),('supported_options',())])
def test_decision_object_has_material_structure(field,value):
    _,need=valid_need()
    with pytest.raises(ValidationError):HumanDecisionNeed.model_validate({**need.model_dump(),field:value})


@pytest.mark.parametrize('raw',[
    'MATERIAL_RISK_OR_COST_DECISION','STEERING_DECISION_REQUIRED','DesignIssue','TaskContractRequest',
    'ProductionPlanGraph','oracle_id','basis_fingerprint','Establish the Motive, relevant actors, and problem boundary',
    'Choose how to handle a material risk or cost',str(uuid4()),'f'*64])
def test_normal_language_rejects_internal_representation(raw):
    with pytest.raises(ValueError,match='HUMAN_LANGUAGE_LEAKAGE'):require_human_language(raw)


def test_realizer_cannot_change_typed_owner_outcomes_or_invent_success():
    ir,_=declared_ir(ROUTINE[0][1]);p,_=presentation(ir);before=deepcopy(p.model_dump())
    words=safe_wording(p)
    for claim in ('质量检查通过','验证已通过','已完成本次生产','已经部署'):
        with pytest.raises(ValueError,match='UNSUPPORTED_SUCCESS'):
            validate_wording(p,words.model_copy(update={'summary':claim}))
    with pytest.raises(ValidationError):HumanVisibleWording.model_validate({**words.model_dump(),'guardian':'PASS'})
    assert p.model_dump()==before


def test_realizer_cannot_manufacture_decision_or_copy_owner_objective():
    ir,_=declared_ir(ROUTINE[0][1]);p,_=presentation(ir);words=safe_wording(p)
    with pytest.raises(ValueError,match='INVENTED_DECISION'):
        validate_wording(p,words.model_copy(update={'next_step':'请你决定技术栈？'}))
    with pytest.raises(ValueError,match='HUMAN_LANGUAGE_LEAKAGE'):
        validate_wording(p,words.model_copy(update={'summary':p.agenda[0]['title']}))
    with pytest.raises(ValueError,match='AGENDA_BINDING'):
        validate_wording(p,words.model_copy(update={'agenda':()}))

@pytest.mark.parametrize('always_leak',[False,True])
def test_stream_leak_recovery_keeps_same_basis_and_never_emits_internal_clause(always_leak):
    from tests.test_wic_response_contract_expression import _envelope
    from spg.application.wic_response import realize_with_language_recovery
    from spg.domain.wic_response import GovernedResponseRealization
    envelope=_envelope(None);original=envelope.model_dump();emitted=[]
    class Realizer:
        inputs=[]
        def realize_stream(self,e,on_response_delta):
            self.inputs.append(e)
            value='STEERING_DECISION_REQUIRED。' if len(self.inputs)==1 or always_leak else '当前连接失败，先核对请求是否到达服务。'
            on_response_delta(value)
            return GovernedResponseRealization(content=value,provider_identity='test:wording')
    realizer=Realizer()
    result=realize_with_language_recovery(realizer,envelope,emitted.append)
    assert len(realizer.inputs)==2 and result.structural_repair_count==1
    assert all(e.basis_fingerprint==envelope.basis_fingerprint for e in realizer.inputs)
    assert envelope.model_dump()==original
    assert ''.join(emitted)==result.content and not language_leaks(result.content)
    assert realizer.inputs[1].expression_refinement['same_basis'] is True


def test_cloud_detail_wording_preserves_owner_failure_without_raw_prose():
    from spg.application.human_visible import cloud_presentation,cloud_error_wording
    original={'state':'FAILED','blocker':'FUTURE_RAW_OWNER_REASON','operations':[{'output_summary':'raw debugging evidence'}]}
    result=cloud_presentation(original)
    assert {k:result[k] for k in original}==original
    assert not language_leaks(result['human_visible']['blocker'])
    assert result['human_visible']['status']=='部署失败'
    assert not language_leaks(cloud_error_wording(original['blocker']))


@pytest.mark.parametrize('text',('接下来推进 Steering','依照 IRK 处理','先准备 Task Contract','完成 Guided Design'))
def test_owner_component_names_do_not_leak_into_normal_collaboration(text):
    assert language_leaks(text)
