"""Deterministic governance policy over one Deep WIC candidate and exact basis."""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from spg.domain.conversation import ConversationTurnIntent
from spg.domain.interaction import (
    ActiveWorkInterpretationContext, InteractionAssessment,
    InteractionAssessmentCandidate, InteractionRecord,
    WorkFocusClassification, WorkImpactDisposition,
)
from spg.domain.wic_intelligence import (
    GovernanceCandidateKind, InferenceDisposition, PatternSignal,
    ProgressiveSemanticStructure, QuestionDisposition, QuestionEvaluation,
    ReadinessTarget, SemanticAuthority, SemanticCategory, SemanticDelta,
    SemanticDeltaOperation, TransitionReadiness, TransitionReadinessStatus,
)


_QUESTION_COST_RANK = {"LOW": 2, "MEDIUM": 1, "HIGH": 0}


def _delta_id(basis: str, category: SemanticCategory, operation: SemanticDeltaOperation, value: str | None):
    return uuid5(NAMESPACE_URL, f"watt:wic-delta:{basis}:{category.value}:{operation.value}:{value or ''}")


def _delta(category, operation, value, record, basis, *, prior=None, prior_assessment=None, authority=SemanticAuthority.ADVISORY, rationale):
    return SemanticDelta(
        id=_delta_id(basis, category, operation, value), category=category,
        operation=operation, value=value, prior_value=prior,
        source_record_ids=(record.id,), basis_fingerprint=basis,
        prior_assessment_id=None if prior_assessment is None else prior_assessment.id,
        confidence=1.0 if operation is SemanticDeltaOperation.SUPERSEDED else 0.9,
        rationale=rationale, authority=authority,
    )


