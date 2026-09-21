"""Response decisions consume admitted semantics; no transcript-specific routing."""

from datetime import UTC, datetime
import hashlib
from uuid import UUID

import pytest
from pydantic import ValidationError

from spg.application.response_contract import build_response_contract
from spg.domain.conversation import ConversationTurnIntent as Intent
from spg.domain.engineering_semantics import (
    EngineeringSemanticFact,
    SemanticEpistemicStatus,
    SemanticFactAuthority,
    SemanticFactProvenance,
    SemanticRelation,
    SemanticRoleOrigin,
    semantic_fact_statement,
)
from spg.domain.interaction import (
    InteractionActor,
    InteractionAssessment,
    InteractionRecord,
    WorkAdmissionReadiness,
    WorkAdmissionReadinessStatus,
)
from spg.domain.response_contract import (
    AdvancementObligation as Advance,
    InformationBudget as Budget,
    InteractionMode as Mode,
    JudgmentStance,
    OpeningMove as Opening,
    PrimaryObligation as Obligation,
    ResponseContract,
    ResponseIntent,
    ResponseMove as Move,
)
from spg.domain.wic_intelligence import (
    GovernanceCandidateKind,
    InferenceDisposition,
    ProgressiveSemanticStructure,
    QuestionDisposition,
    QuestionEvaluation,
    SemanticCategory,
    SemanticDelta,
    SemanticDeltaOperation,
)


def _assessment(intent=Intent.EXPLORE, *, questions=(), selected=None, facts=(), deltas=(), governance=GovernanceCandidateKind.NO_GOVERNED_CHANGE, **updates):
    semantics = ProgressiveSemanticStructure(
        turn_intent=intent,
        basis_fingerprint="a" * 64,
        source_record_ids=(UUID(int=1),),
        reception_meanings=(),
        working_facts=facts,
        deltas=deltas,
        pattern_signals=(),
        inference_disposition=InferenceDisposition.NO_INFERENCE,
        questions=questions,
        selected_question=selected,
        governance_candidate=governance,
        readiness=(),
    )
    values = dict(
        id=UUID(int=2), interaction_id=UUID(int=3),
        basis_fingerprint="a" * 64, basis_last_sequence=1,
        candidate_context=facts, candidate_constraints=(), current_requests=(),
        unresolved_material_questions=(), meanings=(), natural_response="Admitted response",
        readiness=WorkAdmissionReadiness(
            status=WorkAdmissionReadinessStatus.READY, profile="test", profile_version="1",
            satisfied_requirements=("intent",), missing_information=(),
            unresolved_material_questions=(), reasons=("Executable context",),
            basis_fingerprint="a" * 64,
        ),
        progressive_semantics=semantics, provider_identity="test", schema_version="test",
        created_at=datetime(2026, 9, 21, tzinfo=UTC),
    )
    values.update(updates)
    return InteractionAssessment(**values)


def _intent(mode, **values):
    return ResponseIntent(interaction_mode=mode, rationale="Semantic purpose of this Human turn", **values)


def _record(text, *, identity=1, sequence=1, actor=InteractionActor.HUMAN):
    return InteractionRecord(
        id=UUID(int=identity), interaction_id=UUID(int=3), sequence=sequence,
        actor=actor, source="test", content=text,
        content_fingerprint=hashlib.sha256(text.encode()).hexdigest(),
        created_at=datetime(2026, 9, 21, tzinfo=UTC),
    )


def _question(**updates):
    values = dict(
        question="Which account owns authorization for the irreversible operation?",
        affected_dimensions=("AUTHORITY",), answer_already_available=False,
        safe_reversible_assumption_available=False, watt_authorized_to_choose=False,
        blocks_next_governed_step=True, cognitive_cost="LOW", decision_value=100,
        disposition=QuestionDisposition.ASK_HUMAN_NOW, rationale="Requires Human authority",
    )
    values.update(updates)
    return QuestionEvaluation(**values)


