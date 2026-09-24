"""Explicit, checkpointed Watt-native reasoning and tool execution loop."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol
from uuid import UUID, uuid4

from spg.domain.native_execution import (
    AttemptTerminalOutcome,
    CheckpointBundleRecord,
    ControlAction,
    EffectCondition,
    ExecutionBindingV2,
    ExecutionMode,
    InferenceAction,
    InferenceDecisionRejected,
    InferenceRequest,
    InferenceResponse,
    KernelCheckpoint,
    KernelRunResult,
    PWUContractVersionRecord,
    RepairabilityClassification,
    ToolExecutionRequest,
    ToolExecutionResult,
    WorkingPlan,
    canonical_digest,
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
    ) -> RepairabilityClassification | None: ...


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

    _PROCESS_TOOLS = {"process.run", "test.run", "build.run", "dependency.sync"}
    _DIAGNOSTIC_TOOLS = {"file.read", "git.status", "git.diff", "test.run", "build.run", "preview.inspect"}

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
        session_step_frontier: int = 0,
        recovered_results: tuple[ToolExecutionResult, ...] = (),
        control_probe: ControlProbe | None = None,
    ) -> KernelRunResult:
        inference_count = 0
        tool_count = 0
        step_sequence = max(
            prior_checkpoint.step_sequence if prior_checkpoint else 0,
            session_step_frontier,
        )
        prior_results: tuple[ToolExecutionResult, ...] = recovered_results
        if prior_checkpoint is not None:
            checkpoint_results = prior_checkpoint.execution_manifest.get("tool_results", [])
            if isinstance(checkpoint_results, list):
                prior_results = tuple(
                    ToolExecutionResult.model_validate(item)
                    for item in checkpoint_results
                    if isinstance(item, dict)
                ) + recovered_results
        final_checkpoint_id = prior_checkpoint.id if prior_checkpoint else None
        residual_obligations = tuple(binding.obligation_references)
        ineffective_rounds = 0
        rejected_decision_rounds = 0
        evidence_required = False
        if prior_checkpoint is not None:
            checkpoint_residual = prior_checkpoint.semantic_manifest.get(
                "residual_obligations"
            )
            if isinstance(checkpoint_residual, list) and all(
                isinstance(item, str) for item in checkpoint_residual
            ):
                residual_obligations = tuple(checkpoint_residual)

        history_provider = getattr(self.audit, "recent_repair_reality", None)
        repair_history = history_provider() if callable(history_provider) else ()

        while inference_count < binding.resource_envelope.max_inference_submissions:
            repair_history = history_provider() if callable(history_provider) else repair_history
            evidence_required = any(
                item.get("operation_id") == str(binding.attempt_id)
                and item.get("status") == "OPEN"
                and item.get("repairability") == RepairabilityClassification.REPAIRABLE_WITH_SUFFICIENT_EVIDENCE.value
                for item in repair_history
            )
            control = await control_probe() if control_probe else None
            if control in {ControlAction.PAUSE, ControlAction.STOP, ControlAction.CANCEL}:
                checkpoint = await self._checkpoint(
                    binding=binding,
                    worker_epoch=worker_epoch,
                    step_sequence=step_sequence,
                    working_plan=working_plan,
                    tool_results=prior_results,
                    residual_obligations=residual_obligations,
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
                    residual_obligations=residual_obligations,
                )

            step_sequence += 1
            request = self.context.assemble(
                binding=binding,
                contract=contract,
                working_plan=working_plan,
                step_sequence=step_sequence,
                # CONTINUE is itself a non-terminal declaration. Keep tools
                # available after a mutating round even if that response predicts
                # no residual work: the effects have not yet been observed and a
                # follow-up verification may still be required. The ineffective
                # round bound below still forces a terminal decision after three
                # read/check-only rounds.
                available_tools=(
                    tuple(
                        item for item in self.tools.contracts()
                        if not evidence_required or item.get("identity") in self._DIAGNOSTIC_TOOLS
                    )
                    if ineffective_rounds < 3
                    else ()
                ),
                residual_obligations=residual_obligations,
                previous_results=prior_results,
                checkpoint=prior_checkpoint,
                repair_history=repair_history,
            )
            inference_step_id = await self.audit.begin_inference(request)
            try:
                response = await self.inference.infer(request)
            except InferenceDecisionRejected as error:
                await self.audit.finish_inference(inference_step_id, None, error)
                inference_count += 1
                rejected_decision_rounds += 1
                output = {
                    "error_type": "InferenceDecisionRejected",
                    "reason_code": error.reason_code,
                    "response_observed": True,
                    "effect_observed": False,
                }
                validation_issues = getattr(error, "validation_issues", ())
                if validation_issues:
                    output["validation_issues"] = list(validation_issues)
                rejection = ToolExecutionResult(
                    delivery_id=uuid4(),
                    tool_identity="inference.decision",
                    condition=EffectCondition.FAILED,
                    output=output,
                    output_digest=canonical_digest(output),
                    evidence=({"type": "PROVIDER_DECISION_REJECTION", **output},),
                )
                prior_results = prior_results + (rejection,)
                ineffective_rounds += 1
                checkpoint = await self._checkpoint(
                    binding=binding,
                    worker_epoch=worker_epoch,
                    step_sequence=step_sequence,
                    working_plan=working_plan,
                    tool_results=prior_results,
                    residual_obligations=residual_obligations,
                )
                prior_checkpoint = checkpoint
                final_checkpoint_id = checkpoint.id
                if rejected_decision_rounds < 2:
                    continue
                return KernelRunResult(
                    runtime_mode=ExecutionMode.FINISHED,
                    terminal_outcome=AttemptTerminalOutcome.UNABLE_TO_COMPLETE,
                    final_checkpoint_id=final_checkpoint_id,
                    step_count=step_sequence,
                    inference_submissions=inference_count,
                    tool_effects=tool_count,
                    summary="two observed Provider decisions failed local validation",
                    residual_obligations=residual_obligations,
                )
            except BaseException as error:
                await self.audit.finish_inference(inference_step_id, None, error)
                raise
            await self.audit.finish_inference(inference_step_id, response, None)
            inference_count += 1
            working_plan = response.working_plan
            residual_obligations = response.residual_obligations

            if response.action is InferenceAction.CONTINUE:
                results: list[ToolExecutionResult] = []
                for proposal in response.tool_calls:
                    if evidence_required and proposal.tool_identity not in self._DIAGNOSTIC_TOOLS:
                        checkpoint = await self._checkpoint(
                            binding=binding, worker_epoch=worker_epoch,
                            step_sequence=step_sequence, working_plan=working_plan,
                            tool_results=prior_results,
                            residual_obligations=residual_obligations,
                        )
                        return KernelRunResult(
                            runtime_mode=ExecutionMode.FINISHED,
                            terminal_outcome=AttemptTerminalOutcome.BOUNDARY_CROSSING_REQUIRED,
                            final_checkpoint_id=checkpoint.id,
                            step_count=step_sequence,
                            inference_submissions=inference_count,
                            tool_effects=tool_count,
                            summary="Mutation requires an admitted acceptance oracle after inconclusive diagnostic evidence",
                            residual_obligations=residual_obligations,
                        )
                    if tool_count >= binding.resource_envelope.max_tool_effects:
                        return await self._budget_exhausted(
                            binding=binding,
                            worker_epoch=worker_epoch,
                            step_sequence=step_sequence,
                            working_plan=working_plan,
                            inference_count=inference_count,
                            tool_count=tool_count,
                            prior_results=tuple(results),
                            residual_obligations=residual_obligations,
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
                    interrupted_by: ControlAction | None = None
                    tool_task = asyncio.create_task(self.tools.execute(tool_request))
                    try:
                        if (
                            control_probe is not None
                            and proposal.tool_identity in self._PROCESS_TOOLS
                        ):
                            while not tool_task.done():
                                done, _ = await asyncio.wait(
                                    {tool_task}, timeout=0.1
                                )
                                if done:
                                    break
                                interrupted_by = await control_probe()
                                if interrupted_by in {
                                    ControlAction.PAUSE,
                                    ControlAction.STOP,
                                    ControlAction.CANCEL,
                                }:
                                    tool_task.cancel()
                                    try:
                                        await tool_task
                                    except asyncio.CancelledError:
                                        pass
                                    output = {
                                        "control": interrupted_by.value,
                                        "effect_observed": False,
                                        "process_tree_terminated": True,
                                        "delivery_id": str(tool_request.delivery_id),
                                    }
                                    result = ToolExecutionResult(
                                        delivery_id=tool_request.delivery_id,
                                        tool_identity=proposal.tool_identity,
                                        condition=EffectCondition.FAILED,
                                        output=output,
                                        output_digest=canonical_digest(output),
                                        evidence=(
                                            {
                                                "type": "PROCESS_TERMINATION_RECEIPT",
                                                "digest": canonical_digest(output),
                                            },
                                        ),
                                    )
                                    break
                            else:
                                result = await tool_task
                            if interrupted_by is None:
                                result = await tool_task
                        else:
                            result = await tool_task
                    except BaseException as error:
                        await self.audit.finish_tool(effect_id, tool_request, None, error)
                        raise
                    repairability = await self.audit.finish_tool(effect_id, tool_request, result, None)
                    tool_count += 1
                    results.append(result)
                    if repairability is RepairabilityClassification.REPAIRABLE_WITH_SUFFICIENT_EVIDENCE:
                        evidence_required = True
                    elif repairability is RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE:
                        evidence_required = False
                    elif repairability in {
                        RepairabilityClassification.REQUIRES_HUMAN_INPUT,
                        RepairabilityClassification.REQUIRES_HUMAN_DECISION,
                        RepairabilityClassification.UNSAFE_TO_AUTOREPAIR,
                    }:
                        checkpoint = await self._checkpoint(
                            binding=binding, worker_epoch=worker_epoch,
                            step_sequence=step_sequence, working_plan=working_plan,
                            tool_results=prior_results + tuple(results),
                            residual_obligations=residual_obligations,
                        )
                        return KernelRunResult(
                            runtime_mode=ExecutionMode.FINISHED,
                            terminal_outcome=(
                                AttemptTerminalOutcome.UNABLE_TO_COMPLETE
                                if repairability is RepairabilityClassification.UNSAFE_TO_AUTOREPAIR
                                else AttemptTerminalOutcome.BOUNDARY_CROSSING_REQUIRED
                            ),
                            final_checkpoint_id=checkpoint.id,
                            step_count=step_sequence,
                            inference_submissions=inference_count,
                            tool_effects=tool_count,
                            summary=f"Repairability boundary: {repairability.value}",
                            residual_obligations=residual_obligations,
                        )
                    if interrupted_by is not None:
                        checkpoint = await self._checkpoint(
                            binding=binding,
                            worker_epoch=worker_epoch,
                            step_sequence=step_sequence,
                            working_plan=working_plan,
                            tool_results=tuple(results),
                            residual_obligations=residual_obligations,
                        )
                        return self._control_result(
                            control=interrupted_by,
                            checkpoint=checkpoint,
                            step_sequence=step_sequence,
                            inference_count=inference_count,
                            tool_count=tool_count,
                            residual_obligations=residual_obligations,
                        )
                # Keep the complete settled receipt frontier in every checkpoint.
                # Provider-native tool calls cannot update residual obligations in
                # the same response, so the next reasoning step needs all earlier
                # receipts to decide whether the admitted outcome is complete.
                prior_results = prior_results + tuple(results)
                useful_mutation = any(
                    proposal.tool_identity not in {"file.read", "git.status", "git.diff", "test.run", "build.run", "process.run", "preview.inspect"}
                    and result.condition is EffectCondition.SETTLED
                    for proposal, result in zip(response.tool_calls, results, strict=False)
                ) or any(
                    proposal.tool_identity == "file.write"
                    and result.condition is EffectCondition.SETTLED
                    for proposal, result in zip(response.tool_calls, results, strict=False)
                )
                ineffective_rounds = 0 if useful_mutation else ineffective_rounds + 1
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
            residual_obligations=residual_obligations,
        )

    @staticmethod
    def _control_result(
        *,
        control: ControlAction,
        checkpoint: CheckpointBundleRecord,
        step_sequence: int,
        inference_count: int,
        tool_count: int,
        residual_obligations: tuple[str, ...],
    ) -> KernelRunResult:
        terminal = None
        if control is ControlAction.STOP:
            terminal = AttemptTerminalOutcome.STOPPED
        elif control is ControlAction.CANCEL:
            terminal = AttemptTerminalOutcome.CANCELLED
        return KernelRunResult(
            runtime_mode=(
                ExecutionMode.PAUSED
                if control is ControlAction.PAUSE
                else ExecutionMode.FINISHED
            ),
            terminal_outcome=terminal,
            final_checkpoint_id=checkpoint.id,
            step_count=step_sequence,
            inference_submissions=inference_count,
            tool_effects=tool_count,
            summary=f"control request applied after process-tree termination: {control.value}",
            residual_obligations=residual_obligations,
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
        residual_obligations: tuple[str, ...],
    ) -> KernelRunResult:
        checkpoint = await self._checkpoint(
            binding=binding,
            worker_epoch=worker_epoch,
            step_sequence=step_sequence,
            working_plan=working_plan,
            tool_results=prior_results,
            residual_obligations=residual_obligations,
        )
        return KernelRunResult(
            runtime_mode=ExecutionMode.FINISHED,
            terminal_outcome=AttemptTerminalOutcome.BUDGET_EXHAUSTED,
            final_checkpoint_id=checkpoint.id,
            step_count=step_sequence,
            inference_submissions=inference_count,
            tool_effects=tool_count,
            summary="native execution resource envelope was exhausted",
            residual_obligations=residual_obligations,
        )
