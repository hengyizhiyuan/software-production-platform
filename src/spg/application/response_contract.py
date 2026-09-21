"""Build turn response obligations over admitted interpretation and Reality.

No Human phrase matching lives here. The semantic interpreter selects the mode;
legacy TurnIntent remains a compatibility input. The builder cannot mutate Work,
Semantic Truth, Steering, or authority.
"""

from __future__ import annotations

import unicodedata

from spg.application.production_intelligence import (
    default_system_capability_reality,
    is_system_capability_question,
)
from spg.domain.conversation import ConversationTurnIntent
from spg.domain.engineering_semantics import current_semantic_facts, semantic_fact_statement
from spg.domain.interaction import InteractionActor, InteractionAssessment, InteractionRecord, WorkAdmissionReadinessStatus
from spg.domain.response_contract import (
    AdvancementObligation as Advance,
    CapabilityAlignmentContext,
    CapabilityAlignmentMode,
    DesignCollaborationMode as DesignMode,
    ExploreInteractionStrategy,
    InformationBudget as Budget,
    InteractionMode as Mode,
    JudgmentStance,
    OpeningMove as Opening,
    PrimaryObligation as Obligation,
    ProductionRelevance,
    ResponseContract,
    ResponseIntent,
    ResponseMove as Move,
    ReasoningStep as Reason,
)
from spg.domain.wic_intelligence import (
    GovernanceCandidateKind,
    QuestionDisposition,
    SemanticCategory,
)


_LEGACY_MODES = {
    ConversationTurnIntent.EXPLORE: Mode.EXPLORE,
    ConversationTurnIntent.BUILD: Mode.DESIGN,
    ConversationTurnIntent.NEW_GOAL: Mode.DESIGN,
    ConversationTurnIntent.HOW_TO: Mode.ANSWER,
    ConversationTurnIntent.DIRECT_QUESTION: Mode.ANSWER,
    ConversationTurnIntent.SIDE_QUESTION: Mode.ANSWER,
    ConversationTurnIntent.RECOMMEND: Mode.DECIDE,
    ConversationTurnIntent.REQUEST_RECOMMENDATION: Mode.DECIDE,
    ConversationTurnIntent.COMPARE: Mode.DECIDE,
    ConversationTurnIntent.REQUEST_DECISION_SUPPORT: Mode.DECIDE,
    ConversationTurnIntent.REQUEST_DETAIL: Mode.ANALYZE,
    ConversationTurnIntent.MODIFY: Mode.EXECUTE,
    ConversationTurnIntent.DEPLOY: Mode.EXECUTE,
    ConversationTurnIntent.ACTION_REQUEST: Mode.EXECUTE,
    ConversationTurnIntent.CONTINUE_CURRENT_WORK: Mode.EXECUTE,
    ConversationTurnIntent.CORRECTION: Mode.CORRECT,
    ConversationTurnIntent.DISAGREEMENT: Mode.ANALYZE,
    ConversationTurnIntent.CONTEXT_ADDITION: Mode.DESIGN,
    ConversationTurnIntent.MATERIAL_BRANCH: Mode.DESIGN,
    ConversationTurnIntent.FEEDBACK: Mode.ANALYZE,
    ConversationTurnIntent.HUMAN_DECISION: Mode.EXECUTE,
}

