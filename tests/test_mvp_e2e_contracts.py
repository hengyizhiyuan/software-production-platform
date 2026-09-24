from pathlib import Path
import subprocess
from uuid import uuid4

import pytest

from spg.config import Settings
from spg.domain.runtime import (
    ArtifactContract,
    ArtifactOperation,
    CompletionContract,
)
from spg.infrastructure.configured_executor import render_governed_instruction
from spg.infrastructure.executor_boundary import (
    SubprocessExecutorTransport,
    build_executor_child_environment,
)
from spg.providers.repository_markdown_verifier import (
    evaluate_repository_artifact,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_PATH = "docs/mvp-e2e/first-real-governed-work.md"
VALID_CONTENT = """# First Real Governed MVP Work

## Purpose

This artifact was produced through the local governed MVP execution flow.

## Guardrails

Provider completion is not Production Truth.
Production Reality is determined independently.

## Evidence Boundary

Human Authority is required before trusted repository integration.
"""


def test_e2e_01_optional_image_profile_preserves_default_runtime() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    base = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
    override = (PROJECT_ROOT / "compose.e2e.yaml").read_text(encoding="utf-8")

    assert "FROM native-verification AS native-tool-host" in dockerfile
    assert "--extra codex-executor" not in dockerfile
    assert dockerfile.rstrip().endswith("FROM runtime-base AS runtime")
    assert "target: runtime" in base
    assert "CODEX_HOME" not in base
    assert "SPG_EXECUTOR_ADAPTER" not in base
    assert "SPG_EXECUTOR_SANDBOX_MODE" not in base
    assert "compose.native-executor.yaml" in override
    assert "codex-sdk" not in override
    assert "SPG_VERIFICATION_ADAPTER: contract-driven-repository" in override
    assert "SPG_RUNTIME_PROFILE: local-docker-native-e2e" in override


def test_e2e_02_typed_configuration_is_bounded() -> None:
    defaults = Settings()
    assert defaults.executor_adapter == "unconfigured"
    assert defaults.verification_adapter == "unconfigured"
    assert defaults.executor_timeout_seconds == 120.0
    assert defaults.executor_max_internal_turns == 3
    assert defaults.executor_sandbox_mode == "workspace-write"
    configured = Settings(
        executor_adapter="watt-native",
        verification_adapter="mvp-e2e-markdown",
        executor_timeout_seconds=600,
        executor_max_internal_turns=1,
        executor_sandbox_mode="full-access",
    )
    assert configured.executor_timeout_seconds == 600
    assert configured.executor_max_internal_turns == 1
    assert configured.executor_sandbox_mode == "full-access"
    with pytest.raises(ValueError):
        Settings(executor_timeout_seconds=601)
    with pytest.raises(ValueError):
        Settings(executor_max_internal_turns=0)
    with pytest.raises(ValueError):
        Settings(executor_sandbox_mode="unsupported")


def test_e2e_03_child_environment_keeps_credentials_out_of_transport() -> None:
    environment = build_executor_child_environment(
        {
            "HOME": "/home/spg",
            "LEGACY_EXECUTOR_HOME": "/home/spg/.legacy-executor",
            "PATH": "/usr/local/bin:/usr/bin",
            "SPG_DATABASE_URL": "not-transported",
            "OPENAI_API_KEY": "not-transported",
            "OTHER_PROVIDER_TOKEN": "not-transported",
        },
        platform_name="posix",
    )
    assert "LEGACY_EXECUTOR_HOME" not in environment
    assert environment["HOME"] == "/home/spg"
    assert "SPG_DATABASE_URL" not in environment
    assert "OPENAI_API_KEY" not in environment
    assert "OTHER_PROVIDER_TOKEN" not in environment


def test_e2e_04_provider_timeout_is_explicit_and_bounded() -> None:
    transport = SubprocessExecutorTransport(
        provider_binding="deterministic-fixture",
        timeout_seconds=630,
        provider_timeout_seconds=600,
        provider_max_internal_turns=3,
        provider_sandbox_mode="full-access",
    )
    assert transport.provider_timeout_seconds == 600
    assert transport.provider_max_internal_turns == 3
    assert transport.provider_sandbox_mode == "full-access"
    with pytest.raises(ValueError):
        SubprocessExecutorTransport(provider_timeout_seconds=601)
    with pytest.raises(ValueError):
        SubprocessExecutorTransport(provider_max_internal_turns=0)
    with pytest.raises(ValueError):
        SubprocessExecutorTransport(provider_sandbox_mode="unsupported")


def test_e2e_05_instruction_contains_only_governed_scope() -> None:
    artifact = _artifact_contract()
    contract = CompletionContract(
        required_outputs=(TARGET_PATH,),
        required_changes=(TARGET_PATH,),
        verification_obligations=("Verify the exact E2E Markdown artifact",),
        artifact_contract=artifact,
    )
    instruction = render_governed_instruction("Create the admitted document", contract)
    assert "Create the admitted document" in instruction
    assert instruction.count(TARGET_PATH) >= 3
    assert "Operation: CREATE" in instruction
    assert "Do not modify any other repository path" in instruction
    assert "Do not commit, push, or change a Git ref" in instruction


def test_e2e_06_targeted_markdown_verification_passes_exact_subject(
    tmp_path: Path,
) -> None:
    repository, source = _repository(tmp_path)
    target = repository / TARGET_PATH
    target.parent.mkdir(parents=True)
    target.write_text(VALID_CONTENT, encoding="utf-8")
    _git(repository, "add", TARGET_PATH)
    _git(repository, "commit", "-m", "candidate")
    proposed = _git(repository, "rev-parse", "HEAD")

    facts = evaluate_repository_artifact(
        repository,
        source,
        proposed,
        _artifact_contract(source_revision=source),
    )
    assert facts.passed


def test_e2e_07_targeted_markdown_verification_rejects_scope_drift(
    tmp_path: Path,
) -> None:
    repository, source = _repository(tmp_path)
    target = repository / TARGET_PATH
    target.parent.mkdir(parents=True)
    target.write_text(VALID_CONTENT, encoding="utf-8")
    (repository / "unexpected.txt").write_text("scope drift\n", encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "invalid candidate")
    proposed = _git(repository, "rev-parse", "HEAD")

    facts = evaluate_repository_artifact(
        repository,
        source,
        proposed,
        _artifact_contract(source_revision=source),
    )
    assert not facts.passed
    assert not facts.exact_path_only


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG E2E Test")
    _git(repository, "config", "user.email", "spg-e2e@example.invalid")
    (repository / "AI_context.md").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "AI_context.md")
    _git(repository, "commit", "-m", "baseline")
    return repository, _git(repository, "rev-parse", "HEAD")


def _artifact_contract(*, source_revision: str = "baseline") -> ArtifactContract:
    return ArtifactContract(
        engineering_resource_id=uuid4(),
        repository_identity="test://mvp-e2e",
        source_baseline_id=uuid4(),
        source_revision=source_revision,
        artifact_path=TARGET_PATH,
        operation=ArtifactOperation.CREATE,
        expected_outcome="Create the historical governed E2E document",
        verification_obligation="Verify the exact E2E Markdown artifact",
    )


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
