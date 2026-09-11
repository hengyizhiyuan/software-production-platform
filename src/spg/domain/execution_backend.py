"""Stable backend interface shared by native and legacy execution implementations."""

from __future__ import annotations

from typing import Protocol

from spg.domain.native_execution import (
    BackendCapabilities,
    BackendControlCommand,
    BackendControlReceipt,
    BackendObservation,
    ExecutionHandle,
    NativeExecutionAdmission,
)


class ExecutionBackend(Protocol):
    def capabilities(self) -> BackendCapabilities: ...
    async def start(self, admission: NativeExecutionAdmission) -> ExecutionHandle: ...
    async def observe(self, handle: ExecutionHandle) -> BackendObservation: ...
    async def control(self, command: BackendControlCommand) -> BackendControlReceipt: ...
