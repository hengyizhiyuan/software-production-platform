"""R2 Semantic Step owner diagnostics; controlled candidates, no model or Work."""
from contextlib import contextmanager
from dataclasses import asdict, replace
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.application.semantic_steps import SemanticStepApplicationService, SemanticStepRefinementExhausted
from spg.domain.model_runtime import ModelUsage
from spg.domain.steering import (RealityReference, RealityReferenceKind, SemanticStepResultCandidate,
    SemanticResultKind, SteeringAuthorityAssessment, SteeringStepType, SteeringInvariantViolation,
    StaleSemanticStepCandidate)
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.model_runtime import ModelFailureKind, ModelProviderError
from spg.providers.deepseek_semantic import DeepSeekSemanticStepCapability
from tests.test_deepseek_semantic_provider import _Runtime
from tests.test_c3_greenfield_target_proof import exact_source, scope_fixture


def basis():
    work, plan, step = uuid4(), uuid4(), uuid4()
    value = SimpleNamespace(work_id=work, steering_plan_revision_id=plan,
        step=SimpleNamespace(id=step, type=SteeringStepType.DESIGN), basis_fingerprint="b" * 64,
        engineering_resource_id=uuid4(), design_context=None)
    candidate = SemanticStepResultCandidate(work_id=work, steering_plan_revision_id=plan,
        step_id=step, step_type=SteeringStepType.DESIGN, basis_fingerprint=value.basis_fingerprint,
        result_kind=SemanticResultKind.DESIGN_DIRECTION, bounded_summary="Controlled candidate direction only.",
        decisions=("Retain the original admitted direction",),
        evidence_refs=(RealityReference(kind=RealityReferenceKind.WORK, identity=work),),
        authority_assessment=SteeringAuthorityAssessment.WITHIN_AUTHORITY, completion_claimed=True)
    return value, candidate


def service(monkeypatch, capability, semantic_input, admission):
    captured, commits = [], []
    @contextmanager
    def unit_of_work():
        yield SimpleNamespace(session=object(), commit=lambda: commits.append(True))
    monkeypatch.setattr(NativeExecutionStore, "record_bounded_refinement", lambda self, **values: captured.append(values))
    owner = object.__new__(SemanticStepApplicationService)
    owner.database, owner.capability = SimpleNamespace(unit_of_work=unit_of_work), capability
    owner.assemble_input = lambda _: semantic_input
    owner.result_for_step = lambda _: None
    owner.admit = admission
    return owner, captured, commits


class ControlledCapability:
    def __init__(self, first, revised, *, revised_usage=None):
        self.first, self.revised, self.calls, self.feedback = first, revised, [], None
        self.last_usage = asdict(ModelUsage(total_tokens=17))
        self.revised_usage = asdict(ModelUsage(unknown=True)) if revised_usage is None else revised_usage
        self.last_semantic_observations = ()

    def execute(self, value):
        self.calls.append(("execute", value.basis_fingerprint))
        self.last_semantic_observations = ({"stage": "INITIAL_CANDIDATE", "output_sha256": "a" * 64},)
        if isinstance(self.first, Exception):
            raise self.first
        return self.first

    def refine(self, value, *, validation_feedback):
        self.calls.append(("refine", value.basis_fingerprint))
        self.feedback = validation_feedback
        self.last_usage = self.revised_usage
        self.last_semantic_observations = ({"stage": "REVISED_CANDIDATE", "output_sha256": "c" * 64},)
        if isinstance(self.revised, Exception):
            raise self.revised
        return self.revised


