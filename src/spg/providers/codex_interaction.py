"""Codex adapters for WIC semantics and dedicated Human-facing conversation."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from copy import deepcopy
from dataclasses import dataclass
from inspect import Parameter, signature
import json
from queue import Empty, Queue
from threading import Thread
from time import monotonic
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, ValidationError

from spg.application.conversation import (
    ConversationResponseComposer,
    WattNativeConversationContextAssembler,
    conversation_response_policy,
)
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
    InterpretationMeaningKind,
    WorkFocusClassification,
    WorkImpactDisposition,
)
from spg.domain.wic_response import (
    GovernedResponseEnvelope,
    GovernedResponseRealization,
)


CodexFactory = Callable[[], AbstractContextManager[Any]]
INTERRUPT_GRACE_SECONDS = 5.0


def _enum_value(value: object) -> str:
    candidate = getattr(value, "value", value)
    return str(candidate).lower()


def _safe_validation_summary(error: BaseException) -> str:
    """Expose schema locations/types without echoing Provider input or secrets."""

    if not isinstance(error, ValidationError):
        return type(error).__name__
    issues = []
    for issue in error.errors(include_url=False, include_input=False)[:5]:
        location = ".".join(str(part) for part in issue.get("loc", ())) or "root"
        issues.append(f"{location}:{issue.get('type', 'validation_error')}")
    return ", ".join(issues) or "ValidationError"


def _provider_strict_output_schema(schema: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(schema)

    def normalize(value: object) -> None:
        if isinstance(value, dict):
            if "$ref" in value:
                reference = value["$ref"]
                value.clear()
                value["$ref"] = reference
                return
            for nested in value.values():
                normalize(nested)
        elif isinstance(value, list):
            for nested in value:
                normalize(nested)

    normalize(normalized)
    return normalized


def _default_codex_factory() -> AbstractContextManager[Any]:
    """Load the legacy SDK only when that explicit rollback adapter is used."""

    from openai_codex import Codex

    return Codex()


def _codex_controls() -> tuple[Any, Any]:
    from openai_codex import ApprovalMode, Sandbox

    return ApprovalMode, Sandbox


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


class _CoalescedCollaborationProviderPayload(BaseModel):
    """Only the advisory values consumed after a single-call response.

    The staged contract still carries the full expression handoff. Here the
    wording is already present in the same envelope, so context projections,
    turn-taking hints and alternatives need not be serialized a second time.
    Explicit answers and recommendation grounds remain WIC-owned values.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    turn_intent: ConversationTurnIntent
    direct_answer: str | None
    design_intent_frame: _DesignIntentFrameProviderPayload | None
    recommended_next_action: str | None
    concise_basis: str | None
    detailed_explanation_requested: bool
    response_language: str = Field(min_length=1, max_length=32)


class _CoalescedSemanticProviderPayload(_InteractionSemanticProviderPayload):
    """Full current facts with explicit reuse of immutable prior advisory values."""

    retained_prior_meaning_indexes: tuple[StrictInt, ...]
    reuse_prior_design_intent_frame: StrictBool
    collaboration: _CoalescedCollaborationProviderPayload


class _CoalescedInteractionProviderPayload(_ConversationProviderPayload):
    """One transport envelope preserving WIC and expression field ownership."""

    semantics: _CoalescedSemanticProviderPayload


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

    semantic_thread_id: str | None = None
    semantic_turn_id: str | None = None
    conversation_thread_id: str | None = None
    conversation_turn_id: str | None = None
    semantic_seconds: float | None = None
    conversation_seconds: float | None = None
    first_response_delta_seconds: float | None = None
    semantic_prompt_characters: int | None = None
    conversation_prompt_characters: int | None = None
    semantic_model: str | None = None
    conversation_model: str | None = None
    semantic_reasoning_effort: str | None = None
    conversation_reasoning_effort: str | None = None
    pipeline_mode: str = "staged"
    pipeline_reason: str | None = None
    provider_call_count: int = 2
    coalesced_thread_id: str | None = None
    coalesced_turn_id: str | None = None
    coalesced_seconds: float | None = None
    coalesced_prompt_characters: int | None = None
    coalesced_model: str | None = None
    coalesced_reasoning_effort: str | None = None
    coalesced_output_characters: int | None = None
    coalesced_semantic_characters: int | None = None
    retained_prior_meaning_count: int | None = None
    new_meaning_count: int | None = None
    reused_prior_design_intent_frame: bool | None = None
    provider_stage_seconds: dict[str, float] | None = None
    semantic_request_id: str | None = None
    conversation_request_id: str | None = None
    coalesced_request_id: str | None = None
    semantic_provider: str | None = None
    conversation_provider: str | None = None
    coalesced_provider: str | None = None
    semantic_usage: dict[str, object] | None = None
    conversation_usage: dict[str, object] | None = None
    coalesced_usage: dict[str, object] | None = None
    semantic_retry_count: int | None = None
    conversation_retry_count: int | None = None
    coalesced_retry_count: int | None = None


