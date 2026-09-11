"""Stable execution backend adapters for migration from legacy Codex execution."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from uuid import uuid4

from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.domain.native_execution import (
    BackendCapabilities,
    BackendControlCommand,
    BackendControlReceipt,
    BackendObservation,
    ControlRequestCondition,
    ExecutionHandle,
    NativeExecutionAdmission,
)


class NativeExecutionBackend:
    """Queue-backed Watt-native implementation of the stable backend contract."""

    def __init__(self, runtime: NativeExecutorRuntimeService) -> None:
        self.runtime = runtime

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            backend_identity="watt-native",
            backend_version="1",
            binding_schema_versions=(2,),
            supports_pause=True,
            supports_native_checkpoint=True,
            supports_multi_repository=True,
            max_writable_repositories=16,
            environment_profiles=("local-container-v1",),
        )

    async def start(self, admission: NativeExecutionAdmission) -> ExecutionHandle:
        entry = await asyncio.to_thread(self.runtime.admit, admission)
        return ExecutionHandle(
            backend_identity="watt-native",
            dispatch_id=entry.id,
            attempt_id=entry.attempt_id,
            generation=entry.grant_revision,
            opaque_reference=f"queue:{entry.id}",
        )

    async def observe(self, handle: ExecutionHandle) -> BackendObservation:
        return await asyncio.to_thread(self.runtime.observe, handle)

    async def control(self, command: BackendControlCommand) -> BackendControlReceipt:
        return await asyncio.to_thread(self.runtime.control, command)


LegacyStart = Callable[[NativeExecutionAdmission], Awaitable[ExecutionHandle]]
LegacyObserve = Callable[[ExecutionHandle], Awaitable[BackendObservation]]


class LegacyCodexExecutionBackend:
    """Explicit compatibility bridge; legacy Codex remains distinct from native execution."""

    def __init__(self, start: LegacyStart, observe: LegacyObserve) -> None:
        self._start = start
        self._observe = observe

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            backend_identity="legacy-codex",
            backend_version="1",
            binding_schema_versions=(2,),
            supports_pause=False,
            supports_native_checkpoint=False,
            supports_multi_repository=False,
            max_writable_repositories=1,
            environment_profiles=("legacy-dedicated-executor",),
        )

    async def start(self, admission: NativeExecutionAdmission) -> ExecutionHandle:
        return await self._start(admission)

    async def observe(self, handle: ExecutionHandle) -> BackendObservation:
        return await self._observe(handle)

    async def control(self, command: BackendControlCommand) -> BackendControlReceipt:
        return BackendControlReceipt(
            command_id=command.command_id,
            accepted=False,
            condition=ControlRequestCondition.REJECTED,
            message="legacy Codex backend does not support native control",
            recorded_at=datetime.now(timezone.utc),
        )
