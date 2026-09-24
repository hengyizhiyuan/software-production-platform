from datetime import UTC, datetime
from pathlib import Path
import subprocess
from types import SimpleNamespace
from uuid import uuid4
import asyncio

import pytest

from spg.domain.production_environment import (
    CollectedEnvironmentOutput,
    EnvironmentCommand,
    EnvironmentCommandResult,
    EnvironmentConfiguration,
    EnvironmentLifecycleState,
    EnvironmentProviderError,
    EnvironmentProvisionRequest,
    EnvironmentRuntimeState,
    PreparedRepositoryMount,
    PreparedWorkspaceV1,
    ProductionEnvironmentV1,
    ProductionWorkspaceV1,
    RepositoryAcquisitionPolicyV1,
    RepositoryAssetBinding,
    RepositoryBranchSelection,
    RuntimeConfiguration,
)
from spg.infrastructure.production_environment import (
    ContainerProductionEnvironmentProvider,
    DockerCliContainerRuntime,
)
from spg.infrastructure.executor_runtime.production_environment_tool_host import (
    ProductionEnvironmentNativeToolHost,
)
from spg.domain.production_environment import (
    EnvironmentCommandObservation,
    ProviderEnvironmentHandle,
)


class FakeContainerRuntime:
    def __init__(self):
        self.created = []
        self.commands = []
        self.collected = []
        self.removed = []
        self.exit_code = 0

    def create(self, request):
        self.created.append(request)
        return f"container:{request.environment.id}"

    def execute(self, opaque_reference, command):
        self.commands.append((opaque_reference, command))
        return EnvironmentCommandResult(command=command, exit_code=self.exit_code)

    def collect(self, opaque_reference, path):
        self.collected.append((opaque_reference, path))
        return CollectedEnvironmentOutput(
            path=path,
            artifact_reference=f"artifact:{path}",
            content_digest="a" * 64,
            size_bytes=1,
        )

    def remove(self, opaque_reference):
        self.removed.append(opaque_reference)


def provision_request(tmp_path):
    now = datetime.now(UTC)
    work_id, workspace_id, environment_id = uuid4(), uuid4(), uuid4()
    workspace = ProductionWorkspaceV1(
        id=workspace_id,
        work_id=work_id,
        repository_assets=(
            RepositoryAssetBinding(
                asset_id=uuid4(),
                repository_identity="repo:frontend",
                source="file:///repo",
                branch="feature/environment",
                default_branch="main",
                requested_branch="feature/environment",
                source_revision="a" * 40,
                source_tree_identity="b" * 40,
                acquisition_policy=RepositoryAcquisitionPolicyV1(
                    branch_selection=RepositoryBranchSelection.HUMAN_REQUESTED,
                ),
                mount_path="/workspace/frontend",
                writable=True,
                provenance_reference="repository-reality:1",
            ),
        ),
        environment_configuration=EnvironmentConfiguration(
            provider_profile="container-v1"
        ),
        runtime_configuration=RuntimeConfiguration(runtime_profile="preview-v1"),
        created_at=now,
    )
    environment = ProductionEnvironmentV1(
        id=environment_id,
        work_id=work_id,
        workspace_id=workspace_id,
        lifecycle_state=EnvironmentLifecycleState.INITIALIZING,
        runtime_state=EnvironmentRuntimeState.PREPARING,
        created_at=now,
        updated_at=now,
    )
    repository_path = tmp_path / "workspace" / "frontend"
    repository_path.mkdir(parents=True)
    prepared = PreparedWorkspaceV1(
        workspace_id=workspace_id,
        root_path=repository_path.parent,
        repository_mounts=(
            PreparedRepositoryMount(
                repository_identity="repo:frontend",
                host_path=repository_path,
                container_path="/workspace/frontend",
                source_revision="a" * 40,
                writable=True,
            ),
        ),
        prepared_at=now,
    )
    return EnvironmentProvisionRequest(
        environment=environment,
        workspace=workspace,
        prepared_workspace=prepared,
        image_reference="registry.example/watt/python@sha256:" + "c" * 64,
    )


def test_container_provider_covers_prepare_execute_collect_and_cleanup(tmp_path):
    runtime = FakeContainerRuntime()
    provider = ContainerProductionEnvironmentProvider(runtime)
    request = provision_request(tmp_path)
    handle = provider.create_workspace_environment(request)
    install = EnvironmentCommand(
        argv=("python", "-m", "pip", "install", "-r", "requirements.txt"),
        working_directory="/workspace/frontend",
    )
    test = EnvironmentCommand(
        argv=("python", "-m", "pytest"),
        working_directory="/workspace/frontend",
    )

    assert provider.prepare_dependencies(handle, (install,))[0].exit_code == 0
    assert provider.execute_commands(handle, (test,))[0].command == test
    assert provider.collect_outputs(handle, ("/workspace/frontend/index.html",))[0].size_bytes == 1
    provider.cleanup(handle)

    assert len(runtime.created) == 1
    assert len(runtime.commands) == 2
    assert runtime.removed == [handle.opaque_reference]


