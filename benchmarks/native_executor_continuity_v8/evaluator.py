"""Frozen deterministic engineering-quality evaluator for benchmark v2."""

from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess


DIMENSIONS = (
    "correctness",
    "maintainability",
    "scope_discipline",
    "tests",
    "operability",
)

MINIMUM_TESTS = {"T1": 4, "T2": 4, "T3": 3, "T4": 4, "T5": 6, "T6": 4}


def _repositories(root: Path, task: dict) -> dict[str, Path]:
    if tuple(task["repositories"]) == ("primary",):
        return {"primary": root}
    return {name: root / name for name in task["repositories"]}


def _changed_paths(repo: Path) -> set[str]:
    process = subprocess.run(
        ["git", "-C", str(repo), "status", "--short", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    )
    paths = {
        line[3:].strip().removesuffix("/")
        for line in process.stdout.splitlines()
        if len(line) >= 4
    }
    return {
        path for path in paths
        if not ({"__pycache__", ".pytest_cache"} & set(Path(path).parts))
        and not path.endswith((".pyc", ".pyo"))
    }


def _source_files(repos: dict[str, Path]) -> list[Path]:
    return [
        path
        for repo in repos.values()
        for path in repo.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and "tests" not in path.parts
        and "__pycache__" not in path.parts
    ]


def _test_count(repos: dict[str, Path]) -> int:
    count = 0
    for repo in repos.values():
        for path in repo.glob("tests/test_*.py"):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError, UnicodeError):
                continue
            count += sum(
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name.startswith("test_")
                for node in ast.walk(tree)
            )
    return count


def evaluate(root: Path, task: dict, checks: list[dict], terminal: str | None) -> dict:
    """Return anchored scores and the independent mandatory gate."""

    repos = _repositories(root, task)
    checks_pass = bool(checks) and all(item.get("returncode") == 0 for item in checks)
    expected: dict[str, set[str]] = {
        name: set(spec["write_scope"])
        for name, spec in task["repositories"].items()
    }
    changed = {name: _changed_paths(repo) for name, repo in repos.items()}
    outside_scope = {
        name: sorted(paths - expected[name]) for name, paths in changed.items()
    }
    missing_outputs = {
        name: sorted(path for path in expected[name] if not (repos[name] / path).is_file())
        for name in repos
    }
    exact_scope = not any(outside_scope.values()) and not any(missing_outputs.values())

    source_files = _source_files(repos)
    source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace") for path in source_files
    )
    debt_markers = len(re.findall(r"\b(?:TODO|FIXME|NotImplementedError)\b", source_text))
    syntax_ok = True
    for path in source_files:
        if path.suffix == ".py":
            try:
                ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError, UnicodeError):
                syntax_ok = False
                break

    test_count = _test_count(repos)
    minimum_tests = MINIMUM_TESTS[task["id"]]
    forbidden_network = task["id"] == "T6" and bool(
        re.search(r"\b(?:fetch|XMLHttpRequest|WebSocket)\s*\(", source_text)
    )
    oversized = any(path.stat().st_size > 100_000 for path in source_files)

    scores = {
        "correctness": 4 if checks_pass and terminal == "RESULT_READY" else (2 if checks_pass else 0),
        "maintainability": (
            4 if syntax_ok and debt_markers == 0 else (3 if syntax_ok and debt_markers == 1 else 1)
        ),
        "scope_discipline": 4 if exact_scope else (2 if not any(outside_scope.values()) else 0),
        "tests": (
            4 if checks_pass and test_count >= minimum_tests
            else (3 if checks_pass and test_count >= 2 else (2 if checks_pass else 0))
        ),
        "operability": (
            4 if checks_pass and terminal == "RESULT_READY" and not forbidden_network and not oversized
            else (2 if checks_pass and not forbidden_network and not oversized else 0)
        ),
    }
    material_defects = [name for name, value in scores.items() if value < 3]
    mandatory_pass = checks_pass and exact_scope and not forbidden_network
    return {
        "status": "SCORED_FROZEN_V8",
        "score": scores,
        "mean": round(sum(scores.values()) / len(DIMENSIONS), 3),
        "material_defects": material_defects,
        "mandatory_gate_passed": mandatory_pass,
        "evidence": {
            "checks_passed": checks_pass,
            "changed_paths": {name: sorted(paths) for name, paths in changed.items()},
            "outside_scope": outside_scope,
            "missing_outputs": missing_outputs,
            "test_count": test_count,
            "minimum_test_count": minimum_tests,
            "syntax_ok": syntax_ok,
            "debt_marker_count": debt_markers,
            "forbidden_network_call": forbidden_network,
            "oversized_source": oversized,
        },
    }
