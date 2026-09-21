from __future__ import annotations

import json
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from spg.application.response_contract import build_response_contract
from spg.application.response_contract_expression import (
    governed_contract_realizer_instruction,
    response_contract_expression_guidance,
)
from spg.application.wic_response import (
    GovernedDeltaGate,
    GovernedResponsePolicyViolation,
    governed_response_envelope,
    reconcile_contract_response,
)
from spg.domain.conversation import (
    CognitiveMaturity,
    ConversationContextMessage,
    ConversationTurnIntent,
    ConversationalMove,
    HumanAbstractionLevel,
    HumanConversationMode,
    InteractionStrategy,
)
from spg.domain.interaction import WorkAdmissionReadinessStatus
from spg.domain.response_contract import (
    InteractionMode, ResponseContract, ResponseIntent, ResponseMove,
)
from spg.domain.wic_intelligence import GovernanceCandidateKind, PatternSignal
from spg.domain.wic_response import GovernedResponseEnvelope, ResponseReconciliation


def _assessment(intent=ConversationTurnIntent.DIRECT_QUESTION):
    return SimpleNamespace(
        basis_fingerprint="a" * 64,
        basis_work_revision_id=None,
        basis_steering_plan_revision_id=None,
        basis_active_runtime_binding_id=None,
        supporting_references=("repository:README.md",),
        engineering_semantic_facts=(),
        readiness=SimpleNamespace(status=WorkAdmissionReadinessStatus.READY),
        progressive_semantics=SimpleNamespace(
            basis_fingerprint="a" * 64,
            turn_intent=intent,
            source_record_ids=(),
            deltas=(),
            pattern_signals=(),
            governance_candidate=GovernanceCandidateKind.CONVERSATION_ONLY,
            working_motive="Explore or implement a login experience.",
            working_desired_outcome="A useful next step for this turn.",
            working_facts=("A login page is being discussed.",),
            working_constraints=("Do not start production during exploration.",),
            unresolved_human_decisions=(),
            explicit_assumptions=(),
            selected_question=None,
            questions=(),
            semantic_policy_revision="semantic-v1",
            question_policy_revision="question-v1",
        ),
    )


def _contract(mode=InteractionMode.ANSWER) -> ResponseContract:
    return build_response_contract(
        _assessment(),
        interpretation=ResponseIntent(
            interaction_mode=mode,
            rationale="The semantic interpreter identified this turn's collaboration need.",
            executable_context=mode is InteractionMode.EXECUTE,
        ),
    )


def _envelope(contract: ResponseContract | None) -> GovernedResponseEnvelope:
    return GovernedResponseEnvelope(
        basis_fingerprint="a" * 64,
        governed_content="当前连接失败。下一步核对请求是否到达服务。",
        reconciliation=ResponseReconciliation.CONFIRM,
        governance_candidate="CONVERSATION_ONLY",
        semantic_policy_revision="semantic-v1",
        question_policy_revision="question-v1",
        response_language="zh-CN",
        interaction_strategy=InteractionStrategy(
            human_abstraction_level=HumanAbstractionLevel.SOLUTION,
            cognitive_maturity=CognitiveMaturity.FRAMING,
            human_mode=HumanConversationMode.ASKING,
            primary_move=ConversationalMove.ANSWER,
            next_conversational_granularity="Answer directly.",
        ),
        response_contract=contract,
    )


def test_envelope_projects_contract_allowance_without_changing_semantic_truth() -> None:
    assessment = _assessment(ConversationTurnIntent.BUILD)
    contract = _contract(InteractionMode.EXECUTE)
    recent = (
        ConversationContextMessage(actor="WATT", content="已有的登录方案只包含邮箱登录。"),
    )
    envelope = governed_response_envelope(
        assessment,
        governed_content="按已确定的邮箱登录方案继续。还要再确认登录方式吗？",
        provisional_content=None,
        reconciliation=ResponseReconciliation.CONFIRM,
        latest_human_input="按刚才的设计开始。",
        response_contract=contract,
        recent_relevant_messages=recent,
    )

    assert envelope.response_contract == contract
    assert envelope.latest_human_input == "按刚才的设计开始。"
    assert envelope.recent_relevant_messages == recent
    assert envelope.interaction_strategy.primary_move is ConversationalMove.CONFIRM
    assert envelope.interaction_strategy.max_questions == 0
    assert not envelope.interaction_strategy.question_allowed
    assert envelope.selected_question is None
    assert envelope.governed_content == "按已确定的邮箱登录方案继续。"
    assert envelope.facts_to_preserve == assessment.progressive_semantics.working_facts
    assert assessment.progressive_semantics.turn_intent is ConversationTurnIntent.BUILD
    assert assessment.engineering_semantic_facts == ()


