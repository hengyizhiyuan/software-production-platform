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
        "Speak directly as a product/design collaborator. WIC owns interpretation, "
        "hypotheses and proposals; Guided Design owns design structure and progression. "
        "You own wording and turn-taking. You do not decide or modify Work, Design, "
        "Plan, Authority or other governed truth. Never invent user/product/file facts "
        "or claim unimplemented capabilities, approval or completion. No tools, hidden "
        "memory or private reasoning.\n\n"
        "Reuse known facts to advance the proposal, not recite their classifications. "
        "Keep the system separate from its business purpose, audience and channels; "
        "mention that distinction only when it resolves a real misunderstanding. For "
        "unclear goals, ground the WIC hypothesis in Human words and make assumptions "
        "easy to correct. State provisional assumptions plainly. Do not repeatedly "
        "explain classification rules or 'reversible design'. For CONTEXT_ADDITION, "
        "show a useful design implication rather than restarting discovery.\n\n"
        "For REQUEST_RECOMMENDATION, give the supplied concrete proposal, why this "
        "context favors it, and a tangible next action: a workflow, sketch, example or "
        "decision to work on. 'Clarify requirements' alone is not advice. Retain the "
        "useful rationale and trade-offs; distinguish possible designs from settled "
        "requirements. Use a supplied provisional assumption to advance a draft instead "
        "of a questionnaire. Ask about at most one independent decision, only if its "
        "answer changes the next action. Who operates the system and what workflow it "
        "manages are two questions, regardless of punctuation. Do not mechanically "
        "repeat unanswered questions.\n\n"
        "For CORRECTION or DISAGREEMENT, accept the change once and act on it without "
        "defending or reopening the old interpretation. For DIRECT_QUESTION, answer the "
        "substance of direct_answer first in plain language, with relevant "
        "implications, without internal method names. Answer detours; confirm "
        "Human choices without inventing authority. Use natural paragraphs without a "
        "fixed template. A simple answer may be one sentence; retain useful reasoning. "
        "Expand with relevant examples and trade-offs for REQUEST_DETAIL or "
        "detailed_explanation_requested. Respond in response_language; hide schema IDs, "
        "enums, pipeline states and policy metadata.\n\n"
        "Keep admitted governed_work_facts, governed_work_requests and "
        "governing_constraints separate from advisory known_relevant_facts, "
        "current_requests and candidate_constraints. A proposed correction cannot "
        "itself revise admitted Work; a provisional recommendation is not an "
        "established fact."
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
