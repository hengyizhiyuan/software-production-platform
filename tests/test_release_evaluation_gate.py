from pathlib import Path
import os
import pytest
from spg.config import Settings
from spg.infrastructure.persistence import Database

from spg.evaluation.release_gate import (
    CORPUS, EvaluationCase, qualify, select_cases, persist_evaluation,
    compare_baseline,
)


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


def test_p1_q7_versioned_release_evaluation_compares_qualified_baseline(
    p1_postgres_database, tmp_path: Path, monkeypatch,
) -> None:
    postgres_database = p1_postgres_database
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import delete, select
    from spg.infrastructure.persistence.evaluation_schema import evaluation_runs
    database_url = postgres_database.engine.url.render_as_string(hide_password=False)
    monkeypatch.setenv("SPG_DATABASE_URL", database_url)
    command.upgrade(Config(Path(__file__).resolve().parents[1] / "alembic.ini"), "head")
    sample = tmp_path / "test_evaluation_sample.py"
    sample.write_text("def test_interaction(): assert True\n"
                      "def test_production(): assert True\n"
                      "def test_resilience(): assert True\n"
                      "def test_assurance(): assert False\n", encoding="utf-8")
    cases = tuple(EvaluationCase(name, domain, f"{sample}::{selector}",
        critical=domain != "ASSURANCE", required_environment="PYTHON")
        for name, domain, selector in (
            ("P1-INTERACTION", "INTERACTION", "test_interaction"),
            ("P1-PRODUCTION", "PRODUCTION", "test_production"),
            ("P1-RESILIENCE", "RESILIENCE", "test_resilience"),
            ("P1-ASSURANCE", "ASSURANCE", "test_assurance"),
        ))
    try:
        baseline_report = qualify(cases)
        assert baseline_report["qualification"] == "PASS"
        baseline = persist_evaluation(database_url, version="previous-qualified",
            revision="a" * 40, purpose="release", report=baseline_report)
        sample.write_text(sample.read_text().replace("test_assurance(): assert False",
                                                     "test_assurance(): assert True"), encoding="utf-8")
        current_report = qualify(cases)
        current = persist_evaluation(database_url, version="current-candidate",
            revision="b" * 40, purpose="release", report=current_report)
        assert current["baseline_run_id"] == baseline["id"]
        assert current["trend"]["status"] == "COMPARED"
        assert current["trend"]["delta"]["failure"] == -1
        assert current["trend"]["delta"]["total_success"] == 1
        assert current["trend"]["current"]["work_cost"] == "UNREPORTED"
        repeated = persist_evaluation(database_url, version="current-candidate",
            revision="c" * 40, purpose="release", report=current_report)
        assert repeated["baseline_run_id"] == baseline["id"]
        changed_set = compare_baseline({"cases": current_report["cases"][:3]}, baseline_report)
        assert changed_set["status"] == "PARTIAL_COMPARISON"
        assert changed_set["removed_case_ids"] == ["P1-ASSURANCE"]
        assert changed_set["delta"]["failure"] == 0
        with postgres_database.engine.connect() as connection:
            rows = connection.execute(select(evaluation_runs.c.version).where(
                evaluation_runs.c.version.in_(("previous-qualified", "current-candidate")))).all()
        assert {row[0] for row in rows} == {"previous-qualified", "current-candidate"}
    finally:
        with postgres_database.engine.begin() as connection:
            connection.execute(delete(evaluation_runs).where(evaluation_runs.c.version.in_(
                ("previous-qualified", "current-candidate"))))


@pytest.fixture
def p1_postgres_database():
    url = os.environ.get("SPG_TEST_DATABASE_URL")
    if not url:
        pytest.skip("SPG_TEST_DATABASE_URL is required")
    database = Database.from_settings(Settings(database_url=url))
    try:
        yield database
    finally:
        database.dispose()
