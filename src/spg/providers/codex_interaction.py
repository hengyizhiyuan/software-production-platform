"""Codex adapters for WIC semantics and dedicated Human-facing conversation."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
import json
from queue import Empty, Queue
from threading import Thread
from typing import Any

from openai_codex import ApprovalMode, Codex, Sandbox
from pydantic import BaseModel, ConfigDict, ValidationError

from spg.application.conversation import ConversationResponseComposer
from spg.application.guided_design import (
    design_schema_by_identity,
    design_schema_registry,
)
from spg.domain.conversation import (
    CollaborationAlternative,
    ConversationAttentionLevel,
    ConversationContext,
    ConversationPolicyHint,
    ConversationResponseCandidate,
    ConversationTurnIntent,
    StructuredCollaborationResult,
)
from spg.domain.design_intent import (
    DesignCollaborationMode,
    DesignIntentFrame,
    DesignObjectType,
    DesignScopeLevel,
)
from spg.domain.interaction import (
    InteractionAssessmentCandidate,
    InteractionInterpretationInput,
    InteractionInvariantViolation,
    InteractionSemanticCandidate,
    InterpretationMeaning,
    WorkFocusClassification,
    WorkImpactDisposition,
)
from spg.providers.codex_sdk_executor import INTERRUPT_GRACE_SECONDS, _enum_value
from spg.providers.codex_semantic import _provider_strict_output_schema


CodexFactory = Callable[[], AbstractContextManager[Any]]


class _InteractionProviderMeaning(InterpretationMeaning):
    """Strict wire shape over unchanged domain defaults."""

    clarification_required: bool


class _DesignIntentFrameProviderPayload(DesignIntentFrame):
    """Strict wire requiredness over advisory frame defaults."""

    design_subject: str
    object_type: DesignObjectType
    business_context: str | None
    desired_outcome: str | None
    scope_level: DesignScopeLevel
    collaboration_mode: DesignCollaborationMode
    candidate_assumptions: tuple[str, ...]
    ambiguities: tuple[str, ...]
    confidence: float


class _StructuredCollaborationProviderPayload(StructuredCollaborationResult):
    """Strict wire requiredness over domain-level optional/default semantics."""

    turn_intent: ConversationTurnIntent
    direct_answer: str | None
    known_relevant_facts: tuple[str, ...]
    current_objective: str | None
    current_collaboration_focus: str | None
    design_intent_frame: _DesignIntentFrameProviderPayload | None
    recommended_next_action: str | None
    concise_basis: str | None
    unresolved_human_decision: str | None
    alternatives: tuple[CollaborationAlternative, ...]
    attention_level: ConversationAttentionLevel
    progression_guidance_appropriate: bool
    detailed_explanation_requested: bool
    response_language: str
    policy_hints: tuple[ConversationPolicyHint, ...]


class _InteractionSemanticProviderPayload(BaseModel):
    """WIC semantic wire result; deliberately contains no Human-facing prose."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    interpreted_motive: str | None
    desired_outcome: str | None
    candidate_context: tuple[str, ...]
    candidate_constraints: tuple[str, ...]
    current_requests: tuple[str, ...]
    unresolved_material_questions: tuple[str, ...]
    meanings: tuple[_InteractionProviderMeaning, ...]
    focus_classification: WorkFocusClassification | None
    impact_disposition: WorkImpactDisposition | None
    supporting_references: tuple[str, ...]
    collaboration: _StructuredCollaborationProviderPayload


