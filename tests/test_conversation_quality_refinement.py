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
RECOVERY_CASES = tuple(
    case
    for case in json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    if case.get("evaluation_group") == "wic_experience_recovery"
)


def test_experience_recovery_corpus_covers_required_human_journeys() -> None:
    assert {case["id"] for case in RECOVERY_CASES} == {
        "recovery-broad-enterprise-site-zh",
        "recovery-consumer-decision-mini-program-zh",
        "recovery-mobile-app-zh",
        "recovery-internal-approval-system-zh",
        "recovery-developer-cli-zh",
        "recovery-engineering-infrastructure-zh",
        "recovery-content-site-zh",
        "recovery-vague-business-idea-zh",
        "recovery-domain-context-zh",
        "recovery-specific-style-question-zh",
        "recovery-direct-pages-question-zh",
        "recovery-human-uncertainty-zh",
        "recovery-long-context-zh",
    }
    contracts = {
        contract for case in RECOVERY_CASES for contract in case["quality_contracts"]
    }
    assert {
        "cognitive_alignment",
        "orient_before_detail",
        "direct_answer_first",
        "meaningful_alternatives",
        "not_questionnaire",
        "no_recap_dump",
        "advance_the_thinking",
        "object_relevant_next_move",
        "no_unsupported_domain_premise",
        "no_cross_domain_template",
        "technical_context_sensitivity",
        "help_frame_immature_concept",
    }.issubset(contracts)


def test_recovery_corpus_spans_distinct_objects_without_expected_prose() -> None:
    broad_cases = {
        case["id"]: case
        for case in RECOVERY_CASES
        if "no_cross_domain_template" in case["quality_contracts"]
    }
    assert len(broad_cases) >= 8
    assert len({case["category"] for case in broad_cases.values()}) >= 6
    for case in broad_cases.values():
        assert "expected_response" not in case
        assert len(case.get("review_guidance", ())) >= 2
        assert "object_relevant_next_move" in case["quality_contracts"] or (
            "help_frame_immature_concept" in case["quality_contracts"]
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
