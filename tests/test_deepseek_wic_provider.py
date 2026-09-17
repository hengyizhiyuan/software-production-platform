from __future__ import annotations

from datetime import UTC, datetime
import json
from uuid import UUID

import pytest

from spg.domain.conversation import (
    CognitiveMaturity,
    ConversationalMove,
    HumanAbstractionLevel,
    HumanConversationMode,
    InteractionStrategy,
)
from spg.domain.interaction import (
    Interaction,
    InteractionActor,
    InteractionCondition,
    InteractionInterpretationInput,
    InteractionInvariantViolation,
    InteractionRecord,
)
from spg.domain.model_runtime import (
    ModelProfile,
    ModelProvider,
    ModelProviderRegistry,
    ModelPurpose,
    ModelTiming,
    ModelUsage,
    PurposeProfileRouter,
    StructuredModelResult,
    WattModelRuntime,
)
from spg.domain.wic_response import GovernedResponseEnvelope, ResponseReconciliation
from spg.providers.deepseek_interaction import (
    DeepSeekWorkInteractionCapability,
    _structured_json_text,
)


def _basis() -> InteractionInterpretationInput:
    now = datetime(2026, 9, 13, tzinfo=UTC)
    return InteractionInterpretationInput(
        interaction=Interaction(
            id=UUID(int=1), condition=InteractionCondition.OPEN,
            created_by="human", updated_by="human", created_at=now, updated_at=now,
        ),
        records=(InteractionRecord(
            id=UUID(int=2), interaction_id=UUID(int=1), sequence=1,
            actor=InteractionActor.HUMAN, source="human",
            content="我想做一个运营管理平台。", content_fingerprint="a" * 64,
            created_at=now,
        ),),
        basis_fingerprint="b" * 64,
    )


def test_deepseek_accepts_only_a_complete_json_code_fence() -> None:
    assert _structured_json_text('```json\n{"ok":true}\n```') == '{"ok":true}'
    assert _structured_json_text('prefix {"ok":true}') == 'prefix {"ok":true}'


def _envelope() -> str:
    return json.dumps({
        "natural_response": "可以。先把它理解为帮助 Watt 推广工作的运营后台。",
        "semantics": {
            "interpreted_motive": "开发 Watt 运营管理后台",
            "desired_outcome": "支持 Watt 推广工作",
            "candidate_context": [],
            "candidate_constraints": [],
            "current_requests": ["设计运营管理平台"],
            "unresolved_material_questions": [],
            "meanings": [],
            "focus_classification": None,
            "impact_disposition": None,
            "supporting_references": [],
            "collaboration": {
                "turn_intent": "BUILD",
                "direct_answer": None,
                "design_intent_frame": None,
                "recommended_next_action": "先定义一期业务闭环",
                "concise_basis": "当前信息足以形成可修正的初步理解",
                "detailed_explanation_requested": False,
                "response_language": "zh-CN",
            },
            "retained_prior_meaning_indexes": [],
            "reuse_prior_design_intent_frame": False,
        },
    }, ensure_ascii=False)


class _Adapter:
    provider = ModelProvider.DEEPSEEK
    calls = 0

    def __init__(self, outputs: list[str] | None = None) -> None:
        self.outputs = list(outputs or ())

    def generate(self, **options):
        self.calls += 1
        output = self.outputs.pop(0) if self.outputs else (
            json.dumps(
                {"natural_response": "先确认目标，再说明下一步。"},
                ensure_ascii=False,
            )
            if options.get("input_text", "").startswith("Realize this governed")
            else _envelope()
        )
        callback = options.get("on_output_delta")
        stage = options.get("on_stage")
        if stage:
            for name in (
                "provider_request_queued", "provider_request_sent",
                "provider_response_accepted", "provider_first_response_event",
                "provider_first_token",
            ):
                stage(name)
        if callback:
            for index in range(0, len(output), 17):
                callback(output[index:index + 17])
        return StructuredModelResult(
            output_text=output, provider=self.provider,
            requested_model="deepseek-flash", effective_model="deepseek-flash",
            request_id="response-1", usage=ModelUsage(total_tokens=50),
            timing=ModelTiming(first_token_seconds=0.2, completed_seconds=1.0),
        )


def _runtime(adapter: _Adapter | None = None) -> tuple[WattModelRuntime, _Adapter]:
    adapter = adapter or _Adapter()
    registry = ModelProviderRegistry()
    registry.register(adapter)
    profiles = {
        purpose: ModelProfile(
            purpose=purpose, provider=ModelProvider.DEEPSEEK,
            model="deepseek-flash", reasoning_effort="low", timeout_seconds=30,
        )
        for purpose in (ModelPurpose.WIC_SEMANTIC, ModelPurpose.CONVERSATION_RESPONSE)
    }
    return WattModelRuntime(registry, PurposeProfileRouter(profiles)), adapter


