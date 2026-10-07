"""Intent stays authoritative while outcome definition gates actual production."""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from spg.application.intent_realization import IntentRealizationKernel, IntentRealizationViolation, project_interaction_candidate
from spg.application.interaction import WorkInteractionService
from spg.application.response_contract import build_response_contract
from spg.application.wic_intelligence import build_progressive_semantics
from spg.application.wic_response import policy_governed_response
from spg.domain.intent_realization import (ProductionDefinitionGap, ProductionSufficiency,
    ProductionIntent, SemanticArgument, SemanticOrigin, SemanticProvenance)
from spg.domain.interaction import InteractionAssessmentCandidate
from spg.domain.response_contract import ResponseIntent, InteractionMode
from spg.providers.interaction_contract import _TurnSemanticProviderPayload
from tests.irk_test_fixtures import semantic_candidate, question
from tests.test_response_contract import _assessment, _record

PROPOSAL = '先做一个介绍产品能力、适用场景和联系入口的品牌展示首版，不包含登录和客户后台'
QUESTION = '首版先按这个品牌展示方案做，还是需要包含登录和客户后台？'


def guidance(**updates):
    values = dict(status='GUIDANCE_REQUIRED', reason='真实生产意图清楚，但首版用途及产品能力边界尚未确定',
        gaps=(ProductionDefinitionGap(subject='首版产品目的与能力边界', kind='MATERIAL_OUTCOME',
            consequence='品牌展示和账户服务会改变交付内容、数据责任与验证目标'),),
        proposal=PROPOSAL, proposal_basis='先把产品价值讲清楚，可形成边界有限且便于审查的第一版', question=QUESTION)
    values.update(updates)
    return ProductionSufficiency(**values)


def meaning(record, sufficiency, *, scope=(), bounded=False, questions=()):
    return semantic_candidate(record, production=ProductionIntent(objective='开发工律官网',
        primary_change='创建产品官网首版', current=True, new_work=True, bounded_change=bounded,
        systemic_design=not bounded, scope=scope), questions=questions).model_copy(
            update={'production_sufficiency': sufficiency})


def govern(raw, record, history=(), observations=()):
    basis = SimpleNamespace(interaction=SimpleNamespace(id=record.interaction_id), records=(record,),
        basis_fingerprint='a'*64, governed_semantic_history=history, observed_reality=observations)
    return IntentRealizationKernel().govern(SimpleNamespace(semantic_intent=raw, provider_identity='fixture:compiler'), basis)


def projected(ir, record):
    candidate = project_interaction_candidate(InteractionAssessmentCandidate(
        semantic_intent=ir, natural_response='原始建议', provider_identity='fixture:compiler'), ir)
    semantics = build_progressive_semantics(candidate=candidate, records=(record,), basis_fingerprint=ir.basis_fingerprint,
        prior_assessment=None, active_context=None, focus=candidate.focus_classification, impact=None, semantic_ir=ir)
    readiness = WorkInteractionService._evaluate_readiness(candidate, ir.basis_fingerprint,
        governance_candidate=semantics.governance_candidate, progressive_semantics=semantics)
    return candidate, semantics, readiness


def test_broad_intent_keeps_meaning_and_confidence_but_does_not_admit_execution():
    record = _record('我要开发一个工律的官网')
    ir = govern(meaning(record, guidance()), record)
    assert ir.current_production[0].objective == '开发工律官网'
    assert not ir.items[0].requires_human and ir.items[0].confidence == 1
    candidate, semantics, readiness = projected(ir, record)
    assert readiness.status.value == 'NOT_READY'
    assert 'PRODUCTION_DEFINITION' in readiness.missing_information
    assert semantics.selected_question == QUESTION
    assert sum(q.disposition.value == 'ASK_HUMAN_NOW' for q in semantics.questions) == 1
    owed = IntentRealizationKernel().obligations(ir, uuid4())
    assert owed[0].plane.value == 'WORK' and owed[0].state.value == 'REQUIRES_HUMAN'
    response = policy_governed_response(candidate, semantics, latest_human_input=record.content, active_context=None)
    assert PROPOSAL in response and QUESTION in response
    assert 'risk or cost' not in response and '技术栈' not in response
    assessment = _assessment(semantic_ir=ir, readiness=readiness, progressive_semantics=semantics,
        interpreted_motive=candidate.interpreted_motive, desired_outcome=candidate.desired_outcome)
    contract = build_response_contract(assessment, interpretation=ResponseIntent(interaction_mode=InteractionMode.EXECUTE,
        rationale='Human 请求生产，先确定影响成果范围的首版方向'))
    assert contract.question_budget == 1 and contract.selected_question == QUESTION
    assert contract.opening_move.value == 'RECOMMENDATION_FIRST'
    assert contract.primary_obligation.value == 'PROPOSE'
    assert contract.advancement_obligation.value == 'ASK_ONE_BLOCKING_QUESTION'


