"""Adaptive Human-facing turn strategy over admitted WIC semantics."""

from __future__ import annotations

import re

from spg.domain.conversation import (
    CognitiveMaturity,
    ConversationalMove,
    HumanAbstractionLevel,
    HumanConversationMode,
    InteractionStrategy,
)
from spg.domain.interaction import InteractionAssessment
from spg.domain.wic_intelligence import (
    GovernanceCandidateKind,
    PatternSignal,
)


_UNCERTAIN = re.compile(r"(不知道|没想好|不确定|拿不准|没有概念|not sure|don't know|do not know)", re.I)
_COMPARE = re.compile(r"(对比|比较|还是|区别|取舍|哪个好|which|compare|versus|\bvs\b)", re.I)
_RECOMMEND = re.compile(r"(建议|应该|怎么设计|如何设计|怎么做|how should|recommend)", re.I)
_EXPLANATION = re.compile(
    r"(为什么|是什么(?:意思)?|怎么理解|解释|原理|\bwhy\b|\bexplain\b|what does .+ mean)",
    re.I,
)
_IMPLEMENTATION = re.compile(
    r"(API|接口|数据库|PostgreSQL|MySQL|表结构|字段|迁移|部署|容器|代码|组件|CSS|SDK|schema|endpoint)",
    re.I,
)
_SPECIFIC = re.compile(r"(\d|必须|不得|只要|比例|期限|预算|优先|具体|exact|must|percent|%)", re.I)
_CORRECTION = re.compile(r"(不对|不是|纠正|改口|我说的是|rather than|correction)", re.I)
_BROAD_GOAL = re.compile(
    r"^(?:我想|我要|希望|打算)(?:做|开发|创建|搭建|建设|设计)|^(?:i want|we want|i'd like)\b",
    re.I,
)
_FORMED_RELATION = re.compile(
    r"(面向|用于|帮助|支持|解决|针对|供.{0,16}使用|\bfor\b|\bhelps?\b|\bused by\b)",
    re.I,
)


def _altitude(text: str) -> HumanAbstractionLevel:
    if _IMPLEMENTATION.search(text):
        return HumanAbstractionLevel.IMPLEMENTATION
    if _BROAD_GOAL.search(text) and not _SPECIFIC.search(text):
        return (
            HumanAbstractionLevel.SOLUTION
            if _FORMED_RELATION.search(text)
            else HumanAbstractionLevel.VISION
        )
    if (
        _SPECIFIC.search(text)
        or _CORRECTION.search(text)
        or text.endswith(("?", "？"))
    ):
        return HumanAbstractionLevel.SOLUTION
    if _UNCERTAIN.search(text):
        return HumanAbstractionLevel.VISION
    return HumanAbstractionLevel.DOMAIN


def select_interaction_strategy(
    assessment: InteractionAssessment,
    *,
    latest_human_input: str,
) -> InteractionStrategy:
    """Choose how to advance without changing admitted meaning or authority."""

    semantics = assessment.progressive_semantics
    if semantics is None:
        raise ValueError("Interaction Strategy requires progressive semantics")
    text = latest_human_input.strip()
    signals = set(semantics.pattern_signals)
    altitude = _altitude(text)
    uncertain = bool(_UNCERTAIN.search(text))
    correcting = PatternSignal.EXPLICIT_CORRECTION in signals or bool(_CORRECTION.search(text))
    asking = PatternSignal.DIRECT_QUESTION in signals or text.endswith(("?", "？"))
    specifying = bool(_SPECIFIC.search(text)) or altitude is HumanAbstractionLevel.IMPLEMENTATION

    if correcting:
        mode = HumanConversationMode.CORRECTING
        maturity = CognitiveMaturity.SPECIFYING
    elif asking:
        mode = HumanConversationMode.ASKING
        maturity = CognitiveMaturity.EVALUATING if (_COMPARE.search(text) or _RECOMMEND.search(text)) else CognitiveMaturity.FRAMING
    elif uncertain:
        mode = HumanConversationMode.EXPLORING
        maturity = CognitiveMaturity.EXPLORING
    elif specifying:
        mode = HumanConversationMode.SPECIFYING
        maturity = CognitiveMaturity.SPECIFYING
    else:
        mode = HumanConversationMode.EXPLORING
        maturity = CognitiveMaturity.FRAMING if altitude is not HumanAbstractionLevel.VISION else CognitiveMaturity.EXPLORING

    question_allowed = False
    question_guidance = None
    max_questions = 0
    if semantics.governance_candidate is GovernanceCandidateKind.HUMAN_DECISION_REQUIRED:
        move = ConversationalMove.ESCALATE_HUMAN_DECISION
        question_allowed = True
        max_questions = 1
        question_guidance = "Ask only for the one Human-owned boundary required to continue safely."
    elif PatternSignal.BROWNFIELD_REALITY_CONFLICT in signals:
        move = ConversationalMove.CORRECT
    elif correcting:
        move = ConversationalMove.CONFIRM
    elif asking and _COMPARE.search(text):
        move = ConversationalMove.COMPARE
    elif asking and _RECOMMEND.search(text):
        move = ConversationalMove.PROPOSE
    elif asking and _EXPLANATION.search(text):
        move = ConversationalMove.EXPLAIN
    elif asking:
        move = ConversationalMove.ANSWER
    elif uncertain:
        move = ConversationalMove.PROPOSE
    elif maturity in {CognitiveMaturity.EXPLORING, CognitiveMaturity.FRAMING}:
        move = ConversationalMove.ORIENT
        question_allowed = True
        max_questions = 1
        question_guidance = (
            "First contribute a useful frame grounded in the actual object and everything the "
            "Human already supplied. Ask at most one question only if its answer would materially "
            "improve the next move. Derive that question from the highest-value unresolved concept "
            "for this specific object, at the Human's current abstraction level. Do not introduce "
            "a domain premise the Human did not supply, repeat known information, or follow a fixed "
            "discovery sequence."
        )
    elif specifying:
        move = ConversationalMove.PROPOSE
    else:
        move = ConversationalMove.ORIENT

    granularity = {
        HumanAbstractionLevel.VISION: "Stay at motive and problem-space level; move down by at most one level.",
        HumanAbstractionLevel.DOMAIN: "Use the supplied context and narrow to one meaningful direction.",
        HumanAbstractionLevel.SOLUTION: "Address the concrete product or design choice before requesting another detail.",
        HumanAbstractionLevel.IMPLEMENTATION: "Respond at implementation level with relevant consequences and trade-offs.",
    }[altitude]
    return InteractionStrategy(
        human_abstraction_level=altitude,
        cognitive_maturity=maturity,
        human_mode=mode,
        primary_move=move,
        next_conversational_granularity=granularity,
        question_allowed=question_allowed,
        max_questions=max_questions,
        question_guidance=question_guidance,
    )