def _compact_interaction_basis(
    basis: InteractionInterpretationInput, *, coalesced: bool = False
) -> dict[str, Any]:
    """Remove transport-only duplication without truncating interpretation evidence."""

    payload = basis.model_dump(mode="json")
    for key in ("created_by", "updated_by", "created_at", "updated_at"):
        payload.get("interaction", {}).pop(key, None)
    for record in payload.get("records", ()):
        for key in ("interaction_id", "content_fingerprint", "created_at"):
            record.pop(key, None)
    prior = payload.get("prior_assessment")
    if prior is not None:
        for key in (
            "interaction_id", "provider_identity", "model_identity", "schema_version",
            "created_at",
        ):
            prior.pop(key, None)
        if coalesced:
            prior.pop("readiness", None)
            if any(
                message.get("actor") == "WATT"
                and message.get("content") == prior.get("natural_response")
                for message in payload.get("recent_conversation_messages", ())
            ):
                prior.pop("natural_response", None)
            prior["meanings"] = [
                {
                    "index": index,
                    "kind": meaning["kind"],
                    "statement": meaning["statement"],
                    "source_record_ids": meaning["source_record_ids"],
                }
                for index, meaning in enumerate(prior.get("meanings", ()))
            ]
    return payload


class _JsonStringFieldStream:
    """Extract one JSON string field without exposing its structured envelope."""

    def __init__(self, field: str) -> None:
        self._marker = json.dumps(field)
        self._buffer = ""
        self._emitted = ""
        self.complete = False

    def feed(self, delta: str) -> str:
        if self.complete:
            return ""
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

    def _decode_prefix(self, value: str) -> str:
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
                self.complete = True
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
    on_pipeline_stage: Callable[[str], None] | None = None,
) -> _StreamingTerminal:
    completed: Queue[tuple[str, Any]] = Queue(maxsize=1)

    def consume() -> None:
        raw_response: list[str] = []
        final_item_text: str | None = None
        completed_turn: object | None = None
        extractor = (
            None if response_field is None else _JsonStringFieldStream(response_field)
        )
        response_closed = False

        def observe_response_complete(probe: _JsonStringFieldStream) -> None:
            nonlocal response_closed
            if probe.complete and not response_closed:
                response_closed = True
                if on_pipeline_stage is not None:
                    on_pipeline_stage("natural_response_completed")

        try:
            for notification in turn.stream():
                if notification.method == "item/agentMessage/delta":
                    if on_pipeline_stage is not None:
                        on_pipeline_stage("provider_first_token")
                    delta = str(notification.payload.delta)
                    raw_response.append(delta)
                    if extractor is not None:
                        response_delta = extractor.feed(delta)
                        if response_delta and on_response_delta is not None:
                            on_response_delta(response_delta)
                        observe_response_complete(extractor)
                elif notification.method == "item/completed":
                    item = notification.payload.item
                    if getattr(item, "type", None) == "agentMessage":
                        final_item_text = str(item.text)
                        if response_field is not None and not response_closed:
                            final_probe = _JsonStringFieldStream(response_field)
                            final_probe.feed(final_item_text)
                            observe_response_complete(final_probe)
                elif notification.method == "turn/completed":
                    completed_turn = notification.payload.turn
                    if (
                        on_pipeline_stage is not None
                        and _enum_value(completed_turn.status) == "completed"
                        and completed_turn.error is None
                    ):
                        on_pipeline_stage("semantic_envelope_completed")
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
        reasoning_effort: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.repository_location = repository_location
        self.codex_factory = codex_factory or _default_codex_factory
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.timeout_seconds = timeout_seconds
        self.last_thread_id: str | None = None
        self.last_turn_id: str | None = None
        self.last_prompt_characters: int | None = None

    def interpret_semantics(
        self, basis: InteractionInterpretationInput
    ) -> InteractionSemanticCandidate:
        self.last_thread_id = None
        self.last_turn_id = None
        instruction = self.instruction(basis)
        self.last_prompt_characters = len(instruction)
        ApprovalMode, Sandbox = _codex_controls()
        with self.codex_factory() as codex:
            thread = codex.thread_start(
                approval_mode=ApprovalMode.deny_all,
                cwd=self.repository_location,
                ephemeral=True,
                model=self.model,
                sandbox=Sandbox.read_only,
            )
            turn = thread.turn(
                instruction,
                approval_mode=ApprovalMode.deny_all,
                cwd=self.repository_location,
                effort=self.reasoning_effort,
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
    def instruction(
        basis: InteractionInterpretationInput, *, coalesced: bool = False
    ) -> str:
        payload = _compact_interaction_basis(basis, coalesced=coalesced)
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
            }
            for schema in design_schema_registry()
        ]
        output_contract = (
            "This is the WIC semantic boundary: populate the semantics object in the "
            "joint transport envelope. The natural_response field belongs to "
            "Conversation Intelligence and must express the same interpretation. "
            if coalesced else
            "This is the WIC semantic boundary: return structured collaboration "
            "semantics only and do not write the Human-facing response. "
        )
        active_work_instruction = (
            "When active_work_context exists, preserve its governed Motive, outcome, "
            "context, constraints, and requests unless the latest input actually proposes "
            "change. Classify focus and production impact without silently rewriting Work "
            "or injecting input into an active cycle. Regardless of satisfaction state, "
            "an explicit addition, removal or correction of a constraint applying to the "
            "current Work is an ON_TOPIC governed change: include the complete resulting "
            "constraint set and use HUMAN_GOVERNANCE_REQUIRED, or "
            "CURRENT_RESULT_MAY_BE_INSUFFICIENT when an active production binding or "
            "current satisfaction makes that boundary applicable. Never classify such a "
            "constraint change as NO_GOVERNED_CHANGE. "
            "compare an explicitly declared long-lived objective with the active Work. "
            "If the Human names a different product, system, platform or similarly durable "
            "objective, classify it as UNRELATED_NEW_DEMAND with NEW_WORK_RECOMMENDED, "
            "preserve the current governed Work, and recommend explicit Human confirmation "
            "before independent Work formation. Do not treat an ordinary feature, question "
            "or relevant exploration as a new Work merely because its wording differs. "
            "Never create Work or transfer production authority automatically. When Work is "
            "currently satisfied, also distinguish same-Motive continuation from new Work. "
            if not coalesced or getattr(basis, "active_work_context", None) is not None else ""
        )
        frame_null_instruction = (
            "Use null for design_intent_frame only for explicit prior-frame reuse or when "
            "the turn and persisted basis contain no design/build/change/review intent. "
            if coalesced else
            "Use null for design_intent_frame only when the turn and persisted basis contain no "
            "design/build/change/review intent. "
        )
        document_location_instruction = (
            "For a question about a design document location, the current facts are: "
            "no design-document file has been generated or saved during this discussion, "
            "so no output path is determined. The discussion is retained. An exact file "
            "and location are established through the existing reviewable production "
            "proposal before writing; express this fact without requiring internal "
            "process terminology. "
            if getattr(basis, "active_work_context", None) is None else
            "For a question about a design document location, answer from the supplied "
            "governed Work facts and Reality references. Distinguish a requested output "
            "path from a produced artifact. If the supplied basis does not establish an "
            "actual file location, say that its location is unknown; do not infer that "
            "no artifact exists from a missing path. "
        )
        collaboration_instruction = (
            "Use the compact collaboration schema; do not duplicate current facts "
            "as an expression handoff. Put material unresolved decisions in "
            "semantics.unresolved_material_questions. "
            if coalesced else
            "Capture known relevant facts, current objective/focus, an unresolved "
            "Human-owned decision and material alternatives/trade-offs. Choose small "
            "policy_hints for the conversation composer. "
        )
        return (
            "Interpret one Human–Watt interaction from the exact persisted basis. "
            + output_contract
            + "Do not use tools, hidden conversation memory, or repository inspection. Provider "
            "output is advisory and creates no Work, Design, Plan, Authority, Evidence, "
            "or Runtime truth. Distinguish idle context from an actionable Motive. A "
            "clear long-lived Motive needs a desired outcome but not an exact production "
            "target. Repository binding, repository creation and exact artifact placement are "
            "production prerequisites, not material questions blocking pre-Work admission. "
            "When Human requests Work first and repository binding later, keep that sequence "
            "in context/requests and do not put repository selection in unresolved_material_questions. "
            "Preserve explicit facts, constraints, requests, corrections, and "
            "Human decisions. "
            + active_work_instruction
            + "supporting_references may only repeat exact values from the source records supporting_references arrays. "
            "Allowed kinds are VERIFICATION, RUNTIME_FACT, COMPLETION and ENGINEERING_FINDING, each with a UUID. "
            "Do not copy active Work, design, agenda, semantic-result or governance references into this field. "
            "If source records contain no supporting_references, return an empty array. Every "
            "meaning must cite only source_record_ids in the basis. Recent Watt dialogue "
            "is advisory wording for conversational continuity, not Human input or "
            "governed evidence; it cannot override source records or Work Reality. "
            "\n\nFor design/build/change/review intent, create a concise Design Intent "
            "Frame using the schema enums. Separate the designed object from its "
            "business scenario, audience and channels. A platform supporting promotion "
            "is PRODUCT_SYSTEM; planning the promotion itself is OPERATIONAL_ACTIVITY; "
            "changing an existing system is FEATURE. Use UNKNOWN for an unestablished "
            "object. Preserve an unchanged frame; replace affected framing on correction. "
            "Record candidate_assumptions, ambiguities and calibrated confidence; put "
            "material ambiguities in unresolved_material_questions. These distinctions "
            "belong in structured fields. Human-facing wording should use the corrected "
            "understanding to help, without explaining the classification exercise. "
            + frame_null_instruction
            + "Keep the system's users/operators distinct from the audience of the "
            "business it supports: a promotion audience is not automatically the "
            "platform's operators. Keep an unknown operator provisional. "
            "\n\nSelect the most specific collaboration.turn_intent for the latest input "
            "from the full bounded context, independently from how mature or detailed "
            "the Human's thinking is. Prefer the concise vocabulary for new results: "
            "BUILD asks Watt to make or shape a new object; HOW_TO asks how to do "
            "something; DIRECT_QUESTION asks for a factual or explanatory answer; "
            "RECOMMEND asks for a judgment; COMPARE asks for trade-offs; EXPLORE "
            "develops possibilities; MODIFY changes an existing object; CORRECTION "
            "replaces prior understanding; DEPLOY requests deployment; ACTION_REQUEST "
            "asks Watt to perform another bounded action. CONTEXT_ADDITION adds facts; "
            "DISAGREEMENT rejects a direction; HUMAN_DECISION owns a choice. Do not "
            "classify every early or vague statement as EXPLORE: a vague request to "
            "build a product is still BUILD. "
            "Use exactly one turn_intent enum value from the output schema; never invent "
            "a synonym such as CREATE, QUESTION or REQUEST_INFORMATION. "
            "WIC owns these advisory interpretations. "
            "A DIRECT_QUESTION or HOW_TO result must include a concrete, non-empty "
            "direct_answer containing the core answer, even when natural_response already "
            "contains that answer. Never return null for direct_answer on those intents. "
            + document_location_instruction
            + "REQUEST_DETAIL must set detailed_explanation_requested true. "
            + collaboration_instruction
            + "Set response language to the Human's language. For BUILD, do not return only "
            "methodology or a clarification question. Supply a concrete, reversible first "
            "candidate grounded in the actual object, then at most one question only if its "
            "answer materially changes that candidate. When the Human is uncertain, propose "
            "a useful starting point rather than making them invent the answer. For a new goal, continuation "
            "or recommendation, supply one useful priority in recommended_next_action "
            "and its context-specific reason in concise_basis. Prefer a product decision "
            "or concrete workflow over naming the next design document. Rank the choice "
            "using the Human's actual objective, constraints and corrections; explain "
            "a material trade-off when it helps. Do not assume a budget, launch stage "
            "or operator the Human never supplied. If necessary, state one provisional "
            "assumption and advance a useful draft. REQUEST_RECOMMENDATION requires "
            "an actual recommendation, rationale and tangible next action; 'clarify "
            "requirements' or a menu of modules alone is insufficient. Keep these "
            "advisory values concise, never private reasoning or chain of thought. "
            "Distinguish suggestions from Human facts and admitted decisions. Ask only "
            "when an unresolved fact changes the next material choice. After a correction "
            "or rejected recommendation, use the revised direction without reopening it. "
            "Return JSON only matching the schema, "
            "including every key and [] for empty arrays. Keep structured values concise "
            "without omitting explicit facts or requested explanation. Schema applicability "
            "does not establish the current design issue or readiness; never infer agenda "
            "progress from the schema catalogue."
            + ("" if coalesced else
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
                separators=(",", ":"),
            ))
            + "\n\nExact persisted Interaction basis:\n"
            + json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )


