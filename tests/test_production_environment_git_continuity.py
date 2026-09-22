from datetime import UTC, datetime
from pathlib import Path
import subprocess

import pytest

from spg.domain.production_environment import EnvironmentProviderError
from spg.infrastructure.production_environment import GitContinuityInspector


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def commit(repository: Path, path: str, content: str, message: str) -> str:
    target = repository / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    git(repository, "add", path)
    git(repository, "-c", "user.name=Watt Test", "-c", "user.email=watt@example.invalid", "commit", "-m", message)
    return git(repository, "rev-parse", "HEAD")


def test_git_continuity_preserves_branch_commit_ancestry_and_diff(tmp_path):
    repository = tmp_path / "brownfield"
    repository.mkdir()
    git(repository, "init", "-b", "main")
    base = commit(repository, "index.html", "v1", "base")
    git(repository, "switch", "-c", "feature/environment")
    current = commit(repository, "index.html", "v2", "feature")

    continuity = GitContinuityInspector().inspect(
        repository,
        repository_identity="repo:brownfield",
        base_revision=base,
        observed_at=datetime.now(UTC),
    )

    assert continuity.branch == "feature/environment"
    assert continuity.base_commit == base
    assert continuity.current_commit == current
    assert continuity.ancestry == (base, current)
    assert continuity.diff_reference == f"{base}..{current}"


def test_git_continuity_rejects_non_ancestor_baseline(tmp_path):
    repository = tmp_path / "brownfield"
    repository.mkdir()
    git(repository, "init", "-b", "main")
    base = commit(repository, "index.html", "v1", "base")
    git(repository, "switch", "--orphan", "unrelated")
    (repository / "index.html").unlink(missing_ok=True)
    commit(repository, "other.txt", "unrelated", "unrelated")

    with pytest.raises(EnvironmentProviderError, match="not an ancestor"):
        GitContinuityInspector().inspect(
            repository,
            repository_identity="repo:brownfield",
            base_revision=base,
        )