_MODE_SHAPES = {
    Mode.EXPLORE: (Obligation.PROPOSE, Opening.CONTRIBUTION_FIRST, (Move.POSSIBILITIES, Move.USEFUL_DISTINCTIONS), Budget.RELEVANT_DIVERGENCE, Advance.ANSWER_ONLY),
    Mode.ANALYZE: (Obligation.ASSESS, Opening.JUDGMENT_FIRST, (Move.CONCLUSION, Move.REASONING, Move.TRADEOFF), Budget.REASONED_TRADEOFFS, Advance.ANSWER_ONLY),
    Mode.DESIGN: (Obligation.PROPOSE, Opening.RECOMMENDATION_FIRST, (Move.RECOMMENDATION, Move.REASONING, Move.TRADEOFF), Budget.REASONED_TRADEOFFS, Advance.PROPOSE_AND_WAIT),
    Mode.DECIDE: (Obligation.RECOMMEND, Opening.RECOMMENDATION_FIRST, (Move.RECOMMENDATION, Move.DECISIVE_FACTORS, Move.TRADEOFF), Budget.DECISIVE_FACTORS, Advance.PROPOSE_AND_WAIT),
    Mode.ANSWER: (Obligation.ANSWER, Opening.ANSWER_FIRST, (Move.DIRECT_ANSWER, Move.OPTIONAL_ADJACENT_INSIGHT), Budget.MINIMUM_SUFFICIENT, Advance.ANSWER_ONLY),
    Mode.DIAGNOSE: (Obligation.DIAGNOSE, Opening.CAUSE_FIRST, (Move.CAUSE, Move.EVIDENCE, Move.FIX, Move.VERIFY), Budget.FOCUSED_DIAGNOSIS, Advance.ANSWER_ONLY),
    Mode.EXECUTE: (Obligation.EXECUTE, Opening.ACK_AND_EXECUTE, (Move.ACKNOWLEDGE, Move.PROCEED), Budget.MINIMAL_ACKNOWLEDGEMENT, Advance.ACK_AND_EXECUTE),
    Mode.CORRECT: (Obligation.CORRECT, Opening.ACKNOWLEDGE_CORRECTION, (Move.ACKNOWLEDGE, Move.CORRECT_UNDERSTANDING, Move.NEXT_STEP), Budget.CORRECTION_AND_CONTINUE, Advance.ANSWER_AND_PROCEED),
    Mode.STATUS: (Obligation.REPORT_REALITY, Opening.REALITY_FIRST, (Move.CURRENT_REALITY, Move.GAP, Move.NEXT_STEP), Budget.CONCISE_REALITY, Advance.ANSWER_ONLY),
}

_MATERIAL_DIMENSIONS = frozenset({
    "CURRENT_RESULT", "RESULT", "AUTHORITY", "SAFETY", "SAFETY_PRIVACY",
    "PRIVACY", "IRREVERSIBILITY", "COST", "SCOPE", "ACCEPTANCE", "ACCEPTANCE_MEANING",
})
_MATERIAL_CATEGORIES = frozenset({
    SemanticCategory.FACT, SemanticCategory.CONSTRAINT, SemanticCategory.MOTIVE,
    SemanticCategory.DESIRED_OUTCOME, SemanticCategory.HUMAN_DECISION,
})

_DIRECT_PRODUCTION_INTENTS = frozenset({
    ConversationTurnIntent.BUILD,
    ConversationTurnIntent.NEW_GOAL,
    ConversationTurnIntent.MODIFY,
    ConversationTurnIntent.DEPLOY,
    ConversationTurnIntent.ACTION_REQUEST,
    ConversationTurnIntent.CONTINUE_CURRENT_WORK,
    ConversationTurnIntent.MATERIAL_BRANCH,
})
_PRODUCTION_ADVISORY_INTENTS = frozenset({
    ConversationTurnIntent.HOW_TO,
    ConversationTurnIntent.RECOMMEND,
    ConversationTurnIntent.REQUEST_RECOMMENDATION,
    ConversationTurnIntent.COMPARE,
    ConversationTurnIntent.REQUEST_DECISION_SUPPORT,
})


