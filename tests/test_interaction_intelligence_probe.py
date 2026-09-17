from __future__ import annotations

import json
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = (
    ROOT / "benchmarks/conversation_quality/interaction_intelligence_probe.py"
)
SPEC = importlib.util.spec_from_file_location("interaction_intelligence_probe", PROBE_PATH)
assert SPEC is not None and SPEC.loader is not None
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)
add_cross_case_flags = PROBE.add_cross_case_flags
evaluate_case = PROBE.evaluate_case


def _observed(**updates):
    value = {
        "id": "website-build",
        "input": "我想做一个企业官网。",
        "expected_intents": ["BUILD"],
        "expected_moves": ["PROPOSE"],
        "domain_terms": ["官网", "客户", "信任"],
        "turn_intent": "BUILD",
        "primary_move": "PROPOSE",
        "interaction_strategy": {"candidate_first": True, "max_questions": 1},
        "response": "可以先做一个以客户信任为主线的官网候选：首页说明价值，案例页证明结果，再保留一个清晰的联系入口。",
        "progressive_growth": True,
        "single_response_identity": True,
        "projection_matches_stream": True,
        "replay_matches_projection": True,
        "provider_matches": True,
        "model_matches": True,
    }
    value.update(updates)
    return value


def test_probe_corpus_is_bounded_diverse_and_intent_explicit() -> None:
    cases = json.loads(
        (ROOT / "benchmarks/conversation_quality/interaction_intelligence_cases.json")
        .read_text(encoding="utf-8")
    )
    assert 15 <= len(cases) <= 20
    assert len({case["id"] for case in cases}) == len(cases)
    intents = {intent for case in cases for intent in case["expected_intents"]}
    assert {
        "BUILD", "HOW_TO", "DIRECT_QUESTION", "RECOMMEND", "COMPARE",
        "EXPLORE", "MODIFY", "CORRECTION", "DEPLOY", "ACTION_REQUEST",
    }.issubset(intents)
    ids = {case["id"] for case in cases}
    assert {
        "consumer-mini-program-build", "mobile-app-build", "leave-approval-build",
        "logs-cli-build", "engineering-context-build", "content-site-build",
        "ratio-style-recommendation", "human-uncertainty", "existing-work-change",
    }.issubset(ids)


def test_probe_evaluator_accepts_a_grounded_candidate_without_exact_prose() -> None:
    assert evaluate_case(_observed()) == []


def test_probe_evaluator_flags_intent_move_echo_and_stream_divergence() -> None:
    flags = evaluate_case(
        _observed(
            turn_intent="EXPLORE",
            primary_move="ORIENT",
            response="我想做一个企业官网。？",
            progressive_growth=False,
            projection_matches_stream=False,
        )
    )
    assert "TURN_INTENT_MISMATCH" in flags
    assert "INTERACTION_MOVE_MISMATCH" in flags
    assert "ASK_OR_ORIENT_WHEN_ANSWER_OR_PROPOSE_EXPECTED" in flags
    assert "SEMANTIC_ECHO" in flags
    assert "NON_PROGRESSIVE_RESPONSE_STREAM" in flags
    assert "STREAM_PROJECTION_DIVERGENCE" in flags


def test_probe_evaluator_flags_how_to_question_instead_of_answer() -> None:
    flags = evaluate_case(
        _observed(
            expected_intents=["HOW_TO"],
            turn_intent="HOW_TO",
            expected_moves=["ANSWER"],
            primary_move="ANSWER",
            interaction_strategy={"answer_first": False, "max_questions": 0},
            response="你希望这个官网先解决什么问题？",
        )
    )
    assert "HOW_TO_NOT_ANSWERED_DIRECTLY" in flags
    assert "QUESTION_ALLOWANCE_EXCEEDED" in flags


def test_probe_evaluator_reports_failed_turn_without_secondary_semantic_noise() -> None:
    assert evaluate_case(
        _observed(status="FAILED", failure_code="ModelProviderError")
    ) == ["TURN_FAILED:ModelProviderError"]


def test_probe_cross_domain_check_avoids_chinese_substring_collisions() -> None:
    case = _observed(
        id="website-recommendation",
        expected_intents=["RECOMMEND"],
        turn_intent="RECOMMEND",
        domain_terms=["官网", "视觉"],
        response=(
            "建议使用真实人物场景，不要使用库存感的模特图。"
            "部署后检查运行日志是否存在报错。"
        ),
        interaction_strategy={"candidate_first": True, "max_questions": 0},
    )
    assert not any(
        flag.startswith("CROSS_DOMAIN_LEAKAGE") for flag in evaluate_case(case)
    )


def test_probe_flags_repeated_orient_and_template_reuse_across_cases() -> None:
    same = "先明确当前对象的核心目标，再梳理关键用户和主要场景，最后形成一个可以继续验证的具体候选方向。"
    cases = [
        {"id": str(index), "primary_move": "ORIENT", "response": same, "quality_flags": []}
        for index in range(4)
    ]
    add_cross_case_flags(cases)
    assert "REPEATED_ORIENT_DEFAULT" in cases[2]["quality_flags"]
    assert any(flag.startswith("TEMPLATE_REUSE_WITH:") for flag in cases[0]["quality_flags"])
