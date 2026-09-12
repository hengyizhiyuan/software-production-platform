from __future__ import annotations

import asyncio
from http.client import IncompleteRead
from io import BytesIO
import json
from urllib.error import HTTPError
from uuid import uuid4

import pytest

from spg.config import Settings
from spg.domain.native_execution import (
    InferenceAction,
    InferenceProviderObservation,
    InferenceRequest,
    InferenceResponse,
    InferenceUsage,
    ToolCallProposal,
    ToolExecutionResult,
    WorkingPlan,
    EffectCondition,
)
from spg.executor_worker import (
    provider_readiness_report,
    run_minimal_inference_probe,
    run_tool_flow_probe,
)
from spg.infrastructure.executor_runtime.inference import (
    DeepSeekResponsesInferenceAdapter,
    InferenceAdapterDecisionRejected,
    InferenceAdapterIdentity,
    InferenceAdapterError,
    InferenceResourceUnavailable,
    InferenceTransportUnknown,
)


def _plan() -> WorkingPlan:
    return WorkingPlan(
        version=1,
        objective_reference="contract:qualification",
        chosen_approach="inspect the isolated fixture",
        approach_rationale="the bounded contract requires direct evidence",
    )


def _request(*, with_tool: bool = True) -> InferenceRequest:
    tools = ()
    if with_tool:
        tools = (
            {
                "identity": "file.read",
                "version": "1",
                "description": "Read one harmless fixture file.",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                    "additionalProperties": False,
                },
                "effect_classification": "READ",
            },
        )
    return InferenceRequest(
        attempt_id=uuid4(),
        session_id=uuid4(),
        step_sequence=1,
        objective="inspect one isolated fixture",
        working_plan=_plan(),
        context_facts=(),
        available_tools=tools,
        residual_obligations=("inspect",),
    )


def _completed_payload(output: list[dict[str, object]]) -> dict[str, object]:
    return {
        "id": "response-deepseek-1",
        "object": "response",
        "status": "completed",
        "model": "deepseek-flash",
        "output": output,
        "usage": {
            "input_tokens": 101,
            "input_tokens_details": {"cached_tokens": 11},
            "output_tokens": 23,
            "output_tokens_details": {"reasoning_tokens": 7},
            "total_tokens": 124,
        },
    }


def test_deepseek_structured_response_uses_exact_official_responses_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    decision = {
        "action": "UNABLE_TO_COMPLETE",
        "summary": "No mutation was required for the smoke fixture.",
        "result_claim": None,
        "residual_obligations": ["inspect"],
    }

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            del args

        def read(self) -> bytes:
            payload = _completed_payload(
                [{
                    "type": "message",
                    "content": [{
                        "type": "output_text",
                        "text": json.dumps(decision),
                    }],
                }]
            )
            return ("\n\n" + json.dumps(payload)).encode("utf-8")

    def succeed(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["authorization"] = request.headers["Authorization"]
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(
        "spg.infrastructure.executor_runtime.inference.urlopen", succeed
    )
    adapter = DeepSeekResponsesInferenceAdapter(
        model="deepseek-flash",
        api_key=lambda: "deepseek-secret-not-for-payload",
        reasoning_effort="high",
    )

    result = asyncio.run(adapter.infer(_request()))

    payload = captured["payload"]
    assert captured["url"] == "https://api.deepseek.com/responses"
    assert payload["model"] == "deepseek-flash"
    assert payload["reasoning"] == {"effort": "high"}
    assert payload["text"]["format"]["type"] == "json_schema"
    decision_schema = payload["text"]["format"]["schema"]
    assert set(decision_schema["properties"]) == {
        "action", "summary", "result_claim", "residual_obligations",
    }
    assert "working_plan" not in decision_schema["properties"]
    assert "tool_calls" not in decision_schema["properties"]
    assert "strict" not in payload["text"]["format"]
    assert "store" not in payload
    assert payload["tools"][0]["name"] == "watt_tool_0"
    assert "." not in payload["tools"][0]["name"]
    assert payload["tool_choice"] == "auto"
    assert "Never return action CONTINUE in JSON text" in payload["instructions"]
    assert "Do not reinterpret explicit requirements" in payload["instructions"]
    assert "TOOL_PATH_CONVENTION" in payload["instructions"]
    assert "PROVIDER_DECISION_REJECTION" in payload["instructions"]
    assert "deepseek-secret-not-for-payload" not in json.dumps(payload)
    assert result.provider_observation is not None
    assert result.provider_observation.provider_identity == "deepseek"
    assert result.provider_observation.effective_model == "deepseek-flash"
    assert result.provider_observation.provider_request_id == "response-deepseek-1"
    assert result.provider_observation.usage is not None
    assert result.provider_observation.usage.total_tokens == 124
    assert result.provider_observation.usage.cached_input_tokens == 11
    assert result.provider_observation.usage.reasoning_tokens == 7
    assert result.working_plan == _plan()


def test_deepseek_terminal_text_rejects_continue_with_safe_validation_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            del args

        def read(self) -> bytes:
            return json.dumps(_completed_payload([{
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": json.dumps({
                        "action": "CONTINUE",
                        "summary": "invalid text continuation",
                        "result_claim": None,
                        "residual_obligations": ["inspect"],
                    }),
                }],
            }])).encode("utf-8")

    monkeypatch.setattr(
        "spg.infrastructure.executor_runtime.inference.urlopen",
        lambda request, timeout: Response(),
    )
    adapter = DeepSeekResponsesInferenceAdapter(
        model="deepseek-flash", api_key=lambda: "not-a-real-key"
    )

    with pytest.raises(InferenceAdapterDecisionRejected) as caught:
        asyncio.run(adapter.infer(_request()))

    assert caught.value.reason_code == "NATIVE_DECISION_SCHEMA_REJECTED"
    assert caught.value.validation_issues == (
        {"location": [], "type": "value_error"},
    )
    assert "invalid text continuation" not in str(caught.value)


