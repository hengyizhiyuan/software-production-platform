"""Deterministic reconciliation and policy-aware Human-facing realization."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from spg.domain.interaction import (
    ActiveWorkInterpretationContext,
    InteractionAssessment,
    InteractionAssessmentCandidate,
)
from spg.domain.wic_intelligence import (
    GovernanceCandidateKind,
    PatternSignal,
    ProgressiveSemanticStructure,
    SemanticAuthority,
    SemanticCategory,
    SemanticDeltaOperation,
)
from spg.domain.wic_reception import FastReceptionCandidate
from spg.domain.wic_response import (
    GovernedResponseEnvelope,
    GovernedResponseRealization,
    ResponseReconciliation,
)


_CLAUSE_BOUNDARIES = frozenset("，,；;。！？!?\n")


def bounded_response_chunks(content: str, *, max_chars: int = 96) -> Iterable[str]:
    """Yield readable clauses without changing the admitted response text."""

    pending = ""
    for character in content:
        pending += character
        if character in _CLAUSE_BOUNDARIES or (
            len(pending) >= max_chars and character.isspace()
        ):
            yield pending
            pending = ""
    if pending:
        yield pending


class GovernedResponsePolicyViolation(ValueError):
    """A Realizer attempted to emit wording forbidden by the envelope."""


class GovernedDeltaGate:
    """Validate bounded clauses before any text becomes Human-visible."""

    def __init__(
        self,
        envelope: GovernedResponseEnvelope,
        emit: Callable[[str], None],
    ) -> None:
        self.envelope = envelope
        self.emit = emit
        self.pending = ""
        self.emitted: list[str] = []

    def feed(self, delta: str) -> None:
        self.pending += delta
        complete: list[str] = []
        start = 0
        for index, character in enumerate(self.pending):
            if character in _CLAUSE_BOUNDARIES:
                complete.append(self.pending[start : index + 1])
                start = index + 1
        self.pending = self.pending[start:]
        for clause in complete:
            self._admit(clause)

    def finish(self) -> str:
        if self.pending:
            self._admit(self.pending)
            self.pending = ""
        content = "".join(self.emitted)
        if not content.strip():
            raise GovernedResponsePolicyViolation(
                "Governed response Realizer produced no admissible content"
            )
        return content

    def _admit(self, clause: str) -> None:
        normalized = clause.casefold()
        forbidden = next(
            (
                claim
                for claim in self.envelope.forbidden_claims
                if claim.casefold() in normalized
            ),
            None,
        )
        if forbidden is not None:
            raise GovernedResponsePolicyViolation(
                f"Realizer emitted a forbidden governed claim: {forbidden}"
            )
        self.emitted.append(clause)
        # Validate the complete clause first, then expose bounded visual chunks.
        # This keeps forbidden phrases atomic at the gate without reverting to
        # whole-response buffering.
        for start in range(0, len(clause), 32):
            self.emit(clause[start : start + 32])


class DeterministicGovernedResponseRealizer:
    """Provider-neutral fallback that streams the admitted wording itself."""

    provider_identity = "watt:governed-response-realizer"
    model_identity = None

    def realize_stream(
        self,
        envelope: GovernedResponseEnvelope,
        *,
        on_response_delta: Callable[[str], None],
    ) -> GovernedResponseRealization:
        for chunk in bounded_response_chunks(envelope.governed_content):
            on_response_delta(chunk)
        return GovernedResponseRealization(
            content=envelope.governed_content,
            provider_identity=self.provider_identity,
        )


def governed_response_envelope(
    assessment: InteractionAssessment,
    *,
    governed_content: str,
    provisional_content: str | None,
    reconciliation: ResponseReconciliation,
) -> GovernedResponseEnvelope:
    """Build the expression handoff exclusively from admitted WIC semantics."""

    semantics = assessment.progressive_semantics
    if semantics is None:
        raise ValueError("Controlled WIC realization requires progressive semantics")
    forbidden: list[str] = []
    if semantics.unresolved_human_decisions or any(
        delta.category is SemanticCategory.HUMAN_DECISION
        and delta.authority is SemanticAuthority.HUMAN_OWNED
        for delta in semantics.deltas
    ):
        forbidden.extend(
            (
                "默认开放全部客户数据",
                "全部客户数据",
                "保留 90 天",
                "保留90天",
                "我会默认客户已经同意",
                "我们默认客户已经同意",
                "assume that the customer has consented",
            )
        )
    if PatternSignal.BROWNFIELD_REALITY_CONFLICT in semantics.pattern_signals:
        forbidden.extend(
            (
                "当前系统使用 MySQL",
                "当前系统使用MySQL",
                "直接修改 MySQL",
                "直接修改MySQL",
                "current system uses MySQL",
            )
        )
    return GovernedResponseEnvelope(
        basis_fingerprint=assessment.basis_fingerprint,
        governed_content=governed_content,
        provisional_content=provisional_content,
        reconciliation=reconciliation,
        working_motive=semantics.working_motive,
        working_desired_outcome=semantics.working_desired_outcome,
        facts_to_preserve=semantics.working_facts,
        constraints_to_preserve=semantics.working_constraints,
        unresolved_human_decisions=semantics.unresolved_human_decisions,
        explicit_assumptions=semantics.explicit_assumptions,
        selected_question=semantics.selected_question,
        governance_candidate=semantics.governance_candidate.value,
        forbidden_claims=tuple(dict.fromkeys(forbidden)),
        source_references=assessment.supporting_references,
        semantic_policy_revision=semantics.semantic_policy_revision,
        question_policy_revision=semantics.question_policy_revision,
        response_language=(
            "zh-CN" if re.search(r"[\u4e00-\u9fff]", governed_content) else "en"
        ),
    )


def _explicit_new_object(text: str) -> str | None:
    match = re.search(
        r"(?:另外|还有).*?(?:我想|我要|想).*?(?:开发|做|创建)(.+?(?:系统|平台|网站|应用))",
        text,
    )
    return None if match is None else match.group(1).strip("，,。 ")


def policy_governed_response(
    candidate: InteractionAssessmentCandidate,
    semantics: ProgressiveSemanticStructure,
    *,
    latest_human_input: str,
    active_context: ActiveWorkInterpretationContext | None,
) -> str:
    """Accept Provider wording only when it agrees with admitted semantic policy."""

    chinese = bool(re.search(r"[\u4e00-\u9fff]", latest_human_input))
    signals = set(semantics.pattern_signals)
    human_owned = any(
        delta.category is SemanticCategory.HUMAN_DECISION
        and delta.authority is SemanticAuthority.HUMAN_OWNED
        for delta in semantics.deltas
    )
    if human_owned:
        if chinese:
            if not re.search(r"(客户数据|个人信息|隐私|外部模型|权限|保留期|留存)", latest_human_input):
                return (
                    "这里涉及必须由你决定的高影响边界。"
                    "我可以先梳理可回退方案、影响范围和验证办法，但不会替你决定预算、删除、迁移或其他不可逆条件。"
                    "请确认允许的范围、审批人和回退条件。"
                )
            return (
                "这里涉及必须由你决定的关键边界：哪些数据可以交给外部模型、谁有访问权限，以及保留多久。"
                "你确认前，我可以继续梳理不依赖这些决定的架构部分，例如数据分级、最小化传输、隔离和审计，"
                "但不会替你设定权限或保留期，也不会默认客户已经同意。"
                "请确认允许外发的数据范围、审批人和保留期限。"
            )
        return (
            "This crosses Human-owned data and authority boundaries: the data allowed outside, "
            "access scope, and retention period require your decision. I can continue with data "
            "classification, minimization, isolation, and audit design, but I will not choose "
            "those boundaries or assume customer consent."
        )

    if PatternSignal.BROWNFIELD_REALITY_CONFLICT in signals:
        governed_fact = next(
            (
                delta.value
                for delta in semantics.deltas
                if delta.category is SemanticCategory.FACT
                and delta.operation is SemanticDeltaOperation.SUPERSEDED
                and delta.authority is SemanticAuthority.GOVERNED_REALITY
            ),
            "Current Repository Reality must be used.",
        )
        if chinese:
            return (
                f"先纠正一个事实：{governed_fact} 你的目标仍然有效；后续方案会沿用当前仓库的真实技术栈，"
                "只调整实现路径，不会把这个事实纠正误当成对你意图的否定。"
            )
        return (
            f"One factual correction first: {governed_fact} Your underlying objective remains "
            "valid; the implementation should follow the repository's actual stack."
        )

    correction = next(
        (
            delta
            for delta in semantics.deltas
            if delta.category is SemanticCategory.MOTIVE
            and delta.operation is SemanticDeltaOperation.SUPERSEDED
        ),
        None,
    )
    if correction is not None and correction.value:
        if chinese:
            return (
                f"明白，你是在纠正设计对象：{correction.value}。"
                "我会从这个修正后的理解继续，之前的对象判断不再作为后续依据。"
            )
        return (
            f"Understood—you are correcting the design object to: {correction.value}. "
            "I will continue from that corrected understanding."
        )

    if PatternSignal.CONSTRAINT_ADDITION in signals:
        additions = tuple(
            delta.value
            for delta in semantics.deltas
            if delta.category is SemanticCategory.CONSTRAINT
            and delta.operation is SemanticDeltaOperation.ADDED
            and delta.value
        )
        retained = tuple(
            value for value in semantics.working_constraints if value not in additions
        )
        if chinese:
            added_text = "；".join(additions) or latest_human_input.strip()
            retained_text = "；".join(retained)
            suffix = (
                f"原有目标和既有约束继续保留：{retained_text}。"
                if retained_text else "当前 Work 的目标和既有范围保持不变。"
            )
            return f"我会把这次输入作为当前 Work 的新增约束处理：{added_text}。{suffix}这不会创建新的 Work。"
        added_text = "; ".join(additions) or latest_human_input.strip()
        retained_text = "; ".join(retained)
        suffix = (
            f" Existing obligations remain: {retained_text}."
            if retained_text else " The current Work objective and scope remain unchanged."
        )
        return f"I will treat this as an added constraint on the current Work: {added_text}.{suffix} This does not create a new Work."

    # New-Work boundaries are a Human decision even when the Provider sounds decisive.
    if semantics.governance_candidate is GovernanceCandidateKind.NEW_MOTIVE_CANDIDATE:
        motive = (
            _explicit_new_object(latest_human_input)
            or candidate.interpreted_motive
            or latest_human_input.strip()
        )
        if chinese:
            return f"这看起来是一个新的长期对象：{motive}。我会保持当前 Work 不变，由你决定是否为它创建新的 Work。"
        return f"This appears to be a new long-lived object: {motive}. The current Work stays unchanged until you decide whether to create a new Work."

    content = candidate.natural_response.strip()
    if not content:
        raise ValueError("Policy-aware response realization produced empty content")
    return content


def reconcile_fast_and_deep(
    fast: FastReceptionCandidate | None,
    semantics: ProgressiveSemanticStructure,
) -> ResponseReconciliation:
    if fast is None:
        return ResponseReconciliation.REFINE
    return reconcile_provisional_intent(fast.provisional_turn_intent, semantics)


def reconcile_provisional_intent(
    intent: str,
    semantics: ProgressiveSemanticStructure,
) -> ResponseReconciliation:
    signals = set(semantics.pattern_signals)
    expected = {
        "CORRECTION": PatternSignal.EXPLICIT_CORRECTION,
        "CONSTRAINT_ADDITION": PatternSignal.CONSTRAINT_ADDITION,
        "BOUNDED_CHANGE": PatternSignal.BOUNDED_CHANGE,
        "POSSIBLE_NEW_OBJECT": PatternSignal.NEW_LONG_LIVED_OBJECT,
        "HUMAN_OWNED_DECISION": PatternSignal.HIGH_IMPACT_AMBIGUITY,
        "DIRECT_QUESTION": PatternSignal.DIRECT_QUESTION,
    }.get(intent)
    if expected is None or expected not in signals:
        return ResponseReconciliation.MATERIAL_CORRECTION
    if PatternSignal.BROWNFIELD_REALITY_CONFLICT in signals:
        return ResponseReconciliation.MATERIAL_CORRECTION
    if intent in {"CORRECTION", "HUMAN_OWNED_DECISION", "POSSIBLE_NEW_OBJECT"}:
        return ResponseReconciliation.CONFIRM
    return ResponseReconciliation.REFINE


def corrected_continuation(deep_content: str, *, chinese: bool) -> str:
    prefix = "我重新核对后，需要修正刚才的理解：" if chinese else "After checking the full context, I need to correct my initial understanding: "
    return prefix + deep_content.lstrip()
