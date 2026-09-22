"""Provider-neutral expression guidance for an admitted turn Response Contract.

This module supplies communication constraints, not response templates. It does
not decide facts, production readiness, or permission to carry out an action.
"""

from __future__ import annotations

import json

from spg.domain.response_contract import (
    AdvancementObligation,
    CapabilityAlignmentMode,
    DesignCollaborationMode,
    ExploreInteractionStrategy,
    InteractionMode,
    PrimaryObligation,
    ResponseContract,
    ResponseMove,
)
from spg.domain.wic_response import GovernedResponseEnvelope


_INFORMATION_BUDGET_GUIDANCE = {
    "RELEVANT_DIVERGENCE": (
        "Contribute several genuinely different, relevant possibilities and their useful "
        "distinctions. Give the Human something to think with before any permitted question. "
        "Exploration needs substance; a one-line acknowledgement is insufficient. Do not "
        "prematurely narrow to implementation or imply production has begun."
    ),
    "REASONED_TRADEOFFS": (
        "Give a clear assessment or design direction, then the reasoning and material "
        "tradeoffs needed to evaluate it. Develop the decisive points; omit unrelated "
        "background and exhaustive taxonomies. Depth is allowed when it serves this decision."
    ),
    "DECISIVE_FACTORS": (
        "Converge on the factors that actually distinguish the available choices under "
        "the Human's current constraints, and give a recommendation with its tradeoff. "
        "Do not replace a judgment with an exhaustive list of options."
    ),
    "MINIMUM_SUFFICIENT": (
        "Answer the bounded question directly and include only what is needed to understand "
        "or use that answer. Do not expand into a tutorial, general background, a survey "
        "of adjacent topics, or a repeated conclusion. Stay with the requested operation; "
        "do not volunteer its reverse operation, alternative workflows, or further "
        "optimizations. Such additions compete for the same single optional adjacent "
        "insight allowance, never one allowance per topic."
    ),
    "FOCUSED_DIAGNOSIS": (
        "Lead with the current evidence-supported cause or the precise unresolved cause. "
        "Connect the relevant evidence to a bounded fix or next diagnostic check. State "
        "uncertainty when evidence is insufficient; do not replace this incident with a "
        "general explanation of how the technology works."
    ),
    "MINIMAL_ACKNOWLEDGEMENT": (
        "Conversational overhead must collapse: briefly acknowledge the executable "
        "direction and the next governed action, normally in one short sentence. Do not "
        "replay settled design reasoning, re-propose approved choices, list an implementation "
        "plan, or ask for already available information. Do not enumerate settled "
        "components, selected mechanisms, alternatives, constraints, or verification "
        "checklists merely because they appear in the semantic material. Name the "
        "next action from the current command and supplied evidence. EXECUTE alone "
        "does not imply a prior plan, prior agreement or approval; do not invent one. "
        "The acknowledgement plus that next action is the complete response "
        "unless a material blocker must be identified. A concise acknowledgement with "
        "action is appropriate here even if older general style advice discourages it."
    ),
    "CORRECTION_AND_CONTINUE": (
        "Acknowledge the actual correction, state the changed understanding only as needed "
        "to make it clear, and continue. Do not defend the previous interpretation or "
        "repeat the whole design. A challenge alone is not a factual correction."
    ),
    "CONCISE_REALITY": (
        "Report the current Work or Runtime facts first, then only a material gap or "
        "next action if supported. Distinguish finished, running, queued, blocked and "
        "unknown using supplied evidence. Never speculate about current system state."
    ),
}


