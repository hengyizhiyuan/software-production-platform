from collections.abc import Iterator
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, inspect, select, update

from spg.application.completion import CompletionService
from spg.application.execution import ExecutionService
from spg.application.governance import CandidateGovernanceService
from spg.application.integration import RepositoryIntegrationService
from spg.application.preparation import PreparationService
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
from spg.domain.runtime import (
    BootstrapRequest,
    CompletionContract,
    InitialRunRequest,
    ProductionHorizon,
    RuntimeInvariantViolation,
    RuntimeNotBootstrapped,
    RuntimeRecordNotFound,
    SnapshotCondition,
    WorkUnitCondition,
)
from spg.domain.runtime_commit import RuntimeCommitRequest
from spg.domain.verification import VerificationResultValue
from spg.infrastructure.git_integration import GitRepositoryIntegrationAdapter
from spg.infrastructure.persistence import Database, metadata
from spg.infrastructure.persistence.runtime_schema import (
    baseline_candidates,
    current_trusted_baseline_pointer,
    human_authorizations,
    production_admissibility_records,
    production_snapshots,
    production_work_units,
    repository_integration_effects,
    runtime_commits,
    runtime_tables,
    transition_history,
    verification_records,
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
OBLIGATION = "runtime commit exact-subject verification"


@dataclass(frozen=True)
class RuntimeCommitFacts:
    database: Database
    repository: Path
    runtime: RuntimeService
    service: RuntimeCommitService
    baseline: object
    spine: object
    candidate: object
    authorization: object
    effect: object | None
    request: RuntimeCommitRequest | None
    integration: RepositoryIntegrationService
    integration_request: RepositoryIntegrationRequest


class ReadOnlyGitSpy:
    def __init__(self, *, wrong_tree: bool = False, missing_commit: bool = False):
        self.delegate = GitRepositoryIntegrationAdapter()
        self.wrong_tree = wrong_tree
        self.missing_commit = missing_commit
        self.mutation_calls = 0

    def read_ref(self, repository_path, repository_ref):
        return self.delegate.read_ref(repository_path, repository_ref)

    def commit_exists(self, repository_path, commit_identity):
        if self.missing_commit:
            return False
        return self.delegate.commit_exists(repository_path, commit_identity)

    def read_commit_tree(self, repository_path, commit_identity):
        if self.wrong_tree:
            return "wrong-tree"
        return self.delegate.read_commit_tree(repository_path, commit_identity)

    def compare_and_swap_ref(self, *args, **kwargs):
        self.mutation_calls += 1
        raise AssertionError("S4-B must not mutate a repository ref")


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


def _build(
    database: Database,
    repository: Path,
    tmp_path: Path,
    *,
    label: str = "runtime-commit",
    converge: bool = True,
    commit_git=None,
) -> RuntimeCommitFacts:
    runtime = RuntimeService(database)
    preparation = PreparationService(database)
    execution = ExecutionService(database, preparation=preparation)
    completion = CompletionService(database, observer=execution.observer)
    verification = VerificationService(database, observer=execution.observer)
    governance = CandidateGovernanceService(database)
    integration = RepositoryIntegrationService(database)
    service = RuntimeCommitService(database, git=commit_git)
    try:
        baseline = runtime.current_baseline()
    except RuntimeNotBootstrapped:
        baseline = runtime.bootstrap_trusted_baseline(
            BootstrapRequest(
                repository_path=repository,
                repository_identity="test://s4b-repository",
                repository_ref="refs/heads/main",
                authority_identity="architecture-lead:test",
                scope={"slice": "S4-B"},
            )
        ).snapshot
    spine = runtime.create_initial_runtime_spine(
        InitialRunRequest(
            intent_ref=f"intent:test:s4b:{label}",
            goal="Commit exact integrated documentation Reality",
            production_horizon=ProductionHorizon.DOCUMENTATION,
            initial_work_unit_objective=f"Produce {label}",
            completion_contract=CompletionContract(
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
    preparation.prepare_attempt(
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
    executor = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=(
                DeterministicFileOperation(
                    operation=DeterministicFileOperationType.CREATE,
                    repository_relative_path=f"docs/{label}.md",
                    content=f"{label} output\n",
                ),
            ),
            reported_outcome=ProviderReportedOutcome.SUCCESS,
            summary="deterministic S4-B execution",
        )
    )
    execution_result = execution.dispatch_and_observe(attempt.id, executor)
    completion_result = completion.evaluate_observation(execution_result.observation.id)
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
            rationale="authorize exact governed Candidate",
        )
    )
    integration_request = RepositoryIntegrationRequest(
        candidate_id=candidate.id,
        candidate_fingerprint=candidate.fingerprint,
        human_authorization_id=authorization.id,
    )
    effect = None
    request = None
    if converge:
        effect = integration.integrate_repository_candidate(integration_request).effect
        request = RuntimeCommitRequest(
            candidate_id=candidate.id,
            candidate_fingerprint=candidate.fingerprint,
            human_authorization_id=authorization.id,
            repository_integration_effect_id=effect.id,
        )
    return RuntimeCommitFacts(
        database=database,
        repository=repository,
        runtime=runtime,
        service=service,
        baseline=baseline,
        spine=spine,
        candidate=candidate,
        authorization=authorization,
        effect=effect,
        request=request,
        integration=integration,
        integration_request=integration_request,
    )


def _with_converged(facts: RuntimeCommitFacts) -> RuntimeCommitFacts:
    effect = facts.integration.integrate_repository_candidate(
        facts.integration_request
    ).effect
    request = RuntimeCommitRequest(
        candidate_id=facts.candidate.id,
        candidate_fingerprint=facts.candidate.fingerprint,
        human_authorization_id=facts.authorization.id,
        repository_integration_effect_id=effect.id,
    )
    return RuntimeCommitFacts(
        **{
            **facts.__dict__,
            "effect": effect,
            "request": request,
        }
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


def _move_pointer_away(facts: RuntimeCommitFacts) -> None:
    other_id = uuid4()
    with facts.database.unit_of_work() as unit_of_work:
        store = RuntimeStore(unit_of_work.session)
        pointer = store.current_pointer()
        store.insert_snapshot(
            {
                "id": other_id,
                "condition": SnapshotCondition.TRUSTED.value,
                "repository_identity": facts.candidate.repository_identity,
                "repository_ref": facts.candidate.target_authoritative_ref,
                "repository_revision": facts.candidate.proposed_commit_identity,
                "source_baseline_id": facts.baseline.id,
            }
        )
        store.update_baseline_pointer(
            pointer.version,
            other_id,
            expected_snapshot_id=facts.baseline.id,
        )
        unit_of_work.commit()


def test_s4b_migration_downgrade_and_reupgrade(postgres_database: Database) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260829_07")
    assert "runtime_commits" not in inspect(postgres_database.engine).get_table_names()
    command.upgrade(config, "head")
    assert "runtime_commits" in inspect(postgres_database.engine).get_table_names()


def test_s4b_01_sealed_candidate_required(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    with pytest.raises(RuntimeRecordNotFound, match="Candidate not found"):
        facts.service.commit_runtime_candidate(
            facts.request.model_copy(update={"candidate_id": uuid4()})
        )


def test_s4b_02_exact_human_authorization_required(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    with pytest.raises(RuntimeRecordNotFound, match="Authorization not found"):
        facts.service.commit_runtime_candidate(
            facts.request.model_copy(update={"human_authorization_id": uuid4()})
        )


def test_s4b_03_authorization_must_match_candidate_fingerprint(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    with facts.database.engine.begin() as connection:
        connection.execute(
            update(human_authorizations)
            .where(human_authorizations.c.id == facts.authorization.id)
            .values(candidate_fingerprint="0" * 64)
        )
    with pytest.raises(RuntimeInvariantViolation, match="Authorization"):
        facts.service.commit_runtime_candidate(facts.request)


def test_s4b_04_converged_repository_integration_required(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    with facts.database.engine.begin() as connection:
        connection.execute(
            update(repository_integration_effects)
            .where(repository_integration_effects.c.id == facts.effect.id)
            .values(state="PREPARED", converged_at=None)
        )
    with pytest.raises(RuntimeInvariantViolation, match="CONVERGED"):
        facts.service.commit_runtime_candidate(facts.request)


def test_s4b_05_integration_matches_exact_candidate_repository_ref(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    with facts.database.engine.begin() as connection:
        connection.execute(
            update(repository_integration_effects)
            .where(repository_integration_effects.c.id == facts.effect.id)
            .values(target_authoritative_ref="refs/heads/other")
        )
    with pytest.raises(RuntimeInvariantViolation, match="exact CONVERGED"):
        facts.service.commit_runtime_candidate(facts.request)


def test_s4b_06_authoritative_ref_currently_equals_proposed(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    _git(
        git_repository,
        "update-ref",
        facts.candidate.target_authoritative_ref,
        facts.candidate.expected_source_repository_revision,
    )
    with pytest.raises(RuntimeInvariantViolation, match="authoritative repository ref"):
        facts.service.commit_runtime_candidate(facts.request)


def test_s4b_07_candidate_proposed_commit_tree_revalidated(postgres_database, git_repository, tmp_path) -> None:
    spy = ReadOnlyGitSpy(wrong_tree=True)
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        commit_git=spy,
    )
    with pytest.raises(RuntimeInvariantViolation, match="tree does not match"):
        facts.service.commit_runtime_candidate(facts.request)


def test_s4b_08_current_baseline_equals_candidate_source(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    assert facts.runtime.current_baseline().id == facts.candidate.source_baseline_id
    result = facts.service.commit_runtime_candidate(facts.request)
    assert result.runtime_commit.source_baseline_id == facts.baseline.id


def test_s4b_09_stale_source_baseline_blocks_commit(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    _move_pointer_away(facts)
    with pytest.raises(RuntimeInvariantViolation, match="Source Baseline"):
        facts.service.commit_runtime_candidate(facts.request)
    assert _count(postgres_database, runtime_commits) == 0


def test_s4b_10_exact_verification_admissibility_basis_required(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    with facts.database.engine.begin() as connection:
        connection.execute(
            update(verification_records)
            .where(verification_records.c.id == facts.candidate.verification_record_ids[0])
            .values(result="FAIL")
        )
    with pytest.raises(RuntimeInvariantViolation, match="Verification basis"):
        facts.service.commit_runtime_candidate(facts.request)


def test_s4b_11_satisfied_pwu_required(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    with facts.database.engine.begin() as connection:
        connection.execute(
            update(production_work_units)
            .where(production_work_units.c.id == facts.spine.work_unit.id)
            .values(condition="PRODUCED")
        )
    with pytest.raises(RuntimeInvariantViolation, match="SATISFIED"):
        facts.service.commit_runtime_candidate(facts.request)


def test_s4b_12_new_trusted_baseline_created(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    result = facts.service.commit_runtime_candidate(facts.request)
    assert result.trusted_baseline.condition is SnapshotCondition.TRUSTED
    assert result.trusted_baseline.id != facts.baseline.id


def test_s4b_13_new_baseline_binds_exact_candidate(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    result = facts.service.commit_runtime_candidate(facts.request)
    record = result.runtime_commit
    assert record.candidate_id == facts.candidate.id
    assert record.candidate_fingerprint == facts.candidate.fingerprint
    assert record.new_baseline_id == result.trusted_baseline.id


def test_s4b_14_new_baseline_binds_exact_commit_tree(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    result = facts.service.commit_runtime_candidate(facts.request)
    assert result.trusted_baseline.repository_revision == facts.candidate.proposed_commit_identity
    assert result.runtime_commit.repository_tree_identity == facts.candidate.proposed_tree_identity


def test_s4b_15_old_trusted_baseline_remains_immutable(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before = facts.baseline
    facts.service.commit_runtime_candidate(facts.request)
    with facts.database.unit_of_work() as unit_of_work:
        after = RuntimeStore(unit_of_work.session).snapshot(before.id)
    assert after == before


def test_s4b_16_current_pointer_advances_source_to_new(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    result = facts.service.commit_runtime_candidate(facts.request)
    assert result.current_pointer.snapshot_id == result.trusted_baseline.id
    assert result.current_pointer.version == 1


def test_s4b_17_baseline_pointer_history_are_atomic(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    result = facts.service.commit_runtime_candidate(facts.request)
    with facts.database.unit_of_work() as unit_of_work:
        history = RuntimeStore(unit_of_work.session).transitions()
    assert _count(postgres_database, runtime_commits) == 1
    assert _count(postgres_database, production_snapshots) == 2
    assert result.current_pointer.snapshot_id == result.trusted_baseline.id
    assert {item.reason for item in history} >= {
        "EXACT_GOVERNED_REALITY_COMMITTED",
        "RUNTIME_COMMIT_BASELINE_ADVANCED",
    }


def test_s4b_18_injected_failure_rolls_back_entire_commit(postgres_database, git_repository, tmp_path, monkeypatch) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before = facts.runtime.current_baseline()
    monkeypatch.setattr(
        RuntimeStore,
        "insert_runtime_commit",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("injected Runtime Commit failure")
        ),
    )
    with pytest.raises(RuntimeError, match="injected Runtime Commit failure"):
        facts.service.commit_runtime_candidate(facts.request)
    assert facts.runtime.current_baseline() == before
    assert _count(postgres_database, production_snapshots) == 1
    assert _count(postgres_database, runtime_commits) == 0


def test_s4b_19_same_commit_retry_is_idempotent(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    first = facts.service.commit_runtime_candidate(facts.request)
    second = facts.service.commit_runtime_candidate(facts.request)
    assert second.idempotent_recognition is True
    assert second.runtime_commit.id == first.runtime_commit.id
    assert second.trusted_baseline.id == first.trusted_baseline.id


def test_s4b_20_duplicate_trusted_baseline_not_created(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    facts.service.commit_runtime_candidate(facts.request)
    facts.service.commit_runtime_candidate(facts.request)
    assert _count(postgres_database, production_snapshots) == 2
    assert _count(postgres_database, runtime_commits) == 1


def test_s4b_21_concurrent_candidate_same_source_cannot_overwrite(postgres_database, git_repository, tmp_path) -> None:
    first = _build(postgres_database, git_repository, tmp_path, label="candidate-a", converge=False)
    second = _build(postgres_database, git_repository, tmp_path, label="candidate-b", converge=False)
    first = _with_converged(first)
    _git(git_repository, "update-ref", "refs/heads/main", first.baseline.repository_revision)
    second = _with_converged(second)
    _git(git_repository, "update-ref", "refs/heads/main", first.candidate.proposed_commit_identity)
    first.service.commit_runtime_candidate(first.request)
    _git(git_repository, "update-ref", "refs/heads/main", second.candidate.proposed_commit_identity)
    with pytest.raises(RuntimeInvariantViolation, match="Source Baseline"):
        second.service.commit_runtime_candidate(second.request)
    assert _count(postgres_database, runtime_commits) == 1


def test_s4b_22_runtime_commit_does_not_mutate_repository_ref(postgres_database, git_repository, tmp_path) -> None:
    spy = ReadOnlyGitSpy()
    facts = _build(postgres_database, git_repository, tmp_path, commit_git=spy)
    before = _git(git_repository, "rev-parse", "refs/heads/main")
    facts.service.commit_runtime_candidate(facts.request)
    assert _git(git_repository, "rev-parse", "refs/heads/main") == before
    assert spy.mutation_calls == 0


def test_s4b_23_runtime_commit_does_not_merge_rebase_push(postgres_database, git_repository, tmp_path) -> None:
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", str(remote))
    _git(git_repository, "remote", "add", "origin", str(remote))
    spy = ReadOnlyGitSpy()
    facts = _build(postgres_database, git_repository, tmp_path, commit_git=spy)
    proposed = facts.candidate.proposed_commit_identity
    parents_before = _git(git_repository, "show", "-s", "--format=%P", proposed)
    facts.service.commit_runtime_candidate(facts.request)
    assert _git(git_repository, "show", "-s", "--format=%P", proposed) == parents_before
    assert _git(remote, "for-each-ref", "--format=%(refname)") == ""
    assert spy.mutation_calls == 0


def test_s4b_24_pwu_remains_satisfied(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    facts.service.commit_runtime_candidate(facts.request)
    assert facts.runtime.inspect_run(facts.spine.run.id).work_unit.condition is WorkUnitCondition.SATISFIED


def test_s4b_25_candidate_basis_remains_immutable(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before = facts.candidate
    facts.service.commit_runtime_candidate(facts.request)
    with facts.database.unit_of_work() as unit_of_work:
        after = RuntimeStore(unit_of_work.session).baseline_candidate(before.id)
    assert after == before


def test_s4b_26_human_authorization_remains_immutable(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before = facts.authorization
    facts.service.commit_runtime_candidate(facts.request)
    with facts.database.unit_of_work() as unit_of_work:
        after = RuntimeStore(unit_of_work.session).human_authorization(before.id)
    assert after == before


def test_s4b_27_repository_converged_before_runtime_commit(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    assert facts.effect.state is RepositoryEffectState.CONVERGED
    assert _git(git_repository, "rev-parse", "refs/heads/main") == facts.candidate.proposed_commit_identity
    assert facts.runtime.current_baseline() == facts.baseline
    assert _count(postgres_database, runtime_commits) == 0


def test_s4b_28_success_aligns_baseline_with_repository(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    result = facts.service.commit_runtime_candidate(facts.request)
    observed = _git(git_repository, "rev-parse", "refs/heads/main")
    assert result.trusted_baseline.repository_revision == observed
    assert observed == facts.candidate.proposed_commit_identity


def test_s4b_29_no_cross_system_exactly_once_claim(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    repository_before = _git(git_repository, "rev-parse", "refs/heads/main")
    first = facts.service.commit_runtime_candidate(facts.request)
    retry = facts.service.commit_runtime_candidate(facts.request)
    assert retry.idempotent_recognition is True
    assert retry.runtime_commit.id == first.runtime_commit.id
    assert _git(git_repository, "rev-parse", "refs/heads/main") == repository_before


def test_s4b_30_documentation_horizon_remains_valid(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path, label="decision-record")
    result = facts.service.commit_runtime_candidate(facts.request)
    assert facts.spine.run.production_horizon is ProductionHorizon.DOCUMENTATION
    assert result.trusted_baseline.repository_revision == facts.candidate.proposed_commit_identity


def test_s4b_31_no_s5_recovery_scope_leakage(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    facts.service.commit_runtime_candidate(facts.request)
    assert not {
        "reconciliation_jobs",
        "recovery_attempts",
        "compensations",
        "sagas",
        "distributed_transactions",
    } & set(inspect(postgres_database.engine).get_table_names())


def test_s4b_32_existing_full_regression(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    result = facts.service.commit_runtime_candidate(facts.request)
    assert "runtime_commits" in metadata.tables
    assert len(runtime_tables) == 26
    assert _count(postgres_database, current_trusted_baseline_pointer) == 1
    assert _count(postgres_database, production_admissibility_records) == 1
    assert _count(postgres_database, transition_history) > 0
    assert result.runtime_commit.repository_integration_effect_id == facts.effect.id
    assert "v0.1" in (
        PROJECT_ROOT / "docs/architecture/system-architecture-baseline-v0.1.md"
    ).read_text(encoding="utf-8")
