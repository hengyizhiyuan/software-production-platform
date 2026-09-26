import json
from dataclasses import replace
from types import SimpleNamespace
from uuid import UUID
import pytest

from spg.domain.model_runtime import (
    ModelProfile,
    ModelProvider,
    ModelPurpose,
    ModelTiming,
    ModelUsage,
    StructuredModelResult,
)
from spg.domain.steering import (
    RealityReference,
    RealityReferenceKind,
    SemanticResultKind,
    SteeringStepType,
    SteeringInvariantViolation,
)
from spg.providers.deepseek_semantic import DeepSeekSemanticStepCapability


class _Runtime:
    def __init__(self) -> None:
        self.calls = []
        self.closed = False

    def profile(self, purpose):
        assert purpose is ModelPurpose.STEERING_SEMANTIC
        return ModelProfile(
            purpose=purpose,
            provider=ModelProvider.DEEPSEEK,
            model="deepseek-flash",
            reasoning_effort=None,
            timeout_seconds=30,
        )

    def generate(self, **options):
        self.calls.append(options)
        return StructuredModelResult(
            output_text=json.dumps({
                "bounded_summary": "The bounded design issue is resolved.",
                "decisions": ["Use one static page with a verified button behavior."],
                "derived_constraints": [],
                "proposed_production": None,
                "disposition": {
                    "state": "RESOLVED",
                    "authority_assessment": "WITHIN_AUTHORITY",
                    "unresolved_questions": [],
                    "human_attention_recommendation": None,
                    "completion_claimed": True,
                },
            }),
            provider=ModelProvider.DEEPSEEK,
            requested_model="deepseek-flash",
            effective_model="deepseek-flash",
            request_id="semantic-1",
            usage=ModelUsage(total_tokens=42),
            timing=ModelTiming(completed_seconds=1.0),
        )

    def close(self):
        self.closed = True


def test_deepseek_semantic_executes_the_governed_steering_purpose() -> None:
    runtime = _Runtime()
    capability = DeepSeekSemanticStepCapability(runtime)
    work_id = UUID(int=1)
    revision_id = UUID(int=2)
    step_id = UUID(int=3)
    input_value = SimpleNamespace(
        work_id=work_id,
        steering_plan_revision_id=revision_id,
        step=SimpleNamespace(id=step_id, type=SteeringStepType.DESIGN),
        basis_fingerprint="a" * 64,
        constraints=(),
        reality_refs=(RealityReference(kind=RealityReferenceKind.WORK, identity=work_id),),
        model_dump=lambda **_options: {
            "work_id": str(work_id),
            "steering_plan_revision_id": str(revision_id),
            "step": {"id": str(step_id), "type": "DESIGN"},
            "basis_fingerprint": "a" * 64,
        },
    )

    result = capability.execute(input_value)

    assert runtime.calls[0]["purpose"] is ModelPurpose.STEERING_SEMANTIC
    assert result.result_kind is SemanticResultKind.DESIGN_DIRECTION
    assert result.completion_claimed is True
    assert result.reasoning_provider_identity.endswith("request:semantic-1")
    assert capability.last_usage == {"input_tokens": None, "output_tokens": None,
                                     "cached_tokens": None, "reasoning_tokens": None,
                                     "total_tokens": 42, "unknown": False}
    capability.close()
    assert runtime.closed is True


def test_semantic_refinement_uses_same_input_and_explicit_validation_feedback() -> None:
    runtime = _Runtime()
    capability = DeepSeekSemanticStepCapability(runtime)
    input_value = SimpleNamespace(
        work_id=UUID(int=1), steering_plan_revision_id=UUID(int=2),
        step=SimpleNamespace(id=UUID(int=3), type=SteeringStepType.DESIGN),
        basis_fingerprint="a" * 64, constraints=(),
        reality_refs=(RealityReference(kind=RealityReferenceKind.WORK, identity=UUID(int=1)),),
        model_dump=lambda **_options: {"step": {"type": "DESIGN"}},
    )
    candidate = capability.refine(
        input_value,
        validation_feedback="DESIGN cannot close toward PRODUCE without a current production proposal",
    )
    assert candidate.basis_fingerprint == input_value.basis_fingerprint
    assert candidate.step_id == input_value.step.id
    assert "previous candidate was rejected" in runtime.calls[0]["input_text"]
    assert "Do not add Human constraints, permissions" in runtime.calls[0]["input_text"]


def test_missing_disposition_gets_one_typed_repair_without_loose_admission() -> None:
    class Runtime(_Runtime):
        def generate(self, **options):
            result = super().generate(**options)
            if len(self.calls) == 1:
                candidate = json.loads(result.output_text)
                del candidate["disposition"]
                return replace(result, output_text=json.dumps(candidate))
            return result

    runtime = Runtime()
    value = SimpleNamespace(
        work_id=UUID(int=1), steering_plan_revision_id=UUID(int=2),
        step=SimpleNamespace(id=UUID(int=3), type=SteeringStepType.DESIGN),
        basis_fingerprint="a" * 64, constraints=(),
        reality_refs=(RealityReference(kind=RealityReferenceKind.WORK, identity=UUID(int=1)),),
        model_dump=lambda **_options: {"step": {"type": "DESIGN"}},
    )
    result = DeepSeekSemanticStepCapability(runtime).execute(value)
    assert result.completion_claimed is True
    assert len(runtime.calls) == 2
    assert "prior result omitted" in runtime.calls[1]["input_text"].lower()

    class StillMalformed(Runtime):
        def generate(self, **options):
            result = _Runtime.generate(self, **options)
            candidate = json.loads(result.output_text)
            del candidate["disposition"]
            return replace(result, output_text=json.dumps(candidate))

    broken = StillMalformed()
    with pytest.raises(SteeringInvariantViolation):
        DeepSeekSemanticStepCapability(broken).execute(value)
    assert len(broken.calls) == 2


