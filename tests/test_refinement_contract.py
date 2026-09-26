"""Boundary classification is independent of the owner that generated a candidate."""

from datetime import UTC, datetime

from spg.application.interaction import _classify_turn_failure
from spg.domain.interaction import StructuredResponseSchemaViolation
from spg.domain.refinement_contract import RefinementClass, classify_refinement


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
