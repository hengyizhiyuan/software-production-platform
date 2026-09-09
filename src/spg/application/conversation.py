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
from spg.domain.interaction import InteractionActor, InteractionInterpretationInput


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
    ) -> ConversationResponseCandidate:
        context = self.context_provider.assemble(basis, collaboration)
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
