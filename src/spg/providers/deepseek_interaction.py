"""DeepSeek adapters for WIC semantics and Human-facing conversation."""

from __future__ import annotations

from dataclasses import asdict, replace
import json
import re
from time import monotonic
from typing import Callable

from pydantic import ValidationError

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
        self, basis: InteractionInterpretationInput
    ) -> InteractionSemanticCandidate:
        instruction = CodexSdkInteractionSemanticCapability.instruction(basis)
        self.last_prompt_characters = len(instruction)
        result = self.runtime.generate(
            purpose=ModelPurpose.WIC_SEMANTIC,
            instructions=instruction,
            input_text="Return the WIC semantic result for the exact supplied basis.",
            output_schema=CodexSdkInteractionSemanticCapability.output_schema(),
        )
        try:
            payload = _InteractionSemanticProviderPayload.model_validate_json(
                _structured_json_text(result.output_text)
            )
        except (ValidationError, ValueError, TypeError) as error:
            raise InteractionInvariantViolation(
                "WIC semantic Provider returned an invalid structured result"
            ) from error
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
            raise InteractionInvariantViolation(
                "Conversation Provider returned an invalid Human-facing result"
            ) from error
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
            "For MODIFY, start with the proposed delta or its consequence, never with "
            "'I understand' or a restatement of the request. If question_allowed is false, "
            "ask no question and do not reproduce a question from governed_content; otherwise "
            "ask at most max_questions after the useful answer or candidate. Treat the "
            "question-mark count as a hard expression constraint: use none when questions are "
            "disallowed and at most one when one question is allowed; fold any answer choices "
            "into that single sentence. "
            "Never emit any forbidden_claim. Return JSON only with one natural_response "
            "string.\n\nGoverned Response Envelope:\n"
            + json.dumps(
                envelope.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
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

    def interpret_controlled_stream_observed(
        self,
        basis: InteractionInterpretationInput,
        *,
        on_response_delta: Callable[[str], None],
        on_pipeline_stage: Callable[[str], None],
    ) -> InteractionAssessmentCandidate:
        """Retry one syntax-invalid coalesced envelope before any Human visibility.

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
            )
        except InteractionInvariantViolation as first_error:
            if not (
                str(first_error).startswith(
                    "Coalesced collaboration Provider returned an invalid structured result"
                )
                and _is_root_json_invalid(first_error)
            ):
                raise
            on_pipeline_stage("structured_json_repair_started")

        try:
            candidate = self._interpret(
                basis,
                on_response_delta=observe_only,
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
