from collections.abc import Callable, Iterator
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, inspect, select, update
from sqlalchemy.exc import IntegrityError

from spg.application.completion import CompletionService
from spg.application.execution import ExecutionService
from spg.application.governance import CandidateGovernanceService
from spg.application.integration import RepositoryIntegrationService
from spg.application.preparation import PreparationService
from spg.application.runtime import RuntimeService
from spg.application.verification import VerificationService
from spg.domain.execution import ProviderReportedOutcome
from spg.domain.governance import (
    CandidateAuthorizationScope,
    CandidateCondition,
    CandidateSealRequest,
    HumanAuthorizationRequest,
)
from spg.domain.integration import (
    RepositoryEffectState,
    RepositoryEffectType,
    RepositoryIntegrationRequest,
)
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
    WorkUnitCondition,
)
from spg.domain.verification import VerificationResultValue
from spg.infrastructure.git_integration import GitRepositoryIntegrationAdapter
from spg.infrastructure.persistence import Database, OptimisticConcurrencyConflict, metadata
from spg.infrastructure.persistence.runtime_schema import (
    baseline_candidates,
    current_trusted_baseline_pointer,
    human_authorizations,
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
OBLIGATION = "repository integration exact-subject verification"


@dataclass(frozen=True)
class IntegrationFacts:
    database: Database
    repository: Path
    runtime: RuntimeService
    integration: RepositoryIntegrationService
    baseline: object
    spine: object
    proposed_snapshot: object
    candidate: object
    authorization: object
    request: RepositoryIntegrationRequest


class DelegatingGitAdapter:
    def __init__(
        self,
        delegate: GitRepositoryIntegrationAdapter | None = None,
        *,
        before_cas: Callable[[], None] | None = None,
        mutate: bool = True,
        raise_before_cas: bool = False,
    ) -> None:
        self.delegate = delegate or GitRepositoryIntegrationAdapter()
        self.before_cas = before_cas
        self.mutate = mutate
        self.raise_before_cas = raise_before_cas
        self.read_ref_calls = 0
        self.cas_calls = 0

    def read_ref(self, repository_path, repository_ref):
        self.read_ref_calls += 1
        return self.delegate.read_ref(repository_path, repository_ref)

    def commit_exists(self, repository_path, commit_identity):
        return self.delegate.commit_exists(repository_path, commit_identity)

    def read_commit_tree(self, repository_path, commit_identity):
        return self.delegate.read_commit_tree(repository_path, commit_identity)

    def compare_and_swap_ref(
        self,
        repository_path,
        repository_ref,
        expected_old_revision,
        proposed_new_revision,
    ):
        self.cas_calls += 1
        if self.before_cas is not None:
            self.before_cas()
        if self.raise_before_cas:
            raise RuntimeError("injected failure before Git CAS")
        if not self.mutate:
            return True
        return self.delegate.compare_and_swap_ref(
            repository_path,
            repository_ref,
            expected_old_revision,
            proposed_new_revision,
        )


class InvalidCommitAdapter(DelegatingGitAdapter):
    def __init__(self, *, wrong_tree: bool = False) -> None:
        super().__init__()
        self.wrong_tree = wrong_tree

    def commit_exists(self, repository_path, commit_identity):
        return self.wrong_tree

    def read_commit_tree(self, repository_path, commit_identity):
        return "wrong-tree"


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
    git_adapter=None,
    label: str = "integration",
) -> IntegrationFacts:
    runtime = RuntimeService(database)
    preparation = PreparationService(database)
    execution = ExecutionService(database, preparation=preparation)
    completion = CompletionService(database, observer=execution.observer)
    verification = VerificationService(database, observer=execution.observer)
    governance = CandidateGovernanceService(database)
    integration = RepositoryIntegrationService(database, git=git_adapter)
    try:
        baseline = runtime.current_baseline()
    except RuntimeNotBootstrapped:
        baseline = runtime.bootstrap_trusted_baseline(
            BootstrapRequest(
                repository_path=repository,
                repository_identity="test://s4a-repository",
                repository_ref="refs/heads/main",
                authority_identity="architecture-lead:test",
                scope={"slice": "S4-A"},
            )
        ).snapshot
    spine = runtime.create_initial_runtime_spine(
        InitialRunRequest(
            intent_ref=f"intent:test:s4a:{label}",
            goal="Integrate an exact authorized documentation Candidate",
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
            summary="deterministic S4-A execution",
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
            rationale="authorize exact later repository integration",
        )
    )
    request = RepositoryIntegrationRequest(
        candidate_id=candidate.id,
        candidate_fingerprint=candidate.fingerprint,
        human_authorization_id=authorization.id,
    )
    return IntegrationFacts(
        database=database,
        repository=repository,
        runtime=runtime,
        integration=integration,
        baseline=baseline,
        spine=spine,
        proposed_snapshot=proposed,
        candidate=candidate,
        authorization=authorization,
        request=request,
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


def _stored_effect(database: Database):
    with database.unit_of_work() as unit_of_work:
        return unit_of_work.session.execute(
            select(repository_integration_effects)
        ).mappings().one()


def test_s4a_migration_downgrade_and_reupgrade(postgres_database: Database) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260828_06")
    assert "repository_integration_effects" not in inspect(
        postgres_database.engine
    ).get_table_names()
    command.upgrade(config, "head")
    assert "repository_integration_effects" in inspect(
        postgres_database.engine
    ).get_table_names()


def test_s4a_01_sealed_candidate_required(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    with pytest.raises(RuntimeRecordNotFound, match="Candidate not found"):
        facts.integration.integrate_repository_candidate(
            facts.request.model_copy(update={"candidate_id": uuid4()})
        )
    with pytest.raises(IntegrityError):
        with facts.database.engine.begin() as connection:
            connection.execute(
                update(baseline_candidates)
                .where(baseline_candidates.c.id == facts.candidate.id)
                .values(condition="DRAFT")
            )


def test_s4a_02_exact_human_authorization_required(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    with pytest.raises(RuntimeRecordNotFound, match="Authorization not found"):
        facts.integration.integrate_repository_candidate(
            facts.request.model_copy(update={"human_authorization_id": uuid4()})
        )


def test_s4a_03_authorization_matches_candidate_fingerprint(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    with pytest.raises(RuntimeInvariantViolation, match="fingerprint"):
        facts.integration.integrate_repository_candidate(
            facts.request.model_copy(update={"candidate_fingerprint": "0" * 64})
        )


def test_s4a_04_authorization_scope_is_exact(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    scope = facts.authorization.scope.model_dump(mode="json")
    scope["target_authoritative_ref"] = "refs/heads/other"
    with facts.database.engine.begin() as connection:
        connection.execute(
            update(human_authorizations)
            .where(human_authorizations.c.id == facts.authorization.id)
            .values(authorization_scope=scope)
        )
    with pytest.raises(RuntimeInvariantViolation, match="exact repository integration"):
        facts.integration.integrate_repository_candidate(facts.request)


def test_s4a_05_exact_proposed_commit_exists(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    service = RepositoryIntegrationService(
        postgres_database,
        git=InvalidCommitAdapter(),
    )
    with pytest.raises(RuntimeInvariantViolation, match="does not exist"):
        service.integrate_repository_candidate(facts.request)
    assert _count(postgres_database, repository_integration_effects) == 0


def test_s4a_06_exact_proposed_tree_matches(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    service = RepositoryIntegrationService(
        postgres_database,
        git=InvalidCommitAdapter(wrong_tree=True),
    )
    with pytest.raises(RuntimeInvariantViolation, match="tree does not match"):
        service.integrate_repository_candidate(facts.request)


def test_s4a_07_prepared_persisted_before_git_mutation(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)

    def assert_prepared() -> None:
        row = _stored_effect(postgres_database)
        assert row["state"] == RepositoryEffectState.PREPARED.value
        assert _git(git_repository, "rev-parse", "refs/heads/main") == facts.candidate.expected_source_repository_revision

    adapter = DelegatingGitAdapter(before_cas=assert_prepared)
    result = RepositoryIntegrationService(postgres_database, git=adapter).integrate_repository_candidate(facts.request)
    assert result.converged is True


def test_s4a_08_stable_operation_identity(postgres_database, git_repository, tmp_path) -> None:
    adapter = DelegatingGitAdapter()
    facts = _build(postgres_database, git_repository, tmp_path, git_adapter=adapter)
    first = facts.integration.integrate_repository_candidate(facts.request)
    repeated = facts.integration.integrate_repository_candidate(facts.request)
    assert first.effect.id == repeated.effect.id
    assert first.effect.operation_fingerprint == repeated.effect.operation_fingerprint
    assert adapter.cas_calls == 1
    assert _count(postgres_database, repository_integration_effects) == 1


def test_s4a_09_expected_source_ref_cas_success(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    result = facts.integration.integrate_repository_candidate(facts.request)
    assert result.cas_attempted is True
    assert _git(git_repository, "rev-parse", "refs/heads/main") == facts.candidate.proposed_commit_identity


def test_s4a_10_diverged_ref_blocks_cas(postgres_database, git_repository, tmp_path) -> None:
    adapter = DelegatingGitAdapter()
    facts = _build(postgres_database, git_repository, tmp_path, git_adapter=adapter)
    (git_repository / "diverged.md").write_text("diverged\n", encoding="utf-8")
    _git(git_repository, "add", "diverged.md")
    _git(git_repository, "commit", "-m", "diverge authoritative source")
    diverged = _git(git_repository, "rev-parse", "refs/heads/main")
    result = facts.integration.integrate_repository_candidate(facts.request)
    assert result.converged is False
    assert result.effect.state is RepositoryEffectState.PREPARED
    assert result.observed_repository_revision == diverged
    assert adapter.cas_calls == 0


def test_s4a_11_no_force_update(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    (git_repository / "unexpected.md").write_text("unexpected\n", encoding="utf-8")
    _git(git_repository, "add", "unexpected.md")
    _git(git_repository, "commit", "-m", "unexpected authority")
    unexpected = _git(git_repository, "rev-parse", "HEAD")
    facts.integration.integrate_repository_candidate(facts.request)
    assert _git(git_repository, "rev-parse", "HEAD") == unexpected


def test_s4a_12_no_merge_rebase_or_cherry_pick(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    result = facts.integration.integrate_repository_candidate(facts.request)
    parents = _git(git_repository, "show", "-s", "--format=%P", result.effect.proposed_repository_revision).split()
    assert parents == [facts.candidate.expected_source_repository_revision]
    assert _git(git_repository, "rev-parse", "HEAD") == facts.candidate.proposed_commit_identity


def test_s4a_13_independent_ref_observation_required(postgres_database, git_repository, tmp_path) -> None:
    adapter = DelegatingGitAdapter()
    facts = _build(postgres_database, git_repository, tmp_path, git_adapter=adapter)
    result = facts.integration.integrate_repository_candidate(facts.request)
    assert result.converged is True
    assert adapter.read_ref_calls >= 2


def test_s4a_14_command_success_alone_not_converged(postgres_database, git_repository, tmp_path) -> None:
    adapter = DelegatingGitAdapter(mutate=False)
    facts = _build(postgres_database, git_repository, tmp_path, git_adapter=adapter)
    result = facts.integration.integrate_repository_candidate(facts.request)
    assert result.cas_attempted is True
    assert result.converged is False
    assert result.effect.state is RepositoryEffectState.PREPARED


def test_s4a_15_observed_proposed_revision_converges(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    result = facts.integration.integrate_repository_candidate(facts.request)
    assert result.observed_repository_revision == facts.candidate.proposed_commit_identity
    assert result.effect.state is RepositoryEffectState.CONVERGED
    assert result.effect.converged_at is not None


def test_s4a_16_wrong_observed_revision_cannot_converge(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        git_adapter=DelegatingGitAdapter(mutate=False),
    )
    result = facts.integration.integrate_repository_candidate(facts.request)
    assert result.observed_repository_revision == facts.candidate.expected_source_repository_revision
    assert result.effect.state is RepositoryEffectState.PREPARED


def test_s4a_17_repository_integration_does_not_runtime_commit(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    facts.integration.integrate_repository_candidate(facts.request)
    assert _count(postgres_database, runtime_commits) == 0
    assert facts.candidate.condition is CandidateCondition.SEALED


def test_s4a_18_repository_integration_does_not_advance_baseline(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before = facts.runtime.current_baseline()
    facts.integration.integrate_repository_candidate(facts.request)
    assert facts.runtime.current_baseline() == before


def test_s4a_19_pwu_remains_satisfied(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    facts.integration.integrate_repository_candidate(facts.request)
    assert facts.runtime.inspect_run(facts.spine.run.id).work_unit.condition is WorkUnitCondition.SATISFIED


def test_s4a_20_candidate_basis_remains_immutable(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before = facts.candidate
    facts.integration.integrate_repository_candidate(facts.request)
    with facts.database.unit_of_work() as unit_of_work:
        after = RuntimeStore(unit_of_work.session).baseline_candidate(before.id)
    assert after == before


def test_s4a_21_authorization_remains_historical(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before = facts.authorization
    facts.integration.integrate_repository_candidate(facts.request)
    with facts.database.unit_of_work() as unit_of_work:
        after = RuntimeStore(unit_of_work.session).human_authorization(before.id)
    assert after == before


def test_s4a_22_no_remote_push(postgres_database, git_repository, tmp_path) -> None:
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", str(remote))
    _git(git_repository, "remote", "add", "origin", str(remote))
    facts = _build(postgres_database, git_repository, tmp_path)
    facts.integration.integrate_repository_candidate(facts.request)
    assert _git(remote, "for-each-ref", "--format=%(refname)") == ""


def test_s4a_23_failure_before_cas_leaves_ref_unchanged(postgres_database, git_repository, tmp_path) -> None:
    adapter = DelegatingGitAdapter(raise_before_cas=True)
    facts = _build(postgres_database, git_repository, tmp_path, git_adapter=adapter)
    before = _git(git_repository, "rev-parse", "HEAD")
    with pytest.raises(RuntimeError, match="before Git CAS"):
        facts.integration.integrate_repository_candidate(facts.request)
    assert _git(git_repository, "rev-parse", "HEAD") == before
    assert _stored_effect(postgres_database)["state"] == RepositoryEffectState.PREPARED.value


def test_s4a_24_post_cas_pre_converged_interruption_is_representable(postgres_database, git_repository, tmp_path, monkeypatch) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    monkeypatch.setattr(
        RuntimeStore,
        "mark_repository_effect_converged",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("injected post-CAS interruption")
        ),
    )
    with pytest.raises(RuntimeError, match="post-CAS interruption"):
        facts.integration.integrate_repository_candidate(facts.request)
    assert _git(git_repository, "rev-parse", "HEAD") == facts.candidate.proposed_commit_identity
    assert _stored_effect(postgres_database)["state"] == RepositoryEffectState.PREPARED.value


def test_s4a_25_post_cas_interruption_does_not_advance_baseline(postgres_database, git_repository, tmp_path, monkeypatch) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before = facts.runtime.current_baseline()
    monkeypatch.setattr(
        RuntimeStore,
        "mark_repository_effect_converged",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("interrupt")),
    )
    with pytest.raises(RuntimeError, match="interrupt"):
        facts.integration.integrate_repository_candidate(facts.request)
    assert facts.runtime.current_baseline() == before


def test_s4a_26_no_exactly_once_claim(postgres_database, git_repository, tmp_path, monkeypatch) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    original = RuntimeStore.mark_repository_effect_converged
    monkeypatch.setattr(
        RuntimeStore,
        "mark_repository_effect_converged",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("interrupt")),
    )
    with pytest.raises(RuntimeError):
        facts.integration.integrate_repository_candidate(facts.request)
    monkeypatch.setattr(RuntimeStore, "mark_repository_effect_converged", original)
    adapter = DelegatingGitAdapter()
    retry = RepositoryIntegrationService(postgres_database, git=adapter).integrate_repository_candidate(facts.request)
    assert retry.effect.state is RepositoryEffectState.PREPARED
    assert retry.converged is False
    assert adapter.cas_calls == 0


def test_s4a_27_optimistic_and_duplicate_operation_protection(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)

    def concurrent_observation() -> None:
        row = _stored_effect(postgres_database)
        with postgres_database.unit_of_work() as unit_of_work:
            RuntimeStore(unit_of_work.session).record_repository_effect_observation(
                row["id"],
                row["version"],
                facts.candidate.expected_source_repository_revision,
                row["prepared_at"],
            )
            unit_of_work.commit()

    service = RepositoryIntegrationService(
        postgres_database,
        git=DelegatingGitAdapter(before_cas=concurrent_observation),
    )
    with pytest.raises(OptimisticConcurrencyConflict):
        service.integrate_repository_candidate(facts.request)
    assert _count(postgres_database, repository_integration_effects) == 1


def test_s4a_28_documentation_horizon_remains_valid(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path, label="decision-record")
    result = facts.integration.integrate_repository_candidate(facts.request)
    assert facts.spine.run.production_horizon is ProductionHorizon.DOCUMENTATION
    assert result.effect.state is RepositoryEffectState.CONVERGED


def test_s4a_29_no_general_external_effect_platform(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    result = facts.integration.integrate_repository_candidate(facts.request)
    assert result.effect.effect_type is RepositoryEffectType.REPOSITORY_REF_ADVANCE
    assert not {"sagas", "effect_groups", "compensations", "workflow_jobs"} & set(
        inspect(postgres_database.engine).get_table_names()
    )


def test_s4a_30_no_s4b_scope_leakage(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before = facts.runtime.current_baseline()
    result = facts.integration.integrate_repository_candidate(facts.request)
    assert result.effect.state is RepositoryEffectState.CONVERGED
    assert facts.runtime.current_baseline() == before
    assert _count(postgres_database, runtime_commits) == 0


def test_s4a_31_existing_full_regression_contracts(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    result = facts.integration.integrate_repository_candidate(facts.request)
    assert "repository_integration_effects" in metadata.tables
    assert len(runtime_tables) == 26
    assert _count(postgres_database, current_trusted_baseline_pointer) == 1
    assert result.effect.state is RepositoryEffectState.CONVERGED
    assert "v0.1" in (
        PROJECT_ROOT / "docs/architecture/system-architecture-baseline-v0.1.md"
    ).read_text(encoding="utf-8")
