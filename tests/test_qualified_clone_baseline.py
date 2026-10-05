"""Exact internal PWU inputs do not advance an accepted Git branch."""
from pathlib import Path
import subprocess
from uuid import uuid4
import pytest
from spg.infrastructure.git_workspace import GitCloneAttemptWorkspace, RepositoryRealityError


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True, stderr=subprocess.PIPE).strip()


@pytest.fixture
def source(tmp_path):
    repo = tmp_path / "source"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Qualification")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "index.html").write_text("<h1>Initial</h1>")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "accepted")
    initial = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "--detach")
    (repo / "team.html").write_text("<h1>Qualified predecessor</h1>")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "qualified internal output")
    internal = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "main")
    return repo, initial, internal


def prepare(source, tmp_path, **kwargs):
    repo, _initial, internal = source
    return GitCloneAttemptWorkspace().prepare(repository_path=repo,
        workspace_root=tmp_path / "workspaces", attempt_id=uuid4(),
        repository_identity="test://qualified-clone", repository_ref="refs/heads/main",
        source_revision=internal, **kwargs)


def test_unqualified_detached_source_stays_rejected(source, tmp_path):
    with pytest.raises(RepositoryRealityError, match="branch does not resolve"):
        prepare(source, tmp_path)


def test_exact_qualified_input_preserves_authoritative_branch_and_acquisition(source, tmp_path):
    repo, initial, internal = source
    binding = prepare(source, tmp_path, expected_authoritative_revision=initial)
    assert git(binding.workspace_path, "rev-parse", "HEAD") == internal
    assert (binding.workspace_path / "team.html").is_file()
    assert git(repo, "rev-parse", "main") == initial
    assert git(binding.workspace_path, "for-each-ref", "--format=%(refname)", "refs/remotes") == "refs/remotes/origin/main"
    assert git(binding.workspace_path, "status", "--porcelain") == ""


def test_qualified_input_cannot_hide_authoritative_ref_change(source, tmp_path):
    repo, initial, internal = source
    git(repo, "update-ref", "refs/heads/main", internal)
    with pytest.raises(RepositoryRealityError, match="branch does not resolve"):
        prepare(source, tmp_path, expected_authoritative_revision=initial)
