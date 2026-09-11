"""Container entrypoint for one Watt-native Executor worker."""

from __future__ import annotations

import asyncio

from spg.application.bootstrap import bootstrap
from spg.domain.native_execution import WorkerOffer
from spg.executor.kernel import NativeExecutorKernel
from spg.infrastructure.executor_runtime.inference import OpenAIResponsesInferenceAdapter
from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.executor_runtime.remote_tool_host import RemoteNativeToolHost
from spg.infrastructure.executor_runtime.runtime_ports import DurableCheckpointPort, DurableKernelAudit
from spg.infrastructure.executor_runtime.worker import NativeExecutionWorker


async def run_worker() -> None:
    application = bootstrap()
    settings = application.settings
    if not settings.native_executor_enabled:
        raise RuntimeError("SPG_NATIVE_EXECUTOR_ENABLED must be true")
    if not settings.native_executor_inference_model or settings.native_executor_openai_api_key is None:
        raise RuntimeError("native Executor inference model and credential are required")
    if settings.native_executor_internal_token is None:
        raise RuntimeError("native Executor internal Tool Host token is required")
    database = application.persistence()
    runtime = application.native_executor_runtime(database)
    storage = ContentAddressedStorage(settings.native_executor_storage_root / "checkpoints")
    remote_tools = RemoteNativeToolHost(
        settings.native_executor_tool_host_url,
        settings.native_executor_internal_token.get_secret_value(),
    )
    inference = OpenAIResponsesInferenceAdapter(
        model=settings.native_executor_inference_model,
        api_key=settings.native_executor_openai_api_key.get_secret_value,
        base_url=settings.native_executor_openai_base_url,
        timeout_seconds=settings.executor_timeout_seconds,
    )

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
        provider_profiles=("openai-responses",),
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
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
