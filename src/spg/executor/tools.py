"""Tool contracts, grant checks, and a provider-neutral tool registry."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import PurePosixPath

from spg.domain.native_execution import (
    CapabilityGrant,
    NativeExecutionConflict,
    ToolExecutionRequest,
    ToolExecutionResult,
)


ToolHandler = Callable[[ToolExecutionRequest], Awaitable[ToolExecutionResult]]


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
        "identity": "process.run",
        "version": "1",
        "description": "Run one allowlisted argv process without a shell.",
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
        "identity": "test.run",
        "version": "1",
        "description": "Run an admitted Python or Node test recipe.",
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
        grant = self._grant_for(definition.identity, request.capability_grants)
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
        raw_path = request.proposal.arguments.get("path")
        if not isinstance(raw_path, str):
            return
        if "\\" in raw_path:
            raise NativeExecutionConflict("tool paths must use POSIX separators")
        path = PurePosixPath(raw_path)
        if path.is_absolute() or ".." in path.parts:
            raise NativeExecutionConflict("tool path escapes the workspace")
        allowed = tuple(str(item) for item in grant.scope.get("paths", ()))
        forbidden = tuple(str(item) for item in grant.scope.get("forbidden_paths", ()))
        normalized = str(path)
        if forbidden and any(_within(normalized, root) for root in forbidden):
            raise NativeExecutionConflict("tool path is explicitly forbidden")
        if allowed and not any(_within(normalized, root) for root in allowed):
            raise NativeExecutionConflict("tool path is outside the granted scope")


def _within(path: str, root: str) -> bool:
    root = root.rstrip("/")
    return path == root or path.startswith(f"{root}/")
