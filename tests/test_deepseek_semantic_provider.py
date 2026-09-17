import json
from types import SimpleNamespace
from uuid import UUID

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