def build_progressive_semantics(
    *,
    candidate: InteractionAssessmentCandidate,
    records: tuple[InteractionRecord, ...],
    basis_fingerprint: str,
    prior_assessment: InteractionAssessment | None,
    active_context: ActiveWorkInterpretationContext | None,
    focus: WorkFocusClassification | None,
    impact: WorkImpactDisposition | None,
    semantic_ir=None,
) -> ProgressiveSemanticStructure:
    from spg.domain.intent_realization import SemanticKind
    latest = records[-1]
    semantic_ir = semantic_ir or getattr(candidate, "semantic_intent", None)
    items = () if semantic_ir is None else semantic_ir.items
    signals: list[PatternSignal] = []
    deltas: list[SemanticDelta] = []
    contradictions: list[str] = []
    base_motive = active_context.work_revision.motive if active_context else (prior_assessment.interpreted_motive if prior_assessment else None)
    base_constraints = active_context.work_revision.constraints if active_context else (prior_assessment.candidate_constraints if prior_assessment else ())
    base_facts = active_context.work_revision.context_facts if active_context else (prior_assessment.candidate_context if prior_assessment else ())
    correction = next((item for item in items if item.kind is SemanticKind.CORRECTION
        and any(source.origin.value in {"HUMAN_EXPLICIT", "HUMAN_CORRECTION"} for source in item.provenance)), None)
    working_motive = candidate.interpreted_motive or base_motive
    if correction is not None:
        working_motive = correction.statement
    if candidate.turn_intent is ConversationTurnIntent.DISAGREEMENT:
        working_motive = base_motive or working_motive
    if correction:
        signals.append(PatternSignal.EXPLICIT_CORRECTION)
    if working_motive and working_motive != base_motive:
        deltas.append(_delta(SemanticCategory.MOTIVE,
            SemanticDeltaOperation.SUPERSEDED if correction else
            SemanticDeltaOperation.ADDED if base_motive is None else SemanticDeltaOperation.REVISED,
            working_motive, latest, basis_fingerprint, prior=base_motive,
            prior_assessment=prior_assessment, rationale="Consume the governed IRK meaning on the exact current basis."))
    explicit_constraints = tuple(item.statement for item in items if item.kind is SemanticKind.CONSTRAINT)
    if explicit_constraints:
        signals.append(PatternSignal.CONSTRAINT_ADDITION)
    constraints = tuple(dict.fromkeys((*base_constraints, *candidate.candidate_constraints, *explicit_constraints)))
    for value in constraints:
        if value not in base_constraints:
            deltas.append(_delta(SemanticCategory.CONSTRAINT, SemanticDeltaOperation.ADDED, value,
                latest, basis_fingerprint, rationale="IRK-governed constraint; no downstream prose interpretation."))
    production = tuple(item.production for item in items if item.production is not None and item.production.current)
    if production:
        signals.append(PatternSignal.PRODUCTION_REQUEST)
    if any(goal.bounded_change for goal in production):
        signals.append(PatternSignal.BOUNDED_CHANGE)
    if semantic_ir is not None and semantic_ir.repository_source:
        signals.append(PatternSignal.REPOSITORY_SOURCE)
    if any(item.kind in {SemanticKind.QUESTION, SemanticKind.ANALYSIS, SemanticKind.STATUS_QUERY} for item in items):
        signals.append(PatternSignal.DIRECT_QUESTION)
    if focus is WorkFocusClassification.UNRELATED_NEW_DEMAND:
        signals.append(PatternSignal.NEW_LONG_LIVED_OBJECT)
    from spg.application.intent_realization import current_step_semantic_items
    current_items = current_step_semantic_items(semantic_ir)
    human_owned = any(item.requires_human for item in current_items)
    # Reversibility never derives authority from a lexical phrase.
    safe_inference = bool(semantic_ir and any(q.safe_reversible_assumption
        for q in semantic_ir.questions)) and not human_owned
    decisions = [item.statement for item in current_items if item.requires_human]
    if human_owned:
        signals.append(PatternSignal.HIGH_IMPACT_AMBIGUITY)
        for decision in decisions:
            deltas.append(_delta(SemanticCategory.HUMAN_DECISION, SemanticDeltaOperation.ADDED,
                decision, latest, basis_fingerprint, authority=SemanticAuthority.HUMAN_OWNED,
                rationale="The governed semantic item retains an unresolved Human-owned decision."))
    questions: list[QuestionEvaluation] = []
    typed_questions = {} if semantic_ir is None else {q.question: q for q in semantic_ir.questions}
    for question in tuple(dict.fromkeys((*candidate.unresolved_material_questions,
            *typed_questions, *decisions))):
        typed = typed_questions.get(question)
        reversible = bool(typed and typed.safe_reversible_assumption) and not human_owned
        blocking = True if typed is None else typed.blocks_current_step and not reversible
        human_decision = question in decisions or bool(typed and typed.requires_human)
        questions.append(QuestionEvaluation(question=question, affected_dimensions=("SCOPE", "AUTHORITY"),
            answer_already_available=False, safe_reversible_assumption_available=reversible,
            watt_authorized_to_choose=reversible, blocks_next_governed_step=blocking,
            cognitive_cost="LOW", decision_value=100 if human_decision else 70 if typed is None else typed.decision_value,
            disposition=QuestionDisposition.INFER_REVERSIBLY if reversible else QuestionDisposition.DEFER_UNTIL_RELEVANT,
            rationale="Consume the compiler's structured question boundary; inference never grants operational authority."))
    for item in items:
        if item.kind is SemanticKind.CORRECTION and any(source.origin.value == "REPOSITORY_OBSERVED" for source in item.provenance):
            contradictions.append(item.statement)
            signals.append(PatternSignal.BROWNFIELD_REALITY_CONFLICT)
            if item.observed_facts:
                value = "; ".join(f"{key}: {claim.value}" for key, claim in item.observed_facts.items())
                deltas.append(_delta(SemanticCategory.FACT, SemanticDeltaOperation.SUPERSEDED,
                    value, latest, basis_fingerprint, authority=SemanticAuthority.GOVERNED_REALITY,
                    rationale="IRK validated every structured fact against the exact referenced owner observation."))
            else:
                deltas.append(_delta(SemanticCategory.FACT, SemanticDeltaOperation.SUPERSEDED,
                    item.statement, latest, basis_fingerprint, authority=SemanticAuthority.ADVISORY,
                    rationale="Compiler wording alone does not replace owner-observed facts."))
    askable = [
        (index, item)
        for index, item in enumerate(questions)
        if not item.answer_already_available
        and not item.safe_reversible_assumption_available
        and not item.watt_authorized_to_choose
        and item.blocks_next_governed_step
    ]
    if askable:
        winner, _ = max(
            askable,
            key=lambda pair: (
                pair[1].decision_value,
                _QUESTION_COST_RANK[pair[1].cognitive_cost],
                -pair[0],
            ),
        )
        questions[winner] = questions[winner].model_copy(
            update={"disposition": QuestionDisposition.ASK_HUMAN_NOW}
        )
    selected = next(
        (
            item.question
            for item in questions
            if item.disposition is QuestionDisposition.ASK_HUMAN_NOW
        ),
        None,
    )
    unresolved = tuple(dict.fromkeys((*decisions, *((selected,) if selected else ()))))

    conversation_only = active_context is None and not production and bool(items) and all(
        item.kind in {SemanticKind.QUESTION, SemanticKind.ANALYSIS, SemanticKind.STATUS_QUERY,
            SemanticKind.FACT, SemanticKind.CONSTRAINT, SemanticKind.OPERATIONAL_ACTION}
        for item in items)
    if PatternSignal.NEW_LONG_LIVED_OBJECT in signals:
        governance = GovernanceCandidateKind.NEW_MOTIVE_CANDIDATE
    elif human_owned:
        governance = GovernanceCandidateKind.HUMAN_DECISION_REQUIRED
    elif conversation_only:
        governance = GovernanceCandidateKind.CONVERSATION_ONLY
    elif active_context is None:
        governance = GovernanceCandidateKind.WORK_FORMATION_PROPOSAL
    elif impact is WorkImpactDisposition.NO_GOVERNED_CHANGE:
        governance = GovernanceCandidateKind.NO_GOVERNED_CHANGE
    else:
        governance = GovernanceCandidateKind.WORK_REVISION_PROPOSAL

    motive_ok = bool(working_motive and working_motive.strip())
    outcome_ok = bool(candidate.desired_outcome and candidate.desired_outcome.strip())
    blocked = bool(unresolved)
    readiness = (
        TransitionReadiness(
            target=ReadinessTarget.WORK_FORMATION,
            status=TransitionReadinessStatus.READY if active_context is None and not conversation_only and motive_ok and outcome_ok and not blocked else TransitionReadinessStatus.NOT_READY if active_context is None else TransitionReadinessStatus.NOT_APPLICABLE,
            satisfied_evidence=tuple(x for x, ok in (("MOTIVE", motive_ok), ("DESIRED_OUTCOME", outcome_ok)) if ok),
            missing_material_evidence=(
                ("WORK_MOTIVE",)
                if conversation_only
                else tuple(x for x, ok in (("MOTIVE", motive_ok), ("DESIRED_OUTCOME", outcome_ok)) if not ok)
                + (("HIGHEST_VALUE_QUESTION_ANSWER",) if selected else ())
            ),
            unresolved_human_decisions=unresolved, material_risks=("HIGH_IMPACT_AUTHORITY",) if decisions else (),
            useful_work_may_continue=True, basis_fingerprint=basis_fingerprint,
        ),
        TransitionReadiness(
            target=ReadinessTarget.WORK_REVISION,
            status=TransitionReadinessStatus.READY if active_context is not None and not blocked and governance is GovernanceCandidateKind.WORK_REVISION_PROPOSAL else TransitionReadinessStatus.NOT_READY if active_context is not None else TransitionReadinessStatus.NOT_APPLICABLE,
            satisfied_evidence=("ACTIVE_WORK_BASIS",) if active_context else (),
            missing_material_evidence=("HIGHEST_VALUE_QUESTION_ANSWER",) if selected else (), unresolved_human_decisions=unresolved,
            material_risks=("HIGH_IMPACT_AUTHORITY",) if decisions else (), useful_work_may_continue=True,
            basis_fingerprint=basis_fingerprint,
        ),
        TransitionReadiness(
            target=ReadinessTarget.DESIGN_PROGRESSION,
            status=TransitionReadinessStatus.READY if motive_ok or active_context is not None else TransitionReadinessStatus.NOT_READY,
            satisfied_evidence=("CURRENT_FOCUS",) if motive_ok or active_context else (),
            missing_material_evidence=() if motive_ok or active_context else ("CURRENT_FOCUS",),
            unresolved_human_decisions=unresolved, material_risks=(),
            useful_work_may_continue=True, basis_fingerprint=basis_fingerprint,
        ),
    )
    meaning_values: list[str] = []
    if correction:
        meaning_values.append("EXPLICIT_CORRECTION")
    meaning_values.extend(f"CONSTRAINT:{value}" for value in explicit_constraints)
    if contradictions:
        meaning_values.append("FACTUAL_CONTRADICTION")
    if human_owned:
        meaning_values.append("HUMAN_OWNED_DECISION")
    meanings = tuple(dict.fromkeys(meaning_values)) or (
        "DEEP_WIC_WORKING_UNDERSTANDING",
    )
    return ProgressiveSemanticStructure(
        turn_intent=candidate.turn_intent,
        basis_fingerprint=basis_fingerprint,
        source_record_ids=tuple(record.id for record in records),
        reception_meanings=meanings, working_motive=working_motive,
        working_desired_outcome=candidate.desired_outcome,
        working_facts=tuple(dict.fromkeys((*base_facts, *candidate.candidate_context))),
        working_constraints=constraints,
        working_requests=tuple(dict.fromkeys(candidate.current_requests)),
        explicit_assumptions=("Use the existing reversible convention.",) if safe_inference else (),
        unresolved_human_decisions=unresolved, deltas=tuple(deltas),
        pattern_signals=tuple(dict.fromkeys(signals)),
        inference_disposition=InferenceDisposition.HUMAN_OWNED_DECISION if human_owned else InferenceDisposition.SAFE_REVERSIBLE_INFERENCE if safe_inference else InferenceDisposition.NO_INFERENCE,
        questions=tuple(questions), selected_question=selected,
        governance_candidate=governance, readiness=readiness,
        factual_contradictions=tuple(contradictions),
    )
