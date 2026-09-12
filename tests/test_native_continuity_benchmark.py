from __future__ import annotations

import json
from pathlib import Path

from spg.domain.native_execution import canonical_digest

from benchmarks.native_executor_continuity.runner import (
    BudgetLedger,
    SPEC_PATH,
    plan,
    prepare_repositories,
)


def _spec() -> dict:
    return json.loads(SPEC_PATH.read_text())


def test_frozen_plan_is_exactly_eighteen_pairs_and_thirty_six_executions() -> None:
    spec = _spec()
    generated = plan(spec)
    frozen = json.loads((SPEC_PATH.parent / "../../.spg/validation-evidence/native-cont/frozen-plan.json").resolve().read_text())

    assert canonical_digest(spec) == "e57d664eb9dbe2988949c0cecf1bb37ab010ecdaf07808dc1921d93bcac91c57"
    assert frozen["spec_digest"] == canonical_digest(spec)
    assert generated == frozen["trials"]
    assert len(generated) == 36
    assert len({item["execution_id"] for item in generated}) == 36
    assert sum(item["arm"] == "A" for item in generated) == 18
    assert sum(item["arm"] == "B" for item in generated) == 18


def test_replacement_assignments_are_only_the_three_frozen_b_executions() -> None:
    replacements = {
        item["execution_id"]
        for item in plan(_spec())
        if "model_replacement" in item["injections"]
    }
    assert replacements == {"T3-2-B", "T4-1-B", "T5-2-B"}


def test_single_repository_fixture_uses_workspace_root(tmp_path: Path) -> None:
    task = next(item for item in _spec()["tasks"] if item["id"] == "T1")
    root, repos = prepare_repositories(tmp_path / "single", task)

    assert repos == {"primary": root}
    assert (root / ".git").is_dir()
    assert not (root / "primary").exists()


def test_multi_repository_fixture_uses_mount_prefixes(tmp_path: Path) -> None:
    task = next(item for item in _spec()["tasks"] if item["id"] == "T5")
    root, repos = prepare_repositories(tmp_path / "multi", task)

    assert set(repos) == {"client", "server"}
    assert all(path.parent == root and (path / ".git").is_dir() for path in repos.values())


def test_existing_cost_ledger_is_never_reset(tmp_path: Path) -> None:
    spec = _spec()
    output = tmp_path / "results.json"
    output.write_text(json.dumps({
        "schema_version": 1,
        "spec_digest": canonical_digest(spec),
        "started_at": "2026-09-12T00:00:00+00:00",
        "trials": [],
        "provider_requests": [{"request_id": "historical", "cost_rmb": 0.5}],
        "actual_cost_rmb": 0.5,
    }))

    ledger = BudgetLedger(output, spec)

    assert ledger.data["actual_cost_rmb"] == 0.5
    assert ledger.data["provider_requests"][0]["request_id"] == "historical"
    assert ledger.data["in_progress"] is None
