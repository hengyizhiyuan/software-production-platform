"""DeepSeek adapters for WIC semantics and Human-facing conversation."""

from __future__ import annotations

from dataclasses import asdict
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
    ConversationTurnIntent,
    ConversationContext,
    ConversationResponseCandidate,
    StructuredCollaborationResult,
)
from spg.domain.interaction import (
    InteractionAssessmentCandidate,
    InteractionInterpretationInput,
    InteractionInvariantViolation,
    InteractionSemanticCandidate,
    StructuredResponseSchemaViolation,
)
from spg.domain.intent_realization import SemanticKind, TurnSemanticCandidate
from spg.domain.engineering_semantics import (
    EngineeringSemanticFactCandidate, current_semantic_facts,
)
from spg.domain.model_runtime import ModelPurpose, StructuredModelResult, WattModelRuntime
from spg.domain.wic_response import (
    GovernedResponseEnvelope,
    GovernedResponseRealization,
)
from spg.providers.interaction_contract import (
    ConversationContract,
    InteractionSemanticContract,
    WorkInteractionPipeline,
    ConversationPipelineEvidence,
    _CoalescedInteractionProviderPayload,
    _ConversationProviderPayload,
    _InteractionSemanticProviderPayload,
    _JsonStringFieldStream,
    _safe_validation_summary,
)


LOGGER = logging.getLogger(__name__)


def _discard_unbound_supersession(
    semantic: TurnSemanticCandidate,
    facts: tuple[EngineeringSemanticFactCandidate, ...],
    basis: InteractionInterpretationInput,
) -> tuple[TurnSemanticCandidate, tuple[EngineeringSemanticFactCandidate, ...], int]:
    """Drop only revocations unsupported by current owner Reality."""
    allowed_obligations = {
        reference.removeprefix("obligation:")
        for observation in basis.observed_reality
        if observation.owner == "turn-obligation-ledger"
        and observation.facts.get("state") in {"PENDING", "RUNNING"}
        for reference in observation.evidence_references
        if reference.startswith("obligation:")
    }
    prior_facts = (basis.active_work_context.work_revision.engineering_semantic_facts
        if basis.active_work_context is not None else
        (() if basis.prior_assessment is None else basis.prior_assessment.engineering_semantic_facts))
    current_fact_ids = {fact.id for fact in current_semantic_facts(prior_facts)}
    removed = 0
    items = []
    for item in semantic.items:
        supported = (tuple(ref for ref in item.supersedes if ref in allowed_obligations)
            if item.kind is SemanticKind.CORRECTION else ())
        removed += len(item.supersedes) - len(supported)
        items.append(item if supported == item.supersedes else
            item.model_copy(update={"supersedes": supported}))
    supported_facts = []
    for fact in facts:
        if set(fact.supersedes_fact_ids) <= current_fact_ids:
            supported_facts.append(fact)
        else:
            removed += 1
    if removed:
        LOGGER.warning("WIC compiler discarded %s unbound supersession claims", removed)
    return (semantic.model_copy(update={"items": tuple(items)}),
        tuple(supported_facts), removed)


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