def test_legacy_envelope_builder_creates_a_contract_from_admitted_turn_intent() -> None:
    envelope = governed_response_envelope(
        _assessment(ConversationTurnIntent.EXPLORE),
        governed_content="登录可以从低摩擦和控制感两个角度展开。",
        provisional_content=None,
        reconciliation=ResponseReconciliation.CONFIRM,
        latest_human_input="我们先聊聊登录。",
    )
    assert envelope.response_contract.interaction_mode is InteractionMode.EXPLORE
    assert not envelope.interaction_strategy.question_allowed
    assert envelope.interaction_strategy.cognitive_maturity is CognitiveMaturity.EXPLORING


def test_envelope_refuses_a_contract_from_another_turn_basis() -> None:
    wrong = _contract().model_copy(update={"basis_fingerprint": "b" * 64})
    with pytest.raises(ValueError, match="admitted turn basis"):
        governed_response_envelope(
            _assessment(),
            governed_content="可以。",
            provisional_content=None,
            reconciliation=ResponseReconciliation.CONFIRM,
            latest_human_input="可以吗？",
            response_contract=wrong,
        )


def test_zero_question_contract_preserves_later_diagnostic_obligations() -> None:
    emitted: list[str] = []
    gate = GovernedDeltaGate(_envelope(_contract(InteractionMode.DIAGNOSE)), emitted.append)
    gate.feed("当前连接")
    assert emitted == []
    gate.feed("失败。还要继续吗？先检查请求是否到达服务。")

    # Bounded clauses become visible before provider finalization. Dropping an
    # unneeded question cannot also truncate the requested cause or next check.
    assert "".join(emitted) == "当前连接失败。先检查请求是否到达服务。"
    assert gate.finish() == "当前连接失败。先检查请求是否到达服务。"
    assert gate.suppressed == ["还要继续吗？"]


def test_contract_question_budget_is_authoritative_over_legacy_strategy() -> None:
    contract = ResponseContract.model_validate(
        _contract().model_dump()
        | {"question_budget": 1, "selected_question": "允许修改哪一个环境？"}
    )
    emitted: list[str] = []
    gate = GovernedDeltaGate(_envelope(contract), emitted.append)
    gate.feed("需要确认环境边界。允许修改哪一个环境？还要重新设计吗？明确边界后即可继续。")
    assert gate.finish() == "需要确认环境边界。允许修改哪一个环境？明确边界后即可继续。"
    assert gate.question_count == 1


@pytest.mark.parametrize(
    "question",
    (
        "请告诉我你偏向哪一个。",
        "你希望先做哪一种。",
        "可以继续吗。",
        "Could you confirm the target environment.",
        "Please share the missing access scope.",
        "Tell me which option you prefer.",
    ),
)
def test_question_budget_covers_information_requests_without_question_marks(question: str) -> None:
    emitted: list[str] = []
    gate = GovernedDeltaGate(_envelope(_contract()), emitted.append)
    gate.feed("可沿用当前配置。" + question + " 下一步检查日志。")
    assert gate.finish() == "可沿用当前配置。 下一步检查日志。"


def test_suppressed_information_request_does_not_leave_its_sentence_tail_visible() -> None:
    emitted: list[str] = []
    gate = GovernedDeltaGate(_envelope(_contract()), emitted.append)
    gate.feed("当前配置可用。请告诉我，")
    gate.feed("你偏向哪一种。下一步检查日志。")
    assert gate.finish() == "当前配置可用。下一步检查日志。"