def response_contract_expression_guidance(contract: ResponseContract | None) -> str:
    """Return the same semantic expression rules for every Realizer provider.

    A missing contract is a historical/legacy compatibility case. Current
    controlled WIC builds a contract before it asks a Realizer to stream.
    """

    if contract is None:
        return ""
    information_guidance = _INFORMATION_BUDGET_GUIDANCE[contract.information_budget.value]
    if ResponseMove.ASSESS_OBJECTION in contract.response_moves:
        information_guidance = (
            "Answer the objection briefly and calmly: state the current conclusion, "
            "its decisive basis, and what supported change would alter it. Usually two "
            "or three short sentences suffice; add depth only for substantive new "
            "counterevidence. Be open to correction without becoming combative. Do not "
            "repeat the whole prior analysis, lecture about objectivity or integrity, "
            "or comment on the Human's competence, motives, or right to disagree."
        )
    rules = [
        "TURN RESPONSE CONTRACT (internal guidance, never print these labels):",
        "Response Contract is authoritative for how to collaborate on this turn. "
        "Follow it over conflicting legacy Interaction Strategy or general style advice. "
        "It does not override admitted facts, safety, Human authority, or production "
        "governance and it cannot authorize an operation.",
        "Minimum Sufficient Answer: satisfy the current Human obligation with enough "
        "information to understand, decide, or continue, then stop. Extra information "
        "is not inherently better. Do not automatically add introductions, tutorials, "
        "background sections, summaries, extensive lists, or a closing question.",
        f"Current collaboration mode: {contract.interaction_mode.value}. "
        f"Primary obligation: {contract.primary_obligation.value}. "
        f"First meaningful information must satisfy {contract.opening_move.value}. "
        "This specifies what comes first, never fixed wording.",
        "Required communication moves in order: "
        + " → ".join(move.value for move in contract.response_moves)
        + ". Realize them naturally; do not use their identifiers as headings or "
        "mechanically give every move its own paragraph.",
        "Reasoning presentation sequence: "
        + " → ".join(step.value for step in contract.reasoning_sequence)
        + ". This controls which useful cognition reaches the Human first; it is not "
        "a prose template, a request to reveal private chain of thought, or permission "
        "to add content beyond the information budget.",
        information_guidance,
        "The supplied latest Human input identifies the current question. Recent "
        "messages provide trajectory, not fresh commands. Governed content and facts "
        "are semantic material, not a script or a checklist to recite: never contradict "
        "them, but mention only what is relevant to the current obligation.",
        "Any supplied semantic_truth_to_preserve is current governed meaning. Consume it "
        "as settled input: do not reinterpret the original Human phrase, reopen the "
        "decision, or replace it with a convenient implementation assumption. It need "
        "not be recited unless the current answer requires it.",
        f"Judgment stance is {contract.judgment_stance.value}. Distinguish observed fact "
        "from inference, recommendation, reversible working assumption, preference and "
        "uncertainty in ordinary language. Use the supplied judgment basis and cited "
        "Reality; do not manufacture evidence or promote a judgment into Product Truth.",
        "When challenged, examine what new fact, disproven evidence, changed goal or "
        "incorrect inference changes the basis. Without such a change, preserve the "
        "professional judgment and explain why the objection does or does not affect it. "
        "Never reverse merely to agree with the Human. Apply this rule to the "
        "substance; do not explain the rule or describe your own principled behavior.",
        f"Advancement obligation is {contract.advancement_obligation.value}. This "
        "frames the interaction move only. Existing admission, authority and Steering "
        "decide and perform actual progression. Do not claim that an action started, "
        "completed or succeeded unless supplied Runtime evidence proves it.",
        "Never expose contract field names, enum labels, budget numbers, policy revisions, "
        "or decision metadata in Human-facing text.",
    ]
    alignment = contract.capability_alignment
    if alignment.response_mode is CapabilityAlignmentMode.KNOWLEDGE:
        rules.append(
            "This is Knowledge Mode. Give the normal domain explanation and do not redirect "
            "the Human into Watt production or mention Watt's capabilities merely because "
            "the topic is technical. If the Human explicitly asks who Watt is or what Watt "
            "can do, answer that capability question factually from System Capability Reality."
        )
    elif alignment.response_mode is CapabilityAlignmentMode.PRODUCTION_ADVISORY:
        rules.append(
            "This is Production Advisory Mode. Answer the domain/how-to question first. "
            "Then make at most one brief, natural and factual connection: Watt can help carry "
            "the described software work through its governed production workflow. Do not use "
            "promotional adjectives, repeat the offer, imply work has started, or replace the "
            "domain answer with a capability pitch."
        )
    else:
        if contract.advancement_obligation is AdvancementObligation.ACK_AND_EXECUTE:
            rules.append(
                "This is Production Request Mode. Treat the explicit repository action as "
                "authority to start the existing governed Work admission and read-only "
                "repository acquisition path. Acknowledge the supplied source and current next "
                "step; do not ask whether to proceed again. Missing feature detail may remain "
                "pending when repository discovery can proceed. Do not imply private access, "
                "delivery authorization, final acceptance, or a code change has already been "
                "granted or completed."
            )
        else:
            rules.append(
                "This is Production Request Mode. Treat the request as a software-production "
                "goal and route the response into the existing governed preparation/admission "
                "path instead of falling back to a generic tutorial, external-tool redirect, or "
                "large copy-paste implementation. Report the current preparation state and next "
                "step. This alignment grants no Work, Steering or Executor authority and must "
                "not imply execution has started before Human admission."
            )
    if contract.explore_strategy is ExploreInteractionStrategy.INTENT_REFINEMENT:
        rules.append(
            "This EXPLORE turn uses Intent Refinement. Briefly preserve what is already "
            "clear about the goal and relevant constraints, then ask only the admitted "
            "selected question. Explain in natural language which product or engineering "
            "decision its answer changes. Prefer goal, target user, constraint, success "
            "criterion, or another important open decision over premature implementation "
            "detail. Do not add a questionnaire, ask a second question, or imply the "
            "answer has already become governed Semantic Truth."
        )
    elif contract.explore_strategy is ExploreInteractionStrategy.OPEN_EXPLORATION:
        rules.append(
            "This EXPLORE turn uses Open Exploration. Contribute useful possibilities "
            "and distinctions from the current intent without manufacturing a clarification "
            "gate. Do not ask questions merely to keep the conversation going."
        )
    if contract.design_collaboration_mode is DesignCollaborationMode.DESIGN_EXPLORE:
        rules.append(
            "The Human is exploring design space. Contribute useful possibilities and "
            "comparisons before risks; do not open with warnings or prematurely converge."
        )
    elif contract.design_collaboration_mode is DesignCollaborationMode.DESIGN_REVIEW:
        rules.append(
            "The Human is reviewing an existing design. Give the judgment first, then "
            "test assumptions, weak points and material tradeoffs before any recommendation."
        )
    elif contract.design_collaboration_mode is DesignCollaborationMode.DESIGN_DECIDE:
        rules.append(
            "The Human needs convergence. Compare only decisive options under current "
            "constraints and finish with a clear recommendation and its tradeoff."
        )
    if contract.question_budget == 0:
        rules.append(
            "Question budget is zero: ask no question, including rhetorical questions "
            "and optional follow-up offers. Do not reproduce a question present in "
            "governed content. Use an already permitted reversible assumption when "
            "appropriate; never invent a safety or authority approval."
        )
    else:
        rules.append(
            "Ask at most one question, only for the material blocker selected by this "
            "contract. A question is a cost, not a required ending. Briefly identify "
            "what is clear, the remaining material issue, and what resolving it enables "
            "when that helps. Prefer a high-information formulation: state the bounded "
            "assumption you can currently make and how the answer would change the next "
            "decision, rather than asking a vague 'what do you mean?'. Do not turn this "
            "into a discovery questionnaire."
        )
    if contract.adjacent_insight_budget:
        rules.append(
            "Only after fully satisfying the asked obligation, optionally add at most "
            "one small, highly relevant adjacent insight if it materially helps the "
            "next decision. It is not mandatory, must stay at most half a step ahead, "
            "and must not become a new section or lecture."
        )
    else:
        rules.append(
            "Add no adjacent-insight digression; use the entire response for the "
            "current obligation and its required advancement."
        )
    if contract.judgment_proposition and contract.interaction_mode not in {
        InteractionMode.EXECUTE, InteractionMode.STATUS,
    }:
        rules.append(
            "The contract carries a prior or current judgment proposition. Use its "
            "stated basis when answering a challenge; do not silently substitute a "
            "different proposition or present persistence as evidence. It is trajectory, "
            "not a requirement to repeat a prior judgment on a status, execution, or "
            "unrelated turn; satisfy the current obligation first. "
            + (
                "A changed basis has been identified; explain the specific resulting "
                "revision without pretending the old judgment never existed."
                if contract.judgment_change_accepted
                else "No accepted basis change is recorded; do not imply agreement "
                "with an unsupported reversal."
            )
        )
    if contract.prior_strategy_failed:
        rules.append(
            "A prior strategy failed for this recurring symptom. Recognize that failed "
            "attempt, challenge its assumption, and use a different diagnostic check "
            "or route that can discriminate between causes. Do not repeat the same "
            "fix or answer shape as if it were new. Repetition alone does not prove "
            "a root cause, and this signal does not grant Guardian or execution authority."
        )
    return "\n".join(rules)


