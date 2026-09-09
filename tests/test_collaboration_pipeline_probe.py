from types import SimpleNamespace

import pytest

from benchmarks.conversation_quality.pipeline_probe import (
    ProviderObservation,
    SCENARIOS_V31_ZH,
    TextObservation,
    completed_top_level_string,
    first_complete_sentence,
    load_scenarios,
    selected_case_numbers,
    stable_hash,
)
from benchmarks.conversation_quality.replay_probe import interpret_fixed_basis, replay_cases


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


def test_text_observer_measures_real_sentence_gaps_and_tail_separately():
    observed = TextObservation()
    observed.delta(" ", 1)
    observed.delta("先做报名", 2)
    observed.delta("和候补。", 3.5)
    observed.delta("\n", 5)
    observed.delta("这是最常用的流程。", 8)
    observed.terminal(12, success=True)
    result = observed.as_dict()
    assert result["first_text_seconds"] == 2
    assert result["first_complete_sentence_seconds"] == 3.5
    assert result["first_complete_sentence_text"] == "先做报名和候补。"
    assert result["maximum_text_delta_gap_seconds"] == 4.5
    assert result["last_text_to_completion_seconds"] == 4
    assert result["first_sentence_survives_final"] is True
    assert len(result["text_delta_events"]) == 5
    assert "usefulness requires Human review" in result["sentence_measurement"]


@pytest.mark.parametrize("success", (True, False))
def test_final_reset_never_manufactures_first_text_sentence_or_tail(success):
    observed = TextObservation()
    observed.reset("最终回答。", 10)
    observed.terminal(12, success=success)
    result = observed.as_dict()
    assert result["first_text_seconds"] is None
    assert result["first_complete_sentence_seconds"] is None
    assert result["maximum_text_delta_gap_seconds"] is None
    assert result["last_text_to_completion_seconds"] is None
    assert result["completion_seconds"] == (12 if success else None)
    assert result["failure_received_seconds"] == (None if success else 12)


def test_failed_or_replaced_stream_retains_only_observed_initial_sentence():
    observed = TextObservation()
    observed.delta("建议做报名。", 2)
    observed.reset("建议做名额管理。", 6)
    observed.terminal(7, success=True)
    assert observed.as_dict()["first_complete_sentence_seconds"] == 2
    assert observed.as_dict()["first_sentence_survives_final"] is False
    assert observed.as_dict()["last_text_to_completion_seconds"] is None
    failed = TextObservation()
    failed.delta("建议做报名。", 2)
    failed.terminal(8, success=False)
    assert failed.as_dict()["first_complete_sentence_seconds"] == 2
    assert failed.as_dict()["completion_seconds"] is None
    assert failed.as_dict()["first_sentence_survives_final"] is None
    assert failed.as_dict()["last_text_to_completion_seconds"] is None


def test_later_observation_failure_invalidates_success_without_erasing_actual_stream():
    observed = TextObservation()
    observed.delta("先做好报名。", 1)
    observed.delta("候补可以后补。", 1.5)
    observed.terminal(2, success=True)
    assert observed.as_dict()["last_text_to_completion_seconds"] == 0.5

    # Model replay bookkeeping failing after the candidate was returned: a FAILED
    # case must not contribute successful completion or final-content statistics.
    observed.terminal(3, success=False)
    result = observed.as_dict()
    assert result["completion_seconds"] is None
    assert result["last_text_to_completion_seconds"] is None
    assert result["first_sentence_survives_final"] is None
    assert result["failure_received_seconds"] == result["terminal_received_seconds"] == 3
    assert result["first_text_seconds"] == result["first_complete_sentence_seconds"] == 1
    assert result["first_complete_sentence_text"] == "先做好报名。"
    assert result["maximum_text_delta_gap_seconds"] == 0.5
    assert len(result["text_delta_events"]) == 2


@pytest.mark.parametrize(("text", "expected"), (
    ("版本 3.1 先做好报名。后面再扩展。", "版本 3.1 先做好报名。"),
    ("Budget is 2.5. Start here.", "Budget is 2.5."),
    ("Start with sign-up. Then waitlists.", "Start with sign-up."),
    ("没有完整句", None),
))
def test_complete_sentence_is_only_an_explicit_punctuation_heuristic(text, expected):
    assert first_complete_sentence(text) == expected


