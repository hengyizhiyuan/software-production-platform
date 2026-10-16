"""Bounded Formation rounds: which stops may open a new round, and how many."""
from datetime import UTC, datetime, timedelta

import pytest

from spg.application.governed_obligations import (
    FORMATION_MAX_ROUNDS, formation_retry_decision, formation_stop_kind)

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
TRANSPORT = "OBLIGATION_FORMATION_TRANSPORT_ModelProviderError"
PENDING = "OBLIGATION_FORMATION_PENDING_OUTCOME_UNKNOWN"
CONFLICT = "OBLIGATION_PROJECTION_CONFLICTING_DISPOSITION"
REVIEW = "OBLIGATION_SEMANTIC_COMPONENT_MISMATCH"
CORRESPONDENCE = "OBLIGATION_SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN"


def stops(*reasons, age_minutes=1):
    # A rejected-candidate stop is one where the Owner validated both candidates.
    return tuple((NOW - timedelta(minutes=age_minutes * (len(reasons) - i)), r, r in (CONFLICT, REVIEW, CORRESPONDENCE))
                 for i, r in enumerate(reasons))


@pytest.mark.parametrize("reason,validated,kind", [(TRANSPORT, False, "TRANSIENT"), (PENDING, False, "TRANSIENT"),
    (CONFLICT, True, "GENERATOR"), (CORRESPONDENCE, True, "GENERATOR"), (CORRESPONDENCE, False, None),
    ("OBLIGATION_FORMATION_BUDGET_EXHAUSTED", False, "GENERATOR"),
    ("OBLIGATION_FORMATION_WIRE_RECEIPT_IDENTITY_DRIFT", True, None), ("OBLIGATION_FORMATION_RECEIPT_LIMIT", True, None),
    ("OBLIGATION_ADMITTED_ITEM_HUMAN_SOURCE_INVALID", False, None), (None, True, None)])
def test_only_transient_and_rejected_candidate_stops_are_retryable(reason, validated, kind):
    assert formation_stop_kind(reason, candidates_validated=validated) == kind


def test_first_round_has_no_stop_and_no_retry():
    assert formation_retry_decision((), now=NOW) == (1, None, False)


def test_transient_stops_retry_up_to_their_limit():
    assert formation_retry_decision(stops(TRANSPORT), now=NOW) == (2, "TRANSIENT", True)
    assert formation_retry_decision(stops(TRANSPORT, PENDING, TRANSPORT), now=NOW) == (4, "TRANSIENT", True)
    assert formation_retry_decision(stops(TRANSPORT, PENDING, TRANSPORT, TRANSPORT), now=NOW)[2] is False


def test_a_stochastic_defect_gets_exactly_one_fresh_round():
    assert formation_retry_decision(stops(CONFLICT), now=NOW) == (2, "GENERATOR", True)
    assert formation_retry_decision(stops(CONFLICT, REVIEW), now=NOW) == (2, "GENERATOR", False)


def test_identity_or_capacity_stops_never_open_a_round():
    assert formation_retry_decision(stops("OBLIGATION_FORMATION_RECEIPT_LIMIT"), now=NOW) == (1, None, False)
    assert formation_retry_decision(stops(TRANSPORT, "OBLIGATION_FORMATION_WIRE_RECEIPT_IDENTITY_DRIFT"),
                                    now=NOW)[2] is False


def test_rounds_are_bounded_overall_and_in_time():
    assert len(stops(*([TRANSPORT] * FORMATION_MAX_ROUNDS))) == FORMATION_MAX_ROUNDS
    assert formation_retry_decision(stops(*([TRANSPORT] * FORMATION_MAX_ROUNDS)), now=NOW)[2] is False
    assert formation_retry_decision(stops(TRANSPORT, age_minutes=120), now=NOW)[2] is False


def test_a_later_round_is_a_distinct_inventory_and_round_one_is_unchanged():
    from types import SimpleNamespace
    from uuid import uuid4
    from spg.application.governed_obligations import fulfillment_inventory
    from tests.test_c3_fulfillment_admission_stop import basis
    revision, ir = basis()
    first = fulfillment_inventory(revision, ir, source_revision=revision.source_revision)
    again = fulfillment_inventory(revision, ir, source_revision=revision.source_revision, formation_round=1)
    second = fulfillment_inventory(revision, ir, source_revision=revision.source_revision, formation_round=2)
    assert first == again and "formation_round" not in first
    assert second["formation_round"] == 2 and second["inventory_fingerprint"] != first["inventory_fingerprint"]
    with pytest.raises(ValueError):
        fulfillment_inventory(revision, ir, source_revision=revision.source_revision, formation_round=FORMATION_MAX_ROUNDS + 1)


def test_a_human_restart_reopens_the_window_but_not_the_round_budget():
    old = stops(CONFLICT, age_minutes=600)
    assert formation_retry_decision(old, now=NOW)[2] is False
    assert formation_retry_decision(old, now=NOW, human_restart_at=NOW - timedelta(minutes=1)) == (2, "GENERATOR", True)
    spent = stops(CONFLICT, REVIEW, age_minutes=600)
    assert formation_retry_decision(spent, now=NOW, human_restart_at=NOW)[2] is False