def test_revised_admission_failure_retains_exact_candidate_lineage_and_actual_safe_feedback(monkeypatch):
    sentinel = "private-provider-key-sentinel"
    monkeypatch.setenv("SPG_DEEPSEEK_API_KEY", sentinel)
    value, first = basis()
    revised = first.model_copy(update={"bounded_summary": "Revised candidate contains untrusted prose " + sentinel})
    capability = ControlledCapability(first, revised)
    calls = []
    def admission(*args):
        calls.append(args[1])
        raise ValueError("INTENT_COMPLETENESS_MISMATCH: current requirement " + sentinel)
    owner, records, commits = service(monkeypatch, capability, value, admission)
    with pytest.raises(SemanticStepRefinementExhausted, match="INTENT_COMPLETENESS_MISMATCH"):
        owner.execute(value.work_id)
    assert [kind for kind, _ in capability.calls] == ["execute", "refine"]
    assert all(fingerprint == value.basis_fingerprint for _, fingerprint in capability.calls)
    assert len(records) == len(commits) == 1 and records[0]["converged"] is False
    record, diag = records[0], records[0]["diagnostic_evidence"]
    assert diag["first_validation_feedback"] == capability.feedback
    assert sentinel not in capability.feedback and "[REDACTED]" in capability.feedback
    assert diag["failure_stage"] == "REVISED_ADMISSION"
    assert diag["second_failure"]["validator_code"] == "INTENT_COMPLETENESS_MISMATCH"
    assert diag["second_error_type"] == "ValueError"
    lineage = diag["candidate_lineage"]
    assert lineage[0]["candidate"]["candidate_fingerprint"] != lineage[1]["candidate"]["candidate_fingerprint"]
    assert lineage[1]["parent_candidate_fingerprint"] == lineage[0]["candidate"]["candidate_fingerprint"]
    assert all(row["candidate"]["work_id"] == str(value.work_id) and row["candidate"]["basis_fingerprint"] == value.basis_fingerprint for row in lineage)
    assert record["model_token_usage"] == {"total_tokens": None, "unknown": True}
    assert diag["budget"] == {"candidate_attempt_count": 2, "candidate_attempt_limit": 2,
        "feedback_attempt_count": 1, "feedback_attempt_limit": 1, "observation_is_authority": False}
    serialized = json.dumps(diag)
    assert sentinel not in serialized and "Revised candidate contains" not in serialized
    assert first.model_dump(mode="json")["bounded_summary"] == "Controlled candidate direction only."


def test_revised_provider_failure_preserves_typed_safe_reason_with_unknown_numeric_usage(monkeypatch):
    value, first = basis()
    error = ModelProviderError(ModelFailureKind.TIMEOUT_OR_NETWORK, "unretained raw HTTP body",
        request_sent=True, usage_unknown=True, retryable=True, request_id="semantic-request-safe")
    capability = ControlledCapability(first, error)
    def admission(*args):
        raise SteeringInvariantViolation("DESIGN cannot close toward PRODUCE without a current production proposal")
    owner, records, _ = service(monkeypatch, capability, value, admission)
    with pytest.raises(ModelProviderError) as raised:
        owner.execute(value.work_id)
    assert raised.value is error and len(capability.calls) == 2
    diag = records[0]["diagnostic_evidence"]
    assert diag["failure_stage"] == "REVISED_PROVIDER_CANDIDATE"
    assert diag["candidate_lineage"][1]["candidate"] is None
    assert diag["candidate_lineage"][1]["parent_candidate_fingerprint"]
    assert diag["second_failure"]["code"] == "SEMANTIC_PROVIDER_FAILURE"
    observation = diag["second_failure"]["provider"]
    assert observation["provider_failure"]["kind"] == "TIMEOUT_OR_NETWORK"
    assert observation["usage"]["total_tokens"] is None and observation["transport_retry_count"] is None
    assert "unretained raw HTTP body" not in json.dumps(diag)


