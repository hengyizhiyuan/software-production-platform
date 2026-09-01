"""Focused S6-C2-HR1 host portability and no-Turn preflight checks."""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
import subprocess
import tomllib
from uuid import uuid4

from spg.domain.execution import ProviderReportedOutcome
from spg.domain.preparation import ExecutorBinding
from spg.infrastructure.codex_executor_binding import (
    AUTH_READINESS_AVAILABLE,
    AUTH_READINESS_HUMAN_LOGIN_REQUIRED,
    AUTH_READINESS_REQUIRES_EXECUTION_TIME_PROOF,
    CODEX_BINDING,
    classify_codex_authentication_readiness,
    preflight_codex_binding,
)
from spg.infrastructure.executor_boundary import (
    DedicatedExecutorPreflightResponse,
    DedicatedExecutorRequest,
    SubprocessExecutorTransport,
    _fingerprint,
    build_executor_child_environment,
)


ROOT = Path(__file__).resolve().parents[1]
CODEX_PROFILE = "codex-executor"


def test_host_01_codex_dependency_profile_is_explicit() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert CODEX_PROFILE in project["project"]["optional-dependencies"]


def test_host_02_profile_locks_exact_codex_packages() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["optional-dependencies"][CODEX_PROFILE] == [
        "openai-codex==0.147.0",
        "openai-codex-cli-bin==0.147.0",
    ]
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    versions = {package["name"]: package["version"] for package in lock["package"]}
    assert versions["openai-codex"] == "0.147.0"
    assert versions["openai-codex-cli-bin"] == "0.147.0"


def test_host_03_codex_sdk_is_not_a_core_dependency() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert all(
        not dependency.startswith("openai-codex")
        for dependency in project["project"]["dependencies"]
    )


def test_host_04_explicit_codex_home_takes_precedence() -> None:
    environment = build_executor_child_environment(
        {
            "CODEX_HOME": r"D:\executor-state",
            "USERPROFILE": r"C:\native-user",
            "PATH": r"C:\Windows\System32",
        },
        platform_name="nt",
    )
    assert environment["CODEX_HOME"] == r"D:\executor-state"


def test_host_05_windows_userprofile_resolves_state_without_home() -> None:
    environment = build_executor_child_environment(
        {
            "USERPROFILE": r"C:\native-user",
            "PATH": r"C:\Windows\System32",
        },
        platform_name="nt",
    )
    assert environment["CODEX_HOME"] == r"C:\native-user\.codex"
    assert "HOME" not in environment


def test_host_06_posix_home_resolves_state() -> None:
    environment = build_executor_child_environment(
        {"HOME": "/home/executor", "PATH": "/usr/bin"},
        platform_name="posix",
    )
    assert environment["CODEX_HOME"] == "/home/executor/.codex"
    assert environment["HOME"] == "/home/executor"


def test_host_07_missing_state_roots_is_a_clear_preflight_blocker(
    tmp_path: Path,
) -> None:
    request = _boundary_request(tmp_path, source_revision="not-observed")
    environment = build_executor_child_environment(
        {"PATH": "/usr/bin"},
        platform_name="posix",
    )
    response = preflight_codex_binding(
        request,
        environment=environment,
        sdk_version_resolver=lambda: "0.147.0",
    )
    assert response.binding_status == "MISSING_RUNTIME_PREREQUISITE"
    assert response.metadata["missing_runtime_prerequisites"] == ["CODEX_HOME"]
    assert (
        response.authentication_readiness
        == AUTH_READINESS_HUMAN_LOGIN_REQUIRED
    )


def test_host_08_windows_home_compatibility_is_not_global_or_manufactured() -> None:
    source = {
        "USERPROFILE": r"C:\native-user",
        "PATH": r"C:\Windows\System32",
    }
    before = dict(source)
    environment = build_executor_child_environment(source, platform_name="nt")
    assert source == before
    assert "HOME" not in environment


