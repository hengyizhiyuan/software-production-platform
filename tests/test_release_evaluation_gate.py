from pathlib import Path

from spg.evaluation.release_gate import CORPUS, EvaluationCase, qualify, select_cases


def test_critical_regression_fails_domain_and_release_gate(
    tmp_path: Path, monkeypatch,
) -> None:
    failed = tmp_path / "test_controlled_regression.py"
    failed.write_text(
        "def test_accepted_behavior():\n"
        "    assert False, 'controlled regression must fail qualification'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SPG_TEST_DATABASE_URL", "qualification-present")
    result = qualify((EvaluationCase(
        "CONTROLLED_REGRESSION", "ASSURANCE", str(failed), critical=True,
    ),))
    assert result["qualification"] == "FAIL"
    assert result["domains"]["ASSURANCE"] == "FAIL"
    assert result["cases"][0]["result"] == "FAILED"
    assert result["cases"][0]["counts"]["failures"] == 1


def test_release_gate_requires_postgresql_instead_of_accepting_skips(monkeypatch) -> None:
    import pytest

    monkeypatch.delenv("SPG_TEST_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="PostgreSQL cases must not silently skip"):
        qualify(())


def test_corpus_classifies_each_case_and_focuses_affected_capability() -> None:
    assert all(
        case.capability_family and case.protected_invariant and case.risk
        and case.origin and case.required_environment and case.baseline_version
        for case in CORPUS
    )
    focused = select_cases(purpose="focused", capability_families=("SELF_OBSERVE",))
    identities = {case.identity for case in focused}
    assert {"TRANSIENT_HEALTH_NOISE", "CONFIRMED_HEALTH_FAILURE",
            "AUTHORITATIVE_REALITY_MISMATCH", "RESPONSE_OPERATION_REALITY"} <= identities
    assert "HUMAN_DELIVERY_AUTHORITY" not in identities
    release = select_cases(purpose="release")
    assert {case.identity for case in release} == {case.identity for case in CORPUS if case.critical}
    assert any(case.scenario_type == "GOLDEN_JOURNEY" for case in release)


def test_noncritical_similarity_group_consolidates_without_losing_history() -> None:
    cases = (
        EvaluationCase("DOGFOOD_ORIGINAL", "RESILIENCE", "tests/test_release_evaluation_gate.py",
                       critical=False, capability_family="SELF_OBSERVE", origin="DOGFOOD",
                       duplicate_group="startup-noise", estimated_cost_seconds=40),
        EvaluationCase("DOGFOOD_DUPLICATE", "RESILIENCE", "tests/test_release_evaluation_gate.py",
                       critical=False, capability_family="SELF_OBSERVE", origin="DOGFOOD",
                       duplicate_group="startup-noise", estimated_cost_seconds=10),
        EvaluationCase("CRITICAL_ORACLE", "ASSURANCE", "tests/test_release_evaluation_gate.py",
                       critical=True, capability_family="SELF_OBSERVE",
                       duplicate_group="startup-noise", risk="CRITICAL"),
    )
    focused = select_cases(cases, purpose="focused", capability_families=("SELF_OBSERVE",))
    assert {case.identity for case in focused} == {"DOGFOOD_DUPLICATE", "CRITICAL_ORACLE"}
    assert len(cases) == 3  # grouping selects a representative; it never erases history
    release = select_cases(cases, purpose="release")
    assert tuple(case.identity for case in release) == ("CRITICAL_ORACLE",)


def test_meaningful_regression_is_preferred_over_cheaper_duplicate() -> None:
    cases = (
        EvaluationCase("HISTORICAL_FAILURE", "RESILIENCE", "tests/test_release_evaluation_gate.py",
                       critical=False, capability_family="SELF_OBSERVE",
                       duplicate_group="startup-noise", estimated_cost_seconds=40,
                       last_meaningful_regression="2026-09-25"),
        EvaluationCase("CHEAPER_DUPLICATE", "RESILIENCE", "tests/test_release_evaluation_gate.py",
                       critical=False, capability_family="SELF_OBSERVE",
                       duplicate_group="startup-noise", estimated_cost_seconds=10),
    )
    assert tuple(case.identity for case in select_cases(
        cases, purpose="focused", capability_families=("SELF_OBSERVE",),
    )) == ("HISTORICAL_FAILURE",)