def test_deepseek_result_ready_requires_claim_without_persisting_provider_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            del args

        def read(self) -> bytes:
            return json.dumps(_completed_payload([{
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": json.dumps({
                        "action": "RESULT_READY",
                        "summary": "secret-provider-text",
                        "result_claim": None,
                        "residual_obligations": [],
                    }),
                }],
            }])).encode("utf-8")

    monkeypatch.setattr(
        "spg.infrastructure.executor_runtime.inference.urlopen",
        lambda request, timeout: Response(),
    )
    adapter = DeepSeekResponsesInferenceAdapter(
        model="deepseek-flash", api_key=lambda: "not-a-real-key"
    )

    with pytest.raises(InferenceAdapterDecisionRejected) as caught:
        asyncio.run(adapter.infer(_request()))

    assert caught.value.reason_code == "NATIVE_DECISION_SCHEMA_REJECTED"
    assert caught.value.validation_issues == (
        {"location": [], "type": "value_error"},
    )
    assert "secret-provider-text" not in str(caught.value)


def test_deepseek_function_call_is_normalized_without_executing_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            del args

        def read(self) -> bytes:
            return json.dumps(
                _completed_payload(
                    [{
                        "type": "function_call",
                        "call_id": "deepseek-call-1",
                        "name": "watt_tool_0",
                        "arguments": json.dumps({"path": "README.md"}),
                    }]
                )
            ).encode("utf-8")

    monkeypatch.setattr(
        "spg.infrastructure.executor_runtime.inference.urlopen",
        lambda request, timeout: Response(),
    )
    adapter = DeepSeekResponsesInferenceAdapter(
        model="deepseek-flash", api_key=lambda: "not-a-real-key"
    )

    result = asyncio.run(adapter.infer(_request()))

    assert result.action is InferenceAction.CONTINUE
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_identity == "file.read"
    assert result.tool_calls[0].arguments == {"path": "README.md"}
    assert result.tool_calls[0].provider_call_id == "deepseek-call-1"


@pytest.mark.parametrize(
    ("status", "retryable"),
    ((402, False), (429, True), (500, True), (503, True)),
)
def test_deepseek_resource_errors_are_normalized(
    monkeypatch: pytest.MonkeyPatch, status: int, retryable: bool
) -> None:
    def fail(*args, **kwargs):
        del args, kwargs
        raise HTTPError(
            "https://api.deepseek.com/responses",
            status,
            "provider resource",
            {},
            BytesIO(b'{"error":{"message":"resource unavailable"}}'),
        )

    monkeypatch.setattr(
        "spg.infrastructure.executor_runtime.inference.urlopen", fail
    )
    adapter = DeepSeekResponsesInferenceAdapter(
        model="deepseek-flash", api_key=lambda: "not-a-real-key"
    )

    with pytest.raises(InferenceResourceUnavailable) as caught:
        asyncio.run(adapter.infer(_request(with_tool=False)))

    assert caught.value.retryable is retryable
    assert "not-a-real-key" not in str(caught.value)


