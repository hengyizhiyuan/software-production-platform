"""C3 typed Provider failure receipts; controlled runtime only, no live calls."""
from __future__ import annotations

from datetime import UTC, datetime
import json

import pytest

from spg.application.governed_obligations import form_fulfillment_projection, fulfillment_capability_contracts
from spg.domain.governed_obligation import fulfillment_source_ref
from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
from spg.infrastructure.model_runtime import ModelFailureKind, ModelProviderError
from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider, provider_failure_observation
from tests.test_c3_fulfillment_components import current_lifecycle_candidate
from tests.test_fulfillment_projection import basis, Oracle


class ControlledRuntime:
    def __init__(self, output):
        self.output, self.calls, self.closes = output, 0, 0

    def generate(self, **kwargs):
        self.calls += 1
        if isinstance(self.output, Exception):
            raise self.output
        return self.output

    def close(self):
        self.closes += 1


def typed_failure(message="Unretained Provider body"):
    return ModelProviderError(ModelFailureKind.INCOMPLETE_RESPONSE, message,
        request_sent=True, usage_unknown=False, retryable=True,
        provider_status="incomplete", termination_reason="max_output_tokens",
        request_id="request-controlled-failure", occurred_at=datetime(2026, 10, 9, 12, 58, 10, tzinfo=UTC))


def invoke(provider, phase, inventory, plan, *, receipt_callback=None):
    if phase == "MODEL_REQUEST":
        return provider.form(inventory, fulfillment_capability_contracts(), receipt_callback=receipt_callback)
    return provider.review(inventory, plan, capabilities=fulfillment_capability_contracts(), receipt_callback=receipt_callback)


@pytest.mark.parametrize("phase", ["MODEL_REQUEST", "SEMANTIC_REVIEW"])
def test_typed_failure_replaces_stale_observation_without_output_or_retry(phase, monkeypatch):
    sentinel = "private-provider-key-sentinel"
    monkeypatch.setenv("SPG_DEEPSEEK_API_KEY", sentinel)
    error = typed_failure("raw HTTP body and credentials " + sentinel)
    runtime = ControlledRuntime(error)
    provider = ModelFulfillmentCandidateProvider(lambda: runtime)
    provider.last_observation = {"request_id": "stale-request", "usage": {"total_tokens": 0}}
    _, _, inventory, plan = current_lifecycle_candidate()
    responses = []
    with pytest.raises(ModelProviderError) as raised:
        invoke(provider, phase, inventory, plan, receipt_callback=lambda **values: responses.append(values))
    assert raised.value is error
    assert runtime.calls == runtime.closes == 1 and responses == []
    observation = provider.last_observation
    assert observation["provider_failure"] == {
        "kind": "INCOMPLETE_RESPONSE", "request_sent": True, "usage_unknown": False,
        "retryable": True, "provider_status": "incomplete", "termination_reason": "max_output_tokens",
        "request_id": "request-controlled-failure", "occurred_at": "2026-10-09T12:58:10+00:00"}
    assert observation["usage"]["unknown"] is True
    assert all(value is None for key, value in observation["usage"].items() if key != "unknown")
    assert observation["transport_retry_count"] is None
    serialized = json.dumps(observation)
    assert sentinel not in serialized and "raw HTTP" not in serialized and "stale-request" not in serialized


@pytest.mark.parametrize("phase", ["MODEL_REQUEST", "SEMANTIC_REVIEW"])
def test_runtime_factory_failure_clears_previous_observation(phase):
    def unavailable():
        raise RuntimeError("Factory unavailable")
    provider = ModelFulfillmentCandidateProvider(unavailable)
    provider.last_observation = {"request_id": "previous-success", "usage": {"total_tokens": 0}}
    _, _, inventory, plan = current_lifecycle_candidate()
    with pytest.raises(RuntimeError, match="Factory unavailable"):
        invoke(provider, phase, inventory, plan)
    assert provider.last_observation is None


def test_failure_whitelist_rejects_invalid_types_unbounded_fields_and_known_secrets(monkeypatch):
    sentinel = "private-provider-key-sentinel"
    monkeypatch.setenv("SPG_DEEPSEEK_API_KEY", sentinel)
    error = typed_failure("raw body " + sentinel)
    error.kind = sentinel
    error.request_sent, error.usage_unknown, error.retryable = "true", 1, "later"
    error.provider_status, error.termination_reason = "HTTP body " + sentinel, "x" * 121
    error.request_id, error.occurred_at = sentinel, "not a typed timestamp"
    error.raw_http_body = "arbitrary body must not be projected"
    observation = provider_failure_observation(error)
    assert all(value is None for value in observation["provider_failure"].values())
    assert observation["usage"]["total_tokens"] is None and observation["usage"]["unknown"] is True
    serialized = json.dumps(observation)
    assert sentinel not in serialized and "raw_http_body" not in serialized
    error = typed_failure()
    error.request_id = "x" * 201
    error.provider_status = "x" * 65
    assert provider_failure_observation(error)["provider_failure"]["request_id"] is None
    assert provider_failure_observation(error)["provider_failure"]["provider_status"] is None