class _ConversationProviderPayload(BaseModel):
    """Dedicated Human-facing wire result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    natural_response: str


@dataclass(frozen=True)
class _StreamingTurnResult:
    status: object
    error: object | None
    final_response: str


@dataclass(frozen=True)
class _StreamingTerminal:
    result: _StreamingTurnResult | None = None
    timed_out: bool = False


@dataclass(frozen=True)
class ConversationPipelineEvidence:
    """Ephemeral Provider provenance for validation, never product truth."""

    semantic_thread_id: str
    semantic_turn_id: str
    conversation_thread_id: str
    conversation_turn_id: str


class _JsonStringFieldStream:
    """Extract one JSON string field without exposing its structured envelope."""

    def __init__(self, field: str) -> None:
        self._marker = json.dumps(field)
        self._buffer = ""
        self._emitted = ""

    def feed(self, delta: str) -> str:
        self._buffer += delta
        marker_at = self._buffer.find(self._marker)
        if marker_at < 0:
            return ""
        value_at = marker_at + len(self._marker)
        while value_at < len(self._buffer) and self._buffer[value_at].isspace():
            value_at += 1
        if value_at >= len(self._buffer) or self._buffer[value_at] != ":":
            return ""
        value_at += 1
        while value_at < len(self._buffer) and self._buffer[value_at].isspace():
            value_at += 1
        if value_at >= len(self._buffer) or self._buffer[value_at] != '"':
            return ""
        decoded = self._decode_prefix(self._buffer[value_at + 1 :])
        emitted = decoded[len(self._emitted) :]
        self._emitted = decoded
        return emitted

    @staticmethod
    def _decode_prefix(value: str) -> str:
        decoded: list[str] = []
        index = 0
        escapes = {
            '"': '"',
            "\\": "\\",
            "/": "/",
            "b": "\b",
            "f": "\f",
            "n": "\n",
            "r": "\r",
            "t": "\t",
        }
        while index < len(value):
            character = value[index]
            if character == '"':
                break
            if character != "\\":
                decoded.append(character)
                index += 1
                continue
            if index + 1 >= len(value):
                break
            escaped = value[index + 1]
            if escaped == "u":
                if index + 6 > len(value):
                    break
                digits = value[index + 2 : index + 6]
                try:
                    codepoint = int(digits, 16)
                except ValueError:
                    break
                if 0xD800 <= codepoint <= 0xDBFF:
                    if (
                        index + 12 > len(value)
                        or value[index + 6 : index + 8] != "\\u"
                    ):
                        break
                    low_digits = value[index + 8 : index + 12]
                    try:
                        low = int(low_digits, 16)
                    except ValueError:
                        break
                    if not 0xDC00 <= low <= 0xDFFF:
                        break
                    decoded.append(
                        chr(
                            0x10000
                            + ((codepoint - 0xD800) << 10)
                            + (low - 0xDC00)
                        )
                    )
                    index += 12
                    continue
                decoded.append(chr(codepoint))
                index += 6
                continue
            replacement = escapes.get(escaped)
            if replacement is None:
                break
            decoded.append(replacement)
            index += 2
        return "".join(decoded)


def _wait_for_streaming_terminal(
    turn: Any,
    *,
    timeout_seconds: float | None,
    on_response_delta: Callable[[str], None] | None,
    response_field: str | None,
) -> _StreamingTerminal:
    completed: Queue[tuple[str, Any]] = Queue(maxsize=1)

    def consume() -> None:
        raw_response: list[str] = []
        final_item_text: str | None = None
        completed_turn: object | None = None
        extractor = (
            None if response_field is None else _JsonStringFieldStream(response_field)
        )
        try:
            for notification in turn.stream():
                if notification.method == "item/agentMessage/delta":
                    delta = str(notification.payload.delta)
                    raw_response.append(delta)
                    if on_response_delta is not None and extractor is not None:
                        response_delta = extractor.feed(delta)
                        if response_delta:
                            on_response_delta(response_delta)
                elif notification.method == "item/completed":
                    item = notification.payload.item
                    if getattr(item, "type", None) == "agentMessage":
                        final_item_text = str(item.text)
                elif notification.method == "turn/completed":
                    completed_turn = notification.payload.turn
            if completed_turn is None:
                raise RuntimeError("turn completed event not received")
            completed.put(
                (
                    "result",
                    _StreamingTurnResult(
                        status=completed_turn.status,
                        error=completed_turn.error,
                        final_response=final_item_text or "".join(raw_response),
                    ),
                )
            )
        except Exception as error:
            completed.put(("error", error))

    worker = Thread(
        target=consume,
        name="spg-conversation-codex-stream",
        daemon=True,
    )
    worker.start()
    try:
        kind, value = completed.get(timeout=timeout_seconds)
    except Empty:
        try:
            turn.interrupt()
        except Exception:
            pass
        try:
            completed.get(timeout=INTERRUPT_GRACE_SECONDS)
        except Empty:
            pass
        return _StreamingTerminal(timed_out=True)
    if kind == "error":
        raise value
    return _StreamingTerminal(result=value)


class CodexSdkInteractionSemanticCapability:
    """WIC-owned advisory semantic interpretation, without response wording."""

    def __init__(
        self,
        *,
        repository_location: str,
        codex_factory: CodexFactory | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.repository_location = repository_location
        self.codex_factory = codex_factory or Codex
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.last_thread_id: str | None = None
        self.last_turn_id: str | None = None

    def interpret_semantics(
        self, basis: InteractionInterpretationInput
    ) -> InteractionSemanticCandidate:
        with self.codex_factory() as codex:
            thread = codex.thread_start(
                approval_mode=ApprovalMode.deny_all,
                cwd=self.repository_location,
                ephemeral=True,
                model=self.model,
                sandbox=Sandbox.read_only,
            )
            turn = thread.turn(
                self.instruction(basis),
                approval_mode=ApprovalMode.deny_all,
                cwd=self.repository_location,
                model=self.model,
                output_schema=self.output_schema(),
                sandbox=Sandbox.read_only,
            )
            terminal = _wait_for_streaming_terminal(
                turn,
                timeout_seconds=self.timeout_seconds,
                on_response_delta=None,
                response_field=None,
            )
        if terminal.timed_out or terminal.result is None:
            raise InteractionInvariantViolation(
                "WIC semantic Provider did not complete in its bounded Turn"
            )
        result = terminal.result
        if _enum_value(result.status) != "completed" or result.error is not None:
            raise InteractionInvariantViolation(
                "WIC semantic Provider did not return a completed result"
            )
        try:
            payload = _InteractionSemanticProviderPayload.model_validate_json(
                result.final_response.strip()
            )
        except ValidationError as error:
            safe_errors = [
                {
                    "location": [str(item) for item in detail["loc"]],
                    "message": detail["msg"],
                    "type": detail["type"],
                }
                for detail in error.errors(include_input=False)
            ]
            raise InteractionInvariantViolation(
                "WIC semantic Provider returned an invalid structured result: "
                + json.dumps(safe_errors, ensure_ascii=False, sort_keys=True)
            ) from error
        except (ValueError, TypeError) as error:
            raise InteractionInvariantViolation(
                "WIC semantic Provider returned an invalid structured result"
            ) from error
        self.last_thread_id = str(thread.id)
        self.last_turn_id = str(turn.id)
        return InteractionSemanticCandidate(
            **payload.model_dump(),
            provider_identity=f"codex-sdk:semantic-thread:{thread.id}:turn:{turn.id}",
            model_identity=self.model,
        )

    @staticmethod
    def output_schema() -> dict[str, Any]:
        return _provider_strict_output_schema(
            _InteractionSemanticProviderPayload.model_json_schema()
        )

    @staticmethod
    def instruction(basis: InteractionInterpretationInput) -> str:
        payload = basis.model_dump(mode="json")
        selected_schema = (
            design_schema_by_identity(
                basis.interaction.selected_design_schema_identity,
                basis.interaction.selected_design_schema_version,
            )
            if basis.interaction.selected_design_schema_identity is not None
            else None
        )
        schema_candidates = [
            {
                "identity": schema.identity,
                "version": schema.version,
                "title": schema.title,
                "applicability": schema.applicability,
                "first_focus": {
                    "stage": schema.issues[0].title,
                    "objective": schema.issues[0].objective,
                    "why_it_matters": schema.issues[0].why_it_matters,
                },
            }
            for schema in design_schema_registry()
        ]
        return (
            "Interpret one Human–Watt interaction from the exact persisted basis. "
            "This is the WIC semantic boundary: return structured collaboration "
            "semantics only and do not write the Human-facing response. Do not use "
            "tools, hidden conversation memory, or repository inspection. Provider "
            "output is advisory and creates no Work, Design, Plan, Authority, Evidence, "
            "or Runtime truth. Distinguish idle context from an actionable Motive. A "
            "clear long-lived Motive needs a desired outcome but not an exact production "
            "target. Preserve explicit facts, constraints, requests, corrections, and "
            "Human decisions. When active_work_context exists, preserve its governed "
            "Motive, outcome, context, constraints, and requests unless the latest input "
            "actually proposes change. Classify focus and production impact without "
            "silently rewriting Work or injecting input into an active cycle. When Work "
            "is currently satisfied, distinguish same-Motive continuation from new Work. "
            "supporting_references may only repeat references present in the basis. Every "
            "meaning must cite only source_record_ids in the basis. "
            "\n\nBefore proposing Guided Design direction, create a concise candidate "
            "Design Intent Frame for any input that asks Watt to create, change, "
            "design, execute, or review something. Separate the object being designed "
            "from its business scenario, audience, channels, and operating context. "
            "Classify object_type as PRODUCT_SYSTEM, BUSINESS_PROCESS, FEATURE, "
            "OPERATIONAL_ACTIVITY, REVIEW_ANALYSIS, or UNKNOWN; scope_level as "
            "strategic, product, capability, or implementation; and collaboration_mode "
            "as exploration, design, execution, or review. For example, an operations "
            "management platform used to promote Watt is a PRODUCT_SYSTEM; promotion, "
            "social channels, livestreaming, and target audiences are its business "
            "context, not proof that the object is an operational campaign. An explicit "
            "change to an existing system is FEATURE. Planning one launch livestream is "
            "OPERATIONAL_ACTIVITY. 'Improve engineering efficiency' is UNKNOWN unless "
            "the Human identifies whether the object is a tool, process, AI workflow, "
            "or organization change. Preserve a prior frame when new facts do not alter "
            "the object. A correction must replace the affected framing without "
            "defending the previous interpretation. Use candidate_assumptions, "
            "ambiguities, and calibrated confidence rather than false certainty. Put "
            "material framing ambiguity into unresolved_material_questions. Store only "
            "concise product-relevant interpretation, never private reasoning. Use null "
            "for design_intent_frame only when the turn and persisted basis contain no "
            "design/build/change/review intent. "
            "\n\nFor collaboration.turn_intent select the single best behavioral intent. "
            "DIRECT_QUESTION asks for a concrete answer; NEW_GOAL introduces a Motive; "
            "CONTEXT_ADDITION supplies facts; CORRECTION replaces a prior understanding; "
            "DISAGREEMENT rejects a direction; REQUEST_RECOMMENDATION asks what Watt "
            "recommends; REQUEST_DECISION_SUPPORT asks for alternatives or trade-offs; "
            "REQUEST_DETAIL explicitly asks for a full explanation; SIDE_QUESTION is a "
            "bounded detour; CONTINUE_CURRENT_WORK asks to progress; MATERIAL_BRANCH "
            "opens a consequential branch; FEEDBACK evaluates experience or a result; "
            "HUMAN_DECISION communicates an owned choice. WIC retains interpretation "
            "ownership; this label is response-scoped and non-authoritative. "
            "A DIRECT_QUESTION must include a concrete direct_answer. For the question "
            "about where a design document is output, the current product truth is that "
            "pre-Work Guided Design does not automatically generate or write a design-document "
            "artifact and has no artifact path yet; the design basis is retained and an "
            "exact target is decided later through a reviewable production proposal. "
            "REQUEST_DETAIL must set detailed_explanation_requested true. Capture known "
            "relevant facts, current objective/focus, one useful next action, concise "
            "product rationale, any unresolved Human-owned decision, and only material "
            "alternatives/trade-offs. Choose small policy_hints for the conversation "
            "composer; do not include private reasoning or chain of thought. Set response "
            "language to the Human's language. Return JSON only matching the schema, "
            "including every key and [] for empty arrays."
            "\n\nAvailable Design Schemas (selection occurs after framing):\n"
            + json.dumps(
                {
                    "currently_selected": (
                        None
                        if selected_schema is None
                        else {
                            "identity": selected_schema.identity,
                            "version": selected_schema.version,
                            "title": selected_schema.title,
                        }
                    ),
                    "candidates": schema_candidates,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n\nExact persisted Interaction basis:\n"
            + json.dumps(payload, ensure_ascii=False, sort_keys=True)
        )


class CodexSdkConversationProvider:
    """Dedicated replaceable Provider for Watt-to-Human language realization."""

    def __init__(
        self,
        *,
        repository_location: str,
        codex_factory: CodexFactory | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.repository_location = repository_location
        self.codex_factory = codex_factory or Codex
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.last_thread_id: str | None = None
        self.last_turn_id: str | None = None

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
            context,
            collaboration,
            on_response_delta=on_response_delta,
        )

    def _respond(
        self,
        context: ConversationContext,
        collaboration: StructuredCollaborationResult,
        *,
        on_response_delta: Callable[[str], None] | None,
    ) -> ConversationResponseCandidate:
        with self.codex_factory() as codex:
            thread = codex.thread_start(
                approval_mode=ApprovalMode.deny_all,
                cwd=self.repository_location,
                ephemeral=True,
                model=self.model,
                sandbox=Sandbox.read_only,
            )
            turn = thread.turn(
                self.instruction(context, collaboration),
                approval_mode=ApprovalMode.deny_all,
                cwd=self.repository_location,
                model=self.model,
                output_schema=self.output_schema(),
                sandbox=Sandbox.read_only,
            )
            terminal = _wait_for_streaming_terminal(
                turn,
                timeout_seconds=self.timeout_seconds,
                on_response_delta=on_response_delta,
                response_field="natural_response",
            )
        if terminal.timed_out or terminal.result is None:
            raise InteractionInvariantViolation(
                "Conversation Provider did not complete in its bounded Turn"
            )
        result = terminal.result
        if _enum_value(result.status) != "completed" or result.error is not None:
            raise InteractionInvariantViolation(
                "Conversation Provider did not return a completed result"
            )
        try:
            payload = _ConversationProviderPayload.model_validate_json(
                result.final_response.strip()
            )
        except (ValueError, TypeError) as error:
            raise InteractionInvariantViolation(
                "Conversation Provider returned an invalid Human-facing result"
            ) from error
        self.last_thread_id = str(thread.id)
        self.last_turn_id = str(turn.id)
        return ConversationResponseCandidate(
            content=payload.natural_response,
            provider_identity=f"codex-sdk:conversation-thread:{thread.id}:turn:{turn.id}",
            model_identity=self.model,
        )

    @staticmethod
    def output_schema() -> dict[str, Any]:
        return _provider_strict_output_schema(_ConversationProviderPayload.model_json_schema())

    @staticmethod
    def instruction(
        context: ConversationContext,
        collaboration: StructuredCollaborationResult,
    ) -> str:
        return (
            "You are Watt's dedicated Human-facing Conversation Provider. Turn the "
            "supplied structured collaboration result and bounded conversation context "
            "into one natural response. You own wording, coherence, adaptive detail, and "
            "turn-taking only. You do not decide or modify Work, Design, Plan, Authority, "
            "Evidence, Verification, Repository, or Runtime truth. Do not use tools, hidden "
            "memory, or outside facts. Do not expose the JSON structure, enums, schema "
            "identity/version, internal stage identifiers, policy hints, provider contracts, "
            "or private reasoning unless the Human explicitly asks for relevant system "
            "details. Never claim advisory wording is governed truth. "
            "Use the Design Intent Frame to state the currently understood design object "
            "naturally when it materially prevents confusion. Keep business context "
            "distinct from what is being built. If the frame is ambiguous or low "
            "confidence, present it as a candidate understanding and invite one concise "
            "correction; never turn enum names or confidence numbers into normal prose. "
            "\n\nBehavior policy: for DIRECT_QUESTION, answer direct_answer in the first "
            "sentence and add progression only when useful. For CONTEXT_ADDITION, use and "
            "acknowledge the new fact without forcing progression. For CORRECTION or "
            "DISAGREEMENT, accept the correction without defensiveness or repetition. For "
            "REQUEST_RECOMMENDATION, make one clear recommendation with concise rationale. "
            "For REQUEST_DECISION_SUPPORT, explain material alternatives and trade-offs. "
            "For SIDE_QUESTION, answer boundedly and return to focus only when useful. For "
            "HUMAN_DECISION, confirm the choice and its immediate implication without "
            "inventing authority. Preserve proactive Guided Design leadership: lead with a "
            "useful framing or next action when supported, not a questionnaire. "
            "\n\nUse progressive disclosure. An ordinary response should usually be two "
            "to five short paragraphs, with one primary recommendation/action and at most "
            "one highest-impact question. Use no more than one question mark in the entire "
            "response; if several unknowns exist, ask only the single one whose answer most "
            "changes the next decision. Reuse known facts and never ask the Human to "
            "repeat supplied information. If detailed_explanation_requested is true, expand "
            "enough to answer the request rather than enforcing artificial brevity. Respond "
            "in response_language. Return JSON only with natural_response."
            "\n\nBounded Conversation Context:\n"
            + json.dumps(context.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
            + "\n\nStructured Collaboration Result:\n"
            + json.dumps(
                collaboration.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
            )
        )


class CodexSdkWorkInteractionCapability:
    """Compatibility facade over separated WIC semantics and conversation wording."""

    def __init__(
        self,
        *,
        repository_location: str,
        codex_factory: CodexFactory | None = None,
        model: str | None = None,
        conversation_model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.repository_location = repository_location
        self.codex_factory = codex_factory or Codex
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.semantic_capability = CodexSdkInteractionSemanticCapability(
            repository_location=repository_location,
            codex_factory=self.codex_factory,
            model=model,
            timeout_seconds=timeout_seconds,
        )
        self.conversation_provider = CodexSdkConversationProvider(
            repository_location=repository_location,
            codex_factory=self.codex_factory,
            model=conversation_model or model,
            timeout_seconds=timeout_seconds,
        )
        self.response_composer = ConversationResponseComposer(
            self.conversation_provider
        )
        self.last_pipeline_evidence: ConversationPipelineEvidence | None = None
        self.last_collaboration_result: StructuredCollaborationResult | None = None

    def interpret(
        self, basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate:
        return self._interpret(basis, on_response_delta=None)

    def interpret_stream(
        self,
        basis: InteractionInterpretationInput,
        *,
        on_response_delta: Callable[[str], None],
    ) -> InteractionAssessmentCandidate:
        return self._interpret(basis, on_response_delta=on_response_delta)

    def _interpret(
        self,
        basis: InteractionInterpretationInput,
        *,
        on_response_delta: Callable[[str], None] | None,
    ) -> InteractionAssessmentCandidate:
        semantic = self.semantic_capability.interpret_semantics(basis)
        self.last_collaboration_result = semantic.collaboration
        response = self.response_composer.compose(
            basis,
            semantic.collaboration,
            on_response_delta=on_response_delta,
        )
        if not all(
            (
                self.semantic_capability.last_thread_id,
                self.semantic_capability.last_turn_id,
                self.conversation_provider.last_thread_id,
                self.conversation_provider.last_turn_id,
            )
        ):
            raise InteractionInvariantViolation(
                "Conversation pipeline completed without Provider provenance"
            )
        self.last_pipeline_evidence = ConversationPipelineEvidence(
            semantic_thread_id=str(self.semantic_capability.last_thread_id),
            semantic_turn_id=str(self.semantic_capability.last_turn_id),
            conversation_thread_id=str(self.conversation_provider.last_thread_id),
            conversation_turn_id=str(self.conversation_provider.last_turn_id),
        )
        return InteractionAssessmentCandidate(
            interpreted_motive=semantic.interpreted_motive,
            desired_outcome=semantic.desired_outcome,
            design_intent_frame=semantic.collaboration.design_intent_frame,
            candidate_context=semantic.candidate_context,
            candidate_constraints=semantic.candidate_constraints,
            current_requests=semantic.current_requests,
            unresolved_material_questions=semantic.unresolved_material_questions,
            meanings=semantic.meanings,
            focus_classification=semantic.focus_classification,
            impact_disposition=semantic.impact_disposition,
            supporting_references=semantic.supporting_references,
            natural_response=response.content,
            provider_identity=semantic.provider_identity,
            model_identity=semantic.model_identity,
        )

    @staticmethod
    def output_schema() -> dict[str, Any]:
        """Backward-compatible alias for the WIC semantic wire contract."""

        return CodexSdkInteractionSemanticCapability.output_schema()

    @staticmethod
    def conversation_output_schema() -> dict[str, Any]:
        return CodexSdkConversationProvider.output_schema()

    @staticmethod
    def _instruction(basis: InteractionInterpretationInput) -> str:
        """Backward-compatible alias for focused contract inspection."""

        return CodexSdkInteractionSemanticCapability.instruction(basis)

    @staticmethod
    def _wait_for_streaming_terminal(
        turn: Any,
        *,
        timeout_seconds: float | None,
        on_response_delta: Callable[[str], None] | None,
    ) -> _StreamingTerminal:
        return _wait_for_streaming_terminal(
            turn,
            timeout_seconds=timeout_seconds,
            on_response_delta=on_response_delta,
            response_field="natural_response",
        )
