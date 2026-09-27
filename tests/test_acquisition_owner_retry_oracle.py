from copy import deepcopy

import pytest

from benchmarks.golden.runtime.owner_retry_oracle import observed_acquisition_recovery


def receipts():
    request = dict(interaction_id="interaction", source_record_id="human-record",
        source="https://example.invalid/project.git", authority_identity="human:owner",
        operation_kind="ACQUIRE")
    return [
        dict(id="first", request=dict(request, request_id="first", attempt_number=1),
            observation=dict(intake_request_id="first", condition="FAILED_RETRYABLE",
                failure_category="NETWORK_FAILURE")),
        dict(id="second", request=dict(request, request_id="second", attempt_number=2,
            previous_attempt_id="first"), observation=dict(intake_request_id="second",
                previous_attempt_id="first", condition="READY", revision="a" * 40,
                tree="b" * 40, operation_evidence=dict(verified=True,
                    capability_id="git.repository.acquire", resulting_revision="a" * 40))),
    ]


def qualifies(rows):
    return observed_acquisition_recovery(rows, interaction_id="interaction",
        source_record_id="human-record")


def test_pre_work_owner_recovery_requires_no_work_event():
    assert qualifies(receipts())


@pytest.mark.parametrize("row,part,key,value", [
    (1, "request", "previous_attempt_id", "unrelated"),
    (1, "request", "source_record_id", "another-human-record"),
    (1, "request", "authority_identity", "another-owner"),
    (1, "request", "source", "https://example.invalid/other.git"),
    (1, "request", "attempt_number", 4),
    (0, "observation", "failure_category", "AUTH_REQUIRED"),
    (1, "observation", "revision", "c" * 40),
])
def test_other_lineage_or_terminal_or_unverified_effect_is_not_recovery(row, part, key, value):
    rows = deepcopy(receipts())
    rows[row][part][key] = value
    assert not qualifies(rows)


def test_narrative_ready_without_verified_git_receipt_is_not_recovery():
    rows = receipts()
    rows[1]["observation"]["operation_evidence"]["verified"] = False
    assert not qualifies(rows)
