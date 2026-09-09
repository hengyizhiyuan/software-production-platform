from types import SimpleNamespace

import pytest

from benchmarks.conversation_quality.pipeline_probe import (
    ProviderObservation,
    SCENARIOS_V31_ZH,
    completed_top_level_string,
)


@pytest.mark.parametrize(
    ("prefix", "expected"),
    [
        ('{"natural_response":"unfinished', None),
        ('{"natural_response":"has \\"quotes\\" and 中文"', 'has "quotes" and 中文'),
        ('{"semantics":{"natural_response":"internal"},"natural_response":"public"', "public"),
        ('{"other":"natural_response", "natural_response":null', None),
        ('{"other":"a \\"natural_response\\": \\"fake\\"", "natural_response":"real"', "real"),
        ('{"natural_response":"\\ud83d', None),
        ('{"natural_response":"\\ud83d\\udea6"', "🚦"),
    ],
)
def test_response_completion_observer_requires_closed_top_level_string(prefix, expected):
    assert completed_top_level_string(prefix, "natural_response") == expected


def test_chinese_benchmark_preserves_supplied_context_and_recommendation_request():
    assert len(SCENARIOS_V31_ZH) == 5
    assert SCENARIOS_V31_ZH[1] == (
        "这个平台主要用于推广 Watt。\n目标用户包括个人开发者、小型开发团队。\n渠道包括公众号、小红书和直播。"
    )
    assert SCENARIOS_V31_ZH[-1] == "你建议下一步先设计什么？"


def test_observation_preserves_sdk_calls_and_distinguishes_text_from_envelope():
    stages = {}
    observation = ProviderObservation(stages, [0])
    envelope = '{"natural_response":"你好", "semantics":{}}'

    class Turn:
        id = "turn"

        def stream(self):
            yield SimpleNamespace(method="item/agentMessage/delta", payload=SimpleNamespace(delta='{"natural_response":"你好"'))
            assert "natural_response_completed_seconds" in stages
            assert "semantic_envelope_completed_seconds" not in stages
            yield SimpleNamespace(method="item/completed", payload=SimpleNamespace(item=SimpleNamespace(type="agentMessage", text=envelope)))
            yield SimpleNamespace(method="turn/completed", payload=SimpleNamespace(turn=SimpleNamespace(status="completed", error=None)))

    class Client:
        id = "thread"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def thread_start(self, **kwargs):
            assert kwargs == {"ephemeral": True}
            return self

        def turn(self, instruction, **kwargs):
            assert instruction == "original prompt"
            assert kwargs == {"output_schema": {"type": "object"}}
            return Turn()

    with observation.factory(Client)() as client:
        thread = client.thread_start(ephemeral=True)
        turn = thread.turn("original prompt", output_schema={"type": "object"})
        assert thread.id == "thread" and turn.id == "turn"
        assert len(list(turn.stream())) == 3
    assert stages["wire_characters"] == len(envelope)
    assert stages["wire_utf8_bytes"] == len(envelope.encode("utf-8"))
    assert stages["natural_response_completed_seconds"] <= stages["semantic_envelope_completed_seconds"]
    assert stages["semantic_envelope_completed_seconds"] <= stages["sdk_teardown_completed_seconds"]


@pytest.mark.parametrize("status", ("completed", "failed"))
def test_terminal_fallback_observes_wire_without_inventing_success(status):
    stages = {}
    observation = ProviderObservation(stages, [0])
    wire = '{"natural_response":"Text", "semantics":{}}'

    class Client:
        id = "id"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def thread_start(self):
            return self

        def turn(self):
            return self

        def stream(self):
            yield SimpleNamespace(method="item/agentMessage/delta", payload=SimpleNamespace(delta=wire))
            yield SimpleNamespace(method="turn/completed", payload=SimpleNamespace(turn=SimpleNamespace(status=status, error=None)))

    with observation.factory(Client)() as client:
        list(client.thread_start().turn().stream())
    assert stages["wire_characters"] == len(wire)
    assert stages["wire_semantic_field_characters"] == {}
    assert ("semantic_envelope_completed_seconds" in stages) == (status == "completed")
