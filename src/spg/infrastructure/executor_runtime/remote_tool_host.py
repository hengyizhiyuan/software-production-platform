"""HTTP client for the separately deployed native Tool Host."""

from __future__ import annotations

import asyncio
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from spg.domain.native_execution import ToolExecutionRequest, ToolExecutionResult
from spg.executor.tools import PUBLIC_NATIVE_TOOL_CONTRACTS


class RemoteNativeToolHost:
    """Registry-compatible client; no database/provider credentials cross it."""

    def __init__(self, base_url: str, token: str, *, timeout_seconds: float = 180) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token
        self.timeout_seconds = timeout_seconds

    def contracts(self) -> tuple[dict[str, object], ...]:
        return PUBLIC_NATIVE_TOOL_CONTRACTS

    async def execute(self, execution: ToolExecutionRequest) -> ToolExecutionResult:
        try:
            return await asyncio.to_thread(self._execute_sync, execution)
        except asyncio.CancelledError:
            cancellation = await asyncio.shield(
                asyncio.to_thread(self._cancel_sync, execution.delivery_id)
            )
            if not cancellation.get("termination_proven", False):
                raise RuntimeError(
                    "native Tool Host could not prove process-tree termination"
                ) from None
            raise

    async def receipt(self, delivery_id) -> ToolExecutionResult | None:
        return await asyncio.to_thread(self._receipt_sync, delivery_id)

    def _execute_sync(self, execution: ToolExecutionRequest) -> ToolExecutionResult:
        request = Request(
            f"{self.base_url}/internal/native-tools/execute",
            data=execution.model_dump_json().encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "X-Watt-Internal-Token": self._token},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read().decode("utf-8")
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"native Tool Host rejected execution ({error.code}): {detail}") from None
        except (URLError, TimeoutError) as error:
            raise RuntimeError(f"native Tool Host unavailable: {error}") from None
        return ToolExecutionResult.model_validate_json(payload)

    def _cancel_sync(self, delivery_id) -> dict[str, object]:
        request = Request(
            f"{self.base_url}/internal/native-tools/executions/{delivery_id}/cancel",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json", "X-Watt-Internal-Token": self._token},
        )
        try:
            with urlopen(request, timeout=min(self.timeout_seconds, 10)) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError(f"native Tool Host cancellation failed: {error}") from None

    def _receipt_sync(self, delivery_id) -> ToolExecutionResult | None:
        request = Request(
            f"{self.base_url}/internal/native-tools/executions/{delivery_id}/receipt",
            method="GET",
            headers={"X-Watt-Internal-Token": self._token},
        )
        try:
            with urlopen(request, timeout=min(self.timeout_seconds, 10)) as response:
                return ToolExecutionResult.model_validate_json(
                    response.read().decode("utf-8")
                )
        except HTTPError as error:
            if error.code == 404:
                return None
            raise RuntimeError(
                f"native Tool Host receipt query failed ({error.code})"
            ) from None
        except (URLError, TimeoutError) as error:
            raise RuntimeError(f"native Tool Host unavailable: {error}") from None