def test_host_09_windows_filtering_is_case_insensitive() -> None:
    environment = build_executor_child_environment(
        {
            "userprofile": r"C:\native-user",
            "path": r"C:\Windows\System32",
            "systemroot": r"C:\Windows",
            "spg_database_url": "prohibited",
            "OpenAI_Api_Key": "prohibited",
        },
        platform_name="nt",
    )
    assert environment["USERPROFILE"] == r"C:\native-user"
    assert environment["PATH"] == r"C:\Windows\System32"
    assert environment["SYSTEMROOT"] == r"C:\Windows"
    assert not any(name.casefold() == "spg_database_url" for name in environment)
    assert not any(name.casefold() == "openai_api_key" for name in environment)


def test_host_10_database_configuration_never_reaches_child() -> None:
    environment = build_executor_child_environment(
        {
            "USERPROFILE": r"C:\native-user",
            "PATH": r"C:\Windows\System32",
            "SPG_DATABASE_URL": "postgresql://prohibited",
        },
        platform_name="nt",
    )
    assert "SPG_DATABASE_URL" not in environment


def test_host_11_unrelated_provider_credentials_never_reach_child() -> None:
    environment = build_executor_child_environment(
        {
            "USERPROFILE": r"C:\native-user",
            "PATH": r"C:\Windows\System32",
            "OPENAI_API_KEY": "prohibited",
            "ANTHROPIC_API_KEY": "prohibited",
            "CUSTOM_AUTH_TOKEN": "prohibited",
        },
        platform_name="nt",
    )
    serialized_names = {name.casefold() for name in environment}
    assert "openai_api_key" not in serialized_names
    assert "anthropic_api_key" not in serialized_names
    assert "custom_auth_token" not in serialized_names


def test_host_12_required_windows_runtime_variables_are_narrowly_retained() -> None:
    source = {
        "USERPROFILE": r"C:\native-user",
        "SYSTEMROOT": r"C:\Windows",
        "PATH": r"C:\Windows\System32",
        "PYTHONPATH": r"C:\project\src",
        "TEMP": r"C:\Temp",
        "TMP": r"C:\Temp",
        "APPDATA": r"C:\native-user\AppData\Roaming",
        "LOCALAPPDATA": r"C:\native-user\AppData\Local",
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "UNRELATED": "prohibited",
    }
    environment = build_executor_child_environment(source, platform_name="nt")
    assert set(environment) == {
        "USERPROFILE",
        "SYSTEMROOT",
        "PATH",
        "PYTHONPATH",
        "TEMP",
        "TMP",
        "APPDATA",
        "LOCALAPPDATA",
        "LANG",
        "LC_ALL",
        "CODEX_HOME",
        "PYTHONIOENCODING",
    }


def test_host_13_codex_sdk_binds_inside_dedicated_child(tmp_path: Path) -> None:
    request = _committed_boundary_request(tmp_path)
    response = _real_child_preflight(request)
    assert response.binding_status == "READY_FOR_REAL_PROBE_AUTH_UNPROVEN"
    assert response.adapter_identity == (
        "spg.providers.codex_sdk_executor.CodexSdkExecutor"
    )
    assert response.sdk_version == "0.147.0"
    assert response.binding_identity == CODEX_BINDING
    assert response.metadata["preflight_only"] is True


def test_host_14_preflight_creates_no_provider_thread_or_turn(
    tmp_path: Path,
) -> None:
    response = _real_child_preflight(_committed_boundary_request(tmp_path))
    assert response.provider_turn_started is False
    assert response.provider_outcome is ProviderReportedOutcome.UNKNOWN
    assert response.metadata["provider_turn_started"] is False
    assert response.metadata.get("thread_id") is None
    assert response.metadata.get("turn_id") is None


def test_host_15_transport_and_auth_classification_are_credential_free(
    tmp_path: Path,
) -> None:
    request = _boundary_request(tmp_path, source_revision="not-observed")
    serialized = request.model_dump_json()
    assert "CODEX_HOME" not in serialized
    assert "auth.json" not in serialized
    assert "API_KEY" not in serialized

    state_root = tmp_path / "state"
    state_root.mkdir()
    (state_root / "auth.json").write_text("not-inspected", encoding="utf-8")
    assert classify_codex_authentication_readiness(
        {"CODEX_HOME": str(state_root)}
    ) == AUTH_READINESS_AVAILABLE
    (state_root / "auth.json").unlink()
    assert classify_codex_authentication_readiness(
        {"CODEX_HOME": str(state_root)}
    ) == AUTH_READINESS_REQUIRES_EXECUTION_TIME_PROOF