def _capability_alignment(
    assessment: InteractionAssessment,
    intent: ConversationTurnIntent,
    source_records: tuple[InteractionRecord, ...],
) -> CapabilityAlignmentContext:
    """Match this turn to Watt capability without granting production authority."""

    reality = default_system_capability_reality()
    current_work = any((
        assessment.basis_work_revision_id is not None,
        assessment.basis_steering_plan_revision_id is not None,
        assessment.basis_active_runtime_binding_id is not None,
    ))
    design_frame = getattr(assessment, "design_intent_frame", None)
    object_type = None if design_frame is None else design_frame.object_type
    object_match = object_type in set(reality.production_object_types)
    explicit_capability_question = bool(
        source_records
        and is_system_capability_question(source_records[-1].content)
    )
    direct_goal = intent in _DIRECT_PRODUCTION_INTENTS
    advisory_goal = intent in _PRODUCTION_ADVISORY_INTENTS and object_match
    capability_match = (
        direct_goal or advisory_goal or current_work or explicit_capability_question
    )
    if direct_goal and capability_match:
        response_mode = CapabilityAlignmentMode.PRODUCTION
        relevance = ProductionRelevance.DIRECT_PRODUCTION_GOAL
        rationale = (
            "The admitted turn intent requests software-production progression; "
            "existing Work authority and admission rules remain controlling."
        )
    elif advisory_goal and capability_match:
        response_mode = CapabilityAlignmentMode.PRODUCTION_ADVISORY
        relevance = ProductionRelevance.POTENTIAL_PRODUCTION_GOAL
        rationale = (
            "The Human asks how to approach a software-production object that matches "
            "Watt's governed production capability."
        )
    else:
        response_mode = CapabilityAlignmentMode.KNOWLEDGE
        relevance = ProductionRelevance.GENERAL_KNOWLEDGE
        rationale = (
            "The current obligation is a knowledge response; software topic alone does "
            "not justify a production handoff."
        )
    return CapabilityAlignmentContext(
        user_intent=intent,
        production_relevance=relevance,
        current_work_context=current_work,
        watt_capability_match=capability_match,
        response_mode=response_mode,
        explicit_capability_question=explicit_capability_question,
        capability_reality_reference=f"system-capability-reality:{reality.version}",
        rationale=rationale,
    )


def _design_collaboration_mode(
    mode: Mode,
    interpretation: ResponseIntent | None,
) -> DesignMode | None:
    """Refine design collaboration without multiplying top-level interaction modes."""

    requested = (
        None if interpretation is None else interpretation.design_collaboration_mode
    )
    if requested is not None and mode in {
        Mode.EXPLORE, Mode.ANALYZE, Mode.DESIGN, Mode.DECIDE,
    }:
        return requested
    return None


