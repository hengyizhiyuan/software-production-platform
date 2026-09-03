"""Focused MVP-E2E-1I checkout synchronization contracts."""

from pathlib import Path
import subprocess

import pytest

from spg.domain.runtime import RepositoryRealityError
from spg.infrastructure.git_checkout import GitTrustedCheckoutSynchronizer


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, str, str, str, str]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "README.md").write_text("source\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "source")
    source = _git(repository, "rev-parse", "HEAD")

    (repository / "result.md").write_text("trusted\n", encoding="utf-8")
    _git(repository, "add", "result.md")
    _git(repository, "commit", "-m", "trusted")
    trusted = _git(repository, "rev-parse", "HEAD")
    tree = _git(repository, "rev-parse", "HEAD^{tree}")

    _git(repository, "read-tree", "--reset", "-u", source)
    return repository, "refs/heads/main", source, trusted, tree


def _synchronize(
    repository: Path,
    reference: str,
    source: str,
    trusted: str,
    tree: str,
):
    return GitTrustedCheckoutSynchronizer().synchronize(
        repository_path=repository,
        authoritative_ref=reference,
        source_revision=source,
        trusted_revision=trusted,
        trusted_tree_identity=tree,
    )


def test_checkout_01_04_06_07_materializes_exact_trusted_tree(tmp_path: Path) -> None:
    repository, reference, source, trusted, tree = _repository(tmp_path)

    result = _synchronize(repository, reference, source, trusted, tree)

    assert result.synchronized is True
    assert result.repository_ref == reference
    assert result.repository_revision == trusted
    assert result.repository_tree_identity == tree
    assert _git(repository, "status", "--porcelain=v1") == ""
    assert (repository / "result.md").read_text(encoding="utf-8") == "trusted\n"


def test_checkout_10_repeat_is_idempotent(tmp_path: Path) -> None:
    repository, reference, source, trusted, tree = _repository(tmp_path)
    _synchronize(repository, reference, source, trusted, tree)

    result = _synchronize(repository, reference, source, trusted, tree)

    assert result.synchronized is False
    assert _git(repository, "status", "--porcelain=v1") == ""


@pytest.mark.parametrize("change_kind", ["unstaged", "untracked", "staged"])
def test_checkout_08_unexpected_changes_are_preserved_and_blocked(
    tmp_path: Path,
    change_kind: str,
) -> None:
    repository, reference, source, trusted, tree = _repository(tmp_path)
    if change_kind == "unstaged":
        (repository / "README.md").write_text("independent\n", encoding="utf-8")
    elif change_kind == "untracked":
        (repository / "independent.txt").write_text("keep\n", encoding="utf-8")
    else:
        (repository / "README.md").write_text("staged\n", encoding="utf-8")
        _git(repository, "add", "README.md")

    with pytest.raises(RepositoryRealityError, match="REPOSITORY_CHECKOUT_DIVERGENCE"):
        _synchronize(repository, reference, source, trusted, tree)

    if change_kind == "unstaged":
        assert (repository / "README.md").read_text(encoding="utf-8") == "independent\n"
    elif change_kind == "untracked":
        assert (repository / "independent.txt").read_text(encoding="utf-8") == "keep\n"
    else:
        assert (repository / "README.md").read_text(encoding="utf-8") == "staged\n"


def test_checkout_02_03_05_wrong_ref_or_tree_is_blocked(tmp_path: Path) -> None:
    repository, reference, source, trusted, tree = _repository(tmp_path)

    with pytest.raises(RepositoryRealityError, match="REPOSITORY_CHECKOUT_DIVERGENCE"):
        _synchronize(repository, "refs/heads/other", source, trusted, tree)
    with pytest.raises(RepositoryRealityError, match="REPOSITORY_CHECKOUT_DIVERGENCE"):
        _synchronize(repository, reference, source, trusted, "0" * 40)


def test_checkout_09_does_not_create_commits_or_advance_runtime_state(
    tmp_path: Path,
) -> None:
    repository, reference, source, trusted, tree = _repository(tmp_path)
    commits_before = _git(repository, "rev-list", "--count", "--all")

    _synchronize(repository, reference, source, trusted, tree)

    assert _git(repository, "rev-list", "--count", "--all") == commits_before
    assert _git(repository, "rev-parse", reference) == trusted