@pytest.mark.parametrize("case,mode,intent,obligation,opening,budget", [
    ("A", Mode.DIAGNOSE, Intent.DIRECT_QUESTION, Obligation.DIAGNOSE, Opening.CAUSE_FIRST, Budget.FOCUSED_DIAGNOSIS),
    ("B", Mode.ANSWER, Intent.DIRECT_QUESTION, Obligation.ANSWER, Opening.ANSWER_FIRST, Budget.MINIMUM_SUFFICIENT),
    ("C", Mode.ANALYZE, Intent.FEEDBACK, Obligation.ASSESS, Opening.JUDGMENT_FIRST, Budget.REASONED_TRADEOFFS),
    ("D", Mode.DECIDE, Intent.COMPARE, Obligation.COMPARE, Opening.JUDGMENT_FIRST, Budget.DECISIVE_FACTORS),
    ("E", Mode.STATUS, Intent.DIRECT_QUESTION, Obligation.REPORT_REALITY, Opening.REALITY_FIRST, Budget.CONCISE_REALITY),
    ("F", Mode.EXECUTE, Intent.CONTINUE_CURRENT_WORK, Obligation.EXECUTE, Opening.ACK_AND_EXECUTE, Budget.MINIMAL_ACKNOWLEDGEMENT),
    ("G", Mode.CORRECT, Intent.DISAGREEMENT, Obligation.ASSESS, Opening.JUDGMENT_FIRST, Budget.DECISIVE_FACTORS),
    ("H", Mode.DIAGNOSE, Intent.FEEDBACK, Obligation.DIAGNOSE, Opening.CAUSE_FIRST, Budget.FOCUSED_DIAGNOSIS),
    ("I", Mode.EXPLORE, Intent.EXPLORE, Obligation.PROPOSE, Opening.CONTRIBUTION_FIRST, Budget.RELEVANT_DIVERGENCE),
    ("J", Mode.EXECUTE, Intent.ACTION_REQUEST, Obligation.EXECUTE, Opening.ACK_AND_EXECUTE, Budget.MINIMAL_ACKNOWLEDGEMENT),
    ("K", Mode.DIAGNOSE, Intent.MODIFY, Obligation.DIAGNOSE, Opening.CAUSE_FIRST, Budget.FOCUSED_DIAGNOSIS),
])
def test_semantic_mode_matrix(case, mode, intent, obligation, opening, budget):
    contract = build_response_contract(_assessment(intent), interpretation=_intent(mode))
    assert contract.interaction_mode == (Mode.ANALYZE if case == "G" else mode)
    assert contract.primary_obligation is obligation
    assert contract.opening_move is opening
    assert contract.information_budget is budget
    assert contract.question_budget == 0
    assert contract.selected_question is None
    assert contract.authority == "ADVISORY_ONLY"


def test_same_login_topic_has_distinct_explore_design_execute_obligations():
    assessment = _assessment(facts=("The current topic is login functionality.",))
    contracts = [build_response_contract(assessment, interpretation=_intent(mode)) for mode in (Mode.EXPLORE, Mode.DESIGN, Mode.EXECUTE)]
    assert len({contract.response_moves for contract in contracts}) == 3
    assert len({contract.information_budget for contract in contracts}) == 3
    assert contracts[0].advancement_obligation is Advance.ANSWER_ONLY
    assert contracts[1].advancement_obligation is Advance.PROPOSE_AND_WAIT
    assert contracts[2].advancement_obligation is Advance.ACK_AND_EXECUTE
    assert contracts[2].response_moves == (Move.ACKNOWLEDGE, Move.PROCEED)


def test_turn_wording_does_not_control_semantic_mode_or_budget():
    left = build_response_contract(_assessment(current_requests=("Just implement the login option.",)), interpretation=_intent(Mode.EXECUTE))
    right = build_response_contract(_assessment(current_requests=("Proceed with the agreed authentication approach.",)), interpretation=_intent(Mode.EXECUTE))
    assert left == right


def test_builder_does_not_promote_response_advice_into_semantic_or_work_truth():
    assessment = _assessment(facts=("The accepted weekday count is five.",))
    before = assessment.model_dump_json()
    contract = build_response_contract(assessment, interpretation=_intent(Mode.ANALYZE, judgment_stance=JudgmentStance.RECOMMENDATION, judgment_proposition="Prefer a compact grid."))
    assert assessment.model_dump_json() == before
    assert "Prefer a compact grid" not in before
    assert contract.authority == "ADVISORY_ONLY"
    with pytest.raises(ValidationError):
        ResponseContract.model_validate({**contract.model_dump(), "authority": "GOVERNED_REALITY"})
    with pytest.raises(ValidationError):
        contract.question_budget = 1