@pytest.mark.parametrize("phase", ["MODEL_REQUEST", "SEMANTIC_REVIEW"])
def test_terminal_failure_preserves_exact_sources_and_same_basis_never_reopens_calls(phase, monkeypatch):
    sentinel = "private-provider-key-sentinel"
    monkeypatch.setenv("SPG_DEEPSEEK_API_KEY", sentinel)
    revision, ir, inventory, plan = current_lifecycle_candidate()
    before_facts = [fact.model_dump(mode="json") for fact in revision.engineering_semantic_facts]
    before_clauses = [clause.model_dump(mode="json") for clause in ir.clauses]
    failure_runtime = ControlledRuntime(typed_failure("unretained HTTP content " + sentinel))
    runtimes = [failure_runtime]
    if phase == "SEMANTIC_REVIEW":
        from tests.test_c3_fulfillment_capacity_representation import controlled_wire
        wire, _context = controlled_wire(inventory, plan)
        formation_runtime = ControlledRuntime(StructuredModelResult(output_text=json.dumps(wire),
            provider=ModelProvider.DEEPSEEK, requested_model="controlled", effective_model="controlled",
            request_id="request-controlled-formation", usage=ModelUsage(total_tokens=17),
            timing=ModelTiming(completed_seconds=0.1)))
        runtimes.insert(0, formation_runtime)
    pending_runtimes = iter(runtimes)
    provider = ModelFulfillmentCandidateProvider(lambda: next(pending_runtimes))
    provider.last_observation = {"request_id": "stale-success", "usage": {"total_tokens": 0}}
    bindings = form_fulfillment_projection(revision, ir, provider=provider)
    assert all(binding.state == "UNRESOLVED" for binding in bindings)
    expected_refs = [source["source_ref"] for source in inventory["sources"]]
    assert set(map(fulfillment_source_ref, bindings)) == set(expected_refs)
    receipt = bindings[0].formation_receipt
    terminal = next(row for row in receipt["candidate_attempts"] if row.get("terminal"))
    assert terminal["failure_stage"] == phase
    assert terminal["candidate"] is None and terminal["validation_passed"] is False
    assert terminal["unresolved_source_refs"] == receipt["unresolved_source_refs"] == expected_refs
    assert terminal["model"] == provider_failure_observation(failure_runtime.output)
    assert receipt["provider_call_count"] == len(runtimes) and receipt["attempt_count"] == 1
    assert receipt["observed_model_call_count"] == len(runtimes) - 1
    assert receipt["candidate_attempt_limit"] == 2 and receipt["maximum_model_calls"] == 4
    assert terminal["terminal_reason"] == "OBLIGATION_FORMATION_TRANSPORT_ModelProviderError"
    assert f"work-plan-receipt:{terminal['receipt_id']}" in receipt["receipt_refs"]
    before_rows = list(provider._fulfillment_receipts)
    replay = form_fulfillment_projection(revision, ir, provider=provider)
    assert provider._fulfillment_receipts == before_rows
    assert all(runtime.calls == runtime.closes == 1 for runtime in runtimes)
    assert replay[0].formation_receipt["receipt_refs"] == receipt["receipt_refs"]
    assert [fact.model_dump(mode="json") for fact in revision.engineering_semantic_facts] == before_facts
    assert [clause.model_dump(mode="json") for clause in ir.clauses] == before_clauses
    assert sentinel not in json.dumps(receipt) and "unretained HTTP content" not in json.dumps(receipt)


def test_untyped_failure_cannot_reuse_stale_typed_metadata():
    revision, ir = basis()
    provider = Oracle([RuntimeError("private exception prose must not be recorded")])
    provider.last_observation = provider_failure_observation(typed_failure())
    bindings = form_fulfillment_projection(revision, ir, provider=provider)
    terminal = next(row for row in bindings[0].formation_receipt["candidate_attempts"] if row.get("terminal"))
    assert terminal["model"] is None and terminal["failure_stage"] == "MODEL_REQUEST"
    assert terminal["terminal_reason"] == "OBLIGATION_FORMATION_TRANSPORT_RuntimeError"
    assert "private exception prose" not in json.dumps(bindings[0].formation_receipt)
    form_fulfillment_projection(revision, ir, provider=provider)
    assert len(provider.calls) == 1


def test_untyped_exception_has_no_provider_failure_claim():
    assert provider_failure_observation(RuntimeError("untrusted error text")) is None
