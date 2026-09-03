"""Focused MVP-E2E-1E sandbox and terminal-NONE contracts."""

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.domain.preparation import ExecutorBinding
from spg.domain.runtime import CompletionContract
from spg.infrastructure.codex_executor_binding import preflight_codex_binding
from spg.infrastructure.executor_boundary import (
    DedicatedExecutorRequest,
    SubprocessExecutorTransport,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_sandbox_01_02_03_profiles_are_explicit_and_do_not_relax_docker() -> None:
    base = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
    e2e = (PROJECT_ROOT / "compose.e2e.yaml").read_text(encoding="utf-8")

    assert "SPG_EXECUTOR_SANDBOX_MODE" not in base
    assert "SPG_EXECUTOR_SANDBOX_MODE: full-access" in e2e
    assert "privileged:" not in e2e
    assert "CAP_SYS_ADMIN" not in e2e
    assert "seccomp=unconfined" not in e2e
    assert "/var/run/docker.sock" not in e2e


def test_sandbox_02_locked_sdk_exposes_public_full_access_policy() -> None:
    openai_codex = pytest.importorskip("openai_codex")

    assert openai_codex.Sandbox.workspace_write.value == "workspace-write"
    assert openai_codex.Sandbox.full_access.value == "full-access"


def test_sandbox_02_04_05_07_full_access_is_accepted_without_a_turn(
    tmp_path: Path,
) -> None:
    openai_codex = pytest.importorskip("openai_codex")
    state_root = tmp_path / "state"
    state_root.mkdir()
    (state_root / "auth.json").touch()
    repository = tmp_path / "repository"
    workspace = tmp_path / "workspace"
    repository.mkdir()
    workspace.mkdir()
    selected = []

    class Adapter:
        def preflight(self, _dispatch):
            return {"provider_turn_started": False, "preflight_only": True}

    def adapter_factory(_materialized, *, workspace_validator, sandbox):
        assert workspace_validator is not None
        selected.append(sandbox)
        return Adapter()

    response = preflight_codex_binding(
        _request(workspace),
        environment={
            "CODEX_HOME": str(state_root),
            "PATH": "/usr/bin",
            "SPG_EXECUTOR_PROVIDER_SANDBOX_MODE": "full-access",
        },
        sdk_version_resolver=lambda: "0.147.0",
        adapter_factory=adapter_factory,
    )

    assert selected == [openai_codex.Sandbox.full_access]
    assert response.binding_status == "READY_FOR_REAL_PROBE_AUTH_UNPROVEN"
    assert response.provider_turn_started is False
    assert response.metadata["selected_sandbox_policy"] == "full-access"
    assert response.metadata["sandbox_policy_validation"] == (
        "PUBLIC_SDK_ENUM_ACCEPTED_NO_TURN"
    )
    marker = workspace / "writable"
    marker.write_text("ok\n", encoding="utf-8")
    marker.unlink()
    assert not marker.exists()
    assert workspace.resolve() != repository.resolve()


def test_sandbox_06_provider_policy_is_child_scoped_and_secret_free(
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured = {}

    def fake_run(*_args, **kwargs):
        captured.update(kwargs["env"])
        return SimpleNamespace(returncode=0, stdout=b"{}", stderr=b"")

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("SPG_DATABASE_URL", "prohibited")
    monkeypatch.setenv("OPENAI_API_KEY", "prohibited")
    monkeypatch.setattr("subprocess.run", fake_run)

    SubprocessExecutorTransport(
        provider_binding="codex-sdk-state-runtime-preflight",
        provider_sandbox_mode="full-access",
    ).exchange(_request(tmp_path))

    assert captured["SPG_EXECUTOR_PROVIDER_SANDBOX_MODE"] == "full-access"
    assert "SPG_DATABASE_URL" not in captured
    assert "OPENAI_API_KEY" not in captured


def test_sandbox_11_completion_contract_decides_if_none_is_acceptable() -> None:
    assert CompletionContract(
        required_outputs=("docs/result.md",)
    ).requires_observed_production_result
    assert CompletionContract(
        required_changes=("docs/result.md",)
    ).requires_observed_production_result
    assert not CompletionContract(
        forbidden_changes=("secrets",)
    ).requires_observed_production_result
    assert not CompletionContract(
        verification_obligations=("verify no-op",)
    ).requires_observed_production_result


def _request(workspace: Path) -> DedicatedExecutorRequest:
    attempt_id = uuid4()
    return DedicatedExecutorRequest.model_construct(
        dispatch_id=uuid4(),
        attempt_id=attempt_id,
        generation=1,
        production_run_id=uuid4(),
        work_unit_id=uuid4(),
        plan_revision_id=uuid4(),
        source_baseline_id=uuid4(),
        context_package_id=uuid4(),
        context_package_version=1,
        completion_contract_fingerprint="completion-contract",
        executor_binding=ExecutorBinding(
            binding_ref="binding:codex-sandbox-preflight",
            capability_identity="capability:executor",
            profile_identity="profile:local-docker-codex-e2e",
        ),
        materialized_execution_input_id=uuid4(),
        materialized_execution_input_fingerprint="materialized-input",
        workspace_identity=f"attempt-worktree:{attempt_id}",
        executor_workspace_path=workspace,
        repository_identity="fixture://repository",
        source_revision="fixture-source-revision",
        provider_input="No-Turn sandbox preflight",
        request_fingerprint="fixture-request-fingerprint",
    )