@pytest.mark.parametrize('kind', ['SAFE_DEFAULT', 'ROUTINE_HOW'])
def test_defaults_and_execution_mechanics_do_not_create_questions(kind):
    record = _record('给现有官网导航栏增加“联系我们”，链接到已有 contact 页面，其他内容不要改。')
    sufficient = ProductionSufficiency(status='READY', reason='唯一改动、链接目标及保持其余内容的约束都已确定',
        gaps=(ProductionDefinitionGap(subject='既有项目的实现方式', kind=kind,
            consequence='沿用仓库既有实现，执行者负责文件定位及普通技术细节'),))
    ir = govern(meaning(record, sufficient, bounded=True), record)
    _, semantics, readiness = projected(ir, record)
    assert readiness.status.value == 'READY' and semantics.selected_question is None
    assert IntentRealizationKernel().obligations(ir, uuid4())[0].state.value == 'PENDING'


def test_accept_recommendation_binds_exact_previous_scope_and_proceeds():
    first = _record('我要开发一个工律的官网')
    prior = govern(meaning(first, guidance()), first)
    answer = _record('按你的建议来', identity=2, sequence=2)
    accepted = SemanticArgument(value=str(prior.id), provenance=SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,
        source_record_id=answer.id, source_text=answer.content))
    sufficient = ProductionSufficiency(status='READY', reason='当前 Human 已选择上一轮的有限品牌展示建议',
        recommendation_acceptance=accepted)
    current = govern(meaning(answer, sufficient, scope=(PROPOSAL,)), answer, history=(prior,))
    _, semantics, readiness = projected(current, answer)
    assert readiness.status.value == 'READY' and semantics.selected_question is None
    assert current.current_production[0].scope == (PROPOSAL,)
    assert not current.current_production[0].delivery_authorized


def test_accepting_design_recommendation_can_activate_previously_noncurrent_intent():
    first=_record('官网首版先比较品牌展示和客户后台，再让我决定')
    raw=meaning(first,guidance())
    raw=raw.model_copy(update={'items':(raw.items[0].model_copy(update={'production':
        raw.items[0].production.model_copy(update={'current':False,'new_work':False})}),)})
    prior=govern(raw,first)
    assert not prior.current_production
    assert not any(o.plane.value=='WORK' for o in IntentRealizationKernel().obligations(prior,uuid4()))
    answer=_record('按你的建议来',identity=2,sequence=2)
    accepted=ProductionSufficiency(status='READY',reason='Human 现在批准上一轮明确的有限方向，开始当前生产',
        recommendation_acceptance=SemanticArgument(value=str(prior.id),provenance=SemanticProvenance(
            origin=SemanticOrigin.HUMAN_EXPLICIT,source_record_id=answer.id,source_text=answer.content)))
    current=govern(meaning(answer,accepted,scope=(PROPOSAL,)),answer,history=(prior,))
    _,_,readiness=projected(current,answer)
    assert readiness.status.value=='READY'
    assert IntentRealizationKernel().obligations(current,uuid4())[0].plane.value=='WORK'


def test_default_recommendation_is_not_specific_to_websites():
    record=_record('我想做一个团队排班工具，先给我一个能开始的版本建议')
    proposal='建议首版只录入团队成员和每日班次并展示排班表，不加入薪资和外部账号连接'
    definition=guidance(proposal=proposal,proposal_basis='先覆盖可核对的排班闭环，避免默认扩大到财务与外部数据权限',
        question='首版先按这个有限排班方案做，还是需要不同的主要目标？')
    raw=meaning(record,definition)
    raw=raw.model_copy(update={'items':(raw.items[0].model_copy(update={'production':raw.items[0].production.model_copy(
        update={'objective':'创建团队排班工具','primary_change':'形成有限排班首版'})}),)})
    prior=govern(raw,record); _,semantics,readiness=projected(prior,record)
    assert semantics.selected_question==definition.question and readiness.status.value=='NOT_READY'
    answer=_record('按你的建议来',identity=2,sequence=2)
    accepted=ProductionSufficiency(status='READY',reason='Human 明确选择有限排班首版，其他功能保持排除',
        recommendation_acceptance=SemanticArgument(value=str(prior.id),provenance=SemanticProvenance(
            origin=SemanticOrigin.HUMAN_EXPLICIT,source_record_id=answer.id,source_text=answer.content)))
    current=meaning(answer,accepted,scope=(proposal,))
    current=current.model_copy(update={'items':(current.items[0].model_copy(update={'production':current.items[0].production.model_copy(
        update={'objective':'创建团队排班工具','primary_change':'形成有限排班首版'})}),)})
    _,_,ready=projected(govern(current,answer,history=(prior,)),answer)
    assert ready.status.value=='READY'


