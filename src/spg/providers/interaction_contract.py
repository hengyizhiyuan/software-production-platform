"""Provider-neutral WIC wire contracts and collaboration pipeline."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from inspect import Parameter, signature
import json
from time import monotonic
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, ValidationError

from spg.application.conversation import (
    ConversationResponseComposer,
    WattNativeConversationContextAssembler,
    conversation_response_policy,
)
from spg.application.guided_design import design_schema_by_identity, design_schema_registry
from spg.domain.interaction_actions import InteractionActionCandidate, CanonicalOperation
from spg.domain.intent_realization import TurnSemanticCandidate
from spg.domain.response_contract import ResponseIntent
from spg.application.production_intelligence import default_system_capability_reality
from spg.application.response_contract_expression import (
    governed_contract_realizer_instruction,
    response_contract_expression_guidance,
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
from spg.domain.engineering_semantics import (
    EngineeringSemanticFactCandidate,
    NeutralSemanticExtractionCandidate,
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

def _safe_validation_summary(error: BaseException) -> str:
    """Expose schema locations/types without echoing Provider input or secrets."""

    if not isinstance(error, ValidationError):
        if isinstance(error, ValueError) and str(error).startswith(('ACTION_', 'SEMANTIC_', 'PRIMARY_', 'EXPLICIT_', 'PRODUCTION_', 'EXPECTED_', 'RESPONSE_', 'TURN_')):
            return str(error)[:300]
        return type(error).__name__
    issues = []
    safe_item_errors = {
        "SEMANTIC_TYPE_MISMATCH: operational items require an action",
        "SEMANTIC_TYPE_MISMATCH: only read-only questions may carry an action",
        "SEMANTIC_TYPE_MISMATCH: production items require structured production intent",
        "SEMANTIC_TYPE_MISMATCH: design frames belong to typed design or goal items",
        "Provider candidates cannot directly assert SUPERSEDED status",
        "System inference cannot assert Human-confirmed truth",
        "Semantic removal must identify the facts it supersedes",
        "Neutral extraction roles must align with ordered values",
    }
    for issue in error.errors(include_url=False, include_input=False)[:5]:
        location = ".".join(str(part) for part in issue.get("loc", ())) or "root"
        detail = str(issue.get("ctx", {}).get("error", ""))
        if detail in safe_item_errors:
            issues.append(f"{location}:{detail}")
        else:
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
            if "properties" in value:
                value["required"] = list(value["properties"])
            for nested in value.values():
                normalize(nested)
        elif isinstance(value, list):
            for nested in value:
                normalize(nested)

    normalize(normalized)
    return normalized

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

    response_intent: ResponseIntent | None = None
    interpreted_motive: str | None
    desired_outcome: str | None
    candidate_context: tuple[str, ...]
    candidate_constraints: tuple[str, ...]
    current_requests: tuple[str, ...]
    unresolved_material_questions: tuple[str, ...]
    action_candidates: tuple[InteractionActionCandidate, ...] = ()
    semantic_intent: TurnSemanticCandidate | None = None
    neutral_semantic_extractions: tuple[NeutralSemanticExtractionCandidate, ...] = ()
    semantic_fact_candidates: tuple[EngineeringSemanticFactCandidate, ...] = ()
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
    semantic_structured_repair_count: int | None = None
    semantic_action_repair_signal: str | None = None
    conversation_retry_count: int | None = None
    coalesced_retry_count: int | None = None
    coalesced_structured_repair_count: int | None = None

def _compact_interaction_basis(
    basis: InteractionInterpretationInput, *, coalesced: bool = False
) -> dict[str, Any]:
    """Remove transport-only duplication without truncating interpretation evidence."""

    payload = basis.model_dump(mode="json")
    payload["governed_semantic_history"] = [
        {"ir_id": prior["id"], "source_record_id": prior["source_record_id"],
         "items": [{"identity": f"{prior['id']}:{item['item_id']}",
                    "kind": item["kind"], "statement": item["statement"],
                    "action": None if item.get("action") is None else {
                        "operation": item["action"]["operation"],
                        "arguments": {key: value["value"] for key, value
                            in item["action"].get("arguments", {}).items()}},
                    "production": None if item.get("production") is None else {
                        "objective": item["production"]["objective"],
                        "current": item["production"]["current"]}}
                   for item in prior["items"]]}
        for prior in payload.get("governed_semantic_history", ())]
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

    @property
    def observed_content(self) -> str:
        return self._emitted

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

class InteractionSemanticContract:
    """Canonical WIC semantic schema and instruction."""

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
        capability_reality = default_system_capability_reality()
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
            "When active_work_context exists, its scope and authority remain governed. "
            "If pending_human_question is present and the latest Human input "
            "answers that question with a definite choice, classify HUMAN_DECISION, include a "
            "DECISION_INPUT meaning grounded in that latest record, and retain the verbatim answer "
            "in current_requests. This answer belongs to the current Work; an ANSWER or DECIDE "
            "response posture must not turn it into a side question. An unrelated comment, request "
            "for explanation or unresolved answer remains conversation and grants no authority. "
            "Preserve the governed Motive, outcome, context, constraints, and requests unless the latest input actually proposes "
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
            "A question about an existing feature's state, including an unpunctuated "
            "Chinese yes/no question ending in 吗, is a SIDE_QUESTION with "
            "NO_GOVERNED_CHANGE unless the Human actually requests a change. "
            "Answer it using known Reality and say when the status is unknown. "
            "For this side question, direct_answer should be a short answer in the "
            "Human's language; do not say Basis, governed, Work, or other internal "
            "process terms. Distinguish an absent requested effect from proof that "
            "no effect exists in a produced artifact. "
            "An explicit feature edit such as changing a sidebar width belongs to "
            "the current Work revision; a separately requested new application belongs "
            "to a distinct Work formation decision. "
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
            + "System Capability Reality: Watt is an AI-native software production "
            "system. It can understand intent and constraints, reason about software "
            "products and architecture, create or modify software artifacts through "
            "governed Work, execute bounded engineering tasks, and verify results using "
            "attributable evidence. It must not claim external submission, deployment, "
            "publication, account action, or another real-world effect without actual "
            "integration, authority, and evidence. This is capability truth, not marketing "
            "copy or permission to start Work. Capability Reality version: "
            + capability_reality.version
            + ". "
            + "Do not use tools, hidden conversation memory, or repository inspection. Provider "
            "output is advisory and creates no Work, Design, Plan, Authority, Evidence, "
            "or Runtime truth. Distinguish idle context from an actionable Motive. A "
            "clear long-lived Motive needs a desired outcome but not an exact production "
            "target. Repository binding, repository creation and exact artifact placement are "
            "production prerequisites, not material questions blocking pre-Work admission. "
            "Evaluate sufficiency for the NEXT safe governed step, not completeness of the "
            "whole Work. "
            "Repository-observable fields, existing API/storage, stack and current routes "
            "must first be discovered by the governed repository preparation path. Lack "
            "of source contents in this pre-Work input does not make them Human decisions. "
            "Do not invent a schema or ask Human to choose new storage before discovery. "
            "Put in unresolved_material_questions only Human-owned decisions "
            "that materially block that next step (authority, safety, destructive effect, "
            "scope, cost, privacy, external mutation, or acceptance meaning). Keep cheap, "
            "reversible details such as filenames, placeholder content, layout and styling "
            "as unconfirmed candidate assumptions or ambiguities in the Design Intent Frame; "
            "never present those defaults as Human-approved facts. A simple course-table "
            "page with invented data can form Work before its filename/style/orientation is "
            "fixed. Do not ask for another ceremonial confirmation before admission. "
            "When Human requests Work first and repository binding later, keep that sequence "
            "in context/requests and do not put repository selection in unresolved_material_questions. "
            "Preserve explicit facts, constraints, requests, corrections, and "
            "Human decisions. "
            "When a Human requests production and also asks Watt to analyze the "
            "repository to identify a decision for the Human, preserve that as a "
            "separate current ANALYSIS item dependent on the production item. "
            "Its answer remains unknown until grounded inspection; do not treat "
            "mentioned scope alternatives as a selected implementation scope. "
            "Do not require the Human to answer a question that Watt must first "
            "investigate in the repository. "
            "For software-production meaning whose repeated reinterpretation could "
            "materially change Production or Verification, populate the two-stage "
            "engineering semantic fields. neutral_semantic_extractions records only "
            "observable syntax such as ordered values, quantities, bounds, references, "
            "behavior, state change, or scope; it must not assign contextual roles that "
            "the Human did not explicitly name. Return exactly one explicit_roles entry "
            "for each values entry, using null when the Human named no role. "
            "IRK is the only Human-language interpreter. semantic_intent is mandatory and "
            "contains one or more typed items plus exact current-Human clause spans covering "
            "the entire utterance, including punctuation. Preserve EVERY independently meaningful "
            "clause, primary change, restriction, correction and future intent. Use OPERATIONAL_ACTION "
            "only for bounded operations, PRODUCTION_INTENT for product changes, QUESTION/ANALYSIS "
            "for answers, STATUS_QUERY for observed progress, EXPLORE/DESIGN for advisory ideas, "
            "CONSTRAINT/FACT/CORRECTION for their respective meanings. "
            "Every semantic item must be linked by semantic_item_ids from at least one "
            "exact current-Human clause, except a separately witnessed REPOSITORY_OBSERVED "
            "FACT. Link an inferred clarification QUESTION to the current request clause "
            "that motivates it while retaining MODEL_CANDIDATE provenance; do not present "
            "that question as an independent Human statement. If it is only response wording, "
            "omit the extra semantic item and keep the clarification in natural_response. "
            "observed_facts may contain "
            "only exact key/value pairs from observed_reality with REPOSITORY_OBSERVED provenance; "
            "a citation alone cannot turn your prose into observed fact. "
            "If you add a REPOSITORY_OBSERVED FACT item, include an exact observed_facts "
            "key/value claim from observed_reality; otherwise omit that supplemental item. "
            "Do not compress a mixed "
            "acquisition plus unresolved future modification into one item. Production.current "
            "is true only for a present request to make a product change; broad current goals remain "
            "production goals. When the actual current product objective or primary requested "
            "change has not been supplied, declare its key in production.unresolved_arguments "
            "(objective, primary_change, or repository_reference). A generic intention to change "
            "something supplies no executable product goal. Preserve independent current actions "
            "and future goals separately. Concrete broad business goals do supply objectives; "
            "implementation details remain owner choices. unresolved describes optional details; typed questions with "
            "blocks_current_step=true or item.requires_human can prevent current admission. "
            "Repository inspection and choosing safe implementation details belong to existing owners, "
            "not a Human questionnaire. primary_change retains the actual primary requested outcome. "
            "scope contains business scope summaries; it must not invent adjacent features. "
            "repository_required means the requested outcome depends on an ALREADY EXISTING "
            "repository/source identity to preserve or acquire. It does not mean implementation "
            "will eventually need code or Git storage. For a new product with no existing source, "
            "set repository_reference=null and repository_required=false; Watt may create its own "
            "managed source. Set repository_required=true only for an explicitly supplied existing "
            "repository, an applicable governed Product/Work source, or a request to continue an "
            "existing codebase whose source selection is unresolved. In that last case include "
            "repository_reference in unresolved_arguments and require Human resolution before "
            "production; never silently replace that existing source with a new workspace. "
            "Advisory DESIGN or EXPLORE items may carry design_frame. A PRODUCTION_INTENT "
            "item may carry a proposed design_frame, but only its production field can authorize "
            "the current goal; design assumptions never expand scope. "
            "A parallel Root design_intent_frame cannot override the IR or turn a question into systemic design. "
            "target_paths contains only literal Human-requested repository-relative file paths. "
            "allowed_areas contains only literal Human-requested filesystem patterns ending in /**. "
            "Natural business areas belong in scope. Discovered implementation paths remain owner hypotheses. "
            "bounded_change and systemic_design distinguish a "
            "bounded feature/maintenance task from explicitly requested system-wide design. new_work "
            "is true only for an explicitly independent new long-lived goal; current bounded continuation "
            "preserves the existing Work motive. Parallel legacy fields cannot override these IR semantics. "
            "For QUESTION and ANALYSIS items, answer contains the answer to that specific item, "
            "without claiming execution of a separate operational item. Keep mixed answers "
            "separate so actual owner results cannot erase an independently asked question. "
            "A current question about a repository property derived from source files "
            "needs a governed read operation when no exact owner observation already "
            "answers it. Bind INSPECT_REPOSITORY as a READ_ONLY_QUERY on that question "
            "or as its explicit dependency, ordered after ACQUIRE_REPOSITORY when acquisition "
            "is needed. Repository readiness, revision and tree metadata alone do not "
            "establish a framework, dependency or implementation fact. Do not invent an "
            "answer or turn this owner-readable fact into a Human decision. "
            "Each operational action uses the canonical operation enum, speech_act, structured "
            "arguments, conditional flag and unresolved uncertainty. Use only the argument keys "
            "consumed by that qualified operation; never supply parallel alternatives or ignored keys. "
            "First preserve each independent Human clause and its speech act, polarity, current or future "
            "scope, requested effect, correction and source span. Then bind canonical operations. "
            "Fill each SemanticClause speech_act, polarity, modality, temporal_scope, requested_effects, "
            "refers_to and supersedes from governed meaning. For a contextual reference, use the "
            "exact identity IR_UUID:item_id from governed_semantic_history in clause.refers_to; "
            "an older Human target argument is valid only when that referenced governed item binds "
            "the same target, while the current clause supplies fresh action consent. Do not copy "
            "earlier Human statements into new semantic items or current-source clauses; use "
            "governed history references for earlier meaning. "
            "A current effect must be supported by an "
            "affirmative current request clause; negative, future, hypothetical and question clauses carry "
            "no current write authority. Resolve contextual references to exact governed item identities. "
            "For every current branch action, atomic_branch_effects lists each physical effect separately "
            "with its exact target_branch and current Human clause provenance. CREATE_BRANCH authorizes "
            "only CREATE_BRANCH; SWITCH_BRANCH authorizes only SWITCH_BRANCH; "
            "CREATE_AND_SWITCH_BRANCH requires both CREATE_BRANCH and SWITCH_BRANCH claims. "
            "When one current Turn requests creating and then switching to the same branch, use one "
            "CREATE_AND_SWITCH_BRANCH item, not separate create and switch items. Ordering the two "
            "requested effects does not make the action conditional; reserve conditional=true for "
            "an external prerequisite that has not been satisfied. "
            "In clause.requested_effects use operation tokens such as CREATE_BRANCH and SWITCH_BRANCH; "
            "put the branch name in action.arguments.target_branch and each atomic effect target_branch. "
            "Judge the Human's requested checkout state, not just whether a branch name should exist. "
            "A single imperative can request a composite branch effect without separately saying "
            "'create' and 'switch': when its meaning is to move the current checkout onto a newly "
            "formed branch, preserve both effects. Creation alone is appropriate when the request "
            "concerns branch existence while the current checkout is to remain where it is. "
            "A single current clause may direct both creation of a new branch and movement of the "
            "current checkout to it; bind both effects when its meaning entails both. A request "
            "only to make a branch exist authorizes creation alone, and moving to an already "
            "existing branch authorizes switching alone. Audit these distinctions before output. "
            "When a same-Turn action refers to a target literally named in another current Human "
            "clause, link the action to that FACT item with depends_on and cite the exact target "
            "literal as argument provenance; the effect itself cites the current action clause. "
            "Do not infer a switch merely from creation, or creation merely from switching. "
            "When the exact requested effect is uncertain, declare it unresolved instead of adding an effect. "
            "Branch operations use target_branch as a local branch name (without refs/heads/). "
            "A new branch name requires literal current or earlier Human provenance; an observed "
            "existing branch cannot invent authority to create a new target. unresolved_arguments names "
            "only blocking argument keys; optional uncertainty prose in unresolved does not require "
            "Human intervention. Existing owners choose workspace paths and bind one observed exact "
            "baseline. Missing consent, multiple targets and irreversible decisions remain Human-owned. "
            "One Interaction binds one repository asset owner. When a current acquisition "
            "clause supplies distinct repository sources without selecting one target, "
            "keep repository_source unresolved and ask which source this Interaction should use; "
            "do not emit two executable acquisitions from one ambiguous clause. "
            "Supported operations are "
            + ", ".join(operation.value for operation in CanonicalOperation if operation is not CanonicalOperation.OTHER) + ". "
            "When an explicit imperative has no supported canonical operation or lacks a required "
            "target, preserve its current Human clause and emit a nonexecutable semantic item "
            "with the unresolved limitation and genuine Human dependency. Do not output OTHER, "
            "an empty semantic item list, or a different supported Action just to fit the schema. "
            "A file-level request must not acquire a branch effect through overlapping tooling vocabulary. "
            "FETCH_PUBLIC_RESOURCE uses a url argument; SEARCH_GITHUB can use a typed "
            "search_kind argument for repository, code or issue retrieval. Negated, hypothetical, quoted "
            "For public search query arguments, compile concise indexable technical keywords in "
            "the source's likely indexing language while preserving the Human's exact topic and "
            "scope; translating query terms is allowed, inventing a framework or product domain is not. "
            "or discussed commands do not authorize execution. Questions about capabilities are "
            "questions, not effects. Current explicit action consent must cite an exact span in "
            "the current Human record. "
            "A production goal can require preparatory inspection by its Work owner without "
            "making inspection a separately requested Human Action. Compile a current operational "
            "Action only when the Human clause actually asks for that operation; do not add an "
            "INSPECT_REPOSITORY action merely because an implementation goal needs code discovery. "
            "For any affirmative current operation or read-only query, set action.current true; "
            "only future or hypothetical clauses may describe noncurrent actions. "
            "Arguments may cite earlier Human evidence for contextual follow-ups, but old "
            "commands never confer new consent. target_branch, repository_source "
            "and candidate_revision must be bound to actual supplied or observed evidence. Include "
            "query as a structured search argument; do not require a downstream model to reinterpret "
            "the Human question. Queries may be MODEL_CANDIDATE with evidence_reference compiler:query "
            "and grant only bounded read-only retrieval. Mark unbound arguments unresolved. "
            "All operational/prod items and arguments retain provenance. Human provenance requires "
            "source_record_id and verbatim source_text. Non-Human origins need a real basis evidence "
            "reference, never a fabricated observation. Inferred facts never become Human authority. "
            "Production intent never grants delivery_authorized; explicit acceptance, delivery consent, "
            "push and PR are distinct operational items. Use depends_on item IDs for ordered effects. "
            "requires_human is true only for genuine unresolved material authority or safety. "
            "A current action or production goal with an exact current Human basis, "
            "resolved effect target and no Human-owned blocker needs calibrated "
            "confidence of at least 0.8 to cross the owner admission gate. If the "
            "evidence supports less confidence, preserve the specific uncertainty "
            "in typed unresolved arguments or requires_human; never use a low score "
            "alone as a silent substitute for an explicit blocker. "
            "Preserve typed questions with blocks_current_step, requires_human and provenance. "
            "For a question you infer rather than quote from the Human, use MODEL_CANDIDATE "
            "provenance with evidence_reference compiler:question and no Human source identity. "
            "Never set both requires_human and safe_reversible_assumption true: a required "
            "Human decision has no inferred answer. If Human explicitly reserves a product, architecture, "
            "authority, cost or risk choice (including analysis-first then let Human decide), also compile "
            "human_decisions: concrete subject/question, typed effect, exact Human-stated options as SemanticArguments "
            "with literal provenance, one material_effects entry per option, authority_provenance citing the exact "
            "current Human clause that reserves the choice, required_before_production, and why_now. "
            "This does not authorize Work or production. Keep requested analysis as ANALYSIS and do not "
            "turn routine implementation details or optional discovery into human_decisions. Empty is normal. "
            "A nonblocking optional question may "
            "use a reversible working assumption without requiring Human input now. "
            "Repository-observable questions and feature details deferred until discovery must "
            "have blocks_current_step false; missing external runtime secrets block only the "
            "owner boundary where actual observation proves necessity, not read-only preparation. "
            "Cheap reversible details may be explicit candidate assumptions with no operational "
            "authorization. Record human_abstraction_level and uncertain for expression strategy. "
            "Operational.current distinguishes current execution from a future request after a "
            "production outcome. A requested Preview after product completion is part of the "
            "production acceptance obligation (preview_required true), not a current Preview "
            "with no Candidate. Current Preview requests must retain a verifiable action obligation. "
            "Actually preparing or starting an existing project so that its running Preview can be reviewed "
            "is a current production goal even when no source edit is requested. The runtime owner must inspect "
            "the exact source and reach any genuine missing-credential boundary; do not claim the credential "
            "is already present or omit the production goal because startup may require a secret. "
            "For status subjects use WORK_CURRENT, WORK_HISTORY, WORK_DIAGNOSTIC or PREVIEW as "
            "appropriate; a current checked-out branch QUESTION or STATUS_QUERY must carry QUERY_CURRENT_BRANCH "
            "with READ_ONLY_QUERY, which remains strictly read-only. QUERY_CURRENT_BRANCH "
            "asks for the currently checked-out branch and accepts no target_branch argument. "
            "A question about whether a separately named branch exists is a read-only QUESTION "
            "about that named branch, not a request to create or switch it and not a query "
            "for the current checkout. Set its typed subject to branch:<exact local branch name> "
            "and omit QUERY_CURRENT_BRANCH; that Action reports only the checked-out branch. "
            "Cite the branch name from the current Human clause; "
            "answer existence only from actual owner evidence, and retain uncertainty when "
            "the supplied observation does not establish that fact. "
            "action_candidates is a deprecated compatibility field: return [] because the application "
            "projects it from governed semantic_intent. Collaboration/response_intent is an "
            "interaction directive consuming these same items, never a second interpretation. "
            "semantic_fact_candidates then binds "
            "those observations to small reusable product-semantic relations and "
            "Work-scoped subjects. Use contextual subjects such as image.width or "
            "api.response_time; do not invent domain parser types. Keep product meaning "
            "distinct from HTML/DOM or other implementation shape. HUMAN_EXPLICIT means "
            "the Human explicitly supplied the semantic role; inferred contextual roles "
            "must be SYSTEM_INFERRED with WORKING_ASSUMPTION or UNRESOLVED. "
            "For REFERENCE facts, set reference_role to PROJECT_REPOSITORY only when the "
            "Human explicitly identifies the exact URL as their current Product or Project "
            "repository. Set EXTERNAL_REFERENCE for an external example, article, or source "
            "repository; otherwise leave it null. This role is typed meaning, never inferred "
            "from the fact subject spelling, language, host, or URL shape. "
            "PROJECT_REPOSITORY requires HUMAN_EXPLICIT authority, CONFIRMED status, "
            "EXPLICIT role origin, and exact Human source text containing the URL. "
            "A later explicit "
            "correction identifies the current fact UUIDs it supersedes. Preserve current "
            "facts unless the Human changes or removes them. Use empty arrays when no fact "
            "earns structured representation. Every neutral extraction and semantic fact "
            "source_text must be an exact verbatim non-empty substring of the cited Human "
            "source record; do not normalize spacing, punctuation, casing, or wording, and "
            "cite the record that actually contains that exact text. "
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
            "IRK owns meaning; WIC consumes it for interaction strategy. "
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
            "use corrected facts without reopening them. Unsupported disagreement is not "
            "a correction of fact and must not reverse a judgment by itself. "
            "Populate response_intent for THIS turn, independently of the Work lifecycle: "
            "EXPLORE contributes relevant possibilities; ANALYZE assesses a claim or architecture; "
            "DESIGN shapes a solution; DECIDE chooses with decisive tradeoffs; ANSWER answers a "
            "bounded question; DIAGNOSE investigates an observed symptom; EXECUTE requests action "
            "on sufficiently clear intent; CORRECT replaces a mistaken understanding; STATUS "
            "reports actual progress. A topic does not determine mode: discussion of an existing "
            "plan differs from a command to carry it out. Use executable_context only when the "
            "current request and context sufficiently specify a bounded next action; this grants "
            "no authority. Distinguish a bounded knowledge question from a how-to request about "
            "a software-production object, and both from an explicit request that Watt create or "
            "modify software. A technical topic alone is not a production goal; HOW_TO should "
            "preserve the domain answer, while BUILD or ACTION_REQUEST must not be reduced to a "
            "generic tutorial. Refine design collaboration compositionally with "
            "design_collaboration_mode: DESIGN_EXPLORE when the Human wants divergence or "
            "brainstorming, DESIGN_REVIEW when inspecting an existing proposal or challenging "
            "its assumptions, DESIGN_DECIDE when comparing and converging on a recommendation, "
            "and null when the turn is not design collaboration. This refinement does not "
            "replace interaction_mode or create Product Truth. For exploration/discussion/status use SIDE_QUESTION and "
            "NO_GOVERNED_CHANGE on active Work; do not turn conversational ideas into changes. "
            "Use minimal sufficient semantic answer material: no tutorial unless requested. "
            "Questions have cost: unresolved_material_questions is empty unless a missing answer "
            "materially blocks result, authority, safety, cost, scope or acceptance and cannot be "
            "handled by a reversible assumption. Missing diagnostic evidence is not itself "
            "an authority blocker. For ambiguous EXPLORE intent, rank open decisions by how much "
            "they change the next product or engineering decision. Surface only the single "
            "highest-value question, favoring goal, target user, material constraint, success "
            "criterion or product boundary over premature implementation detail. Stop refining "
            "when the next useful decision is sufficiently clear; do not build a questionnaire. "
            "Do not invent a permission/consent question because logs "
            "might hypothetically contain sensitive data; ask only for a concrete missing "
            "fact after available ordinary checks are exhausted. A request to fix a defect "
            "asks Watt to own the checks and repair, not return a debugging questionnaire. "
            "EXECUTE needs a brief acknowledgment and "
            "governed next action, not a replay of settled design. EXPLORE needs useful ideas, "
            "not a questionnaire or one-line acknowledgment. When EXECUTE follows settled "
            "design, consume current Engineering Semantic Truth and Work Reality exactly; do "
            "not reinterpret the original phrase, reopen decisions, or silently replace an "
            "unspecified implementation detail with a conflicting assumption. "
            "In response_intent keep FACT, INFERENCE, RECOMMENDATION, WORKING_ASSUMPTION, "
            "PREFERENCE and UNCERTAINTY distinct. Record a concise judgment_proposition and "
            "judgment_basis as exact existing reference IDs or exact supplied evidence/constraints; "
            "set judgment_subject to the stable decision topic, retaining it for objections and "
            "changing it for unrelated questions. "
            "never invent evidence. The previous_response_contract is advisory turn history, "
            "not engineering truth. Unsupported disagreement must inspect and preserve its "
            "judgment unless actual new facts, disproven evidence, changed goals/priorities or "
            "a demonstrated inference error changes the basis. Explain a proposed change in "
            "judgment_change_reason and cite its basis; mere disagreement is not new evidence. "
            "When the Human reports an attempted strategy failed, set prior_strategy_failed, "
            "with a stable repeated_failure_signature describing the symptom (reuse it across "
            "the same failure); change diagnostic strategy, do not repeat prior repair advice. "
            "These fields are short interaction evidence, not private reasoning. "
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

class ConversationContract:
    """Canonical Human-facing response schema and instruction."""

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
            + ConversationContract.response_policy()
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


class WorkInteractionPipeline:
    """Provider-neutral WIC semantic and conversation composition."""

    def __init__(
        self, *, repository_location: str, model: str | None = None,
        conversation_model: str | None = None,
        reasoning_effort: str | None = None,
        conversation_reasoning_effort: str | None = None,
        timeout_seconds: float | None = None,
        coalesce_pre_work: bool = True,
        semantic_capability: Any,
        conversation_provider: Any,
    ) -> None:
        self.repository_location = repository_location
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.timeout_seconds = timeout_seconds
        self.semantic_capability = semantic_capability
        self.conversation_provider = conversation_provider
        self.coalesce_pre_work = coalesce_pre_work
        self.response_composer = ConversationResponseComposer(conversation_provider)
        self.governed_response_realizer = None
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
            is not WorkInteractionPipeline.interpret_stream
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
        return "staged", "provider_neutral_pipeline"

    @staticmethod
    def _assessment_candidate(
        semantic: InteractionSemanticCandidate,
        response: ConversationResponseCandidate,
    ) -> InteractionAssessmentCandidate:
        return InteractionAssessmentCandidate(
            turn_intent=semantic.collaboration.turn_intent,
            response_intent=semantic.response_intent,
            interpreted_motive=semantic.interpreted_motive,
            desired_outcome=semantic.desired_outcome,
            design_intent_frame=semantic.collaboration.design_intent_frame,
            candidate_context=semantic.candidate_context,
            candidate_constraints=semantic.candidate_constraints,
            current_requests=semantic.current_requests,
            unresolved_material_questions=semantic.unresolved_material_questions,
            neutral_semantic_extractions=semantic.neutral_semantic_extractions,
            semantic_fact_candidates=semantic.semantic_fact_candidates,
            action_candidates=semantic.action_candidates,
            semantic_intent=semantic.semantic_intent,
            meanings=semantic.meanings,
            focus_classification=semantic.focus_classification,
            impact_disposition=semantic.impact_disposition,
            supporting_references=semantic.supporting_references,
            natural_response=response.content,
            provider_identity=semantic.provider_identity,
            model_identity=semantic.model_identity,
        )

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
            InteractionSemanticContract.instruction(basis, coalesced=True)
            + "\n\nConversation Intelligence expression policy:\n"
            + ConversationContract.response_policy()
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
        """Provider-neutral alias for the WIC semantic wire contract."""

        return InteractionSemanticContract.output_schema()

    @staticmethod
    def conversation_output_schema() -> dict[str, Any]:
        return ConversationContract.output_schema()

    @staticmethod
    def _instruction(basis: InteractionInterpretationInput) -> str:
        """Provider-neutral alias for focused contract inspection."""

        return InteractionSemanticContract.instruction(basis)