def _reasoning_sequence(
    *,
    mode: Mode,
    capability_mode: CapabilityAlignmentMode,
    design_mode: DesignMode | None,
    obligation: Obligation,
    adjacent_insight_budget: int,
    moves: tuple[Move, ...],
) -> tuple[Reason, ...]:
    """Select presentation order, not private reasoning steps or prose templates."""

    if design_mode is DesignMode.DESIGN_EXPLORE:
        return (
            Reason.CONTEXT_MAP,
            Reason.OPTION_SPACE,
            Reason.COMPARISON,
            Reason.RISKS_AND_CONSTRAINTS,
            Reason.DECISION_POINT,
        )
    if mode is Mode.EXPLORE:
        return (
            Reason.CONTEXT_MAP,
            Reason.OPTION_SPACE,
            Reason.COMPARISON,
            Reason.RISKS_AND_CONSTRAINTS,
            Reason.DECISION_POINT,
        )
    if design_mode is DesignMode.DESIGN_REVIEW:
        return (
            Reason.JUDGMENT,
            Reason.EVIDENCE,
            Reason.RISKS_AND_CONSTRAINTS,
            Reason.TRADE_OFFS,
            Reason.RECOMMENDATION,
        )
    if design_mode is DesignMode.DESIGN_DECIDE:
        return (
            Reason.GOAL,
            Reason.CONSTRAINTS,
            Reason.COMPARISON,
            Reason.TRADE_OFFS,
            Reason.RECOMMENDATION,
        )
    if mode is Mode.DESIGN:
        return (
            Reason.GOAL,
            Reason.CONSTRAINTS,
            Reason.ARCHITECTURE_OPTIONS,
            Reason.TRADE_OFFS,
            Reason.RECOMMENDATION,
        )
    if mode in {Mode.ANALYZE, Mode.DECIDE}:
        return (Reason.JUDGMENT, Reason.EVIDENCE, Reason.TRADE_OFFS, Reason.RECOMMENDATION)
    if mode is Mode.DIAGNOSE:
        return (
            Reason.OBSERVED_SYMPTOM,
            Reason.EVIDENCE,
            Reason.HYPOTHESIS,
            Reason.ROOT_CAUSE,
            Reason.FIX,
        )
    if mode is Mode.EXECUTE and Move.PROCEED in moves:
        return (Reason.ACKNOWLEDGE, Reason.PROCEED, Reason.REPORT_RESULT)
    if mode is Mode.STATUS or obligation is Obligation.REPORT_REALITY:
        return (
            Reason.CURRENT_CONCLUSION,
            Reason.KEY_PROGRESS,
            Reason.CURRENT_OWNER_OR_NEXT_STEP,
            Reason.IMPORTANT_LIMITATION,
        )
    if obligation is Obligation.CLARIFY_BLOCKER:
        return (
            Reason.CURRENT_CONCLUSION,
            Reason.IMPORTANT_LIMITATION,
            Reason.CURRENT_OWNER_OR_NEXT_STEP,
        )
    if mode is Mode.EXECUTE and Move.RECOMMENDATION in moves:
        return (Reason.GOAL, Reason.CONSTRAINTS, Reason.RECOMMENDATION)
    if mode is Mode.CORRECT:
        return (Reason.ACKNOWLEDGE, Reason.CORRECTED_TRUTH, Reason.CONTINUE)
    if (
        mode is Mode.ANSWER
        and capability_mode is CapabilityAlignmentMode.PRODUCTION_ADVISORY
    ):
        return (Reason.DIRECT_ANSWER, Reason.CAPABILITY_ALIGNMENT)
    if mode is Mode.ANSWER:
        sequence = (Reason.DIRECT_ANSWER,)
        return (
            (*sequence, Reason.DECISION_POINT)
            if adjacent_insight_budget
            else sequence
        )
    return (Reason.DIRECT_ANSWER,)


def _source_grounded(value: str, records: tuple[InteractionRecord, ...], *, cited_ids=()) -> bool:
    """Check an existing semantic value against Human source, without reinterpreting it."""
    normalized = "".join(unicodedata.normalize("NFKC", value).casefold().split()).strip("。.!！?？,，;；")
    return bool(normalized) and any(
        record.actor is InteractionActor.HUMAN
        and (not cited_ids or record.id in cited_ids)
        and normalized in "".join(unicodedata.normalize("NFKC", record.content).casefold().split())
        for record in records
    )


def _judgment_sources(assessment: InteractionAssessment, source_records: tuple[InteractionRecord, ...]) -> tuple[dict[str, str | None], set[str]]:
    """Resolve citation aliases to one material identity, preserving record provenance.

    Inventory all available material evidence, not just whichever subset a prior
    response happened to cite. Re-citing an old fact through a new alias cannot
    manufacture a changed premise. Unbound Provider prose remains expression
    context, not independent proof of a new fact or changed Human objective.
    """

    available: dict[str, str | None] = {
        reference: None if reference.startswith(("record:", "interaction_record:", "turn:")) else f"reference:{reference}"
        for reference in assessment.supporting_references
    }
    for field, prefix in (
        (assessment.basis_work_revision_id, "work_revision"),
        (assessment.basis_steering_plan_revision_id, "steering_plan_revision"),
        (assessment.basis_active_runtime_binding_id, "runtime_binding"),
    ):
        if field:
            available[f"{prefix}:{field}"] = None
    for fact in current_semantic_facts(assessment.engineering_semantic_facts):
        statement = semantic_fact_statement(fact)
        references = {f"semantic_fact:{fact.id}", str(fact.id), statement}
        available.update({reference: f"semantic:FACT:{statement}" for reference in references})
    semantics = assessment.progressive_semantics
    if semantics:
        available.update({value: available.get(value) or (f"semantic:FACT:{value}" if _source_grounded(value, source_records) else None) for value in semantics.working_facts})
        available.update({value: available.get(value) or (f"semantic:CONSTRAINT:{value}" if _source_grounded(value, source_records) else None) for value in semantics.working_constraints})
        if semantics.working_motive:
            available[semantics.working_motive] = f"semantic:MOTIVE:{semantics.working_motive}" if _source_grounded(semantics.working_motive, source_records) else None
        if semantics.working_desired_outcome:
            available[semantics.working_desired_outcome] = f"semantic:DESIRED_OUTCOME:{semantics.working_desired_outcome}" if _source_grounded(semantics.working_desired_outcome, source_records) else None
        # Records are provenance, not proof that a professional premise changed.
        available.update({f"record:{item}": None for item in semantics.source_record_ids})
        for delta in semantics.deltas:
            references = {f"semantic_delta:{delta.id}"}
            if delta.value:
                references.add(delta.value)
            identity = f"semantic:{delta.category.value}:{delta.value}" if (
                delta.category in _MATERIAL_CATEGORIES and delta.value
                and _source_grounded(delta.value, source_records, cited_ids=delta.source_record_ids)
            ) else None
            available.update({reference: available.get(reference) or identity for reference in references})
    return available, {identity for identity in available.values() if identity is not None}


