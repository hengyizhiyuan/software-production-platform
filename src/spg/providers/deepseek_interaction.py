"""DeepSeek adapters for WIC semantics and Human-facing conversation."""

from __future__ import annotations

from dataclasses import asdict, replace
import json
import logging
import re
from time import monotonic
from typing import Callable

from pydantic import ValidationError

from spg.application.response_contract_expression import (
    governed_contract_realizer_instruction,
    response_contract_expression_guidance,
)
from spg.application.conversation import ConversationResponseComposer
from spg.domain.conversation import (
    ConversationContext,
    ConversationResponseCandidate,
    StructuredCollaborationResult,
)
from spg.domain.interaction import (
    InteractionAssessmentCandidate,
    InteractionInterpretationInput,
    InteractionInvariantViolation,
    InteractionSemanticCandidate,
)
from spg.domain.model_runtime import ModelPurpose, StructuredModelResult, WattModelRuntime
from spg.domain.wic_response import (
    GovernedResponseEnvelope,
    GovernedResponseRealization,
)
from spg.providers.codex_interaction import (
    CodexSdkConversationProvider,
    CodexSdkInteractionSemanticCapability,
    CodexSdkWorkInteractionCapability,
    ConversationPipelineEvidence,
    _CoalescedInteractionProviderPayload,
    _ConversationProviderPayload,
    _InteractionSemanticProviderPayload,
    _JsonStringFieldStream,
    _safe_validation_summary,
)


LOGGER = logging.getLogger(__name__)


def _safe_result_shape(value: str) -> str:
    """Log field names and size, never model prose, prompts, or credentials."""
    try:
        parsed = json.loads(_structured_json_text(value))
        fields = sorted(parsed) if isinstance(parsed, dict) else [type(parsed).__name__]
    except ValueError:
        fields = ["invalid_json"]
    return f"fields={fields} length={len(value)}"


def _usage(result: StructuredModelResult) -> dict[str, object]:
    return asdict(result.usage)


_JSON_FENCE = re.compile(r"\A```(?:json)?\s*(.*?)\s*```\Z", re.IGNORECASE | re.DOTALL)


def _structured_json_text(value: str) -> str:
    """Normalize only one complete JSON fence; never salvage arbitrary prose."""

    stripped = value.strip()
    match = _JSON_FENCE.fullmatch(stripped)
    return (match.group(1) if match is not None else stripped).strip()


def _is_root_json_invalid(error: InteractionInvariantViolation) -> bool:
    """Identify syntax-invalid JSON without treating schema rejection as retryable."""

    cause = error.__cause__
    if not isinstance(cause, ValidationError):
        return False
    issues = cause.errors(include_input=False, include_url=False)
    return len(issues) == 1 and issues[0].get("loc") == () and (
        issues[0].get("type") == "json_invalid"
    )


def _is_structured_payload_invalid(error: InteractionInvariantViolation) -> bool:
    """Limit bounded repair to Provider wire/schema validation failures."""

    return isinstance(error.__cause__, ValidationError)


class DeepSeekInteractionSemanticCapability:
    """WIC semantic port implemented through the shared model runtime."""

    provider_identity = "deepseek-responses"

    def __init__(self, runtime: WattModelRuntime) -> None:
        self.runtime = runtime
        profile = runtime.profile(ModelPurpose.WIC_SEMANTIC)
        self.model = profile.model
        self.reasoning_effort = profile.reasoning_effort
        self.last_thread_id: str | None = None
        self.last_turn_id: str | None = None
        self.last_request_id: str | None = None
        self.last_prompt_characters: int | None = None
        self.last_usage: dict[str, object] | None = None
        self.last_retry_count: int | None = None
        self.last_result: StructuredModelResult | None = None

    def interpret_semantics(
        self,
        basis: InteractionInterpretationInput,
        *,
        on_stage: Callable[[str], None] | None = None,
    ) -> InteractionSemanticCandidate:
        instruction = CodexSdkInteractionSemanticCapability.instruction(basis)
        self.last_prompt_characters = len(instruction)
        result = self.runtime.generate(
            purpose=ModelPurpose.WIC_SEMANTIC,
            instructions=instruction,
            input_text="Return the WIC semantic result for the exact supplied basis.",
            output_schema=CodexSdkInteractionSemanticCapability.output_schema(),
            on_stage=on_stage,
        )
        try:
            payload = _InteractionSemanticProviderPayload.model_validate_json(
                _structured_json_text(result.output_text)
            )
        except (ValidationError, ValueError, TypeError) as error:
            raise InteractionInvariantViolation(
                "WIC semantic Provider returned an invalid structured result"
            ) from error
        if on_stage is not None:
            on_stage("semantic_payload_validated")
        self._observe(result)
        return InteractionSemanticCandidate(
            **payload.model_dump(),
            provider_identity=self._result_identity(result, "semantic"),
            model_identity=result.effective_model or result.requested_model,
        )

    def _observe(self, result: StructuredModelResult) -> None:
        self.last_result = result
        self.last_request_id = result.request_id
        self.last_usage = _usage(result)
        self.last_retry_count = result.retry_count

    @staticmethod
    def _result_identity(result: StructuredModelResult, role: str) -> str:
        request = result.request_id or "unknown"
        return f"deepseek-responses:{role}:request:{request}"