def test_incomplete_unresolved_disposition_gets_one_strict_repair() -> None:
    class Runtime(_Runtime):
        def generate(self, **options):
            result = super().generate(**options)
            candidate = json.loads(result.output_text)
            candidate["disposition"] = {
                "state": "UNRESOLVED",
                "authority_assessment": "UNCERTAIN",
                "unresolved_questions": ["Which admitted direction should this Step use?"],
                "human_attention_recommendation": "Choose the bounded direction.",
                "completion_claimed": False,
            }
            if len(self.calls) == 1:
                del candidate["disposition"]["human_attention_recommendation"]
                del candidate["disposition"]["completion_claimed"]
            return replace(result, output_text=json.dumps(candidate))

    value = SimpleNamespace(
        work_id=UUID(int=1), steering_plan_revision_id=UUID(int=2),
        step=SimpleNamespace(id=UUID(int=3), type=SteeringStepType.DESIGN),
        basis_fingerprint="a" * 64, constraints=(),
        reality_refs=(RealityReference(kind=RealityReferenceKind.WORK, identity=UUID(int=1)),),
        model_dump=lambda **_options: {"step": {"type": "DESIGN"}},
    )
    runtime = Runtime()
    result = DeepSeekSemanticStepCapability(runtime).execute(value)

    assert len(runtime.calls) == 2
    assert "prior disposition omitted" in runtime.calls[1]["input_text"].lower()
    assert result.completion_claimed is False
    assert result.human_attention_recommendation == "Choose the bounded direction."

    class ConflictingAuthority(Runtime):
        def generate(self, **options):
            result = super().generate(**options)
            candidate = json.loads(result.output_text)
            candidate["disposition"]["authority_assessment"] = "WITHIN_AUTHORITY"
            return replace(result, output_text=json.dumps(candidate))

    conflicting = ConflictingAuthority()
    with pytest.raises(SteeringInvariantViolation):
        DeepSeekSemanticStepCapability(conflicting).execute(value)
    assert len(conflicting.calls) == 1


def test_invalid_json_gets_exactly_one_strict_repair() -> None:
    class Runtime(_Runtime):
        def generate(self, **options):
            result = super().generate(**options)
            if len(self.calls) == 1:
                return replace(result, output_text=result.output_text + " trailing")
            return result

    value = SimpleNamespace(
        work_id=UUID(int=1), steering_plan_revision_id=UUID(int=2),
        step=SimpleNamespace(id=UUID(int=3), type=SteeringStepType.DESIGN),
        basis_fingerprint="a" * 64, constraints=(),
        reality_refs=(RealityReference(kind=RealityReferenceKind.WORK, identity=UUID(int=1)),),
        model_dump=lambda **_options: {"step": {"type": "DESIGN"}},
    )
    runtime = Runtime()
    result = DeepSeekSemanticStepCapability(runtime).execute(value)
    assert result.completion_claimed is True
    assert len(runtime.calls) == 2
    assert "not one valid complete json value" in runtime.calls[1]["input_text"].lower()

    class StillMalformed(_Runtime):
        def generate(self, **options):
            result = super().generate(**options)
            return replace(result, output_text=result.output_text + " trailing")

    broken = StillMalformed()
    with pytest.raises(SteeringInvariantViolation):
        DeepSeekSemanticStepCapability(broken).execute(value)
    assert len(broken.calls) == 2


def test_missing_production_field_gets_one_strict_repair() -> None:
    proposal = {
        "target_kind": "CODE_WORK",
        "objective": "Build the bounded countdown page",
        "artifact_targets": [],
        "code_targets": ["index.html"],
        "allowed_areas": [],
        "forbidden_areas": [],
        "verification_expectation": "Verify the countdown interaction",
    }

    class Runtime(_Runtime):
        def generate(self, **options):
            result = super().generate(**options)
            candidate = json.loads(result.output_text)
            candidate["proposed_production"] = dict(proposal)
            if len(self.calls) == 1:
                del candidate["proposed_production"]["verification_expectation"]
            return replace(result, output_text=json.dumps(candidate))

    value = SimpleNamespace(
        work_id=UUID(int=1), steering_plan_revision_id=UUID(int=2),
        step=SimpleNamespace(id=UUID(int=3), type=SteeringStepType.DESIGN),
        basis_fingerprint="a" * 64, constraints=(),
        reality_refs=(RealityReference(kind=RealityReferenceKind.WORK, identity=UUID(int=1)),),
        model_dump=lambda **_options: {"step": {"type": "DESIGN"}},
    )
    runtime = Runtime()
    result = DeepSeekSemanticStepCapability(runtime).execute(value)

    assert result.proposed_production is not None
    assert result.proposed_production.verification_expectation == (
        "Verify the countdown interaction"
    )
    assert len(runtime.calls) == 2
    assert "omitted one or more required fields" in runtime.calls[1]["input_text"]
