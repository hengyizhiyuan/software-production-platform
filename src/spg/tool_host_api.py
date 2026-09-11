"""Internal-only ASGI boundary for the isolated native Tool Host process."""

from __future__ import annotations

import hmac
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException

from spg.domain.native_execution import ToolExecutionRequest, ToolExecutionResult
from spg.infrastructure.executor_runtime.tool_host import LocalNativeToolHost


def create_tool_host_application() -> FastAPI:
    root_value = os.environ.get("SPG_NATIVE_EXECUTOR_WORKSPACE_ROOT")
    token = os.environ.pop("SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN", None)
    if not root_value or not token:
        raise RuntimeError("native Tool Host requires workspace root and internal token")
    allowed_root = Path(root_value).resolve()
    allowed_root.mkdir(parents=True, exist_ok=True)
    api = FastAPI(title="Watt Native Tool Host", docs_url=None, redoc_url=None)

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"service": "native-tool-host", "status": "ready"}

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
        return await LocalNativeToolHost(workspace).registry().execute(request)

    return api