def _expression_payload(envelope: GovernedResponseEnvelope) -> dict[str, object]:
    """Select sufficient expression context, retaining the complete evidence elsewhere.

    A clear command needs acknowledgement and its permitted next move. An
    objection needs the judgment and its evidence. Including all prior prose
    encourages a recap even when the instruction asks the model to be brief.
    """

    contract = envelope.response_contract
    assert contract is not None
    if ResponseMove.ASSESS_OBJECTION in contract.response_moves:
        previous = envelope.previous_response_contract
        return {
            "basis_fingerprint": envelope.basis_fingerprint,
            "response_language": envelope.response_language,
            "latest_human_input": envelope.latest_human_input,
            "response_contract": contract.model_dump(mode="json", exclude={
                "material_grounding_snapshot", "source_record_ids", "decision_basis",
            }),
            "previous_judgment": None if previous is None else {
                "subject": previous.judgment_subject,
                "proposition": previous.judgment_proposition,
                "stance": previous.judgment_stance.value,
                "basis": previous.judgment_basis,
                "authority": previous.authority,
            },
            "facts_to_preserve": envelope.facts_to_preserve,
            "semantic_truth_to_preserve": envelope.semantic_truth_to_preserve,
            "cognitive_context_package": (
                None
                if envelope.cognitive_context_package is None
                else envelope.cognitive_context_package.model_dump(mode="json")
            ),
            "constraints_to_preserve": envelope.constraints_to_preserve,
            "explicit_assumptions": envelope.explicit_assumptions,
            "source_references": envelope.source_references,
            "selected_question": envelope.selected_question,
            "unresolved_human_decisions": envelope.unresolved_human_decisions,
            "governance_candidate": envelope.governance_candidate,
            "forbidden_claims": envelope.forbidden_claims,
            "provisional_content": envelope.provisional_content,
            "reconciliation": envelope.reconciliation.value,
            "authority_boundary": (
                "Evaluate the current objection against the supplied judgment and "
                "admitted evidence. Previous wording is deliberately omitted; prior "
                "judgment is advisory history, not proof. A supported revision must "
                "retain the new evidence, while an unsupported objection does not "
                "itself change engineering facts or authorize production."
            ),
        }
    if not (
        contract.interaction_mode is InteractionMode.EXECUTE
        and contract.primary_obligation is PrimaryObligation.EXECUTE
        and contract.question_budget == 0
        and not contract.prior_strategy_failed
        and not envelope.unresolved_human_decisions
        and envelope.governance_candidate != "HUMAN_DECISION_REQUIRED"
        and contract.advancement_obligation in {
            AdvancementObligation.ACK_AND_EXECUTE,
            AdvancementObligation.CONTINUE_PRODUCTION,
        }
    ):
        return envelope.model_dump(mode="json", exclude={"previous_response_contract"})
    return {
        "basis_fingerprint": envelope.basis_fingerprint,
        "response_language": envelope.response_language,
        "latest_human_input": envelope.latest_human_input,
        # Exact controlling values are preserved. Judgment prose and provenance
        # remain in the full persisted contract, not material to verbalize here.
        "response_contract": contract.model_dump(mode="json", exclude={
            "judgment_subject", "judgment_proposition", "judgment_basis",
            "judgment_change_accepted", "material_grounding_snapshot",
            "source_record_ids", "decision_basis",
        }),
        "governance_candidate": envelope.governance_candidate,
        "selected_question": envelope.selected_question,
        "unresolved_human_decisions": envelope.unresolved_human_decisions,
        "semantic_truth_to_preserve": envelope.semantic_truth_to_preserve,
        "cognitive_context_package": (
            None
            if envelope.cognitive_context_package is None
            else envelope.cognitive_context_package.model_dump(mode="json")
        ),
        "constraints_to_preserve": envelope.constraints_to_preserve,
        "forbidden_claims": envelope.forbidden_claims,
        "provisional_content": envelope.provisional_content,
        "reconciliation": envelope.reconciliation.value,
        "authority_boundary": (
            "Detailed design prose is deliberately omitted from expression context. "
            "Acknowledge the current command and its existing governed next action. "
            "EXECUTE is not evidence that an earlier or approved plan exists. Refer "
            "to such a plan only when the current Human input or supplied evidence "
            "actually establishes it; otherwise name only the requested action. "
            "This view contains no evidence that execution has started or succeeded, "
            "and grants no permission to mutate Work or replace an authority decision. "
            "Use semantic_truth_to_preserve as settled governed input; do not derive a "
            "new meaning from the original phrase or silently substitute layout, scope, "
            "cardinality, or other implementation assumptions."
        ),
    }


