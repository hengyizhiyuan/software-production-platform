"""Deterministic governance policy over one Deep WIC candidate and exact basis."""

from __future__ import annotations

import re
from uuid import NAMESPACE_URL, uuid5

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


_HUMAN_AUTHORITY = re.compile(
    r"(客户数据|个人信息|隐私|外部模型|删除|销毁|不可逆|迁移|付费|预算|权限|保留期|留存)"
)
_SAFE_REVERSIBLE = re.compile(r"(沿用现有规范|现有样式|文案|可撤销|可逆)")
_CORRECTION = re.compile(r"(?:不对|不是|纠正|改口)[，,:：\s]*(.+)")
_NEW_OBJECT = re.compile(r"(?:另外|还有).*(?:我想|我要).*(?:开发|做|创建).*(?:系统|平台|网站|应用)")
_GENERAL_INFORMATION_QUESTION = re.compile(
    r"(?:一般|通常|常见|是什么|有哪些|包括哪些|区别|为什么|怎么理解|需要哪些|"
    r"\bwhat\b|\bwhich\b|\bwhy\b|\bhow\b|\busually\b|\btypically\b|\bcommon\b)",
    re.IGNORECASE,
)
_WORK_INTENT = re.compile(
    r"(?:我想|我要|我们想|我们要|请帮|帮我|开发|创建|搭建|建设|改造|实现|"
    r"\bi want\b|\bwe want\b|\bhelp me\b|\bbuild\b|\bcreate\b|\bimplement\b)",
    re.IGNORECASE,
)


def _correction_target(value: str) -> str:
    reversed_object = re.search(r"不是.+?[，,]是(.+)", value)
    if reversed_object:
        return reversed_object.group(1).strip("。 ")
    positive = re.split(r"[,，]不是", value, maxsplit=1)[0].strip()
    return positive or value.strip("。 ")


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


def _explicit_constraints(text: str) -> tuple[str, ...]:
    if "新增约束" not in text and not any(term in text for term in ("必须", "不得", "不要")):
        return ()
    tail = text.split("：", 1)[-1]
    return tuple(part.strip(" ，。") for part in re.split(r"[；;]", tail) if part.strip(" ，。"))