def test_host_16_canonical_workspace_identity_survives_host_path_translation(
    tmp_path: Path,
) -> None:
    request = _committed_boundary_request(tmp_path)
    response = _real_child_preflight(request)
    assert response.workspace_identity == request.workspace_identity
    assert response.metadata["workspace_identity"] == request.workspace_identity


def test_host_17_posix_allowlist_behavior_remains_provider_neutral() -> None:
    environment = build_executor_child_environment(
        {
            "HOME": "/home/executor",
            "PATH": "/usr/bin",
            "TMPDIR": "/tmp",
            "LANG": "C.UTF-8",
            "USERPROFILE": "prohibited-on-posix",
            "SPG_DATABASE_URL": "prohibited",
        },
        platform_name="posix",
    )
    assert environment == {
        "HOME": "/home/executor",
        "PATH": "/usr/bin",
        "TMPDIR": "/tmp",
        "LANG": "C.UTF-8",
        "CODEX_HOME": "/home/executor/.codex",
        "PYTHONIOENCODING": "utf-8",
    }


def test_installed_codex_distributions_are_exact() -> None:
    assert version("openai-codex") == "0.147.0"
    assert version("openai-codex-cli-bin") == "0.147.0"


def _real_child_preflight(
    request: DedicatedExecutorRequest,
) -> DedicatedExecutorPreflightResponse:
    raw = SubprocessExecutorTransport(
        provider_binding=CODEX_BINDING,
        timeout_seconds=30.0,
    ).exchange(request)
    response = DedicatedExecutorPreflightResponse.model_validate_json(raw)
    assert response.metadata["spg_database_configuration_present"] is False
    assert response.metadata["authentication_secret_inspected"] is False
    assert response.authentication_readiness in {
        AUTH_READINESS_AVAILABLE,
        AUTH_READINESS_HUMAN_LOGIN_REQUIRED,
        AUTH_READINESS_REQUIRES_EXECUTION_TIME_PROOF,
    }
    return response


def _committed_boundary_request(tmp_path: Path) -> DedicatedExecutorRequest:
    repository = tmp_path / f"attempt-{uuid4()}"
    repository.mkdir()
    _git(repository, "init")
    _git(repository, "config", "user.name", "SPG Host Test")
    _git(repository, "config", "user.email", "spg-host-test@example.invalid")
    (repository / "README.md").write_text("host test\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "host preflight fixture")
    revision = _git(repository, "rev-parse", "HEAD").stdout.strip()
    return _boundary_request(repository, source_revision=revision)


def _boundary_request(
    workspace: Path,
    *,
    source_revision: str,
) -> DedicatedExecutorRequest:
    attempt_id = uuid4()
    basis = {
        "protocol": "spg-dedicated-executor-v1",
        "dispatch_id": str(uuid4()),
        "attempt_id": str(attempt_id),
        "generation": 1,
        "production_run_id": str(uuid4()),
        "work_unit_id": str(uuid4()),
        "plan_revision_id": str(uuid4()),
        "source_baseline_id": str(uuid4()),
        "context_package_id": str(uuid4()),
        "context_package_version": 1,
        "completion_contract_fingerprint": "completion-contract",
        "executor_binding": ExecutorBinding(
            binding_ref="binding:codex-host-preflight",
            capability_identity="capability:codex-executor",
            profile_identity="profile:codex-0.147.0",
        ).model_dump(mode="json"),
        "materialized_execution_input_id": str(uuid4()),
        "materialized_execution_input_fingerprint": "materialized-input",
        "workspace_identity": f"attempt-worktree:{attempt_id}",
        "executor_workspace_path": str(workspace),
        "repository_identity": "repository:host-preflight",
        "source_revision": source_revision,
        "provider_input": "No-Turn host preflight input.",
    }
    return DedicatedExecutorRequest(
        **basis,
        request_fingerprint=_fingerprint(basis),
    )


def _git(repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
        text=True,
    )
