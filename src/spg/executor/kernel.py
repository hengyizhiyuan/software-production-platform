"""Explicit, checkpointed Watt-native reasoning and tool execution loop."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol
from uuid import UUID, uuid4

from spg.domain.native_execution import (
    AttemptTerminalOutcome,
    CheckpointBundleRecord,
    ControlAction,
    ExecutionBindingV2,
    ExecutionMode,
    InferenceAction,
    InferenceRequest,
    InferenceResponse,
    KernelCheckpoint,
    KernelRunResult,
    PWUContractVersionRecord,
    ToolExecutionRequest,
    ToolExecutionResult,
    WorkingPlan,
)
from spg.executor.context import NativeContextAssembler
from spg.executor.tools import NativeToolRegistry


class InferencePort(Protocol):
    async def infer(self, request: InferenceRequest) -> InferenceResponse: ...


class CheckpointPort(Protocol):
    async def commit(self, checkpoint: KernelCheckpoint) -> CheckpointBundleRecord: ...


class KernelAuditPort(Protocol):
    async def begin_inference(self, request: InferenceRequest) -> UUID: ...
    async def finish_inference(
        self, step_id: UUID, response: InferenceResponse | None, error: BaseException | None
    ) -> None: ...
    async def begin_tool(self, step_id: UUID, request: ToolExecutionRequest) -> UUID: ...
    async def finish_tool(
        self,
        effect_id: UUID,
        request: ToolExecutionRequest,
        result: ToolExecutionResult | None,
        error: BaseException | None,
    ) -> None: ...


class NullKernelAudit:
    async def begin_inference(self, request: InferenceRequest) -> UUID:
        return uuid4()

    async def finish_inference(
        self, step_id: UUID, response: InferenceResponse | None, error: BaseException | None
    ) -> None:
        return None

    async def begin_tool(self, step_id: UUID, request: ToolExecutionRequest) -> UUID:
        return uuid4()

    async def finish_tool(
        self,
        effect_id: UUID,
        request: ToolExecutionRequest,
        result: ToolExecutionResult | None,
        error: BaseException | None,
    ) -> None:
        return None


ControlProbe = Callable[[], Awaitable[ControlAction | None]]


class NativeExecutorKernel:
    """Run bounded inference/tool cycles while preserving resumable working state."""

    def __init__(
        self,
        *,
        inference: InferencePort,
        tools: NativeToolRegistry,
        checkpoints: CheckpointPort,
        audit: KernelAuditPort | None = None,
        context: NativeContextAssembler | None = None,
    ) -> None:
        self.inference = inference
        self.tools = tools
        self.checkpoints = checkpoints
        self.audit = audit or NullKernelAudit()
        self.context = context or NativeContextAssembler()

    async def run(
        self,
        *,
        binding: ExecutionBindingV2,
        contract: PWUContractVersionRecord,
        worker_epoch: int,
        working_plan: WorkingPlan,
        prior_checkpoint: CheckpointBundleRecord | None = None,
        control_probe: ControlProbe | None = None,
    ) -> KernelRunResult:
        inference_count = 0
        tool_count = 0
        step_sequence = prior_checkpoint.step_sequence if prior_checkpoint else 0
        prior_results: tuple[ToolExecutionResult, ...] = ()
        final_checkpoint_id = prior_checkpoint.id if prior_checkpoint else None

        while inference_count < binding.resource_envelope.max_inference_submissions:
            control = await control_probe() if control_probe else None
            if control in {ControlAction.PAUSE, ControlAction.STOP, ControlAction.CANCEL}:
                checkpoint = await self._checkpoint(
                    binding=binding,
                    worker_epoch=worker_epoch,
                    step_sequence=step_sequence,
                    working_plan=working_plan,
                    tool_results=prior_results,
                    residual_obligations=tuple(binding.obligation_references),
                )
                mode = ExecutionMode.PAUSED if control is ControlAction.PAUSE else ExecutionMode.FINISHED
                terminal = None
                if control is ControlAction.STOP:
                    terminal = AttemptTerminalOutcome.STOPPED
                elif control is ControlAction.CANCEL:
                    terminal = AttemptTerminalOutcome.CANCELLED
                return KernelRunResult(
                    runtime_mode=mode,
                    terminal_outcome=terminal,
                    final_checkpoint_id=checkpoint.id,
                    step_count=step_sequence,
                    inference_submissions=inference_count,
                    tool_effects=tool_count,
                    summary=f"control request applied: {control.value}",
                    residual_obligations=tuple(binding.obligation_references),
                )

            step_sequence += 1
            request = self.context.assemble(
                binding=binding,
                contract=contract,
                working_plan=working_plan,
                step_sequence=step_sequence,
                available_tools=self.tools.contracts(),
                previous_results=prior_results,
                checkpoint=prior_checkpoint,
            )
            inference_step_id = await self.audit.begin_inference(request)
            try:
                response = await self.inference.infer(request)
            except BaseException as error:
                await self.audit.finish_inference(inference_step_id, None, error)
                raise
            await self.audit.finish_inference(inference_step_id, response, None)
            inference_count += 1
            working_plan = response.working_plan

            if response.action is InferenceAction.CONTINUE:
                results: list[ToolExecutionResult] = []
                for proposal in response.tool_calls:
                    if tool_count >= binding.resource_envelope.max_tool_effects:
                        return await self._budget_exhausted(
                            binding=binding,
                            worker_epoch=worker_epoch,
                            step_sequence=step_sequence,
                            working_plan=working_plan,
                            inference_count=inference_count,
                            tool_count=tool_count,
                            prior_results=tuple(results),
                        )
                    tool_request = ToolExecutionRequest(
                            delivery_id=uuid4(),
                            attempt_id=binding.attempt_id,
                            worker_epoch=worker_epoch,
                            step_id=inference_step_id,
                            proposal=proposal,
                            capability_grants=binding.capability_grants,
                            workspace=binding.workspace,
                        )
                    effect_id = await self.audit.begin_tool(inference_step_id, tool_request)
                    try:
                        result = await self.tools.execute(tool_request)
                    except BaseException as error:
                        await self.audit.finish_tool(effect_id, tool_request, None, error)
                        raise
                    await self.audit.finish_tool(effect_id, tool_request, result, None)
                    tool_count += 1
                    results.append(result)
                prior_results = tuple(results)
                checkpoint = await self._checkpoint(
                    binding=binding,
                    worker_epoch=worker_epoch,
                    step_sequence=step_sequence,
                    working_plan=working_plan,
                    tool_results=prior_results,
                    residual_obligations=response.residual_obligations,
                )
                prior_checkpoint = checkpoint
                final_checkpoint_id = checkpoint.id
                continue

            checkpoint = await self._checkpoint(
                binding=binding,
                worker_epoch=worker_epoch,
                step_sequence=step_sequence,
                working_plan=working_plan,
                tool_results=prior_results,
                result_claim=response.result_claim,
                residual_obligations=response.residual_obligations,
            )
            final_checkpoint_id = checkpoint.id
            if response.action is InferenceAction.WAITING_RESOURCE:
                return KernelRunResult(
                    runtime_mode=ExecutionMode.WAITING_RESOURCE,
                    final_checkpoint_id=final_checkpoint_id,
                    step_count=step_sequence,
                    inference_submissions=inference_count,
                    tool_effects=tool_count,
                    summary=response.summary,
                    residual_obligations=response.residual_obligations,
                )
            outcome = {
                InferenceAction.RESULT_READY: AttemptTerminalOutcome.RESULT_READY,
                InferenceAction.UNABLE_TO_COMPLETE: AttemptTerminalOutcome.UNABLE_TO_COMPLETE,
                InferenceAction.BOUNDARY_CROSSING_REQUIRED: AttemptTerminalOutcome.BOUNDARY_CROSSING_REQUIRED,
            }[response.action]
            return KernelRunResult(
                runtime_mode=ExecutionMode.FINISHED,
                terminal_outcome=outcome,
                final_checkpoint_id=final_checkpoint_id,
                step_count=step_sequence,
                inference_submissions=inference_count,
                tool_effects=tool_count,
                summary=response.summary,
                result_claim=response.result_claim,
                residual_obligations=response.residual_obligations,
            )

        return await self._budget_exhausted(
            binding=binding,
            worker_epoch=worker_epoch,
            step_sequence=step_sequence,
            working_plan=working_plan,
            inference_count=inference_count,
            tool_count=tool_count,
            prior_results=prior_results,
        )

    async def _checkpoint(
        self,
        *,
        binding: ExecutionBindingV2,
        worker_epoch: int,
        step_sequence: int,
        working_plan: WorkingPlan,
        tool_results: tuple[ToolExecutionResult, ...],
        result_claim: dict[str, object] | None = None,
        residual_obligations: tuple[str, ...] = (),
    ) -> CheckpointBundleRecord:
        return await self.checkpoints.commit(
            KernelCheckpoint(
                step_sequence=step_sequence,
                working_plan=working_plan,
                tool_results=tool_results,
                source_vector_digest=binding.source_vector.digest or "",
                result_claim=result_claim,
                residual_obligations=residual_obligations,
            )
        )

    async def _budget_exhausted(
        self,
        *,
        binding: ExecutionBindingV2,
        worker_epoch: int,
        step_sequence: int,
        working_plan: WorkingPlan,
        inference_count: int,
        tool_count: int,
        prior_results: tuple[ToolExecutionResult, ...],
    ) -> KernelRunResult:
        checkpoint = await self._checkpoint(
            binding=binding,
            worker_epoch=worker_epoch,
            step_sequence=step_sequence,
            working_plan=working_plan,
            tool_results=prior_results,
            residual_obligations=tuple(binding.obligation_references),
        )
        return KernelRunResult(
            runtime_mode=ExecutionMode.FINISHED,
            terminal_outcome=AttemptTerminalOutcome.BUDGET_EXHAUSTED,
            final_checkpoint_id=checkpoint.id,
            step_count=step_sequence,
            inference_submissions=inference_count,
            tool_effects=tool_count,
            summary="native execution resource envelope was exhausted",
            residual_obligations=tuple(binding.obligation_references),
        )
