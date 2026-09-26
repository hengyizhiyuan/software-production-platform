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
from spg.providers.semantic_wire import (
    SemanticStepWireContract,
    _admitted_derived_constraints,
)

LOGGER = logging.getLogger(__name__)


def _missing_selected_disposition_fields(error: ValidationError, raw: str) -> bool:
    """Recognize an incomplete wire envelope without relaxing semantic validation."""

    try:
        decoded = json.loads(raw)
    except (ValueError, TypeError):
        return False
    if not isinstance(decoded, dict) or not isinstance(decoded.get("disposition"), dict):
        return False
    variant = {
        "RESOLVED": "_SemanticProviderResolvedDisposition",
        "UNRESOLVED": "_SemanticProviderUnresolvedDisposition",
        "AUTHORITY_EXPANSION": "_SemanticProviderAuthorityExpansionDisposition",
    }.get(decoded["disposition"].get("state"))
    if variant is None:
        return False
    selected = []
    for issue in error.errors():
        location = tuple(issue.get("loc", ()))
        if location[:1] != ("disposition",):
            return False
        if len(location) >= 3 and location[1] == variant:
            selected.append(issue)
    return bool(selected) and all(
        issue.get("type") == "missing"
        and len(tuple(issue.get("loc", ()))) == 3
        and tuple(issue.get("loc", ()))[-1] in {
            "state", "authority_assessment", "unresolved_questions",
            "human_attention_recommendation", "completion_claimed",
        }
        for issue in selected
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
        instruction = SemanticStepWireContract._instruction(input)
        schema = SemanticStepWireContract.output_schema()
        result = self.runtime.generate(
            purpose=ModelPurpose.STEERING_SEMANTIC,
            instructions=instruction,
            input_text="Return the governed semantic Steering result for this exact Step.",
            output_schema=schema,
        )
        try:
            payload = SemanticStepWireContract._parse_payload_ignoring_annotations(
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
            missing_proposal_fields = (
                isinstance(cause, ValidationError)
                and bool(cause.errors())
                and all(
                    issue.get("type") == "missing"
                    and tuple(issue.get("loc", ()))[:1]
                    == ("proposed_production",)
                    for issue in cause.errors()
                )
            )
            missing_disposition_fields = (
                isinstance(cause, ValidationError)
                and _missing_selected_disposition_fields(cause, result.output_text)
            )
            invalid_json = isinstance(cause, JSONDecodeError)
            if not (
                missing_disposition or missing_proposal_fields
                or missing_disposition_fields or invalid_json
            ):
                raise
            try:
                shape = sorted(json.loads(result.output_text))
            except (ValueError, TypeError):
                shape = ["invalid_json"]
            LOGGER.warning(
                "Steering semantic wire repair request=%s model=%s stage=%s fields=%s output_length=%s attempts=1",
                result.request_id, result.effective_model or result.requested_model,
                "root:json_invalid"
                if invalid_json
                else "payload_validation:missing_proposal_fields"
                if missing_proposal_fields
                else "payload_validation:missing_disposition_fields"
                if missing_disposition_fields
                else "payload_validation:missing_disposition",
                shape, len(result.output_text),
            )
            result = self.runtime.generate(
                purpose=ModelPurpose.STEERING_SEMANTIC,
                instructions=instruction,
                input_text=(
                    "The prior result was not one valid complete JSON value. "
                    if invalid_json else
                    "The prior proposed_production omitted one or more required fields. "
                    if missing_proposal_fields else
                    "The prior disposition omitted one or more required fields. "
                    if missing_disposition_fields else
                    "The prior result omitted the required disposition envelope. "
                ) + (
                    "Return one complete result for the SAME governed Step, including "
                    "all proposed_production fields and every disposition field "
                    "(state, authority_assessment, unresolved_questions, "
                    "human_attention_recommendation, completion_claimed) that truthfully "
                    "matches the supported evidence. "
                    "Do not infer Human authority or loosen the proposal contract. "
                    "Prior candidate:\n" + result.output_text
                ),
                output_schema=schema,
            )
            payload = SemanticStepWireContract._parse_payload_ignoring_annotations(
                result.output_text
            )
        return self._candidate(input, payload, result)

    def refine(
        self, input: SemanticStepInput, *, validation_feedback: str,
    ) -> SemanticStepResultCandidate:
        """One correction against the same immutable basis and admission contract."""
        result = self.runtime.generate(
            purpose=ModelPurpose.STEERING_SEMANTIC,
            instructions=SemanticStepWireContract._instruction(input),
            input_text=(
                "The previous candidate was rejected by the governed semantic "
                "admission boundary: " + validation_feedback + "\n"
                "Return a revised candidate for the SAME Step and Reality basis. "
                "Do not add Human constraints, permissions, credentials, or scope. "
                "If the evidence cannot support completion, state the unresolved "
                "decision truthfully."
            ),
            output_schema=SemanticStepWireContract.output_schema(),
        )
        payload = SemanticStepWireContract._parse_payload_ignoring_annotations(
            result.output_text
        )
        return self._candidate(input, payload, result)

    def _candidate(self, input, payload, result) -> SemanticStepResultCandidate:
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
