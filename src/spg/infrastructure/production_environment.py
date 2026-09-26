"""Production Environment provider and Git continuity infrastructure adapters."""

from __future__ import annotations

from datetime import UTC, datetime
import base64
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from threading import RLock, Thread
from typing import Protocol
from urllib.parse import quote, urlsplit
from uuid import UUID

from spg.domain.assets import (
    RepositoryAcquisitionFailure,
    RepositoryAcquisitionFailureCategory,
)
from spg.domain.production_environment import (
    CollectedEnvironmentOutput,
    EnvironmentCommand,
    EnvironmentCommandObservation,
    EnvironmentCommandResult,
    EnvironmentProviderError,
    EnvironmentProvisionRequest,
    GitContinuityV1,
    PreparedRepositoryMount,
    PreparedWorkspaceV1,
    ProviderEnvironmentHandle,
    ProductionWorkspaceV1,
    safe_workspace_path,
)


class GitRepositoryAcquirer:
    """Production Environment-owned acquisition of one complete branch history."""

    def acquire(self, root: Path, source: str, destination: Path,
        *, credential: str | None = None) -> None:
        command = [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-C",
            str(root),
            "clone",
            "--no-local",
            "--single-branch",
            "--",
            source,
            str(destination),
        ]
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "GIT_TERMINAL_PROMPT": "0",
            "LANG": "C.UTF-8",
        }
        if credential is not None:
            if urlsplit(source).hostname != "github.com":
                raise RepositoryAcquisitionFailure(
                    RepositoryAcquisitionFailureCategory.AUTH_REQUIRED,
                    "GitHub credential cannot be used for another repository host.",
                    technical_evidence={"operation": "git clone", "credential_scope": "github.com"},
                    retryable=False,
                )
            basic = base64.b64encode(f"x-access-token:{credential}".encode()).decode()
            environment.update({"GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
                "GIT_CONFIG_VALUE_0": f"Authorization: Basic {basic}"})
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=90,
                env=environment,
            )
        except subprocess.TimeoutExpired as exc:
            raise RepositoryAcquisitionFailure(
                RepositoryAcquisitionFailureCategory.NETWORK_FAILURE,
                "The repository did not respond before the acquisition timeout. Retry when network access is available.",
                technical_evidence={
                    "operation": "git clone --single-branch",
                    "timeout_seconds": 90,
                    "stderr": self._bounded(exc.stderr),
                },
                retryable=True,
            ) from exc
        except OSError as exc:
            raise RepositoryAcquisitionFailure(
                RepositoryAcquisitionFailureCategory.FILESYSTEM_FAILURE,
                "The repository workspace could not be prepared on this runtime.",
                technical_evidence={
                    "operation": "git clone --single-branch",
                    "os_error": str(exc)[:4000],
                },
                retryable=True,
            ) from exc
        if result.returncode == 0:
            return
        raise self._failure(result)

    def fetch_selected_branch(self, repository: Path, branch: str) -> dict[str, object]:
        """Fetch one branch into an isolated PE Workspace without host credentials."""

        GitIsolatedWorkspacePreparer._validate_branch(branch)
        repository = repository.resolve()
        if not repository.is_dir():
            raise EnvironmentProviderError("Bound repository Workspace is unavailable")
        origin = subprocess.run(
            ("git", "-c", f"safe.directory={repository}", "-C", str(repository), "remote", "get-url", "origin"),
            capture_output=True, text=True, timeout=15,
        )
        if origin.returncode:
            raise EnvironmentProviderError("Workspace has no observed origin remote")
        source = origin.stdout.strip()
        parsed = urlsplit(source)
        if Path(source).is_absolute():
            pass
        elif parsed.scheme:
            if (
                parsed.scheme != "https" or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment
            ):
                raise EnvironmentProviderError("Git fetch requires a credential-free HTTPS origin")
        else:
            raise EnvironmentProviderError("Git fetch requires an exact local or HTTPS origin")
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "LANG": "C.UTF-8",
        }
        command = (
            "git", "-c", f"safe.directory={repository}",
            "-c", "credential.helper=", "-c", "core.hooksPath=/dev/null",
            "-C", str(repository), "fetch", "--no-tags",
            "--no-recurse-submodules", "origin", branch,
        )
        try:
            result = subprocess.run(
                command, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=90, env=environment,
            )
        except subprocess.TimeoutExpired as error:
            return {"returncode": 124, "stdout": "", "stderr": "Repository fetch timed out.", "fetched_revision": None}
        fetched_revision = None
        if result.returncode == 0:
            fetched_revision = GitContinuityInspector._git(repository, "rev-parse", "FETCH_HEAD^{commit}")
        return {
            "returncode": result.returncode,
            "stdout": self._bounded(result.stdout),
            "stderr": self._bounded(result.stderr),
            "fetched_revision": fetched_revision,
        }

    def create_work_branch(
        self,
        root: Path,
        base_repository: Path,
        base_branch: str,
        source: str,
        destination: Path,
        target_branch: str,
    ) -> None:
        """Create an isolated local branch from an acquired exact baseline."""

        try:
            GitIsolatedWorkspacePreparer._validate_branch(target_branch)
        except EnvironmentProviderError as exc:
            raise RepositoryAcquisitionFailure(
                RepositoryAcquisitionFailureCategory.INVALID_BRANCH,
                "The requested local branch name is invalid.",
                technical_evidence={"operation": "git check-ref-format --branch"},
                retryable=False,
            ) from exc
        if not base_repository.resolve().is_dir():
            raise EnvironmentProviderError("Bound repository baseline is unavailable")
        base_revision = GitContinuityInspector._git(
            base_repository, "rev-parse", "HEAD^{commit}"
        )
        GitContinuityInspector._git(
            root,
            "clone", "--no-local", "--single-branch", "--branch", base_branch,
            "--", str(base_repository), str(destination),
        )
        observed = GitContinuityInspector._git(
            destination, "rev-parse", "HEAD^{commit}"
        )
        if observed != base_revision:
            raise EnvironmentProviderError("Branch base differs from bound repository revision")
        GitContinuityInspector._git(destination, "switch", "-c", target_branch)
        GitContinuityInspector._git(destination, "remote", "set-url", "origin", source)
        if GitContinuityInspector._git(destination, "rev-parse", "HEAD^{commit}") != base_revision:
            raise EnvironmentProviderError("Branch creation changed the baseline commit")

    @staticmethod
    def _bounded(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        return value.strip()[:4000]

    def _failure(
        self, result: subprocess.CompletedProcess[str]
    ) -> RepositoryAcquisitionFailure:
        stderr = self._bounded(result.stderr)
        lowered = stderr.casefold()
        category = RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE
        message = "Repository acquisition failed and can be retried."
        retryable = True
        if any(
            marker in lowered
            for marker in (
                "authentication failed",
                "could not read username",
                "terminal prompts disabled",
                "permission denied (publickey)",
                "http basic: access denied",
            )
        ):
            category = RepositoryAcquisitionFailureCategory.AUTH_REQUIRED
            message = "Repository read authorization is required before Watt can acquire this repository."
        elif any(
            marker in lowered
            for marker in (
                "remote branch",
                "couldn't find remote ref",
                "invalid branch name",
            )
        ):
            category = RepositoryAcquisitionFailureCategory.INVALID_BRANCH
            message = "The selected repository branch does not exist or is invalid."
            retryable = False
        elif any(
            marker in lowered
            for marker in (
                "repository not found",
                "does not appear to be a git repository",
                "not found",
            )
        ):
            category = RepositoryAcquisitionFailureCategory.REPOSITORY_NOT_FOUND
            message = "The repository could not be found at the supplied address."
            retryable = False
        elif any(
            marker in lowered
            for marker in (
                "could not resolve host",
                "failed to connect",
                "connection timed out",
                "network is unreachable",
                "connection reset",
            )
        ):
            category = RepositoryAcquisitionFailureCategory.NETWORK_FAILURE
            message = "Network access to the repository failed. Retry when connectivity is restored."
        elif any(
            marker in lowered
            for marker in (
                "permission denied",
                "no space left on device",
                "read-only file system",
                "cannot create directory",
            )
        ):
            category = RepositoryAcquisitionFailureCategory.FILESYSTEM_FAILURE
            message = "The repository workspace could not be written on this runtime."
        elif result.returncode in {128, 129} and not stderr:
            category = RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_TERMINAL
            message = "Repository acquisition failed without a recoverable response."
            retryable = False
        return RepositoryAcquisitionFailure(
            category,
            message,
            technical_evidence={
                "operation": "git clone --single-branch",
                "returncode": result.returncode,
                "stderr": stderr,
            },
            retryable=retryable,
        )


class ContainerRuntimePort(Protocol):
    """Narrow port implemented by Docker or another qualified container runtime."""

    def create(self, request: EnvironmentProvisionRequest) -> str: ...

    def execute(
        self,
        opaque_reference: str,
        command: EnvironmentCommand,
    ) -> EnvironmentCommandResult: ...

    def execute_observed(
        self,
        opaque_reference: str,
        command: EnvironmentCommand,
    ) -> EnvironmentCommandObservation: ...

    def collect(
        self,
        opaque_reference: str,
        path: str,
    ) -> CollectedEnvironmentOutput: ...

    def remove(self, opaque_reference: str) -> None: ...


class ContainerProductionEnvironmentProvider:
    """Initial provider over a container runtime port, without Docker coupling."""

    provider_identity = "container-v1"

    def __init__(self, runtime: ContainerRuntimePort) -> None:
        self.runtime = runtime

    def create_workspace_environment(
        self,
        request: EnvironmentProvisionRequest,
    ) -> ProviderEnvironmentHandle:
        try:
            opaque_reference = self.runtime.create(request)
        except Exception as exc:
            raise EnvironmentProviderError("container environment creation failed") from exc
        if not opaque_reference:
            raise EnvironmentProviderError("container runtime returned no environment identity")
        return ProviderEnvironmentHandle(
            provider_identity=self.provider_identity,
            environment_id=request.environment.id,
            opaque_reference=opaque_reference,
        )

    def prepare_dependencies(
        self,
        handle: ProviderEnvironmentHandle,
        commands: tuple[EnvironmentCommand, ...],
    ) -> tuple[EnvironmentCommandResult, ...]:
        results = self._execute(handle, commands)
        if any(result.exit_code != 0 for result in results):
            raise EnvironmentProviderError("dependency preparation failed")
        return results

    def execute_commands(
        self,
        handle: ProviderEnvironmentHandle,
        commands: tuple[EnvironmentCommand, ...],
    ) -> tuple[EnvironmentCommandResult, ...]:
        return self._execute(handle, commands)

    def execute_observed(
        self,
        handle: ProviderEnvironmentHandle,
        command: EnvironmentCommand,
    ) -> EnvironmentCommandObservation:
        self._validate_handle(handle)
        try:
            return self.runtime.execute_observed(handle.opaque_reference, command)
        except Exception as exc:
            raise EnvironmentProviderError("container command observation failed") from exc

    def collect_outputs(
        self,
        handle: ProviderEnvironmentHandle,
        paths: tuple[str, ...],
    ) -> tuple[CollectedEnvironmentOutput, ...]:
        self._validate_handle(handle)
        normalized = tuple(safe_workspace_path(path) for path in paths)
        if len(set(normalized)) != len(normalized):
            raise EnvironmentProviderError("output paths must be unique")
        try:
            return tuple(
                self.runtime.collect(handle.opaque_reference, path) for path in normalized
            )
        except Exception as exc:
            raise EnvironmentProviderError("container output collection failed") from exc

    def cleanup(self, handle: ProviderEnvironmentHandle) -> None:
        self._validate_handle(handle)
        try:
            self.runtime.remove(handle.opaque_reference)
        except Exception as exc:
            raise EnvironmentProviderError("container cleanup failed") from exc

    def _execute(
        self,
        handle: ProviderEnvironmentHandle,
        commands: tuple[EnvironmentCommand, ...],
    ) -> tuple[EnvironmentCommandResult, ...]:
        self._validate_handle(handle)
        try:
            return tuple(
                self.runtime.execute(handle.opaque_reference, command)
                for command in commands
            )
        except Exception as exc:
            raise EnvironmentProviderError("container command execution failed") from exc

    def _validate_handle(self, handle: ProviderEnvironmentHandle) -> None:
        if handle.provider_identity != self.provider_identity:
            raise EnvironmentProviderError("environment handle belongs to another provider")


class GitContinuityInspector:
    """Read-only Git continuity observation for one exact ancestor path."""

    def inspect(
        self,
        repository_path: Path,
        *,
        repository_identity: str,
        base_revision: str,
        observed_at: datetime | None = None,
    ) -> GitContinuityV1:
        repository = repository_path.resolve()
        top_level = Path(self._git(repository, "rev-parse", "--show-toplevel")).resolve()
        if top_level != repository:
            raise EnvironmentProviderError("repository_path must be the Git repository root")
        base_commit = self._git(repository, "rev-parse", f"{base_revision}^{{commit}}")
        current_commit = self._git(repository, "rev-parse", "HEAD^{commit}")
        current_tree_identity = self._git(repository, "rev-parse", "HEAD^{tree}")
        if self._run(repository, "merge-base", "--is-ancestor", base_commit, current_commit).returncode:
            raise EnvironmentProviderError("base revision is not an ancestor of current HEAD")
        branch_result = self._run(repository, "symbolic-ref", "--short", "-q", "HEAD")
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "DETACHED"
        descendants = self._git(
            repository,
            "rev-list",
            "--reverse",
            f"{base_commit}..{current_commit}",
        ).splitlines()
        ancestry = (base_commit, *descendants)
        if current_commit == base_commit:
            ancestry = (base_commit,)
        return GitContinuityV1(
            repository_identity=repository_identity,
            source=repository.as_uri(),
            branch=branch,
            base_commit=base_commit,
            current_commit=current_commit,
            current_tree_identity=current_tree_identity,
            ancestry=ancestry,
            diff_reference=f"{base_commit}..{current_commit}",
            observed_at=observed_at or datetime.now(UTC),
        )

    @classmethod
    def _git(cls, repository: Path, *arguments: str) -> str:
        result = cls._run(repository, *arguments)
        if result.returncode:
            raise EnvironmentProviderError(
                result.stderr.strip() or f"Git command failed: {' '.join(arguments)}"
            )
        return result.stdout.strip()

    @staticmethod
    def _run(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={
                "PATH": os.environ.get("PATH", ""),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                "GIT_TERMINAL_PROMPT": "0",
                "LANG": "C.UTF-8",
            },
        )


class GitIsolatedWorkspacePreparer:
    """Clone exact repository revisions into one Work-centric Workspace root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def prepare(self, workspace: ProductionWorkspaceV1) -> PreparedWorkspaceV1:
        target = (self.root / str(workspace.id)).resolve()
        if target.parent != self.root:
            raise EnvironmentProviderError("Workspace identity escapes configured root")
        if target.exists():
            raise EnvironmentProviderError("Workspace identity already exists")
        temporary = Path(tempfile.mkdtemp(prefix=f".{workspace.id}.", dir=self.root))
        try:
            prepared = []
            for asset in workspace.repository_assets:
                if asset.branch is None:
                    raise EnvironmentProviderError(
                        "Repository Reality has no selected branch"
                    )
                self._validate_branch(asset.branch)
                relative = Path(*Path(asset.mount_path.removeprefix("/workspace/")).parts)
                destination = (temporary / relative).resolve()
                if temporary not in destination.parents:
                    raise EnvironmentProviderError("repository mount escapes Workspace root")
                destination.parent.mkdir(parents=True, exist_ok=True)
                self._git(
                    temporary,
                    "clone",
                    "--single-branch",
                    "--branch",
                    asset.branch,
                    "--no-checkout",
                    "--no-hardlinks",
                    asset.source,
                    str(destination),
                )
                # A verified PWU output may be a detached, unreferenced commit
                # in the source object database. The selected branch clone does
                # not necessarily include it; fetch that exact object only.
                probe = subprocess.run(
                    ["git", "-C", str(destination), "cat-file", "-e",
                     f"{asset.source_revision}^{{commit}}"],
                    check=False, capture_output=True,
                )
                if probe.returncode != 0:
                    self._git(
                        destination, "fetch", "--no-tags", "--no-write-fetch-head",
                        asset.source, asset.source_revision,
                    )
                self._git(destination, "checkout", "--detach", asset.source_revision)
                revision = self._git(destination, "rev-parse", "HEAD^{commit}")
                tree = self._git(destination, "rev-parse", "HEAD^{tree}")
                if revision != asset.source_revision or tree != asset.source_tree_identity:
                    raise EnvironmentProviderError(
                        "prepared repository differs from admitted Repository Reality"
                    )
                if self._git(destination, "rev-parse", "--is-shallow-repository") != "false":
                    raise EnvironmentProviderError(
                        "Repository acquisition did not preserve full history"
                    )
                remote_branches = {
                    item
                    for item in self._git(
                        destination,
                        "for-each-ref",
                        "--format=%(refname:short)",
                        "refs/remotes/origin",
                    ).splitlines()
                    if item and item != "origin/HEAD"
                }
                if remote_branches != {f"origin/{asset.branch}"}:
                    raise EnvironmentProviderError(
                        "Repository acquisition fetched branches outside selected Reality"
                    )
                prepared.append(
                    (asset, relative)
                )
            os.replace(temporary, target)
            mounts = tuple(
                PreparedRepositoryMount(
                    repository_identity=asset.repository_identity,
                    host_path=target / relative,
                    container_path=asset.mount_path,
                    source_revision=asset.source_revision,
                    writable=asset.writable,
                )
                for asset, relative in prepared
            )
            return PreparedWorkspaceV1(
                workspace_id=workspace.id,
                root_path=target,
                repository_mounts=mounts,
                prepared_at=datetime.now(UTC),
            )
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise

    def cleanup(self, prepared: PreparedWorkspaceV1) -> None:
        path = prepared.root_path.resolve()
        if path.parent != self.root:
            raise EnvironmentProviderError("refusing to clean outside configured Workspace root")
        shutil.rmtree(path, ignore_errors=False)

    @classmethod
    def _git(cls, repository: Path, *arguments: str) -> str:
        result = GitContinuityInspector._run(repository, *arguments)
        if result.returncode:
            raise EnvironmentProviderError(result.stderr.strip() or "Git Workspace preparation failed")
        return result.stdout.strip()

    @staticmethod
    def _validate_branch(branch: str) -> None:
        result = subprocess.run(
            ["git", "check-ref-format", "--branch", branch],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode:
            raise EnvironmentProviderError("selected repository branch is invalid")


class DockerCliContainerRuntime:
    """Real single-host Docker implementation of the container runtime port."""

    def __init__(
        self,
        docker_binary: str = "docker",
        *,
        workspace_volume: str | None = None,
        workspace_volume_root: Path | None = None,
    ) -> None:
        if workspace_volume is not None and not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]+", workspace_volume
        ):
            raise ValueError("Docker Workspace volume name is invalid")
        if workspace_volume is not None and workspace_volume_root is None:
            raise ValueError("Docker Workspace volume requires its mounted root")
        self.docker_binary = docker_binary
        self.workspace_volume = workspace_volume
        self.workspace_volume_root = (
            None if workspace_volume_root is None else workspace_volume_root.resolve()
        )
        self._mounts: dict[str, tuple[PreparedRepositoryMount, ...]] = {}
        self._lock = RLock()

    def create(self, request: EnvironmentProvisionRequest) -> str:
        name = f"watt-pe-{request.environment.id}"
        arguments = [
            "create",
            "--name",
            name,
            "--label",
            f"watt.production-environment={request.environment.id}",
            "--network",
            "none",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,nosuid,size=64m",
        ]
        entrypoint = "while :; do sleep 3600; done"
        if self.workspace_volume is None:
            for mount in request.prepared_workspace.repository_mounts:
                value = f"type=bind,source={mount.host_path.resolve()},target={mount.container_path}"
                if not mount.writable:
                    value += ",readonly"
                arguments.extend(("--mount", value))
        else:
            arguments.extend(
                (
                    "--mount",
                    f"type=volume,source={self.workspace_volume},target=/watt-workspaces",
                    "--tmpfs",
                    "/workspace:rw,exec,nosuid,size=8m,mode=1777",
                )
            )
            links = []
            assert self.workspace_volume_root is not None
            for mount in request.prepared_workspace.repository_mounts:
                if not mount.writable:
                    raise EnvironmentProviderError(
                        "shared-volume Production Environment requires writable Native mounts"
                    )
                host_path = mount.host_path.resolve()
                if self.workspace_volume_root not in host_path.parents:
                    raise EnvironmentProviderError(
                        "prepared Native mount is outside the configured Workspace volume"
                    )
                relative = host_path.relative_to(self.workspace_volume_root).as_posix()
                target = mount.container_path
                parent = str(Path(target).parent).replace("\\", "/")
                links.append(
                    f"mkdir -p {shlex.quote(parent)} && "
                    f"ln -s {shlex.quote('/watt-workspaces/' + relative)} "
                    f"{shlex.quote(target)}"
                )
            entrypoint = " && ".join((*links, "while :; do sleep 3600; done"))
        arguments.extend(
            (
                "--entrypoint",
                "sh",
                request.image_reference,
                "-c",
                entrypoint,
            )
        )
        container_id = self._docker(*arguments)
        try:
            self._docker("start", container_id)
        except Exception:
            self._run("rm", "-f", container_id)
            raise
        with self._lock:
            self._mounts[container_id] = request.prepared_workspace.repository_mounts
        return container_id

    def execute(
        self,
        opaque_reference: str,
        command: EnvironmentCommand,
    ) -> EnvironmentCommandResult:
        result = self._run(
            "exec",
            "-w",
            command.working_directory,
            *self._python_environment_arguments(command),
            opaque_reference,
            *command.argv,
        )
        stdout_digest = sha256(result.stdout.encode("utf-8")).hexdigest()
        stderr_digest = sha256(result.stderr.encode("utf-8")).hexdigest()
        return EnvironmentCommandResult(
            command=command,
            exit_code=result.returncode,
            stdout_reference=f"sha256:{stdout_digest}",
            stderr_reference=f"sha256:{stderr_digest}",
        )

    def execute_observed(
        self,
        opaque_reference: str,
        command: EnvironmentCommand,
    ) -> EnvironmentCommandObservation:
        result = self._run(
            "exec",
            "-w",
            command.working_directory,
            *self._python_environment_arguments(command),
            opaque_reference,
            *command.argv,
        )
        stdout = result.stdout.encode("utf-8")
        stderr = result.stderr.encode("utf-8")
        limit = 32 * 1024
        command_result = EnvironmentCommandResult(
            command=command,
            exit_code=result.returncode,
            stdout_reference=f"sha256:{sha256(stdout).hexdigest()}",
            stderr_reference=f"sha256:{sha256(stderr).hexdigest()}",
        )
        return EnvironmentCommandObservation(
            result=command_result,
            stdout=stdout[:limit].decode("utf-8", errors="replace"),
            stderr=stderr[:limit].decode("utf-8", errors="replace"),
            stdout_truncated=len(stdout) > limit,
            stderr_truncated=len(stderr) > limit,
        )

    @staticmethod
    def _python_environment_arguments(command: EnvironmentCommand) -> tuple[str, ...]:
        if command.python_source_path is None:
            return ()
        return (
            "-e",
            f"PYTHONPATH={command.python_source_path}",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
        )

    def collect(
        self,
        opaque_reference: str,
        path: str,
    ) -> CollectedEnvironmentOutput:
        normalized = safe_workspace_path(path)
        with self._lock:
            mounts = self._mounts.get(opaque_reference)
        if mounts is None:
            raise EnvironmentProviderError("container Workspace mount map is unavailable")
        selected = next(
            (
                mount
                for mount in mounts
                if normalized == mount.container_path
                or normalized.startswith(mount.container_path.rstrip("/") + "/")
            ),
            None,
        )
        if selected is None:
            raise EnvironmentProviderError("output path is outside admitted repository mounts")
        relative = normalized.removeprefix(selected.container_path).removeprefix("/")
        output = (selected.host_path / Path(*relative.split("/"))).resolve()
        root = selected.host_path.resolve()
        if output != root and root not in output.parents:
            raise EnvironmentProviderError("output path escapes repository mount")
        if not output.is_file():
            raise EnvironmentProviderError("requested output is not a regular file")
        content = output.read_bytes()
        digest = sha256(content).hexdigest()
        return CollectedEnvironmentOutput(
            path=normalized,
            artifact_reference=f"artifact:sha256:{digest}",
            content_digest=digest,
            size_bytes=len(content),
        )

    def remove(self, opaque_reference: str) -> None:
        result = self._run("rm", "-f", opaque_reference)
        if result.returncode:
            raise EnvironmentProviderError(result.stderr.strip() or "Docker cleanup failed")
        with self._lock:
            self._mounts.pop(opaque_reference, None)

    def _docker(self, *arguments: str) -> str:
        result = self._run(*arguments)
        if result.returncode:
            raise EnvironmentProviderError(result.stderr.strip() or "Docker command failed")
        return result.stdout.strip()

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        }
        docker_host = os.environ.get("DOCKER_HOST")
        if docker_host:
            environment["DOCKER_HOST"] = docker_host
        return subprocess.run(
            [self.docker_binary, *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
        )


class StaticPreviewRuntime:
    """Bounded Human-review HTTP runtime over one prepared static artifact."""

    def __init__(self, bind_host: str = "127.0.0.1") -> None:
        self.bind_host = bind_host
        self._servers: dict[UUID, tuple[ThreadingHTTPServer, Thread]] = {}
        self._lock = RLock()

    def start(self, runtime_id: UUID, root: Path, entrypoint: str) -> dict:
        entry = Path(entrypoint)
        if entry.is_absolute() or ".." in entry.parts or entrypoint in {"", "."}:
            raise EnvironmentProviderError("Preview entrypoint must be safe and relative")
        preview_root = root.resolve()
        subject = (preview_root / entry).resolve()
        if preview_root not in subject.parents or not subject.is_file():
            raise EnvironmentProviderError("Preview entrypoint is unavailable")

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(preview_root), **kwargs)

            def end_headers(self):
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'",
                )
                super().end_headers()

            def log_message(self, *_args):
                pass

        with self._lock:
            if runtime_id in self._servers:
                raise EnvironmentProviderError("Preview Runtime identity is already active")
            server = ThreadingHTTPServer((self.bind_host, 0), Handler)
            thread = Thread(target=server.serve_forever, daemon=True, name=f"preview-{runtime_id}")
            thread.start()
            self._servers[runtime_id] = (server, thread)
        encoded_entrypoint = quote(entrypoint.replace("\\", "/"))
        return {
            "status": "READY",
            "url": f"http://{self.bind_host}:{server.server_port}/{encoded_entrypoint}",
            "runtime_id": str(runtime_id),
            "entrypoint_sha256": sha256(subject.read_bytes()).hexdigest(),
        }

    def stop(self, runtime_id: UUID) -> None:
        with self._lock:
            active = self._servers.pop(runtime_id, None)
        if active is None:
            return
        server, thread = active
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


class GitDeliveryPreparer:
    """Create one authorized local branch and commit; never push or merge."""

    def prepare_candidate(
        self,
        repository_path: Path,
        *,
        repository_identity: str,
        base_revision: str,
        commit_message: str,
        author_name: str,
        author_email: str,
    ) -> GitContinuityV1:
        repository = repository_path.resolve()
        status = GitContinuityInspector._git(repository, "status", "--porcelain")
        if not status:
            raise EnvironmentProviderError("Delivery commit requires observed repository changes")
        GitContinuityInspector._git(repository, "add", "-A")
        GitContinuityInspector._git(
            repository,
            "-c",
            f"user.name={author_name}",
            "-c",
            f"user.email={author_email}",
            "commit",
            "-m",
            commit_message,
        )
        return GitContinuityInspector().inspect(
            repository,
            repository_identity=repository_identity,
            base_revision=base_revision,
        )

    def authorize_branch(
        self,
        repository_path: Path,
        *,
        repository_identity: str,
        base_revision: str,
        candidate_revision: str,
        target_branch: str,
    ) -> GitContinuityV1:
        repository = repository_path.resolve()
        head = GitContinuityInspector._git(repository, "rev-parse", "HEAD^{commit}")
        if head != candidate_revision:
            raise EnvironmentProviderError("Workspace HEAD differs from reviewed Candidate")
        branch_exists = self._run(
            repository,
            "show-ref",
            "--verify",
            "--quiet",
            f"refs/heads/{target_branch}",
        )
        if branch_exists.returncode == 0:
            existing = GitContinuityInspector._git(
                repository,
                "rev-parse",
                f"refs/heads/{target_branch}^{{commit}}",
            )
            if existing != candidate_revision:
                raise EnvironmentProviderError("target delivery branch already exists")
            current = GitContinuityInspector._git(repository, "branch", "--show-current")
            if current != target_branch:
                GitContinuityInspector._git(repository, "switch", target_branch)
        else:
            GitContinuityInspector._git(repository, "switch", "-c", target_branch)
        return GitContinuityInspector().inspect(
            repository,
            repository_identity=repository_identity,
            base_revision=base_revision,
        )

    @staticmethod
    def _run(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return GitContinuityInspector._run(repository, *arguments)
