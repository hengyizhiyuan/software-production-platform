from __future__ import annotations

from datetime import UTC, datetime
import json
from uuid import UUID

from spg.domain.interaction import (
    Interaction,
    InteractionActor,
    InteractionCondition,
    InteractionInterpretationInput,
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
from spg.providers.deepseek_interaction import DeepSeekWorkInteractionCapability


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
                "turn_intent": "NEW_GOAL",
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

    def generate(self, **options):
        self.calls += 1
        output = _envelope()
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


def _runtime() -> tuple[WattModelRuntime, _Adapter]:
    adapter = _Adapter()
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
    assert capability.last_pipeline_evidence.provider_call_count == 1
    assert capability.last_pipeline_evidence.coalesced_request_id == "response-1"
    assert capability.last_pipeline_evidence.coalesced_retry_count == 0
    assert "provider_first_token" in stages
    assert "validation_completed" in stages


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
