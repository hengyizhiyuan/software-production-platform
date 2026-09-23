from pathlib import Path
import subprocess
from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.domain.assets import (
    RepositoryAcquisitionFailure,
    RepositoryAcquisitionFailureCategory,
)
from spg.infrastructure.production_environment import GitRepositoryAcquirer
from spg.application.interaction import _repository_branch_status_answer
from spg.application.repository_branch_authority import governed_branch_creation_target
from spg.domain.engineering_semantics import SemanticFactAuthority
from spg.domain.interaction import InteractionActor, RepositoryAcquisitionState


@pytest.mark.parametrize(
    "stderr,category,retryable",
    (
        (
            "fatal: could not read Username for 'https://github.com': terminal prompts disabled",
            RepositoryAcquisitionFailureCategory.AUTH_REQUIRED,
            True,
        ),
        (
            "remote: Repository not found.",
            RepositoryAcquisitionFailureCategory.REPOSITORY_NOT_FOUND,
            False,
        ),
        (
            "fatal: unable to access: Could not resolve host: github.com",
            RepositoryAcquisitionFailureCategory.NETWORK_FAILURE,
            True,
        ),
        (
            "fatal: Remote branch missing not found in upstream origin",
            RepositoryAcquisitionFailureCategory.INVALID_BRANCH,
            False,
        ),
        (
            "fatal: cannot create directory: No space left on device",
            RepositoryAcquisitionFailureCategory.FILESYSTEM_FAILURE,
            True,
        ),
    ),
)
def test_git_acquisition_preserves_failure_category_and_technical_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stderr: str,
    category: RepositoryAcquisitionFailureCategory,
    retryable: bool,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0], returncode=128, stdout="", stderr=stderr
        ),
    )

    with pytest.raises(RepositoryAcquisitionFailure) as raised:
        GitRepositoryAcquirer().acquire(
            tmp_path,
            "https://github.com/acme/repository.git",
            tmp_path / "repository",
        )

    failure = raised.value
    assert failure.category is category
    assert failure.retryable is retryable
    assert failure.technical_evidence["stderr"] == stderr
    assert "Traceback" not in failure.human_message


def test_git_acquisition_disables_interactive_credential_prompt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observed = {}

    def run(*args, **kwargs):
        observed.update(kwargs)
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout="", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", run)
    GitRepositoryAcquirer().acquire(
        tmp_path,
        "https://github.com/acme/repository.git",
        tmp_path / "repository",
    )

    assert observed["env"]["GIT_TERMINAL_PROMPT"] == "0"


def test_branch_status_answer_uses_current_work_revision_not_model_plan() -> None:
    reality = SimpleNamespace(
        governed_revision=SimpleNamespace(
            repository_ref="refs/heads/main",
            source_revision="abc123",
        ),
        repository_acquisition_state=RepositoryAcquisitionState.REQUESTED,
    )
    pending = _repository_branch_status_answer(
        "切好了吗？目前项目分支是什么？", reality
    )
    reality.governed_revision.repository_ref = "refs/heads/test"
    reality.repository_acquisition_state = RepositoryAcquisitionState.READY
    ready = _repository_branch_status_answer(
        "切好了吗？目前项目分支是什么？", reality
    )

    assert "仍绑定本地分支 main" in pending
    assert "尚未完成" in pending
    assert "本地分支是 test" in ready
    assert "推送到远端" in ready


@pytest.mark.parametrize(
    "human_command,expected",
    (
        ("切一个新分支：test", "test"),
        ("如何创建分支 test？", None),
        ("不要创建分支 test", None),
        ("切一个新分支：other", None),
    ),
)
def test_provider_branch_vocabulary_requires_cited_human_command(
    human_command: str, expected: str | None,
) -> None:
    source_id = uuid4()
    branch_fact = SimpleNamespace(
        is_current=True,
        subject="repository.branch_name",
        value="test",
        authority=SemanticFactAuthority.HUMAN_EXPLICIT,
        qualifiers={"branch_kind": "new"},
        provenance=SimpleNamespace(source_record_ids=(source_id,)),
    )
    record = SimpleNamespace(actor=InteractionActor.HUMAN, content=human_command)

    assert governed_branch_creation_target(
        (branch_fact,), record_for_id=lambda record_id: record if record_id == source_id else None,
    ) == expected