def test_allowed_information_request_is_counted_once_across_clauses() -> None:
    contract = ResponseContract.model_validate(
        _contract().model_dump()
        | {"question_budget": 1, "selected_question": "允许修改哪一个环境？"}
    )
    emitted: list[str] = []
    gate = GovernedDeltaGate(_envelope(contract), emitted.append)
    gate.feed("请确认，允许修改哪一个环境？")
    assert gate.finish() == "请确认，允许修改哪一个环境？"
    assert gate.question_count == 1


@pytest.mark.parametrize(
    "content",
    (
        "例句是“还需要继续吗？”，这是历史引用。",
        "表达式 `ready ? yes : no` 使用条件运算。",
        "访问 https://example.test/view?mode=compact 即可。",
        "Use `ready ? yes : no`. It is a conditional expression.",
        'The earlier message was "Which environment?". That is the cited context.',
    ),
)
def test_question_like_literals_are_not_suppressed_as_questions(content: str) -> None:
    emitted: list[str] = []
    gate = GovernedDeltaGate(_envelope(_contract()), emitted.append)
    for index in range(0, len(content), 3):
        gate.feed(content[index:index + 3])
    assert gate.finish() == content
    assert gate.question_count == 0


@pytest.mark.parametrize(
    "label",
    (
        "INFORMATION_BUDGET=MINIMAL",
        '"question_budget":0',
        "INTERACTION_MODE:EXECUTE",
        '"response_contract":{}',
    ),
)
def test_contract_metadata_cannot_leak_across_provider_chunks(label: str) -> None:
    emitted: list[str] = []
    gate = GovernedDeltaGate(_envelope(_contract()), emitted.append)
    gate.feed(label[:7])
    with pytest.raises(GovernedResponsePolicyViolation, match="internal Response Contract"):
        gate.feed(label[7:] + "\n")
    assert emitted == []


def test_contract_gate_keeps_existing_governed_claim_protection() -> None:
    envelope = _envelope(_contract()).model_copy(
        update={"forbidden_claims": ("客户已经同意",)}
    )
    emitted: list[str] = []
    gate = GovernedDeltaGate(envelope, emitted.append)
    gate.feed("默认客户已经")
    with pytest.raises(GovernedResponsePolicyViolation, match="forbidden governed claim"):
        gate.feed("同意。")
    assert emitted == []


def test_information_budget_does_not_blindly_truncate_required_evidence() -> None:
    emitted: list[str] = []
    gate = GovernedDeltaGate(_envelope(_contract(InteractionMode.ANALYZE)), emitted.append)
    evidence = "This is relevant evidence for the assessment. " * 40
    gate.feed(evidence)
    assert gate.finish() == evidence
    assert "".join(emitted) == evidence


def test_contract_stream_preserves_paragraphs_after_admitted_text() -> None:
    emitted: list[str] = []
    gate = GovernedDeltaGate(_envelope(_contract(InteractionMode.EXPLORE)), emitted.append)
    gate.feed("\n\n")
    gate.feed("先从低摩擦登录切入。\n")
    gate.feed("\n再比较隐私和控制感。\n\n")
    expected = "先从低摩擦登录切入。\n\n再比较隐私和控制感。\n\n"
    assert gate.finish() == expected
    assert "".join(emitted) == expected


def test_english_sentence_emits_before_provider_completes_even_when_separator_is_later() -> None:
    emitted: list[str] = []
    gate = GovernedDeltaGate(_envelope(_contract(InteractionMode.EXPLORE)), emitted.append)
    first = "Email access reduces the initial setup."
    gate.feed(first)
    assert emitted == []
    gate.feed(" ")
    assert "".join(emitted) == first
    gate.feed("Keep a recovery path.")
    assert gate.finish() == first + " Keep a recovery path."


def test_sentence_stream_does_not_split_internal_url_or_decimal_dots() -> None:
    emitted: list[str] = []
    gate = GovernedDeltaGate(_envelope(_contract()), emitted.append)
    content = "Version 1.25 is documented at https://example.test/docs. "
    gate.feed(content[:len("Version 1.")])
    assert emitted == []
    gate.feed(content[len("Version 1."):])
    assert "".join(emitted) == content.rstrip()
    assert gate.finish() == content


