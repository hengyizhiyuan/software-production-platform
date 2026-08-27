"""Provider-neutral Executor capability boundary established by S2-A."""

from typing import Protocol

from spg.domain.execution import ExecutorDispatchRequest, ExecutorDispatchResult


class ExecutorCapabilityContract(Protocol):
    """Capability contract implemented by configured Executor adapters."""

    def dispatch(self, request: ExecutorDispatchRequest) -> ExecutorDispatchResult: ...