@pytest.mark.parametrize('problem', ['old-human', 'model', 'wrong-reference', 'scope-lost'])
def test_acceptance_cannot_be_fabricated_or_detached_from_recommendation(problem):
    first = _record('我要开发一个工律的官网'); prior = govern(meaning(first, guidance()), first)
    answer = _record('按你的建议来', identity=2, sequence=2)
    provenance = SemanticProvenance(origin=SemanticOrigin.MODEL_CANDIDATE, evidence_reference='compiler:inference') if problem == 'model' else SemanticProvenance(
        origin=SemanticOrigin.HUMAN_EXPLICIT, source_record_id=first.id if problem == 'old-human' else answer.id,
        source_text=first.content if problem == 'old-human' else answer.content)
    sufficient = ProductionSufficiency(status='READY', reason='当前候选声称已接受首版建议，必须核验精确依据',
        recommendation_acceptance=SemanticArgument(value=str(uuid4()) if problem == 'wrong-reference' else str(prior.id), provenance=provenance))
    with pytest.raises(IntentRealizationViolation):
        govern(meaning(answer, sufficient, scope=() if problem == 'scope-lost' else (PROPOSAL,)), answer, history=(prior,))


def test_accepting_recommendation_does_not_turn_greenfield_into_existing_source_requirement():
    first=_record('我要开发一个工律的官网');prior=govern(meaning(first,guidance()),first)
    answer=_record('按你的建议来',identity=2,sequence=2)
    accepted=ProductionSufficiency(status='READY',reason='当前 Human 只接受首版建议，没有另行选择既有项目源码',
        recommendation_acceptance=SemanticArgument(value=str(prior.id),provenance=SemanticProvenance(
            origin=SemanticOrigin.HUMAN_EXPLICIT,source_record_id=answer.id,source_text=answer.content)))
    raw=meaning(answer,accepted,scope=(PROPOSAL,))
    raw=raw.model_copy(update={'items':(raw.items[0].model_copy(update={'production':
        raw.items[0].production.model_copy(update={'repository_required':True})}),)})
    with pytest.raises(IntentRealizationViolation,match='SOURCE_MEANING_CHANGED'):
        govern(raw,answer,history=(prior,))


def test_guidance_preserves_requested_comparison_analysis():
    from spg.domain.intent_realization import SemanticItem,SemanticKind
    from spg.application.wic_response import production_guidance_content
    record=_record('先分析品牌展示与客户后台的差异，再让我决定')
    raw=meaning(record,guidance())
    comparison='品牌展示只覆盖信息页；客户后台需要身份认证、客户数据和权限验证。'
    item=SemanticItem(item_id='comparison',kind=SemanticKind.ANALYSIS,statement='比较两个首版范围',
        answer=comparison,confidence=1,provenance=raw.items[0].provenance)
    raw=raw.model_copy(update={'items':(*raw.items,item),'clauses':(raw.clauses[0].model_copy(
        update={'semantic_item_ids':(raw.items[0].item_id,item.item_id)}),)})
    ir=govern(raw,record)
    text=production_guidance_content(ir)
    assert comparison in text and PROPOSAL in text and text.count('？')==1


def test_unsupported_context_cannot_be_quoted_as_known_product_context():
    record = _record('开发官网')
    with pytest.raises(IntentRealizationViolation, match='CONTEXT_UNGROUNDED'):
        govern(meaning(record, guidance(context_references=('invented:product',))), record)


@pytest.mark.parametrize('updates', [dict(status='READY'), dict(gaps=()), dict(question=None), dict(proposal=None)])
def test_incomplete_or_contradictory_sufficiency_fails_closed(updates):
    with pytest.raises(ValidationError): guidance(**updates)


def test_fresh_compiler_must_explicitly_assess_production_definition():
    record = _record('创建一个产品')
    raw = meaning(record, None)
    with pytest.raises(ValidationError, match='PRODUCTION_DEFINITION_INCOMPLETE'):
        _TurnSemanticProviderPayload.model_validate(raw.model_dump())
    assert _TurnSemanticProviderPayload.model_validate(meaning(record, guidance()).model_dump()).production_sufficiency


def test_guidance_outranks_reversible_implementation_questions():
    record = _record('开发官网')
    ir = govern(meaning(record, guidance(), questions=(question('布局细节可以稍后确定',
        blocking=False, human=False, reversible=True),)), record)
    _, semantics, readiness = projected(ir, record)
    assert semantics.selected_question == QUESTION and readiness.status.value == 'NOT_READY'


def test_workspace_exposes_concrete_outcome_choice_without_authority_template():
    from spg.application.human_attention import attention_from_semantic_decisions
    from spg.application.human_visible import safe_wording, validate_wording
    from tests.test_human_interaction_authority import presentation
    record=_record('我要开发一个工律的官网');ir=govern(meaning(record,guidance()),record)
    rows=attention_from_semantic_decisions(ir,product_id=uuid4(),product_name='工律')
    assert len(rows)==1 and rows[0]['kind']=='PRODUCTION_DEFINITION_REQUIRED'
    assert rows[0]['actions']==[] and rows[0]['human_decision_need'] is None
    projection,_=presentation(ir)
    words=validate_wording(projection,safe_wording(projection))
    assert words.decisions[0].question==QUESTION and PROPOSAL in words.decisions[0].why_now
    assert '明确授权' not in words.decisions[0].question