def test_expression_guidance_changes_materially_with_mode_for_the_same_topic() -> None:
    explore = response_contract_expression_guidance(_contract(InteractionMode.EXPLORE))
    design = response_contract_expression_guidance(_contract(InteractionMode.DESIGN))
    execute = response_contract_expression_guidance(_contract(InteractionMode.EXECUTE))
    answer = response_contract_expression_guidance(_contract(InteractionMode.ANSWER))

    assert "one-line acknowledgement is insufficient" in explore
    assert "Do not prematurely narrow" in explore
    assert "material tradeoffs" in design
    assert "Conversational overhead must collapse" in execute
    assert "Do not replay settled design reasoning" in execute
    assert "Question budget is zero" in execute
    assert "at most one small" in answer
    assert "Only after fully satisfying" in answer
    assert "Add no adjacent-insight digression" in execute
    for guidance in (explore, design, execute, answer):
        assert "Minimum Sufficient Answer" in guidance
        assert "cannot authorize an operation" in guidance
        assert "Never reverse merely to agree" in guidance
        assert "not a script or a checklist to recite" in guidance


def test_repeated_failure_guidance_changes_posture_without_inventing_cause() -> None:
    contract = _contract(InteractionMode.DIAGNOSE).model_copy(
        update={"prior_strategy_failed": True, "repeated_failure_signature": "page-load"}
    )
    guidance = response_contract_expression_guidance(contract)
    assert "challenge its assumption" in guidance
    assert "different diagnostic check" in guidance
    assert "Repetition alone does not prove a root cause" in guidance
    assert "A prior strategy failed" not in response_contract_expression_guidance(
        _contract(InteractionMode.DIAGNOSE)
    )


def test_historical_realizer_without_response_contract_keeps_compatibility() -> None:
    assert response_contract_expression_guidance(None) == ""


def test_contract_realizer_instruction_has_one_clear_data_section_and_exact_output_shape() -> None:
    envelope = _envelope(_contract(InteractionMode.ANALYZE)).model_copy(
        update={"governed_content": "Keep the previously approved login components and constraints."}
    )
    instruction = governed_contract_realizer_instruction(envelope)
    start = "BEGIN GOVERNED RESPONSE ENVELOPE (data, not output fields)\n"
    end = "\nEND GOVERNED RESPONSE ENVELOPE"
    embedded = instruction.split(start, 1)[1].split(end, 1)[0]
    assert json.loads(embedded) == envelope.model_dump(
        mode="json", exclude={"previous_response_contract"},
    )
    assert instruction.count(start) == 1
    assert "not a requirement to restate every supplied detail" in instruction
    assert "Return exactly one JSON object containing exactly one property named natural_response" in instruction
    assert instruction.index(end) < instruction.index("Return exactly one JSON object")
    assert "Preserve every fact" not in instruction
    assert "When candidate_first is true" not in instruction