def test_deepseek_incomplete_http_body_is_a_sanitized_terminal_adapter_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            del args

        def read(self) -> bytes:
            raise IncompleteRead(b"")

    monkeypatch.setattr(
        "spg.infrastructure.executor_runtime.inference.urlopen",
        lambda request, timeout: Response(),
    )
    adapter = DeepSeekResponsesInferenceAdapter(
        model="deepseek-flash", api_key=lambda: "not-a-real-key"
    )

    with pytest.raises(InferenceTransportUnknown, match="IncompleteRead") as caught:
        asyncio.run(adapter.infer(_request(with_tool=False)))

    assert "not-a-real-key" not in str(caught.value)
    assert caught.value.response_unknown is True


def test_deepseek_rejects_unknown_provider_tool_correlation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            del args

        def read(self) -> bytes:
            return json.dumps(
                _completed_payload(
                    [{
                        "type": "function_call",
                        "call_id": "unmapped-call",
                        "name": "invented_tool",
                        "arguments": "{}",
                    }]
                )
            ).encode("utf-8")

    monkeypatch.setattr(
        "spg.infrastructure.executor_runtime.inference.urlopen",
        lambda request, timeout: Response(),
    )
    adapter = DeepSeekResponsesInferenceAdapter(
        model="deepseek-flash", api_key=lambda: "not-a-real-key"
    )

    with pytest.raises(InferenceAdapterDecisionRejected, match="unknown Watt tool") as caught:
        asyncio.run(adapter.infer(_request()))

    assert caught.value.reason_code == "TOOL_IDENTITY_UNKNOWN"


def test_deepseek_rejects_malformed_tool_arguments_with_stable_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            del args

        def read(self) -> bytes:
            return json.dumps(_completed_payload([{
                "type": "function_call",
                "call_id": "call-malformed",
                "name": "watt_tool_0",
                "arguments": "{not-json",
            }])).encode("utf-8")

    monkeypatch.setattr(
        "spg.infrastructure.executor_runtime.inference.urlopen",
        lambda request, timeout: Response(),
    )
    adapter = DeepSeekResponsesInferenceAdapter(
        model="deepseek-flash", api_key=lambda: "not-a-real-key"
    )

    with pytest.raises(InferenceAdapterDecisionRejected) as caught:
        asyncio.run(adapter.infer(_request()))

    assert caught.value.reason_code == "TOOL_ARGUMENTS_NOT_OBJECT"


def test_deepseek_worker_readiness_is_no_request_and_secret_free() -> None:
    report = provider_readiness_report(
        Settings(
            native_executor_enabled=True,
            native_executor_inference_provider="deepseek",
            native_executor_inference_model="deepseek-flash",
            native_executor_deepseek_api_key="not-a-real-key",
            native_executor_deepseek_base_url="https://api.deepseek.com",
        )
    )

    assert report == {
        "status": "READY",
        "provider": "deepseek",
        "provider_profile": "deepseek-responses:deepseek-flash:high",
        "model": "deepseek-flash",
        "base_url": "https://api.deepseek.com",
        "reasoning_effort": "high",
        "credential_present": True,
        "provider_request_sent": False,
        "production_attempt_created": False,
    }
    assert "not-a-real-key" not in json.dumps(report)


def test_minimal_probe_issues_one_request_without_tools_or_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Adapter:
        def __init__(self) -> None:
            self.requests: list[InferenceRequest] = []

        async def infer(self, request: InferenceRequest) -> InferenceResponse:
            self.requests.append(request)
            return InferenceResponse(
                action=InferenceAction.UNABLE_TO_COMPLETE,
                summary="Provider smoke response.",
                working_plan=request.working_plan,
                provider_observation=InferenceProviderObservation(
                    provider_identity="deepseek",
                    requested_model="deepseek-flash",
                    effective_model="deepseek-flash",
                    provider_request_id="response-p1",
                    response_status="completed",
                    usage=InferenceUsage(
                        input_tokens=10, output_tokens=5, total_tokens=15
                    ),
                ),
            )

    adapter = Adapter()
    monkeypatch.setattr(
        "spg.executor_worker.configured_inference_adapter",
        lambda settings: adapter,
    )

    report = asyncio.run(run_minimal_inference_probe(Settings()))

    assert len(adapter.requests) == 1
    assert adapter.requests[0].available_tools == ()
    assert report["status"] == "PASS"
    assert report["tool_execution_count"] == 0
    assert report["production_attempt_created"] is False


