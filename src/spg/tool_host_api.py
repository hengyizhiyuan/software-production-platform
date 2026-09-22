"""Internal-only ASGI boundary for the isolated native Tool Host process."""

from __future__ import annotations

import hmac
import os
from pathlib import Path
import subprocess
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException

from spg.domain.native_execution import (
    EffectCondition,
    NativeExecutionConflict,
    ToolExecutionRequest,
    ToolExecutionResult,
    canonical_digest,
)
from spg.infrastructure.executor_runtime.tool_host import (
    LocalNativeToolHost,
    NativeProcessSupervisor,
)
from spg.infrastructure.executor_runtime.landlock_sandbox import (
    LandlockProcessSandbox,
    LandlockUnavailable,
)
from spg.infrastructure.executor_runtime.local_storage import DeliveryReceiptSpool
from spg.infrastructure.executor_runtime.production_environment_tool_host import (
    ProductionEnvironmentNativeToolHost,
)
from spg.infrastructure.executor_runtime.workspace_host import WorkspaceMaterializationError
from spg.infrastructure.production_environment import (
    ContainerProductionEnvironmentProvider,
    DockerCliContainerRuntime,
)


def create_tool_host_application() -> FastAPI:
    root_value = os.environ.get("SPG_NATIVE_EXECUTOR_WORKSPACE_ROOT")
    token = os.environ.pop("SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN", None)
    if not root_value or not token:
        raise RuntimeError("native Tool Host requires workspace root and internal token")
    allowed_root = Path(root_value).resolve()
    allowed_root.mkdir(parents=True, exist_ok=True)
    receipt_spool = DeliveryReceiptSpool(
        Path(
            os.environ.get(
                "SPG_NATIVE_EXECUTOR_RECEIPT_SPOOL_ROOT",
                str(allowed_root.parent / "native-tool-receipts"),
            )
        ),
        max_bytes=int(
            os.environ.get("SPG_NATIVE_EXECUTOR_RECEIPT_SPOOL_MAX_BYTES", "134217728")
        ),
    )
    process_supervisor = NativeProcessSupervisor()
    production_workspace_volume = os.environ.get(
        "SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_WORKSPACE_VOLUME"
    )
    isolation_required = os.environ.get(
        "SPG_NATIVE_EXECUTOR_CONTAINER_ISOLATION_REQUIRED", "false"
    ).lower() in {"1", "true", "yes", "on"}
    process_sandbox = (
        LandlockProcessSandbox() if isolation_required else None
    )
    api = FastAPI(title="Watt Native Tool Host", docs_url=None, redoc_url=None)

    @api.get("/health")
    def health() -> dict[str, object]:
        isolation = (
            process_sandbox.readiness()
            if process_sandbox is not None
            else {"isolation": "in-process-test-only"}
        )
        return {"service": "native-tool-host", "status": "ready", **isolation}

    @api.post("/internal/native-tools/execute", response_model=ToolExecutionResult)
    async def execute(
        request: ToolExecutionRequest,
        x_watt_internal_token: str = Header(default=""),
    ) -> ToolExecutionResult:
        if not hmac.compare_digest(x_watt_internal_token, token):
            raise HTTPException(status_code=403, detail="internal Tool Host authority denied")
        workspace = Path(request.workspace.host_storage_id).resolve()
        if workspace != allowed_root and allowed_root not in workspace.parents:
            raise HTTPException(status_code=409, detail="workspace is outside Tool Host root")
        for mount in request.workspace.mounts:
            mount_path = Path(mount.host_path).resolve()
            if mount_path != workspace and workspace not in mount_path.parents:
                raise HTTPException(status_code=409, detail="workspace mount escapes execution workspace")
        request_digest = canonical_digest(request)
        existing = receipt_spool.get(request.delivery_id)
        if existing is not None:
            if existing.get("request_digest") != request_digest:
                raise HTTPException(
                    status_code=409,
                    detail="delivery identity has different durable meaning",
                )
            return ToolExecutionResult.model_validate(existing.get("result"))
        try:
            receipt_spool.ensure_capacity()
        except OSError as error:
            raise HTTPException(
                status_code=507,
                detail={
                    "condition": "RECEIPT_SPOOL_CAPACITY_EXHAUSTED",
                    "durable_ack": False,
                    "effect_admitted": False,
                    "message": str(error),
                },
            ) from None
        try:
            production_host = ProductionEnvironmentNativeToolHost.from_manifest(
                request.workspace,
                provider=ContainerProductionEnvironmentProvider(
                    DockerCliContainerRuntime(
                        workspace_volume=production_workspace_volume,
                        workspace_volume_root=allowed_root,
                    )
                ),
            )
            registry = (
                production_host.registry()
                if production_host is not None
                else LocalNativeToolHost(
                    workspace,
                    process_supervisor=process_supervisor,
                    process_sandbox=process_sandbox,
                ).registry()
            )
            result = await registry.execute(request)
        except (
            NativeExecutionConflict,
            WorkspaceMaterializationError,
            ValueError,
            OSError,
            LandlockUnavailable,
            subprocess.TimeoutExpired,
        ) as error:
            output = {
                "error_type": type(error).__name__,
                "message": str(error)[:1000],
                "effect_observed": False,
            }
            digest = canonical_digest(output)
            result = ToolExecutionResult(
                delivery_id=request.delivery_id,
                tool_identity=request.proposal.tool_identity,
                condition=EffectCondition.FAILED,
                output=output,
                output_digest=digest,
                evidence=({"type": "TOOL_REJECTION", "digest": digest},),
            )
        receipt_spool.put(
            request.delivery_id,
            request_digest=request_digest,
            result=result.model_dump(mode="json"),
        )
        return result

    @api.get(
        "/internal/native-tools/executions/{delivery_id}/receipt",
        response_model=ToolExecutionResult,
    )
    def receipt(
        delivery_id: UUID,
        x_watt_internal_token: str = Header(default=""),
    ) -> ToolExecutionResult:
        if not hmac.compare_digest(x_watt_internal_token, token):
            raise HTTPException(status_code=403, detail="internal Tool Host authority denied")
        stored = receipt_spool.get(delivery_id)
        if stored is None:
            raise HTTPException(status_code=404, detail="Tool receipt is unavailable")
        return ToolExecutionResult.model_validate(stored.get("result"))

    @api.post("/internal/native-tools/executions/{delivery_id}/cancel")
    async def cancel_execution(
        delivery_id: UUID,
        x_watt_internal_token: str = Header(default=""),
    ) -> dict[str, object]:
        if not hmac.compare_digest(x_watt_internal_token, token):
            raise HTTPException(status_code=403, detail="internal Tool Host authority denied")
        return await process_supervisor.terminate(delivery_id)

    return api