class CodexSdkConversationProvider:
    """Dedicated replaceable Provider for Watt-to-Human language realization."""

    def __init__(
        self,
        *,
        repository_location: str,
        codex_factory: CodexFactory | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.repository_location = repository_location
        self.codex_factory = codex_factory or _default_codex_factory
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.timeout_seconds = timeout_seconds
        self.last_thread_id: str | None = None
        self.last_turn_id: str | None = None
        self.last_prompt_characters: int | None = None

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
        self.last_thread_id = None
        self.last_turn_id = None
        instruction = self.instruction(context, collaboration)
        self.last_prompt_characters = len(instruction)
        ApprovalMode, Sandbox = _codex_controls()
        with self.codex_factory() as codex:
            thread = codex.thread_start(
                approval_mode=ApprovalMode.deny_all,
                cwd=self.repository_location,
                ephemeral=True,
                model=self.model,
                sandbox=Sandbox.read_only,
            )
            turn = thread.turn(
                instruction,
                approval_mode=ApprovalMode.deny_all,
                cwd=self.repository_location,
                effort=self.reasoning_effort,
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
    def response_policy() -> str:
        """Conversation Intelligence owns this policy in both transport modes."""

        return conversation_response_policy()

    @staticmethod
    def instruction(
        context: ConversationContext,
        collaboration: StructuredCollaborationResult,
    ) -> str:
        return (
            "You are Watt's dedicated Human-facing Conversation Provider. Turn the "
            "supplied structured collaboration result and bounded conversation context "
            "into one natural response. "
            + CodexSdkConversationProvider.response_policy()
            + " Return JSON only with natural_response."
            + "\n\nBounded Conversation Context:\n"
            + json.dumps(
                context.model_dump(mode="json"), ensure_ascii=False,
                sort_keys=True, separators=(",", ":"),
            )
            + "\n\nStructured Collaboration Result:\n"
            + json.dumps(
                collaboration.model_dump(mode="json"),
                ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            )
        )


class CodexSdkGovernedResponseRealizer:
    """Codex transport for expression-only realization of governed WIC semantics."""

    provider_identity = "codex-sdk:governed-realizer"

    def __init__(
        self,
        *,
        repository_location: str,
        codex_factory: CodexFactory,
        model: str | None,
        reasoning_effort: str | None,
        timeout_seconds: float | None,
    ) -> None:
        self.repository_location = repository_location
        self.codex_factory = codex_factory
        self.model_identity = model
        self.reasoning_effort = reasoning_effort
        self.timeout_seconds = timeout_seconds
        self.last_thread_id: str | None = None
        self.last_turn_id: str | None = None

    def realize_stream(
        self,
        envelope: GovernedResponseEnvelope,
        *,
        on_response_delta: Callable[[str], None],
    ) -> GovernedResponseRealization:
        instruction = (
            "You are Watt's Governed Response Realizer. The supplied envelope is "
            "already governed. Express it naturally without changing intent, facts, "
            "constraints, Work boundaries, readiness, authority, corrections, or its "
            "Human-owned decisions. Interaction Strategy owns only the conversational "
            "move, altitude, and whether a question is useful; follow it exactly. Treat "
            "governed_content as semantic material rather than wording to echo. Show "
            "understanding by advancing the thinking, not by paraphrasing the Human. "
            "Lead with the answer, judgment, useful frame, comparison, or proposal named "
            "by primary_move. When answer_first is true, answer before framing or asking. "
            "When candidate_first is true, contribute a concrete, low-commitment candidate "
            "before any question. Stay at next_conversational_granularity. If question_allowed "
            "is false, ask no question. If true, ask at most max_questions and follow "
            "question_guidance. A selected_question is governed input but Interaction "
            "Strategy decides whether it should be visible this turn. Never emit "
            "forbidden_claims, narrate internal workflow, or add a production decision. "
            "Use concise, natural language unless depth is needed. Return JSON only with "
            "natural_response.\n\n"
            + json.dumps(
                envelope.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        ApprovalMode, Sandbox = _codex_controls()
        started_at = monotonic()
        first_delta_seconds: float | None = None
        stages: dict[str, float] = {}

        def stage(name: str) -> None:
            stages.setdefault(name, monotonic() - started_at)

        def publish(delta: str) -> None:
            nonlocal first_delta_seconds
            if delta.strip() and first_delta_seconds is None:
                first_delta_seconds = monotonic() - started_at
            on_response_delta(delta)

        with self.codex_factory() as codex:
            thread = codex.thread_start(
                approval_mode=ApprovalMode.deny_all,
                cwd=self.repository_location,
                ephemeral=True,
                model=self.model_identity,
                sandbox=Sandbox.read_only,
            )
            turn = thread.turn(
                instruction,
                approval_mode=ApprovalMode.deny_all,
                cwd=self.repository_location,
                effort=self.reasoning_effort,
                model=self.model_identity,
                output_schema=CodexSdkConversationProvider.output_schema(),
                sandbox=Sandbox.read_only,
            )
            terminal = _wait_for_streaming_terminal(
                turn,
                timeout_seconds=self.timeout_seconds,
                on_response_delta=publish,
                response_field="natural_response",
                on_pipeline_stage=stage,
            )
        if terminal.timed_out or terminal.result is None:
            raise InteractionInvariantViolation(
                "Governed Response Realizer did not complete in its bounded Turn"
            )
        result = terminal.result
        if _enum_value(result.status) != "completed" or result.error is not None:
            raise InteractionInvariantViolation(
                "Governed Response Realizer did not return a completed result"
            )
        try:
            payload = _ConversationProviderPayload.model_validate_json(
                result.final_response.strip()
            )
        except (ValueError, TypeError) as error:
            raise InteractionInvariantViolation(
                "Governed Response Realizer returned an invalid result"
            ) from error
        self.last_thread_id = str(thread.id)
        self.last_turn_id = str(turn.id)
        return GovernedResponseRealization(
            content=payload.natural_response,
            provider_identity=(
                f"codex-sdk:governed-realizer-thread:{thread.id}:turn:{turn.id}"
            ),
            model_identity=self.model_identity,
            timing={
                "request_to_first_text_seconds": first_delta_seconds,
                "request_to_complete_seconds": monotonic() - started_at,
                **stages,
            },
        )


class CodexSdkWorkInteractionCapability:
    """Keep semantic/expression ownership while coalescing eligible pre-Work transport."""

    def __init__(
        self,
        *,
        repository_location: str,
        codex_factory: CodexFactory | None = None,
        model: str | None = None,
        conversation_model: str | None = None,
        reasoning_effort: str | None = None,
        conversation_reasoning_effort: str | None = None,
        coalesce_pre_work: bool = True,
        timeout_seconds: float | None = None,
        semantic_capability: Any | None = None,
        conversation_provider: Any | None = None,
    ) -> None:
        self.repository_location = repository_location
        self.codex_factory = codex_factory or _default_codex_factory
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.timeout_seconds = timeout_seconds
        if (semantic_capability is None) != (conversation_provider is None):
            raise ValueError("Semantic and Conversation providers must be supplied together")
        self.semantic_capability = semantic_capability or CodexSdkInteractionSemanticCapability(
            repository_location=repository_location,
            codex_factory=self.codex_factory,
            model=model,
            reasoning_effort=reasoning_effort,
            timeout_seconds=timeout_seconds,
        )
        self.conversation_provider = conversation_provider or CodexSdkConversationProvider(
            repository_location=repository_location,
            codex_factory=self.codex_factory,
            model=conversation_model or model,
            reasoning_effort=conversation_reasoning_effort,
            timeout_seconds=timeout_seconds,
        )
        self.coalesce_pre_work = coalesce_pre_work
        self.response_composer = ConversationResponseComposer(
            self.conversation_provider
        )
        self.governed_response_realizer = CodexSdkGovernedResponseRealizer(
            repository_location=repository_location,
            codex_factory=self.codex_factory,
            model=conversation_model or model,
            reasoning_effort=conversation_reasoning_effort,
            timeout_seconds=timeout_seconds,
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

    def interpret_stream_observed(
        self,
        basis: InteractionInterpretationInput,
        *,
        on_response_delta: Callable[[str], None],
        on_pipeline_stage: Callable[[str], None],
    ) -> InteractionAssessmentCandidate:
        if (
            getattr(self.interpret_stream, "__func__", None)
            is not CodexSdkWorkInteractionCapability.interpret_stream
        ):
            return self.interpret_stream(basis, on_response_delta=on_response_delta)
        return self._interpret(
            basis, on_response_delta=on_response_delta,
            on_pipeline_stage=on_pipeline_stage,
        )

    def _interpret(
        self,
        basis: InteractionInterpretationInput,
        *,
        on_response_delta: Callable[[str], None] | None,
        on_pipeline_stage: Callable[[str], None] | None = None,
    ) -> InteractionAssessmentCandidate:
        self.last_pipeline_evidence = None
        self.last_collaboration_result = None
        if (
            getattr(self.response_composer, "provider", self.conversation_provider)
            is not self.conversation_provider
        ):
            raise InteractionInvariantViolation(
                "Conversation composer Provider does not match the configured Provider"
            )
        mode, selection_reason = self.pipeline_selection(basis)
        if mode == "coalesced_pre_work":
            return self._interpret_coalesced(
                basis, on_response_delta=on_response_delta,
                on_pipeline_stage=on_pipeline_stage,
            )
        started_at = monotonic()
        first_response_delta_seconds: float | None = None

        def publish_delta(delta: str) -> None:
            nonlocal first_response_delta_seconds
            if delta.strip() and first_response_delta_seconds is None:
                first_response_delta_seconds = monotonic() - started_at
            if on_response_delta is not None:
                on_response_delta(delta)

        semantic = self.semantic_capability.interpret_semantics(basis)
        semantic_completed_at = monotonic()
        self.last_collaboration_result = semantic.collaboration
        compose = self.response_composer.compose
        try:
            semantic_parameter = signature(compose).parameters.get("current_semantics")
        except (TypeError, ValueError):
            semantic_parameter = None
        composition_options: dict[str, Any] = {
            "on_response_delta": publish_delta if on_response_delta is not None else None
        }
        if semantic_parameter is not None and semantic_parameter.kind in (
            Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY
        ):
            composition_options["current_semantics"] = semantic
        response = compose(basis, semantic.collaboration, **composition_options)
        conversation_completed_at = monotonic()
        semantic_request_id = getattr(
            self.semantic_capability, "last_request_id",
            getattr(self.semantic_capability, "last_turn_id", None),
        )
        conversation_request_id = getattr(
            self.conversation_provider, "last_request_id",
            getattr(self.conversation_provider, "last_turn_id", None),
        )
        if not all(
            (
                semantic_request_id,
                conversation_request_id,
            )
        ):
            raise InteractionInvariantViolation(
                "Conversation pipeline completed without Provider provenance"
            )
        self.last_pipeline_evidence = ConversationPipelineEvidence(
            pipeline_reason=selection_reason,
            semantic_thread_id=getattr(self.semantic_capability, "last_thread_id", None),
            semantic_turn_id=getattr(self.semantic_capability, "last_turn_id", None),
            conversation_thread_id=getattr(self.conversation_provider, "last_thread_id", None),
            conversation_turn_id=getattr(self.conversation_provider, "last_turn_id", None),
            semantic_request_id=str(semantic_request_id),
            conversation_request_id=str(conversation_request_id),
            semantic_provider=getattr(self.semantic_capability, "provider_identity", None),
            conversation_provider=getattr(self.conversation_provider, "provider_identity", None),
            semantic_usage=getattr(self.semantic_capability, "last_usage", None),
            conversation_usage=getattr(self.conversation_provider, "last_usage", None),
            semantic_retry_count=getattr(self.semantic_capability, "last_retry_count", None),
            conversation_retry_count=getattr(self.conversation_provider, "last_retry_count", None),
            semantic_seconds=semantic_completed_at - started_at,
            conversation_seconds=conversation_completed_at - semantic_completed_at,
            first_response_delta_seconds=first_response_delta_seconds,
            semantic_prompt_characters=getattr(
                self.semantic_capability, "last_prompt_characters", None
            ),
            conversation_prompt_characters=getattr(
                self.conversation_provider, "last_prompt_characters", None
            ),
            semantic_model=getattr(self.semantic_capability, "model", None),
            conversation_model=getattr(self.conversation_provider, "model", None),
            semantic_reasoning_effort=getattr(
                self.semantic_capability, "reasoning_effort", None
            ),
            conversation_reasoning_effort=getattr(
                self.conversation_provider, "reasoning_effort", None
            ),
        )
        return self._assessment_candidate(semantic, response)

    def pipeline_selection(self, basis: InteractionInterpretationInput) -> tuple[str, str]:
        """Expose the effective route without running a Provider or changing state."""

        if not self.coalesce_pre_work:
            return "staged", "explicit_opt_out"
        if basis.active_work_context is not None:
            return "staged", "active_work"
        # Explicit replacements retain their own contracts and must be invoked.
        if (
            type(self.semantic_capability) is not CodexSdkInteractionSemanticCapability
            or type(self.conversation_provider) is not CodexSdkConversationProvider
            or type(self.response_composer) is not ConversationResponseComposer
            or type(self.response_composer.context_provider)
            is not WattNativeConversationContextAssembler
            or self.response_composer.provider is not self.conversation_provider
        ):
            return "staged", "custom_provider_or_context"
        if self.semantic_capability.model != self.conversation_provider.model:
            return "staged", "models_differ"
        if self.semantic_capability.reasoning_effort != self.conversation_provider.reasoning_effort:
            return "staged", "reasoning_efforts_differ"
        return "coalesced_pre_work", "native_pre_work_shared_configuration"

    @staticmethod
    def _assessment_candidate(
        semantic: InteractionSemanticCandidate,
        response: ConversationResponseCandidate,
    ) -> InteractionAssessmentCandidate:
        return InteractionAssessmentCandidate(
            turn_intent=semantic.collaboration.turn_intent,
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

    def _interpret_coalesced(
        self,
        basis: InteractionInterpretationInput,
        *,
        on_response_delta: Callable[[str], None] | None,
        on_pipeline_stage: Callable[[str], None] | None = None,
    ) -> InteractionAssessmentCandidate:
        """Share one ephemeral call; admission still waits for the complete envelope."""

        started_at = monotonic()
        first_response_delta_seconds: float | None = None
        stages: dict[str, float] = {}

        def stage(name: str) -> None:
            if name not in stages:
                stages[name] = monotonic() - started_at
                if on_pipeline_stage is not None:
                    on_pipeline_stage(name)

        def publish_delta(delta: str) -> None:
            nonlocal first_response_delta_seconds
            if delta.strip() and first_response_delta_seconds is None:
                first_response_delta_seconds = monotonic() - started_at
            if on_response_delta is not None:
                on_response_delta(delta)

        stage("provider_context_started")
        instruction = self.coalesced_instruction(basis)
        stage("provider_context_prepared")
        model = self.semantic_capability.model
        effort = self.semantic_capability.reasoning_effort
        stage("provider_starting")
        ApprovalMode, Sandbox = _codex_controls()
        with self.codex_factory() as codex:
            thread = codex.thread_start(
                approval_mode=ApprovalMode.deny_all,
                cwd=self.repository_location,
                ephemeral=True,
                model=model,
                sandbox=Sandbox.read_only,
            )
            turn = thread.turn(
                instruction,
                approval_mode=ApprovalMode.deny_all,
                cwd=self.repository_location,
                effort=effort,
                model=model,
                output_schema=self.coalesced_output_schema(),
                sandbox=Sandbox.read_only,
            )
            stage("provider_turn_started")
            terminal = _wait_for_streaming_terminal(
                turn,
                timeout_seconds=self.timeout_seconds,
                on_response_delta=(publish_delta if on_response_delta is not None else None),
                response_field="natural_response",
                on_pipeline_stage=stage,
            )
        stage("provider_teardown_completed")
        if terminal.timed_out or terminal.result is None:
            raise InteractionInvariantViolation(
                "Coalesced collaboration Provider did not complete in its bounded Turn"
            )
        result = terminal.result
        if _enum_value(result.status) != "completed" or result.error is not None:
            raise InteractionInvariantViolation(
                "Coalesced collaboration Provider did not return a completed result"
            )
        stage("payload_validation_started")
        try:
            payload = _CoalescedInteractionProviderPayload.model_validate_json(
                result.final_response.strip()
            )
        except (ValueError, TypeError) as error:
            raise InteractionInvariantViolation(
                "Coalesced collaboration Provider returned an invalid structured result "
                f"({_safe_validation_summary(error)})"
            ) from error
        content = payload.natural_response.strip()
        if not content:
            raise InteractionInvariantViolation(
                "Coalesced collaboration Provider returned an empty Human-facing response"
            )
        identity = f"codex-sdk:collaboration-thread:{thread.id}:turn:{turn.id}"
        semantic_values = payload.semantics.model_dump(
            exclude={
                "retained_prior_meaning_indexes", "reuse_prior_design_intent_frame",
                "meanings", "collaboration",
            }
        )
        semantic_values["meanings"] = self._expand_coalesced_meanings(payload.semantics, basis)
        semantic_values["collaboration"] = self._expand_coalesced_collaboration(
            payload.semantics, basis
        )
        semantic = InteractionSemanticCandidate(
            **semantic_values,
            provider_identity=identity,
            model_identity=model,
        )
        response = ConversationResponseCandidate(
            content=content, provider_identity=identity, model_identity=model
        )
        candidate = self._assessment_candidate(semantic, response)
        stage("payload_validated")
        self.last_collaboration_result = semantic.collaboration
        self.last_pipeline_evidence = ConversationPipelineEvidence(
            pipeline_mode="coalesced_pre_work",
            pipeline_reason="native_pre_work_shared_configuration",
            provider_call_count=1,
            coalesced_thread_id=str(thread.id),
            coalesced_turn_id=str(turn.id),
            coalesced_seconds=monotonic() - started_at,
            coalesced_prompt_characters=len(instruction),
            coalesced_model=model,
            coalesced_reasoning_effort=effort,
            first_response_delta_seconds=first_response_delta_seconds,
            coalesced_output_characters=len(result.final_response),
            coalesced_semantic_characters=len(json.dumps(
                payload.semantics.model_dump(mode="json"),
                ensure_ascii=False, separators=(",", ":"),
            )),
            retained_prior_meaning_count=len(payload.semantics.retained_prior_meaning_indexes),
            new_meaning_count=len(payload.semantics.meanings),
            reused_prior_design_intent_frame=payload.semantics.reuse_prior_design_intent_frame,
            provider_stage_seconds=dict(stages),
        )
        return candidate

    @staticmethod
    def _expand_coalesced_meanings(
        payload: _CoalescedSemanticProviderPayload,
        basis: InteractionInterpretationInput,
    ) -> tuple[InterpretationMeaning, ...]:
        indexes = payload.retained_prior_meaning_indexes
        prior = basis.prior_assessment
        if len(set(indexes)) != len(indexes) or any(
            index < 0 or prior is None or index >= len(prior.meanings)
            for index in indexes
        ):
            raise InteractionInvariantViolation(
                "Coalesced meaning retention references an invalid prior meaning index"
            )
        retained = () if prior is None else tuple(prior.meanings[index] for index in indexes)
        meanings = (*retained, *payload.meanings)
        source_ids = {record.id for record in basis.records}
        if any(
            source_id not in source_ids
            for meaning in meanings
            for source_id in meaning.source_record_ids
        ):
            raise InteractionInvariantViolation(
                "Coalesced meaning references a source record outside the exact basis"
            )
        return meanings

    @staticmethod
    def _expand_coalesced_collaboration(
        payload: _CoalescedSemanticProviderPayload,
        basis: InteractionInterpretationInput,
    ) -> StructuredCollaborationResult:
        frame = payload.collaboration.design_intent_frame
        prior = basis.prior_assessment
        if payload.reuse_prior_design_intent_frame:
            if prior is None or prior.design_intent_frame is None:
                raise InteractionInvariantViolation(
                    "Coalesced frame reuse requires an existing prior design intent frame"
                )
            if frame is not None:
                raise InteractionInvariantViolation(
                    "Coalesced frame reuse cannot also supply a new design intent frame"
                )
            if (
                payload.collaboration.turn_intent is ConversationTurnIntent.CORRECTION
                or any(meaning.kind is InterpretationMeaningKind.CORRECTION for meaning in payload.meanings)
            ):
                raise InteractionInvariantViolation(
                    "Coalesced frame reuse is not allowed for a correction"
                )
            frame = prior.design_intent_frame
        elif frame is None and prior is not None and prior.design_intent_frame is not None:
            raise InteractionInvariantViolation(
                "Coalesced prior frame requires explicit reuse or a complete replacement"
            )
        try:
            return StructuredCollaborationResult(
                **payload.collaboration.model_dump(exclude={"design_intent_frame"}),
                design_intent_frame=frame,
                known_relevant_facts=payload.candidate_context,
                current_objective=payload.desired_outcome,
            )
        except ValidationError as error:
            raise InteractionInvariantViolation(
                "Coalesced collaboration Provider returned an invalid structured result "
                f"({_safe_validation_summary(error)})"
            ) from error

    @staticmethod
    def coalesced_output_schema() -> dict[str, Any]:
        return _provider_strict_output_schema(
            _CoalescedInteractionProviderPayload.model_json_schema()
        )

    @staticmethod
    def coalesced_instruction(basis: InteractionInterpretationInput) -> str:
        return (
            CodexSdkInteractionSemanticCapability.instruction(basis, coalesced=True)
            + "\n\nConversation Intelligence expression policy:\n"
            + CodexSdkConversationProvider.response_policy()
            + "\n\nReturn one JSON envelope with natural_response FIRST, then semantics. "
            "Use the same interpretation for both; begin the useful answer before the "
            "semantic ledger. The response remains advisory until complete validation. "
            "Keep current facts, constraints and requests complete, including removals. "
            "For unchanged prior meanings, return their indexes in retained_prior_meaning_indexes; "
            "meanings contains only new/revised source interpretations. Omit superseded or "
            "irrelevant indexes; never rephrase retained meanings. Use [] when none exist. "
            "Every new meaning cites existing source_record_ids. Set reuse_prior_design_intent_frame "
            "true only when the entire prior frame remains unchanged and neither the turn "
            "nor new meanings express a CORRECTION; then set collaboration.design_intent_frame "
            "null to reuse the exact prior value. Otherwise set reuse false and provide the "
            "complete new/corrected frame; null without reuse is allowed only with no prior "
            "frame and no design intent. Never "
            "combine reuse with a supplied frame or carry a superseded frame into a changed "
            "object. Before returning, check collaboration.turn_intent and every new "
            "meaning.kind: if ANY is CORRECTION, reuse_prior_design_intent_frame MUST "
            "be false and collaboration.design_intent_frame MUST contain the full "
            "replacement frame, even when the correction only changes admission order "
            "or a repository prerequisite and the product category stays the same. "
            "Return no text outside the JSON."
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