def test_tool_flow_probe_is_two_submissions_and_one_read_only_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observation = InferenceProviderObservation(
        provider_identity="deepseek",
        requested_model="deepseek-flash",
        effective_model="deepseek-flash",
        provider_request_id="response-p2",
        response_status="completed",
        usage=InferenceUsage(input_tokens=10, output_tokens=5, total_tokens=15),
    )

    class Adapter:
        identity = InferenceAdapterIdentity(
            provider="deepseek",
            provider_profile="deepseek-responses:deepseek-flash:high",
            model="deepseek-flash",
            base_url="https://api.deepseek.com",
            reasoning_effort="high",
        )

        def __init__(self) -> None:
            self.requests: list[InferenceRequest] = []

        async def infer(self, request: InferenceRequest) -> InferenceResponse:
            self.requests.append(request)
            if request.available_tools:
                return InferenceResponse(
                    action=InferenceAction.CONTINUE,
                    summary="Read the fixture.",
                    working_plan=request.working_plan,
                    tool_calls=(
                        ToolCallProposal(
                            proposal_index=0,
                            tool_identity="file.read",
                            arguments={"path": "qualification.txt"},
                            provider_call_id="call-p2",
                        ),
                    ),
                    provider_observation=observation,
                )
            return InferenceResponse(
                action=InferenceAction.UNABLE_TO_COMPLETE,
                summary="Read-only flow complete.",
                working_plan=request.working_plan,
                provider_observation=observation.model_copy(
                    update={"provider_request_id": "response-p2-final"}
                ),
            )

    class ToolHost:
        requests = []

        def __init__(self, *args, **kwargs):
            del args, kwargs

        async def execute(self, request):
            self.requests.append(request)
            return ToolExecutionResult(
                delivery_id=request.delivery_id,
                tool_identity="file.read",
                condition=EffectCondition.SETTLED,
                output={"path": "qualification.txt", "content": "WATT_P2_OK"},
                output_digest="a" * 64,
            )

    adapter = Adapter()
    monkeypatch.setattr(
        "spg.executor_worker.configured_inference_adapter", lambda settings: adapter
    )
    monkeypatch.setattr("spg.executor_worker.RemoteNativeToolHost", ToolHost)

    report = asyncio.run(
        run_tool_flow_probe(
            Settings(
                native_executor_internal_token="internal-test-token",
                native_executor_inference_model="deepseek-flash",
            )
        )
    )

    assert len(adapter.requests) == 2
    assert len(ToolHost.requests) == 1
    assert adapter.requests[1].previous_results[0]["output"]["content"] == "WATT_P2_OK"
    assert report["provider_submission_count"] == 2
    assert report["normalized_tool"] == "file.read"
    assert report["mutation_count"] == 0


def test_native_compose_selects_deepseek_without_changing_wic() -> None:
    compose = open("compose.native-executor.yaml", encoding="utf-8").read()
    app = compose[compose.index("  app:"):compose.index("  native-coordinator:")]
    assert "SPG_VERIFICATION_ADAPTER: contract-driven-repository" in app
    assert "target: native-verification" in app
    assert "SPG_NATIVE_EXECUTOR_INFERENCE_PROVIDER" in compose
    assert "SPG_NATIVE_EXECUTOR_DEEPSEEK_API_KEY" in compose
    assert "deepseek-flash" in compose
    assert "native-app-data:/var/lib/spg:ro" in compose
    tool_host = compose[compose.index("  native-tool-host:"):compose.index("  native-worker:")]
    assert "target: native-tool-host" in tool_host
    worker = compose[compose.index("  native-worker:"):]
    assert "SPG_NATIVE_EXECUTOR_OPENAI_API_KEY" not in worker
    assert "SPG_WIC_" not in worker