def test_revised_provider_failure_keeps_actual_complete_usage_in_owner_aggregate(monkeypatch):
    value, first = basis()
    usage = ModelUsage(input_tokens=13, output_tokens=10, cached_tokens=0, reasoning_tokens=0, total_tokens=23)
    error = ModelProviderError(ModelFailureKind.INCOMPLETE_RESPONSE, "unretained response body",
        request_sent=True, usage_unknown=False, retryable=True, observed_usage=usage, transport_retry_count=1)
    capability = ControlledCapability(first, error, revised_usage=asdict(usage))
    def admission(*args):
        raise SteeringInvariantViolation("DESIGN cannot close toward PRODUCE without a current production proposal")
    owner, records, _ = service(monkeypatch, capability, value, admission)
    with pytest.raises(ModelProviderError) as raised:
        owner.execute(value.work_id)
    assert raised.value is error and len(capability.calls) == 2
    assert records[0]["model_token_usage"] == {"total_tokens": 40, "unknown": False}
    failure = records[0]["diagnostic_evidence"]["second_failure"]["provider"]
    assert failure["usage"]["total_tokens"] == 23 and failure["transport_retry_count"] == 1
    assert records[0]["diagnostic_evidence"]["budget"]["candidate_attempt_limit"] == 2


def test_provider_parse_then_revised_admission_failure_keeps_distinct_stages(monkeypatch):
    value, revised = basis()
    try:
        raise SteeringInvariantViolation("Semantic reasoning Provider returned an invalid structured result") from ValueError("unsafe path detail")
    except SteeringInvariantViolation as initial:
        capability = ControlledCapability(initial, revised)
    def admission(*args):
        raise ValueError("INTENT_COMPLETENESS_MISMATCH: revised candidate still lacks required evidence")
    owner, records, _ = service(monkeypatch, capability, value, admission)
    with pytest.raises(SemanticStepRefinementExhausted):
        owner.execute(value.work_id)
    diag = records[0]["diagnostic_evidence"]
    assert diag["candidate_lineage"][0]["candidate"] is None
    assert diag["candidate_lineage"][0]["stage"] == "INITIAL_PROVIDER_VALIDATION"
    assert diag["candidate_lineage"][0]["provider_observations"][0]["output_sha256"] == "a" * 64
    assert diag["candidate_lineage"][1]["stage"] == diag["failure_stage"] == "REVISED_ADMISSION"
    assert diag["candidate_lineage"][1]["candidate"]["step_id"] == str(value.step.id)
    assert diag["first_validation_feedback"] == capability.feedback
    assert "unsafe path detail" not in json.dumps(diag)


@pytest.mark.parametrize("usage,expected", [({"total_tokens": 0, "unknown": False}, {"total_tokens": 17, "unknown": False}),
    ({"total_tokens": None, "unknown": True}, {"total_tokens": None, "unknown": True})])
def test_successful_refinement_keeps_same_budget_and_truthful_usage(monkeypatch, usage, expected):
    value, first = basis()
    revised = first.model_copy(update={"decisions": ("Revise the same governed direction",)})
    capability = ControlledCapability(first, revised, revised_usage=usage)
    calls = []
    result = SimpleNamespace(id=uuid4(), completion_satisfied=True)
    def admission(_value, candidate):
        calls.append(candidate)
        if len(calls) == 1:
            raise SteeringInvariantViolation("DESIGN cannot close toward PRODUCE without a current production proposal")
        return result
    owner, records, _ = service(monkeypatch, capability, value, admission)
    assert owner.execute(value.work_id) is result
    assert records[0]["converged"] is True and len(capability.calls) == 2
    assert records[0]["model_token_usage"] == expected
    diag = records[0]["diagnostic_evidence"]
    assert diag["failure_stage"] is None and diag["second_failure"] is None
    assert diag["candidate_lineage"][1]["stage"] == "ADMITTED"
    assert diag["candidate_lineage"][1]["parent_candidate_fingerprint"]


def test_stale_revised_basis_remains_superseded_and_is_not_retried(monkeypatch):
    value, first = basis()
    capability = ControlledCapability(first, first)
    calls = []
    def admission(*args):
        calls.append(True)
        if len(calls) == 1:
            raise ValueError("INTENT_COMPLETENESS_MISMATCH: first rejection")
        raise StaleSemanticStepCandidate("Current governed basis changed")
    owner, records, _ = service(monkeypatch, capability, value, admission)
    with pytest.raises(StaleSemanticStepCandidate):
        owner.execute(value.work_id)
    assert len(capability.calls) == 2 and records[0]["superseded"] is True
    assert records[0]["diagnostic_evidence"]["second_failure"]["code"] == "SEMANTIC_BASIS_CHANGED"


