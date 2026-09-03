"""Focused contracts for container-native Codex state and stopped-Reality projection."""

from contextlib import nullcontext
from pathlib import Path
from uuid import uuid4

from spg.domain.preparation import ExecutorBinding
from spg.infrastructure.codex_executor_binding import (
    AUTH_READINESS_AVAILABLE,
    CODEX_STATE_RUNTIME_BINDING,
    preflight_codex_state_runtime,
)
from spg.infrastructure.executor_boundary import DedicatedExecutorRequest

from docker.start_app import prepare_optional_codex_state


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_state_01_02_03_12_compose_separates_default_and_e2e_state() -> None:
    base = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
    override = (PROJECT_ROOT / "compose.e2e.yaml").read_text(encoding="utf-8")

    assert "CODEX_HOME" not in base
    assert "target: runtime" in base
    assert "source: spg-e2e-codex-state" in override
    assert "target: /home/spg/.codex" in override
    assert "type: bind" not in override
    assert "SPG_CODEX_HOME_HOST" not in override
    assert "SPG_CODEX_AUTH_FILE_HOST" in override
    assert "SPG_CODEX_AUTH_SOURCE: /run/secrets/spg-codex-auth" in override


def test_state_04_auth_input_is_linked_without_content_copy_or_output(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    state_root = tmp_path / "native-state"
    auth_input = tmp_path / "auth-input"
    secret_marker = "credential-content-must-not-be-observed"
    auth_input.write_text(secret_marker, encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(state_root))
    monkeypatch.setenv("SPG_CODEX_AUTH_SOURCE", str(auth_input))
    links: list[tuple[Path, Path]] = []
    monkeypatch.setattr(
        Path,
        "symlink_to",
        lambda target, source: links.append((target, source)),
    )

    prepare_optional_codex_state()

    target = state_root / "auth.json"
    assert links == [(target, auth_input)]
    assert not target.exists()
    assert secret_marker not in capsys.readouterr().out


def test_state_05_06_no_turn_preflight_initializes_state_runtime(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "native-state"
    state_root.mkdir()
    (state_root / "auth.json").write_text("not-inspected", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = _request(workspace)
    runtime_calls = 0

    def runtime_factory(environment, selected_workspace):
        nonlocal runtime_calls
        runtime_calls += 1
        assert environment["CODEX_HOME"] == str(state_root)
        assert selected_workspace == workspace
        (state_root / "state_5.sqlite").touch()
        return nullcontext(object())

    response = preflight_codex_state_runtime(
        request,
        environment={"CODEX_HOME": str(state_root), "PATH": "/usr/bin"},
        sdk_version_resolver=lambda: "0.147.0",
        adapter_factory=_adapter_factory,
        state_runtime_factory=runtime_factory,
    )

    assert response.binding_identity == CODEX_STATE_RUNTIME_BINDING
    assert response.binding_status == "READY_FOR_THREAD_CREATION"
    assert response.authentication_readiness == AUTH_READINESS_AVAILABLE
    assert response.provider_turn_started is False
    assert response.metadata["codex_home_writable"] is True
    assert response.metadata["state_runtime_initialization"] == "APP_SERVER_INITIALIZED"
    assert response.metadata["sqlite_state_artifact_present"] is True
    assert response.metadata["provider_threads_started"] == 0
    assert response.metadata["provider_turns_started"] == 0
    assert runtime_calls == 1


def test_state_05_authentication_blocker_prevents_runtime_start(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "native-state"
    state_root.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runtime_calls = 0

    def forbidden_runtime_factory(_environment, _workspace):
        nonlocal runtime_calls
        runtime_calls += 1
        return nullcontext(object())

    response = preflight_codex_state_runtime(
        _request(workspace),
        environment={"CODEX_HOME": str(state_root), "PATH": "/usr/bin"},
        sdk_version_resolver=lambda: "0.147.0",
        adapter_factory=_adapter_factory,
        state_runtime_factory=forbidden_runtime_factory,
    )

    assert response.binding_status == "AUTHENTICATION_UNAVAILABLE"
    assert response.provider_turn_started is False
    assert runtime_calls == 0


def test_state_04_preflight_metadata_is_credential_free(tmp_path: Path) -> None:
    state_root = tmp_path / "native-state"
    state_root.mkdir()
    secret_marker = "credential-content-must-not-be-serialized"
    (state_root / "auth.json").write_text(secret_marker, encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    response = preflight_codex_state_runtime(
        _request(workspace),
        environment={"CODEX_HOME": str(state_root), "PATH": "/usr/bin"},
        sdk_version_resolver=lambda: "0.147.0",
        adapter_factory=_adapter_factory,
        state_runtime_factory=lambda _environment, _workspace: nullcontext(object()),
    )

    serialized = response.model_dump_json()
    assert secret_marker not in serialized
    assert str(state_root) not in serialized
    assert response.metadata["authentication_secret_inspected"] is False


class _Adapter:
    def preflight(self, _dispatch):
        return {
            "provider_turn_started": False,
            "preflight_only": True,
        }


def _adapter_factory(_materialized, *, workspace_validator):
    assert workspace_validator is not None
    return _Adapter()


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
            binding_ref="binding:codex-state-preflight",
            capability_identity="capability:executor",
            profile_identity="profile:local-docker-codex-e2e",
        ),
        materialized_execution_input_id=uuid4(),
        materialized_execution_input_fingerprint="materialized-input",
        workspace_identity=f"attempt-worktree:{attempt_id}",
        executor_workspace_path=workspace,
        repository_identity="fixture://repository",
        source_revision="fixture-source-revision",
        provider_input="No-Turn state preflight",
        request_fingerprint="fixture-request-fingerprint",
    )
