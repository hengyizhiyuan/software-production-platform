"""Real Git qualification for explicit, fixed-order Join composition."""

import subprocess
from pathlib import Path

from spg.infrastructure.git_join import GitJoinReconciler


def _git(path: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True).stdout.strip()


def test_real_join_composes_independent_branch_trees_without_moving_ref(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "README.md").write_text("base\n")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "base")
    base = _git(repository, "rev-parse", "HEAD")
    parents = []
    for name in ("api", "web"):
        branch = tmp_path / f"branch-{name}"
        _git(repository, "worktree", "add", "--detach", str(branch), base)
        (branch / f"{name}.txt").write_text(f"{name}\n")
        _git(branch, "add", ".")
        _git(branch, "commit", "-m", name)
        parents.append(_git(branch, "rev-parse", "HEAD"))
    workspace = tmp_path / "join"
    _git(repository, "worktree", "add", "--detach", str(workspace), base)
    trees = tuple(_git(repository, "rev-parse", f"{revision}^{{tree}}") for revision in parents)
    reconciler = GitJoinReconciler()
    first = reconciler.reconcile(
        repository=repository, workspace=workspace, input_revision=base,
        parent_revisions=tuple(parents), parent_trees=trees,
    )
    second = reconciler.reconcile(
        repository=repository, workspace=workspace, input_revision=base,
        parent_revisions=tuple(parents), parent_trees=trees,
    )
    assert first == second
    assert first.conflicts == ()
    assert (workspace / "api.txt").read_text() == "api\n"
    assert (workspace / "web.txt").read_text() == "web\n"
    assert _git(repository, "rev-parse", "refs/heads/main") == base
    assert _git(workspace, "rev-parse", "HEAD") == base


def test_real_join_records_conflict_without_choosing_a_branch(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "shared.txt").write_text("base\n")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "base")
    base = _git(repository, "rev-parse", "HEAD")
    parents = []
    for name in ("first", "second"):
        branch = tmp_path / name
        _git(repository, "worktree", "add", "--detach", str(branch), base)
        (branch / "shared.txt").write_text(f"{name}\n")
        _git(branch, "add", ".")
        _git(branch, "commit", "-m", name)
        parents.append(_git(branch, "rev-parse", "HEAD"))
    workspace = tmp_path / "join"
    _git(repository, "worktree", "add", "--detach", str(workspace), base)
    result = GitJoinReconciler().reconcile(
        repository=repository, workspace=workspace, input_revision=base,
        parent_revisions=tuple(parents),
        parent_trees=tuple(_git(repository, "rev-parse", f"{item}^{{tree}}") for item in parents),
    )
    assert result.conflicts
    content = (workspace / "shared.txt").read_text()
    assert "first" in content and "second" in content and "<<<<<<<" in content
    assert _git(repository, "rev-parse", "refs/heads/main") == base
