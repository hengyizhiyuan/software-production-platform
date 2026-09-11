"""Sandbox-facing native tool handlers with narrow environment inheritance."""

from __future__ import annotations

import asyncio
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from uuid import UUID

from spg.domain.native_execution import EffectCondition, ToolExecutionRequest, ToolExecutionResult
from spg.executor.tools import (
    PUBLIC_NATIVE_TOOL_CONTRACTS,
    NativeToolRegistry,
    ToolDefinition,
)
from spg.infrastructure.executor_runtime.workspace_host import PrivateWorkspaceHost


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
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.path_policy = PrivateWorkspaceHost(self.workspace_root.parent)
        self.process_allowlist = process_allowlist
        self.timeout_seconds = timeout_seconds

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
        path = self._content_path(str(request.proposal.arguments["path"]))
        content = await asyncio.to_thread(path.read_text, encoding="utf-8")
        return self._result(
            request.delivery_id,
            "file.read",
            {
                "path": str(request.proposal.arguments["path"]),
                "content": self._bounded_text(content),
                "bytes": len(content.encode("utf-8")),
                "truncated": len(content.encode("utf-8")) > _MAX_MODEL_OUTPUT_BYTES,
            },
        )

    async def write_file(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        path = self._content_path(str(request.proposal.arguments["path"]))
        content = request.proposal.arguments.get("content")
        if not isinstance(content, str):
            raise ValueError("file.write content must be text")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{request.delivery_id}.tmp")
        await asyncio.to_thread(temporary.write_text, content, encoding="utf-8")
        os.replace(temporary, path)
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
            or argv[:3] == ["python", "-m", "pytest"]
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
        path = self._content_path(relative)
        content = await asyncio.to_thread(path.read_text, encoding="utf-8")
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
        result = await asyncio.to_thread(
            subprocess.run,
            argv,
            cwd=cwd,
            env=environment,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout_seconds,
        )
        output = {
            "argv": argv,
            "cwd": str(cwd.relative_to(self.workspace_root)).replace("\\", "/") or ".",
            "returncode": result.returncode,
            "stdout": self._bounded_text(result.stdout),
            "stderr": self._bounded_text(result.stderr),
            "stdout_truncated": len(result.stdout.encode("utf-8")) > _MAX_MODEL_OUTPUT_BYTES,
            "stderr_truncated": len(result.stderr.encode("utf-8")) > _MAX_MODEL_OUTPUT_BYTES,
        }
        return self._result(
            request.delivery_id,
            identity,
            output,
            condition=EffectCondition.SETTLED if result.returncode == 0 else EffectCondition.FAILED,
        )

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
