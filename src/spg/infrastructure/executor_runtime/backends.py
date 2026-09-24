"""Stable Watt-native execution backend and pinned handle routing."""

from __future__ import annotations

import asyncio

from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.domain.native_execution import (
    BackendCapabilities,
    BackendControlCommand,
    BackendControlReceipt,
    BackendObservation,
    ExecutionHandle,
    NativeExecutionAdmission,
    NativeExecutionConflict,
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


class PinnedExecutionBackendRouter:
    """Route existing handles by their immutable backend, across default cutovers."""

    def __init__(self, backends: tuple[object, ...], *, default_backend: str) -> None:
        self._backends = {
            backend.capabilities().backend_identity: backend for backend in backends
        }
        if len(self._backends) != len(backends):
            raise ValueError("execution backend identities must be unique")
        self.set_default(default_backend)

    @property
    def default_backend(self) -> str:
        return self._default_backend

    def set_default(self, backend_identity: str) -> None:
        if backend_identity not in self._backends:
            raise NativeExecutionConflict("execution backend is not registered")
        self._default_backend = backend_identity

    async def start(
        self,
        admission: NativeExecutionAdmission,
        *,
        backend_identity: str | None = None,
    ) -> ExecutionHandle:
        selected = backend_identity or self._default_backend
        if admission.binding.backend_implementation != selected:
            raise NativeExecutionConflict(
                "admission binding is pinned to a different execution backend"
            )
        backend = self._backends[selected]
        writable = len(admission.binding.workspace.mounts)
        capabilities = backend.capabilities()
        if writable > capabilities.max_writable_repositories:
            raise NativeExecutionConflict(
                "execution backend cannot admit this repository vector"
            )
        return await backend.start(admission)

    async def observe(self, handle: ExecutionHandle) -> BackendObservation:
        return await self._backend_for_handle(handle).observe(handle)

    async def control(
        self, command: BackendControlCommand
    ) -> BackendControlReceipt:
        return await self._backend_for_handle(command.handle).control(command)

    def _backend_for_handle(self, handle: ExecutionHandle):
        backend = self._backends.get(handle.backend_identity)
        if backend is None:
            raise NativeExecutionConflict("execution handle backend is not registered")
        return backend