def test_only_an_admitted_material_blocker_can_spend_one_question():
    question = _question()
    contract = build_response_contract(
        _assessment(questions=(question,), selected=question.question, governance=GovernanceCandidateKind.HUMAN_DECISION_REQUIRED),
        interpretation=_intent(Mode.EXECUTE, executable_context=True),
    )
    assert contract.question_budget == 1
    assert contract.selected_question == question.question
    assert contract.primary_obligation is Obligation.CLARIFY_BLOCKER
    assert contract.opening_move is Opening.CLARIFICATION_FIRST
    assert contract.advancement_obligation is Advance.PAUSE_FOR_HUMAN_AUTHORITY
    assert Move.PROCEED not in contract.response_moves


@pytest.mark.parametrize("update", [
    {"answer_already_available": True},
    {"safe_reversible_assumption_available": True},
    {"watt_authorized_to_choose": True},
    {"blocks_next_governed_step": False},
    {"affected_dimensions": ("OPTIONAL_STYLE",)},
])
def test_optional_or_resolved_unknown_does_not_trigger_a_question(update):
    question = _question(**update)
    contract = build_response_contract(_assessment(questions=(question,), selected=question.question), interpretation=_intent(Mode.EXECUTE))
    assert contract.question_budget == 0
    assert contract.advancement_obligation is Advance.ACK_AND_EXECUTE


@pytest.mark.parametrize("mode", [Mode.STATUS, Mode.ANSWER])
def test_read_only_question_is_not_turned_into_work_admission_interrogation(mode):
    question = _question()
    contract = build_response_contract(
        _assessment(questions=(question,), selected=question.question, governance=GovernanceCandidateKind.HUMAN_DECISION_REQUIRED),
        interpretation=_intent(mode),
    )
    assert contract.question_budget == 0
    assert contract.advancement_obligation is Advance.ANSWER_ONLY


def test_existing_active_production_can_be_framed_but_never_mutated():
    assessment = _assessment(basis_active_runtime_binding_id=UUID(int=77))
    before = assessment.model_dump_json()
    contract = build_response_contract(assessment, interpretation=_intent(Mode.EXECUTE))
    assert contract.advancement_obligation is Advance.CONTINUE_PRODUCTION
    assert contract.information_budget is Budget.MINIMAL_ACKNOWLEDGEMENT
    assert assessment.model_dump_json() == before


def test_unready_execution_uses_governed_preparation_without_claiming_execution():
    assessment = _assessment()
    assessment = assessment.model_copy(update={"readiness": assessment.readiness.model_copy(update={"status": WorkAdmissionReadinessStatus.NOT_READY})})
    contract = build_response_contract(assessment, interpretation=_intent(Mode.EXECUTE))
    assert contract.advancement_obligation is Advance.PROPOSE_AND_WAIT
    assert Move.PROCEED not in contract.response_moves
    assert contract.information_budget is Budget.MINIMAL_ACKNOWLEDGEMENT


def _professional_judgment(assessment=None):
    return build_response_contract(
        assessment or _assessment(facts=("The team has two engineers.", "Low operating cost is required.")),
        interpretation=_intent(Mode.ANALYZE, judgment_subject="service topology", judgment_stance=JudgmentStance.RECOMMENDATION, judgment_proposition="Keep a modular monolith.", judgment_basis=("The team has two engineers.",)),
    )


@pytest.mark.parametrize("basis,reason", [
    ((f"record:{UUID(int=1)}",), "The Human disagreed."),
    (("Invented benchmark proves the opposite.",), "New evidence supposedly exists."),
    (("Low operating cost is required.",), "An already available but previously uncited fact was rediscovered."),
])
def test_unsupported_or_stale_basis_cannot_flip_judgment(basis, reason):
    assessment = _assessment(Intent.DISAGREEMENT, facts=("The team has two engineers.", "Low operating cost is required."))
    prior = _professional_judgment(assessment)
    result = build_response_contract(assessment, previous_contract=prior, interpretation=_intent(
        Mode.CORRECT, judgment_subject="service topology", judgment_stance=JudgmentStance.RECOMMENDATION,
        judgment_proposition="Split into microservices.", judgment_basis=basis,
        judgment_basis_changed=True, judgment_change_reason=reason,
    ))
    assert result.judgment_proposition == prior.judgment_proposition
    assert not result.judgment_change_accepted
    assert result.interaction_mode is Mode.ANALYZE
    assert result.opening_move is Opening.JUDGMENT_FIRST
    assert Move.ASSESS_OBJECTION in result.response_moves


