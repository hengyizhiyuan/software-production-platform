from datetime import UTC, datetime
from uuid import uuid4

from spg.application.work import WorkApplicationService
from spg.domain.product import (
    EngineeringScopeCondition,
    EngineeringScopeRecord,
    ResourceBindingCondition,
    ResourceBindingRecord,
    RuntimeFactSummary,
    WorkCondition,
    WorkProjection,
    WorkRecord,
    WorkStatus,
)


def _work(*, condition: WorkCondition = WorkCondition.READY) -> WorkRecord:
    now = datetime.now(UTC)
    return WorkRecord(
        id=uuid4(),
        goal_id=None,
        raw_user_requirement="  exact raw request\n",
        refined_title="Exact Work",
        desired_outcome="Produce exact output",
        constraints=(),
        tags=("mvp", "mvp", "review"),
        condition=condition,
        engineering_scope_id=None,
        scope_summary=None,
        production_objective="Produce exact output",
        expected_artifact_path="docs/output.md",
        verification_expectation="verify output",
        created_at=now,
        updated_at=now,
    )


def _projection_service() -> WorkApplicationService:
    service = object.__new__(WorkApplicationService)
    service.executor = None
    service.verifier = None
    return service


def test_work_contract_preserves_raw_source_and_has_no_project_ownership() -> None:
    work = _work()
    assert work.raw_user_requirement == "  exact raw request\n"
    assert work.tags == ("mvp", "review")
    assert "project_id" not in WorkRecord.model_fields
    assert "resource_id" not in WorkRecord.model_fields


def test_engineering_scope_structurally_supports_many_resource_bindings() -> None:
    now = datetime.now(UTC)
    scope_id = uuid4()
    scope = EngineeringScopeRecord(
        id=scope_id,
        work_id=uuid4(),
        summary="two-resource future shape",
        fingerprint="a" * 64,
        condition=EngineeringScopeCondition.PROPOSED,
        bindings=tuple(
            ResourceBindingRecord(
                id=uuid4(),
                engineering_scope_id=scope_id,
                resource_id=uuid4(),
                condition=ResourceBindingCondition.PROPOSED,
                created_at=now,
            )
            for _ in range(2)
        ),
        created_at=now,
        updated_at=now,
    )
    assert len(scope.bindings) == 2


def test_product_projection_is_not_a_runtime_transition_contract() -> None:
    assert "status" in WorkProjection.model_fields
    assert "condition" not in WorkProjection.model_fields
    assert "transition" not in WorkProjection.model_fields


def test_provider_success_without_observation_is_not_completed() -> None:
    status, _, _, _ = _projection_service()._projection_state(
        _work(),
        RuntimeFactSummary(
            attempt_id=uuid4(),
            dispatch_id=uuid4(),
            provider_outcome="SUCCESS",
        ),
    )
    assert status is WorkStatus.RUNNING
    assert status is not WorkStatus.COMPLETED


def test_runtime_commit_completion_separates_steering_from_legacy_work() -> None:
    trusted_cycle = RuntimeFactSummary(
        completion_id=uuid4(),
        completion_outcome="PRODUCED",
        verification_results=("PASS",),
        integration_effect_id=uuid4(),
        integration_state="CONVERGED",
        runtime_commit_id=uuid4(),
    )
    legacy, _, _, _ = _projection_service()._projection_state(
        _work(),
        trusted_cycle,
    )
    steering_active, _, _, _ = _projection_service()._projection_state(
        _work(),
        trusted_cycle,
        steering_enabled=True,
    )
    steering_complete, _, _, _ = _projection_service()._projection_state(
        _work(),
        trusted_cycle,
        steering_enabled=True,
        steering_complete=True,
    )
    assert legacy is WorkStatus.COMPLETED
    assert steering_active is WorkStatus.RUNNING
    assert steering_complete is WorkStatus.COMPLETED


def test_unknown_or_not_produced_reality_is_blocked_not_completed() -> None:
    status, _, _, _ = _projection_service()._projection_state(
        _work(),
        RuntimeFactSummary(
            attempt_id=uuid4(),
            dispatch_id=uuid4(),
            provider_outcome="UNKNOWN",
            observation_id=uuid4(),
            completion_id=uuid4(),
            completion_outcome="NOT_PRODUCED",
        ),
    )
    assert status is WorkStatus.BLOCKED


def test_stopped_unknown_none_reality_is_blocked_before_completion() -> None:
    status, step, event, next_action = _projection_service()._projection_state(
        _work(),
        RuntimeFactSummary(
            attempt_id=uuid4(),
            dispatch_id=uuid4(),
            provider_outcome="UNKNOWN",
            observation_id=uuid4(),
            completion_requires_production_result=True,
        ),
    )
    assert status is WorkStatus.BLOCKED
    assert step == "EXECUTION_STOPPED"
    assert event == "PROVIDER_OUTCOME_UNKNOWN_PRODUCTION_NONE"
    assert next_action == (
        "Execution stopped before Provider completion. "
        "Architecture/Operator review required."
    )
    assert "Evaluate Completion" not in next_action


def test_terminal_success_none_required_result_is_blocked_without_rewriting_provider() -> None:
    facts = RuntimeFactSummary(
        attempt_id=uuid4(),
        dispatch_id=uuid4(),
        provider_outcome="SUCCESS",
        observation_id=uuid4(),
        completion_requires_production_result=True,
    )

    status, step, event, next_action = _projection_service()._projection_state(
        _work(),
        facts,
    )

    assert status is WorkStatus.BLOCKED
    assert step == "EXECUTION_STOPPED"
    assert event == "REQUIRED_PRODUCTION_RESULT_ABSENT"
    assert next_action == (
        "Execution completed without the required production result. "
        "Architecture/Operator review required."
    )
    assert facts.provider_outcome == "SUCCESS"


def test_terminal_success_none_remains_representable_when_contract_allows_none() -> None:
    status, step, _, next_action = _projection_service()._projection_state(
        _work(),
        RuntimeFactSummary(
            attempt_id=uuid4(),
            dispatch_id=uuid4(),
            provider_outcome="SUCCESS",
            observation_id=uuid4(),
            completion_requires_production_result=False,
        ),
    )

    assert status is WorkStatus.RUNNING
    assert step == "PRODUCTION_OBSERVATION"
    assert next_action == "Evaluate Completion"


def test_broad_request_uses_needs_refinement_policy() -> None:
    assert WorkApplicationService._is_too_broad(
        "Rewrite the whole entire platform and all systems"
    )
    assert not WorkApplicationService._is_too_broad(
        "Add one bounded Work projection"
    )
