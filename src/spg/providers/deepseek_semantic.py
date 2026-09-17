"""DeepSeek adapter for governed semantic Steering Step execution."""

from __future__ import annotations

from dataclasses import asdict

from spg.domain.model_runtime import ModelPurpose, StructuredModelResult, WattModelRuntime
from spg.domain.steering import (
    SemanticResultKind,
    SemanticStepInput,
    SemanticStepResultCandidate,
    SteeringStepType,
)
from spg.providers.codex_semantic import (
    CodexSdkSemanticStepCapability,
    _admitted_derived_constraints,
)


class DeepSeekSemanticStepCapability:
    """Execute one read-only Steering semantic Step through Watt model runtime."""

    provider_identity = "deepseek-responses:steering-semantic"

    def __init__(self, runtime: WattModelRuntime) -> None:
        self.runtime = runtime
        self.profile = runtime.profile(ModelPurpose.STEERING_SEMANTIC)
        self.last_result: StructuredModelResult | None = None
        self.last_usage: dict[str, object] | None = None

    def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
        result = self.runtime.generate(
            purpose=ModelPurpose.STEERING_SEMANTIC,
            instructions=CodexSdkSemanticStepCapability._instruction(input),
            input_text="Return the governed semantic Steering result for this exact Step.",
            output_schema=CodexSdkSemanticStepCapability.output_schema(),
        )
        payload = (
            CodexSdkSemanticStepCapability._parse_payload_ignoring_annotations(
                result.output_text
            )
        )
        self.last_result = result
        self.last_usage = asdict(result.usage)
        kind = (
            SemanticResultKind.DESIGN_DIRECTION
            if input.step.type is SteeringStepType.DESIGN
            else SemanticResultKind.WORK_REFINEMENT
        )
        return SemanticStepResultCandidate(
            work_id=input.work_id,
            steering_plan_revision_id=input.steering_plan_revision_id,
            step_id=input.step.id,
            step_type=input.step.type,
            basis_fingerprint=input.basis_fingerprint,
            result_kind=kind,
            bounded_summary=payload.bounded_summary,
            decisions=payload.decisions,
            derived_constraints=_admitted_derived_constraints(payload, input),
            evidence_refs=input.reality_refs,
            unresolved_questions=payload.unresolved_questions,
            authority_assessment=payload.authority_assessment,
            human_attention_recommendation=(
                payload.human_attention_recommendation
            ),
            proposed_production=payload.domain_production_proposal(),
            reasoning_provider_identity=(
                "deepseek-responses:steering-semantic:request:"
                f"{result.request_id or 'unknown'}"
            ),
            completion_claimed=payload.completion_claimed,
        )

    def close(self) -> None:
        self.runtime.close()
