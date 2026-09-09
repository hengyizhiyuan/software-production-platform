from collections.abc import Iterator
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from spg.application.interaction import WorkInteractionService
from spg.domain.conversation import (
    ConversationContext,
    ConversationPolicyHint,
    ConversationTurnIntent,
    StructuredCollaborationResult,
)
from spg.domain.interaction import (
    WorkAdmissionReadiness,
    WorkAdmissionReadinessStatus,
    WorkFocusClassification,
    WorkImpactDisposition,
    WorkSatisfactionState,
    WorkTransitionChoice,
)
from spg.providers.codex_interaction import (
    CodexSdkConversationProvider,
    CodexSdkWorkInteractionCapability,
    _JsonStringFieldStream,
)


def _object_schemas(value: object, path: str = "$") -> Iterator[tuple[str, dict]]:
    if isinstance(value, dict):
        if "properties" in value:
            yield path, value
        for key, nested in value.items():
            yield from _object_schemas(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _object_schemas(nested, f"{path}[{index}]")


def _schema_nodes(value: object) -> Iterator[dict]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _schema_nodes(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _schema_nodes(nested)


def test_wic_provider_schema_is_recursively_strict_and_ref_safe() -> None:
    schema = CodexSdkWorkInteractionCapability.output_schema()
    assert "natural_response" not in schema["properties"]
    assert "collaboration" in schema["properties"]
    for path, object_schema in _object_schemas(schema):
        assert set(object_schema["properties"]) == set(
            object_schema.get("required", [])
        ), path
        assert object_schema.get("additionalProperties") is False, path
    for node in _schema_nodes(schema):
        if "$ref" in node:
            assert set(node) == {"$ref"}


def test_wic_provider_stream_exposes_only_incremental_human_response() -> None:
    payload = {
        "natural_response": "先明确用户价值，再比较方案 A 与 B。\\n只问一个关键问题。🚦",
        "interpreted_motive": "设计运营管理平台",
        "desired_outcome": None,
        "candidate_context": [],
        "candidate_constraints": [],
        "current_requests": [],
        "unresolved_material_questions": [],
        "meanings": [],
        "focus_classification": None,
        "impact_disposition": None,
        "supporting_references": [],
    }
    encoded = json.dumps(payload, ensure_ascii=True, separators=(", ", " : "))
    extractor = _JsonStringFieldStream("natural_response")
    emitted = "".join(
        extractor.feed(encoded[offset : offset + 5])
        for offset in range(0, len(encoded), 5)
    )

    assert emitted == payload["natural_response"]
    assert "interpreted_motive" not in emitted


def test_wic_streaming_terminal_collects_provider_events_and_final_result() -> None:
    payload = {
        "natural_response": "I will lead with the highest-impact design decision.",
        "interpreted_motive": "Design an operations platform",
        "desired_outcome": None,
        "candidate_context": [],
        "candidate_constraints": [],
        "current_requests": [],
        "unresolved_material_questions": [],
        "meanings": [],
        "focus_classification": None,
        "impact_disposition": None,
        "supporting_references": [],
    }
    encoded = json.dumps(payload, separators=(",", ":"))

    class Turn:
        def stream(self):
            for offset in range(0, len(encoded), 11):
                yield SimpleNamespace(
                    method="item/agentMessage/delta",
                    payload=SimpleNamespace(delta=encoded[offset : offset + 11]),
                )
            yield SimpleNamespace(
                method="item/completed",
                payload=SimpleNamespace(
                    item=SimpleNamespace(type="agentMessage", text=encoded)
                ),
            )
            yield SimpleNamespace(
                method="turn/completed",
                payload=SimpleNamespace(
                    turn=SimpleNamespace(status="completed", error=None)
                ),
            )

    deltas: list[str] = []
    terminal = CodexSdkWorkInteractionCapability._wait_for_streaming_terminal(
        Turn(),
        timeout_seconds=1,
        on_response_delta=deltas.append,
    )

    assert terminal.timed_out is False
    assert terminal.result is not None
    assert terminal.result.final_response == encoded
    assert "".join(deltas) == payload["natural_response"]


def test_ready_readiness_cannot_hide_material_questions() -> None:
    with pytest.raises(ValidationError, match="cannot retain material blockers"):
        WorkAdmissionReadiness(
            status=WorkAdmissionReadinessStatus.READY,
            profile="LONG_LIVED_STEERING",
            profile_version="v0",
            satisfied_requirements=("MOTIVE", "DESIRED_OUTCOME"),
            missing_information=(),
            unresolved_material_questions=("Which repository?",),
            reasons=("invalid",),
            basis_fingerprint="a" * 64,
        )


def test_wic3_provider_contract_exposes_bounded_focus_and_impact_taxonomies() -> None:
    schema = CodexSdkWorkInteractionCapability.output_schema()
    encoded = str(schema)
    assert {item.value for item in WorkFocusClassification} == {
        "ON_TOPIC",
        "RELEVANT_EXPLORATION",
        "SIDE_QUESTION",
        "MATERIAL_BRANCH",
        "UNRELATED_NEW_DEMAND",
    }
    assert {item.value for item in WorkImpactDisposition} == {
        "NO_GOVERNED_CHANGE",
        "CURRENT_CYCLE_REMAINS_VALID",
        "DEFER_TO_PRODUCTION_BOUNDARY",
        "CURRENT_RESULT_MAY_BE_INSUFFICIENT",
        "HUMAN_GOVERNANCE_REQUIRED",
        "NEW_WORK_RECOMMENDED",
    }
    assert "focus_classification" in encoded
    assert "impact_disposition" in encoded
    assert "supporting_references" in encoded


def test_wic4_lifecycle_taxonomies_are_small_and_human_governed() -> None:
    assert {item.value for item in WorkSatisfactionState} == {
        "NO_FOCUSED_WORK",
        "IN_PROGRESS",
        "CURRENTLY_SATISFIED",
    }
    assert {item.value for item in WorkTransitionChoice} == {
        "PENDING_HUMAN",
        "CONTINUE_CURRENT_WORK",
        "START_NEW_WORK",
        "DISMISSED",
    }


def test_wic_provider_instruction_requires_progressive_context_aware_leadership() -> None:
    basis = SimpleNamespace(
        model_dump=lambda mode: {
            "records": [
                {"content": "Design an operations management platform."},
                {"content": "Regional operations managers are the primary users."},
            ]
        },
        interaction=SimpleNamespace(
            selected_design_schema_identity=None,
            selected_design_schema_version=None,
        ),
        records=(
            SimpleNamespace(content="Design an operations management platform."),
            SimpleNamespace(content="Regional operations managers are the primary users."),
        ),
    )

    instruction = CodexSdkWorkInteractionCapability._instruction(basis)

    assert "WIC semantic boundary" in instruction
    assert "do not write the Human-facing response" in instruction
    assert "DIRECT_QUESTION" in instruction
    assert "REQUEST_RECOMMENDATION" in instruction
    assert "REQUEST_DETAIL" in instruction
    assert "CORRECTION" in instruction
    assert "does not automatically generate or write a design-document" in instruction


def test_dedicated_conversation_provider_owns_human_facing_policy() -> None:
    context = ConversationContext(
        source_basis_fingerprint="a" * 64,
        latest_human_message="你建议下一步做什么？",
        known_relevant_facts=("用户是个人开发者",),
        response_language="Chinese",
    )
    collaboration = StructuredCollaborationResult(
        turn_intent=ConversationTurnIntent.REQUEST_RECOMMENDATION,
        known_relevant_facts=("用户是个人开发者",),
        recommended_next_action="先定义核心使用场景",
        concise_basis="场景决定产品边界",
        response_language="Chinese",
        policy_hints=(ConversationPolicyHint.GUIDE_PROACTIVELY,),
    )

    instruction = CodexSdkConversationProvider.instruction(context, collaboration)

    assert "dedicated Human-facing Conversation Provider" in instruction
    assert "own wording" in instruction
    assert "two to five short paragraphs" in instruction
    assert "no more than one question mark" in instruction
    assert "Reuse known facts" in instruction
    assert "REQUEST_RECOMMENDATION" in instruction
    assert "questionnaire" in instruction
    assert "do not decide or modify Work, Design, Plan, Authority" in instruction


def test_wic_human_facing_response_does_not_append_internal_design_metadata() -> None:
    response = "先确定主要使用者，因为这会影响后续边界。\n\n谁负责日常操作？"

    rendered = WorkInteractionService._human_facing_response(response)

    assert rendered == response
    assert "设计方式：" not in rendered
    assert "当前阶段：" not in rendered
    assert "Facilitation strategy:" not in rendered
