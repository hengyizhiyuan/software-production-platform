from __future__ import annotations

from types import SimpleNamespace

import pytest

from spg.application.interaction_strategy import select_interaction_strategy
from spg.application.wic_response import _content_at_strategy_granularity
from spg.domain.conversation import (
    CognitiveMaturity,
    ConversationalMove,
    HumanAbstractionLevel,
    HumanConversationMode,
)
from spg.domain.wic_intelligence import GovernanceCandidateKind, PatternSignal


def _assessment(
    *signals: PatternSignal,
    governance: GovernanceCandidateKind = GovernanceCandidateKind.CONVERSATION_ONLY,
):
    return SimpleNamespace(
        progressive_semantics=SimpleNamespace(
            pattern_signals=signals,
            governance_candidate=governance,
        )
    )


@pytest.mark.parametrize(
    ("text", "signals", "move", "altitude", "maturity", "mode"),
    (
        (
            "我想做一个企业官网。",
            (),
            ConversationalMove.ORIENT,
            HumanAbstractionLevel.VISION,
            CognitiveMaturity.EXPLORING,
            HumanConversationMode.EXPLORING,
        ),
        (
            "我想做一个面向C端用户的决策助手类小程序。",
            (),
            ConversationalMove.ORIENT,
            HumanAbstractionLevel.SOLUTION,
            CognitiveMaturity.FRAMING,
            HumanConversationMode.EXPLORING,
        ),
        (
            "我们的客户男女比例是3:7，你觉得官网风格应该怎么设计？",
            (PatternSignal.DIRECT_QUESTION,),
            ConversationalMove.PROPOSE,
            HumanAbstractionLevel.SOLUTION,
            CognitiveMaturity.EVALUATING,
            HumanConversationMode.ASKING,
        ),
        (
            "企业官网一般都需要哪些页面？",
            (PatternSignal.DIRECT_QUESTION,),
            ConversationalMove.ANSWER,
            HumanAbstractionLevel.SOLUTION,
            CognitiveMaturity.FRAMING,
            HumanConversationMode.ASKING,
        ),
        (
            "为什么企业官网需要案例页面？",
            (PatternSignal.DIRECT_QUESTION,),
            ConversationalMove.EXPLAIN,
            HumanAbstractionLevel.SOLUTION,
            CognitiveMaturity.FRAMING,
            HumanConversationMode.ASKING,
        ),
        (
            "我其实也不知道该做成什么样。",
            (),
            ConversationalMove.PROPOSE,
            HumanAbstractionLevel.VISION,
            CognitiveMaturity.EXPLORING,
            HumanConversationMode.EXPLORING,
        ),
        (
            "不对，我是要做后台系统。",
            (PatternSignal.EXPLICIT_CORRECTION,),
            ConversationalMove.CONFIRM,
            HumanAbstractionLevel.SOLUTION,
            CognitiveMaturity.SPECIFYING,
            HumanConversationMode.CORRECTING,
        ),
    ),
)
def test_strategy_meets_the_human_at_their_current_altitude(
    text, signals, move, altitude, maturity, mode
) -> None:
    strategy = select_interaction_strategy(
        _assessment(*signals), latest_human_input=text
    )
    assert strategy.primary_move is move
    assert strategy.human_abstraction_level is altitude
    assert strategy.cognitive_maturity is maturity
    assert strategy.human_mode is mode
    assert strategy.max_questions <= 1


def test_broad_motive_allows_one_object_specific_question_after_orientation() -> None:
    strategy = select_interaction_strategy(
        _assessment(), latest_human_input="我想做一个企业官网。"
    )
    assert strategy.primary_move is ConversationalMove.ORIENT
    assert strategy.question_allowed
    assert strategy.max_questions == 1
    assert "actual object" in strategy.question_guidance
    assert "highest-value unresolved concept" in strategy.question_guidance
    assert "fixed discovery sequence" in strategy.question_guidance
    assert "organization or business" not in strategy.question_guidance


def test_human_uncertainty_gets_a_proposal_instead_of_a_questionnaire() -> None:
    strategy = select_interaction_strategy(
        _assessment(), latest_human_input="我其实也不知道该做成什么样。"
    )
    assert strategy.primary_move is ConversationalMove.PROPOSE
    assert not strategy.question_allowed


def test_human_authority_keeps_one_bounded_escalation_question() -> None:
    strategy = select_interaction_strategy(
        _assessment(governance=GovernanceCandidateKind.HUMAN_DECISION_REQUIRED),
        latest_human_input="客户数据能不能交给外部模型？",
    )
    assert strategy.primary_move is ConversationalMove.ESCALATE_HUMAN_DECISION
    assert strategy.question_allowed
    assert strategy.max_questions == 1


@pytest.mark.parametrize(
    ("human_input", "content"),
    (
        ("我想做一个企业官网。", "先明确官网要建立哪种信任。它主要代表什么业务？"),
        ("我想做一个面向C端用户的决策助手类小程序。", "这类产品的关键是缩短选择过程。它首先帮助用户做哪类决定？"),
        ("我想做一个员工请假审批系统。", "先抓住真实审批链路。现在请假通常经过哪些角色？"),
        ("我想做一个日志分析 CLI。", "先确定高频诊断场景。用户最常从哪类日志问题开始排查？"),
        ("我想设计一个工程上下文基础设施。", "先界定它必须稳定承载的责任。哪些上下文需要跨工具保持一致？"),
    ),
)
def test_strategy_preserves_model_selected_object_specific_next_move(
    human_input: str, content: str
) -> None:
    strategy = select_interaction_strategy(
        _assessment(), latest_human_input=human_input
    )
    assert strategy.question_allowed
    assert _content_at_strategy_granularity(content, strategy) == content


def test_strategy_suppresses_but_never_replaces_a_disallowed_question() -> None:
    strategy = select_interaction_strategy(
        _assessment(), latest_human_input="我其实也不知道该做成什么样。"
    )
    content = "可以先比较两种有明确取舍的方向。你更喜欢哪一种？"
    assert not strategy.question_allowed
    assert _content_at_strategy_granularity(content, strategy) == (
        "可以先比较两种有明确取舍的方向。"
    )