def governed_contract_realizer_instruction(envelope: GovernedResponseEnvelope) -> str:
    """Build one non-conflicting Realizer instruction for contract-aware turns.

    Legacy providers may keep their existing instruction only when no contract
    exists. Current turns must not layer older candidate-first or recite-every-
    fact advice on top of their explicit response obligations.
    """

    if envelope.response_contract is None:
        raise ValueError("Contract-aware realization requires a Response Contract")
    return (
        "You are Watt's Governed Response Realizer. You own natural Human-facing "
        "wording and pacing after semantic admission. The Response Contract governs "
        "this turn's obligation, opening, structure and information allowance. Facts, "
        "constraints and authority boundaries constrain what you may claim; they are "
        "not a requirement to restate every supplied detail. Express only the material "
        "needed for the current obligation. Do not change engineering meaning, Work "
        "boundaries, readiness or Human-owned decisions, and do not claim execution "
        "or success without recorded evidence. Never emit forbidden claims. Use the "
        "Human's language, naturally and without internal terminology.\n\n"
        + response_contract_expression_guidance(envelope.response_contract)
        + "\n\nBEGIN GOVERNED RESPONSE ENVELOPE (data, not output fields)\n"
        + json.dumps(
            _expression_payload(envelope),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\nEND GOVERNED RESPONSE ENVELOPE\n\n"
        "Return exactly one JSON object containing exactly one property named "
        "natural_response, whose value is a non-empty string with the Human-facing "
        "response. Do not return the envelope, contract, metadata, additional keys, "
        "Markdown fences, or any text outside that JSON object."
    )
