"""Adaptive Human-facing turn strategy over admitted WIC semantics."""

from __future__ import annotations


from spg.domain.conversation import (
    CognitiveMaturity,
    ConversationTurnIntent,
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


def select_interaction_strategy(
    assessment: InteractionAssessment,
    *,
    latest_human_input: str,
) -> InteractionStrategy:
    """Choose how to advance without changing admitted meaning or authority."""

    semantics = assessment.progressive_semantics
    if semantics is None:
        raise ValueError("Interaction Strategy requires progressive semantics")
    signals = set(semantics.pattern_signals)
    intent = getattr(
        semantics, "turn_intent", ConversationTurnIntent.EXPLORE
    )
    ir = getattr(assessment, "semantic_ir", None)
    altitude = HumanAbstractionLevel.DOMAIN if ir is None else HumanAbstractionLevel(ir.human_abstraction_level)
    uncertain = False if ir is None else ir.uncertain
    correcting = (
        intent in {
            ConversationTurnIntent.CORRECTION,
            ConversationTurnIntent.DISAGREEMENT,
        }
        or PatternSignal.EXPLICIT_CORRECTION in signals
    )
    answer_intents = {
        ConversationTurnIntent.DIRECT_QUESTION,
        ConversationTurnIntent.HOW_TO,
        ConversationTurnIntent.SIDE_QUESTION,
    }
    explain_intents = {ConversationTurnIntent.REQUEST_DETAIL}
    build_intents = {
        ConversationTurnIntent.BUILD,
        ConversationTurnIntent.NEW_GOAL,
    }
    recommend_intents = {
        ConversationTurnIntent.RECOMMEND,
        ConversationTurnIntent.REQUEST_RECOMMENDATION,
    }
    compare_intents = {
        ConversationTurnIntent.COMPARE,
        ConversationTurnIntent.REQUEST_DECISION_SUPPORT,
    }
    action_intents = {
        ConversationTurnIntent.MODIFY,
        ConversationTurnIntent.DEPLOY,
        ConversationTurnIntent.ACTION_REQUEST,
        ConversationTurnIntent.CONTINUE_CURRENT_WORK,
        ConversationTurnIntent.MATERIAL_BRANCH,
    }
    specifying = (
        intent in action_intents
        or bool(ir and any(item.kind.value == "CONSTRAINT" for item in ir.items))
        or altitude is HumanAbstractionLevel.IMPLEMENTATION
    )

    if correcting:
        mode = HumanConversationMode.CORRECTING
        maturity = CognitiveMaturity.SPECIFYING
    elif intent in answer_intents | explain_intents | recommend_intents | compare_intents:
        mode = HumanConversationMode.ASKING
        maturity = (
            CognitiveMaturity.EVALUATING
            if intent in recommend_intents | compare_intents
            else CognitiveMaturity.FRAMING
        )
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
    candidate_first = False
    answer_first = False
    if semantics.governance_candidate is GovernanceCandidateKind.HUMAN_DECISION_REQUIRED:
        move = ConversationalMove.ESCALATE_HUMAN_DECISION
        question_allowed = True
        max_questions = 1
        question_guidance = "Ask only for the one Human-owned boundary required to continue safely."
    elif PatternSignal.BROWNFIELD_REALITY_CONFLICT in signals:
        move = ConversationalMove.CORRECT
    elif correcting:
        move = ConversationalMove.CONFIRM
    elif intent in compare_intents:
        move = ConversationalMove.COMPARE
        question_allowed = True
        max_questions = 1
        question_guidance = (
            "Compare the available directions first. Ask one question only when its answer "
            "would materially change the trade-off or recommendation."
        )
    elif intent in recommend_intents:
        move = ConversationalMove.PROPOSE
        candidate_first = True
        question_allowed = True
        max_questions = 1
        question_guidance = (
            "Give the recommendation and its material trade-off first. Ask one question only "
            "when its answer would materially change the recommendation."
        )
    elif intent in answer_intents:
        move = ConversationalMove.ANSWER
        answer_first = True
    elif intent in explain_intents:
        move = ConversationalMove.EXPLAIN
        answer_first = True
    elif intent in build_intents:
        move = ConversationalMove.PROPOSE
        candidate_first = True
        question_allowed = True
        max_questions = 1
        question_guidance = (
            "Offer a concrete, low-commitment candidate for this exact object first. "
            "Only then ask one question if its answer would materially change that candidate. "
            "Do not make the Human invent the starting point or answer a discovery checklist."
        )
    elif uncertain:
        move = ConversationalMove.PROPOSE
        candidate_first = True
    elif intent in action_intents:
        move = ConversationalMove.PROPOSE
        candidate_first = True
        question_allowed = True
        max_questions = 1
        question_guidance = (
            "Propose the bounded change first. Ask one question only for a missing fact that "
            "materially changes the proposed delta or its governed boundary."
        )
    elif intent is ConversationTurnIntent.HUMAN_DECISION:
        move = ConversationalMove.CONFIRM
    elif intent in {
        ConversationTurnIntent.EXPLORE,
        ConversationTurnIntent.CONTEXT_ADDITION,
        ConversationTurnIntent.FEEDBACK,
    }:
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
    else:
        move = ConversationalMove.ORIENT

    granularity = {
        HumanAbstractionLevel.VISION: "Stay at motive and problem-space level; move down by at most one level.",
        HumanAbstractionLevel.DOMAIN: "Use the supplied context and narrow to one meaningful direction.",
        HumanAbstractionLevel.SOLUTION: "Address the concrete product or design choice before requesting another detail.",
        HumanAbstractionLevel.IMPLEMENTATION: "Respond at implementation level with relevant consequences and trade-offs.",
    }[altitude]
    return InteractionStrategy(
        turn_intent=intent,
        human_abstraction_level=altitude,
        cognitive_maturity=maturity,
        human_mode=mode,
        primary_move=move,
        next_conversational_granularity=granularity,
        question_allowed=question_allowed,
        max_questions=max_questions,
        question_guidance=question_guidance,
        candidate_first=candidate_first,
        answer_first=answer_first,
    )
