"""Validate runnable multi-turn review fixtures, not subjective model quality."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spg.domain.conversation import ConversationTurnIntent


CORPUS_PATH = (
    Path(__file__).resolve().parents[1]
    / "benchmarks"
    / "conversation_quality"
    / "corpus.json"
)
MULTITURN_CASES = tuple(
    case
    for case in json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    if case.get("evaluation_group") == "v32_multiturn"
)


def test_multiturn_review_covers_quality_risks_beyond_single_intent() -> None:
    contracts = {
        contract for case in MULTITURN_CASES for contract in case["quality_contracts"]
    }

    assert {
        "priority_grounded_in_constraints",
        "correction_persistence",
        "respect_rejected_direction",
        "respect_deferred_question",
        "detour_return",
        "value_proportional_detail",
        "warm_without_flattery",
        "no_invented_user_facts",
        "no_invented_file_path",
    }.issubset(contracts)


@pytest.mark.parametrize("case", MULTITURN_CASES, ids=lambda case: case["id"])
def test_multiturn_fixture_can_run_from_an_empty_pre_work_conversation(case) -> None:
    # Every step is a Human input; Watt replies must come from the tested condition.
    # No fixture supplies a favorable model reply or claims an existing saved file.
    messages = case["messages"]
    intents = [ConversationTurnIntent(value) for value in case["expected_intents"]]

    assert len(messages) >= 3
    assert len(messages) == len(intents)
    assert all(isinstance(message, str) and message.strip() for message in messages)
    assert intents[0] is ConversationTurnIntent.NEW_GOAL
    assert intents[-1].value == case["expected_intent"]
    assert len(case["review_guidance"]) >= 2
    assert all(
        isinstance(guidance, str) and guidance.strip()
        for guidance in case["review_guidance"]
    )
