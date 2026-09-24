from types import SimpleNamespace
from uuid import uuid4

from spg.application.interaction import (
    WorkInteractionService,
    _declares_distinct_long_lived_object,
    _nonmutating_question,
    _provider_supplied_human_wording,
)
from spg.domain.conversation import ConversationTurnIntent
from spg.domain.interaction import (
    InteractionAssessmentCandidate,
    InterpretationMeaning,
    InterpretationMeaningKind,
    WorkFocusClassification,
    WorkImpactDisposition,
    WorkSatisfactionState,
)
from spg.domain.response_contract import InteractionMode, ResponseIntent


def test_side_question_new_motive_and_current_feature_edit_remain_distinct() -> None:
    active = SimpleNamespace(work_revision=SimpleNamespace(
        motive="制作三栏页面", desired_outcome="可使用的三栏页面",
        context_facts=(), constraints=(), requests=(),
    ), active_production_binding_id=None,
        satisfaction_state=WorkSatisfactionState.IN_PROGRESS)
    assert _nonmutating_question("有淡入淡出了吗")
    assert _nonmutating_question("这个状态是什么意思？")
    assert not _declares_distinct_long_lived_object("有淡入淡出了吗", active)
    assert _declares_distinct_long_lived_object("再给我做一个计算器应用", active)
    assert not _nonmutating_question("左侧栏改成 120px")
    assert not _declares_distinct_long_lived_object("左侧栏改成 120px", active)

    side = InteractionAssessmentCandidate(
        turn_intent=ConversationTurnIntent.DIRECT_QUESTION,
        focus_classification=WorkFocusClassification.SIDE_QUESTION,
        interpreted_motive=active.work_revision.motive,
        desired_outcome=active.work_revision.desired_outcome,
        natural_response="当前证据还不能确认是否已有淡入淡出。",
        provider_identity="test",
    )
    focus, impact, change = WorkInteractionService._normalize_active_candidate(side, active)
    assert focus is WorkFocusClassification.SIDE_QUESTION
    assert impact is WorkImpactDisposition.NO_GOVERNED_CHANGE
    assert change is None

    different = side.model_copy(update={
        "focus_classification": WorkFocusClassification.UNRELATED_NEW_DEMAND,
    })
    focus, impact, change = WorkInteractionService._normalize_active_candidate(different, active)
    assert focus is WorkFocusClassification.UNRELATED_NEW_DEMAND
    assert impact is WorkImpactDisposition.NEW_WORK_RECOMMENDED
    assert change is None

    refinement = side.model_copy(update={
        "turn_intent": ConversationTurnIntent.MODIFY,
        "focus_classification": WorkFocusClassification.ON_TOPIC,
        "current_requests": ("左侧栏改成 120px",),
    })
    focus, impact, change = WorkInteractionService._normalize_active_candidate(refinement, active)
    assert focus is WorkFocusClassification.ON_TOPIC
    assert impact is WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED
    assert change.changed_fields == ("requests",)


def test_semantic_only_provider_evidence_never_bypasses_visible_realization() -> None:
    assert not _provider_supplied_human_wording({
        "pipeline_mode": "staged", "provider_call_count": 1,
        "conversation_request_id": None,
    })
    assert _provider_supplied_human_wording({
        "pipeline_mode": "staged", "provider_call_count": 2,
        "conversation_request_id": "response-2",
    })
    assert _provider_supplied_human_wording(SimpleNamespace(
        pipeline_mode="coalesced_pre_work", provider_call_count=1,
        conversation_request_id=None,
    ))


def test_explicit_feature_request_survives_design_response_posture() -> None:
    request = (
        "我想在工作面板页上方导航条加个链接，链接的标题是“工律使用文档”，"
        "链接的URL是：https://docs.gonglv.work"
    )
    active = SimpleNamespace(
        work_revision=SimpleNamespace(
            motive="在已有仓库开发新需求",
            desired_outcome="实现并验证新需求",
            context_facts=(), constraints=(), requests=("切个新分支：feat_test",),
            engineering_semantic_facts=(),
        ),
        active_production_binding_id=None,
        satisfaction_state=WorkSatisfactionState.IN_PROGRESS,
    )
    latest_record_id = uuid4()
    candidate = InteractionAssessmentCandidate(
        turn_intent=ConversationTurnIntent.MODIFY,
        response_intent=ResponseIntent(
            interaction_mode=InteractionMode.DESIGN,
            rationale="Discuss the bounded implementation.",
        ),
        focus_classification=WorkFocusClassification.SIDE_QUESTION,
        impact_disposition=WorkImpactDisposition.NO_GOVERNED_CHANGE,
        interpreted_motive="在已有仓库的工作面板页增加文档链接",
        desired_outcome="工作面板页显示工律使用文档链接",
        current_requests=(*active.work_revision.requests, request),
        meanings=(InterpretationMeaning(
            kind=InterpretationMeaningKind.REQUEST,
            statement="Add the requested documentation link.",
            source_record_ids=(latest_record_id,),
            confidence=0.95,
            rationale="The Human explicitly requested this UI change.",
        ),),
        natural_response="I will make the change.",
        provider_identity="test",
    )
    focus, impact, change = WorkInteractionService._normalize_active_candidate(
        candidate, active, latest_human_input=request,
    )
    assert focus is WorkFocusClassification.ON_TOPIC
    assert impact is WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED
    assert change is not None
    assert "requests" in change.changed_fields

    paraphrased = candidate.model_copy(update={
        "current_requests": (*active.work_revision.requests, "Add the requested documentation link."),
    })
    focus, impact, change = WorkInteractionService._normalize_active_candidate(
        paraphrased, active,
        latest_human_input=request,
        latest_human_record_id=latest_record_id,
    )
    assert focus is WorkFocusClassification.ON_TOPIC
    assert impact is WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED
    assert change is not None

    _, unrelated_impact, unrelated_change = WorkInteractionService._normalize_active_candidate(
        paraphrased, active,
        latest_human_input=request,
        latest_human_record_id=uuid4(),
    )
    assert unrelated_impact is WorkImpactDisposition.NO_GOVERNED_CHANGE
    assert unrelated_change is None

    advisory = candidate.model_copy(update={
        "turn_intent": ConversationTurnIntent.DIRECT_QUESTION,
    })
    _, advisory_impact, advisory_change = WorkInteractionService._normalize_active_candidate(
        advisory, active, latest_human_input=request,
    )
    assert advisory_impact is WorkImpactDisposition.NO_GOVERNED_CHANGE
    assert advisory_change is None
