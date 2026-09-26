"""A transient repository timeout does not require a Human retry button."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.application.production_admission import ProductionAdmissionTrigger
from spg.domain.assets import RepositoryAcquisitionFailureCategory


@pytest.mark.parametrize("failure_category, expected_attempts", [
    (RepositoryAcquisitionFailureCategory.NETWORK_FAILURE, 2),
    (RepositoryAcquisitionFailureCategory.AUTH_REQUIRED, 1),
])
def test_retries_only_network_failure_once_under_same_work(
    monkeypatch, failure_category, expected_attempts,
):
    interaction_id, work_id, first_id = uuid4(), uuid4(), uuid4()
    source = "https://github.com/example/public-project.git"

    class Assets:
        def __init__(self):
            self.attempts = [{
                "intake_request_id": str(first_id),
                "source": source,
                "condition": "REQUESTED",
                "operation_kind": "ACQUIRE",
            }]
            self.requests = []

        def latest_attempt_for_work(self, selected_work_id):
            assert selected_work_id == work_id
            return self.attempts[-1]

        def next_attempt_number(self, selected_work_id):
            assert selected_work_id == work_id
            return len(self.attempts) + 1

        def start_intake(self, request):
            self.requests.append(request)
            self.attempts.append({
                "intake_request_id": str(request.request_id),
                "source": request.source,
                "condition": "REQUESTED",
                "operation_kind": request.operation_kind,
            })
            return self.attempts[-1]

        def execute_intake(self, request_id):
            attempt = next(item for item in self.attempts
                           if item["intake_request_id"] == str(request_id))
            attempt.update({
                "condition": "FAILED_RETRYABLE" if request_id == first_id else "READY",
                "failure_category": failure_category.value if request_id == first_id else None,
                "resource_id": None if request_id == first_id else str(uuid4()),
            })
            return attempt

    class Interactions:
        def __init__(self):
            self.progress = []

        def get_shared_understanding(self, selected_interaction_id):
            assert selected_interaction_id == interaction_id
            return SimpleNamespace(
                governed_work_id=work_id,
                interpreted_motive="Add the requested link",
                desired_outcome="A reviewable navigation change",
            )

        def record_production_admission_progress(self, *args, **kwargs):
            self.progress.append((args, kwargs))

    assets, interactions = Assets(), Interactions()
    trigger = ProductionAdmissionTrigger(interactions, None, assets, None)
    monkeypatch.setattr(
        trigger, "_bind_and_activate", lambda **kwargs: kwargs["observation"]
    )
    result = trigger.execute(
        interaction_id, SimpleNamespace(), SimpleNamespace(source="human:owner")
    )

    assert len(assets.attempts) == expected_attempts
    assert result["condition"] == (
        "READY" if expected_attempts == 2 else "FAILED_RETRYABLE"
    )
    if expected_attempts == 2:
        retry = assets.requests[0]
        assert retry.work_id == work_id
        assert retry.source == source
        assert retry.previous_attempt_id == first_id
        assert retry.attempt_number == 2
        assert assets.attempts[0]["condition"] == "FAILED_RETRYABLE"
    assert len(interactions.progress) == 1
