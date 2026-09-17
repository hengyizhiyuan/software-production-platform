from types import SimpleNamespace

from spg.application.interaction import (
    WorkInteractionService,
    _declares_distinct_long_lived_object,
    _nonmutating_question,
    _provider_supplied_human_wording,
)
from spg.domain.conversation import ConversationTurnIntent
from spg.domain.interaction import (
    InteractionAssessmentCandidate,
    WorkFocusClassification,
    WorkImpactDisposition,
    WorkSatisfactionState,
)


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
