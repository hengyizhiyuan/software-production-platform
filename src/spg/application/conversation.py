"""Human-facing Conversation Intelligence over governed Watt semantics."""

from __future__ import annotations

from collections.abc import Callable

from spg.domain.conversation import (
    ConversationContext,
    ConversationContextProvider,
    ConversationContextMessage,
    ConversationProvider,
    ConversationResponseCandidate,
    StructuredCollaborationResult,
)
from spg.domain.interaction import (
    InteractionActor,
    InteractionInterpretationInput,
    InteractionSemanticCandidate,
)


def conversation_response_policy() -> str:
    """Shared expression policy; transport adapters do not invent their own style."""

    return (
        "Speak as a thoughtful product/design collaborator. WIC owns interpretation, "
        "hypotheses and proposals; Guided Design owns structure and progression. You "
        "own wording and turn-taking; you do not decide or modify Work, Design, Plan, Authority "
        "or other governed truth. Never invent user/product/file facts, capabilities, "
        "approval or completion. No tools or hidden memory; never reveal private reasoning.\n\n"
        "Lead with the useful answer or supplied judgment, without a standalone "
        "acknowledgement such as '可以。'. For DIRECT_QUESTION, give "
        "direct_answer first; a simple answer may be one sentence. Reuse known facts "
        "to explain what matters now, without recapping the conversation. Demonstrate "
        "understanding through the quality of the next move; do not paraphrase the "
        "Human's latest message unless a correction, genuine ambiguity, or costly "
        "constraint requires explicit confirmation. State "
        "necessary assumptions plainly, grounded in Human words. Keep object, audience "
        "and operator classifications in structured fields; express their practical "
        "consequence to the user.\n\n"
        "For REQUEST_RECOMMENDATION, present the supplied priority as a recommended "
        "choice, not a universal necessity; explain why the user's "
        "actual circumstances favor it, a material trade-off if any, and a concrete "
        "next action. A module catalogue or 'clarify requirements' is not advice. "
        "Use the supplied hypothesis to move a draft forward. Distinguish suggestions "
        "from settled requirements; preserve reasoned disagreement without flattery. "
        "Ask about at most one independent decision, only when it changes the next "
        "action. Zero questions is normal. Do not bundle unrelated decisions, "
        "restart discovery or repeat unanswered questions as a questionnaire.\n\n"
        "Match the Human's conversational altitude. For an open-ended early motive, reason "
        "from the actual object, its supplied context and what is already known. Contribute "
        "one useful frame before asking anything. Choose the next move from the unresolved "
        "concept that most changes this specific problem; do not apply a reusable discovery "
        "sequence, substitute nouns into stock framing, or ask again for an already supplied "
        "audience, object form or constraint. Avoid premature solution detail. When the Human "
        "is uncertain, supply expertise and a "
        "small set of meaningful directions instead of returning a question list. "
        "When the Human asks a concrete question, answer at that level instead of "
        "restarting discovery. ASK is one possible move, never the default.\n\n"
        "For CORRECTION or DISAGREEMENT, acknowledge once and advance from the "
        "corrected facts or direction, without defending or revisiting the old frame. "
        "Use CONTEXT_ADDITION for its practical implication. Answer detours directly; "
        "resume the main topic when the Human returns. Confirm choices without inventing "
        "authority. Admitted facts, constraints and requests remain separate from "
        "advisory candidates; a suggestion cannot amend admitted Work.\n\n"
        "Use warm, plain professional language, without stock praise, repeated apologies "
        "or a fixed template. Across unrelated objects, vary the conceptual focus as well as "
        "the wording; do not reuse the same question with nouns replaced. Every example, "
        "choice and field you mention must belong to the actual object; never borrow a detail "
        "from an adjacent domain. Do not narrate an inventory of known and unknown fields or "
        "state a default assumption unless it materially helps the current choice. Match "
        "response_language and requested detail. Keep useful "
        "rationale, examples and trade-offs; expand for REQUEST_DETAIL or "
        "detailed_explanation_requested. Each paragraph adds information. Hide schema "
        "IDs, enums, pipeline states and policy metadata."
    )

class ConversationInvariantViolation(RuntimeError):
    """Raised when Human-facing realization violates its bounded contract."""