def test_initial_authority_rejection_does_not_receive_new_refinement_or_observation(monkeypatch):
    value, first = basis()
    capability = ControlledCapability(first, first)
    def admission(*args):
        raise SteeringInvariantViolation("Semantic result cannot silently add Human constraints")
    owner, records, _ = service(monkeypatch, capability, value, admission)
    with pytest.raises(SteeringInvariantViolation, match="cannot silently add"):
        owner.execute(value.work_id)
    assert len(capability.calls) == 1 and records == []


# Real provider adapter contract with a controlled Runtime; these are fixtures.

def semantic_provider_input():
    return SimpleNamespace(work_id=uuid4(), steering_plan_revision_id=uuid4(),
        step=SimpleNamespace(id=uuid4(), type=SteeringStepType.DESIGN),
        basis_fingerprint="a" * 64, constraints=(),
        reality_refs=(RealityReference(kind=RealityReferenceKind.WORK, identity=uuid4()),),
        model_dump=lambda **options: {"step": {"type": "DESIGN"}})


def test_semantic_revision_schema_failure_preserves_observed_candidate_before_parse():
    class Runtime(_Runtime):
        def generate(self, **options):
            result = super().generate(**options)
            if len(self.calls) == 2:
                return replace(result, output_text='{"invalid": "unretained candidate prose"}', request_id="semantic-revised-invalid")
            return result
    runtime = Runtime()
    capability = DeepSeekSemanticStepCapability(runtime)
    value = semantic_provider_input()
    original = capability.execute(value)
    with pytest.raises(SteeringInvariantViolation):
        capability.refine(value, validation_feedback="DESIGN cannot close toward PRODUCE without a current production proposal")
    assert len(runtime.calls) == 2 and original.basis_fingerprint == value.basis_fingerprint
    observed = capability.last_semantic_observations
    assert len(observed) == 1 and observed[0]["stage"] == "REVISED_CANDIDATE"
    assert observed[0]["outcome"] == "RESPONSE_OBSERVED" and len(observed[0]["output_sha256"]) == 64
    assert observed[0]["model"]["request_id"] == "semantic-revised-invalid"
    assert observed[0]["model"]["usage"]["total_tokens"] == 42
    assert "unretained candidate prose" not in json.dumps(observed)
    assert capability.last_result.request_id == "semantic-revised-invalid"


def test_semantic_revision_provider_failure_clears_success_and_retains_only_typed_fields(monkeypatch):
    sentinel = "private-provider-key-sentinel"
    monkeypatch.setenv("SPG_DEEPSEEK_API_KEY", sentinel)
    class Runtime(_Runtime):
        def generate(self, **options):
            if self.calls:
                self.calls.append(options)
                raise ModelProviderError(ModelFailureKind.INVALID_MODEL_OR_REQUEST, "raw HTTP " + sentinel,
                    request_sent=True, usage_unknown=False, retryable=False,
                    provider_status="400", termination_reason="invalid_request", request_id="semantic-failed-request")
            return super().generate(**options)
    runtime = Runtime()
    capability = DeepSeekSemanticStepCapability(runtime)
    value = semantic_provider_input()
    capability.execute(value)
    with pytest.raises(ModelProviderError):
        capability.refine(value, validation_feedback="Same governed basis")
    observed = capability.last_semantic_observations
    assert len(runtime.calls) == 2 and len(observed) == 1 and capability.last_result is None
    assert observed[0]["stage"] == "REVISED_CANDIDATE" and observed[0]["outcome"] == "PROVIDER_FAILURE"
    failure = observed[0]["model"]
    assert failure["provider_failure"]["request_id"] == "semantic-failed-request"
    assert failure["usage"]["total_tokens"] is None and failure["transport_retry_count"] is None
    assert capability.last_usage["total_tokens"] is None and capability.last_usage["unknown"] is True
    assert sentinel not in json.dumps(observed) and "raw HTTP" not in json.dumps(observed)