def test_extended_scenarios_preserve_original_sequence_and_cover_constraints():
    messages, intents = load_scenarios("v32-zh")
    assert messages[:5] == SCENARIOS_V31_ZH
    assert len(messages) == len(intents) == 9
    assert "预算五千元" in messages[5]
    assert "先别继续问问题" in messages[6]
    assert "纠正一下" in messages[7]
    assert "详细解释" in messages[8]
    assert selected_case_numbers("1,4,4", len(messages)) == {1, 4}
    with pytest.raises(ValueError):
        selected_case_numbers("0", len(messages))


def _replay_basis_payload():
    from datetime import UTC, datetime
    from uuid import UUID
    from spg.domain.interaction import (
        Interaction, InteractionActor, InteractionCondition,
        InteractionInterpretationInput, InteractionRecord,
    )

    now = datetime(2026, 9, 9, tzinfo=UTC)
    return InteractionInterpretationInput(
        interaction=Interaction(
            id=UUID(int=1), condition=InteractionCondition.OPEN,
            created_by="human", updated_by="human", created_at=now, updated_at=now,
        ),
        records=(InteractionRecord(
            id=UUID(int=2), interaction_id=UUID(int=1), sequence=1,
            actor=InteractionActor.HUMAN, source="human", content="先做报名后台。",
            content_fingerprint="a" * 64, created_at=now,
        ),), basis_fingerprint="b" * 64,
    ).model_dump(mode="json")


def test_replay_selects_exact_recorded_basis_and_rejects_missing_or_changed_snapshots():
    basis = _replay_basis_payload()
    case = {"number": 1, "basis": basis, "basis_sha256": stable_hash(basis)}
    report = {"cases": [case, {**case, "repetition": 2}]}
    assert replay_cases(report, "1") == [case]
    changed = {**case, "basis_sha256": "wrong"}
    with pytest.raises(ValueError, match="mismatched"):
        replay_cases({"cases": [changed]})
    with pytest.raises(ValueError, match="Missing"):
        replay_cases({"cases": [{"number": 1}]})
    with pytest.raises(ValueError, match="absent"):
        replay_cases({"cases": [{**case, "number": 2}]}, "1")


def test_replay_reconstructs_independent_identical_bases_without_feeding_back_answers():
    payload = _replay_basis_payload()
    captured = []
    deltas = []
    stages = []

    class Capability:
        def interpret_stream_observed(self, basis, *, on_response_delta, on_pipeline_stage):
            captured.append(basis)
            on_response_delta("建议做好报名。")
            on_pipeline_stage("payload_validated")
            return SimpleNamespace(natural_response="建议做好报名。")

    for _ in range(2):
        result = interpret_fixed_basis(Capability(), payload, deltas.append, stages.append)
        assert result.natural_response == "建议做好报名。"
    assert captured[0] is not captured[1]
    assert captured[0] == captured[1]
    assert len(captured[1].records) == 1
    assert stable_hash(payload) == stable_hash(captured[1].model_dump(mode="json"))
    assert deltas == ["建议做好报名。"] * 2
    assert stages == ["payload_validated"] * 2


def test_provider_call_attempts_include_failed_start_without_manufacturing_turn():
    stages = {}
    observation = ProviderObservation(stages, [0])

    class Client:
        id = "thread"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def thread_start(self):
            return self

        def turn(self, *_args, **_kwargs):
            raise RuntimeError("setup failed")

    with observation.factory(Client)() as client:
        thread = client.thread_start()
        for _ in range(2):
            with pytest.raises(RuntimeError, match="setup failed"):
                thread.turn("unchanged input", model="test-model", effort="low")
    assert stages["provider_call_attempts"] == 2
    assert len(stages["provider_calls"]) == 2
    assert stages["provider_calls"][0]["model"] == "test-model"
    assert stages["provider_calls"][0]["effort"] == "low"
    assert stages["provider_calls"][0]["prompt_sha256"] == stages["provider_calls"][1]["prompt_sha256"]
    assert all("turn_created" not in call for call in stages["provider_calls"])
    assert "provider_turn_ready_seconds" not in stages
    assert "provider_terminal_seconds" not in stages


def test_all_added_multiturn_corpus_cases_are_loadable_as_real_human_sequences():
    import json
    from pathlib import Path

    corpus = json.loads((Path(__file__).parents[1] / "benchmarks/conversation_quality/corpus.json").read_text())
    cases = [case for case in corpus if case.get("evaluation_group") == "v32_multiturn"]
    assert len(cases) == 6
    for case in cases:
        messages, intents = load_scenarios("v3-en", case["id"])
        assert len(messages) == len(intents) >= 3
        assert all(isinstance(message, str) and message.strip() for message in messages)
        assert intents[0] == "NEW_GOAL"
