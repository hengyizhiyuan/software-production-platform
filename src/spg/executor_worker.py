"""Container entrypoint for one Watt-native Executor worker."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Callable
import json
from uuid import uuid4

from spg.application.bootstrap import bootstrap
from spg.config import Settings
from spg.domain.native_execution import (
    CapabilityGrant,
    EffectCondition,
    InferenceAction,
    InferenceRequest,
    ToolExecutionRequest,
    WorkerOffer,
    WorkingPlan,
    WorkspaceManifest,
    WorkspaceMount,
)
from spg.executor.kernel import NativeExecutorKernel
from spg.executor.tools import PUBLIC_NATIVE_TOOL_CONTRACTS
from spg.infrastructure.executor_runtime.inference import (
    DeepSeekResponsesInferenceAdapter,
    OpenAIResponsesInferenceAdapter,
    ResponsesInferenceAdapter,
)
from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.executor_runtime.remote_tool_host import RemoteNativeToolHost
from spg.infrastructure.executor_runtime.runtime_ports import DurableCheckpointPort, DurableKernelAudit
from spg.infrastructure.executor_runtime.worker import NativeExecutionWorker


ProviderFactory = Callable[[Settings], ResponsesInferenceAdapter]


def _required_model(settings: Settings) -> str:
    if not settings.native_executor_inference_model:
        raise RuntimeError("native Executor inference model is required")
    return settings.native_executor_inference_model


def _deepseek_adapter(settings: Settings) -> ResponsesInferenceAdapter:
    credential = settings.native_executor_deepseek_api_key
    if credential is None or not credential.get_secret_value():
        raise RuntimeError("native Executor DeepSeek credential is required")
    return DeepSeekResponsesInferenceAdapter(
        model=_required_model(settings),
        api_key=credential.get_secret_value,
        base_url=settings.native_executor_deepseek_base_url,
        timeout_seconds=settings.executor_timeout_seconds,
        reasoning_effort=settings.native_executor_inference_reasoning_effort,
    )


def _openai_adapter(settings: Settings) -> ResponsesInferenceAdapter:
    credential = settings.native_executor_openai_api_key
    if credential is None or not credential.get_secret_value():
        raise RuntimeError("native Executor OpenAI credential is required")
    return OpenAIResponsesInferenceAdapter(
        model=_required_model(settings),
        api_key=credential.get_secret_value,
        base_url=settings.native_executor_openai_base_url,
        timeout_seconds=settings.executor_timeout_seconds,
    )


_PROVIDER_FACTORIES: dict[str, ProviderFactory] = {
    "deepseek": _deepseek_adapter,
    "openai": _openai_adapter,
}


def configured_inference_adapter(settings: Settings) -> ResponsesInferenceAdapter:
    return _PROVIDER_FACTORIES[settings.native_executor_inference_provider](settings)


def provider_readiness_report(settings: Settings) -> dict[str, object]:
    """Validate worker Provider wiring without sending inference or admitting work."""

    adapter = configured_inference_adapter(settings)
    identity = adapter.identity
    return {
        "status": "READY",
        "provider": identity.provider,
        "provider_profile": identity.provider_profile,
        "model": identity.model,
        "base_url": identity.base_url,
        "reasoning_effort": identity.reasoning_effort,
        "credential_present": True,
        "provider_request_sent": False,
        "production_attempt_created": False,
    }


async def run_minimal_inference_probe(settings: Settings) -> dict[str, object]:
    """Issue exactly one Provider request without Work, PWU, database, or tools."""

    adapter = configured_inference_adapter(settings)
    response = await adapter.infer(
        InferenceRequest(
            attempt_id=uuid4(),
            session_id=uuid4(),
            step_sequence=1,
            objective=(
                "Provider transport qualification only. Do not request a tool or claim "
                "production. Return UNABLE_TO_COMPLETE with a concise smoke-test summary."
            ),
            working_plan=WorkingPlan(
                version=1,
                objective_reference="provider-qualification:p1",
                chosen_approach="Return one schema-valid transport smoke response.",
                approach_rationale="No production Work, tool, or persistent state is admitted.",
            ),
            context_facts=({"fact_type": "QUALIFICATION", "gate": "P1"},),
            available_tools=(),
            residual_obligations=(),
        )
    )
    observation = response.provider_observation
    if observation is None:
        raise RuntimeError("Provider response had no normalized observation")
    if observation.effective_model != observation.requested_model:
        raise RuntimeError(
            "Provider effective model did not match the admitted exact model"
        )
    return {
        "status": "PASS",
        "gate": "P1",
        "provider": observation.provider_identity,
        "requested_model": observation.requested_model,
        "effective_model": observation.effective_model,
        "provider_request_id": observation.provider_request_id,
        "response_status": observation.response_status,
        "usage": observation.usage.model_dump(mode="json") if observation.usage else None,
        "normalized_action": response.action.value,
        "production_attempt_created": False,
        "tool_execution_count": 0,
    }


async def run_tool_flow_probe(settings: Settings) -> dict[str, object]:
    """Run one bounded two-submission Provider/read-only Tool Host round trip."""

    if settings.native_executor_internal_token is None:
        raise RuntimeError("native Executor internal Tool Host token is required")
    adapter = configured_inference_adapter(settings)
    tools = RemoteNativeToolHost(
        settings.native_executor_tool_host_url,
        settings.native_executor_internal_token.get_secret_value(),
    )
    read_contract = next(
        contract
        for contract in PUBLIC_NATIVE_TOOL_CONTRACTS
        if contract["identity"] == "file.read"
    )
    attempt_id = uuid4()
    session_id = uuid4()
    work_id = uuid4()
    pwu_id = uuid4()
    plan = WorkingPlan(
        version=1,
        objective_reference="provider-qualification:p2",
        chosen_approach="Read the isolated qualification fixture once.",
        approach_rationale="This proves Provider proposal and Tool Host correlation.",
    )
    first = await adapter.infer(
        InferenceRequest(
            attempt_id=attempt_id,
            session_id=session_id,
            step_sequence=1,
            objective=(
                "Provider tool qualification only. Call the one supplied file.read "
                "function exactly once with path qualification.txt. Do not claim production."
            ),
            working_plan=plan,
            context_facts=({"fact_type": "QUALIFICATION", "gate": "P2"},),
            available_tools=(read_contract,),
            residual_obligations=("observe qualification fixture",),
        )
    )
    first_observation = first.provider_observation
    if (
        first_observation is None
        or first_observation.effective_model != adapter.identity.model
    ):
        raise RuntimeError("P2 proposal response did not prove the exact DeepSeek model")
    if first.action is not InferenceAction.CONTINUE or len(first.tool_calls) != 1:
        raise RuntimeError("P2 Provider did not produce exactly one tool proposal")
    proposal = first.tool_calls[0]
    if proposal.tool_identity != "file.read" or proposal.arguments != {
        "path": "qualification.txt"
    }:
        raise RuntimeError("P2 Provider proposal did not match the harmless read contract")

    workspace_path = settings.native_executor_workspace_root / "provider-p2"
    workspace = WorkspaceManifest(
        workspace_id=uuid4(),
        work_id=work_id,
        pwu_id=pwu_id,
        attempt_id=attempt_id,
        source_vector_digest="0" * 64,
        host_storage_id=str(workspace_path),
        environment_profile_digest="0" * 64,
        mounts=(
            WorkspaceMount(
                mount_id="qualification",
                host_path=str(workspace_path),
                container_path="/workspace/qualification",
                writable=True,
                write_scope=(),
                forbidden_paths=(".git",),
            ),
        ),
        evidence_namespace="provider-qualification:p2",
        retention_policy="ephemeral-qualification",
    )
    tool_request = ToolExecutionRequest(
        delivery_id=uuid4(),
        attempt_id=attempt_id,
        worker_epoch=1,
        step_id=uuid4(),
        proposal=proposal,
        capability_grants=(
            CapabilityGrant(
                identity="file.read",
                version="1",
                scope={"paths": ["qualification.txt"]},
            ),
        ),
        workspace=workspace,
    )
    tool_result = await tools.execute(tool_request)
    if tool_result.condition is not EffectCondition.SETTLED:
        raise RuntimeError("P2 harmless read did not settle")

    final = await adapter.infer(
        InferenceRequest(
            attempt_id=attempt_id,
            session_id=session_id,
            step_sequence=2,
            objective=(
                "Provider tool qualification only. Use the supplied settled read result, "
                "then return UNABLE_TO_COMPLETE because no production was admitted."
            ),
            working_plan=first.working_plan,
            context_facts=({"fact_type": "QUALIFICATION", "gate": "P2"},),
            available_tools=(),
            residual_obligations=(),
            previous_results=(tool_result.model_dump(mode="json"),),
        )
    )
    final_observation = final.provider_observation
    if (
        final_observation is None
        or final_observation.effective_model != adapter.identity.model
    ):
        raise RuntimeError("P2 final response did not prove the exact DeepSeek model")
    if final.action is InferenceAction.CONTINUE:
        raise RuntimeError("P2 final response requested an unadmitted additional tool")
    return {
        "status": "PASS",
        "gate": "P2",
        "provider": first_observation.provider_identity,
        "effective_model": first_observation.effective_model,
        "provider_request_ids": [
            first_observation.provider_request_id,
            final_observation.provider_request_id,
        ],
        "provider_submission_count": 2,
        "provider_call_id": proposal.provider_call_id,
        "normalized_tool": proposal.tool_identity,
        "tool_delivery_id": str(tool_result.delivery_id),
        "tool_condition": tool_result.condition.value,
        "tool_output_digest": tool_result.output_digest,
        "final_action": final.action.value,
        "usage": [
            first_observation.usage.model_dump(mode="json")
            if first_observation.usage
            else None,
            final_observation.usage.model_dump(mode="json")
            if final_observation.usage
            else None,
        ],
        "production_attempt_created": False,
        "mutation_count": 0,
    }


async def run_worker() -> None:
    application = bootstrap()
    settings = application.settings
    if not settings.native_executor_enabled:
        raise RuntimeError("SPG_NATIVE_EXECUTOR_ENABLED must be true")
    if settings.native_executor_internal_token is None:
        raise RuntimeError("native Executor internal Tool Host token is required")
    database = application.persistence()
    runtime = application.native_executor_runtime(database)
    storage = ContentAddressedStorage(settings.native_executor_storage_root / "checkpoints")
    remote_tools = RemoteNativeToolHost(
        settings.native_executor_tool_host_url,
        settings.native_executor_internal_token.get_secret_value(),
    )
    inference = configured_inference_adapter(settings)

    def kernel_factory(grant):
        with database.unit_of_work() as uow:
            binding = NativeExecutionStore(uow.session).attempt_binding(grant.allocation.attempt_id)
        return NativeExecutorKernel(
            inference=inference,
            tools=remote_tools,
            checkpoints=DurableCheckpointPort(
                database, storage, attempt_id=binding.attempt_id,
                session_id=binding.session_id, worker_epoch=grant.allocation.lease_epoch,
            ),
            audit=DurableKernelAudit(
                database, attempt_id=binding.attempt_id,
                session_id=binding.session_id, pwu_id=binding.pwu_id,
                envelope_id=binding.resource_envelope_id,
            ),
        )

    worker = NativeExecutionWorker(runtime, kernel_factory)
    offer = WorkerOffer(
        worker_id=settings.native_executor_worker_id,
        worker_profile=settings.native_executor_worker_profile,
        provider_profiles=(settings.native_executor_provider_profile,),
        resource_profiles=(settings.native_executor_resource_profile,),
        capability_identities=(
            "file.read", "file.write", "process.run", "git.status", "git.diff",
            "test.run", "build.run", "dependency.sync", "preview.inspect",
        ),
    )
    try:
        while True:
            worked = await worker.run_once(offer)
            if not worked:
                await asyncio.sleep(settings.native_executor_poll_seconds)
    finally:
        database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-readiness", action="store_true")
    parser.add_argument("--probe-inference", action="store_true")
    parser.add_argument("--probe-tool-flow", action="store_true")
    arguments = parser.parse_args()
    if arguments.check_readiness:
        settings = Settings()
        if not settings.native_executor_enabled:
            raise RuntimeError("SPG_NATIVE_EXECUTOR_ENABLED must be true")
        print(json.dumps(provider_readiness_report(settings), sort_keys=True))
        return
    if arguments.probe_inference:
        settings = Settings()
        if not settings.native_executor_enabled:
            raise RuntimeError("SPG_NATIVE_EXECUTOR_ENABLED must be true")
        print(json.dumps(asyncio.run(run_minimal_inference_probe(settings)), sort_keys=True))
        return
    if arguments.probe_tool_flow:
        settings = Settings()
        if not settings.native_executor_enabled:
            raise RuntimeError("SPG_NATIVE_EXECUTOR_ENABLED must be true")
        print(json.dumps(asyncio.run(run_tool_flow_probe(settings)), sort_keys=True))
        return
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
