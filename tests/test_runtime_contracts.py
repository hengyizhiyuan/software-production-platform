from pathlib import Path
import subprocess

import pytest
from pydantic import ValidationError

from spg.domain.runtime import (
    CompletionContract,
    ProductionHorizon,
    RepositoryRealityError,
)
from spg.infrastructure.git_repository import GitRepositoryObserver


def test_completion_contract_requires_a_declared_obligation() -> None:
    with pytest.raises(ValidationError, match="at least one obligation"):
        CompletionContract()


def test_completion_contract_is_typed_and_not_code_specific() -> None:
    contract = CompletionContract(
        required_outputs=("updated architecture record",),
        verification_obligations=("document review passes",),
    )

    assert contract.required_outputs == ("updated architecture record",)
    assert ProductionHorizon.DOCUMENTATION.value == "DOCUMENTATION"
    assert "changed_code_files" not in CompletionContract.model_fields


def test_git_observer_rejects_dirty_working_reality(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(
        ["git", "-C", str(repository), "init", "-b", "main"],
        check=True,
        capture_output=True,
    )
    (repository / "uncommitted.md").write_text("not authoritative\n", encoding="utf-8")

    with pytest.raises(RepositoryRealityError, match="dirty repository"):
        GitRepositoryObserver().observe(
            repository,
            "test://dirty-repository",
            "refs/heads/main",
        )