def test_existing_wire_repair_retains_both_candidate_hashes_and_unknown_usage_without_new_calls():
    class Runtime(_Runtime):
        def generate(self, **options):
            result = super().generate(**options)
            if len(self.calls) == 1:
                payload = json.loads(result.output_text)
                del payload["disposition"]
                return replace(result, output_text=json.dumps(payload), request_id="semantic-wire-original")
            return replace(result, request_id="semantic-wire-revised", usage=ModelUsage(unknown=True))
    runtime = Runtime()
    capability = DeepSeekSemanticStepCapability(runtime)
    value = semantic_provider_input()
    candidate = capability.execute(value)
    assert candidate.completion_claimed and len(runtime.calls) == 2
    observed = capability.last_semantic_observations
    assert [row["stage"] for row in observed] == ["INITIAL_CANDIDATE", "WIRE_REPAIR_CANDIDATE"]
    assert observed[0]["output_sha256"] != observed[1]["output_sha256"]
    assert observed[0]["model"]["usage"]["total_tokens"] == 42
    assert observed[1]["model"]["usage"]["total_tokens"] is None
    assert capability.last_usage["total_tokens"] is None and capability.last_usage["unknown"] is True
    assert all(row["basis_fingerprint"] == value.basis_fingerprint for row in observed)


def test_scope_unknown_or_failed_request_cannot_turn_prior_observed_subtotal_into_complete_usage(exact_source):
    value, proposal, capability, runtime = scope_fixture(exact_source)
    capability.last_usage = asdict(ModelUsage(input_tokens=11, total_tokens=17))
    validation = capability.validate_production_scope(value, proposal)
    assert validation.missing_acceptance_requirements == () and len(runtime.calls) == 1
    assert capability.last_usage["total_tokens"] is None and capability.last_usage["unknown"] is True
    assert all(number is None for key, number in capability.last_usage.items() if key != "unknown")
    capability.last_usage = asdict(ModelUsage(input_tokens=11, total_tokens=17))
    def failed(**options):
        runtime.calls.append(options)
        raise ModelProviderError(ModelFailureKind.TIMEOUT_OR_NETWORK, "unretained HTTP body",
            request_sent=True, usage_unknown=True, retryable=True)
    runtime.generate = failed
    with pytest.raises(ModelProviderError):
        capability.validate_production_scope(value, proposal)
    assert len(runtime.calls) == 2
    assert capability.last_usage["total_tokens"] is None and capability.last_usage["unknown"] is True
    assert all(number is None for key, number in capability.last_usage.items() if key != "unknown")


def test_scope_failure_keeps_actual_complete_usage_with_prior_observed_usage(exact_source):
    value, proposal, capability, runtime = scope_fixture(exact_source)
    capability.last_usage = asdict(ModelUsage(input_tokens=11, output_tokens=6, cached_tokens=0,
        reasoning_tokens=0, total_tokens=17))
    observed_usage = ModelUsage(input_tokens=13, output_tokens=10, cached_tokens=0,
        reasoning_tokens=0, total_tokens=23)
    def failed(**options):
        runtime.calls.append(options)
        raise ModelProviderError(ModelFailureKind.INCOMPLETE_RESPONSE, "unretained response body",
            request_sent=True, usage_unknown=False, retryable=True, observed_usage=observed_usage,
            transport_retry_count=0)
    runtime.generate = failed
    with pytest.raises(ModelProviderError):
        capability.validate_production_scope(value, proposal)
    assert len(runtime.calls) == 1
    assert capability.last_usage == {"input_tokens": 24, "output_tokens": 16,
        "cached_tokens": 0, "reasoning_tokens": 0, "total_tokens": 40, "unknown": False}
