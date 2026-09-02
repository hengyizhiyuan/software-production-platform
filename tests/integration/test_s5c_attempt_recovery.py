from pathlib import Path
import shutil
from uuid import uuid4

from alembic import command
import pytest
from sqlalchemy import func, inspect, select, update

from spg.application.attempt_recovery import AttemptRecoveryService
from spg.application.completion import CompletionService
from spg.domain.execution import ProviderReportedOutcome
from spg.domain.recovery import (
    AttemptRetryRecoveryRequest,
    RecoveryActionOutcome,
    RecoveryActionRequest,
    RecoveryAssessmentStale,
    RecoveryGuidance,
)
from spg.domain.runtime import (
    AttemptCondition,
    CompletionContract,
    InitialRunRequest,
    ProductionHorizon,
    RuntimeInvariantViolation,
    RuntimeRecordNotFound,
    WorkUnitCondition,
)
from spg.infrastructure.persistence import Database, metadata
from spg.infrastructure.persistence.runtime_schema import (
    attempt_preparations,
    execution_attempts,
    plan_revisions,
    production_runs,
    production_snapshots,
    recovery_action_records,
    runtime_tables,
)
from spg.infrastructure.persistence.runtime_store import RuntimeStore
import test_s5a_recovery_assessment as s5a


pytestmark = pytest.mark.postgresql
clean_runtime_schema = s5a.clean_runtime_schema
git_repository = s5a.git_repository


def _case(
    database,
    repository,
    tmp_path,
    *,
    label="attempt-recovery",
    outcome=ProviderReportedOutcome.FAILURE,
    changes=False,
    dispatch_only=False,
    execute=True,
    completion_contract=None,
):
    facts = s5a._build_attempt(
        database,
        repository,
        tmp_path,
        label=label,
        outcome=outcome,
        changes=changes,
        dispatch_only=dispatch_only,
        execute=execute,
        completion_contract=completion_contract,
    )
    assessment = facts.recovery.assess_recovery(s5a._attempt_request(facts))
    service = AttemptRecoveryService(
        database,
        preparation=facts.preparation,
        execution=facts.execution,
        completion=CompletionService(database, observer=facts.execution.observer),
    )
    request = RecoveryActionRequest(
        recovery_assessment_id=assessment.id,
        expected_assessment_fingerprint=assessment.basis_fingerprint,
    )
    return facts, assessment, service, request


def _retry_request(facts, assessment, tmp_path):
    return AttemptRetryRecoveryRequest(
        recovery_assessment_id=assessment.id,
        expected_assessment_fingerprint=assessment.basis_fingerprint,
        context_package_id=facts.prepared.context_package.id,
        executor_binding=facts.prepared.preparation.executor_binding,
        repository_path=facts.repository,
        workspace_root=tmp_path / "retry-workspaces",
    )


def _count(database: Database, table) -> int:
    with database.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(table))


def _remove_workspace(facts) -> None:
    shutil.rmtree(facts.prepared.preparation.workspace.workspace_path)


def test_s5c_migration_downgrade_and_reupgrade(postgres_database: Database) -> None:
    config = s5a._migration_config(postgres_database)
    command.downgrade(config, "20260829_10")
    columns = {item["name"] for item in inspect(postgres_database.engine).get_columns("recovery_action_records")}
    assert "old_attempt_id" not in columns
    command.upgrade(config, "head")
    columns = {item["name"] for item in inspect(postgres_database.engine).get_columns("recovery_action_records")}
    assert {"old_attempt_id", "new_attempt_id", "workspace_identity"} <= columns


def test_s5c_01_exact_attempt_recovery_assessment_required(postgres_database, git_repository, tmp_path) -> None:
    repository = s5a._build_repository(postgres_database, git_repository, tmp_path, mode="converged")
    assessment = repository.recovery.assess_recovery(repository.recovery_request)
    with pytest.raises(RuntimeInvariantViolation, match="ATTEMPT"):
        AttemptRecoveryService(postgres_database).recover_attempt_work(
            RecoveryActionRequest(
                recovery_assessment_id=assessment.id,
                expected_assessment_fingerprint=assessment.basis_fingerprint,
            )
        )


