from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from spg.application.design_intent import frame_design_intent_text
from spg.application.guided_design import match_design_schema_frame
from spg.domain.conversation import (
    ConversationContext,
    ConversationTurnIntent,
    StructuredCollaborationResult,
)
from spg.domain.design_intent import (
    DesignCollaborationMode,
    DesignIntentFrame,
    DesignObjectType,
    DesignScopeLevel,
)
from spg.providers.codex_interaction import (
    CodexSdkConversationProvider,
    CodexSdkInteractionSemanticCapability,
)


def test_design_intent_frame_rejects_unexplained_false_uncertainty() -> None:
    with pytest.raises(ValidationError, match="explicit ambiguity"):
        DesignIntentFrame(
            design_subject="Improve engineering efficiency",
            object_type=DesignObjectType.UNKNOWN,
            scope_level=DesignScopeLevel.STRATEGIC,
            collaboration_mode=DesignCollaborationMode.EXPLORATION,
            confidence=0.4,
        )


@pytest.mark.parametrize(
    ("human_input", "expected_type", "expected_schema"),
    (
        (
            "我要做一个电商系统。",
            DesignObjectType.PRODUCT_SYSTEM,
            "General Product/System Design",
        ),
        (
            "我要优化研发效率。",
            DesignObjectType.UNKNOWN,
            None,
        ),
        (
            "我要给现有运营后台增加直播排期。",
            DesignObjectType.FEATURE,
            "Existing Product Evolution",
        ),
        (
            "我想策划一次 Watt 发布直播。",
            DesignObjectType.OPERATIONAL_ACTIVITY,
            None,
        ),
    ),
)
def test_framing_distinguishes_design_objects_before_schema_selection(
    human_input: str,
    expected_type: DesignObjectType,
    expected_schema: str | None,
) -> None:
    frame = frame_design_intent_text(human_input)
    schema, _ = match_design_schema_frame(frame)

    assert frame.object_type is expected_type
    assert (None if schema is None else schema.title) == expected_schema


def test_operations_platform_context_does_not_override_product_object() -> None:
    frame = frame_design_intent_text(
        "我想做一个运营管理平台，主要用于推广 Watt，渠道包括公众号、小红书和直播。"
    )
    schema, rationale = match_design_schema_frame(frame)

    assert frame.object_type is DesignObjectType.PRODUCT_SYSTEM
    assert frame.business_context == "Support Watt promotion and related operations."
    assert schema is not None
    assert schema.title == "General Product/System Design"
    assert "Design Intent Frame" in rationale


def test_provider_wire_and_prompts_carry_frame_without_an_extra_provider_stage() -> None:
    schema = CodexSdkInteractionSemanticCapability.output_schema()
    collaboration = schema["$defs"]["_StructuredCollaborationProviderPayload"]

    assert "design_intent_frame" in collaboration["properties"]
    assert "design_intent_frame" in collaboration["required"]
    assert "Before proposing Guided Design direction" in inspect.getsource(
        CodexSdkInteractionSemanticCapability.instruction
    )

    context = ConversationContext(
        source_basis_fingerprint="a" * 64,
        latest_human_message="我想做一个运营管理平台。",
        response_language="Chinese",
    )
    result = StructuredCollaborationResult(
        turn_intent=ConversationTurnIntent.NEW_GOAL,
        design_intent_frame=frame_design_intent_text(
            "我想做一个运营管理平台。"
        ),
        response_language="Chinese",
    )
    instruction = CodexSdkConversationProvider.instruction(context, result)
    assert "Design Intent Frame" in instruction
    assert "PRODUCT_SYSTEM" in instruction