class DeepSeekConversationProvider:
    """Conversation expression port implemented through the shared model runtime."""

    provider_identity = "deepseek-responses"

    def __init__(self, runtime: WattModelRuntime) -> None:
        self.runtime = runtime
        profile = runtime.profile(ModelPurpose.CONVERSATION_RESPONSE)
        self.model = profile.model
        self.reasoning_effort = profile.reasoning_effort
        self.last_thread_id: str | None = None
        self.last_turn_id: str | None = None
        self.last_request_id: str | None = None
        self.last_prompt_characters: int | None = None
        self.last_usage: dict[str, object] | None = None
        self.last_retry_count: int | None = None
        self.last_result: StructuredModelResult | None = None

    def respond(
        self,
        context: ConversationContext,
        collaboration: StructuredCollaborationResult,
    ) -> ConversationResponseCandidate:
        return self._respond(context, collaboration, on_response_delta=None)

    def respond_stream(
        self,
        context: ConversationContext,
        collaboration: StructuredCollaborationResult,
        *,
        on_response_delta: Callable[[str], None],
    ) -> ConversationResponseCandidate:
        return self._respond(
            context, collaboration, on_response_delta=on_response_delta
        )

    def _respond(
        self,
        context: ConversationContext,
        collaboration: StructuredCollaborationResult,
        *,
        on_response_delta: Callable[[str], None] | None,
    ) -> ConversationResponseCandidate:
        instruction = CodexSdkConversationProvider.instruction(context, collaboration)
        self.last_prompt_characters = len(instruction)
        extractor = _JsonStringFieldStream("natural_response")

        def receive(delta: str) -> None:
            useful = extractor.feed(delta)
            if useful and on_response_delta is not None:
                on_response_delta(useful)

        result = self.runtime.generate(
            purpose=ModelPurpose.CONVERSATION_RESPONSE,
            instructions=instruction,
            input_text="Return the Human-facing response for this exact handoff.",
            output_schema=CodexSdkConversationProvider.output_schema(),
            on_output_delta=receive if on_response_delta is not None else None,
        )
        try:
            payload = _ConversationProviderPayload.model_validate_json(
                _structured_json_text(result.output_text)
            )
        except (ValidationError, ValueError, TypeError) as error:
            LOGGER.warning(
                "Conversation expression validation failed request=%s model=%s status=completed stage=human_facing_validation issue=%s %s fallback=semantic",
                result.request_id, result.effective_model or result.requested_model,
                _safe_validation_summary(error), _safe_result_shape(result.output_text),
            )
            # Expression is replaceable; the already validated semantic handoff
            # remains the only source of claims. Do not fail the Work turn for
            # malformed wording, and do not invent an answer in the fallback.
            self._observe(result)
            content = next((value.strip() for value in (
                collaboration.direct_answer,
                collaboration.recommended_next_action,
                collaboration.concise_basis,
                collaboration.current_collaboration_focus,
            ) if value and value.strip()), None)
            if content is None:
                raise InteractionInvariantViolation(
                    "Conversation Provider returned an invalid Human-facing result"
                ) from error
            return ConversationResponseCandidate(
                content=content,
                provider_identity=("deepseek-responses:conversation-semantic-fallback:request:"
                                   f"{result.request_id or 'unknown'}"),
                model_identity=result.effective_model or result.requested_model,
            )
        self._observe(result)
        return ConversationResponseCandidate(
            content=payload.natural_response,
            provider_identity=DeepSeekInteractionSemanticCapability._result_identity(
                result, "conversation"
            ),
            model_identity=result.effective_model or result.requested_model,
        )

    def _observe(self, result: StructuredModelResult) -> None:
        self.last_result = result
        self.last_request_id = result.request_id
        self.last_usage = _usage(result)
        self.last_retry_count = result.retry_count