def test_s5c_02_assessment_fingerprint_must_match(postgres_database, git_repository, tmp_path) -> None:
    _, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    with pytest.raises(RuntimeInvariantViolation, match="fingerprint"):
        service.recover_attempt_work(
            RecoveryActionRequest(
                recovery_assessment_id=assessment.id,
                expected_assessment_fingerprint="0" * 64,
            )
        )


def test_s5c_03_historical_assessment_is_immutable(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, request = _case(postgres_database, git_repository, tmp_path)
    before = assessment
    service.recover_attempt_work(request)
    assert facts.recovery.assessment(before.id) == before


def test_s5c_04_changed_current_reality_makes_old_assessment_non_actionable(postgres_database, git_repository, tmp_path) -> None:
    facts, _, service, request = _case(postgres_database, git_repository, tmp_path)
    facts.runtime.retry_attempt(facts.attempt.id)
    with pytest.raises(RecoveryAssessmentStale):
        service.recover_attempt_work(request)


def test_s5c_05_interrupted_attempt_outcome_remains_historical_unknown(postgres_database, git_repository, tmp_path) -> None:
    facts, _, service, request = _case(
        postgres_database, git_repository, tmp_path,
        outcome=ProviderReportedOutcome.UNKNOWN, changes=True,
    )
    service.recover_attempt_work(request)
    with postgres_database.unit_of_work() as unit_of_work:
        store = RuntimeStore(unit_of_work.session)
        dispatch = store.execution_dispatch_for_attempt(facts.attempt.id)
        report = store.provider_execution_report(dispatch.id)
        attempt = store.attempt(facts.attempt.id)
    assert report.outcome is ProviderReportedOutcome.UNKNOWN
    assert attempt.condition is AttemptCondition.CREATED


def test_s5c_06_reobservation_uses_independent_workspace_reality(postgres_database, git_repository, tmp_path) -> None:
    facts, _, service, request = _case(
        postgres_database, git_repository, tmp_path, dispatch_only=True,
    )
    target = facts.prepared.preparation.workspace.workspace_path / "docs" / "attempt-recovery.md"
    target.write_text("independently observable work\n")
    result = service.recover_attempt_work(request)
    assert result.observation is not None
    assert [item.repository_relative_path for item in result.observation.changes] == ["docs/attempt-recovery.md"]


def test_s5c_07_provider_success_does_not_define_salvageability(postgres_database, git_repository, tmp_path) -> None:
    _, _, service, request = _case(
        postgres_database, git_repository, tmp_path,
        outcome=ProviderReportedOutcome.SUCCESS, changes=False,
    )
    result = service.recover_attempt_work(request)
    assert result.action.outcome is RecoveryActionOutcome.INCOMPLETE


def test_s5c_08_provider_failure_does_not_destroy_valid_work(postgres_database, git_repository, tmp_path) -> None:
    _, _, service, request = _case(
        postgres_database, git_repository, tmp_path,
        outcome=ProviderReportedOutcome.FAILURE, changes=True,
    )
    assert service.recover_attempt_work(request).action.outcome is RecoveryActionOutcome.SALVAGED


def test_s5c_09_provider_unknown_does_not_destroy_valid_work(postgres_database, git_repository, tmp_path) -> None:
    _, _, service, request = _case(
        postgres_database, git_repository, tmp_path,
        outcome=ProviderReportedOutcome.UNKNOWN, changes=True,
    )
    assert service.recover_attempt_work(request).action.outcome is RecoveryActionOutcome.SALVAGED


def test_s5c_10_completion_contract_governs_salvageability(postgres_database, git_repository, tmp_path) -> None:
    contract = CompletionContract(required_outputs=("docs/other.md",))
    _, _, service, request = _case(
        postgres_database, git_repository, tmp_path,
        changes=True, completion_contract=contract,
    )
    assert service.recover_attempt_work(request).action.outcome is RecoveryActionOutcome.INCOMPLETE


def test_s5c_11_completed_observed_work_preserved_without_retry(postgres_database, git_repository, tmp_path) -> None:
    _, _, service, request = _case(postgres_database, git_repository, tmp_path, changes=True)
    before = _count(postgres_database, execution_attempts)
    result = service.recover_attempt_work(request)
    assert result.retry_attempt is None
    assert _count(postgres_database, execution_attempts) == before


def test_s5c_12_recovery_continues_through_normal_completion(postgres_database, git_repository, tmp_path) -> None:
    facts, _, service, request = _case(postgres_database, git_repository, tmp_path, changes=True)
    result = service.recover_attempt_work(request)
    assert result.completion_evaluation.outcome.value == "PRODUCED"
    assert facts.runtime.inspect_run(facts.spine.run.id).work_unit.condition is WorkUnitCondition.PRODUCED


def test_s5c_13_no_special_recovery_produced_state(postgres_database, git_repository, tmp_path) -> None:
    _, _, service, request = _case(postgres_database, git_repository, tmp_path, changes=True)
    result = service.recover_attempt_work(request)
    assert result.action.outcome is RecoveryActionOutcome.SALVAGED
    assert set(WorkUnitCondition) == {
        WorkUnitCondition.PROPOSED,
        WorkUnitCondition.PRODUCED,
        WorkUnitCondition.SATISFIED,
        WorkUnitCondition.SUPERSEDED,
    }


def test_s5c_14_zero_git_diff_is_not_universal_retry_condition(postgres_database, git_repository, tmp_path) -> None:
    contract = CompletionContract(verification_obligations=("non-repository verification",))
    _, _, service, request = _case(
        postgres_database, git_repository, tmp_path,
        outcome=ProviderReportedOutcome.SUCCESS, changes=False,
        completion_contract=contract,
    )
    assert service.recover_attempt_work(request).action.outcome is RecoveryActionOutcome.SALVAGED


def test_s5c_15_retry_requires_retry_guidance(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(
        postgres_database, git_repository, tmp_path,
        outcome=ProviderReportedOutcome.UNKNOWN, changes=False,
    )
    with pytest.raises(RuntimeInvariantViolation, match="does not authorize"):
        service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))


