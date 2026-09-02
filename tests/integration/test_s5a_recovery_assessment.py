from collections.abc import Iterator
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess

from alembic import command
from alembic.config import Config
import pytest
from pydantic import ValidationError
from sqlalchemy import func, inspect, select

from spg.application.completion import CompletionService
from spg.application.execution import ExecutionService
from spg.application.governance import CandidateGovernanceService
from spg.application.integration import RepositoryIntegrationService
from spg.application.preparation import PreparationService
from spg.application.recovery import RecoveryAssessmentService
from spg.application.runtime import RuntimeService
from spg.application.runtime_commit import RuntimeCommitService
from spg.application.verification import VerificationService
from spg.domain.execution import ProviderReportedOutcome
from spg.domain.governance import (
    CandidateAuthorizationScope,
    CandidateSealRequest,
    HumanAuthorizationRequest,
)
from spg.domain.integration import RepositoryEffectState, RepositoryIntegrationRequest
from spg.domain.preparation import (
    ContextArtifactSelection,
    ContextPackageRequest,
    ContextSemanticRole,
    ExecutorBinding,
)
from spg.domain.recovery import (
    AttemptRecoveryAssessmentRequest,
    RecoveryBarrierActive,
    RecoveryClassification,
    RecoveryGuidance,
    RecoverySubjectType,
    RepositoryRecoveryAssessmentRequest,
)
from spg.domain.runtime import (
    BootstrapRequest,
    CompletionContract,
    InitialRunRequest,
    ProductionHorizon,
    RuntimeInvariantViolation,
    RuntimeNotBootstrapped,
    WorkUnitCondition,
)
from spg.domain.runtime_commit import RuntimeCommitRequest
from spg.domain.verification import VerificationResultValue
from spg.infrastructure.git_integration import GitRepositoryIntegrationAdapter
from spg.infrastructure.persistence import Database, metadata
from spg.infrastructure.persistence.runtime_schema import (
    current_trusted_baseline_pointer,
    execution_attempts,
    plan_revisions,
    production_snapshots,
    recovery_assessments,
    repository_integration_effects,
    runtime_commits,
    runtime_tables,
)
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.providers.deterministic_executor import (
    DeterministicExecutionSpecification,
    DeterministicFileOperation,
    DeterministicFileOperationType,
    DeterministicTestExecutor,
)
from spg.providers.deterministic_verifier import DeterministicVerificationProvider


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TABLE_NAMES = {table.name for table in runtime_tables}
OBLIGATION = "recovery exact-subject verification"


@dataclass(frozen=True)
class AttemptFacts:
    database: Database
    repository: Path
    runtime: RuntimeService
    preparation: PreparationService
    execution: ExecutionService
    recovery: RecoveryAssessmentService
    baseline: object
    spine: object
    attempt: object
    prepared: object
    execution_result: object | None


@dataclass(frozen=True)
class RepositoryFacts:
    attempt: AttemptFacts
    candidate: object
    authorization: object
    effect: object
    recovery: RecoveryAssessmentService
    recovery_request: RepositoryRecoveryAssessmentRequest
    runtime_commit_service: RuntimeCommitService
    runtime_commit_request: RuntimeCommitRequest


class NoMutationGitAdapter:
    def __init__(self) -> None:
        self.delegate = GitRepositoryIntegrationAdapter()

    def read_ref(self, repository_path, repository_ref):
        return self.delegate.read_ref(repository_path, repository_ref)

    def commit_exists(self, repository_path, commit_identity):
        return self.delegate.commit_exists(repository_path, commit_identity)

    def read_commit_tree(self, repository_path, commit_identity):
        return self.delegate.read_commit_tree(repository_path, commit_identity)

    def compare_and_swap_ref(self, *args, **kwargs):
        return True


def _migration_config(database: Database) -> Config:
    os.environ["SPG_DATABASE_URL"] = database.engine.url.render_as_string(
        hide_password=False
    )
    return Config(PROJECT_ROOT / "alembic.ini")


