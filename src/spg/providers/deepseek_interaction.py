"""DeepSeek adapters for WIC semantics and Human-facing conversation."""

from __future__ import annotations

from dataclasses import asdict
import json
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
    InteractionInterpretationInput,
    InteractionInvariantViolation,
    InteractionSemanticCandidate,
)
from spg.domain.model_runtime import ModelPurpose, StructuredModelResult, WattModelRuntime
from spg.providers.codex_interaction import (
    CodexSdkConversationProvider,
    CodexSdkInteractionSemanticCapability,
    CodexSdkWorkInteractionCapability,
    ConversationPipelineEvidence,
    _CoalescedInteractionProviderPayload,
    _ConversationProviderPayload,
    _InteractionSemanticProviderPayload,
    _JsonStringFieldStream,
)


def _usage(result: StructuredModelResult) -> dict[str, object]:
    return asdict(result.usage)


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
                result.output_text.strip()
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
                result.output_text.strip()
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

    def close(self) -> None:
        self.runtime.close()

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
                result.output_text.strip()
            )
        except (ValidationError, ValueError, TypeError) as error:
            raise InteractionInvariantViolation(
                "Coalesced collaboration Provider returned an invalid structured result"
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