def test_pre_work_coalesces_to_one_request_and_streams_only_human_text() -> None:
    runtime, adapter = _runtime()
    capability = DeepSeekWorkInteractionCapability(runtime=runtime)
    deltas = []
    stages = []

    result = capability.interpret_stream_observed(
        _basis(), on_response_delta=deltas.append, on_pipeline_stage=stages.append
    )

    assert adapter.calls == 1
    assert "".join(deltas) == result.natural_response
    assert "semantics" not in "".join(deltas)
    assert result.interpreted_motive == "开发 Watt 运营管理后台"
    assert result.turn_intent.value == "BUILD"
    assert capability.last_pipeline_evidence.provider_call_count == 1
    assert capability.last_pipeline_evidence.coalesced_request_id == "response-1"
    assert capability.last_pipeline_evidence.coalesced_retry_count == 0
    assert "provider_first_token" in stages
    assert "validation_completed" in stages


def test_controlled_pre_work_repairs_one_root_json_failure_without_visible_delta() -> None:
    adapter = _Adapter(['{"natural_response":"partial', _envelope()])
    runtime, adapter = _runtime(adapter)
    capability = DeepSeekWorkInteractionCapability(runtime=runtime)
    visible_deltas: list[str] = []
    stages: list[str] = []

    result = capability.interpret_controlled_stream_observed(
        _basis(),
        on_response_delta=visible_deltas.append,
        on_pipeline_stage=stages.append,
    )

    assert result.natural_response.startswith("可以。")
    assert visible_deltas == []
    assert adapter.calls == 2
    assert capability.last_pipeline_evidence is not None
    assert capability.last_pipeline_evidence.provider_call_count == 2
    assert capability.last_pipeline_evidence.coalesced_retry_count == 1
    assert "structured_json_repair_started" in stages
    assert "structured_json_repair_completed" in stages


def test_controlled_pre_work_does_not_retry_valid_json_with_schema_errors() -> None:
    adapter = _Adapter(['{"natural_response":"缺少 semantics"}'])
    runtime, adapter = _runtime(adapter)
    capability = DeepSeekWorkInteractionCapability(runtime=runtime)

    with pytest.raises(InteractionInvariantViolation, match="semantics:missing"):
        capability.interpret_controlled_stream_observed(
            _basis(),
            on_response_delta=lambda _delta: None,
            on_pipeline_stage=lambda _stage: None,
        )

    assert adapter.calls == 1


def test_controlled_pre_work_stops_after_one_failed_json_repair() -> None:
    adapter = _Adapter(["{", "{"])
    runtime, adapter = _runtime(adapter)
    capability = DeepSeekWorkInteractionCapability(runtime=runtime)

    with pytest.raises(
        InteractionInvariantViolation,
        match="root:json_invalid; bounded_repair_exhausted",
    ):
        capability.interpret_controlled_stream_observed(
            _basis(),
            on_response_delta=lambda _delta: None,
            on_pipeline_stage=lambda _stage: None,
        )

    assert adapter.calls == 2


def test_profiles_are_role_specific_and_control_pre_work_coalescing() -> None:
    runtime, _adapter = _runtime()
    changed = dict(runtime.router.profiles)
    profile = changed[ModelPurpose.CONVERSATION_RESPONSE]
    changed[ModelPurpose.CONVERSATION_RESPONSE] = ModelProfile(
        purpose=profile.purpose, provider=profile.provider, model="deepseek-v4-pro",
        reasoning_effort=profile.reasoning_effort, timeout_seconds=profile.timeout_seconds,
    )
    capability = DeepSeekWorkInteractionCapability(
        runtime=WattModelRuntime(runtime.registry, PurposeProfileRouter(changed))
    )
    assert capability.pipeline_selection(_basis()) == (
        "staged", "provider_profiles_differ"
    )


def test_governed_realizer_uses_configured_conversation_profile_and_streams() -> None:
    runtime, adapter = _runtime()
    capability = DeepSeekWorkInteractionCapability(runtime=runtime)
    envelope = GovernedResponseEnvelope(
        basis_fingerprint="b" * 64,
        governed_content="先确认目标，再说明下一步。",
        reconciliation=ResponseReconciliation.REFINE,
        governance_candidate="CONVERSATION_ONLY",
        semantic_policy_revision="policy-v1",
        question_policy_revision="question-v1",
        response_language="zh-CN",
        interaction_strategy=InteractionStrategy(
            human_abstraction_level=HumanAbstractionLevel.SOLUTION,
            cognitive_maturity=CognitiveMaturity.FRAMING,
            human_mode=HumanConversationMode.EXPLORING,
            primary_move=ConversationalMove.ORIENT,
            next_conversational_granularity="Stay at product direction level.",
        ),
    )
    deltas: list[str] = []

    result = capability.governed_response_realizer.realize_stream(
        envelope,
        on_response_delta=deltas.append,
    )

    assert adapter.calls == 1
    assert "".join(deltas) == result.content
    assert result.content == "先确认目标，再说明下一步。"
    assert result.model_identity == "deepseek-flash"
    assert result.request_id == "response-1"
    assert result.usage == {
        "input_tokens": None,
        "output_tokens": None,
        "cached_tokens": None,
        "reasoning_tokens": None,
        "total_tokens": 50,
        "unknown": False,
    }