@pytest.fixture(autouse=True)
def clean_runtime_schema(postgres_database: Database) -> Iterator[None]:
    previous_database_url = os.environ.get("SPG_DATABASE_URL")
    command.upgrade(_migration_config(postgres_database), "head")
    _truncate_runtime(postgres_database)
    try:
        yield
    finally:
        command.upgrade(_migration_config(postgres_database), "head")
        _truncate_runtime(postgres_database)
        if previous_database_url is None:
            os.environ.pop("SPG_DATABASE_URL", None)
        else:
            os.environ["SPG_DATABASE_URL"] = previous_database_url


@pytest.fixture
def git_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "governed-repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "docs").mkdir()
    (repository / "AI_context.md").write_text("baseline context\n", encoding="utf-8")
    (repository / "docs" / "contract.md").write_text(
        "execution contract\n", encoding="utf-8"
    )
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    return repository


def _build_attempt(
    database: Database,
    repository: Path,
    tmp_path: Path,
    *,
    label: str = "recovery",
    outcome: ProviderReportedOutcome = ProviderReportedOutcome.SUCCESS,
    changes: bool = True,
    dispatch_only: bool = False,
    execute: bool = True,
    completion_contract: CompletionContract | None = None,
) -> AttemptFacts:
    runtime = RuntimeService(database)
    preparation = PreparationService(database)
    execution = ExecutionService(database, preparation=preparation)
    recovery = RecoveryAssessmentService(database)
    try:
        baseline = runtime.current_baseline()
    except RuntimeNotBootstrapped:
        baseline = runtime.bootstrap_trusted_baseline(
            BootstrapRequest(
                repository_path=repository,
                repository_identity="test://s5a-repository",
                repository_ref="refs/heads/main",
                authority_identity="architecture-lead:test",
                scope={"slice": "S5-A"},
            )
        ).snapshot
    spine = runtime.create_initial_runtime_spine(
        InitialRunRequest(
            intent_ref=f"intent:test:s5a:{label}",
            goal="Classify exact recovery Reality",
            production_horizon=ProductionHorizon.DOCUMENTATION,
            initial_work_unit_objective=f"Produce {label}",
            completion_contract=completion_contract
            or CompletionContract(
                required_outputs=(f"docs/{label}.md",),
                required_changes=(f"docs/{label}.md",),
                verification_obligations=(OBLIGATION,),
            ),
        )
    )
    attempt = runtime.create_initial_attempt(spine.work_unit.id)
    package = preparation.assemble_context_package(
        spine.work_unit.id,
        repository,
        ContextPackageRequest(
            artifacts=(
                ContextArtifactSelection(
                    semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                    repository_relative_path="AI_context.md",
                ),
                ContextArtifactSelection(
                    semantic_role=ContextSemanticRole.EXECUTION_CONTRACT,
                    repository_relative_path="docs/contract.md",
                ),
            )
        ),
    )
    prepared = preparation.prepare_attempt(
        attempt.id,
        package.id,
        ExecutorBinding(
            binding_ref="binding:deterministic-documentation",
            capability_identity="capability:executor",
            profile_identity="profile:local-fvs",
        ),
        repository,
        tmp_path / "attempt-workspaces",
    )
    execution_result = None
    if dispatch_only:
        execution._persist_dispatch(preparation.prepared_execution_request(attempt.id))
    elif execute:
        operations = (
            (
                DeterministicFileOperation(
                    operation=DeterministicFileOperationType.CREATE,
                    repository_relative_path=f"docs/{label}.md",
                    content=f"{label} output\n",
                ),
            )
            if changes
            else ()
        )
        execution_result = execution.dispatch_and_observe(
            attempt.id,
            DeterministicTestExecutor(
                DeterministicExecutionSpecification(
                    operations=operations,
                    reported_outcome=outcome,
                    summary=f"deterministic {outcome.value} recovery evidence",
                )
            ),
        )
    return AttemptFacts(
        database=database,
        repository=repository,
        runtime=runtime,
        preparation=preparation,
        execution=execution,
        recovery=recovery,
        baseline=baseline,
        spine=spine,
        attempt=attempt,
        prepared=prepared,
        execution_result=execution_result,
    )