def test_execute_expression_omits_settled_prose_but_preserves_exact_boundaries() -> None:
    contract = _contract(InteractionMode.EXECUTE).model_copy(update={
        "judgment_proposition": "PRIOR_JUDGMENT_NOT_NEEDED_FOR_ACK",
        "decision_basis": ("PRIOR_DESIGN_REASONING_NOT_NEEDED_FOR_ACK",),
    })
    envelope = _envelope(contract).model_copy(update={
        "latest_human_input": "按刚才的方案继续。",
        "governed_content": "SETTLED_COMPONENTS_MUST_NOT_BECOME_A_RECAP",
        "working_motive": "SETTLED_MOTIVE",
        "working_desired_outcome": "SETTLED_OUTCOME",
        "facts_to_preserve": ("SETTLED_DESIGN_DETAIL",),
        "constraints_to_preserve": ("Do not publish externally without permission.",),
        "forbidden_claims": ("production has started",),
        "recent_relevant_messages": (
            ConversationContextMessage(actor="WATT", content="PRIOR_LONG_DESIGN_DISCUSSION"),
        ),
    })
    before = envelope.model_dump(mode="json")
    instruction = governed_contract_realizer_instruction(envelope)
    embedded = instruction.split(
        "BEGIN GOVERNED RESPONSE ENVELOPE (data, not output fields)\n", 1,
    )[1].split("\nEND GOVERNED RESPONSE ENVELOPE", 1)[0]
    payload = json.loads(embedded)

    assert payload["latest_human_input"] == envelope.latest_human_input
    assert payload["governance_candidate"] == envelope.governance_candidate
    assert payload["constraints_to_preserve"] == list(envelope.constraints_to_preserve)
    assert payload["forbidden_claims"] == list(envelope.forbidden_claims)
    assert "no evidence that execution has started or succeeded" in payload["authority_boundary"]
    for field in (
        "interaction_mode", "primary_obligation", "opening_move", "response_moves",
        "information_budget", "question_budget", "advancement_obligation", "authority",
    ):
        assert payload["response_contract"][field] == before["response_contract"][field]
    for irrelevant in (
        "SETTLED_COMPONENTS", "SETTLED_MOTIVE", "SETTLED_OUTCOME", "SETTLED_DESIGN_DETAIL",
        "PRIOR_JUDGMENT_NOT_NEEDED", "PRIOR_DESIGN_REASONING_NOT_NEEDED", "PRIOR_LONG_DESIGN",
    ):
        assert irrelevant not in instruction
    assert "Do not enumerate settled components" in instruction
    assert "The acknowledgement plus that next action is the complete response" in instruction
    assert envelope.model_dump(mode="json") == before


def test_execute_expression_keeps_full_material_when_human_authority_is_unresolved() -> None:
    envelope = _envelope(_contract(InteractionMode.EXECUTE)).model_copy(update={
        "governance_candidate": "HUMAN_DECISION_REQUIRED",
        "unresolved_human_decisions": ("External publication requires authorization.",),
        "governed_content": "The publication target must be authorized first.",
    })
    instruction = governed_contract_realizer_instruction(envelope)
    assert envelope.governed_content in instruction
    assert "External publication requires authorization" in instruction


def test_challenge_expression_is_succinct_open_and_not_a_lecture() -> None:
    contract = _contract(InteractionMode.ANALYZE).model_copy(update={
        "response_moves": (
            ResponseMove.CONCLUSION, ResponseMove.ASSESS_OBJECTION, ResponseMove.EVIDENCE,
        ),
    })
    guidance = response_contract_expression_guidance(contract)
    assert "two or three short sentences" in guidance
    assert "Be open to correction without becoming combative" in guidance
    assert "comment on the Human's competence" in guidance
    assert "do not explain the rule" in guidance
    assert "Give a clear assessment or design direction" not in guidance


def _challenge_contract() -> ResponseContract:
    return _contract(InteractionMode.ANALYZE).model_copy(update={
        "response_moves": (
            ResponseMove.CONCLUSION, ResponseMove.ASSESS_OBJECTION, ResponseMove.EVIDENCE,
        ),
        "judgment_subject": "deployment topology",
        "judgment_proposition": "A single deployment currently fits the team.",
        "judgment_basis": ("Two developers maintain the system.",),
    })


