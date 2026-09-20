"""Inference adapters for the Watt-native Executor reasoning port."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from http.client import IncompleteRead, RemoteDisconnected
import json
from socket import timeout as SocketTimeout
from time import monotonic
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from spg.domain.native_execution import (
    InferenceAction,
    InferenceDecisionRejected,
    InferenceProviderObservation,
    InferenceRequest,
    InferenceResponse,
    InferenceTransportObservation,
    InferenceUsage,
    ToolCallProposal,
)


class InferenceFailureCode(StrEnum):
    CONNECT_FAILURE = "CONNECT_FAILURE"
    TIMEOUT = "TIMEOUT"
    UPSTREAM_DISCONNECT = "UPSTREAM_DISCONNECT"
    INCOMPLETE_RESPONSE = "INCOMPLETE_RESPONSE"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    INVALID_MODEL_RESPONSE = "INVALID_MODEL_RESPONSE"


class InferenceAdapterError(RuntimeError):
    """Sanitized provider failure that never includes credentials."""

    def __init__(
        self,
        message: str,
        *,
        failure_code: InferenceFailureCode = InferenceFailureCode.INVALID_MODEL_RESPONSE,
        transport_diagnostics: dict[str, object] | None = None,
    ) -> None:
        RuntimeError.__init__(self, message)
        self.failure_code = failure_code.value
        self.transport_diagnostics = dict(transport_diagnostics or {})


class InferenceAdapterDecisionRejected(InferenceAdapterError, InferenceDecisionRejected):
    """Observed Provider output rejected before any proposed effect can start."""

    def __init__(
        self,
        reason_code: str,
        message: str,
        *,
        validation_issues: tuple[dict[str, object], ...] = (),
    ) -> None:
        InferenceAdapterError.__init__(
            self,
            message,
            failure_code=InferenceFailureCode.INVALID_MODEL_RESPONSE,
        )
        self.reason_code = reason_code
        self.validation_issues = validation_issues


class InferenceResourceUnavailable(InferenceAdapterError):
    """A no-effect provider capacity/quota outcome that parks execution."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool,
        request_sent: bool | None = True,
        transport_diagnostics: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message,
            failure_code=InferenceFailureCode.PROVIDER_ERROR,
            transport_diagnostics=transport_diagnostics,
        )
        self.retryable = retryable
        self.request_sent = request_sent


class InferenceTransportUnknown(InferenceAdapterError):
    """A request may have reached the Provider, but no complete response was observed."""

    response_unknown = True

    def __init__(
        self,
        message: str,
        *,
        failure_code: InferenceFailureCode = InferenceFailureCode.UPSTREAM_DISCONNECT,
        transport_diagnostics: dict[str, object] | None = None,
        request_sent: bool | None = True,
        retryable: bool = True,
    ) -> None:
        diagnostics = transport_diagnostics or {
            "mode": "unknown",
            "response_headers_received": False,
            "response_status_code": None,
            "headers_elapsed_ms": None,
            "first_byte_elapsed_ms": None,
            "elapsed_ms": 0,
            "received_bytes": 0,
            "received_events": 0,
            "terminal_received": False,
            "syntactically_complete": False,
            "failure_code": failure_code.value,
        }
        super().__init__(
            message,
            failure_code=failure_code,
            transport_diagnostics=diagnostics,
        )
        self.request_sent = request_sent
        self.retryable = retryable