def _attempt_request(facts: AttemptFacts) -> AttemptRecoveryAssessmentRequest:
    return AttemptRecoveryAssessmentRequest(
        attempt_id=facts.attempt.id,
        expected_work_unit_id=facts.spine.work_unit.id,
        expected_generation=facts.attempt.generation,
    )


def _build_repository(
    database: Database,
    repository: Path,
    tmp_path: Path,
    *,
    mode: str,
) -> RepositoryFacts:
    attempt = _build_attempt(database, repository, tmp_path)
    completion = CompletionService(database, observer=attempt.execution.observer)
    verification = VerificationService(database, observer=attempt.execution.observer)
    governance = CandidateGovernanceService(database)
    completion_result = completion.evaluate_observation(
        attempt.execution_result.observation.id
    )
    proposed = verification.create_proposed_snapshot(completion_result.evaluation.id)
    verification.verify_obligation(
        proposed.id,
        OBLIGATION,
        DeterministicVerificationProvider(
            {OBLIGATION: VerificationResultValue.PASS}
        ),
    )
    satisfaction = verification.evaluate_admissibility(proposed.id)
    candidate = governance.seal_candidate(
        CandidateSealRequest(
            proposed_snapshot_id=proposed.id,
            production_admissibility_id=satisfaction.admissibility.id,
            expected_work_unit_version=satisfaction.work_unit.version,
        )
    )
    authorization = governance.authorize_candidate(
        HumanAuthorizationRequest(
            authority_identity="human:test",
            candidate_id=candidate.id,
            candidate_fingerprint=candidate.fingerprint,
            scope=CandidateAuthorizationScope(
                repository_identity=candidate.repository_identity,
                target_authoritative_ref=candidate.target_authoritative_ref,
                expected_source_repository_revision=(
                    candidate.expected_source_repository_revision
                ),
                proposed_repository_revision=candidate.proposed_commit_identity,
            ),
        )
    )
    integration_request = RepositoryIntegrationRequest(
        candidate_id=candidate.id,
        candidate_fingerprint=candidate.fingerprint,
        human_authorization_id=authorization.id,
    )
    if mode.startswith("prepared"):
        integration = RepositoryIntegrationService(
            database,
            git=NoMutationGitAdapter(),
        )
    else:
        integration = RepositoryIntegrationService(database)
    effect = integration.integrate_repository_candidate(integration_request).effect
    if mode == "prepared-proposed":
        _git(
            repository,
            "update-ref",
            candidate.target_authoritative_ref,
            candidate.proposed_commit_identity,
        )
    elif mode == "prepared-third":
        (repository / "third-reality.md").write_text("third\n", encoding="utf-8")
        _git(repository, "add", "third-reality.md")
        _git(repository, "commit", "-m", "third repository reality")

    runtime_commit_service = RuntimeCommitService(database)
    runtime_commit_request = RuntimeCommitRequest(
        candidate_id=candidate.id,
        candidate_fingerprint=candidate.fingerprint,
        human_authorization_id=authorization.id,
        repository_integration_effect_id=effect.id,
    )
    if mode == "committed":
        runtime_commit_service.commit_runtime_candidate(runtime_commit_request)
    recovery = RecoveryAssessmentService(database)
    recovery_request = RepositoryRecoveryAssessmentRequest(
        repository_integration_effect_id=effect.id,
        expected_operation_fingerprint=effect.operation_fingerprint,
    )
    return RepositoryFacts(
        attempt=attempt,
        candidate=candidate,
        authorization=authorization,
        effect=effect,
        recovery=recovery,
        recovery_request=recovery_request,
        runtime_commit_service=runtime_commit_service,
        runtime_commit_request=runtime_commit_request,
    )


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _truncate_runtime(database: Database) -> None:
    table_names = ", ".join(f'"{name}"' for name in RUNTIME_TABLE_NAMES)
    with database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {table_names} CASCADE")


def _count(database: Database, table) -> int:
    with database.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(table))


def test_s5a_migration_downgrade_and_reupgrade(postgres_database: Database) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260829_08")
    assert "recovery_assessments" not in inspect(postgres_database.engine).get_table_names()
    command.upgrade(config, "head")
    assert "recovery_assessments" in inspect(postgres_database.engine).get_table_names()