def _judgment(
    assessment: InteractionAssessment,
    interpretation: ResponseIntent | None,
    previous: ResponseContract | None,
    source_records: tuple[InteractionRecord, ...],
) -> tuple[JudgmentStance, str | None, str | None, tuple[str, ...], bool, str]:
    if interpretation is None or interpretation.judgment_proposition is None:
        if previous and previous.judgment_proposition:
            return previous.judgment_stance, previous.judgment_subject, previous.judgment_proposition, previous.judgment_basis, False, "Prior judgment retained as advisory trajectory; this turn offered no replacement judgment."
        return JudgmentStance.UNCERTAINTY, None, None, (), False, "No professional proposition was established on this turn."
    available, material = _judgment_sources(assessment, source_records)
    basis = tuple(item for item in interpretation.judgment_basis if item in available)
    stance = interpretation.judgment_stance
    if stance is JudgmentStance.FACT and not any(available[item] is not None for item in basis):
        stance = JudgmentStance.UNCERTAINTY
    proposed = interpretation.judgment_proposition
    subject = interpretation.judgment_subject
    challenge = bool(assessment.progressive_semantics and assessment.progressive_semantics.turn_intent is ConversationTurnIntent.DISAGREEMENT)
    different_subject = bool(previous and subject and previous.judgment_subject and subject != previous.judgment_subject)
    if different_subject and not challenge:
        return stance, subject, proposed, basis, False, "New judgment concerns a different semantic subject; no prior judgment was reversed."
    if previous and previous.judgment_proposition and proposed != previous.judgment_proposition:
        # A new Human record, a new timestamp, or an asserted change alone cannot
        # reverse a judgment. A changed material premise must be actually cited.
        novel_material = material.difference(previous.material_grounding_snapshot)
        cited_material = {available[item] for item in basis if available[item] is not None}
        admissible_change = bool(
            interpretation.judgment_basis_changed
            and interpretation.judgment_change_reason
            and cited_material.intersection(novel_material)
        )
        if not admissible_change:
            return previous.judgment_stance, previous.judgment_subject, previous.judgment_proposition, previous.judgment_basis, False, "Prior judgment retained: no newly cited material evidence established a changed basis."
        return stance, subject or previous.judgment_subject, proposed, basis, True, f"Judgment revised against changed admitted basis: {interpretation.judgment_change_reason}"
    return stance, subject, proposed, basis, False, "Judgment is advisory; its cited basis was checked against current admitted semantics and Reality references."