def test_s5c_16_retry_revalidates_current_baseline_plan_pwu(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    replacement = facts.runtime.create_initial_runtime_spine(
        InitialRunRequest(
            intent_ref="intent:test:s5c:replacement-plan",
            goal="Represent changed current Plan authority",
            production_horizon=ProductionHorizon.DOCUMENTATION,
            initial_work_unit_objective="Remain outside the assessed Attempt lineage",
            completion_contract=facts.spine.work_unit.completion_contract,
        )
    )
    with postgres_database.engine.begin() as connection:
        connection.execute(
            update(production_runs)
            .where(production_runs.c.id == facts.spine.run.id)
            .values(current_plan_revision_id=replacement.plan_revision.id)
        )
    with pytest.raises(RecoveryAssessmentStale):
        service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))


def test_s5c_17_new_retry_attempt_uses_new_generation(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    result = service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    assert result.original_attempt.generation == 1
    assert result.retry_attempt.generation == 2


def test_s5c_18_original_attempt_is_not_rewritten(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    before = facts.runtime.get_attempt(facts.attempt.id)
    service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    assert facts.runtime.get_attempt(facts.attempt.id) == before


def test_s5c_19_old_generation_cannot_regain_authority(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    result = service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    assert facts.runtime.attempt_is_current(facts.attempt.id) is False
    assert facts.runtime.attempt_is_current(result.retry_attempt.id) is True


def test_s5c_20_late_old_generation_result_cannot_mutate_current_authority(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    observation_id = facts.execution_result.observation.id
    service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    with pytest.raises(RuntimeInvariantViolation, match="stale Attempt generation"):
        CompletionService(postgres_database, observer=facts.execution.observer).evaluate_observation(observation_id)


def test_s5c_21_retry_uses_existing_attempt_isolation(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    result = service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    assert result.retry_preparation.preparation.workspace.workspace_identity == f"attempt-worktree:{result.retry_attempt.id}"


def test_s5c_22_new_retry_workspace_uses_exact_source_baseline(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    result = service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    workspace = result.retry_preparation.preparation.workspace
    assert workspace.source_revision == facts.baseline.repository_revision
    assert s5a._git(workspace.workspace_path, "rev-parse", "HEAD") == facts.baseline.repository_revision


def test_s5c_23_old_workspace_not_mutated_into_new_workspace(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    old = facts.prepared.preparation.workspace.workspace_path
    before = s5a._git(old, "status", "--porcelain")
    result = service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    assert result.retry_preparation.preparation.workspace.workspace_path != old
    assert s5a._git(old, "status", "--porcelain") == before


def test_s5c_24_partial_work_not_blindly_copied(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    partial = facts.prepared.preparation.workspace.workspace_path / "partial.txt"
    partial.write_text("partial\n")
    with pytest.raises(RecoveryAssessmentStale):
        service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    assert _count(postgres_database, execution_attempts) == 1


def test_s5c_25_missing_workspace_distinguished_from_empty_workspace(postgres_database, git_repository, tmp_path) -> None:
    facts, _, _, _ = _case(postgres_database, git_repository, tmp_path, label="missing")
    _remove_workspace(facts)
    assessment = facts.recovery.assess_recovery(s5a._attempt_request(facts))
    service = AttemptRecoveryService(postgres_database, preparation=facts.preparation, execution=facts.execution)
    missing = service.recover_attempt_work(RecoveryActionRequest(recovery_assessment_id=assessment.id, expected_assessment_fingerprint=assessment.basis_fingerprint))
    assert missing.observation is None
    assert missing.workspace_prepared is False


def test_s5c_26_missing_workspace_may_allow_governed_retry(postgres_database, git_repository, tmp_path) -> None:
    facts, _, _, _ = _case(postgres_database, git_repository, tmp_path)
    _remove_workspace(facts)
    assessment = facts.recovery.assess_recovery(s5a._attempt_request(facts))
    service = AttemptRecoveryService(postgres_database, preparation=facts.preparation, execution=facts.execution)
    result = service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    assert result.retry_attempt.generation == 2
    assert result.workspace_prepared is True


def test_s5c_27_workspace_drift_requires_reassessment(postgres_database, git_repository, tmp_path) -> None:
    facts, _, service, request = _case(postgres_database, git_repository, tmp_path)
    (facts.prepared.preparation.workspace.workspace_path / "drift.txt").write_text("drift\n")
    with pytest.raises(RecoveryAssessmentStale):
        service.recover_attempt_work(request)


def test_s5c_28_retry_creation_is_locally_atomic(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    result = service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    assert result.action.new_attempt_id == result.retry_attempt.id
    assert _count(postgres_database, execution_attempts) == 2
    assert _count(postgres_database, recovery_action_records) == 2


def test_s5c_29_injected_db_failure_creates_no_partial_retry_authority(postgres_database, git_repository, tmp_path, monkeypatch) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    original_insert = RuntimeStore.insert_recovery_action
    calls = {"count": 0}
    def fail_retry(store, values):
        calls["count"] += 1
        if values["action_type"] == "RETRY_WITH_NEW_ATTEMPT":
            raise RuntimeError("injected retry persistence failure")
        return original_insert(store, values)
    monkeypatch.setattr(RuntimeStore, "insert_recovery_action", fail_retry)
    with pytest.raises(RuntimeError, match="injected retry persistence failure"):
        service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    assert _count(postgres_database, execution_attempts) == 1


def test_s5c_30_duplicate_recovery_request_does_not_duplicate_retry(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    request = _retry_request(facts, assessment, tmp_path)
    first = service.retry_attempt_from_recovery(request)
    second = service.retry_attempt_from_recovery(request)
    assert second.idempotent_recognition is True
    assert second.retry_attempt.id == first.retry_attempt.id
    assert _count(postgres_database, execution_attempts) == 2


def test_s5c_31_filesystem_preparation_does_not_claim_cross_system_exactly_once(postgres_database, git_repository, tmp_path, monkeypatch) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    original_prepare = service.preparation.prepare_attempt
    monkeypatch.setattr(service.preparation, "prepare_attempt", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("filesystem interrupted")))
    request = _retry_request(facts, assessment, tmp_path)
    with pytest.raises(RuntimeError, match="filesystem interrupted"):
        service.retry_attempt_from_recovery(request)
    assert _count(postgres_database, execution_attempts) == 2
    assert _count(postgres_database, attempt_preparations) == 1
    monkeypatch.setattr(service.preparation, "prepare_attempt", original_prepare)
    assert service.retry_attempt_from_recovery(request).workspace_prepared is True


def test_s5c_32_retry_attempt_is_not_provider_dispatched(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    result = service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    with postgres_database.unit_of_work() as unit_of_work:
        assert RuntimeStore(unit_of_work.session).execution_dispatch_for_attempt(result.retry_attempt.id) is None


def test_s5c_33_provider_resume_is_not_implemented(postgres_database, git_repository, tmp_path) -> None:
    _, assessment, service, request = _case(
        postgres_database, git_repository, tmp_path, execute=False,
    )
    assert assessment.guidance is RecoveryGuidance.RESUME_EXISTING_ATTEMPT
    assert service.recover_attempt_work(request).action.outcome is RecoveryActionOutcome.UNSUPPORTED_DEFERRED


def test_s5c_34_resume_guidance_not_silently_converted_to_retry(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(
        postgres_database, git_repository, tmp_path, execute=False,
    )
    with pytest.raises(RuntimeInvariantViolation):
        service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    assert _count(postgres_database, execution_attempts) == 1


def test_s5c_35_no_replanning_or_supersession(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    before = _count(postgres_database, plan_revisions)
    service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    assert _count(postgres_database, plan_revisions) == before


def test_s5c_36_recovery_barrier_history_not_rewritten(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, request = _case(postgres_database, git_repository, tmp_path, changes=True)
    assert assessment.recovery_barrier is True
    service.recover_attempt_work(request)
    assert facts.recovery.assessment(assessment.id).recovery_barrier is True


def test_s5c_37_unrelated_valid_work_is_preserved(postgres_database, git_repository, tmp_path) -> None:
    facts, _, service, request = _case(postgres_database, git_repository, tmp_path, changes=True)
    salvaged = service.recover_attempt_work(request)
    before = salvaged.observation.observation_fingerprint
    assert service.recover_attempt_work(request).observation.observation_fingerprint == before


def test_s5c_38_real_interruption_inspects_before_replay(postgres_database, git_repository, tmp_path) -> None:
    facts, _, service, request = _case(
        postgres_database, git_repository, tmp_path, dispatch_only=True,
    )
    (facts.prepared.preparation.workspace.workspace_path / "docs" / "attempt-recovery.md").write_text("implementation survived\n")
    result = service.recover_attempt_work(request)
    assert result.action.outcome is RecoveryActionOutcome.SALVAGED
    assert result.retry_attempt is None


def test_s5c_39_documentation_horizon_remains_valid(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    assert facts.spine.run.production_horizon.value == "DOCUMENTATION"


def test_s5c_40_no_s6_codex_scope_leakage(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    names = {table.name for table in metadata.tables.values()}
    assert not names.intersection({"codex_sessions", "provider_resumes", "recovery_daemons"})


def test_s5c_41_existing_full_regression(postgres_database, git_repository, tmp_path) -> None:
    facts, assessment, service, _ = _case(postgres_database, git_repository, tmp_path)
    result = service.retry_attempt_from_recovery(_retry_request(facts, assessment, tmp_path))
    assert result.retry_attempt.generation == 2
    assert len(runtime_tables) == 26
    assert "recovery_action_records" in metadata.tables
