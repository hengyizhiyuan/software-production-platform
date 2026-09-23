"""Tool contracts, grant checks, and a provider-neutral tool registry."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from spg.domain.native_execution import (
    CapabilityGrant,
    NativeExecutionConflict,
    ToolExecutionRequest,
    ToolExecutionResult,
)


ToolHandler = Callable[[ToolExecutionRequest], Awaitable[ToolExecutionResult]]


def validate_generic_git_process(argv: list[str]) -> None:
    """Generic process grants never authorize Git delivery or ref mutations."""

    if not argv or Path(argv[0]).name.lower().removesuffix(".exe") != "git":
        return
    arguments = argv[1:]
    if any(
        argument.startswith(("--output", "--ext-diff", "--config-env", "-c", "-C"))
        for argument in arguments
    ):
        raise ValueError("Git mutation or remote delivery requires a governed Git capability")
    read_only = {
        "status", "diff", "log", "show", "rev-parse", "ls-files",
        "ls-tree", "merge-base", "cat-file",
    }
    if arguments and arguments[0] in read_only:
        return
    if arguments and arguments[0] == "branch" and arguments[1:] in (
        ["--show-current"], ["--list"], ["--all"],
    ):
        return
    raise ValueError("Git mutation or remote delivery requires a governed Git capability")


PUBLIC_NATIVE_TOOL_CONTRACTS: tuple[dict[str, object], ...] = (
    {
        "identity": "file.read",
        "version": "1",
        "description": "Read one UTF-8 file from the private execution workspace.",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False},
        "effect_classification": "READ",
    },
    {
        "identity": "file.write",
        "version": "1",
        "description": "Atomically write one UTF-8 file inside an admitted path scope.",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False},
        "effect_classification": "LOCAL_MUTATION",
    },
    {
        "identity": "filesystem.operation",
        "version": "1",
        "description": "Run one bounded search, stat, mkdir, move, delete, or diff operation inside the admitted Production Environment workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {"type": "string"},
                "path": {"type": "string"},
                "destination": {"type": "string"},
                "query": {"type": "string"},
            },
            "required": ["operation", "path"],
            "additionalProperties": False,
        },
        "effect_classification": "GOVERNED_FILESYSTEM",
    },
    {
        "identity": "process.run",
        "version": "1",
        "description": (
            "Run one allowlisted argv process without a shell. Inline code flags such as "
            "python -c are rejected. For a Python import check, use "
            "['python', '-m', 'package.module'] with cwd='src', or use test.run with "
            "pytest --collect-only."
        ),
        "input_schema": {"type": "object", "properties": {"argv": {"type": "array", "items": {"type": "string"}}, "cwd": {"type": "string"}}, "required": ["argv"], "additionalProperties": False},
        "effect_classification": "PROCESS",
    },
    {
        "identity": "git.status",
        "version": "1",
        "description": "Observe porcelain Git status for one admitted repository mount.",
        "input_schema": {"type": "object", "properties": {"cwd": {"type": "string"}}, "required": ["cwd"], "additionalProperties": False},
        "effect_classification": "READ",
    },
    {
        "identity": "git.diff",
        "version": "1",
        "description": "Observe the bounded Git diff for one admitted repository mount.",
        "input_schema": {"type": "object", "properties": {"cwd": {"type": "string"}}, "required": ["cwd"], "additionalProperties": False},
        "effect_classification": "READ",
    },
    {
        "identity": "git.operation",
        "version": "1",
        "description": "Execute one explicitly granted bounded Git operation in the isolated Work workspace; never push or publish.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {"type": "string"},
                "branch": {"type": "string"},
                "revision": {"type": "string"},
                "ancestor": {"type": "string"},
                "descendant": {"type": "string"},
                "tag": {"type": "string"},
                "message": {"type": "string"},
                "paths": {"type": "array", "items": {"type": "string"}},
                "cwd": {"type": "string"},
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
        "effect_classification": "GOVERNED_GIT",
    },
    {
        "identity": "test.run",
        "version": "1",
        "description": "Run an admitted Python or Node test recipe. cwd is workspace-relative (for example '.', 'client', or 'server'), never '/workspace'.",
        "input_schema": {"type": "object", "properties": {"argv": {"type": "array", "items": {"type": "string"}}, "cwd": {"type": "string"}}, "required": ["argv", "cwd"], "additionalProperties": False},
        "effect_classification": "PROCESS",
    },
    {
        "identity": "build.run",
        "version": "1",
        "description": "Run an admitted build recipe.",
        "input_schema": {"type": "object", "properties": {"argv": {"type": "array", "items": {"type": "string"}}, "cwd": {"type": "string"}}, "required": ["argv", "cwd"], "additionalProperties": False},
        "effect_classification": "PROCESS",
    },
    {
        "identity": "dependency.sync",
        "version": "1",
        "description": "Run a lock-governed dependency synchronization recipe.",
        "input_schema": {"type": "object", "properties": {"argv": {"type": "array", "items": {"type": "string"}}, "cwd": {"type": "string"}}, "required": ["argv", "cwd"], "additionalProperties": False},
        "effect_classification": "PROCESS",
    },
    {
        "identity": "preview.inspect",
        "version": "1",
        "description": "Inspect one static artifact without starting a browser session.",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False},
        "effect_classification": "READ",
    },
)


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    identity: str
    version: str
    description: str
    input_schema: dict[str, object]
    effect_classification: str
    handler: ToolHandler

    def public_contract(self) -> dict[str, object]:
        return {
            "identity": self.identity,
            "version": self.version,
            "description": self.description,
            "input_schema": self.input_schema,
            "effect_classification": self.effect_classification,
        }


class NativeToolRegistry:
    """Dispatch only explicitly registered tools covered by capability grants."""

    def __init__(self, definitions: tuple[ToolDefinition, ...]) -> None:
        identities = [item.identity for item in definitions]
        if len(set(identities)) != len(identities):
            raise ValueError("tool identities must be unique")
        self._definitions = {item.identity: item for item in definitions}

    def contracts(self) -> tuple[dict[str, object], ...]:
        return tuple(item.public_contract() for item in self._definitions.values())

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        definition = self._definitions.get(request.proposal.tool_identity)
        if definition is None:
            raise NativeExecutionConflict(
                f"tool is not registered: {request.proposal.tool_identity}"
            )
        if definition.identity in {
            str(contract["identity"]) for contract in PUBLIC_NATIVE_TOOL_CONTRACTS
        }:
            from spg.application.connector_manifest import built_in_executable_capabilities
            from spg.domain.connectors import ConnectorAvailability, SideEffectLevel

            if definition.identity in {"git.operation", "filesystem.operation"}:
                from spg.executor.git_operations import git_operation_commands

                operation = request.proposal.arguments.get("operation")
                if definition.identity == "git.operation":
                    git_operation_commands(request.proposal.arguments)
                    capability_id = f"git.{operation}"
                else:
                    if operation not in {"search", "stat", "mkdir", "move", "delete", "diff"}:
                        raise NativeExecutionConflict("filesystem operation is not installed")
                    capability_id = f"filesystem.{operation}"
                connector = next(
                    (
                        item for item in built_in_executable_capabilities()
                        if item.capability_id == capability_id
                        and item.availability is ConnectorAvailability.AVAILABLE
                    ),
                    None,
                )
            else:
                connector = next(
                    (
                        item for item in built_in_executable_capabilities()
                        if item.execution_provider == f"native-tool:{definition.identity}"
                        and item.availability is ConnectorAvailability.AVAILABLE
                    ),
                    None,
                )
            if connector is None:
                raise NativeExecutionConflict(
                    f"executable connector is unavailable for tool: {definition.identity}"
                )
        grant = self._grant_for(definition.identity, request.capability_grants)
        if definition.identity in {"git.operation", "filesystem.operation"} and connector.capability_id not in grant.scope.get("capabilities", ()):
            raise NativeExecutionConflict("Operation is not admitted by the Task Contract")
        if connector.side_effect_level is SideEffectLevel.DESTRUCTIVE and any(
            permission not in grant.scope.get("permissions", ())
            for permission in connector.permissions_required
        ):
            raise NativeExecutionConflict("Destructive operation lacks explicit Work permission")
        self._validate_path_scope(request, grant)
        result = await definition.handler(request)
        if result.delivery_id != request.delivery_id:
            raise NativeExecutionConflict("tool result delivery identity differs")
        if result.tool_identity != definition.identity:
            raise NativeExecutionConflict("tool result identity differs")
        return result

    @staticmethod
    def _grant_for(
        identity: str,
        grants: tuple[CapabilityGrant, ...],
    ) -> CapabilityGrant:
        for grant in grants:
            if grant.identity == identity:
                return grant
        raise NativeExecutionConflict(f"tool capability was not granted: {identity}")

    @staticmethod
    def _validate_path_scope(
        request: ToolExecutionRequest,
        grant: CapabilityGrant,
    ) -> None:
        allowed = tuple(str(item) for item in grant.scope.get("paths", ()))
        forbidden = tuple(str(item) for item in grant.scope.get("forbidden_paths", ()))
        for key in ("path", "destination", "cwd"):
            raw_path = request.proposal.arguments.get(key)
            if not isinstance(raw_path, str):
                continue
            if key == "cwd" and raw_path == ".":
                continue
            if "\\" in raw_path:
                raise NativeExecutionConflict("tool paths must use POSIX separators")
            path = PurePosixPath(raw_path)
            if path.is_absolute() or ".." in path.parts:
                raise NativeExecutionConflict("tool path escapes the workspace")
            normalized = str(path)
            if forbidden and any(_within(normalized, root) for root in forbidden):
                raise NativeExecutionConflict("tool path is explicitly forbidden")
            if not allowed:
                continue
            in_scope = any(_within(normalized, root) for root in allowed)
            if key == "cwd":
                in_scope = in_scope or any(_within(root, normalized) for root in allowed)
            if not in_scope:
                raise NativeExecutionConflict("tool path is outside the granted scope")


def _within(path: str, root: str) -> bool:
    root = root.rstrip("/")
    return path == root or path.startswith(f"{root}/")
