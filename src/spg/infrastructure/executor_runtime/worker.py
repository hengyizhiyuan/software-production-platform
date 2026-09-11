"""Long-lived Watt-native worker process coordination."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.domain.native_execution import (
    ControlAction,
    ExecutionAllocationGrant,
    ExecutionMode,
    KernelRunResult,
    NativeExecutionAdmission,
    WorkerOffer,
    WorkingPlan,
)
from spg.executor.kernel import NativeExecutorKernel
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.executor_runtime.inference import InferenceResourceUnavailable


KernelFactory = Callable[[ExecutionAllocationGrant], NativeExecutorKernel]


class NativeExecutionWorker:
    """Claim one fair allocation and run its kernel with lease heartbeats."""

    def __init__(
        self,
        runtime: NativeExecutorRuntimeService,
        kernel_factory: KernelFactory,
        *,
        heartbeat_seconds: int = 10,
    ) -> None:
        if heartbeat_seconds < 1:
            raise ValueError("heartbeat interval must be positive")
        self.runtime = runtime
        self.kernel_factory = kernel_factory
        self.heartbeat_seconds = heartbeat_seconds

    async def run_once(self, offer: WorkerOffer) -> bool:
        grant = await asyncio.to_thread(self.runtime.allocate, offer)
        if grant is None:
            return False
        await asyncio.to_thread(self.runtime.activate_allocation, grant)
        binding_record, contract, checkpoint = await asyncio.to_thread(
            self._load_execution_reality, grant
        )
        semantic = checkpoint.semantic_manifest if checkpoint else {}
        plan_payload = semantic.get("working_plan") if isinstance(semantic, dict) else None
        working_plan = (
            WorkingPlan.model_validate(plan_payload)
            if isinstance(plan_payload, dict)
            else WorkingPlan(
                version=1,
                objective_reference=str(contract.id),
                chosen_approach="Inspect governed Reality and execute the bounded PWU contract.",
                approach_rationale="No prior checkpoint exists for this execution session.",
                obligation_ids=tuple(binding_record.binding.obligation_references),
            )
        )
        stop_heartbeat = asyncio.Event()
        heartbeat_task = asyncio.create_task(self._heartbeat(grant, stop_heartbeat))
        try:
            try:
                result = await self.kernel_factory(grant).run(
                    binding=binding_record.binding,
                    contract=contract,
                    worker_epoch=grant.allocation.lease_epoch,
                    working_plan=working_plan,
                    prior_checkpoint=checkpoint,
                    control_probe=lambda: asyncio.to_thread(
                        self._control_action, grant.allocation.attempt_id
                    ),
                )
            except InferenceResourceUnavailable as error:
                latest = await asyncio.to_thread(
                    self._latest_checkpoint, grant.allocation.attempt_id
                )
                result = KernelRunResult(
                    runtime_mode=ExecutionMode.WAITING_RESOURCE,
                    final_checkpoint_id=latest.id if latest else None,
                    step_count=latest.step_sequence if latest else 0,
                    inference_submissions=0,
                    tool_effects=0,
                    summary=str(error),
                    residual_obligations=tuple(binding_record.binding.obligation_references),
                    resource_retryable=error.retryable,
                )
            await asyncio.to_thread(self.runtime.finish_allocation, grant, result)
            return True
        finally:
            stop_heartbeat.set()
            await heartbeat_task

    async def _heartbeat(
        self,
        grant: ExecutionAllocationGrant,
        stop: asyncio.Event,
    ) -> None:
        while True:
            try:
                await asyncio.wait_for(stop.wait(), timeout=self.heartbeat_seconds)
                return
            except TimeoutError:
                await asyncio.to_thread(
                    self.runtime.heartbeat,
                    grant,
                    lease_seconds=max(self.heartbeat_seconds * 3, 5),
                )

    def _load_execution_reality(self, grant: ExecutionAllocationGrant):
        with self.runtime.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            binding = store.attempt_binding(grant.allocation.attempt_id)
            contract = store.contract(binding.pwu_contract_version_id)
            checkpoint = store.latest_checkpoint(grant.allocation.attempt_id)
            return binding, contract, checkpoint

    def _control_action(self, attempt_id):
        with self.runtime.database.unit_of_work() as uow:
            state = NativeExecutionStore(uow.session).attempt_state(attempt_id)
        return {
            ExecutionMode.PAUSE_REQUESTED: ControlAction.PAUSE,
            ExecutionMode.STOP_REQUESTED: ControlAction.STOP,
            ExecutionMode.CANCEL_REQUESTED: ControlAction.CANCEL,
        }.get(state.runtime_mode)

    def _latest_checkpoint(self, attempt_id):
        with self.runtime.database.unit_of_work() as uow:
            return NativeExecutionStore(uow.session).latest_checkpoint(attempt_id)