def build_progressive_semantics(
    *,
    candidate: InteractionAssessmentCandidate,
    records: tuple[InteractionRecord, ...],
    basis_fingerprint: str,
    prior_assessment: InteractionAssessment | None,
    active_context: ActiveWorkInterpretationContext | None,
    focus: WorkFocusClassification | None,
    impact: WorkImpactDisposition | None,
) -> ProgressiveSemanticStructure:
    latest = records[-1]; text = latest.content.strip(); signals: list[PatternSignal] = []
    deltas: list[SemanticDelta] = []; contradictions: list[str] = []
    base_motive = active_context.work_revision.motive if active_context else (prior_assessment.interpreted_motive if prior_assessment else None)
    base_constraints = active_context.work_revision.constraints if active_context else (prior_assessment.candidate_constraints if prior_assessment else ())
    base_facts = active_context.work_revision.context_facts if active_context else (prior_assessment.candidate_context if prior_assessment else ())
    working_motive = candidate.interpreted_motive
    correction = _CORRECTION.search(text)
    if correction:
        signals.append(PatternSignal.EXPLICIT_CORRECTION)
        explicit = correction.group(1).strip("。 ")
        working_motive = _correction_target(explicit)
        deltas.append(_delta(
            SemanticCategory.MOTIVE, SemanticDeltaOperation.SUPERSEDED,
            working_motive, latest, basis_fingerprint, prior=base_motive,
            prior_assessment=prior_assessment,
            rationale="The latest Human Turn explicitly corrects the prior interpretation.",
        ))
    elif working_motive and working_motive != base_motive:
        deltas.append(_delta(
            SemanticCategory.MOTIVE,
            SemanticDeltaOperation.ADDED if base_motive is None else SemanticDeltaOperation.REVISED,
            working_motive, latest, basis_fingerprint, prior=base_motive,
            prior_assessment=prior_assessment,
            rationale="Deep WIC proposed a Motive candidate on the current exact basis.",
        ))

    explicit_constraints = _explicit_constraints(text)
    if explicit_constraints:
        signals.append(PatternSignal.CONSTRAINT_ADDITION)
    constraints = tuple(dict.fromkeys((*base_constraints, *candidate.candidate_constraints, *explicit_constraints)))
    for value in constraints:
        if value not in base_constraints:
            deltas.append(_delta(
                SemanticCategory.CONSTRAINT, SemanticDeltaOperation.ADDED, value,
                latest, basis_fingerprint,
                rationale="Constraint is explicit in the Human Turn or current candidate.",
            ))

    if re.search(r"把.+(?:改成|改为)", text): signals.append(PatternSignal.BOUNDED_CHANGE)
    if text.endswith(("?", "？")): signals.append(PatternSignal.DIRECT_QUESTION)
    if "建议" in text: signals.append(PatternSignal.RECOMMENDATION_REQUEST)
    if _NEW_OBJECT.search(text): signals.append(PatternSignal.NEW_LONG_LIVED_OBJECT)

    human_owned = bool(_HUMAN_AUTHORITY.search(text))
    safe_inference = bool(_SAFE_REVERSIBLE.search(text)) and not human_owned
    decisions: list[str] = []
    if human_owned:
        signals.append(PatternSignal.HIGH_IMPACT_AMBIGUITY)
        decisions.append("Human must decide the material privacy, authority, cost, destructive, or irreversible boundary.")
        deltas.append(_delta(
            SemanticCategory.HUMAN_DECISION, SemanticDeltaOperation.ADDED,
            decisions[0], latest, basis_fingerprint,
            authority=SemanticAuthority.HUMAN_OWNED,
            rationale="Governance-critical policy reserves this decision for the Human.",
        ))

    lower_facts = " ".join(base_facts).casefold()
    if "mysql" in text.casefold() and "postgresql" in lower_facts:
        signals.append(PatternSignal.BROWNFIELD_REALITY_CONFLICT)
        contradictions.append("Human premise says MySQL; governed repository Reality says PostgreSQL.")
        deltas.append(_delta(
            SemanticCategory.FACT, SemanticDeltaOperation.SUPERSEDED,
            "Current persistence uses PostgreSQL.", latest, basis_fingerprint,
            prior="Current persistence uses MySQL.",
            authority=SemanticAuthority.GOVERNED_REALITY,
            rationale="Repository Reality corrects a factual premise without changing Human Motive.",
        ))

    questions: list[QuestionEvaluation] = []
    if human_owned:
        q = "哪些数据可以外发，以及权限和保留期分别由谁批准？" if "客户数据" in text else "请确认这项高影响决定的权限和边界。"
        questions.append(QuestionEvaluation(
            question=q, affected_dimensions=("SAFETY_PRIVACY", "AUTHORITY"),
            answer_already_available=False, safe_reversible_assumption_available=False,
            watt_authorized_to_choose=False, blocks_next_governed_step=True,
            cognitive_cost="MEDIUM", decision_value=100,
            disposition=QuestionDisposition.ASK_HUMAN_NOW,
            rationale="The answer changes a Human-owned high-impact boundary.",
        ))
    for question in candidate.unresolved_material_questions:
        if any(item.disposition is QuestionDisposition.ASK_HUMAN_NOW for item in questions):
            disposition = QuestionDisposition.DEFER_UNTIL_RELEVANT
        elif safe_inference: disposition = QuestionDisposition.INFER_REVERSIBLY
        else: disposition = QuestionDisposition.ASK_HUMAN_NOW
        questions.append(QuestionEvaluation(
            question=question, affected_dimensions=("SCOPE",),
            answer_already_available=False,
            safe_reversible_assumption_available=safe_inference,
            watt_authorized_to_choose=safe_inference,
            blocks_next_governed_step=not safe_inference,
            cognitive_cost="LOW", decision_value=20 if safe_inference else 70,
            disposition=disposition,
            rationale="v1 selects only the highest-value unresolved decision and carries lower-value detail.",
        ))
    selected = next((q.question for q in questions if q.disposition is QuestionDisposition.ASK_HUMAN_NOW), None)
    unresolved = tuple(dict.fromkeys((*decisions, *((selected,) if selected else ()))))

    conversation_only = (
        active_context is None
        and prior_assessment is None
        and PatternSignal.DIRECT_QUESTION in signals
        and bool(_GENERAL_INFORMATION_QUESTION.search(text))
        and not bool(_WORK_INTENT.search(text))
    )
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