def build_response_contract(
    assessment: InteractionAssessment,
    *,
    interpretation: ResponseIntent | None = None,
    previous_contract: ResponseContract | None = None,
    source_records: tuple[InteractionRecord, ...] = (),
) -> ResponseContract:
    """Build an immutable expression decision; never admit or advance a Work."""

    semantics = assessment.progressive_semantics
    if semantics and semantics.basis_fingerprint != assessment.basis_fingerprint:
        raise ValueError("Response Contract requires the assessment's exact semantic basis")
    _, grounding_snapshot = _judgment_sources(assessment, source_records)
    intent = semantics.turn_intent if semantics else ConversationTurnIntent.EXPLORE
    capability_alignment = _capability_alignment(assessment, intent, source_records)
    mode = interpretation.interaction_mode if interpretation else _LEGACY_MODES[intent]
    if capability_alignment.response_mode is CapabilityAlignmentMode.PRODUCTION_ADVISORY:
        mode = Mode.ANSWER
    elif capability_alignment.response_mode is CapabilityAlignmentMode.PRODUCTION:
        if intent in {
            ConversationTurnIntent.BUILD,
            ConversationTurnIntent.NEW_GOAL,
            ConversationTurnIntent.MATERIAL_BRANCH,
        } and mode in {Mode.EXPLORE, Mode.ANALYZE, Mode.ANSWER}:
            mode = Mode.DESIGN
        elif intent in {
            ConversationTurnIntent.MODIFY,
            ConversationTurnIntent.DEPLOY,
            ConversationTurnIntent.ACTION_REQUEST,
            ConversationTurnIntent.CONTINUE_CURRENT_WORK,
        } and mode in {Mode.EXPLORE, Mode.ANALYZE, Mode.DESIGN, Mode.ANSWER}:
            mode = Mode.EXECUTE
    if intent is ConversationTurnIntent.DISAGREEMENT:
        mode = Mode.ANALYZE
    elif intent in {ConversationTurnIntent.COMPARE, ConversationTurnIntent.REQUEST_DECISION_SUPPORT} and mode in {Mode.ANALYZE, Mode.ANSWER}:
        # An admitted choice obligation is more specific than generic analysis.
        # Explicit exploration remains exploratory even when comparing ideas.
        mode = Mode.DECIDE
    design_mode = _design_collaboration_mode(mode, interpretation)
    obligation, opening, moves, budget, advancement = _MODE_SHAPES[mode]
    reasons = [
        f"Mode comes from semantic interpretation: {interpretation.rationale}" if interpretation
        else f"Legacy compatibility mode comes from admitted TurnIntent {intent.value}.",
        (
            "Capability alignment evaluated admitted intent, production relevance, "
            "current Work context and System Capability Reality: "
            f"{capability_alignment.response_mode.value}."
        ),
        "Minimum sufficient answer: satisfy the current obligation, then stop; no automatic tutorial or recap.",
    ]
    if interpretation and mode is not interpretation.interaction_mode:
        reasons.append(f"Admitted TurnIntent {intent.value} reconciles the advisory mode to {mode.value}.")
    if design_mode is not None:
        reasons.append(
            f"Design collaboration is refined compositionally as {design_mode.value}; "
            "this is a turn posture, not Product Truth."
        )
    if mode is Mode.DECIDE and intent in {ConversationTurnIntent.COMPARE, ConversationTurnIntent.REQUEST_DECISION_SUPPORT}:
        obligation, opening = Obligation.COMPARE, Opening.JUDGMENT_FIRST
        moves = (Move.COMPARISON, Move.DECISIVE_FACTORS, Move.RECOMMENDATION)
    if mode is Mode.ANALYZE and intent is ConversationTurnIntent.REQUEST_DETAIL:
        obligation = Obligation.EXPLAIN
    if intent is ConversationTurnIntent.DISAGREEMENT:
        # Disagreement is an objection to inspect, not automatically a correction.
        opening, moves = Opening.JUDGMENT_FIRST, (Move.CONCLUSION, Move.ASSESS_OBJECTION, Move.EVIDENCE)
        obligation = Obligation.ASSESS
    if capability_alignment.response_mode is CapabilityAlignmentMode.PRODUCTION_ADVISORY:
        obligation, opening = Obligation.ANSWER, Opening.ANSWER_FIRST
        moves = (Move.DIRECT_ANSWER, Move.ALIGN_WITH_PRODUCTION_CAPABILITY)
        budget, advancement = Budget.MINIMUM_SUFFICIENT, Advance.ANSWER_ONLY
        reasons.append(
            "Capability alignment requires the domain answer first and one factual, "
            "non-promotional production-path connection."
        )

    question = None
    if semantics and semantics.selected_question and mode not in {Mode.STATUS, Mode.ANSWER}:
        candidate = next((item for item in semantics.questions if item.question == semantics.selected_question), None)
        if candidate and (
            candidate.disposition is QuestionDisposition.ASK_HUMAN_NOW
            and candidate.blocks_next_governed_step
            and not candidate.answer_already_available
            and not candidate.safe_reversible_assumption_available
            and not candidate.watt_authorized_to_choose
            and _MATERIAL_DIMENSIONS.intersection(candidate.affected_dimensions)
        ):
            question = candidate.question
    human_boundary = bool(semantics and semantics.governance_candidate is GovernanceCandidateKind.HUMAN_DECISION_REQUIRED and mode not in {Mode.STATUS, Mode.ANSWER, Mode.EXPLORE})
    if human_boundary:
        advancement = Advance.PAUSE_FOR_HUMAN_AUTHORITY
        moves = tuple(move for move in moves if move is not Move.PROCEED)
        if not question and mode is Mode.EXECUTE:
            obligation, opening = Obligation.REPORT_REALITY, Opening.REALITY_FIRST
            moves = (Move.CURRENT_REALITY, Move.GAP, Move.NEXT_STEP)
        reasons.append("Existing semantics reserves a Human-owned boundary; this contract grants no authority.")
    elif question:
        advancement = Advance.ASK_ONE_BLOCKING_QUESTION
    if question:
        moves = (*tuple(move for move in moves if move is not Move.PROCEED), Move.CLARIFY_BLOCKER)
        if mode is Mode.EXECUTE:
            obligation, opening = Obligation.CLARIFY_BLOCKER, Opening.CLARIFICATION_FIRST
        reasons.append("One existing admitted question materially blocks progress and has no available answer or reversible assumption.")
    elif mode is Mode.EXECUTE and not human_boundary:
        # This expresses the desired next move, never claims it already happened.
        if assessment.basis_active_runtime_binding_id is not None:
            advancement = Advance.CONTINUE_PRODUCTION
        elif not (
            (interpretation is not None and interpretation.executable_context)
            or assessment.readiness.status is WorkAdmissionReadinessStatus.READY
            or assessment.basis_work_revision_id is not None
        ):
            advancement = Advance.PROPOSE_AND_WAIT
            opening, moves = Opening.RECOMMENDATION_FIRST, (Move.RECOMMENDATION, Move.GAP)
            reasons.append("Execution was requested but executable context is not established; request the existing governed preparation path without claiming execution.")
    elif mode is Mode.DIAGNOSE and not human_boundary:
        if interpretation and interpretation.executable_context:
            advancement = Advance.ANSWER_AND_PROCEED
        elif intent in {
            ConversationTurnIntent.MODIFY, ConversationTurnIntent.ACTION_REQUEST,
            ConversationTurnIntent.DEPLOY, ConversationTurnIntent.CONTINUE_CURRENT_WORK,
        }:
            advancement = Advance.PROPOSE_AND_WAIT
            reasons.append("The Human requested repair or action; frame preparation through the existing governed path instead of handing debugging back to the Human or claiming execution has started.")

    explore_strategy = None
    if mode is Mode.EXPLORE:
        explore_strategy = (
            ExploreInteractionStrategy.INTENT_REFINEMENT
            if question is not None
            else ExploreInteractionStrategy.OPEN_EXPLORATION
        )
        if explore_strategy is ExploreInteractionStrategy.INTENT_REFINEMENT:
            reasons.append(
                "EXPLORE uses Intent Refinement because the admitted semantic question "
                "is the single highest-value unresolved decision that blocks the next "
                "governed step."
            )
        else:
            reasons.append(
                "EXPLORE remains open exploration because no admitted high-value "
                "question is needed to advance useful understanding."
            )

    stance, subject, proposition, basis, changed, judgment_reason = _judgment(assessment, interpretation, previous_contract, source_records)
    if intent is ConversationTurnIntent.DISAGREEMENT and not changed:
        budget = Budget.DECISIVE_FACTORS
    if previous_contract and previous_contract.judgment_proposition and (
        interpretation is None
        or interpretation.judgment_proposition is None
        or interpretation.judgment_proposition != proposition
    ):
        # Preserve the evidence inventory belonging to the retained judgment,
        # even if an interleaved status turn carries a narrower context slice.
        grounding_snapshot = set(previous_contract.material_grounding_snapshot)
    reasons.append(judgment_reason)
    signature = interpretation.repeated_failure_signature if interpretation else None
    failed = bool(interpretation and interpretation.prior_strategy_failed)
    strategy_revision = 0
    if failed and signature and mode in {Mode.DIAGNOSE, Mode.EXECUTE, Mode.CORRECT}:
        repeated = bool(previous_contract and previous_contract.repeated_failure_signature == signature)
        strategy_revision = previous_contract.strategy_revision + 1 if repeated else 1
        mode, obligation, budget = Mode.DIAGNOSE, Obligation.DIAGNOSE, Budget.FOCUSED_DIAGNOSIS
        design_mode = None
        opening = Opening.REALITY_FIRST
        moves = (
            (Move.ACKNOWLEDGE_FAILED_STRATEGY, Move.CHALLENGE_ASSUMPTIONS, Move.INDEPENDENT_EVIDENCE, Move.CHANGE_DIAGNOSTIC_ROUTE, Move.VERIFY)
            if strategy_revision == 1
            else (Move.ACKNOWLEDGE_FAILED_STRATEGY, Move.STOP_UNPRODUCTIVE_ROUTE, Move.INDEPENDENT_EVIDENCE, Move.CHANGE_DIAGNOSTIC_ROUTE, Move.VERIFY)
        )
        if not human_boundary and not question:
            advancement = Advance.REPLAN_REQUEST
        if question:
            moves = (*moves, Move.CLARIFY_BLOCKER)
        reasons.append("The previous route failed: independently challenge its premise and request a changed diagnostic route; do not repeat the failed local repair.")
    elif previous_contract and not signature:
        # Retain the trajectory signal through status and other interleaved turns.
        signature = previous_contract.repeated_failure_signature
        strategy_revision = previous_contract.strategy_revision

    adjacent_insight_budget = (
        1
        if mode is Mode.ANSWER
        and capability_alignment.response_mode is not CapabilityAlignmentMode.PRODUCTION_ADVISORY
        else 0
    )
    reasoning_sequence = _reasoning_sequence(
        mode=mode,
        capability_mode=capability_alignment.response_mode,
        design_mode=design_mode,
        obligation=obligation,
        adjacent_insight_budget=adjacent_insight_budget,
        moves=moves,
    )

    return ResponseContract(
        basis_fingerprint=assessment.basis_fingerprint,
        source_record_ids=semantics.source_record_ids if semantics else (),
        capability_alignment=capability_alignment,
        interaction_mode=mode,
        explore_strategy=explore_strategy,
        design_collaboration_mode=design_mode,
        primary_obligation=obligation,
        opening_move=opening,
        response_moves=moves,
        reasoning_sequence=reasoning_sequence,
        information_budget=budget,
        question_budget=1 if question else 0,
        selected_question=question,
        judgment_stance=stance,
        judgment_subject=subject,
        judgment_proposition=proposition,
        judgment_basis=basis,
        judgment_change_accepted=changed,
        material_grounding_snapshot=tuple(sorted(grounding_snapshot)),
        advancement_obligation=advancement,
        adjacent_insight_budget=adjacent_insight_budget,
        repeated_failure_signature=signature,
        prior_strategy_failed=failed,
        strategy_revision=strategy_revision,
        decision_basis=tuple(reasons),
    )
