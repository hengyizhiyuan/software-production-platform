"""Long-lived Watt-native worker process coordination."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.domain.native_execution import (
    AttemptTerminalOutcome,
    ControlAction,
    ExecutionAllocationGrant,
    ExecutionMode,
    KernelRunResult,
    NativeExecutionConflict,
    NativeExecutionAdmission,
    WorkerOffer,
    WorkingPlan,
)
from spg.executor.kernel import NativeExecutorKernel
from spg.executor.context import NativeContextCapacityError
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.executor_runtime.inference import (
    InferenceAdapterError,
    InferenceResourceUnavailable,
    InferenceTransportUnknown,
)


KernelFactory = Callable[[ExecutionAllocationGrant], NativeExecutorKernel]
SUPPORTED_CHECKPOINT_SCHEMA_VERSIONS = frozenset({1})


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
        binding_record, contract, checkpoint, session_step_frontier = await asyncio.to_thread(
            self._load_execution_reality, grant
        )
        if (
            checkpoint is not None
            and checkpoint.schema_version not in SUPPORTED_CHECKPOINT_SCHEMA_VERSIONS
        ):
            raw_residual = checkpoint.semantic_manifest.get("residual_obligations")
            residual = tuple(binding_record.binding.obligation_references)
            if isinstance(raw_residual, list) and all(
                isinstance(item, str) for item in raw_residual
            ):
                residual = tuple(raw_residual)
            await asyncio.to_thread(
                self.runtime.finish_allocation,
                grant,
                KernelRunResult(
                    runtime_mode=ExecutionMode.WAITING_RESOURCE,
                    final_checkpoint_id=checkpoint.id,
                    step_count=checkpoint.step_sequence,
                    inference_submissions=0,
                    tool_effects=0,
                    summary=(
                        "Checkpoint schema version "
                        f"{checkpoint.schema_version} is not supported by this runtime"
                    ),
                    residual_obligations=residual,
                    resource_retryable=False,
                ),
            )
            return True
        recovered_results = await asyncio.to_thread(
            self._uncheckpointed_results,
            grant.allocation.attempt_id,
            checkpoint.step_sequence if checkpoint else 0,
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
        heartbeat_task = asyncio.create_task(self._heartbeat(grant, stop_heartbeat, offer))
        try:
            try:
                result = await self.kernel_factory(grant).run(
                    binding=binding_record.binding,
                    contract=contract,
                    worker_epoch=grant.allocation.lease_epoch,
                    working_plan=working_plan,
                    prior_checkpoint=checkpoint,
                    session_step_frontier=session_step_frontier,
                    recovered_results=recovered_results,
                    control_probe=lambda: asyncio.to_thread(
                        self._control_action, grant.allocation.attempt_id
                    ),
                )
            except InferenceResourceUnavailable as error:
                latest = await asyncio.to_thread(
                    self._latest_checkpoint, grant.allocation.attempt_id
                )
                residual = tuple(binding_record.binding.obligation_references)
                if latest is not None:
                    checkpoint_residual = latest.semantic_manifest.get(
                        "residual_obligations"
                    )
                    if isinstance(checkpoint_residual, list) and all(
                        isinstance(item, str) for item in checkpoint_residual
                    ):
                        residual = tuple(checkpoint_residual)
                result = KernelRunResult(
                    runtime_mode=ExecutionMode.WAITING_RESOURCE,
                    final_checkpoint_id=latest.id if latest else None,
                    step_count=latest.step_sequence if latest else 0,
                    inference_submissions=0,
                    tool_effects=0,
                    summary=str(error),
                    residual_obligations=residual,
                    resource_retryable=error.retryable,
                )
            except InferenceTransportUnknown as error:
                latest = await asyncio.to_thread(
                    self._latest_checkpoint, grant.allocation.attempt_id
                )
                residual = tuple(binding_record.binding.obligation_references)
                if latest is not None:
                    checkpoint_residual = latest.semantic_manifest.get(
                        "residual_obligations"
                    )
                    if isinstance(checkpoint_residual, list) and all(
                        isinstance(item, str) for item in checkpoint_residual
                    ):
                        residual = tuple(checkpoint_residual)
                result = KernelRunResult(
                    runtime_mode=ExecutionMode.WAITING_RESOURCE,
                    final_checkpoint_id=latest.id if latest else None,
                    step_count=latest.step_sequence if latest else 0,
                    inference_submissions=0,
                    tool_effects=0,
                    summary=(
                        f"PROVIDER_TRANSPORT {error.failure_code}: {error}"
                    ),
                    residual_obligations=residual,
                    resource_retryable=error.retryable,
                )
            except NativeContextCapacityError as error:
                latest = await asyncio.to_thread(
                    self._latest_checkpoint, grant.allocation.attempt_id
                )
                residual = tuple(binding_record.binding.obligation_references)
                if latest is not None:
                    checkpoint_residual = latest.semantic_manifest.get(
                        "residual_obligations"
                    )
                    if isinstance(checkpoint_residual, list) and all(
                        isinstance(item, str) for item in checkpoint_residual
                    ):
                        residual = tuple(checkpoint_residual)
                result = KernelRunResult(
                    runtime_mode=ExecutionMode.WAITING_RESOURCE,
                    final_checkpoint_id=latest.id if latest else None,
                    step_count=latest.step_sequence if latest else 0,
                    inference_submissions=0,
                    tool_effects=0,
                    summary=str(error),
                    residual_obligations=residual,
                    resource_retryable=False,
                )
            except InferenceAdapterError as error:
                latest = await asyncio.to_thread(
                    self._latest_checkpoint, grant.allocation.attempt_id
                )
                residual = tuple(binding_record.binding.obligation_references)
                if latest is not None:
                    checkpoint_residual = latest.semantic_manifest.get(
                        "residual_obligations"
                    )
                    if isinstance(checkpoint_residual, list) and all(
                        isinstance(item, str) for item in checkpoint_residual
                    ):
                        residual = tuple(checkpoint_residual)
                result = KernelRunResult(
                    runtime_mode=ExecutionMode.FINISHED,
                    terminal_outcome=AttemptTerminalOutcome.UNABLE_TO_COMPLETE,
                    final_checkpoint_id=latest.id if latest else None,
                    step_count=latest.step_sequence if latest else 0,
                    inference_submissions=0,
                    tool_effects=0,
                    summary=(
                        "Provider returned no admissible native execution decision: "
                        f"{error}"
                    ),
                    residual_obligations=residual,
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
        offer: WorkerOffer | None = None,
    ) -> None:
        while True:
            try:
                await asyncio.wait_for(stop.wait(), timeout=self.heartbeat_seconds)
                return
            except TimeoutError:
                try:
                    keyword_arguments = {
                        "lease_seconds": max(self.heartbeat_seconds * 3, 5)
                    }
                    if offer is not None:
                        keyword_arguments["offer"] = offer
                    await asyncio.to_thread(
                        self.runtime.heartbeat,
                        grant,
                        **keyword_arguments,
                    )
                except NativeExecutionConflict:
                    # A kernel failure can race with coordinator fencing. Once
                    # shutdown has started, the stale heartbeat is expected and
                    # must not mask the kernel's original recovery signal.
                    if stop.is_set():
                        return
                    raise

    def _load_execution_reality(self, grant: ExecutionAllocationGrant):
        with self.runtime.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            binding = store.attempt_binding(grant.allocation.attempt_id)
            contract = store.contract(binding.pwu_contract_version_id)
            checkpoint = store.latest_checkpoint(grant.allocation.attempt_id)
            session_step_frontier = store.latest_step_sequence_for_session(
                binding.session_id
            )
            return binding, contract, checkpoint, session_step_frontier

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

    def _uncheckpointed_results(self, attempt_id, after_step_sequence):
        with self.runtime.database.unit_of_work() as uow:
            return NativeExecutionStore(uow.session).tool_results_after(
                attempt_id,
                after_step_sequence=after_step_sequence,
            )
