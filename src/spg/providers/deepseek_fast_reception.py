"""Small hosted Fast Reception candidate over the shared model runtime."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from time import monotonic
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from spg.application.wic_reception import apply_fast_grounding_policy
from spg.domain.interaction import InteractionInterpretationInput
from spg.domain.model_runtime import ModelPurpose, WattModelRuntime
from spg.domain.wic_reception import FastContextCard, FastReceptionCandidate, FastReceptionVisibility


class _FastPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provisional_turn_intent: str
    captured_object: str | None
    captured_explicit_constraints: tuple[str, ...]
    detected_correction: str | None
    detected_human_owned_decision: str | None
    confidence: float = Field(ge=0, le=1)
    meaningful_sentence: str


class DeepSeekFastReceptionCapability:
    def __init__(self, runtime: WattModelRuntime) -> None:
        self.runtime = runtime
        self.last_failure_provenance = None

    def receive(self, basis: InteractionInterpretationInput, card: FastContextCard, turn_id: UUID) -> FastReceptionCandidate:
        started_at = datetime.now(UTC); started = monotonic(); first_delta = None

        def delta(value: str) -> None:
            nonlocal first_delta
            if value and first_delta is None: first_delta = (monotonic() - started) * 1000

        latest = basis.records[-1]
        self.last_failure_provenance = None
        profile = self.runtime.profile(ModelPurpose.WIC_FAST_RECEPTION)
        try:
            result = self.runtime.generate(
            purpose=ModelPurpose.WIC_FAST_RECEPTION,
            instructions=(
                "Extract only explicit meaning for an immediate provisional receipt. "
                "Do not plan, recommend, infer preferences, decide privacy/retention/cost, "
                "declare readiness, or create Work. Use only the supplied turn and card. "
                "The sentence must show the key grounded object, correction, constraint, "
                "question, or Human-owned decision; otherwise use low confidence."
            ),
            input_text=json.dumps({
                "latest_human_turn": latest.content,
                "card": card.model_dump(mode="json", exclude={
                    "built_at", "serialized_characters", "serialized_bytes",
                    "estimated_tokens", "build_latency_ms",
                }),
            }, ensure_ascii=False, separators=(",", ":")),
            output_schema=_FastPayload.model_json_schema(),
                on_output_delta=delta,
            )
        except Exception as error:
            self.last_failure_provenance = {
                "provider": profile.provider.value,
                "model": profile.model,
                "profile": profile.identity,
                "first_delta_ms": first_delta,
                "request_sent": getattr(error, "request_sent", None),
                "usage_unknown": getattr(error, "usage_unknown", None),
                "retryable": getattr(error, "retryable", None),
            }
            raise
        payload = _FastPayload.model_validate_json(result.output_text)
        ready = (monotonic() - started) * 1000
        candidate = FastReceptionCandidate(
            interaction_id=basis.interaction.id, turn_id=turn_id,
            source_record_id=latest.id, basis_fingerprint=basis.basis_fingerprint,
            fast_context_fingerprint=card.source_fingerprint,
            active_work_id=card.active_work_id, active_work_revision_id=card.active_work_revision_id,
            provisional_turn_intent=payload.provisional_turn_intent,
            captured_object=payload.captured_object, current_focus=card.current_focus,
            captured_explicit_constraints=payload.captured_explicit_constraints,
            detected_correction=payload.detected_correction,
            detected_human_owned_decision=payload.detected_human_owned_decision,
            confidence=payload.confidence,
            grounding_references=(f"INTERACTION_RECORD:{latest.id}", *card.source_references),
            meaningful_sentence=payload.meaningful_sentence,
            provider=result.provider.value, model=result.effective_model or result.requested_model,
            profile=profile.identity, started_at=started_at, first_delta_ms=first_delta,
            candidate_ready_ms=ready, provider_request_id=result.request_id,
            input_tokens=result.usage.input_tokens, output_tokens=result.usage.output_tokens,
            total_tokens=result.usage.total_tokens, retry_count=result.retry_count,
            visibility_disposition=FastReceptionVisibility.SHADOW,
            policy_disposition=FastReceptionVisibility.SAFE_TO_EMIT,
        )
        return apply_fast_grounding_policy(candidate, basis, card)