def _repair_structured_result(
    runtime: WattModelRuntime,
    *,
    purpose: ModelPurpose,
    invalid_output: str,
    output_schema: dict[str, object],
    on_stage: Callable[[str], None] | None,
    contract_name: str,
    original_instruction: str,
    validation_feedback: str,
) -> StructuredModelResult:
    """Run one structure-only repair without exposing a second provisional stream."""

    repair_guidance = ""
    if "supersession needs current Human correction" in validation_feedback:
        repair_guidance += (
            "Set supersedes to [] on every FACT and OPERATIONAL_ACTION item. "
            "These items cannot revoke earlier effects; keep the current action and "
            "its exact arguments, and keep separate constraints as separate items. "
            "Do not invent a CORRECTION item. "
        )
    if "semantic_fact_candidates." in validation_feedback and "value_error" in validation_feedback:
        repair_guidance += (
            "Repair semantic_fact_candidates authority and lineage: a candidate cannot "
            "assert SUPERSEDED; SYSTEM_INFERRED cannot assert CONFIRMED; REMOVE requires "
            "exact prior fact UUIDs in supersedes_fact_ids. If those facts are unavailable, "
            "omit that ungrounded fact candidate while preserving semantic_intent. "
        )
    if "supersession target is outside current owner basis" in validation_feedback:
        repair_guidance += (
            "Cite only exact pending or running obligation IDs present in current owner "
            "observations. If none is available, set item supersedes to []; preserve "
            "the current Work correction in structured Production Intent. "
        )
    if "non-Human evidence is outside the governed basis" in validation_feedback:
        repair_guidance += (
            "Remove optional claims that cite unobserved evidence references. Never "
            "replace an effect target with model inference; retain source-grounded "
            "current Human intent and ask only if a required target remains unresolved. "
        )
    if "HUMAN_DECISION_" in validation_feedback:
        repair_guidance += (
            "Preserve the Human-reserved choice and requested analysis. Copy each option.value "
            "verbatim from its exact current Human source_text, with HUMAN_EXPLICIT origin "
            "and the current source_record_id. Do not paraphrase options, invent alternatives, "
            "drop a real reserved choice, create a Work, or substitute model authority. "
        )
    if "LOW_CONFIDENCE" in validation_feedback:
        repair_guidance += (
            "Reassess the cited current effect against the exact Human clause and "
            "typed dependencies. Give it execution-level confidence only when the "
            "current request and target are actually supported; otherwise preserve "
            "the uncertainty as a specific typed unresolved argument or genuine "
            "Human-owned decision. Never raise confidence merely to pass validation. "
        )
    if "source-derived repository question" in validation_feedback:
        repair_guidance += (
            "Keep the exact current repository question and its Human provenance. "
            "Bind a current READ_ONLY_QUERY INSPECT_REPOSITORY operation to that "
            "question, or add one ordered dependency, so the repository owner can "
            "read source evidence at the acquired revision before answering. "
            "Do not claim source-derived facts from acquisition metadata alone. "
        )
    if "current branch query needs its read-only owner action" in validation_feedback:
        repair_guidance += (
            "Preserve the current Human branch-status question and any exact owner "
            "fact already observed. Attach a current READ_ONLY_QUERY "
            "QUERY_CURRENT_BRANCH action to that question, with no target_branch; "
            "this operation only reads the checked-out branch. "
        )
    if "READ_RESULT_PREMATURE" in validation_feedback:
        repair_guidance += (
            "Separate an explanatory answer from an actual repository read. "
            "If the Human requested general possibilities and no current source fact, "
            "keep the advisory answer and remove the current read action. If the "
            "Human requested a source-grounded finding, retain the read action "
            "and leave the answer pending until owner evidence is observed. "
        )
    if on_stage is not None:
        on_stage("structured_output_repair_started")
    result = runtime.generate(
        purpose=purpose,
        instructions=(
            f"Repair one completed {contract_name} JSON result to the supplied exact "
            "schema. This is structural repair only. Preserve every existing business "
            "meaning and Human-facing statement exactly unless a change is strictly "
            "required to satisfy the schema or the cited action-binding validation. "
            "For ACTION_REQUEST_MISSING_CANONICAL_BINDING, recover the action meaning "
            "from the original exact latest Human record into action_candidates; do not "
            "reuse an older request, invent a target or turn discussion into consent. "
            "Remove forbidden extra fields. Do not infer "
            "new facts, add recommendations, change authority, or create Semantic Truth. "
            "If a semantic item kind/action mismatch is cited, use a valid nonexecutable "
            "item for unresolved or unsupported meaning; omit the invalid action. Preserve "
            "the Human clause and its limitation instead of dropping all semantic items. "
            "Return only the repaired JSON object.\n"
            f"Observed validation locations/types: {validation_feedback}\n"
            f"{repair_guidance}\n"
            "Original governing contract and exact basis follow. Use them only to "
            "satisfy the rejected contract, including cross-field authority constraints "
            "that JSON Schema cannot express; do not regenerate valid business meaning.\n"
            + original_instruction
        ),
        input_text=invalid_output,
        output_schema=output_schema,
        on_output_delta=None,
        on_stage=on_stage,
    )
    if on_stage is not None:
        on_stage("structured_output_repair_completed")
    return result


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
        self.last_action_repair_signal = None
        self.last_structured_repair_count = 0
        self.last_result: StructuredModelResult | None = None

    def interpret_semantics(
        self,
        basis: InteractionInterpretationInput,
        *,
        on_stage: Callable[[str], None] | None = None,
    ) -> InteractionSemanticCandidate:
        instruction = InteractionSemanticContract.instruction(basis)
        self.last_prompt_characters = len(instruction)
        result = self.runtime.generate(
            purpose=ModelPurpose.WIC_SEMANTIC,
            instructions=instruction,
            input_text="Return the WIC semantic result for the exact supplied basis.",
            output_schema=InteractionSemanticContract.output_schema(),
            on_stage=on_stage,
        )
        self.last_action_repair_signal = None
        self.last_structured_repair_count = 0
        schema = InteractionSemanticContract.output_schema()
        for attempt in range(4):
            try:
                payload = _InteractionSemanticProviderPayload.model_validate_json(
                    _structured_json_text(result.output_text)
                )
                if payload.semantic_intent is not None:
                    semantic, facts, removed = _discard_unbound_supersession(
                        payload.semantic_intent, payload.semantic_fact_candidates, basis)
                    payload = payload.model_copy(update={
                        "semantic_intent": semantic, "semantic_fact_candidates": facts})
                    self.last_structured_repair_count += int(bool(removed))
                self._validate_action_semantics(payload, basis)
                break
            except (ValidationError, ValueError, TypeError) as error:
                issue = _safe_validation_summary(error)
                if isinstance(error, ValueError) and str(error).startswith((
                        'ACTION_', 'SEMANTIC_', 'PRIMARY_', 'EXPLICIT_', 'PRODUCTION_', 'LOW_', 'HUMAN_DECISION_')):
                    from spg.domain.refinement_contract import RefinementSignalKind
                    signal = str(error).split(":", 1)[0]
                    try:
                        self.last_action_repair_signal = RefinementSignalKind(signal).value
                    except ValueError:
                        self.last_action_repair_signal = "SCHEMA_INVALID"
                    issue = str(error)
                if attempt == 3:
                    raise StructuredResponseSchemaViolation(
                        "WIC semantic Provider returned an invalid structured result after "
                        f"three bounded repair attempts ({issue}; bounded_repair_exhausted)",
                        request_id=result.request_id, validation_issue=issue,
                        repair_attempted=True, repair_attempts=3,
                    ) from error
                LOGGER.warning(
                    "WIC semantic validation failed request=%s model=%s status=completed "
                    "stage=payload_validation issue=%s %s repair=started",
                    result.request_id, result.effective_model or result.requested_model,
                    issue, _safe_result_shape(result.output_text),
                )
                result = _repair_structured_result(
                    self.runtime, purpose=ModelPurpose.WIC_SEMANTIC,
                    invalid_output=result.output_text, output_schema=schema,
                    on_stage=on_stage, contract_name="WIC semantic",
                    original_instruction=instruction, validation_feedback=issue,
                )
                self.last_structured_repair_count += 1
        if on_stage is not None:
            on_stage("semantic_payload_validated")
        self._observe(result)
        return InteractionSemanticCandidate(
            **payload.model_dump(),
            provider_identity=self._result_identity(result, "semantic"),
            model_identity=result.effective_model or result.requested_model,
        )

    @staticmethod
    def _validate_action_semantics(payload, basis) -> None:
        from spg.application.intent_realization import validate_semantic_candidate
        if payload.semantic_intent is None:
            signal = "EXPLICIT_ACTION_LOST_BEFORE_EXECUTION" if payload.collaboration.turn_intent is ConversationTurnIntent.ACTION_REQUEST else "SEMANTIC_TYPE_MISMATCH"
            raise ValueError(f"{signal}: IRK compiler omitted semantic_intent")
        validate_semantic_candidate(payload.semantic_intent, basis)
        # Cross-reference validity belongs to the same bounded structured-result
        # repair. Do not discover a broken fact/extraction link after admission.
        from spg.application.engineering_semantics import bind_engineering_semantic_facts
        prior = (basis.active_work_context.work_revision.engineering_semantic_facts
            if basis.active_work_context is not None else
            (() if basis.prior_assessment is None else basis.prior_assessment.engineering_semantic_facts))
        try:
            bind_engineering_semantic_facts(basis_fingerprint=basis.basis_fingerprint,
                records=basis.records, extractions=payload.neutral_semantic_extractions,
                candidates=payload.semantic_fact_candidates, prior_facts=prior)
        except InteractionInvariantViolation as error:
            raise ValueError(f'SEMANTIC_BINDING_INVALID: {error}') from error

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
        instruction = ConversationContract.instruction(context, collaboration)
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
            output_schema=ConversationContract.output_schema(),
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
        self.last_structured_repair_count = 0

    def realize_human_projection(self, projection, *, feedback=None):
        from spg.domain.human_visible import HumanVisibleWording
        from spg.providers.semantic_wire import _provider_strict_output_schema
        result = self.runtime.generate(purpose=ModelPurpose.CONVERSATION_RESPONSE,
            instructions=("You are Watt's WIC Human-visible Response Realizer, the sole ordinary expression authority. "
                "IRK governs meaning; owners govern facts. Express the supplied derived projection in natural Chinese. "
                "Return a coherent wording set once for all Workspace surfaces. Never change status, outcome, "
                "authority, Verification, Guardian, Candidate readiness or evidence. No new scope or Human decision. "
                "Agenda uses exact supplied ids, describes actual step roles in this governed motive; never copies "
                "or literally translates owner objectives. Use the actual product goal (such as the requested website) "
                "and concrete current progress. Avoid workflow narration such as current production step, governed "
                "plan, admitted long-lived Work, or work is ready. Explain constraints as confirmed goals, required "
                "boundaries and approved choices; do not make the user learn internal methodology or context classes. "
                "owner objectives or methodology templates. Decisions uses exact supplied ids and grounded options; "
                "when no decision_needs, decisions must be empty and do not ask for confirmation or implementation choices. "
                "Explain only concrete blockers. No raw enums, class names, hashes, UUIDs, schema keys or internal English "
                "If admission_context.status is NOT_READY, state that production preparation is blocked and has not "
                "entered execution; explain its exact missing/conflicting/stale basis in plain language. A READY Work "
                "does not override that gate. Do not promise autonomous continuation before the basis is ready. "
                "A missing approved-decision/context source is an engineering evidence gap, not permission to "
                "ask the Human to restate intent, confirm scope, or fix prerequisites. Only qualified decision_needs "
                "establish a current Human action. If those are empty, never assign the blocker to the Human. "
                "A CLOSED DESIGN step proves only that its bounded direction check closed; it does not prove "
                "a design artifact, content structure, visual design or approval exists. When APPROVED_DECISION "
                "is missing, never claim an approved design plan or completed visual/content design. "
                "templates in prose (ids only in id fields). If facts lack evidence, preserve uncertainty and do not claim success. "
                "Return headline, summary, current_activity, next_step, agenda(id,text), decisions(id,title,question,why_now), "
                "production_units(id,text). No independent factual or authority fields. "
                + ("Previous wording was rejected: " + feedback if feedback else "")),
            input_text=json.dumps(projection.model_dump(mode="json"), ensure_ascii=False),
            output_schema=_provider_strict_output_schema(HumanVisibleWording.model_json_schema()))
        return HumanVisibleWording.model_validate_json(_structured_json_text(result.output_text))

    def realize_stream(
        self,
        envelope: GovernedResponseEnvelope,
        *,
        on_response_delta: Callable[[str], None],
    ) -> GovernedResponseRealization:
        self.last_structured_repair_count = 0
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
            "Never expose raw enums, internal object names, UUIDs, fingerprints, Guided Design objectives or Steering templates. Translate source-owned facts into natural Chinese without inventing decisions or success. Never emit any forbidden_claim. Return JSON only with one natural_response "
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
        if envelope.expression_refinement:
            instruction += "\nExpression-only correction; retain the exact governed basis, emit no raw internals and do not repeat admitted prefix:\n" + json.dumps(envelope.expression_refinement, ensure_ascii=False)
        result = self.runtime.generate(
            purpose=ModelPurpose.CONVERSATION_RESPONSE,
            instructions=instruction,
            input_text="Realize this governed response without changing its semantics.",
            output_schema=ConversationContract.output_schema(),
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
            result = _repair_structured_result(
                self.runtime, purpose=ModelPurpose.CONVERSATION_RESPONSE,
                invalid_output=result.output_text,
                output_schema=ConversationContract.output_schema(), on_stage=None,
                contract_name="Governed Response Realizer",
                original_instruction=instruction,
                validation_feedback=_safe_validation_summary(error),
            )
            self.last_structured_repair_count = 1
            try:
                payload = _ConversationProviderPayload.model_validate_json(
                    _structured_json_text(result.output_text)
                )
            except (ValidationError, ValueError, TypeError) as second_error:
                raise StructuredResponseSchemaViolation(
                    "Governed Response Realizer returned an invalid result after "
                    "one bounded structural repair (bounded_repair_exhausted)",
                    request_id=result.request_id,
                    validation_issue=_safe_validation_summary(second_error),
                    repair_attempted=True, repair_attempts=1,
                ) from second_error
            if extractor.complete and extractor.observed_content.strip():
                # Structural repair may repair the envelope, but cannot rewrite
                # a complete string already observed by the governed delta gate.
                payload = payload.model_copy(update={
                    'natural_response': extractor.observed_content})
        self.last_result = result
        return GovernedResponseRealization(
            content=payload.natural_response,
            structural_repair_count=self.last_structured_repair_count,
            provider_identity=(
                "deepseek-responses:governed-realizer:request:"
                f"{result.request_id or 'unknown'}"
            ),
            model_identity=result.effective_model or result.requested_model,
            request_id=result.request_id,
            usage=_usage(result),
            timing=asdict(result.timing),
        )


class DeepSeekWorkInteractionCapability(WorkInteractionPipeline):
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
        """Interpret with repair owned by the exact structured Provider boundary."""
        return super().interpret_stream_observed(
            basis,
            on_response_delta=on_response_delta,
            on_pipeline_stage=on_pipeline_stage,
        )

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

        return self._interpret(
            basis,
            on_response_delta=observe_only,
            on_pipeline_stage=on_pipeline_stage,
            controlled_semantic_only=True,
        )

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
            provider_call_count=1 + self.semantic_capability.last_structured_repair_count,
            semantic_request_id=self.semantic_capability.last_request_id,
            semantic_provider=self.semantic_capability.provider_identity,
            semantic_usage=self.semantic_capability.last_usage,
            semantic_retry_count=(self.semantic_capability.last_retry_count or 0)
            + self.semantic_capability.last_structured_repair_count,
            semantic_structured_repair_count=self.semantic_capability.last_structured_repair_count,
            semantic_action_repair_signal=self.semantic_capability.last_action_repair_signal,
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
        repair_count = 0
        for attempt in range(4):
            try:
                payload = _CoalescedInteractionProviderPayload.model_validate_json(
                    _structured_json_text(result.output_text)
                )
                if payload.semantics.semantic_intent is not None:
                    semantic, facts, removed = _discard_unbound_supersession(
                        payload.semantics.semantic_intent,
                        payload.semantics.semantic_fact_candidates, basis)
                    payload = payload.model_copy(update={"semantics": payload.semantics.model_copy(
                        update={"semantic_intent": semantic,
                            "semantic_fact_candidates": facts})})
                    repair_count += int(bool(removed))
                DeepSeekInteractionSemanticCapability._validate_action_semantics(payload.semantics, basis)
                try:
                    self._expand_coalesced_meanings(payload.semantics, basis)
                    self._expand_coalesced_collaboration(payload.semantics, basis)
                except InteractionInvariantViolation as error:
                    raise ValueError("SEMANTIC_TYPE_MISMATCH: " + str(error)) from error
                if not payload.natural_response.strip():
                    raise ValueError("RESPONSE_EMPTY: coalesced Human response is empty")
                break
            except (ValidationError, ValueError, TypeError) as error:
                issue = _safe_validation_summary(error)
                if attempt == 3:
                    raise StructuredResponseSchemaViolation(
                        "Coalesced collaboration Provider returned an invalid structured "
                        f"result after three bounded repair attempts ({issue}; "
                        "bounded_repair_exhausted)",
                        request_id=result.request_id, validation_issue=issue,
                        repair_attempted=True, repair_attempts=3,
                    ) from error
                LOGGER.warning(
                    "Coalesced collaboration validation failed request=%s model=%s "
                    "status=completed stage=payload_validation issue=%s %s repair=started",
                    result.request_id, result.effective_model or result.requested_model,
                    issue, _safe_result_shape(result.output_text),
                )
                result = _repair_structured_result(
                    self.runtime, purpose=ModelPurpose.WIC_SEMANTIC,
                    invalid_output=result.output_text,
                    output_schema=self.coalesced_output_schema(), on_stage=stage,
                    contract_name="coalesced collaboration",
                    original_instruction=instruction, validation_feedback=issue,
                )
                repair_count += 1
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
            provider_call_count=1 + repair_count,
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
            coalesced_retry_count=result.retry_count + repair_count,
            coalesced_structured_repair_count=repair_count,
        )
        return candidate