def test_s5a_01_assessment_binds_exact_subject(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path)
    assessment = facts.recovery.assess_recovery(_attempt_request(facts))
    assert assessment.subject_type is RecoverySubjectType.ATTEMPT
    assert assessment.subject_identity == str(facts.attempt.id)
    with pytest.raises(RuntimeInvariantViolation, match="exact Attempt lineage"):
        facts.recovery.assess_recovery(
            _attempt_request(facts).model_copy(update={"expected_generation": 2})
        )


def test_s5a_02_assessment_basis_is_immutable(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path)
    assessment = facts.recovery.assess_recovery(_attempt_request(facts))
    with pytest.raises(ValidationError):
        assessment.classification = RecoveryClassification.DIVERGED


def test_s5a_03_same_basis_is_idempotent(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path)
    first = facts.recovery.assess_recovery(_attempt_request(facts))
    repeated = facts.recovery.assess_recovery(_attempt_request(facts))
    assert repeated.id == first.id
    assert _count(postgres_database, recovery_assessments) == 1


def test_s5a_04_changed_observation_creates_new_assessment(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_repository(postgres_database, git_repository, tmp_path, mode="prepared-expected")
    first = facts.recovery.assess_recovery(facts.recovery_request)
    _git(
        git_repository,
        "update-ref",
        facts.candidate.target_authoritative_ref,
        facts.candidate.proposed_commit_identity,
    )
    changed = facts.recovery.assess_recovery(facts.recovery_request)
    assert changed.id != first.id
    assert changed.basis_fingerprint != first.basis_fingerprint


def test_s5a_05_provider_success_does_not_define_reality(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path, changes=False)
    assessment = facts.recovery.assess_recovery(_attempt_request(facts))
    assert assessment.observed_facts["provider_outcome"] == "SUCCESS"
    assert assessment.classification is RecoveryClassification.BLOCKED


def test_s5a_06_provider_failure_does_not_erase_observed_work(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(
        postgres_database,
        git_repository,
        tmp_path,
        outcome=ProviderReportedOutcome.FAILURE,
    )
    assessment = facts.recovery.assess_recovery(_attempt_request(facts))
    assert assessment.classification is RecoveryClassification.RECOVERABLE
    assert assessment.observed_facts["observed_change_count"] == 1
    assert assessment.observed_facts["work_product_reference_ids"]


def test_s5a_07_provider_unknown_remains_distinct(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(
        postgres_database,
        git_repository,
        tmp_path,
        outcome=ProviderReportedOutcome.UNKNOWN,
    )
    assessment = facts.recovery.assess_recovery(_attempt_request(facts))
    assert assessment.classification is RecoveryClassification.UNKNOWN
    assert assessment.observed_facts["observed_change_count"] == 1


def test_s5a_08_interrupted_attempt_history_preserved(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path, dispatch_only=True)
    before = facts.runtime.get_attempt(facts.attempt.id)
    assessment = facts.recovery.assess_recovery(_attempt_request(facts))
    assert assessment.classification is RecoveryClassification.UNKNOWN
    assert facts.runtime.get_attempt(facts.attempt.id) == before


def test_s5a_09_interrupted_attempt_not_rewritten_success(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path, dispatch_only=True)
    facts.recovery.assess_recovery(_attempt_request(facts))
    assert facts.runtime.get_attempt(facts.attempt.id).condition.value == "CREATED"


def test_s5a_10_stale_generation_cannot_regain_authority(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path, execute=False)
    newer = facts.runtime.retry_attempt(facts.attempt.id)
    assessment = facts.recovery.assess_recovery(_attempt_request(facts))
    assert assessment.classification is RecoveryClassification.STALE
    assert assessment.subject_is_current is False
    assert newer.generation == 2


def test_s5a_11_prepared_expected_ref_distinct(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_repository(postgres_database, git_repository, tmp_path, mode="prepared-expected")
    assessment = facts.recovery.assess_recovery(facts.recovery_request)
    assert assessment.classification is RecoveryClassification.RECOVERABLE
    assert assessment.differences == ("PREPARED_REF_AT_EXPECTED_SOURCE",)


def test_s5a_12_prepared_proposed_ref_external_convergence(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_repository(postgres_database, git_repository, tmp_path, mode="prepared-proposed")
    assessment = facts.recovery.assess_recovery(facts.recovery_request)
    assert assessment.guidance is RecoveryGuidance.RECORD_EXTERNAL_CONVERGENCE
    assert assessment.differences == ("EXTERNAL_CONVERGENCE_LOCAL_FACT_MISSING",)


def test_s5a_13_prepared_third_ref_diverged(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_repository(postgres_database, git_repository, tmp_path, mode="prepared-third")
    assessment = facts.recovery.assess_recovery(facts.recovery_request)
    assert assessment.classification is RecoveryClassification.DIVERGED
    assert assessment.guidance is RecoveryGuidance.ESCALATE_DIVERGENCE


def test_s5a_14_converged_runtime_commit_missing_recoverable(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_repository(postgres_database, git_repository, tmp_path, mode="converged")
    assessment = facts.recovery.assess_recovery(facts.recovery_request)
    assert assessment.classification is RecoveryClassification.RECOVERABLE
    assert assessment.guidance is RecoveryGuidance.RETRY_RUNTIME_COMMIT


def test_s5a_15_existing_runtime_commit_recognized(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_repository(postgres_database, git_repository, tmp_path, mode="committed")
    assessment = facts.recovery.assess_recovery(facts.recovery_request)
    assert assessment.classification is RecoveryClassification.COHERENT
    assert assessment.observed_facts["runtime_commit_exists"] is True


def test_s5a_16_no_blind_duplicate_runtime_commit(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_repository(postgres_database, git_repository, tmp_path, mode="committed")
    before = _count(postgres_database, runtime_commits)
    facts.recovery.assess_recovery(facts.recovery_request)
    facts.recovery.assess_recovery(facts.recovery_request)
    assert _count(postgres_database, runtime_commits) == before == 1


def test_s5a_17_current_authority_revalidated(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path, execute=False)
    facts.runtime.retry_attempt(facts.attempt.id)
    assessment = facts.recovery.assess_recovery(_attempt_request(facts))
    assert assessment.governed_basis["current_baseline_id"] == str(facts.baseline.id)
    assert assessment.governed_basis["current_attempt_generation"] == 2
    assert assessment.subject_is_current is False


def test_s5a_18_recovery_barrier_blocks_silent_progress(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path, dispatch_only=True)
    assessment = facts.recovery.assess_recovery(_attempt_request(facts))
    assert assessment.recovery_barrier is True
    with pytest.raises(RecoveryBarrierActive):
        facts.recovery.assert_forward_progress_allowed(assessment.id)


def test_s5a_19_unrelated_valid_history_preserved(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path, execute=False)
    newer = facts.runtime.retry_attempt(facts.attempt.id)
    before_baseline = facts.runtime.current_baseline()
    facts.recovery.assess_recovery(_attempt_request(facts))
    assert facts.runtime.current_baseline() == before_baseline
    assert facts.runtime.get_attempt(newer.id) == newer


def test_s5a_20_no_automatic_executor_retry(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path, dispatch_only=True)
    before = _count(postgres_database, execution_attempts)
    facts.recovery.assess_recovery(_attempt_request(facts))
    assert _count(postgres_database, execution_attempts) == before == 1


def test_s5a_21_no_workspace_mutation(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path)
    output = (
        facts.prepared.preparation.workspace.workspace_path
        / "docs"
        / "recovery.md"
    )
    before = output.read_bytes()
    facts.recovery.assess_recovery(_attempt_request(facts))
    assert output.read_bytes() == before


def test_s5a_22_no_git_ref_mutation(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_repository(postgres_database, git_repository, tmp_path, mode="prepared-proposed")
    before = _git(git_repository, "rev-parse", "refs/heads/main")
    facts.recovery.assess_recovery(facts.recovery_request)
    assert _git(git_repository, "rev-parse", "refs/heads/main") == before


def test_s5a_23_no_integration_effect_mutation(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_repository(postgres_database, git_repository, tmp_path, mode="prepared-proposed")
    before = facts.effect
    facts.recovery.assess_recovery(facts.recovery_request)
    with postgres_database.unit_of_work() as unit_of_work:
        after = RuntimeStore(unit_of_work.session).repository_integration_effect(before.id)
    assert after == before
    assert after.state is RepositoryEffectState.PREPARED


def test_s5a_24_no_runtime_commit(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_repository(postgres_database, git_repository, tmp_path, mode="converged")
    facts.recovery.assess_recovery(facts.recovery_request)
    assert _count(postgres_database, runtime_commits) == 0


def test_s5a_25_no_trusted_baseline_advancement(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_repository(postgres_database, git_repository, tmp_path, mode="converged")
    before = facts.attempt.runtime.current_baseline()
    facts.recovery.assess_recovery(facts.recovery_request)
    assert facts.attempt.runtime.current_baseline() == before
    assert _count(postgres_database, production_snapshots) == 1


def test_s5a_26_no_replanning(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path, dispatch_only=True)
    before = _count(postgres_database, plan_revisions)
    facts.recovery.assess_recovery(_attempt_request(facts))
    assert _count(postgres_database, plan_revisions) == before == 1


def test_s5a_27_no_compensation(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path, dispatch_only=True)
    facts.recovery.assess_recovery(_attempt_request(facts))
    assert not {"compensations", "sagas", "rollback_jobs"} & set(
        inspect(postgres_database.engine).get_table_names()
    )


def test_s5a_28_lowest_sufficient_guidance_exposed(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_repository(postgres_database, git_repository, tmp_path, mode="converged")
    assessment = facts.recovery.assess_recovery(facts.recovery_request)
    assert assessment.guidance is RecoveryGuidance.RETRY_RUNTIME_COMMIT
    assert assessment.safely_recoverable is True


def test_s5a_29_no_global_failed_collapse(postgres_database, git_repository, tmp_path) -> None:
    recoverable_facts = _build_attempt(
        postgres_database,
        git_repository,
        tmp_path,
        outcome=ProviderReportedOutcome.FAILURE,
    )
    recoverable = recoverable_facts.recovery.assess_recovery(
        _attempt_request(recoverable_facts)
    )
    facts = _build_attempt(
        postgres_database,
        git_repository,
        tmp_path,
        label="unknown",
        outcome=ProviderReportedOutcome.UNKNOWN,
    )
    unknown = facts.recovery.assess_recovery(_attempt_request(facts))
    assert "FAILED" not in {item.value for item in RecoveryClassification}
    assert recoverable.classification is RecoveryClassification.RECOVERABLE
    assert unknown.classification is RecoveryClassification.UNKNOWN


def test_s5a_30_documentation_horizon_remains_valid(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path)
    assessment = facts.recovery.assess_recovery(_attempt_request(facts))
    assert facts.spine.run.production_horizon is ProductionHorizon.DOCUMENTATION
    assert assessment.classification is RecoveryClassification.COHERENT


def test_s5a_31_no_later_recovery_scope_leakage(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path, dispatch_only=True)
    facts.recovery.assess_recovery(_attempt_request(facts))
    assert not {
        "recovery_jobs",
        "recovery_actions",
        "recovery_workers",
        "reconciliation_commands",
        "compensations",
    } & set(inspect(postgres_database.engine).get_table_names())


def test_s5a_32_existing_full_regression(postgres_database, git_repository, tmp_path) -> None:
    facts = _build_attempt(postgres_database, git_repository, tmp_path)
    assessment = facts.recovery.assess_recovery(_attempt_request(facts))
    assert "recovery_assessments" in metadata.tables
    assert len(runtime_tables) == 26
    assert _count(postgres_database, current_trusted_baseline_pointer) == 1
    assert assessment.classification is RecoveryClassification.COHERENT
    assert "v0.1" in (
        PROJECT_ROOT / "docs/architecture/system-architecture-baseline-v0.1.md"
    ).read_text(encoding="utf-8")
