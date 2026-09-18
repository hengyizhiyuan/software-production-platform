"""DeepSeek adapter for governed semantic Steering Step execution."""

from __future__ import annotations

from dataclasses import asdict
import logging
import json
from json import JSONDecodeError
from pydantic import ValidationError

from spg.domain.model_runtime import ModelPurpose, StructuredModelResult, WattModelRuntime
from spg.domain.steering import (
    SemanticResultKind,
    SemanticStepInput,
    SemanticStepResultCandidate,
    SteeringStepType,
    SteeringInvariantViolation,
)
from spg.providers.codex_semantic import (
    CodexSdkSemanticStepCapability,
    _admitted_derived_constraints,
)

LOGGER = logging.getLogger(__name__)


class DeepSeekSemanticStepCapability:
    """Execute one read-only Steering semantic Step through Watt model runtime."""

    provider_identity = "deepseek-responses:steering-semantic"

    def __init__(self, runtime: WattModelRuntime) -> None:
        self.runtime = runtime
        self.profile = runtime.profile(ModelPurpose.STEERING_SEMANTIC)
        self.last_result: StructuredModelResult | None = None
        self.last_usage: dict[str, object] | None = None

    def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
        instruction = CodexSdkSemanticStepCapability._instruction(input)
        schema = CodexSdkSemanticStepCapability.output_schema()
        result = self.runtime.generate(
            purpose=ModelPurpose.STEERING_SEMANTIC,
            instructions=instruction,
            input_text="Return the governed semantic Steering result for this exact Step.",
            output_schema=schema,
        )
        try:
            payload = CodexSdkSemanticStepCapability._parse_payload_ignoring_annotations(
                result.output_text
            )
        except SteeringInvariantViolation as error:
            cause = error.__cause__
            # Repair only a missing wire envelope, not conflicting authority or
            # an invalid proposal. The repaired output still passes the exact
            # same typed parser and subsequent governed semantic admission.
            missing_disposition = (
                isinstance(cause, ValidationError)
                and len(cause.errors()) == 1
                and cause.errors()[0].get("loc") == ("disposition",)
                and cause.errors()[0].get("type") == "missing"
            )
            invalid_json = isinstance(cause, JSONDecodeError)
            if not (missing_disposition or invalid_json):
                raise
            try:
                shape = sorted(json.loads(result.output_text))
            except (ValueError, TypeError):
                shape = ["invalid_json"]
            LOGGER.warning(
                "Steering semantic wire repair request=%s model=%s stage=%s fields=%s output_length=%s attempts=1",
                result.request_id, result.effective_model or result.requested_model,
                "root:json_invalid" if invalid_json else "payload_validation:missing_disposition",
                shape, len(result.output_text),
            )
            result = self.runtime.generate(
                purpose=ModelPurpose.STEERING_SEMANTIC,
                instructions=instruction,
                input_text=(
                    "The prior result was not one valid complete JSON value. "
                    if invalid_json else
                    "The prior result omitted the required disposition envelope. "
                ) + (
                    "Return one complete result for the SAME governed Step, including "
                    "a disposition that truthfully matches the supported evidence. "
                    "Do not infer Human authority or loosen the proposal contract. "
                    "Prior candidate:\n" + result.output_text
                ),
                output_schema=schema,
            )
            payload = CodexSdkSemanticStepCapability._parse_payload_ignoring_annotations(
                result.output_text
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
