"""Deterministic reconciliation and policy-aware Human-facing realization."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from spg.domain.interaction import (
    ActiveWorkInterpretationContext,
    InteractionAssessment,
    InteractionAssessmentCandidate,
)
from spg.domain.engineering_semantics import (
    SemanticEpistemicStatus,
    current_semantic_facts,
    semantic_fact_statement,
    semantic_fact_reference,
)
from spg.domain.production_intelligence import ContextCandidate, ContextSource
from spg.application.production_intelligence import (
    ContextAssemblyRequest,
    activity_for_response_contract,
    budget_for_response_contract,
    default_context_orchestrator,
    is_system_capability_question,
    system_capability_context_candidate,
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
from spg.application.interaction_strategy import select_interaction_strategy
from spg.application.response_contract import build_response_contract
from spg.domain.conversation import (
    CognitiveMaturity,
    ConversationContextMessage,
    ConversationalMove,
    HumanConversationMode,
    InteractionStrategy,
)
from spg.domain.response_contract import (
    CapabilityAlignmentMode,
    ResponseContract,
    ResponseMove,
)
from spg.domain.wic_response import (
    GovernedResponseEnvelope,
    GovernedResponseRealization,
    ResponseReconciliation,
)


_CLAUSE_BOUNDARIES = frozenset("，,；;。！？!?\n")
_INTERNAL_CONTRACT_ASSIGNMENT = re.compile(
    r"\b(?:response_contract|interaction_mode|primary_obligation|opening_move|"
    r"response_moves|information_budget|question_budget|judgment_stance|judgment_basis|"
    r"advancement_obligation|adjacent_insight_budget|decision_basis)\b[\"']?\s*[:=]",
    re.I,
)
_INFORMATION_REQUEST = re.compile(
    r"^(?:"
    r"(?:请(?:你|您)?|麻烦(?:你|您)?)(?:先|再|帮忙|帮我|进一步)?"
    r"(?:告诉|确认|说明|选择|补充|提供|告知|回答|指明|说一下|给出)"
    r"|(?:你|您)(?:更)?(?:希望|想要|想|倾向|偏向|选择|打算|需要).*(?:哪|什么|多少|如何|怎么|是否)"
    r"|(?:请问|能否|可否|可不可以|能不能|是否)"
    r"|(?:please\s+)?tell\s+(?:me|us)\b"
    r"|(?:please\s+)?let\s+(?:me|us)\s+know\b"
    r"|please\s+(?:confirm|specify|clarify|choose|provide|share)\b"
    r"|(?:can|could|would|will)\s+you\b"
    r"|(?:what|which|where|when|who|how|why)\s+"
    r"(?:is|are|do|does|did|can|could|would|should|will|have|has)\b"
    r")",
    re.I,
)
_QUESTION_PARTICLE = re.compile(r"(?:吗|么|呢)\s*[。.!！；;，,\n]*$")
_URL = re.compile(r"\b(?:https?://|www\.)[^\s<>\"'`]+", re.I)


def _unquoted_expression(text: str) -> str:
    """Mask quoted/code/URL literals while retaining original character offsets.

    A question mark in an example, an inline program, or a URL query is not an
    information request to the Human. Full prefix context handles literals split
    across streamed clauses without waiting for the complete response.
    """

    masked = list(text)
    quote: str | None = None
    code_width = 0
    closing = {'"': '"', "'": "'", "“": "”", "‘": "’", "「": "」", "『": "』"}
    index = 0
    while index < len(text):
        character = text[index]
        if character == "`" and quote is None:
            end = index + 1
            while end < len(text) and text[end] == "`":
                end += 1
            width = end - index
            if code_width == 0:
                code_width = width
            elif width == code_width:
                code_width = 0
            masked[index:end] = " " * width
            index = end
            continue
        if code_width:
            masked[index] = " "
        elif quote is not None:
            masked[index] = " "
            if character == quote:
                quote = None
        elif character in closing and not (
            character == "'" and index > 0 and text[index - 1].isalnum()
        ):
            quote = closing[character]
            masked[index] = " "
        index += 1
    for match in _URL.finditer(text):
        masked[match.start():match.end()] = " " * len(match.group())
    return "".join(masked)


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
        self.suppressed: list[str] = []
        self.question_count = 0
        self.suppress_remainder = False
        self.suppress_question_sentence = False
        self.question_sentence_counted = False
        self.processed_raw = ""

    def feed(self, delta: str) -> None:
        self.pending += delta
        complete: list[str] = []
        start = 0
        for index, character in enumerate(self.pending):
            # English sentence endings become visible as soon as the following
            # separator arrives. A dot inside a token remains part of that token.
            period_boundary = bool(
                self.envelope.response_contract is not None
                and character == "."
                and index + 1 < len(self.pending)
                and self.pending[index + 1].isspace()
            )
            if character in _CLAUSE_BOUNDARIES or period_boundary:
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
        if self.suppress_remainder:
            self.suppressed.append(clause)
            return
        strategy = self.envelope.interaction_strategy
        contract = self.envelope.response_contract
        prior_length = len(self.processed_raw)
        self.processed_raw += clause
        expression = (
            _unquoted_expression(self.processed_raw)[prior_length:]
            if contract is not None else clause
        )
        sentence_ended = clause.endswith("\n") or clause.rstrip().endswith(
            ("。", ".", "!", "！", "?", "？", ";", "；")
        )
        continuing_question = self.question_sentence_counted
        if sentence_ended:
            self.question_sentence_counted = False
        if self.suppress_question_sentence:
            self.suppressed.append(clause)
            self.suppress_question_sentence = not sentence_ended
            return
        stripped = clause.strip()
        if not stripped:
            if contract is not None and self.emitted:
                # Separators belong to the admitted prose. Removing them turns
                # exploration and design paragraphs into an unreadable block.
                self.emitted.append(clause)
                self.emit(clause)
                return
            self.suppressed.append(clause)
            return
        if contract is not None and _INTERNAL_CONTRACT_ASSIGNMENT.search(clause):
            raise GovernedResponsePolicyViolation(
                "Realizer exposed internal Response Contract metadata"
            )
        if (
            not self.emitted
            and strategy.demonstrate_understanding_without_restating
            and re.match(r"^(?:我理解(?:这次|你|您)|I understand\b)", stripped, re.I)
        ):
            self.suppressed.append(clause)
            return
        question_marks = expression.count("?") + expression.count("？")
        question_act = bool(
            question_marks
            or contract is not None and (
                _INFORMATION_REQUEST.search(expression.strip())
                or _QUESTION_PARTICLE.search(expression.strip())
            )
        )
        question_budget = (
            contract.question_budget
            if contract is not None
            else strategy.max_questions if strategy.question_allowed else 0
        )
        if question_act and not continuing_question and self.question_count >= question_budget:
            self.suppressed.append(clause)
            # A disallowed question must not erase a following cause, answer or
            # repair. Retain the historical terminal suppression only for old
            # envelopes that carry no turn contract.
            self.suppress_remainder = contract is None
            self.suppress_question_sentence = contract is not None and not sentence_ended
            return
        if question_act and not continuing_question:
            self.question_count += 1
            self.question_sentence_counted = not sentence_ended
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
    latest_human_input: str,
    response_contract: ResponseContract | None = None,
    previous_response_contract: ResponseContract | None = None,
    recent_relevant_messages: tuple[ConversationContextMessage, ...] = (),
    production_admission_state: str | None = None,
    repository_acquisition_state: str | None = None,
    production_next_step: str | None = None,
    execution_operation_kind: str | None = None,
    execution_operation_reference: str | None = None,
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
    governed_semantic_claims = tuple(
        semantic_fact_statement(fact)
        for fact in current_semantic_facts(assessment.engineering_semantic_facts)
    )
    governed_semantic_claim_set = set(governed_semantic_claims)
    forbidden.extend(
        statement
        for fact in assessment.engineering_semantic_facts
        if fact.epistemic_status is SemanticEpistemicStatus.SUPERSEDED
        and (statement := semantic_fact_statement(fact))
        not in governed_semantic_claim_set
    )
    strategy = select_interaction_strategy(
        assessment, latest_human_input=latest_human_input
    )
    contract = response_contract or build_response_contract(assessment)
    if contract.basis_fingerprint != assessment.basis_fingerprint:
        raise ValueError("Response Contract must match the admitted turn basis")
    strategy = _strategy_for_response_contract(strategy, contract)
    governed_content = _content_at_strategy_granularity(governed_content, strategy)
    selected_question = contract.selected_question if contract.question_budget else None
    current_facts = current_semantic_facts(assessment.engineering_semantic_facts)
    semantic_references = tuple(
        semantic_fact_reference(fact, work_revision_id=fact.admitted_work_revision_id)
        for fact in current_facts
        if fact.admitted_work_revision_id is not None
    )
    if repository_acquisition_state != "RUNNING":
        forbidden.extend(("正在拉取仓库", "正在获取仓库", "acquiring repository"))
    if repository_acquisition_state != "READY":
        forbidden.extend(("仓库已经准备完成", "代码已经拉取完成", "repository ready"))
    if repository_acquisition_state != "WAITING_FOR_AUTHORIZATION":
        forbidden.extend(("正在等待仓库授权", "waiting for repository authorization"))
    if execution_operation_kind != "DESIGN_ARTIFACT":
        forbidden.extend(("正在写设计文档", "正在生成设计文档", "writing the design document"))
    if execution_operation_kind != "IMPLEMENTATION":
        forbidden.extend(("正在编码", "已经开始实现", "implementation is running"))
    if execution_operation_kind == "IMPLEMENTATION":
        forbidden.extend(
            (
                "接下来先写设计文档",
                "将先生成设计文档",
                "design document is next",
                "will write the design document first",
            )
        )
    context_candidates = [
        ContextCandidate(
            candidate_id="response-contract",
            source=ContextSource.RESPONSE_CONTRACT,
            content=(
                f"{contract.interaction_mode.value}; {contract.primary_obligation.value}; "
                f"information={contract.information_budget.value}; "
                f"questions={contract.question_budget}"
            ),
            source_reference=f"response-contract:{contract.basis_fingerprint}",
            authority=contract.authority,
            provenance=tuple(str(item) for item in contract.source_record_ids)
            or (f"interaction-basis:{contract.basis_fingerprint}",),
            priority=95,
            required=True,
        )
    ]
    context_candidates.append(
        system_capability_context_candidate(
            required=(
                is_system_capability_question(latest_human_input)
                or contract.capability_alignment.response_mode
                is not CapabilityAlignmentMode.KNOWLEDGE
            )
        )
    )
    if current_facts:
        context_candidates.append(
            ContextCandidate(
                candidate_id="current-semantic-truth",
                source=ContextSource.SEMANTIC_TRUTH,
                content="; ".join(semantic_fact_statement(fact) for fact in current_facts),
                source_reference=(
                    "semantic-facts:" + ",".join(str(fact.id) for fact in current_facts)
                ),
                authority="ENGINEERING_SEMANTIC_TRUTH",
                provenance=tuple(
                    f"work-reality-revision:{fact.admitted_work_revision_id}"
                    for fact in current_facts
                    if fact.admitted_work_revision_id is not None
                )
                or (f"interaction-basis:{assessment.basis_fingerprint}",),
                priority=100,
                authoritative=True,
                required=True,
            )
        )
    context_candidates.extend(
        ContextCandidate(
            candidate_id=f"source-reference:{index}",
            source=ContextSource.ECF_REALITY,
            content=reference,
            source_reference=reference,
            authority="SOURCE_OWNED_REFERENCE",
            provenance=(reference,),
            priority=70,
        )
        for index, reference in enumerate(assessment.supporting_references, start=1)
    )
    cognitive_context = default_context_orchestrator().assemble(
        ContextAssemblyRequest(
            basis_fingerprint=assessment.basis_fingerprint,
            purpose="Governed Human-facing response",
            activity=activity_for_response_contract(contract),
            candidates=tuple(context_candidates),
            semantic_facts=semantic_references,
            budget=budget_for_response_contract(contract),
        )
    )
    return GovernedResponseEnvelope(
        basis_fingerprint=assessment.basis_fingerprint,
        governed_content=governed_content,
        provisional_content=provisional_content,
        reconciliation=reconciliation,
        working_motive=semantics.working_motive,
        working_desired_outcome=semantics.working_desired_outcome,
        facts_to_preserve=tuple(
            dict.fromkeys((*semantics.working_facts, *governed_semantic_claims))
        ),
        semantic_truth_to_preserve=governed_semantic_claims,
        constraints_to_preserve=semantics.working_constraints,
        unresolved_human_decisions=semantics.unresolved_human_decisions,
        explicit_assumptions=semantics.explicit_assumptions,
        selected_question=selected_question,
        governance_candidate=semantics.governance_candidate.value,
        forbidden_claims=tuple(dict.fromkeys(forbidden)),
        source_references=assessment.supporting_references,
        semantic_policy_revision=semantics.semantic_policy_revision,
        question_policy_revision=semantics.question_policy_revision,
        response_language=(
            "zh-CN" if re.search(r"[\u4e00-\u9fff]", governed_content) else "en"
        ),
        interaction_strategy=strategy,
        cognitive_context_package=cognitive_context,
        response_contract=contract,
        previous_response_contract=previous_response_contract,
        latest_human_input=latest_human_input,
        recent_relevant_messages=recent_relevant_messages,
        production_admission_state=production_admission_state,
        repository_acquisition_state=repository_acquisition_state,
        production_next_step=production_next_step,
        execution_operation_kind=execution_operation_kind,
        execution_operation_reference=execution_operation_reference,
    )


def _strategy_for_response_contract(
    strategy: InteractionStrategy,
    contract: ResponseContract,
) -> InteractionStrategy:
    """Make legacy expression advice a projection of the turn contract.

    Cognitive altitude remains useful. Question allowance and the response move
    cannot compete with the first-class contract supplied to the same Realizer.
    """

    move = {
        "EXPLAIN": ConversationalMove.EXPLAIN,
        "DIAGNOSE": ConversationalMove.EXPLAIN,
        "ANSWER": ConversationalMove.ANSWER,
        "RECOMMEND": ConversationalMove.PROPOSE,
        "COMPARE": ConversationalMove.COMPARE,
        "ASSESS": ConversationalMove.EXPLAIN,
        "REPORT_REALITY": ConversationalMove.ANSWER,
        "PROPOSE": ConversationalMove.PROPOSE,
        "EXECUTE": ConversationalMove.CONFIRM,
        "CORRECT": ConversationalMove.CORRECT,
        "CLARIFY_BLOCKER": ConversationalMove.ESCALATE_HUMAN_DECISION,
    }[contract.primary_obligation.value]
    mode = contract.interaction_mode.value
    values = strategy.model_dump()
    values.update(
        primary_move=move,
        question_allowed=bool(contract.question_budget),
        max_questions=contract.question_budget,
        question_guidance=(
            contract.selected_question
            or "Ask only for the material blocker established by the Response Contract."
        ) if contract.question_budget else None,
        candidate_first=mode in {"EXPLORE", "DESIGN", "DECIDE"},
        answer_first=mode in {"ANSWER", "STATUS", "ANALYZE", "DIAGNOSE", "DECIDE"},
        next_conversational_granularity=(
            "Use response_contract opening_move and response_moves at its "
            "information_budget; stop once the current obligation is satisfied."
        ),
    )
    if mode == "EXPLORE":
        values.update(
            human_mode=HumanConversationMode.EXPLORING,
            cognitive_maturity=CognitiveMaturity.EXPLORING,
        )
    elif mode == "EXECUTE":
        values.update(
            human_mode=HumanConversationMode.SPECIFYING,
            cognitive_maturity=CognitiveMaturity.SPECIFYING,
        )
    elif mode == "DECIDE":
        values.update(
            human_mode=HumanConversationMode.DECIDING,
            cognitive_maturity=CognitiveMaturity.EVALUATING,
        )
    elif mode == "ANALYZE":
        values.update(
            human_mode=HumanConversationMode.ASKING,
            cognitive_maturity=CognitiveMaturity.EVALUATING,
        )
    elif mode == "CORRECT":
        values.update(human_mode=HumanConversationMode.CORRECTING)
    return InteractionStrategy.model_validate(values)


def reconcile_contract_response(
    contract: ResponseContract | None,
    reconciliation: ResponseReconciliation,
    semantics: ProgressiveSemanticStructure | None,
) -> ResponseReconciliation:
    """Do not present an unsupported objection as an accepted correction.

    Fast reception can label a disagreement as a correction before Deep WIC
    resolves its meaning. That classification mismatch is not a changed fact or
    judgment. Actual admitted corrections and Reality conflicts still reconcile
    through the existing correction path.
    """

    if (
        reconciliation is ResponseReconciliation.MATERIAL_CORRECTION
        and contract is not None
        and ResponseMove.ASSESS_OBJECTION in contract.response_moves
        and not contract.judgment_change_accepted
        and semantics is not None
        and not {
            PatternSignal.EXPLICIT_CORRECTION,
            PatternSignal.BROWNFIELD_REALITY_CONFLICT,
        }.intersection(semantics.pattern_signals)
    ):
        return ResponseReconciliation.REFINE
    return reconciliation


def _content_at_strategy_granularity(
    content: str,
    strategy: InteractionStrategy,
) -> str:
    """Enforce question allowance without choosing domain-specific content."""

    if strategy.question_allowed:
        return content
    value = content.rstrip()
    # Deep WIC owns the case-specific next move. Deterministic policy may suppress
    # a question when this turn disallows one, but it must never author a replacement.
    while value.endswith(("?", "？")):
        trimmed = re.sub(r"(?:^|(?<=[。！？!?\n]))[^。！？!?\n]*[?？]\s*$", "", value)
        if trimmed == value:
            break
        value = trimmed.rstrip()
    return value or content


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
                "客户数据能否交给外部模型，必须由你决定；我不会替你设定权限、保留期，也不会默认客户已经同意。"
                "不依赖这项决定的数据分级、最小化传输、隔离和审计可以先继续。"
                "先确认一件事：哪些数据允许发给外部模型？"
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
                f"收到，后续按“{correction.value}”继续；原先的对象判断不再采用。"
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
                f"既有约束继续保留：{retained_text}。"
                if retained_text else "当前目标和范围保持不变。"
            )
            return f"新增约束已纳入：{added_text}。{suffix}"
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
            return f"这更像另一个独立目标：{motive}。当前目标先保持不变；是否单独立项由你决定。"
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
    if intent in {"BROAD_MOTIVE", "CONTEXT_ADDITION", "HUMAN_UNCERTAINTY"} and not (
        PatternSignal.BROWNFIELD_REALITY_CONFLICT in signals
    ):
        return ResponseReconciliation.REFINE
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
