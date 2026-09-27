"""Boundary classification is independent of the owner that generated a candidate."""

from datetime import UTC, datetime

from spg.application.interaction import _classify_turn_failure
from spg.domain.interaction import StructuredResponseSchemaViolation
from spg.domain.refinement_contract import RefinementClass, classify_refinement


def test_owner_retry_exhaustion_is_work_nonconvergence_without_authority_fabrication():
    from spg.domain.refinement_contract import convergence_condition
    basis = dict(missing_acceptance=("REVIEW_RUNTIME_READY",), attempts=2,
        no_progress_count=2, elapsed_seconds=60)
    assert convergence_condition(**basis) == "NOT_YET_CONVERGED"
    assert convergence_condition(**basis, owner_budget_exhausted=True) == "NON_CONVERGING"
    assert convergence_condition(**{**basis, "missing_acceptance": ()},
        owner_budget_exhausted=True) == "CONVERGED_FOR_REVIEW"


def test_bounded_success_is_routine_not_incident() -> None:
    assert classify_refinement(converged=True, same_signature_count=1) is (
        RefinementClass.ROUTINE_STOCHASTIC_REFINEMENT
    )


def test_repeated_success_becomes_economic_signal() -> None:
    assert classify_refinement(converged=True, prior_occurrences=3) is (
        RefinementClass.DEGRADING_OR_RECURRING_REFINEMENT
    )
    assert classify_refinement(converged=True, same_signature_count=2) is (
        RefinementClass.DEGRADING_OR_RECURRING_REFINEMENT
    )


def test_unchanged_failure_and_authority_boundary_are_systemic() -> None:
    for options in (
        {"converged": False, "same_signature_count": 2},
        {"converged": False, "budget_exhausted": True},
        {"converged": False, "authority_required": True},
    ):
        assert classify_refinement(**options) is (
            RefinementClass.SYSTEMIC_OR_NON_CONVERGING_INCIDENT
        )


def test_failed_bounded_wic_repair_is_observable_without_raw_candidate() -> None:
    failure = _classify_turn_failure(
        StructuredResponseSchemaViolation(
            "bounded schema repair exhausted", validation_issue="missing field",
            repair_attempted=True,
        ),
        datetime.now(UTC),
    )
    observation = failure.metadata["refinement_observation"]
    assert observation["refinement_class"] == "SYSTEMIC_OR_NON_CONVERGING_INCIDENT"
    assert observation["attempt_count"] == 2
    assert "candidate" not in observation


def test_lost_action_refinement_retains_specific_signal_in_success_and_exhaustion():
    from spg.application.interaction import _pipeline_refinement_observation
    observation = _pipeline_refinement_observation({
        'semantic_structured_repair_count': 1,
        'semantic_action_repair_signal': 'EXPLICIT_ACTION_LOST_BEFORE_EXECUTION'})
    assert observation['signal_kind'] == 'EXPLICIT_ACTION_LOST_BEFORE_EXECUTION'
    assert observation['attempt_count'] == 2 and observation['converged'] is True
    failure = _classify_turn_failure(StructuredResponseSchemaViolation(
        'repair exhausted', validation_issue='ACTION_REQUEST_MISSING_CANONICAL_BINDING',
        repair_attempted=True), datetime.now(UTC))
    assert failure.metadata['refinement_observation']['signal_kind'] == 'EXPLICIT_ACTION_LOST_BEFORE_EXECUTION'
    assert failure.metadata['refinement_observation']['converged'] is False