def test_challenge_projection_keeps_old_and_new_evidence_without_prior_prose() -> None:
    previous = _challenge_contract()
    current = previous.model_copy(update={
        "judgment_proposition": "An independent service is justified for this new boundary.",
        "judgment_basis": ("The new boundary requires separate release authority.",),
        "judgment_change_accepted": True,
        "decision_basis": ("PRIVATE_DECISION_PROSE_NOT_TO_REPEAT",),
    })
    envelope = _envelope(current).model_copy(update={
        "previous_response_contract": previous,
        "latest_human_input": "新的业务有独立发布权限要求，之前的判断应调整。",
        "governed_content": "OLD_NATURAL_ARGUMENT_MUST_NOT_BE_RECYCLED",
        "facts_to_preserve": ("The new boundary requires separate release authority.",),
        "constraints_to_preserve": ("Keep the main system in one deployment.",),
        "forbidden_claims": ("All services are authorized for deployment.",),
        "recent_relevant_messages": (
            ConversationContextMessage(actor="WATT", content="OLD_LONG_DIALOGUE_MUST_NOT_BE_RECYCLED"),
        ),
    })
    before = envelope.model_dump(mode="json")
    instruction = governed_contract_realizer_instruction(envelope)
    embedded = instruction.split(
        "BEGIN GOVERNED RESPONSE ENVELOPE (data, not output fields)\n", 1,
    )[1].split("\nEND GOVERNED RESPONSE ENVELOPE", 1)[0]
    payload = json.loads(embedded)
    assert payload["previous_judgment"]["proposition"] == previous.judgment_proposition
    assert payload["previous_judgment"]["basis"] == list(previous.judgment_basis)
    assert payload["response_contract"]["judgment_proposition"] == current.judgment_proposition
    assert payload["response_contract"]["judgment_basis"] == list(current.judgment_basis)
    assert payload["response_contract"]["judgment_change_accepted"] is True
    assert payload["facts_to_preserve"] == list(envelope.facts_to_preserve)
    assert payload["constraints_to_preserve"] == list(envelope.constraints_to_preserve)
    assert payload["forbidden_claims"] == list(envelope.forbidden_claims)
    assert "OLD_NATURAL_ARGUMENT" not in instruction
    assert "OLD_LONG_DIALOGUE" not in instruction
    assert "PRIVATE_DECISION_PROSE" not in instruction
    assert "interaction_strategy" not in payload
    assert envelope.model_dump(mode="json") == before


def test_new_execute_request_does_not_assert_that_an_approved_plan_exists() -> None:
    envelope = _envelope(_contract(InteractionMode.EXECUTE)).model_copy(update={
        "latest_human_input": "这个按钮点了没反应，直接修掉。",
        "governed_content": "Investigate the click handler and repair its failure.",
    })
    instruction = governed_contract_realizer_instruction(envelope)
    assert "EXECUTE alone does not imply a prior plan" in instruction
    assert "EXECUTE is not evidence that an earlier or approved plan exists" in instruction
    assert "the Human already approved" not in instruction
    assert envelope.latest_human_input in instruction


def test_unsupported_objection_strategy_evaluates_instead_of_claiming_correction() -> None:
    envelope = governed_response_envelope(
        _assessment(ConversationTurnIntent.DISAGREEMENT),
        governed_content="当前依据仍支持这一判断。",
        provisional_content=None,
        reconciliation=ResponseReconciliation.REFINE,
        latest_human_input="我觉得你的判断不对。",
        response_contract=_challenge_contract(),
    )
    assert envelope.interaction_strategy.human_mode is HumanConversationMode.ASKING
    assert envelope.interaction_strategy.cognitive_maturity is CognitiveMaturity.EVALUATING


@pytest.mark.parametrize(
    "accepted,signals,expected",
    (
        (False, (), ResponseReconciliation.REFINE),
        (True, (), ResponseReconciliation.MATERIAL_CORRECTION),
        (False, (PatternSignal.EXPLICIT_CORRECTION,), ResponseReconciliation.MATERIAL_CORRECTION),
        (False, (PatternSignal.BROWNFIELD_REALITY_CONFLICT,), ResponseReconciliation.MATERIAL_CORRECTION),
    ),
)
def test_reconciliation_uses_admitted_objection_without_hiding_real_correction(
    accepted, signals, expected,
) -> None:
    contract = _challenge_contract().model_copy(update={"judgment_change_accepted": accepted})
    semantics = SimpleNamespace(pattern_signals=signals)
    assert reconcile_contract_response(
        contract, ResponseReconciliation.MATERIAL_CORRECTION, semantics,
    ) is expected
    assert reconcile_contract_response(
        contract, ResponseReconciliation.CONFIRM, semantics,
    ) is ResponseReconciliation.CONFIRM


