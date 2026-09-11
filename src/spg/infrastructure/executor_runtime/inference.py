"""Inference adapters for the Watt-native Executor reasoning port."""

from __future__ import annotations

import asyncio
import json
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from spg.domain.native_execution import InferenceRequest, InferenceResponse


class InferenceAdapterError(RuntimeError):
    """Sanitized provider failure that never includes credentials."""


class InferenceResourceUnavailable(InferenceAdapterError):
    """A no-effect provider capacity/quota outcome that parks execution."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class OpenAIResponsesInferenceAdapter:
    """Configuration-driven OpenAI Responses API adapter; tools remain Watt-owned."""

    def __init__(
        self,
        *,
        model: str,
        api_key: Callable[[], str],
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 120,
    ) -> None:
        if not model:
            raise ValueError("native inference model is required")
        self.model = model
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        return await asyncio.to_thread(self._infer_sync, request)

    def _infer_sync(self, inference_request: InferenceRequest) -> InferenceResponse:
        key = self._api_key()
        if not key:
            raise InferenceAdapterError("OpenAI API credential is unavailable")
        schema = InferenceResponse.model_json_schema()
        payload = {
            "model": self.model,
            "store": False,
            "instructions": (
                "You are the reasoning capability inside Watt-native Executor. "
                "The supplied PWU contract and capability grants are authoritative. "
                "Choose HOW to advance the bounded objective. Never redefine WHAT NEXT, "
                "expand scope, or claim an unobserved effect. Return the required JSON object."
            ),
            "input": json.dumps(inference_request.model_dump(mode="json"), ensure_ascii=False),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "watt_native_executor_decision",
                    # Tool arguments and result claims are intentionally dynamic
                    # JSON maps. The Responses API strict-schema subset rejects
                    # such maps; Pydantic remains the authoritative validator
                    # for the returned provider-neutral contract.
                    "strict": False,
                    "schema": schema,
                }
            },
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{self.base_url}/responses",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                provider_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:1000]
            if error.code in {402, 429}:
                raise InferenceResourceUnavailable(
                    f"OpenAI Responses capacity is unavailable (HTTP {error.code}): {detail}",
                    retryable=error.code == 429,
                ) from None
            raise InferenceAdapterError(
                f"OpenAI Responses request failed with HTTP {error.code}: {detail}"
            ) from None
        except (URLError, TimeoutError) as error:
            raise InferenceAdapterError(f"OpenAI Responses request failed: {error}") from None
        text = provider_payload.get("output_text") or self._output_text(provider_payload)
        if not isinstance(text, str) or not text.strip():
            raise InferenceAdapterError("OpenAI Responses result contained no structured text")
        try:
            return InferenceResponse.model_validate_json(text)
        except Exception as error:
            raise InferenceAdapterError(
                f"OpenAI Responses result violated the native inference contract: {type(error).__name__}"
            ) from None

    @staticmethod
    def _output_text(payload: dict[str, object]) -> str | None:
        for item in payload.get("output", []):
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") == "output_text":
                    value = content.get("text")
                    if isinstance(value, str):
                        return value
        return None


class ScriptedInferenceAdapter:
    """Deterministic adapter for kernel qualification and fault injection."""

    def __init__(self, responses: tuple[InferenceResponse, ...]) -> None:
        self._responses = list(responses)
        self.requests: list[InferenceRequest] = []

    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        self.requests.append(request)
        if not self._responses:
            raise InferenceAdapterError("scripted inference response exhausted")
        return self._responses.pop(0)
