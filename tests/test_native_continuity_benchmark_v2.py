from __future__ import annotations

import json
from pathlib import Path

from spg.domain.native_execution import canonical_digest

from benchmarks.native_executor_continuity_v2.evaluator import evaluate
from benchmarks.native_executor_continuity_v2.runner import (
    BudgetLedger,
    SPEC_PATH,
    plan,
    prepare_repositories,
)


EXPECTED_DIGEST = "6f04b354694d9fdd9b536d49d7879f18c136d8149d8d73a59677d0dd5abdfc97"


def _spec() -> dict:
    return json.loads(SPEC_PATH.read_text())


def test_v2_plan_preserves_the_frozen_execution_count_and_replacements() -> None:
    spec = _spec()
    generated = plan(spec)
    frozen = json.loads(
        (SPEC_PATH.parent / "../../.spg/validation-evidence/native-cont-v2/frozen-plan.json")
        .resolve()
        .read_text()
    )

    assert canonical_digest(spec) == EXPECTED_DIGEST
    assert frozen == {"spec_digest": EXPECTED_DIGEST, "trials": generated}
    assert len(generated) == 36
    assert sum(item["arm"] == "A" for item in generated) == 18
    assert sum(item["arm"] == "B" for item in generated) == 18
    assert {
        item["execution_id"]
        for item in generated
        if "model_replacement" in item["injections"]
    } == {"T3-2-B", "T4-1-B", "T5-2-B"}


def test_v2_budget_includes_the_original_conservative_spend(tmp_path: Path) -> None:
    spec = _spec()
    ledger = BudgetLedger(tmp_path / "results.json", spec)

    assert ledger.data["prior_conservative_cost_rmb"] == 3.69511347
    assert spec["hard_cost_limit"] == 100.0


def test_v2_t5_verification_isolated_by_repository() -> None:
    task = next(item for item in _spec()["tasks"] if item["id"] == "T5")

    assert [(item["cwd"], item["command"]) for item in task["verification"]] == [
        ("client", "pytest -q tests/test_status_client.py"),
        ("server", "pytest -q tests/test_status_api.py"),
        ("client", "python -m compileall -q src"),
        ("server", "python -m compileall -q src"),
    ]


def test_v2_evaluator_applies_frozen_scope_and_quality_anchors(tmp_path: Path) -> None:
    task = next(item for item in _spec()["tasks"] if item["id"] == "T3")
    root, _ = prepare_repositories(tmp_path / "fixture", task)
    (root / "src/labels.py").write_text(
        "def normalize_label(value: str) -> str:\n"
        "    return value.strip().lower().replace(' ', '-')\n\n"
        "def normalize_many(values: list[str]) -> list[str]:\n"
        "    return [normalize_label(value) for value in values]\n",
        encoding="utf-8",
    )

    assessment = evaluate(
        root,
        task,
        [{"command": "frozen", "returncode": 0}],
        "RESULT_READY",
    )

    assert assessment["mandatory_gate_passed"] is True
    assert assessment["material_defects"] == []
    assert assessment["score"] == {
        "correctness": 4,
        "maintainability": 4,
        "scope_discipline": 4,
        "tests": 4,
        "operability": 4,
    }