def test_material_goal_change_can_revise_a_judgment_with_cited_basis():
    prior = _professional_judgment()
    new_goal = "Independent release ownership is now the primary objective."
    delta = SemanticDelta(
        id=UUID(int=5), category=SemanticCategory.DESIRED_OUTCOME, operation=SemanticDeltaOperation.REVISED,
        value=new_goal, prior_value="Keep operating costs minimal.", source_record_ids=(UUID(int=1),),
        basis_fingerprint="a" * 64, confidence=1, rationale="The Human changed the primary goal.",
    )
    result = build_response_contract(
        _assessment(Intent.DISAGREEMENT, deltas=(delta,)), previous_contract=prior,
        source_records=(_record(new_goal),),
        interpretation=_intent(Mode.ANALYZE, judgment_subject="service topology", judgment_stance=JudgmentStance.RECOMMENDATION,
            judgment_proposition="Separate the independently owned service.", judgment_basis=(f"semantic_delta:{delta.id}",),
            judgment_basis_changed=True, judgment_change_reason="Independent releases now matter more than operating cost."),
    )
    assert result.judgment_change_accepted
    assert result.judgment_proposition == "Separate the independently owned service."
    assert result.information_budget is Budget.REASONED_TRADEOFFS


def test_judgment_survives_status_with_narrow_context_without_losing_evidence_inventory():
    prior = _professional_judgment()
    interleaved = build_response_contract(_assessment(), interpretation=_intent(Mode.STATUS), previous_contract=prior)
    assert interleaved.judgment_proposition == prior.judgment_proposition
    assert interleaved.material_grounding_snapshot == prior.material_grounding_snapshot
    challenge = build_response_contract(_assessment(Intent.DISAGREEMENT, facts=("Low operating cost is required.",)), previous_contract=interleaved, interpretation=_intent(
        Mode.ANALYZE, judgment_subject="service topology", judgment_proposition="Split into microservices.",
        judgment_basis=("Low operating cost is required.",), judgment_basis_changed=True, judgment_change_reason="Same old evidence.",
    ))
    assert challenge.judgment_proposition == prior.judgment_proposition
    assert not challenge.judgment_change_accepted


def test_new_topic_can_have_its_own_judgment_without_erasing_prior_truth():
    prior = _professional_judgment()
    result = build_response_contract(_assessment(), previous_contract=prior, interpretation=_intent(
        Mode.ANSWER, judgment_subject="git branch checkout", judgment_stance=JudgmentStance.RECOMMENDATION,
        judgment_proposition="Use a single-branch clone for this need.",
    ))
    assert result.judgment_proposition == "Use a single-branch clone for this need."
    assert not result.judgment_change_accepted


def test_old_semantic_fact_cannot_become_new_evidence_via_a_different_alias():
    fact = EngineeringSemanticFact(
        id=UUID(int=31), subject="team.engineers", relation=SemanticRelation.CARDINALITY,
        value=2, authority=SemanticFactAuthority.HUMAN_EXPLICIT, epistemic_status=SemanticEpistemicStatus.CONFIRMED,
        provenance=SemanticFactProvenance(source_record_ids=(UUID(int=1),), source_text="two engineers", role_origin=SemanticRoleOrigin.EXPLICIT),
    )
    assessment = _assessment(Intent.DISAGREEMENT, engineering_semantic_facts=(fact,))
    prior = _professional_judgment(assessment)
    result = build_response_contract(assessment, previous_contract=prior, interpretation=_intent(
        Mode.ANALYZE, judgment_subject="service topology", judgment_proposition="Split into microservices.",
        judgment_basis=(str(fact.id), semantic_fact_statement(fact)), judgment_basis_changed=True,
        judgment_change_reason="Re-cited the same fact under a different representation.",
    ))
    assert not result.judgment_change_accepted
    assert result.judgment_proposition == prior.judgment_proposition
    assert assessment.engineering_semantic_facts == (fact,)


def test_fact_stance_requires_an_actual_known_citation():
    result = build_response_contract(_assessment(), interpretation=_intent(
        Mode.STATUS, judgment_stance=JudgmentStance.FACT, judgment_proposition="Everything passed.", judgment_basis=("invented evidence",),
    ))
    assert result.judgment_stance is JudgmentStance.UNCERTAINTY
    assert result.judgment_basis == ()