class WattNativeConversationContextAssembler:
    """Bounded native context provider and future ECF replacement seam."""

    max_recent_messages = 8
    max_known_facts = 12
    max_constraints = 8
    max_requests = 8
    max_reality_references = 12

    def assemble(
        self,
        basis: InteractionInterpretationInput,
        collaboration: StructuredCollaborationResult,
    ) -> ConversationContext:
        human_records = tuple(
            record
            for record in basis.records
            if record.actor is InteractionActor.HUMAN
        )
        if not human_records:
            raise ConversationInvariantViolation(
                "Conversation context requires a persisted Human message"
            )
        recent = getattr(basis, "recent_conversation_messages", ())
        if recent:
            messages = list(recent[-self.max_recent_messages :])
            latest = ConversationContextMessage(
                actor="HUMAN", content=human_records[-1].content
            )
            # Legacy synchronous input writes a source record without a UX message.
            if messages[-1] != latest:
                messages = [*messages, latest][-self.max_recent_messages :]
        else:
            # Compatibility for callers whose persisted basis predates dialogue context.
            messages = [
                ConversationContextMessage(actor="HUMAN", content=record.content)
                for record in human_records[-self.max_recent_messages :]
            ]
            if basis.prior_assessment is not None:
                messages.insert(
                    max(len(messages) - 1, 0),
                    ConversationContextMessage(
                        actor="WATT",
                        content=basis.prior_assessment.natural_response,
                    ),
                )
                messages = messages[-self.max_recent_messages :]

        active = basis.active_work_context
        prior = basis.prior_assessment
        known_facts = self._unique(
            (
                *((prior.candidate_context if prior is not None else ())),
                *((active.work_revision.context_facts if active is not None else ())),
                *collaboration.known_relevant_facts,
            ),
            self.max_known_facts,
        )
        constraints = self._unique(
            (
                *((prior.candidate_constraints if prior is not None else ())),
                *((active.work_revision.constraints if active is not None else ())),
            ),
            self.max_constraints,
        )
        requests = self._unique(
            (
                *((prior.current_requests if prior is not None else ())),
                *((active.work_revision.requests if active is not None else ())),
            ),
            self.max_requests,
        )
        reality_refs = self._unique(
            (
                *(active.relevant_reality_references if active is not None else ()),
                *(
                    reference
                    for record in human_records
                    for reference in record.supporting_references
                ),
            ),
            self.max_reality_references,
        )
        return ConversationContext(
            source_basis_fingerprint=basis.basis_fingerprint,
            latest_human_message=human_records[-1].content,
            recent_relevant_messages=tuple(messages),
            known_relevant_facts=known_facts,
            governing_constraints=constraints,
            current_requests=requests,
            current_objective=(
                collaboration.current_objective
                or (
                    active.work_revision.desired_outcome
                    if active is not None
                    else prior.desired_outcome if prior is not None else None
                )
            ),
            current_collaboration_focus=collaboration.current_collaboration_focus,
            current_work_reference=(
                None if active is None else f"WORK:{active.work_revision.work_id}"
            ),
            current_plan_reference=(
                None
                if active is None or active.steering_plan_revision_id is None
                else f"STEERING_PLAN_REVISION:{active.steering_plan_revision_id}"
            ),
            current_attention=collaboration.unresolved_human_decision,
            relevant_reality_references=reality_refs,
            response_language=collaboration.response_language,
            detailed_explanation_requested=(
                collaboration.detailed_explanation_requested
            ),
        )

    @staticmethod
    def _unique(values: tuple[str, ...], limit: int) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))[
            -limit:
        ]


class ConversationResponseComposer:
    """Coordinates context and wording without taking ownership of source truth."""

    def __init__(
        self,
        provider: ConversationProvider,
        *,
        context_provider: ConversationContextProvider | None = None,
    ) -> None:
        self.provider = provider
        self.context_provider = (
            context_provider or WattNativeConversationContextAssembler()
        )

    def compose(
        self,
        basis: InteractionInterpretationInput,
        collaboration: StructuredCollaborationResult,
        *,
        on_response_delta: Callable[[str], None] | None = None,
        current_semantics: InteractionSemanticCandidate | None = None,
    ) -> ConversationResponseCandidate:
        context = self.context_provider.assemble(basis, collaboration)
        if current_semantics is not None:
            context = self._with_current_semantics(context, basis, current_semantics)
        candidate = (
            self.provider.respond_stream(
                context,
                collaboration,
                on_response_delta=on_response_delta,
            )
            if on_response_delta is not None
            else self.provider.respond(context, collaboration)
        )
        content = candidate.content.strip()
        if not content:
            raise ConversationInvariantViolation(
                "Conversation Provider returned an empty Human-facing response"
            )
        return candidate.model_copy(update={"content": content})

    @staticmethod
    def _with_current_semantics(
        context: ConversationContext,
        basis: InteractionInterpretationInput,
        semantic: InteractionSemanticCandidate,
    ) -> ConversationContext:
        """Use the latest advisory view while keeping admitted Work facts distinct.

        A correction may remove a candidate fact or constraint. Unioning prior
        candidates into this context would silently resurrect the superseded value.
        This response projection does not mutate either assessment or Work Reality,
        and keeps the replaceable context-provider protocol unchanged.
        """

        bounds = WattNativeConversationContextAssembler
        active = basis.active_work_context
        revision = None if active is None else active.work_revision
        return context.model_copy(
            update={
                "known_relevant_facts": bounds._unique(
                    (
                        *semantic.candidate_context,
                        *semantic.collaboration.known_relevant_facts,
                    ),
                    bounds.max_known_facts,
                ),
                "governed_work_facts": bounds._unique(
                    () if revision is None else revision.context_facts,
                    bounds.max_known_facts,
                ),
                "governing_constraints": bounds._unique(
                    () if revision is None else revision.constraints,
                    bounds.max_constraints,
                ),
                "candidate_constraints": bounds._unique(
                    semantic.candidate_constraints, bounds.max_constraints
                ),
                "current_requests": bounds._unique(
                    semantic.current_requests, bounds.max_requests
                ),
                "governed_work_requests": bounds._unique(
                    () if revision is None else revision.requests,
                    bounds.max_requests,
                ),
                "current_objective": (
                    semantic.collaboration.current_objective
                    or semantic.desired_outcome
                    or (None if revision is None else revision.desired_outcome)
                ),
            }
        )