class DeepSeekGovernedResponseRealizer:
    """Expression-only realization of an already governed response envelope."""

    provider_identity = "deepseek-responses:governed-realizer"

    def __init__(self, runtime: WattModelRuntime) -> None:
        self.runtime = runtime
        profile = runtime.profile(ModelPurpose.CONVERSATION_RESPONSE)
        self.model_identity = profile.model
        self.reasoning_effort = profile.reasoning_effort
        self.last_result: StructuredModelResult | None = None

    def realize_stream(
        self,
        envelope: GovernedResponseEnvelope,
        *,
        on_response_delta: Callable[[str], None],
    ) -> GovernedResponseRealization:
        extractor = _JsonStringFieldStream("natural_response")

        def receive(delta: str) -> None:
            useful = extractor.feed(delta)
            if useful:
                on_response_delta(useful)

        instruction = (
            "You are Watt's Governed Response Realizer. The supplied envelope was "
            "already admitted by WIC policy. You own only clear, natural wording and "
            "pacing. Do not reinterpret intent, change Work boundaries, invent facts, "
            "make Human-owned decisions, change readiness, or add production authority. "
            "Preserve every fact, constraint, correction, and authority boundary. "
            "Follow interaction_strategy for the turn intent, primary conversational move, "
            "altitude, and question allowance. When answer_first is true, answer immediately. "
            "When candidate_first is true, offer a concrete, reversible candidate for the "
            "actual object before any question. Treat governed_content as semantic material, not "
            "wording to repeat. Demonstrate understanding by advancing the thinking; "
            "avoid paraphrasing the Human, workflow narration, and questionnaire behavior. "
            "Translate internal terms such as Basis, governed constraints, Work revision, "
            "and admission into plain user-facing language. Distinguish an effect not "
            "requested from an effect proven absent in an artifact. "
            "For MODIFY, start with the proposed delta or its consequence, never with "
            "'I understand' or a restatement of the request. If question_allowed is false, "
            "ask no question and do not reproduce a question from governed_content; otherwise "
            "ask at most max_questions after the useful answer or candidate. Treat the "
            "question-mark count as a hard expression constraint: use none when questions are "
            "disallowed and at most one when one question is allowed; fold any answer choices "
            "into that single sentence. "
            "Never emit any forbidden_claim. Return JSON only with one natural_response "
            "string.\n\nGoverned Response Envelope:\n"
            + response_contract_expression_guidance(envelope.response_contract)
            + json.dumps(
                envelope.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        if envelope.response_contract is not None:
            instruction = governed_contract_realizer_instruction(envelope)
        result = self.runtime.generate(
            purpose=ModelPurpose.CONVERSATION_RESPONSE,
            instructions=instruction,
            input_text="Realize this governed response without changing its semantics.",
            output_schema=CodexSdkConversationProvider.output_schema(),
            on_output_delta=receive,
        )
        try:
            payload = _ConversationProviderPayload.model_validate_json(
                _structured_json_text(result.output_text)
            )
        except (ValidationError, ValueError, TypeError) as error:
            LOGGER.warning(
                "Governed Realizer validation failed request=%s issue=%s %s",
                result.request_id, _safe_validation_summary(error),
                _safe_result_shape(result.output_text),
            )
            raise InteractionInvariantViolation(
                "Governed Response Realizer returned an invalid result"
            ) from error
        self.last_result = result
        return GovernedResponseRealization(
            content=payload.natural_response,
            provider_identity=(
                "deepseek-responses:governed-realizer:request:"
                f"{result.request_id or 'unknown'}"
            ),
            model_identity=result.effective_model or result.requested_model,
            request_id=result.request_id,
            usage=_usage(result),
            timing=asdict(result.timing),
        )


class DeepSeekWorkInteractionCapability(CodexSdkWorkInteractionCapability):
    """Preserve WIC ownership and coalescing over DeepSeek Responses transport."""

    def __init__(self, *, runtime: WattModelRuntime, coalesce_pre_work: bool = True) -> None:
        semantic = DeepSeekInteractionSemanticCapability(runtime)
        conversation = DeepSeekConversationProvider(runtime)
        super().__init__(
            repository_location=".",
            model=semantic.model,
            conversation_model=conversation.model,
            reasoning_effort=semantic.reasoning_effort,
            conversation_reasoning_effort=conversation.reasoning_effort,
            timeout_seconds=runtime.profile(ModelPurpose.WIC_SEMANTIC).timeout_seconds,
            coalesce_pre_work=coalesce_pre_work,
            semantic_capability=semantic,
            conversation_provider=conversation,
        )
        self.runtime = runtime
        self.response_composer = ConversationResponseComposer(conversation)
        self.governed_response_realizer = DeepSeekGovernedResponseRealizer(runtime)

    def close(self) -> None:
        self.runtime.close()

    def interpret_stream_observed(
        self,
        basis: InteractionInterpretationInput,
        *,
        on_response_delta: Callable[[str], None],
        on_pipeline_stage: Callable[[str], None],
    ) -> InteractionAssessmentCandidate:
        """One syntax-only coalesced repair for the shadow-mode pipeline too."""
        try:
            return super().interpret_stream_observed(
                basis, on_response_delta=on_response_delta,
                on_pipeline_stage=on_pipeline_stage,
            )
        except InteractionInvariantViolation as first_error:
            if not (self.pipeline_selection(basis)[0] == "coalesced_pre_work"
                    and _is_root_json_invalid(first_error)):
                raise
            on_pipeline_stage("structured_json_repair_started")
        try:
            # The first response may have streamed provisional text. No second
            # provisional stream is emitted; the settled message replaces it.
            candidate = super().interpret_stream_observed(
                basis, on_response_delta=lambda _delta: None,
                on_pipeline_stage=on_pipeline_stage,
            )
        except InteractionInvariantViolation as second_error:
            if _is_root_json_invalid(second_error):
                raise InteractionInvariantViolation(
                    "Coalesced collaboration Provider returned invalid JSON after "
                    "one bounded structured repair attempt (root:json_invalid; "
                    "bounded_repair_exhausted)"
                ) from second_error
            raise
        evidence = self.last_pipeline_evidence
        if evidence is not None:
            self.last_pipeline_evidence = replace(
                evidence,
                provider_call_count=evidence.provider_call_count + 1,
                coalesced_retry_count=(evidence.coalesced_retry_count or 0) + 1,
            )
        on_pipeline_stage("structured_json_repair_completed")
        return candidate

    def interpret_controlled_stream_observed(
        self,
        basis: InteractionInterpretationInput,
        *,
        on_response_delta: Callable[[str], None],
        on_pipeline_stage: Callable[[str], None],
    ) -> InteractionAssessmentCandidate:
        """Repair one invalid Provider envelope before any Human visibility.

        Controlled WIC deliberately discards semantic-provider prose and realizes
        Human-visible wording only after semantic admission.  That boundary makes
        one bounded repair attempt safe: neither attempt can append a response
        delta, Assessment, Conversation message, or governed Work fact.
        """

        del on_response_delta

        def observe_only(_delta: str) -> None:
            return None

        try:
            return self._interpret(
                basis,
                on_response_delta=observe_only,
                on_pipeline_stage=on_pipeline_stage,
                controlled_semantic_only=True,
            )
        except InteractionInvariantViolation as first_error:
            if not _is_structured_payload_invalid(first_error):
                raise
            on_pipeline_stage("structured_output_repair_started")

        try:
            candidate = self._interpret(
                basis,
                on_response_delta=observe_only,
                on_pipeline_stage=on_pipeline_stage,
                controlled_semantic_only=True,
            )
        except InteractionInvariantViolation as second_error:
            if _is_root_json_invalid(second_error):
                raise InteractionInvariantViolation(
                    "WIC semantic Provider returned invalid JSON after "
                    "one bounded structured repair attempt (root:json_invalid; "
                    "bounded_repair_exhausted)"
                ) from second_error
            if _is_structured_payload_invalid(second_error):
                raise InteractionInvariantViolation(
                    "WIC Provider returned an invalid structured result after one "
                    "bounded repair attempt (schema_invalid; bounded_repair_exhausted)"
                ) from second_error
            raise

        evidence = self.last_pipeline_evidence
        if evidence is not None:
            self.last_pipeline_evidence = replace(
                evidence,
                provider_call_count=evidence.provider_call_count + 1,
                semantic_retry_count=(evidence.semantic_retry_count or 0) + 1,
            )
        on_pipeline_stage("structured_output_repair_completed")
        return candidate

    def _interpret(
        self,
        basis: InteractionInterpretationInput,
        *,
        on_response_delta: Callable[[str], None] | None,
        on_pipeline_stage: Callable[[str], None] | None = None,
        controlled_semantic_only: bool = False,
    ) -> InteractionAssessmentCandidate:
        mode, _reason = self.pipeline_selection(basis)
        if not controlled_semantic_only:
            return super()._interpret(
                basis, on_response_delta=on_response_delta,
                on_pipeline_stage=on_pipeline_stage,
            )
        # Controlled admission always requests semantics only.  PRE_WORK used to
        # reuse the coalesced natural_response and synchronously slice that settled
        # string after governance, which looked like streaming but could not expose
        # progressive Conversation generation.  The governed Realizer now owns the
        # only Human-facing Provider stream for both PRE_WORK and active Work.
        self.last_pipeline_evidence = None
        self.last_collaboration_result = None
        started_at = monotonic()
        semantic = self.semantic_capability.interpret_semantics(
            basis, on_stage=on_pipeline_stage
        )
        self.last_collaboration_result = semantic.collaboration
        self.last_pipeline_evidence = ConversationPipelineEvidence(
            pipeline_mode=(
                "governed_pre_work_semantic"
                if mode == "coalesced_pre_work"
                else "staged"
            ),
            pipeline_reason=(
                "controlled_pre_work_semantics_before_governed_realization"
                if mode == "coalesced_pre_work"
                else "controlled_semantics_before_governed_realization"
            ),
            provider_call_count=1,
            semantic_request_id=self.semantic_capability.last_request_id,
            semantic_provider=self.semantic_capability.provider_identity,
            semantic_usage=self.semantic_capability.last_usage,
            semantic_retry_count=self.semantic_capability.last_retry_count,
            semantic_seconds=monotonic() - started_at,
            semantic_prompt_characters=self.semantic_capability.last_prompt_characters,
            semantic_model=self.semantic_capability.model,
            semantic_reasoning_effort=self.semantic_capability.reasoning_effort,
        )
        collaboration = semantic.collaboration
        # Policy may preserve the candidate's text when no special reconciliation
        # applies, so this semantic handoff must itself be safe to show.
        content = (
            collaboration.direct_answer
            or collaboration.recommended_next_action
            or collaboration.concise_basis
            or collaboration.current_collaboration_focus
            or semantic.interpreted_motive
        )
        if not content:
            raise InteractionInvariantViolation(
                "Controlled semantic result lacks material for a Human-facing response"
            )
        return self._assessment_candidate(
            semantic,
            ConversationResponseCandidate(
                content=content,
                provider_identity=semantic.provider_identity,
                model_identity=semantic.model_identity,
            ),
        )

    def pipeline_selection(self, basis: InteractionInterpretationInput) -> tuple[str, str]:
        if not self.coalesce_pre_work:
            return "staged", "explicit_opt_out"
        if basis.active_work_context is not None:
            return "staged", "active_work"
        if self.response_composer.provider is not self.conversation_provider:
            return "staged", "custom_provider_or_context"
        semantic = self.runtime.profile(ModelPurpose.WIC_SEMANTIC)
        conversation = self.runtime.profile(ModelPurpose.CONVERSATION_RESPONSE)
        if not semantic.transport_compatible_with(conversation):
            return "staged", "provider_profiles_differ"
        return "coalesced_pre_work", "native_pre_work_shared_configuration"

    def _interpret_coalesced(
        self,
        basis: InteractionInterpretationInput,
        *,
        on_response_delta: Callable[[str], None] | None,
        on_pipeline_stage: Callable[[str], None] | None = None,
    ):
        started_at = monotonic()
        first_response_delta_seconds: float | None = None
        stages: dict[str, float] = {}

        def stage(name: str) -> None:
            if name not in stages:
                stages[name] = monotonic() - started_at
                if on_pipeline_stage is not None:
                    on_pipeline_stage(name)

        extractor = _JsonStringFieldStream("natural_response")

        def receive(delta: str) -> None:
            nonlocal first_response_delta_seconds
            useful = extractor.feed(delta)
            if useful:
                if first_response_delta_seconds is None:
                    first_response_delta_seconds = monotonic() - started_at
                if on_response_delta is not None:
                    on_response_delta(useful)
            if extractor.complete:
                stage("natural_response_completed")

        stage("provider_context_started")
        stage("context_assembly_started")
        instruction = self.coalesced_instruction(basis)
        stage("provider_context_prepared")
        stage("context_assembly_completed")
        result = self.runtime.generate(
            purpose=ModelPurpose.WIC_SEMANTIC,
            instructions=instruction,
            input_text="Return one coalesced Watt collaboration envelope.",
            output_schema=self.coalesced_output_schema(),
            on_output_delta=receive if on_response_delta is not None else None,
            on_stage=stage,
        )
        stage("semantic_result_completed")
        stage("semantic_envelope_completed")
        stage("provider_teardown_completed")
        stage("payload_validation_started")
        try:
            payload = _CoalescedInteractionProviderPayload.model_validate_json(
                _structured_json_text(result.output_text)
            )
        except (ValidationError, ValueError, TypeError) as error:
            LOGGER.warning(
                "Coalesced collaboration validation failed request=%s model=%s status=completed stage=payload_validation issue=%s %s",
                result.request_id, result.effective_model or result.requested_model,
                _safe_validation_summary(error), _safe_result_shape(result.output_text),
            )
            raise InteractionInvariantViolation(
                "Coalesced collaboration Provider returned an invalid structured result "
                f"({_safe_validation_summary(error)})"
            ) from error
        content = payload.natural_response.strip()
        if not content:
            raise InteractionInvariantViolation(
                "Coalesced collaboration Provider returned an empty Human-facing response"
            )
        identity = DeepSeekInteractionSemanticCapability._result_identity(
            result, "collaboration"
        )
        semantic_values = payload.semantics.model_dump(
            exclude={
                "retained_prior_meaning_indexes",
                "reuse_prior_design_intent_frame",
                "meanings",
                "collaboration",
            }
        )
        semantic_values["meanings"] = self._expand_coalesced_meanings(
            payload.semantics, basis
        )
        semantic_values["collaboration"] = self._expand_coalesced_collaboration(
            payload.semantics, basis
        )
        semantic = InteractionSemanticCandidate(
            **semantic_values,
            provider_identity=identity,
            model_identity=result.effective_model or result.requested_model,
        )
        response = ConversationResponseCandidate(
            content=content,
            provider_identity=identity,
            model_identity=result.effective_model or result.requested_model,
        )
        candidate = self._assessment_candidate(semantic, response)
        stage("payload_validated")
        stage("validation_completed")
        self.last_collaboration_result = semantic.collaboration
        self.semantic_capability._observe(result)
        profile = self.runtime.profile(ModelPurpose.WIC_SEMANTIC)
        self.last_pipeline_evidence = ConversationPipelineEvidence(
            pipeline_mode="coalesced_pre_work",
            pipeline_reason="native_pre_work_shared_configuration",
            provider_call_count=1,
            coalesced_request_id=result.request_id,
            coalesced_provider=result.provider.value,
            coalesced_seconds=monotonic() - started_at,
            coalesced_prompt_characters=len(instruction),
            coalesced_model=result.effective_model or result.requested_model,
            coalesced_reasoning_effort=profile.reasoning_effort,
            first_response_delta_seconds=first_response_delta_seconds,
            coalesced_output_characters=len(result.output_text),
            coalesced_semantic_characters=len(json.dumps(
                payload.semantics.model_dump(mode="json"),
                ensure_ascii=False,
                separators=(",", ":"),
            )),
            retained_prior_meaning_count=len(
                payload.semantics.retained_prior_meaning_indexes
            ),
            new_meaning_count=len(payload.semantics.meanings),
            reused_prior_design_intent_frame=(
                payload.semantics.reuse_prior_design_intent_frame
            ),
            provider_stage_seconds=dict(stages),
            coalesced_usage=_usage(result),
            coalesced_retry_count=result.retry_count,
        )
        return candidate
