"""Inference adapters for the Watt-native Executor reasoning port."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from http.client import IncompleteRead, RemoteDisconnected
import json
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
    InferenceUsage,
    ToolCallProposal,
)


class InferenceAdapterError(RuntimeError):
    """Sanitized provider failure that never includes credentials."""


class InferenceAdapterDecisionRejected(InferenceAdapterError, InferenceDecisionRejected):
    """Observed Provider output rejected before any proposed effect can start."""

    def __init__(
        self,
        reason_code: str,
        message: str,
        *,
        validation_issues: tuple[dict[str, object], ...] = (),
    ) -> None:
        InferenceAdapterError.__init__(self, message)
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
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.request_sent = request_sent


class InferenceTransportUnknown(InferenceAdapterError):
    """A request may have reached the Provider, but no complete response was observed."""

    request_sent = True
    response_unknown = True


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
        request = Request(
            f"{self.base_url}/responses",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_payload = response.read().decode("utf-8").strip()
                provider_payload = json.loads(raw_payload)
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:1000]
            detail = detail.replace(key, "<redacted>")
            if error.code in {402, 429, 500, 503}:
                raise InferenceResourceUnavailable(
                    f"{self.provider_identity} Responses resource is unavailable "
                    f"(HTTP {error.code}): {detail}",
                    retryable=error.code in {429, 500, 503},
                ) from None
            raise InferenceAdapterError(
                f"{self.provider_identity} Responses request failed with HTTP "
                f"{error.code}: {detail}"
            ) from None
        except (URLError, TimeoutError, IncompleteRead, RemoteDisconnected) as error:
            raise InferenceTransportUnknown(
                f"{self.provider_identity} Responses transport failed: "
                f"{type(error).__name__}"
            ) from None
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InferenceAdapterError(
                f"{self.provider_identity} Responses result was not valid JSON: "
                f"{type(error).__name__}"
            ) from None

        if not isinstance(provider_payload, dict):
            raise InferenceAdapterError(
                f"{self.provider_identity} Responses result was not an object"
            )
        observation = self._observation(provider_payload)
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
