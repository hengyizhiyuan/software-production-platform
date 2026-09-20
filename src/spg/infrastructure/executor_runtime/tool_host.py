"""Sandbox-facing native tool handlers with narrow environment inheritance."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import signal
import stat
from uuid import UUID

from spg.domain.native_execution import EffectCondition, ToolExecutionRequest, ToolExecutionResult
from spg.executor.tools import (
    PUBLIC_NATIVE_TOOL_CONTRACTS,
    NativeToolRegistry,
    ToolDefinition,
)
from spg.infrastructure.executor_runtime.workspace_host import PrivateWorkspaceHost
from spg.infrastructure.executor_runtime.landlock_sandbox import (
    LandlockProcessSandbox,
)


_SAFE_ENVIRONMENT = {
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "PATHEXT",
    "COMSPEC",
    "TEMP",
    "TMP",
    "LANG",
    "LC_ALL",
    "PYTHONUTF8",
    "PYTHONIOENCODING",
}
_SECRET_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "DATABASE_URL", "CREDENTIAL")
_MAX_MODEL_OUTPUT_BYTES = 32 * 1024


class NativeProcessSupervisor:
    """Own exact process objects so cancellation never targets a reused PID."""

    def __init__(self) -> None:
        self._active: dict[UUID, asyncio.subprocess.Process] = {}
        self._lock = asyncio.Lock()

    async def register(self, delivery_id: UUID, process: asyncio.subprocess.Process) -> None:
        async with self._lock:
            if delivery_id in self._active:
                raise ValueError(f"process delivery is already active: {delivery_id}")
            self._active[delivery_id] = process

    async def release(self, delivery_id: UUID, process: asyncio.subprocess.Process) -> None:
        async with self._lock:
            if self._active.get(delivery_id) is process:
                self._active.pop(delivery_id, None)

    async def terminate(self, delivery_id: UUID) -> dict[str, object]:
        async with self._lock:
            process = self._active.get(delivery_id)
        if process is None:
            return {
                "delivery_id": str(delivery_id),
                "found": False,
                "termination_proven": True,
            }
        await self._terminate_process_group(process)
        return {
            "delivery_id": str(delivery_id),
            "found": True,
            "pid": process.pid,
            "returncode": process.returncode,
            "termination_proven": process.returncode is not None,
        }

    @staticmethod
    async def _terminate_process_group(process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
            return
        except TimeoutError:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await process.wait()


class LocalNativeToolHost:
    """Execute approved filesystem/process tools inside one private workspace."""

    def __init__(
        self,
        workspace_root: Path,
        *,
        process_allowlist: tuple[str, ...] = (
            "python", "python3", "pytest", "node", "npm", "git", "uv"
        ),
        timeout_seconds: int = 120,
        process_supervisor: NativeProcessSupervisor | None = None,
        process_sandbox: LandlockProcessSandbox | None = None,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.path_policy = PrivateWorkspaceHost(self.workspace_root.parent)
        self.process_allowlist = process_allowlist
        self.timeout_seconds = timeout_seconds
        self.process_supervisor = process_supervisor or NativeProcessSupervisor()
        self.process_sandbox = process_sandbox

    def registry(self) -> NativeToolRegistry:
        handlers = {
            "file.read": self.read_file,
            "file.write": self.write_file,
            "process.run": self.run_process,
            "git.status": self.git_status,
            "git.diff": self.git_diff,
            "test.run": self.run_test,
            "build.run": self.run_build,
            "dependency.sync": self.sync_dependencies,
            "preview.inspect": self.inspect_preview,
        }
        return NativeToolRegistry(tuple(
            ToolDefinition(
                identity=str(contract["identity"]),
                version=str(contract["version"]),
                description=str(contract["description"]),
                input_schema=dict(contract["input_schema"]),
                effect_classification=str(contract["effect_classification"]),
                handler=handlers[str(contract["identity"])],
            )
            for contract in PUBLIC_NATIVE_TOOL_CONTRACTS
        ))

    async def read_file(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        relative = str(request.proposal.arguments["path"])
        try:
            content = await asyncio.to_thread(self._read_text, relative)
        except FileNotFoundError:
            return self._result(
                request.delivery_id,
                "file.read",
                {
                    "path": str(request.proposal.arguments["path"]),
                    "exists": False,
                    "content": None,
                    "bytes": 0,
                    "truncated": False,
                },
            )
        return self._result(
            request.delivery_id,
            "file.read",
            {
                "path": str(request.proposal.arguments["path"]),
                "exists": True,
                "content": self._bounded_text(content),
                "bytes": len(content.encode("utf-8")),
                "truncated": len(content.encode("utf-8")) > _MAX_MODEL_OUTPUT_BYTES,
            },
        )

    async def write_file(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        relative = str(request.proposal.arguments["path"])
        content = request.proposal.arguments.get("content")
        if not isinstance(content, str):
            raise ValueError("file.write content must be text")
        await asyncio.to_thread(
            self._atomic_write_text,
            relative,
            content,
            request.delivery_id,
        )
        return self._result(request.delivery_id, "file.write", {"path": str(request.proposal.arguments["path"]), "bytes": len(content.encode("utf-8"))})

    async def run_process(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        return await self._run_argv(request, "process.run")

    async def git_status(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        cwd = str(request.proposal.arguments["cwd"])
        return await self._run_argv(
            request,
            "git.status",
            argv=["git", "status", "--short", "--untracked-files=all"],
            cwd_value=cwd,
        )

    async def git_diff(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        cwd = str(request.proposal.arguments["cwd"])
        return await self._run_argv(
            request,
            "git.diff",
            argv=["git", "diff", "--no-ext-diff", "--binary"],
            cwd_value=cwd,
        )

    async def run_test(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        argv = self._argv(request)
        allowed = (
            argv[0] == "pytest"
            or argv[:2] == ["node", "--test"]
            or (
                argv[0] == "node"
                and len(argv) >= 2
                and not argv[1].startswith("-")
            )
            or argv[:3] in (["python", "-m", "pytest"], ["python3", "-m", "pytest"])
            or argv[:2] == ["npm", "test"]
            or argv[:3] == ["npm", "run", "test"]
        )
        if not allowed:
            raise ValueError("test.run accepts only pytest, node, or npm test recipes")
        return await self._run_argv(request, "test.run", argv=argv)

    async def run_build(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        argv = self._argv(request)
        if argv[:3] != ["npm", "run", "build"] and argv[:3] != ["python", "-m", "build"]:
            raise ValueError("build.run accepts only admitted npm or Python build recipes")
        return await self._run_argv(request, "build.run", argv=argv)

    async def sync_dependencies(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        argv = self._argv(request)
        allowed = argv[:3] == ["uv", "sync", "--locked"] or argv[:2] == ["npm", "ci"]
        if not allowed:
            raise ValueError("dependency.sync requires a locked uv sync or npm ci recipe")
        return await self._run_argv(request, "dependency.sync", argv=argv)

    async def inspect_preview(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        relative = str(request.proposal.arguments["path"])
        content = await asyncio.to_thread(self._read_text, relative)
        encoded = content.encode("utf-8")
        return self._result(
            request.delivery_id,
            "preview.inspect",
            {
                "path": relative,
                "bytes": len(encoded),
                "content_head": self._bounded_text(content),
                "truncated": len(encoded) > _MAX_MODEL_OUTPUT_BYTES,
            },
        )

    async def _run_argv(
        self,
        request: ToolExecutionRequest,
        identity: str,
        *,
        argv: list[str] | None = None,
        cwd_value: str | None = None,
    ) -> ToolExecutionResult:
        argv = argv or self._argv(request)
        executable = Path(argv[0]).name.lower()
        if executable not in {item.lower() for item in self.process_allowlist}:
            raise ValueError(f"process executable is not allowlisted: {executable}")
        for argument in argv[1:]:
            candidate = Path(argument)
            if argument in {"-c", "-e", "--eval"} and executable in {
                "python", "python3", "node"
            }:
                raise ValueError("inline code execution is not admitted by process.run")
            if candidate.is_absolute() or ".." in candidate.parts:
                raise ValueError("process arguments cannot escape the execution workspace")
        cwd_value = cwd_value or str(request.proposal.arguments.get("cwd", "."))
        cwd = self.workspace_root if cwd_value == "." else self.path_policy.resolve_path(self.workspace_root, str(cwd_value))
        environment = {
            key: value
            for key, value in os.environ.items()
            if key.upper() in _SAFE_ENVIRONMENT
            and not any(marker in key.upper() for marker in _SECRET_MARKERS)
        }
        environment["PYTHONPATH"] = str(self.workspace_root / "src")
        # Executor-owned validation commands must not create undeclared repository
        # artifacts as a side effect.  Python otherwise writes __pycache__ beside
        # admitted source files, which can turn a successful bounded production
        # attempt into a PATH_SCOPE failure after the attempt has finished.
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        launched_argv = argv
        scratch = None
        if self.process_sandbox is not None:
            launched_argv, scratch = self.process_sandbox.command(
                request.delivery_id, self.workspace_root, cwd, argv
            )
        process = await asyncio.create_subprocess_exec(
            *launched_argv,
            cwd=cwd,
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        await self.process_supervisor.register(request.delivery_id, process)
        stdout_task = asyncio.create_task(self._capture_stream(process.stdout))
        stderr_task = asyncio.create_task(self._capture_stream(process.stderr))
        timed_out = False
        try:
            try:
                await asyncio.wait_for(process.wait(), timeout=self.timeout_seconds)
            except TimeoutError:
                timed_out = True
                await self.process_supervisor.terminate(request.delivery_id)
            stdout, stdout_truncated = await stdout_task
            stderr, stderr_truncated = await stderr_task
        except asyncio.CancelledError:
            await asyncio.shield(self.process_supervisor.terminate(request.delivery_id))
            await asyncio.shield(asyncio.gather(stdout_task, stderr_task))
            raise
        finally:
            await self.process_supervisor.release(request.delivery_id, process)
            if scratch is not None:
                self.process_sandbox.cleanup(scratch)
        output = {
            "argv": argv,
            "cwd": str(cwd.relative_to(self.workspace_root)).replace("\\", "/") or ".",
            "process_identity": str(request.delivery_id),
            "pid": process.pid,
            "returncode": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "timed_out": timed_out,
            "process_group_terminated": timed_out,
            "isolation": (
                "landlock-per-delivery"
                if self.process_sandbox is not None
                else "in-process-test-only"
            ),
        }
        return self._result(
            request.delivery_id,
            identity,
            output,
            condition=EffectCondition.SETTLED if process.returncode == 0 else EffectCondition.FAILED,
        )

    @staticmethod
    async def _capture_stream(
        stream: asyncio.StreamReader | None,
    ) -> tuple[str, bool]:
        if stream is None:
            return "", False
        captured = bytearray()
        total = 0
        while True:
            chunk = await stream.read(16 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if len(captured) < _MAX_MODEL_OUTPUT_BYTES:
                captured.extend(chunk[: _MAX_MODEL_OUTPUT_BYTES - len(captured)])
        return captured.decode("utf-8", errors="replace"), total > _MAX_MODEL_OUTPUT_BYTES

    @staticmethod
    def _argv(request: ToolExecutionRequest) -> list[str]:
        argv = request.proposal.arguments.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
            raise ValueError("tool argv must be a non-empty string array")
        return argv

    def _content_path(self, relative: str) -> Path:
        path = self.path_policy.resolve_path(self.workspace_root, relative)
        if ".git" in Path(relative).parts:
            raise ValueError("direct access to Git metadata is prohibited")
        return path

    def _read_text(self, relative: str) -> str:
        with self._parent_directory(relative, create=False) as (parent_fd, name):
            descriptor = os.open(
                name,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=parent_fd,
            )
            try:
                metadata = os.fstat(descriptor)
                if not stat.S_ISREG(metadata.st_mode):
                    raise ValueError("native text reads require a regular file")
                if metadata.st_nlink != 1:
                    raise ValueError("hard-linked workspace files are prohibited")
                with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
                    descriptor = -1
                    return stream.read()
            finally:
                if descriptor >= 0:
                    os.close(descriptor)

    def _atomic_write_text(
        self,
        relative: str,
        content: str,
        delivery_id: UUID,
    ) -> None:
        with self._parent_directory(relative, create=True) as (parent_fd, name):
            try:
                existing = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                existing = None
            if existing is not None and (
                not stat.S_ISREG(existing.st_mode) or existing.st_nlink != 1
            ):
                raise ValueError("workspace write target must be one regular unlinked file")
            temporary = f".{name}.{delivery_id}.tmp"
            descriptor = os.open(
                temporary,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=parent_fd,
            )
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    descriptor = -1
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(
                    temporary,
                    name,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                )
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
                try:
                    os.unlink(temporary, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass

    @contextmanager
    def _parent_directory(self, relative: str, *, create: bool):
        if "\\" in relative:
            raise ValueError("workspace paths must use POSIX separators")
        parts = Path(relative).parts
        if not parts or Path(relative).is_absolute() or ".." in parts:
            raise ValueError("workspace path must be safe and relative")
        if ".git" in parts:
            raise ValueError("direct access to Git metadata is prohibited")
        descriptors: list[int] = []
        descriptor = os.open(
            self.workspace_root,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
        )
        descriptors.append(descriptor)
        try:
            for component in parts[:-1]:
                if create:
                    try:
                        os.mkdir(component, mode=0o700, dir_fd=descriptor)
                    except FileExistsError:
                        pass
                descriptor = os.open(
                    component,
                    os.O_RDONLY
                    | os.O_DIRECTORY
                    | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=descriptor,
                )
                descriptors.append(descriptor)
            yield descriptor, parts[-1]
        finally:
            for opened in reversed(descriptors):
                os.close(opened)

    @staticmethod
    def _bounded_text(value: str) -> str:
        encoded = value.encode("utf-8")
        if len(encoded) <= _MAX_MODEL_OUTPUT_BYTES:
            return value
        return encoded[:_MAX_MODEL_OUTPUT_BYTES].decode("utf-8", errors="ignore")

    @staticmethod
    def _result(
        delivery_id: UUID,
        identity: str,
        output: dict[str, object],
        *,
        condition: EffectCondition = EffectCondition.SETTLED,
    ) -> ToolExecutionResult:
        encoded = json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return ToolExecutionResult(
            delivery_id=delivery_id,
            tool_identity=identity,
            condition=condition,
            output=output,
            output_digest=sha256(encoded).hexdigest(),
            evidence=({"type": "TOOL_RECEIPT", "digest": sha256(encoded).hexdigest()},),
        )