def test_container_provider_rejects_failed_dependency_preparation(tmp_path):
    runtime = FakeContainerRuntime()
    runtime.exit_code = 2
    provider = ContainerProductionEnvironmentProvider(runtime)
    handle = provider.create_workspace_environment(provision_request(tmp_path))
    with pytest.raises(EnvironmentProviderError, match="dependency preparation failed"):
        provider.prepare_dependencies(
            handle,
            (
                EnvironmentCommand(
                    argv=("python", "-m", "pip", "check"),
                    working_directory="/workspace/frontend",
                ),
            ),
        )


@pytest.mark.real_container
def test_docker_runtime_uses_shared_compose_workspace_volume(tmp_path: Path):
    image = "watt-native-executor-runtime:local"
    if subprocess.run(
        ["docker", "image", "inspect", image],
        check=False,
        capture_output=True,
    ).returncode:
        pytest.skip(f"qualified local image is unavailable: {image}")
    volume = f"watt-native-workspace-test-{uuid4().hex}"
    subprocess.run(["docker", "volume", "create", volume], check=True, capture_output=True)
    try:
        seeded = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--user",
                "0",
                "--mount",
                f"type=volume,source={volume},target=/data",
                "--entrypoint",
                "sh",
                image,
                "-c",
                "mkdir -p /data/frontend && printf governed > /data/frontend/value.txt && chown -R 10001:10001 /data/frontend",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert seeded.returncode == 0, seeded.stderr
        request = provision_request(tmp_path).model_copy(
            update={"image_reference": image}
        )
        runtime = DockerCliContainerRuntime(
            workspace_volume=volume,
            workspace_volume_root=tmp_path / "workspace",
        )
        provider = ContainerProductionEnvironmentProvider(runtime)
        handle = provider.create_workspace_environment(request)
        try:
            observed = provider.execute_observed(
                handle,
                EnvironmentCommand(
                    argv=("python", "-c", "print(open('value.txt').read())"),
                    working_directory="/workspace/frontend",
                ),
            )
            assert observed.result.exit_code == 0
            assert observed.stdout.strip() == "governed"
        finally:
            provider.cleanup(handle)
    finally:
        subprocess.run(
            ["docker", "volume", "rm", "-f", volume],
            check=False,
            capture_output=True,
        )


def test_native_tool_command_binds_workspace_python_imports() -> None:
    commands = []

    class RecordingProvider:
        def execute_observed(self, _handle, command):
            commands.append(command)
            return EnvironmentCommandObservation(
                result=EnvironmentCommandResult(command=command, exit_code=0),
                stdout="passed",
                stderr="",
            )

    host = ProductionEnvironmentNativeToolHost(
        provider=RecordingProvider(),
        handle=ProviderEnvironmentHandle(
            provider_identity="test:production-environment",
            environment_id=uuid4(),
            opaque_reference="test-environment",
        ),
        environment_reference="production-environment:test",
        workspace_reference="production-workspace:test",
    )
    request = SimpleNamespace(
        delivery_id=uuid4(),
        proposal=SimpleNamespace(arguments={
            "cwd": ".",
            "argv": ["python", "-m", "pytest", "tests/test_mvp_ui_contracts.py", "-q"],
        }),
    )
    result = asyncio.run(host._run_argv(request, "test.run"))
    assert result.output["returncode"] == 0
    assert commands[0].working_directory == "/workspace/primary"
    assert commands[0].python_source_path == "/workspace/primary/src"


def test_docker_execution_passes_bounded_workspace_python_environment() -> None:
    class RecordingRuntime(DockerCliContainerRuntime):
        def __init__(self):
            super().__init__()
            self.arguments = None

        def _run(self, *arguments):
            self.arguments = arguments
            return subprocess.CompletedProcess(arguments, 0, "passed", "")

    runtime = RecordingRuntime()
    command = EnvironmentCommand(
        argv=("python", "-m", "pytest", "tests/test_mvp_ui_contracts.py", "-q"),
        working_directory="/workspace/primary",
        python_source_path="/workspace/primary/src",
    )
    observed = runtime.execute_observed("test-container", command)
    assert observed.result.exit_code == 0
    assert runtime.arguments == (
        "exec", "-w", "/workspace/primary",
        "-e", "PYTHONPATH=/workspace/primary/src",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "test-container", "python", "-m", "pytest",
        "tests/test_mvp_ui_contracts.py", "-q",
    )
    assert EnvironmentCommand(
        argv=("python", "-m", "pytest"),
        working_directory="/workspace/primary",
    ).python_source_path is None