def test_repeated_failure_changes_diagnostic_strategy_without_a_guardian_engine():
    first = build_response_contract(_assessment(), interpretation=_intent(Mode.DIAGNOSE, repeated_failure_signature="preview-unreachable"))
    failed = _intent(Mode.DIAGNOSE, repeated_failure_signature="preview-unreachable", prior_strategy_failed=True)
    second = build_response_contract(_assessment(), interpretation=failed, previous_contract=first)
    status = build_response_contract(_assessment(), interpretation=_intent(Mode.STATUS), previous_contract=second)
    third = build_response_contract(_assessment(), interpretation=failed, previous_contract=status)
    assert first.response_moves != second.response_moves != third.response_moves
    assert second.strategy_revision == 1
    assert third.strategy_revision == 2
    assert Move.CHALLENGE_ASSUMPTIONS in second.response_moves
    assert Move.STOP_UNPRODUCTIVE_ROUTE in third.response_moves
    assert third.advancement_obligation is Advance.REPLAN_REQUEST
    assert third.authority == "ADVISORY_ONLY"
    assert third.question_budget == 0


def test_failed_local_execute_route_is_reframed_as_focused_diagnosis():
    result = build_response_contract(_assessment(Intent.ACTION_REQUEST), interpretation=_intent(
        Mode.EXECUTE, repeated_failure_signature="unresponsive-control", prior_strategy_failed=True,
    ))
    assert result.interaction_mode is Mode.DIAGNOSE
    assert result.information_budget is Budget.FOCUSED_DIAGNOSIS
    assert result.advancement_obligation is Advance.REPLAN_REQUEST


def test_adjacent_insight_is_bounded_optional_and_after_answer():
    contract = build_response_contract(_assessment(), interpretation=_intent(Mode.ANSWER))
    assert contract.adjacent_insight_budget == 1
    assert contract.response_moves[0] is Move.DIRECT_ANSWER
    with pytest.raises(ValidationError):
        ResponseContract.model_validate({**contract.model_dump(), "response_moves": [Move.OPTIONAL_ADJACENT_INSIGHT, Move.DIRECT_ANSWER]})
    with pytest.raises(ValidationError):
        ResponseContract.model_validate({**contract.model_dump(), "adjacent_insight_budget": 2})


def test_legacy_turn_intent_is_compatible_without_new_mode_heuristics():
    contract = build_response_contract(_assessment(Intent.CONTINUE_CURRENT_WORK))
    assert contract.interaction_mode is Mode.EXECUTE
    assert contract.question_budget == 0
    assert contract.information_budget is Budget.MINIMAL_ACKNOWLEDGEMENT
    assert "Legacy compatibility" in contract.decision_basis[0]


def test_human_authority_pause_never_frames_execution_even_without_an_askable_question():
    contract = build_response_contract(
        _assessment(governance=GovernanceCandidateKind.HUMAN_DECISION_REQUIRED),
        interpretation=_intent(Mode.EXECUTE, executable_context=True),
    )
    assert contract.advancement_obligation is Advance.PAUSE_FOR_HUMAN_AUTHORITY
    assert contract.opening_move is Opening.REALITY_FIRST
    assert contract.question_budget == 0
    assert Move.PROCEED not in contract.response_moves


def test_contract_cannot_be_built_over_mismatched_semantic_basis():
    assessment = _assessment().model_copy(update={"basis_fingerprint": "b" * 64})
    with pytest.raises(ValueError, match="exact semantic basis"):
        build_response_contract(assessment, interpretation=_intent(Mode.ANALYZE))


@pytest.mark.parametrize("intent", [Intent.COMPARE, Intent.REQUEST_DECISION_SUPPORT])
@pytest.mark.parametrize("advisory_mode", [Mode.ANALYZE, Mode.ANSWER])
def test_choice_obligation_converges_on_decisive_factors_despite_generic_advisory_mode(intent, advisory_mode):
    contract = build_response_contract(_assessment(intent), interpretation=_intent(advisory_mode))
    assert contract.interaction_mode is Mode.DECIDE
    assert contract.primary_obligation is Obligation.COMPARE
    assert contract.information_budget is Budget.DECISIVE_FACTORS
    assert contract.response_moves == (Move.COMPARISON, Move.DECISIVE_FACTORS, Move.RECOMMENDATION)


def test_comparing_exploratory_possibilities_does_not_force_a_decision():
    contract = build_response_contract(_assessment(Intent.COMPARE), interpretation=_intent(Mode.EXPLORE))
    assert contract.interaction_mode is Mode.EXPLORE
    assert contract.information_budget is Budget.RELEVANT_DIVERGENCE
    assert contract.advancement_obligation is Advance.ANSWER_ONLY


