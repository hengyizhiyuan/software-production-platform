from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from alembic import command
import pytest
from sqlalchemy import func, inspect, select, update

from spg.application.reconciliation import RecoveryReconciliationService
from spg.domain.integration import RepositoryEffectState
from spg.domain.recovery import (
    RecoveryActionOutcome,
    RecoveryActionRequest,
    RecoveryAssessmentStale,
    RecoveryClassification,
    RecoveryGuidance,
)
from spg.domain.runtime import RuntimeInvariantViolation, RuntimeRecordNotFound
from spg.infrastructure.git_integration import GitRepositoryIntegrationAdapter
from spg.infrastructure.persistence import Database, metadata
from spg.infrastructure.persistence.runtime_schema import (
    baseline_candidates,
    current_trusted_baseline_pointer,
    execution_attempts,
    plan_revisions,
    production_snapshots,
    production_work_units,
    recovery_action_records,
    recovery_assessments,
    repository_integration_effects,
    runtime_commits,
    runtime_tables,
    transition_history,
    verification_records,
)
from spg.infrastructure.persistence.runtime_store import RuntimeStore
import test_s5a_recovery_assessment as s5a


pytestmark = pytest.mark.postgresql
clean_runtime_schema = s5a.clean_runtime_schema
git_repository = s5a.git_repository


class ReadOnlyGitSpy:
    def __init__(self, *, wrong_tree: bool = False) -> None:
        self.delegate = GitRepositoryIntegrationAdapter()
        self.wrong_tree = wrong_tree
        self.mutation_calls = 0

    def read_ref(self, repository_path, repository_ref):
        return self.delegate.read_ref(repository_path, repository_ref)

    def commit_exists(self, repository_path, commit_identity):
        return self.delegate.commit_exists(repository_path, commit_identity)

    def read_commit_tree(self, repository_path, commit_identity):
        if self.wrong_tree:
            return "wrong-tree"
        return self.delegate.read_commit_tree(repository_path, commit_identity)

    def compare_and_swap_ref(self, *args, **kwargs):
        self.mutation_calls += 1
        raise AssertionError("S5-B reconciliation must never mutate Git")


@dataclass(frozen=True)
class ReconciliationFacts:
    repository: object
    assessment: object
    request: RecoveryActionRequest
    service: RecoveryReconciliationService
    git: ReadOnlyGitSpy


def _facts(database, repository, tmp_path, *, mode: str, wrong_tree: bool = False):
    repository_facts = s5a._build_repository(
        database,
        repository,
        tmp_path,
        mode=mode,
    )
    assessment = repository_facts.recovery.assess_recovery(
        repository_facts.recovery_request
    )
    git = ReadOnlyGitSpy(wrong_tree=wrong_tree)
    service = RecoveryReconciliationService(database, git=git)
    return ReconciliationFacts(
        repository=repository_facts,
        assessment=assessment,
        request=RecoveryActionRequest(
            recovery_assessment_id=assessment.id,
            expected_assessment_fingerprint=assessment.basis_fingerprint,
        ),
        service=service,
        git=git,
    )


def _count(database: Database, table) -> int:
    with database.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(table))


def _advance_pointer_to_unrelated_baseline(database: Database, facts) -> UUID:
    unrelated = uuid4()
    with database.unit_of_work() as unit_of_work:
        store = RuntimeStore(unit_of_work.session)
        pointer = store.current_pointer()
        store.insert_snapshot(
            {
                "id": unrelated,
                "condition": "TRUSTED",
                "repository_identity": facts.repository.candidate.repository_identity,
                "repository_ref": facts.repository.candidate.target_authoritative_ref,
                "repository_revision": (
                    facts.repository.candidate.proposed_commit_identity
                ),
                "source_baseline_id": facts.repository.candidate.source_baseline_id,
            }
        )
        store.update_baseline_pointer(
            pointer.version,
            unrelated,
            expected_snapshot_id=pointer.snapshot_id,
        )
        unit_of_work.commit()
    return unrelated


def test_s5b_migration_downgrade_and_reupgrade(postgres_database: Database) -> None:
    config = s5a._migration_config(postgres_database)
    command.downgrade(config, "20260829_09")
    assert "recovery_action_records" not in inspect(postgres_database.engine).get_table_names()
    command.upgrade(config, "head")
    assert "recovery_action_records" in inspect(postgres_database.engine).get_table_names()


def test_s5b_01_exact_recovery_assessment_required(postgres_database) -> None:
    service = RecoveryReconciliationService(postgres_database)
    with pytest.raises(RuntimeRecordNotFound):
        service.record_external_convergence(
            RecoveryActionRequest(
                recovery_assessment_id=uuid4(),
                expected_assessment_fingerprint="0" * 64,
            )
        )