@dataclass(slots=True)
class _TransportTracker:
    mode: str
    started_at: float = field(default_factory=monotonic)
    response_headers_received: bool = False
    response_status_code: int | None = None
    headers_elapsed_ms: int | None = None
    first_byte_elapsed_ms: int | None = None
    received_bytes: int = 0
    received_events: int = 0
    terminal_received: bool = False
    syntactically_complete: bool = False

    def observe_headers(self, status: int | None) -> None:
        self.response_headers_received = True
        self.response_status_code = status
        self.headers_elapsed_ms = self._elapsed_ms()

    def observe_bytes(self, count: int) -> None:
        if count <= 0:
            return
        if self.first_byte_elapsed_ms is None:
            self.first_byte_elapsed_ms = self._elapsed_ms()
        self.received_bytes += count

    def diagnostics(
        self,
        failure_code: InferenceFailureCode | None = None,
    ) -> dict[str, object]:
        return {
            "mode": self.mode,
            "response_headers_received": self.response_headers_received,
            "response_status_code": self.response_status_code,
            "headers_elapsed_ms": self.headers_elapsed_ms,
            "first_byte_elapsed_ms": self.first_byte_elapsed_ms,
            "elapsed_ms": self._elapsed_ms(),
            "received_bytes": self.received_bytes,
            "received_events": self.received_events,
            "terminal_received": self.terminal_received,
            "syntactically_complete": self.syntactically_complete,
            "failure_code": failure_code.value if failure_code is not None else None,
        }

    def observation(self) -> InferenceTransportObservation:
        return InferenceTransportObservation.model_validate(self.diagnostics())

    def _elapsed_ms(self) -> int:
        return max(0, round((monotonic() - self.started_at) * 1000))


@dataclass(frozen=True, slots=True)
class InferenceAdapterIdentity:
    provider: str
    provider_profile: str
    model: str
    base_url: str
    reasoning_effort: str | None


