from __future__ import annotations

import json

import httpx2
import pytest

from spg.domain.model_runtime import ModelProfile, ModelProvider, ModelPurpose
from spg.infrastructure.model_runtime import (
    DeepSeekResponsesModelAdapter,
    ModelFailureKind,
    ModelProviderError,
)


def _profile() -> ModelProfile:
    return ModelProfile(
        purpose=ModelPurpose.WIC_SEMANTIC,
        provider=ModelProvider.DEEPSEEK,
        model="deepseek-flash",
        reasoning_effort="low",
        timeout_seconds=30,
        max_output_tokens=4096,
    )


def test_deepseek_responses_transport_streams_and_normalizes_usage() -> None:
    captured = []
    terminal = {
        "id": "response-wic-1",
        "status": "completed",
        "model": "deepseek-flash",
        "usage": {
            "input_tokens": 12,
            "output_tokens": 7,
            "total_tokens": 19,
            "input_tokens_details": {"cached_tokens": 2},
            "output_tokens_details": {"reasoning_tokens": 3},
        },
    }
    body = "\n".join((
        'data: {"type":"response.output_text.delta","delta":"{\\"ok\\":"}',
        'data: {"type":"response.output_text.delta","delta":"true}"}',
        "data: " + json.dumps({"type": "response.completed", "response": terminal}),
        "",
    ))

    def handler(request: httpx2.Request) -> httpx2.Response:
        captured.append(request)
        return httpx2.Response(200, text=body)

    client = httpx2.Client(
        base_url="https://api.deepseek.com",
        transport=httpx2.MockTransport(handler),
    )
    adapter = DeepSeekResponsesModelAdapter(
        api_key=lambda: "test-secret", base_url="https://api.deepseek.com", client=client
    )
    deltas = []
    stages = []
    result = adapter.generate(
        profile=_profile(),
        instructions="Watt contract",
        input_text="exact basis",
        output_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
        on_output_delta=deltas.append,
        on_stage=stages.append,
    )

    assert result.output_text == '{"ok":true}'
    assert result.request_id == "response-wic-1"
    assert result.effective_model == "deepseek-flash"
    assert result.usage.total_tokens == 19
    assert result.usage.cached_tokens == 2
    assert result.usage.reasoning_tokens == 3
    assert result.retry_count == 0
    assert len(captured) == 1
    payload = json.loads(captured[0].content)
    assert payload["model"] == "deepseek-flash"
    assert payload["reasoning"] == {"effort": "low"}
    assert payload["stream"] is True
    assert payload["max_output_tokens"] == 4096
    assert payload["text"]["format"]["type"] == "json_schema"
    assert stages == [
        "provider_request_queued",
        "provider_request_sent",
        "provider_response_accepted",
        "provider_first_response_event",
        "provider_first_token",
    ]


def test_readiness_is_no_request_and_http_failure_is_not_retried() -> None:
    calls = 0

    def handler(_request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(429, json={"error": {"message": "capacity"}})

    adapter = DeepSeekResponsesModelAdapter(
        api_key=lambda: "test-secret",
        base_url="https://api.deepseek.com",
        client=httpx2.Client(
            base_url="https://api.deepseek.com",
            transport=httpx2.MockTransport(handler),
        ),
    )
    readiness = adapter.readiness(_profile())
    assert readiness["provider_request_sent"] is False
    assert calls == 0

    with pytest.raises(ModelProviderError) as failure:
        adapter.generate(
            profile=_profile(), instructions="x", input_text="y",
            output_schema={"type": "object"},
        )
    assert failure.value.kind is ModelFailureKind.CAPACITY_OR_RATE_LIMIT
    assert calls == 1
    assert "test-secret" not in str(failure.value)


def test_remote_protocol_failure_before_first_event_gets_one_fresh_replay() -> None:
    calls = 0
    terminal = {
        "id": "response-after-recovery",
        "status": "completed",
        "model": "deepseek-flash",
        "usage": {"input_tokens": 3, "output_tokens": 2, "total_tokens": 5},
    }

    def handler(_request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx2.RemoteProtocolError("server disconnected")
        return httpx2.Response(
            200,
            text="\n".join((
                'data: {"type":"response.output_text.delta","delta":"{\\"ok\\":true}"}',
                "data: " + json.dumps({"type": "response.completed", "response": terminal}),
                "",
            )),
        )

    adapter = DeepSeekResponsesModelAdapter(
        api_key=lambda: "test-secret",
        base_url="https://api.deepseek.com",
        client=httpx2.Client(
            base_url="https://api.deepseek.com",
            transport=httpx2.MockTransport(handler),
        ),
    )
    stages = []
    result = adapter.generate(
        profile=_profile(),
        instructions="x",
        input_text="y",
        output_schema={"type": "object"},
        on_stage=stages.append,
    )

    assert calls == 2
    assert result.output_text == '{"ok":true}'
    assert result.retry_count == 1
    assert stages.count("provider_request_sent") == 2
    assert stages.count("provider_transport_recovery") == 1


def test_incomplete_response_preserves_safe_recovery_diagnostics() -> None:
    terminal = {
        "id": "response-incomplete-1",
        "status": "incomplete",
        "model": "deepseek-flash",
        "incomplete_details": {"reason": "max_output_tokens"},
        "usage": {"input_tokens": 10, "output_tokens": 4096, "total_tokens": 4106},
    }
    body = "\n".join((
        'data: {"type":"response.output_text.delta","delta":"{\\"ok\\":"}',
        "data: " + json.dumps({"type": "response.incomplete", "response": terminal}),
        "",
    ))
    adapter = DeepSeekResponsesModelAdapter(
        api_key=lambda: "test-secret",
        base_url="https://api.deepseek.com",
        client=httpx2.Client(
            base_url="https://api.deepseek.com",
            transport=httpx2.MockTransport(
                lambda _request: httpx2.Response(200, text=body)
            ),
        ),
    )

    with pytest.raises(ModelProviderError) as failure:
        adapter.generate(
            profile=_profile(),
            instructions="x",
            input_text="y",
            output_schema={"type": "object"},
        )

    assert failure.value.kind is ModelFailureKind.INCOMPLETE_RESPONSE
    assert failure.value.retryable is True
    assert failure.value.provider_status == "incomplete"
    assert failure.value.termination_reason == "max_output_tokens"
    assert failure.value.request_id == "response-incomplete-1"
    assert failure.value.occurred_at is not None
