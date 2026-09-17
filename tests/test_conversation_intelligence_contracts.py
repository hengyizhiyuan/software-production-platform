from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from spg.application.conversation import (
    ConversationResponseComposer,
    WattNativeConversationContextAssembler,
    conversation_response_policy,
)
from spg.domain.conversation import (
    ConversationContext,
    ConversationContextMessage,
    ConversationPolicyHint,
    ConversationResponseCandidate,
    ConversationTurnIntent,
    StructuredCollaborationResult,
)
from spg.domain.interaction import (
    InteractionActor,
    InteractionSemanticCandidate,
)
from spg.providers.codex_interaction import (
    CodexSdkConversationProvider,
    CodexSdkInteractionSemanticCapability,
    CodexSdkWorkInteractionCapability,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _basis(*messages: str, prior=None, recent=(), active=None):
    return SimpleNamespace(
        basis_fingerprint="a" * 64,
        records=tuple(
            SimpleNamespace(
                actor=InteractionActor.HUMAN,
                content=message,
                supporting_references=(),
            )
            for message in messages
        ),
        prior_assessment=prior,
        active_work_context=active,
        recent_conversation_messages=recent,
    )


def _collaboration(
    intent: ConversationTurnIntent = ConversationTurnIntent.NEW_GOAL,
    **updates,
) -> StructuredCollaborationResult:
    values = {
        "turn_intent": intent,
        "current_objective": "Design an operations platform",
        "current_collaboration_focus": "Primary users and operating problem",
        "recommended_next_action": "Confirm the first high-value operating scenario",
        "concise_basis": "The scenario determines the first product boundary",
        "response_language": "Chinese",
        "policy_hints": (ConversationPolicyHint.GUIDE_PROACTIVELY,),
    }
    values.update(updates)
    return StructuredCollaborationResult(**values)


def test_structured_collaboration_result_guards_intent_specific_requirements() -> None:
    with pytest.raises(ValidationError, match="DIRECT_QUESTION requires"):
        StructuredCollaborationResult(
            turn_intent=ConversationTurnIntent.DIRECT_QUESTION,
            response_language="Chinese",
        )
    with pytest.raises(ValidationError, match="HOW_TO requires"):
        StructuredCollaborationResult(
            turn_intent=ConversationTurnIntent.HOW_TO,
            response_language="Chinese",
        )
    with pytest.raises(ValidationError, match="REQUEST_DETAIL requires"):
        StructuredCollaborationResult(
            turn_intent=ConversationTurnIntent.REQUEST_DETAIL,
            response_language="Chinese",
        )


def test_native_context_assembly_is_bounded_and_reuses_known_reality() -> None:
    prior = SimpleNamespace(
        natural_response="此前已经确认目标用户。",
        candidate_context=("目标用户是个人开发者", "主要渠道是技术公众号"),
        candidate_constraints=("不要重构整个 UI",),
        current_requests=("继续推进设计",),
        desired_outcome="形成可执行的产品设计",
    )
    messages = tuple(f"上下文事实 {index}" for index in range(12))
    result = _collaboration(
        ConversationTurnIntent.CONTINUE_CURRENT_WORK,
        known_relevant_facts=("目标用户是个人开发者", "首要场景是状态观察"),
    )

    context = WattNativeConversationContextAssembler().assemble(
        _basis(*messages, prior=prior),
        result,
    )

    assert len(context.recent_relevant_messages) == 8
    assert context.latest_human_message == "上下文事实 11"
    assert context.known_relevant_facts == (
        "目标用户是个人开发者",
        "主要渠道是技术公众号",
        "首要场景是状态观察",
    )
    assert context.governing_constraints == ("不要重构整个 UI",)
    assert context.current_requests == ("继续推进设计",)
    assert context.current_objective == "Design an operations platform"


def test_response_composer_supplies_only_bounded_context_and_structured_result() -> None:
    class Provider:
        def __init__(self) -> None:
            self.received = None

        def respond(self, context, collaboration):
            self.received = (context, collaboration)
            return ConversationResponseCandidate(
                content="  建议先确认第一个高价值场景。  ",
                provider_identity="test:conversation",
            )

        def respond_stream(self, context, collaboration, *, on_response_delta):
            raise AssertionError("non-streaming composition expected")

    provider = Provider()
    result = _collaboration()
    response = ConversationResponseComposer(provider).compose(
        _basis("我想做一个运营管理平台。"),
        result,
    )

    assert response.content == "建议先确认第一个高价值场景。"
    assert provider.received is not None
    context, received_result = provider.received
    assert isinstance(context, ConversationContext)
    assert context.latest_human_message == "我想做一个运营管理平台。"
    assert received_result == result


def test_codex_wire_contracts_separate_semantics_from_human_expression() -> None:
    semantic_schema = CodexSdkWorkInteractionCapability.output_schema()
    conversation_schema = CodexSdkConversationProvider.output_schema()

    assert "natural_response" not in semantic_schema["properties"]
    assert "collaboration" in semantic_schema["properties"]
    assert set(conversation_schema["properties"]) == {"natural_response"}
    assert conversation_schema["required"] == ["natural_response"]


def test_compatibility_facade_runs_two_provider_neutral_stages_and_streams_wording() -> None:
    result = _collaboration(
        ConversationTurnIntent.REQUEST_RECOMMENDATION,
        known_relevant_facts=("目标用户是小型工作室",),
    )

    class SemanticCapability:
        last_thread_id = "semantic-thread"
        last_turn_id = "semantic-turn"

        def interpret_semantics(self, _basis_value):
            return InteractionSemanticCandidate(
                interpreted_motive="设计运营管理平台",
                desired_outcome="形成可执行的产品设计",
                candidate_context=("目标用户是小型工作室",),
                collaboration=result,
                provider_identity="test:semantic",
                model_identity="test-model",
            )

    class ConversationProvider:
        last_thread_id = "conversation-thread"
        last_turn_id = "conversation-turn"

        def respond(self, context, collaboration):
            raise AssertionError("streaming composition expected")

        def respond_stream(self, context, collaboration, *, on_response_delta):
            assert context.known_relevant_facts == ("目标用户是小型工作室",)
            assert collaboration is result
            on_response_delta("建议先确定")
            on_response_delta("核心运营场景。")
            return ConversationResponseCandidate(
                content="建议先确定核心运营场景。",
                provider_identity="test:conversation",
                model_identity="test-model",
            )

    capability = CodexSdkWorkInteractionCapability(repository_location=".", coalesce_pre_work=False)
    capability.semantic_capability = SemanticCapability()
    capability.conversation_provider = ConversationProvider()
    capability.response_composer = ConversationResponseComposer(
        capability.conversation_provider
    )
    deltas: list[str] = []

    candidate = capability.interpret_stream(
        _basis("你建议下一步先设计哪个部分？"),
        on_response_delta=deltas.append,
    )

    assert candidate.natural_response == "建议先确定核心运营场景。"
    assert "".join(deltas) == candidate.natural_response
    assert candidate.provider_identity == "test:semantic"
    assert capability.last_pipeline_evidence is not None
    assert capability.last_pipeline_evidence.semantic_thread_id == "semantic-thread"
    assert capability.last_pipeline_evidence.conversation_thread_id == "conversation-thread"


def test_conversation_quality_benchmark_has_broad_reusable_coverage() -> None:
    corpus = json.loads(
        (
            PROJECT_ROOT / "benchmarks" / "conversation_quality" / "corpus.json"
        ).read_text(encoding="utf-8")
    )
    categories = {case["category"] for case in corpus}
    intents = {case["expected_intent"] for case in corpus}
    contracts = {
        contract
        for case in corpus
        for contract in case["quality_contracts"]
    }

    assert 25 <= len(corpus) <= 50
    assert len({case["id"] for case in corpus}) == len(corpus)
    assert {
        "vague_new_goal",
        "direct_question",
        "context_addition",
        "known_context_reuse",
        "correction",
        "disagreement",
        "request_recommendation",
        "request_decision_support",
        "request_detail",
        "side_question",
        "material_branch",
        "frustration",
        "guided_design_progression",
        "human_decision",
        "system_limitation",
        "verification_explanation",
        "human_attention",
        "feedback",
    }.issubset(categories)
    assert {
        "DIRECT_QUESTION",
        "NEW_GOAL",
        "CONTEXT_ADDITION",
        "CORRECTION",
        "DISAGREEMENT",
        "REQUEST_RECOMMENDATION",
        "REQUEST_DECISION_SUPPORT",
        "REQUEST_DETAIL",
        "SIDE_QUESTION",
        "CONTINUE_CURRENT_WORK",
        "MATERIAL_BRANCH",
        "FEEDBACK",
        "HUMAN_DECISION",
    }.issubset(intents)
    assert {
        "direct_answer_first",
        "context_fidelity",
        "no_repetition",
        "proactive_guidance",
        "decision_utility",
        "expanded_detail",
        "no_methodology_dump",
        "preserve_authority",
    }.issubset(contracts)


def test_actual_dialogue_preserves_watt_options_for_referential_follow_up() -> None:
    dialogue = tuple(
        ConversationContextMessage(actor=actor, content=content)
        for actor, content in (
            ("HUMAN", "An older message"),
            ("WATT", "An older reply"),
            ("HUMAN", "I want an operations management platform."),
            ("WATT", "Who operates it?"),
            ("HUMAN", "Our marketing team."),
            ("WATT", "We could begin with a content calendar or a lead inbox."),
            ("HUMAN", "The audience is individual developers and small teams."),
            ("WATT", "That is the audience for Watt promotion."),
            ("HUMAN", "Explain your second suggestion."),
        )
    )
    context = WattNativeConversationContextAssembler().assemble(
        _basis("Explain your second suggestion.", recent=dialogue),
        _collaboration(ConversationTurnIntent.REQUEST_DETAIL,
                       detailed_explanation_requested=True),
    )

    assert context.recent_relevant_messages == dialogue[-8:]
    assert context.recent_relevant_messages[-1].content == context.latest_human_message
    assert any("lead inbox" in message.content
               for message in context.recent_relevant_messages)
    assert [message.actor for message in context.recent_relevant_messages].count("WATT") == 4


def test_current_correction_replaces_stale_candidates_and_supplies_current_constraints() -> None:
    prior = SimpleNamespace(
        natural_response="Let us design a promotion campaign.",
        candidate_context=("Design an operating plan", "Audience: large enterprises"),
        candidate_constraints=("Produce a campaign document",),
        current_requests=("Plan a launch livestream",),
        desired_outcome="An operating plan",
    )
    collaboration = _collaboration(
        ConversationTurnIntent.CORRECTION,
        current_objective="Build a Web application system for Watt promotion",
        known_relevant_facts=("Audience: individual developers and small teams",),
    )
    semantic = InteractionSemanticCandidate(
        candidate_context=("Design a Web application system",),
        candidate_constraints=("Reuse the existing authentication",),
        current_requests=("Correct the system design",),
        collaboration=collaboration,
        provider_identity="test:semantic",
    )
    received = []

    class Provider:
        def respond(self, context, collaboration):
            received.append(context)
            return ConversationResponseCandidate(
                content="Understood: a Web application system for Watt promotion.",
                provider_identity="test:conversation",
            )

    ConversationResponseComposer(Provider()).compose(
        _basis("Not an operation plan. I want a Web application system.", prior=prior),
        collaboration,
        current_semantics=semantic,
    )
    context = received[0]
    assert context.known_relevant_facts == (
        "Design a Web application system",
        "Audience: individual developers and small teams",
    )
    assert context.candidate_constraints == ("Reuse the existing authentication",)
    assert context.governing_constraints == ()
    assert context.current_requests == ("Correct the system design",)
    assert context.current_objective == "Build a Web application system for Watt promotion"
    assert prior.candidate_context == ("Design an operating plan", "Audience: large enterprises")


def test_current_candidates_do_not_rewrite_admitted_work_context_or_provider_contract() -> None:
    active = SimpleNamespace(
        work_revision=SimpleNamespace(
            work_id="existing-work",
            context_facts=("Admitted audience: enterprises",),
            constraints=("Keep the current authentication",),
            requests=("Deliver the admitted application",),
            desired_outcome="The admitted application",
        ),
        relevant_reality_references=(),
        steering_plan_revision_id=None,
    )
    collaboration = _collaboration(ConversationTurnIntent.CORRECTION)
    semantic = InteractionSemanticCandidate(
        candidate_context=("Proposed audience: individual developers",),
        candidate_constraints=(),
        current_requests=(),
        collaboration=collaboration,
        provider_identity="test:semantic",
    )
    received = []

    class ExistingContextProvider:
        # The context extension does not require plugins/ECF to accept new arguments.
        def assemble(self, basis, collaboration):
            return WattNativeConversationContextAssembler().assemble(basis, collaboration)

    class Provider:
        def respond(self, context, collaboration):
            received.append(context)
            return ConversationResponseCandidate(
                content="The proposed audience change needs the existing Work review.",
                provider_identity="test:conversation",
            )

    ConversationResponseComposer(
        Provider(), context_provider=ExistingContextProvider()
    ).compose(
        _basis("Change the target audience.", active=active),
        collaboration,
        current_semantics=semantic,
    )
    context = received[0]
    assert context.known_relevant_facts == ("Proposed audience: individual developers",)
    assert context.governed_work_facts == ("Admitted audience: enterprises",)
    assert context.governing_constraints == ("Keep the current authentication",)
    assert context.governed_work_requests == ("Deliver the admitted application",)
    assert context.candidate_constraints == ()
    assert context.current_requests == ()
    assert active.work_revision.context_facts == ("Admitted audience: enterprises",)


def test_latest_source_input_is_present_after_legacy_synchronous_append() -> None:
    dialogue = (
        ConversationContextMessage(actor="HUMAN", content="Recommend a starting point."),
        ConversationContextMessage(actor="WATT", content="Start with the content calendar."),
    )
    context = WattNativeConversationContextAssembler().assemble(
        _basis("Explain the data model for that calendar.", recent=dialogue),
        _collaboration(ConversationTurnIntent.REQUEST_DETAIL,
                       detailed_explanation_requested=True),
    )

    assert context.recent_relevant_messages[:-1] == dialogue
    assert context.recent_relevant_messages[-1] == ConversationContextMessage(
        actor="HUMAN", content="Explain the data model for that calendar."
    )
    assert context.latest_human_message == context.recent_relevant_messages[-1].content


def test_staged_and_coalesced_transport_share_one_conversation_policy(monkeypatch) -> None:
    # This guards ownership and prompt wiring; real responses still need Human review.
    monkeypatch.setattr(
        CodexSdkInteractionSemanticCapability,
        "instruction",
        staticmethod(lambda _basis, *, coalesced=False: "WIC semantic instructions"),
    )
    context = ConversationContext(
        source_basis_fingerprint="a" * 64,
        latest_human_message="你建议下一步先设计什么？",
        response_language="Chinese",
    )
    collaboration = _collaboration(
        ConversationTurnIntent.REQUEST_RECOMMENDATION,
        recommended_next_action="先画出跨渠道内容从选题到发布记录的流程",
        concise_basis="公众号、小红书和直播需要协调内容与排期",
    )
    policy = conversation_response_policy()
    staged = CodexSdkConversationProvider.instruction(context, collaboration)
    coalesced = CodexSdkWorkInteractionCapability.coalesced_instruction(object())

    assert CodexSdkConversationProvider.response_policy() == policy
    assert staged.count(policy) == 1
    assert coalesced.count(policy) == 1
    assert collaboration.recommended_next_action in staged
    assert collaboration.concise_basis in staged
    assert context.latest_human_message in staged