def test_disagreement_cannot_become_work_change_via_raw_correct_mode() -> None:
    from spg.application.interaction import WorkInteractionService
    from spg.domain.interaction import (
        InteractionAssessmentCandidate, WorkFocusClassification, WorkImpactDisposition,
    )

    candidate = InteractionAssessmentCandidate(
        turn_intent=ConversationTurnIntent.DISAGREEMENT,
        response_intent=ResponseIntent(
            interaction_mode=InteractionMode.CORRECT,
            rationale="Provider incorrectly classified a challenge as correction.",
        ),
        natural_response="Keep the current judgment pending evidence.",
        provider_identity="test",
    )
    result = WorkInteractionService._normalize_active_candidate(candidate, SimpleNamespace())
    assert result == (
        WorkFocusClassification.SIDE_QUESTION, WorkImpactDisposition.NO_GOVERNED_CHANGE, None,
    )


def test_contract_aware_instruction_does_not_silently_adapt_legacy_envelope() -> None:
    with pytest.raises(ValueError, match="requires a Response Contract"):
        governed_contract_realizer_instruction(_envelope(None))


def test_deepseek_realizer_uses_contract_instruction_and_streams_only_response() -> None:
    from spg.domain.model_runtime import (
        ModelProvider, ModelTiming, ModelUsage, StructuredModelResult,
    )
    from spg.providers.deepseek_interaction import DeepSeekGovernedResponseRealizer

    envelope = _envelope(_contract(InteractionMode.EXECUTE))
    calls = []
    expected = "按已确定的方案继续实现。"

    def generate(**options):
        calls.append(options)
        content = json.dumps({"natural_response": expected}, ensure_ascii=False)
        for index in range(0, len(content), 4):
            options["on_output_delta"](content[index:index + 4])
        return StructuredModelResult(
            output_text=content,
            provider=ModelProvider.DEEPSEEK,
            requested_model="test-model",
            effective_model="test-model",
            request_id="request-test",
            usage=ModelUsage(total_tokens=50),
            timing=ModelTiming(first_token_seconds=0.1, completed_seconds=0.2),
        )

    runtime = SimpleNamespace(
        profile=lambda _purpose: SimpleNamespace(model="test-model", reasoning_effort="low"),
        generate=generate,
    )
    emitted = []
    result = DeepSeekGovernedResponseRealizer(runtime).realize_stream(
        envelope, on_response_delta=emitted.append,
    )
    assert calls[0]["instructions"] == governed_contract_realizer_instruction(envelope)
    assert "".join(emitted) == expected == result.content
    assert len(emitted) > 1


def test_codex_realizer_uses_same_contract_instruction_without_legacy_conflicts(monkeypatch) -> None:
    from spg.providers import codex_interaction as provider

    envelope = _envelope(_contract(InteractionMode.EXECUTE))
    calls = []
    expected = "按已确定的方案继续实现。"

    def start_turn(instruction, **_options):
        calls.append(instruction)
        return SimpleNamespace(id="turn-test")

    def terminal(_turn, **options):
        options["on_response_delta"](expected[:5])
        options["on_response_delta"](expected[5:])
        return SimpleNamespace(
            timed_out=False,
            result=SimpleNamespace(
                status="completed", error=None,
                final_response=json.dumps({"natural_response": expected}, ensure_ascii=False),
            ),
        )

    codex = SimpleNamespace(
        thread_start=lambda **_options: SimpleNamespace(id="thread-test", turn=start_turn)
    )
    monkeypatch.setattr(
        provider, "_codex_controls",
        lambda: (SimpleNamespace(deny_all="deny"), SimpleNamespace(read_only="read")),
    )
    monkeypatch.setattr(provider, "_wait_for_streaming_terminal", terminal)
    emitted = []
    result = provider.CodexSdkGovernedResponseRealizer(
        repository_location=".", codex_factory=lambda: nullcontext(codex),
        model="test-model", reasoning_effort="low", timeout_seconds=10,
    ).realize_stream(envelope, on_response_delta=emitted.append)
    assert calls == [governed_contract_realizer_instruction(envelope)]
    assert "".join(emitted) == expected == result.content
    assert len(emitted) == 2