@pytest.mark.parametrize("intent", [Intent.MODIFY, Intent.ACTION_REQUEST, Intent.CONTINUE_CURRENT_WORK])
@pytest.mark.parametrize("executable,expected", [(False, Advance.PROPOSE_AND_WAIT), (True, Advance.ANSWER_AND_PROCEED)])
def test_repair_request_preserves_governed_advancement_instead_of_answer_only(intent, executable, expected):
    assessment = _assessment(intent)
    before = assessment.model_dump_json()
    contract = build_response_contract(assessment, interpretation=_intent(Mode.DIAGNOSE, executable_context=executable))
    assert contract.advancement_obligation is expected
    assert contract.information_budget is Budget.FOCUSED_DIAGNOSIS
    assert Move.FIX in contract.response_moves
    assert Move.VERIFY in contract.response_moves
    assert contract.question_budget == 0
    assert assessment.model_dump_json() == before


def test_diagnostic_advancement_cannot_override_an_existing_human_authority_pause():
    contract = build_response_contract(
        _assessment(Intent.MODIFY, governance=GovernanceCandidateKind.HUMAN_DECISION_REQUIRED),
        interpretation=_intent(Mode.DIAGNOSE, executable_context=True),
    )
    assert contract.advancement_obligation is Advance.PAUSE_FOR_HUMAN_AUTHORITY


@pytest.mark.parametrize("source", ["I disagree with that judgment.", "The existing design remains unchanged."])
def test_provider_invented_working_fact_cannot_supply_its_own_judgment_reversal_evidence(source):
    invented = "A benchmark proves separate services are ten times faster."
    result = build_response_contract(
        _assessment(Intent.DISAGREEMENT, facts=(invented,)),
        source_records=(_record(source),), previous_contract=_professional_judgment(),
        interpretation=_intent(Mode.CORRECT, judgment_subject="service topology",
            judgment_proposition="Split into microservices.", judgment_stance=JudgmentStance.RECOMMENDATION,
            judgment_basis=(invented,), judgment_basis_changed=True, judgment_change_reason="New benchmark evidence."),
    )
    assert not result.judgment_change_accepted
    assert result.judgment_proposition == "Keep a modular monolith."
    assert result.information_budget is Budget.DECISIVE_FACTORS


@pytest.mark.parametrize("category", [SemanticCategory.MOTIVE, SemanticCategory.DESIRED_OUTCOME, SemanticCategory.CONSTRAINT])
def test_material_delta_needs_human_source_grounding_not_just_an_existing_record_id(category):
    invented = "The primary objective is now independent releases."
    delta = SemanticDelta(
        id=UUID(int=7), category=category, operation=SemanticDeltaOperation.REVISED,
        value=invented, source_record_ids=(UUID(int=1),), basis_fingerprint="a" * 64,
        confidence=1, rationale="The Provider inferred a changed goal.",
    )
    result = build_response_contract(
        _assessment(Intent.DISAGREEMENT, deltas=(delta,)), source_records=(_record("I disagree."),),
        previous_contract=_professional_judgment(), interpretation=_intent(
            Mode.ANALYZE, judgment_subject="service topology", judgment_proposition="Split into microservices.",
            judgment_basis=(f"semantic_delta:{delta.id}",), judgment_basis_changed=True,
            judgment_change_reason="The primary objective changed.",
        ),
    )
    assert not result.judgment_change_accepted


def test_real_new_human_fact_can_change_judgment_even_during_disagreement():
    fact = "The team now contains forty engineers across independent release groups."
    result = build_response_contract(
        _assessment(Intent.DISAGREEMENT, facts=(fact,)), source_records=(_record(f"I disagree. {fact}"),),
        previous_contract=_professional_judgment(), interpretation=_intent(
            Mode.ANALYZE, judgment_subject="service topology", judgment_proposition="Separate the independently owned services.",
            judgment_basis=(fact,), judgment_basis_changed=True, judgment_change_reason="Team size and release ownership changed.",
        ),
    )
    assert result.judgment_change_accepted
    assert result.information_budget is Budget.REASONED_TRADEOFFS


def test_a_watt_message_cannot_manufacture_a_new_human_priority():
    fact = "Independent releases matter more than low operating cost."
    result = build_response_contract(
        _assessment(Intent.DISAGREEMENT, facts=(fact,)), source_records=(_record(fact, actor=InteractionActor.WATT),),
        previous_contract=_professional_judgment(), interpretation=_intent(
            Mode.ANALYZE, judgment_subject="service topology", judgment_proposition="Split into microservices.",
            judgment_basis=(fact,), judgment_basis_changed=True, judgment_change_reason="Changed priority.",
        ),
    )
    assert not result.judgment_change_accepted