def test_s5b_02_assessment_fingerprint_must_match(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-proposed")
    with pytest.raises(RuntimeInvariantViolation, match="fingerprint"):
        facts.service.record_external_convergence(
            RecoveryActionRequest(
                recovery_assessment_id=facts.assessment.id,
                expected_assessment_fingerprint="f" * 64,
            )
        )


def test_s5b_03_historical_assessment_remains_immutable(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-proposed")
    before = facts.assessment
    facts.service.record_external_convergence(facts.request)
    assert facts.repository.recovery.assessment(before.id) == before


def test_s5b_04_changed_reality_makes_old_assessment_non_actionable(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-proposed")
    (git_repository / "changed-after-assessment.md").write_text("changed\n")
    s5a._git(git_repository, "add", "changed-after-assessment.md")
    s5a._git(git_repository, "commit", "-m", "change after recovery assessment")
    with pytest.raises(RecoveryAssessmentStale):
        facts.service.record_external_convergence(facts.request)


def test_s5b_05_external_convergence_requires_matching_guidance(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-expected")
    assert facts.assessment.guidance is RecoveryGuidance.REOBSERVE
    with pytest.raises(RuntimeInvariantViolation, match="requested action"):
        facts.service.record_external_convergence(facts.request)


def test_s5b_06_prepared_effect_required(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    assert facts.repository.effect.state is RepositoryEffectState.CONVERGED
    with pytest.raises(RuntimeInvariantViolation):
        facts.service.record_external_convergence(facts.request)


def test_s5b_07_observed_ref_must_equal_exact_proposed_revision(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-proposed")
    s5a._git(
        git_repository,
        "update-ref",
        facts.repository.candidate.target_authoritative_ref,
        facts.repository.candidate.expected_source_repository_revision,
    )
    with pytest.raises(RecoveryAssessmentStale):
        facts.service.record_external_convergence(facts.request)


def test_s5b_08_observed_commit_tree_must_match_candidate(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(
        postgres_database,
        git_repository,
        tmp_path,
        mode="prepared-proposed",
        wrong_tree=True,
    )
    with pytest.raises(RecoveryAssessmentStale):
        facts.service.record_external_convergence(facts.request)


def test_s5b_09_exact_candidate_authorization_lineage_required(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-proposed")
    with postgres_database.engine.begin() as connection:
        connection.execute(
            update(baseline_candidates)
            .where(baseline_candidates.c.id == facts.repository.candidate.id)
            .values(fingerprint="a" * 64)
        )
    with pytest.raises(RecoveryAssessmentStale):
        facts.service.record_external_convergence(facts.request)


def test_s5b_10_prepared_proposed_ref_recovers_converged(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-proposed")
    result = facts.service.record_external_convergence(facts.request)
    assert result.effect.state is RepositoryEffectState.CONVERGED
    assert result.action.outcome is RecoveryActionOutcome.APPLIED


def test_s5b_11_convergence_recovery_does_not_mutate_git(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-proposed")
    before = s5a._git(git_repository, "rev-parse", "refs/heads/main")
    facts.service.record_external_convergence(facts.request)
    assert s5a._git(git_repository, "rev-parse", "refs/heads/main") == before
    assert facts.git.mutation_calls == 0


def test_s5b_12_convergence_recovery_is_locally_atomic(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-proposed")
    result = facts.service.record_external_convergence(facts.request)
    assert _count(postgres_database, recovery_action_records) == 1
    with postgres_database.unit_of_work() as unit_of_work:
        reasons = {item.reason for item in RuntimeStore(unit_of_work.session).transitions()}
    assert result.effect.state is RepositoryEffectState.CONVERGED
    assert "RECOVERY_INDEPENDENT_REALITY_CONFIRMED" in reasons
    assert "EXTERNAL_CONVERGENCE_RECORDED_LOCALLY" in reasons


def test_s5b_13_injected_persistence_failure_leaves_effect_prepared(postgres_database, git_repository, tmp_path, monkeypatch) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-proposed")
    monkeypatch.setattr(
        RuntimeStore,
        "insert_recovery_action",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("injected recovery failure")),
    )
    with pytest.raises(RuntimeError, match="injected recovery failure"):
        facts.service.record_external_convergence(facts.request)
    assert facts.repository.recovery.assess_recovery(facts.repository.recovery_request).guidance is RecoveryGuidance.RECORD_EXTERNAL_CONVERGENCE
    assert _count(postgres_database, recovery_action_records) == 0


def test_s5b_14_duplicate_convergence_recovery_is_idempotent(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-proposed")
    first = facts.service.record_external_convergence(facts.request)
    second = facts.service.record_external_convergence(facts.request)
    assert second.idempotent_recognition is True
    assert second.action.id == first.action.id
    assert _count(postgres_database, recovery_action_records) == 1


def test_s5b_15_prepared_expected_ref_does_not_retry_cas(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-expected")
    with pytest.raises(RuntimeInvariantViolation):
        facts.service.record_external_convergence(facts.request)
    assert facts.git.mutation_calls == 0
    assert facts.repository.recovery.assess_recovery(facts.repository.recovery_request).guidance is RecoveryGuidance.REOBSERVE


def test_s5b_16_prepared_third_ref_does_not_recover(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-third")
    with pytest.raises(RuntimeInvariantViolation):
        facts.service.record_external_convergence(facts.request)
    assert facts.repository.recovery.assess_recovery(facts.repository.recovery_request).classification is RecoveryClassification.DIVERGED


def test_s5b_17_divergence_remains_escalated_blocked(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-third")
    assert facts.assessment.guidance is RecoveryGuidance.ESCALATE_DIVERGENCE
    assert facts.assessment.recovery_barrier is True
    assert _count(postgres_database, recovery_action_records) == 0


def test_s5b_18_runtime_commit_requires_matching_guidance(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-proposed")
    with pytest.raises(RuntimeInvariantViolation, match="Runtime Commit reconciliation"):
        facts.service.retry_runtime_commit_from_recovery(facts.request)


def test_s5b_19_converged_integration_required(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-expected")
    with pytest.raises(RuntimeInvariantViolation):
        facts.service.retry_runtime_commit_from_recovery(facts.request)
    assert facts.repository.effect.state is RepositoryEffectState.PREPARED


def test_s5b_20_repository_ref_revalidated_before_runtime_commit_retry(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    s5a._git(
        git_repository,
        "update-ref",
        facts.repository.candidate.target_authoritative_ref,
        facts.repository.candidate.expected_source_repository_revision,
    )
    with pytest.raises(RecoveryAssessmentStale):
        facts.service.retry_runtime_commit_from_recovery(facts.request)


def test_s5b_21_commit_tree_revalidated_before_runtime_commit_retry(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged", wrong_tree=True)
    with pytest.raises(RecoveryAssessmentStale):
        facts.service.retry_runtime_commit_from_recovery(facts.request)


def test_s5b_22_source_trusted_baseline_must_still_be_current(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    _advance_pointer_to_unrelated_baseline(postgres_database, facts)
    with pytest.raises(RecoveryAssessmentStale):
        facts.service.retry_runtime_commit_from_recovery(facts.request)


def test_s5b_23_exact_candidate_verification_admissibility_required(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    verification_id = facts.repository.candidate.verification_record_ids[0]
    with postgres_database.engine.begin() as connection:
        connection.execute(
            update(verification_records)
            .where(verification_records.c.id == verification_id)
            .values(result="FAIL")
        )
    with pytest.raises(RuntimeInvariantViolation, match="Verification"):
        facts.service.retry_runtime_commit_from_recovery(facts.request)


def test_s5b_24_successful_recovery_runtime_commit_creates_exact_baseline(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    result = facts.service.retry_runtime_commit_from_recovery(facts.request)
    assert result.runtime_commit.repository_revision == facts.repository.candidate.proposed_commit_identity
    assert _count(postgres_database, production_snapshots) == 2


def test_s5b_25_successful_recovery_advances_pointer_exactly_once(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    first = facts.service.retry_runtime_commit_from_recovery(facts.request)
    second = facts.service.retry_runtime_commit_from_recovery(facts.request)
    with postgres_database.engine.connect() as connection:
        pointer = connection.execute(select(current_trusted_baseline_pointer)).mappings().one()
    assert pointer["snapshot_id"] == first.runtime_commit.new_baseline_id
    assert pointer["version"] == 1
    assert second.runtime_commit.id == first.runtime_commit.id


def test_s5b_26_recovery_runtime_commit_reuses_s4b_atomicity(postgres_database, git_repository, tmp_path, monkeypatch) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    monkeypatch.setattr(
        RuntimeStore,
        "insert_runtime_commit",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("injected Runtime Commit failure")),
    )
    with pytest.raises(RuntimeError, match="injected Runtime Commit failure"):
        facts.service.retry_runtime_commit_from_recovery(facts.request)
    assert _count(postgres_database, runtime_commits) == 0
    assert _count(postgres_database, production_snapshots) == 1


def test_s5b_27_runtime_commit_retry_is_idempotent(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    first = facts.service.retry_runtime_commit_from_recovery(facts.request)
    second = facts.service.retry_runtime_commit_from_recovery(facts.request)
    assert second.idempotent_recognition is True
    assert second.action.id == first.action.id


def test_s5b_28_existing_runtime_commit_recognized_as_no_action(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    direct = facts.repository.runtime_commit_service.commit_runtime_candidate(
        facts.repository.runtime_commit_request
    )
    result = facts.service.retry_runtime_commit_from_recovery(facts.request)
    assert result.action.outcome is RecoveryActionOutcome.NO_ACTION
    assert result.runtime_commit.id == direct.runtime_commit.id


def test_s5b_29_no_duplicate_trusted_baseline(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    facts.service.retry_runtime_commit_from_recovery(facts.request)
    facts.service.retry_runtime_commit_from_recovery(facts.request)
    assert _count(postgres_database, runtime_commits) == 1
    assert _count(postgres_database, production_snapshots) == 2


def test_s5b_30_stale_source_baseline_blocks_recovery_commit(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    unrelated = _advance_pointer_to_unrelated_baseline(postgres_database, facts)
    with pytest.raises(RecoveryAssessmentStale):
        facts.service.retry_runtime_commit_from_recovery(facts.request)
    with postgres_database.engine.connect() as connection:
        pointer = connection.execute(select(current_trusted_baseline_pointer)).mappings().one()
    assert pointer["snapshot_id"] == unrelated


def test_s5b_31_recovery_does_not_mutate_candidate_pwu_authorization(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    candidate_before = facts.repository.candidate
    work_unit_before = facts.repository.attempt.runtime.inspect_run(facts.repository.attempt.spine.run.id).work_unit
    authorization_before = facts.repository.authorization
    facts.service.retry_runtime_commit_from_recovery(facts.request)
    with postgres_database.unit_of_work() as unit_of_work:
        store = RuntimeStore(unit_of_work.session)
        assert store.baseline_candidate(candidate_before.id) == candidate_before
        assert store.work_unit(work_unit_before.id) == work_unit_before
        assert store.human_authorization(authorization_before.id) == authorization_before


def test_s5b_32_recovery_does_not_replan(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    before = _count(postgres_database, plan_revisions)
    facts.service.retry_runtime_commit_from_recovery(facts.request)
    assert _count(postgres_database, plan_revisions) == before


def test_s5b_33_recovery_does_not_create_retry_attempt(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    before = _count(postgres_database, execution_attempts)
    facts.service.retry_runtime_commit_from_recovery(facts.request)
    assert _count(postgres_database, execution_attempts) == before


def test_s5b_34_recovery_does_not_mutate_workspace(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    before = s5a._git(git_repository, "status", "--porcelain")
    facts.service.retry_runtime_commit_from_recovery(facts.request)
    assert s5a._git(git_repository, "status", "--porcelain") == before
    assert facts.git.mutation_calls == 0


def test_s5b_35_no_compensation_saga_or_general_workflow(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    facts.service.retry_runtime_commit_from_recovery(facts.request)
    names = {table.name for table in runtime_tables}
    assert not names.intersection({"sagas", "compensations", "recovery_jobs", "recovery_workflows"})


def test_s5b_36_recovery_barrier_not_erased_by_rewriting_history(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="prepared-proposed")
    assert facts.assessment.recovery_barrier is True
    facts.service.record_external_convergence(facts.request)
    historical = facts.repository.recovery.assessment(facts.assessment.id)
    assert historical.recovery_barrier is True
    assert historical.guidance is RecoveryGuidance.RECORD_EXTERNAL_CONVERGENCE


def test_s5b_37_documentation_horizon_remains_valid(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    facts.service.retry_runtime_commit_from_recovery(facts.request)
    assert facts.repository.attempt.spine.run.production_horizon.value == "DOCUMENTATION"


def test_s5b_38_no_s5c_or_s6_scope_leakage(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    facts.service.retry_runtime_commit_from_recovery(facts.request)
    names = {table.name for table in metadata.tables.values()}
    assert not names.intersection({"attempt_retries", "workspace_recoveries", "codex_sessions", "replans"})


def test_s5b_39_existing_full_regression_contract_remains(postgres_database, git_repository, tmp_path) -> None:
    facts = _facts(postgres_database, git_repository, tmp_path, mode="converged")
    result = facts.service.retry_runtime_commit_from_recovery(facts.request)
    assert result.runtime_commit is not None
    assert {"recovery_assessments", "recovery_action_records", "runtime_commits"} <= {table.name for table in runtime_tables}
    assert _count(postgres_database, recovery_assessments) >= 1