class _TerminalInferenceDecision(BaseModel):
    """Provider-owned terminal fields; Watt retains the current working plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: InferenceAction
    summary: str = Field(min_length=1)
    result_claim: dict[str, Any] | None = None
    residual_obligations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_terminal_payload(self) -> "_TerminalInferenceDecision":
        if self.action is InferenceAction.CONTINUE:
            raise ValueError("CONTINUE must use an API function call")
        if self.action is InferenceAction.RESULT_READY and self.result_claim is None:
            raise ValueError("RESULT_READY requires a result claim")
        return self


class ResponsesInferenceAdapter:
    """Shared verified mechanics for stateless Responses-compatible providers."""

    provider_identity = "responses-compatible"
    provider_profile = "responses-compatible"
    uses_provider_tools = False
    uses_streaming = False
    includes_store_flag = False
    includes_non_strict_schema_flag = False

    def __init__(
        self,
        *,
        model: str,
        api_key: Callable[[], str],
        base_url: str,
        timeout_seconds: float = 120,
        reasoning_effort: str | None = None,
    ) -> None:
        if not model:
            raise ValueError("native inference model is required")
        if not base_url:
            raise ValueError("native inference base URL is required")
        self.model = model
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.reasoning_effort = reasoning_effort
        self.last_observation: InferenceProviderObservation | None = None

    @property
    def identity(self) -> InferenceAdapterIdentity:
        return InferenceAdapterIdentity(
            provider=self.provider_identity,
            provider_profile=(
                f"{self.provider_profile}:{self.model}:"
                f"{self.reasoning_effort or 'none'}"
            ),
            model=self.model,
            base_url=self.base_url,
            reasoning_effort=self.reasoning_effort,
        )

    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        return await asyncio.to_thread(self._infer_sync, request)

    def _infer_sync(self, inference_request: InferenceRequest) -> InferenceResponse:
        # A caller may reuse one adapter across several steps.  Clear the prior
        # observation so an exception can never be attributed to an older HTTP
        # response by metering/audit wrappers.
        self.last_observation = None
        key = self._api_key()
        if not key:
            raise InferenceAdapterError(
                f"{self.provider_identity} API credential is unavailable"
            )
        payload, provider_tool_names = self._request_payload(inference_request)
        if self.uses_streaming:
            payload["stream"] = True
        tracker = _TransportTracker(
            mode="stream" if self.uses_streaming else "non_stream"
        )
        request = Request(
            f"{self.base_url}/responses",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Accept": (
                    "text/event-stream" if self.uses_streaming else "application/json"
                ),
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                tracker.observe_headers(getattr(response, "status", None))
                provider_payload = (
                    self._read_streamed_payload(response, tracker)
                    if self.uses_streaming
                    else self._read_json_payload(response, tracker)
                )
        except HTTPError as error:
            tracker.observe_headers(error.code)
            detail = error.read().decode("utf-8", errors="replace")[:1000]
            detail = detail.replace(key, "<redacted>")
            if error.code in {402, 429, 500, 503}:
                raise InferenceResourceUnavailable(
                    f"{self.provider_identity} Responses resource is unavailable "
                    f"(HTTP {error.code}): {detail}",
                    retryable=error.code in {429, 500, 503},
                    transport_diagnostics=tracker.diagnostics(
                        InferenceFailureCode.PROVIDER_ERROR
                    ),
                ) from None
            raise InferenceAdapterError(
                f"{self.provider_identity} Responses request failed with HTTP "
                f"{error.code}: {detail}",
                failure_code=InferenceFailureCode.PROVIDER_ERROR,
                transport_diagnostics=tracker.diagnostics(
                    InferenceFailureCode.PROVIDER_ERROR
                ),
            ) from None
        except IncompleteRead as error:
            received_bytes = len(error.partial or b"")
            tracker.observe_bytes(received_bytes)
            expected_more = error.expected
            expected_detail = (
                "unknown"
                if expected_more is None
                else str(expected_more)
            )
            raise InferenceTransportUnknown(
                f"{self.provider_identity} Responses transport failed: "
                f"IncompleteRead (received_bytes={received_bytes}, "
                f"expected_more_bytes={expected_detail})",
                failure_code=InferenceFailureCode.INCOMPLETE_RESPONSE,
                transport_diagnostics=tracker.diagnostics(
                    InferenceFailureCode.INCOMPLETE_RESPONSE
                ),
                request_sent=True,
            ) from None
        except (TimeoutError, SocketTimeout) as error:
            raise InferenceTransportUnknown(
                f"{self.provider_identity} Responses transport failed: "
                f"{type(error).__name__}",
                failure_code=InferenceFailureCode.TIMEOUT,
                transport_diagnostics=tracker.diagnostics(
                    InferenceFailureCode.TIMEOUT
                ),
                request_sent=tracker.response_headers_received or None,
            ) from None
        except RemoteDisconnected as error:
            raise InferenceTransportUnknown(
                f"{self.provider_identity} Responses transport failed: "
                f"{type(error).__name__}",
                failure_code=InferenceFailureCode.UPSTREAM_DISCONNECT,
                transport_diagnostics=tracker.diagnostics(
                    InferenceFailureCode.UPSTREAM_DISCONNECT
                ),
                request_sent=True,
            ) from None
        except URLError as error:
            failure_code = (
                InferenceFailureCode.TIMEOUT
                if isinstance(error.reason, (TimeoutError, SocketTimeout))
                else InferenceFailureCode.CONNECT_FAILURE
            )
            raise InferenceTransportUnknown(
                f"{self.provider_identity} Responses transport failed: "
                f"{failure_code.value}",
                failure_code=failure_code,
                transport_diagnostics=tracker.diagnostics(failure_code),
                request_sent=False if failure_code is InferenceFailureCode.CONNECT_FAILURE else None,
            ) from None
        except InferenceAdapterError:
            raise

        if not isinstance(provider_payload, dict):
            raise InferenceAdapterError(
                f"{self.provider_identity} Responses result was not an object",
                failure_code=InferenceFailureCode.INVALID_MODEL_RESPONSE,
                transport_diagnostics=tracker.diagnostics(
                    InferenceFailureCode.INVALID_MODEL_RESPONSE
                ),
            )
        observation = self._observation(provider_payload).model_copy(
            update={"transport": tracker.observation()}
        )
        self.last_observation = observation
        status = provider_payload.get("status")
        if isinstance(status, str) and status != "completed":
            raise InferenceAdapterDecisionRejected(
                "RESPONSE_NOT_COMPLETED",
                f"{self.provider_identity} Responses result status was {status}"
            )

        provider_calls = self._provider_tool_calls(
            provider_payload, provider_tool_names
        )
        if provider_calls:
            decision = InferenceResponse(
                action=InferenceAction.CONTINUE,
                summary="Execute the provider-proposed tools through the Watt Tool Host.",
                working_plan=inference_request.working_plan,
                tool_calls=provider_calls,
                residual_obligations=inference_request.residual_obligations,
            )
        else:
            text = provider_payload.get("output_text") or self._output_text(provider_payload)
            if not isinstance(text, str) or not text.strip():
                raise InferenceAdapterDecisionRejected(
                    "STRUCTURED_TEXT_MISSING",
                    f"{self.provider_identity} Responses result contained no structured text"
                )
            try:
                decision = self._parse_text_decision(text, inference_request)
            except (ValidationError, json.JSONDecodeError) as error:
                raise InferenceAdapterDecisionRejected(
                    "NATIVE_DECISION_SCHEMA_REJECTED",
                    f"{self.provider_identity} Responses result violated the native "
                    f"inference contract: {type(error).__name__}",
                    validation_issues=self._safe_validation_issues(error),
                ) from None
        return decision.model_copy(update={"provider_observation": observation})

    def _read_json_payload(
        self,
        response: object,
        tracker: _TransportTracker,
    ) -> dict[str, object]:
        raw_payload = response.read()
        tracker.observe_bytes(len(raw_payload))
        if not raw_payload:
            raise InferenceTransportUnknown(
                f"{self.provider_identity} Responses transport returned an empty body",
                failure_code=InferenceFailureCode.EMPTY_RESPONSE,
                transport_diagnostics=tracker.diagnostics(
                    InferenceFailureCode.EMPTY_RESPONSE
                ),
                request_sent=True,
            )
        try:
            provider_payload = json.loads(raw_payload.decode("utf-8").strip())
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InferenceAdapterError(
                f"{self.provider_identity} Responses result was not valid JSON: "
                f"{type(error).__name__}",
                failure_code=InferenceFailureCode.INVALID_MODEL_RESPONSE,
                transport_diagnostics=tracker.diagnostics(
                    InferenceFailureCode.INVALID_MODEL_RESPONSE
                ),
            ) from None
        tracker.terminal_received = True
        tracker.syntactically_complete = True
        return provider_payload

    def _read_streamed_payload(
        self,
        response: object,
        tracker: _TransportTracker,
    ) -> dict[str, object]:
        event_name: str | None = None
        data_lines: list[str] = []

        def consume() -> dict[str, object] | None:
            nonlocal event_name, data_lines
            if not data_lines:
                event_name = None
                return None
            data = "\n".join(data_lines)
            data_lines = []
            selected_event = event_name
            event_name = None
            tracker.received_events += 1
            if data == "[DONE]":
                return None
            try:
                event_payload = json.loads(data)
            except json.JSONDecodeError:
                raise InferenceTransportUnknown(
                    f"{self.provider_identity} Responses stream contained invalid JSON",
                    failure_code=InferenceFailureCode.INCOMPLETE_RESPONSE,
                    transport_diagnostics=tracker.diagnostics(
                        InferenceFailureCode.INCOMPLETE_RESPONSE
                    ),
                    request_sent=True,
                ) from None
            if not isinstance(event_payload, dict):
                return None
            event_type = event_payload.get("type") or selected_event
            if event_type == "response.completed":
                completed = event_payload.get("response")
                if not isinstance(completed, dict):
                    raise InferenceAdapterError(
                        f"{self.provider_identity} completed stream had no response object",
                        failure_code=InferenceFailureCode.INVALID_MODEL_RESPONSE,
                        transport_diagnostics=tracker.diagnostics(
                            InferenceFailureCode.INVALID_MODEL_RESPONSE
                        ),
                    )
                tracker.terminal_received = True
                tracker.syntactically_complete = True
                return completed
            if event_type in {"response.failed", "error"}:
                tracker.terminal_received = True
                raise InferenceAdapterError(
                    f"{self.provider_identity} Responses stream declared Provider failure",
                    failure_code=InferenceFailureCode.PROVIDER_ERROR,
                    transport_diagnostics=tracker.diagnostics(
                        InferenceFailureCode.PROVIDER_ERROR
                    ),
                )
            if event_type == "response.incomplete":
                tracker.terminal_received = True
                raise InferenceTransportUnknown(
                    f"{self.provider_identity} Responses stream declared an incomplete result",
                    failure_code=InferenceFailureCode.INCOMPLETE_RESPONSE,
                    transport_diagnostics=tracker.diagnostics(
                        InferenceFailureCode.INCOMPLETE_RESPONSE
                    ),
                    request_sent=True,
                )
            return None

        for raw_line in response:
            tracker.observe_bytes(len(raw_line))
            try:
                line = raw_line.decode("utf-8").rstrip("\r\n")
            except UnicodeDecodeError:
                raise InferenceTransportUnknown(
                    f"{self.provider_identity} Responses stream contained invalid UTF-8",
                    failure_code=InferenceFailureCode.INCOMPLETE_RESPONSE,
                    transport_diagnostics=tracker.diagnostics(
                        InferenceFailureCode.INCOMPLETE_RESPONSE
                    ),
                    request_sent=True,
                ) from None
            if not line:
                completed = consume()
                if completed is not None:
                    return completed
            elif line.startswith(":"):
                continue
            elif line.startswith("event:"):
                event_name = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        completed = consume()
        if completed is not None:
            return completed
        failure_code = (
            InferenceFailureCode.EMPTY_RESPONSE
            if tracker.received_events == 0
            else InferenceFailureCode.INCOMPLETE_RESPONSE
        )
        raise InferenceTransportUnknown(
            f"{self.provider_identity} Responses stream ended before completion",
            failure_code=failure_code,
            transport_diagnostics=tracker.diagnostics(failure_code),
            request_sent=True,
        )

    def _request_payload(
        self,
        inference_request: InferenceRequest,
    ) -> tuple[dict[str, object], dict[str, str]]:
        schema = deepcopy(self._decision_schema())
        schema.get("properties", {}).pop("provider_observation", None)
        format_payload: dict[str, object] = {
            "type": "json_schema",
            "name": "watt_native_executor_decision",
            "schema": schema,
        }
        if self.includes_non_strict_schema_flag:
            format_payload["strict"] = False
        payload: dict[str, object] = {
            "model": self.model,
            "instructions": self._instructions(),
            "input": json.dumps(
                inference_request.model_dump(mode="json"), ensure_ascii=False
            ),
            "text": {"format": format_payload},
        }
        if self.includes_store_flag:
            payload["store"] = False
        if self.reasoning_effort is not None:
            payload["reasoning"] = {"effort": self.reasoning_effort}
        provider_tool_names: dict[str, str] = {}
        if self.uses_provider_tools and inference_request.available_tools:
            tools, provider_tool_names = self._project_tools(
                inference_request.available_tools
            )
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        return payload, provider_tool_names

    def _decision_schema(self) -> dict[str, Any]:
        return InferenceResponse.model_json_schema()

    def _parse_text_decision(
        self,
        text: str,
        inference_request: InferenceRequest,
    ) -> InferenceResponse:
        del inference_request
        return InferenceResponse.model_validate_json(text)

    @staticmethod
    def _safe_validation_issues(
        error: ValidationError | json.JSONDecodeError,
    ) -> tuple[dict[str, object], ...]:
        if isinstance(error, json.JSONDecodeError):
            return ({"location": ["json"], "type": "json_invalid"},)
        issues: list[dict[str, object]] = []
        for item in error.errors(include_input=False, include_url=False):
            location = [
                part if isinstance(part, int) else str(part)
                for part in item.get("loc", ())
            ]
            issue_type = item.get("type")
            issues.append(
                {
                    "location": location,
                    "type": str(issue_type) if issue_type is not None else "validation_error",
                }
            )
        return tuple(issues)

    def _instructions(self) -> str:
        return (
            "You are the reasoning capability inside Watt-native Executor. "
            "The supplied PWU contract and capability grants are authoritative. "
            "Choose HOW to advance the bounded objective. Never redefine WHAT NEXT, "
            "expand scope, or claim an unobserved effect. Return the required JSON object. "
            "When available_tools is empty, return a terminal action (RESULT_READY, "
            "UNABLE_TO_COMPLETE, BOUNDARY_CROSSING_REQUIRED, or WAITING_RESOURCE); "
            "never return CONTINUE or repeat an already successful check."
        )

    @staticmethod
    def _project_tools(
        contracts: tuple[dict[str, Any], ...]
    ) -> tuple[list[dict[str, object]], dict[str, str]]:
        projected: list[dict[str, object]] = []
        names: dict[str, str] = {}
        for index, contract in enumerate(contracts):
            identity = contract.get("identity")
            description = contract.get("description")
            parameters = contract.get("input_schema")
            if not isinstance(identity, str) or not identity:
                raise InferenceAdapterError("Watt tool contract has no identity")
            provider_name = f"watt_tool_{index}"
            names[provider_name] = identity
            projected.append(
                {
                    "type": "function",
                    "name": provider_name,
                    "description": (
                        f"Watt tool {identity}. "
                        f"{description if isinstance(description, str) else ''}"
                    ).strip(),
                    "parameters": parameters if isinstance(parameters, dict) else {},
                }
            )
        return projected, names

    def _provider_tool_calls(
        self,
        payload: dict[str, object],
        provider_tool_names: dict[str, str],
    ) -> tuple[ToolCallProposal, ...]:
        if not self.uses_provider_tools:
            return ()
        output = payload.get("output")
        if not isinstance(output, list):
            return ()
        proposals: list[ToolCallProposal] = []
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "function_call":
                continue
            provider_name = item.get("name")
            provider_call_id = item.get("call_id")
            arguments_text = item.get("arguments")
            tool_identity = (
                provider_tool_names.get(provider_name)
                if isinstance(provider_name, str)
                else None
            )
            if tool_identity is None:
                raise InferenceAdapterDecisionRejected(
                    "TOOL_IDENTITY_UNKNOWN",
                    f"{self.provider_identity} proposed an unknown Watt tool"
                )
            if not isinstance(provider_call_id, str) or not provider_call_id:
                raise InferenceAdapterDecisionRejected(
                    "TOOL_CALL_ID_MISSING",
                    f"{self.provider_identity} tool proposal had no call identity"
                )
            try:
                arguments = (
                    json.loads(arguments_text)
                    if isinstance(arguments_text, str)
                    else None
                )
            except json.JSONDecodeError:
                arguments = None
            if not isinstance(arguments, dict):
                raise InferenceAdapterDecisionRejected(
                    "TOOL_ARGUMENTS_NOT_OBJECT",
                    f"{self.provider_identity} tool proposal arguments were not a JSON object"
                )
            proposals.append(
                ToolCallProposal(
                    proposal_index=len(proposals),
                    tool_identity=tool_identity,
                    arguments=arguments,
                    provider_call_id=provider_call_id,
                )
            )
        return tuple(proposals)

    def _observation(
        self, payload: dict[str, object]
    ) -> InferenceProviderObservation:
        usage_payload = payload.get("usage")
        usage = None
        if isinstance(usage_payload, dict):
            input_details = usage_payload.get("input_tokens_details")
            output_details = usage_payload.get("output_tokens_details")
            input_tokens = usage_payload.get("input_tokens")
            output_tokens = usage_payload.get("output_tokens")
            total_tokens = usage_payload.get("total_tokens")
            if all(
                isinstance(value, int) and value >= 0
                for value in (input_tokens, output_tokens, total_tokens)
            ):
                usage = InferenceUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cached_input_tokens=(
                        input_details.get("cached_tokens")
                        if isinstance(input_details, dict)
                        and isinstance(input_details.get("cached_tokens"), int)
                        else None
                    ),
                    reasoning_tokens=(
                        output_details.get("reasoning_tokens")
                        if isinstance(output_details, dict)
                        and isinstance(output_details.get("reasoning_tokens"), int)
                        else None
                    ),
                )
        effective_model = payload.get("model")
        provider_request_id = payload.get("id")
        response_status = payload.get("status")
        return InferenceProviderObservation(
            provider_identity=self.provider_identity,
            requested_model=self.model,
            effective_model=effective_model if isinstance(effective_model, str) else None,
            provider_request_id=(
                provider_request_id if isinstance(provider_request_id, str) else None
            ),
            response_status=(
                response_status if isinstance(response_status, str) else "completed"
            ),
            usage=usage,
        )

    @staticmethod
    def _output_text(payload: dict[str, object]) -> str | None:
        output = payload.get("output")
        if not isinstance(output, list):
            return None
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content_items = item.get("content")
            if not isinstance(content_items, list):
                continue
            for content in content_items:
                if isinstance(content, dict) and content.get("type") == "output_text":
                    value = content.get("text")
                    if isinstance(value, str):
                        return value
        return None


class DeepSeekResponsesInferenceAdapter(ResponsesInferenceAdapter):
    """DeepSeek Responses adapter; proposed tools remain Watt-owned effects."""

    provider_identity = "deepseek"
    provider_profile = "deepseek-responses"
    uses_provider_tools = True
    uses_streaming = True

    def __init__(
        self,
        *,
        model: str,
        api_key: Callable[[], str],
        base_url: str = "https://api.deepseek.com",
        timeout_seconds: float = 120,
        reasoning_effort: str | None = "high",
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            reasoning_effort=reasoning_effort,
        )

    def _instructions(self) -> str:
        return (
            super()._instructions()
            + " When a supplied function can advance the work, call that function through "
            "the API tool mechanism; do not place tool calls inside the JSON text. Watt will "
            "validate and execute every proposal. Never return action CONTINUE in JSON text; "
            "CONTINUE is represented only by an API function call. When no tool is needed, "
            "return RESULT_READY with a non-null result_claim, or a truthful terminal/waiting "
            "action, and never include provider or usage metadata in the JSON object. Do not "
            "reinterpret explicit requirements or write tests that assert contrary behavior. "
            "Apply the TOOL_PATH_CONVENTION fact exactly when forming every path or cwd; "
            "do not infer Tool paths from SOURCE_VECTOR container_path. "
            "Do not repeat a tool when its latest receipt already proves the same check; once "
            "all residual obligations have settled evidence, return RESULT_READY. If a prior "
            "inference.decision receipt reports PROVIDER_DECISION_REJECTION, use its stable "
            "reason_code to emit one corrected decision and never repeat the rejected form."
        )

    def _decision_schema(self) -> dict[str, Any]:
        return _TerminalInferenceDecision.model_json_schema()

    def _parse_text_decision(
        self,
        text: str,
        inference_request: InferenceRequest,
    ) -> InferenceResponse:
        terminal = _TerminalInferenceDecision.model_validate_json(text)
        return InferenceResponse(
            action=terminal.action,
            summary=terminal.summary,
            working_plan=inference_request.working_plan,
            result_claim=terminal.result_claim,
            residual_obligations=terminal.residual_obligations,
        )


class OpenAIResponsesInferenceAdapter(ResponsesInferenceAdapter):
    """Configuration-driven OpenAI Responses API adapter; tools remain Watt-owned."""

    provider_identity = "openai"
    provider_profile = "openai-responses"
    includes_store_flag = True
    includes_non_strict_schema_flag = True

    def __init__(
        self,
        *,
        model: str,
        api_key: Callable[[], str],
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 120,
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )


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
