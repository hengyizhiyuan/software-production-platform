"""Responses transport shared by Watt model consumers below role contracts."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from enum import StrEnum
import json
from threading import Lock
from time import monotonic
from typing import Any

import httpx2

from spg.domain.model_runtime import (
    ModelCapabilities,
    ModelProfile,
    ModelProvider,
    ModelStageCallback,
    ModelTiming,
    ModelUsage,
    StructuredModelResult,
)


class ModelFailureKind(StrEnum):
    AUTHENTICATION = "AUTHENTICATION"
    BALANCE_OR_QUOTA = "BALANCE_OR_QUOTA"
    CAPACITY_OR_RATE_LIMIT = "CAPACITY_OR_RATE_LIMIT"
    INVALID_MODEL_OR_REQUEST = "INVALID_MODEL_OR_REQUEST"
    PROTOCOL_OR_SCHEMA = "PROTOCOL_OR_SCHEMA"
    TIMEOUT_OR_NETWORK = "TIMEOUT_OR_NETWORK"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"


class ModelProviderError(RuntimeError):
    """Credential-safe normalized Provider failure."""

    def __init__(
        self,
        kind: ModelFailureKind,
        message: str,
        *,
        request_sent: bool | None,
        usage_unknown: bool,
        retryable: bool,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.request_sent = request_sent
        self.usage_unknown = usage_unknown
        self.retryable = retryable


class ResponsesModelAdapter:
    """Reusable keep-alive streaming mechanics for Responses-style APIs."""

    provider = ModelProvider.OPENAI
    capabilities = ModelCapabilities(
        structured_json_schema=True,
        streaming=True,
        usage=True,
        cached_usage=True,
        reasoning_usage=True,
    )

    def __init__(
        self,
        *,
        api_key: Callable[[], str],
        base_url: str,
        client: httpx2.Client | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("Provider base URL is required")
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx2.Client(
            base_url=self.base_url,
            timeout=120,
            limits=httpx2.Limits(
                max_connections=8,
                max_keepalive_connections=4,
                keepalive_expiry=60,
            ),
        )
        self._owns_client = client is None
        self._request_lock = Lock()

    def readiness(self, profile: ModelProfile) -> dict[str, object]:
        key = self._api_key()
        if not key:
            raise ModelProviderError(
                ModelFailureKind.AUTHENTICATION,
                f"{self.provider.value} API credential is unavailable",
                request_sent=False,
                usage_unknown=False,
                retryable=False,
            )
        if profile.provider is not self.provider:
            raise ValueError("Profile Provider does not match adapter")
        if not profile.model.strip():
            raise ValueError("Profile model is required")
        return {
            "provider": self.provider.value,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
            "base_url": self.base_url,
            "credential_configured": True,
            "provider_request_sent": False,
        }

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def generate(
        self,
        *,
        profile: ModelProfile,
        instructions: str,
        input_text: str,
        output_schema: dict[str, object],
        on_output_delta=None,
        on_stage: ModelStageCallback | None = None,
    ) -> StructuredModelResult:
        if profile.provider is not self.provider:
            raise ValueError("Profile Provider does not match adapter")
        key = self._api_key()
        if not key:
            raise ModelProviderError(
                ModelFailureKind.AUTHENTICATION,
                f"{self.provider.value} API credential is unavailable",
                request_sent=False,
                usage_unknown=False,
                retryable=False,
            )
        started = monotonic()
        sent_at: float | None = None
        first_event_at: float | None = None
        first_token_at: float | None = None
        output_parts: list[str] = []
        final_payload: dict[str, Any] | None = None
        payload = self._payload(
            profile=profile,
            instructions=instructions,
            input_text=input_text,
            output_schema=output_schema,
        )

        def stage(name: str) -> None:
            if on_stage is not None:
                on_stage(name)

        stage("provider_request_queued")
        try:
            # The role-level WIC worker is sequential today. This lock also keeps
            # a shared HTTP/1.1 connection from interleaving future consumers.
            with self._request_lock:
                sent_at = monotonic()
                stage("provider_request_sent")
                with self._client.stream(
                    "POST",
                    "/responses",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=profile.timeout_seconds,
                ) as response:
                    if response.status_code >= 400:
                        self._raise_http_error(response, key)
                    stage("provider_response_accepted")
                    for line in response.iter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if not data:
                            continue
                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError as error:
                            raise ModelProviderError(
                                ModelFailureKind.MALFORMED_RESPONSE,
                                f"{self.provider.value} stream contained invalid JSON",
                                request_sent=True,
                                usage_unknown=True,
                                retryable=False,
                            ) from error
                        if first_event_at is None:
                            first_event_at = monotonic()
                            stage("provider_first_response_event")
                        event_type = event.get("type")
                        if event_type == "response.output_text.delta":
                            delta = event.get("delta")
                            if isinstance(delta, str) and delta:
                                if first_token_at is None:
                                    first_token_at = monotonic()
                                    stage("provider_first_token")
                                output_parts.append(delta)
                                if on_output_delta is not None:
                                    on_output_delta(delta)
                        elif event_type in {
                            "response.completed",
                            "response.incomplete",
                            "response.failed",
                        }:
                            candidate = event.get("response")
                            if isinstance(candidate, dict):
                                final_payload = candidate
        except ModelProviderError:
            raise
        except httpx2.TimeoutException as error:
            raise ModelProviderError(
                ModelFailureKind.TIMEOUT_OR_NETWORK,
                f"{self.provider.value} request timed out",
                request_sent=True,
                usage_unknown=True,
                retryable=True,
            ) from error
        except httpx2.HTTPError as error:
            raise ModelProviderError(
                ModelFailureKind.TIMEOUT_OR_NETWORK,
                f"{self.provider.value} transport failed: {type(error).__name__}",
                request_sent=True,
                usage_unknown=True,
                retryable=True,
            ) from error

        completed_at = monotonic()
        if final_payload is None:
            raise ModelProviderError(
                ModelFailureKind.PROTOCOL_OR_SCHEMA,
                f"{self.provider.value} stream ended without a terminal response",
                request_sent=True,
                usage_unknown=True,
                retryable=False,
            )
        status = final_payload.get("status")
        if status != "completed":
            raise ModelProviderError(
                ModelFailureKind.PROTOCOL_OR_SCHEMA,
                f"{self.provider.value} response status was {status or 'unknown'}",
                request_sent=True,
                usage_unknown=self._usage(final_payload).unknown,
                retryable=False,
            )
        output_text = "".join(output_parts) or self._output_text(final_payload)
        if not output_text.strip():
            raise ModelProviderError(
                ModelFailureKind.MALFORMED_RESPONSE,
                f"{self.provider.value} response contained no output text",
                request_sent=True,
                usage_unknown=self._usage(final_payload).unknown,
                retryable=False,
            )
        return StructuredModelResult(
            output_text=output_text,
            provider=self.provider,
            requested_model=profile.model,
            effective_model=(
                str(final_payload["model"])
                if isinstance(final_payload.get("model"), str)
                else None
            ),
            request_id=(
                str(final_payload["id"])
                if isinstance(final_payload.get("id"), str)
                else None
            ),
            usage=self._usage(final_payload),
            timing=ModelTiming(
                request_sent_seconds=(
                    None if sent_at is None else sent_at - started
                ),
                first_response_event_seconds=(
                    None if first_event_at is None else first_event_at - started
                ),
                first_token_seconds=(
                    None if first_token_at is None else first_token_at - started
                ),
                completed_seconds=completed_at - started,
            ),
            retry_count=0,
        )

    def _payload(
        self,
        *,
        profile: ModelProfile,
        instructions: str,
        input_text: str,
        output_schema: dict[str, object],
    ) -> dict[str, object]:
        schema = self._compact_schema(output_schema)
        payload: dict[str, object] = {
            "model": profile.model,
            "instructions": instructions,
            "input": input_text,
            "stream": True,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "watt_collaboration_result",
                    "schema": schema,
                }
            },
        }
        if profile.reasoning_effort is not None:
            payload["reasoning"] = {"effort": profile.reasoning_effort}
        if profile.max_output_tokens is not None:
            payload["max_output_tokens"] = profile.max_output_tokens
        return payload

    @staticmethod
    def _compact_schema(schema: dict[str, object]) -> dict[str, object]:
        """Remove annotation-only JSON Schema text without weakening constraints."""

        compact = deepcopy(schema)

        def visit(value: object) -> None:
            if isinstance(value, dict):
                for key in ("title", "description", "examples", "default", "$comment"):
                    value.pop(key, None)
                for nested in value.values():
                    visit(nested)
            elif isinstance(value, list):
                for nested in value:
                    visit(nested)

        visit(compact)
        return compact

    def _raise_http_error(self, response: httpx2.Response, key: str) -> None:
        detail = response.read().decode("utf-8", errors="replace")[:1000]
        detail = detail.replace(key, "<redacted>")
        status = response.status_code
        if status in {401, 403}:
            kind = ModelFailureKind.AUTHENTICATION
            retryable = False
        elif status == 402:
            kind = ModelFailureKind.BALANCE_OR_QUOTA
            retryable = False
        elif status in {429, 500, 503}:
            kind = ModelFailureKind.CAPACITY_OR_RATE_LIMIT
            retryable = True
        elif status in {400, 404, 409, 422}:
            kind = ModelFailureKind.INVALID_MODEL_OR_REQUEST
            retryable = False
        else:
            kind = ModelFailureKind.PROTOCOL_OR_SCHEMA
            retryable = False
        raise ModelProviderError(
            kind,
            f"{self.provider.value} request failed with HTTP {status}: {detail}",
            request_sent=True,
            usage_unknown=status >= 500,
            retryable=retryable,
        )

    @staticmethod
    def _output_text(payload: dict[str, Any]) -> str:
        direct = payload.get("output_text")
        if isinstance(direct, str):
            return direct
        parts: list[str] = []
        output = payload.get("output")
        if not isinstance(output, list):
            return ""
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str):
                        parts.append(text)
        return "".join(parts)

    @staticmethod
    def _usage(payload: dict[str, Any]) -> ModelUsage:
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return ModelUsage(unknown=True)
        input_details = usage.get("input_tokens_details")
        output_details = usage.get("output_tokens_details")

        def integer(container: object, key: str) -> int | None:
            if not isinstance(container, dict):
                return None
            value = container.get(key)
            return value if isinstance(value, int) and not isinstance(value, bool) else None

        return ModelUsage(
            input_tokens=integer(usage, "input_tokens"),
            output_tokens=integer(usage, "output_tokens"),
            cached_tokens=integer(input_details, "cached_tokens"),
            reasoning_tokens=integer(output_details, "reasoning_tokens"),
            total_tokens=integer(usage, "total_tokens"),
            unknown=False,
        )


class DeepSeekResponsesModelAdapter(ResponsesModelAdapter):
    """DeepSeek protocol choices stay below Watt role-specific contracts."""

    provider = ModelProvider.DEEPSEEK
