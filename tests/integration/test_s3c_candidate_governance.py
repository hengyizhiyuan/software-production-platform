from collections.abc import Iterator
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from alembic import command
from alembic.config import Config
from pydantic import ValidationError
import pytest
from sqlalchemy import func, inspect, select, update

from spg.application.completion import CompletionService
from spg.application.execution import ExecutionService
from spg.application.governance import CandidateGovernanceService
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
    RepositoryRealityError,
    RuntimeInvariantViolation,
    RuntimeNotBootstrapped,
    RuntimeRecordNotFound,
    WorkUnitCondition,
)
from spg.domain.verification import VerificationResultValue
from spg.infrastructure.persistence import Database, OptimisticConcurrencyConflict, metadata
from spg.infrastructure.persistence.runtime_schema import (
    baseline_candidates,
    current_trusted_baseline_pointer,
    governance_records,
    human_authorizations,
    production_admissibility_records,
    production_runs,
    production_work_units,
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
OBLIGATION = "candidate exact-subject verification"


@dataclass(frozen=True)
class CandidateFacts:
    database: Database
    repository: Path
    runtime: RuntimeService
    governance: CandidateGovernanceService
    baseline: object
    spine: object
    attempt: object
    execution_result: object
    completion_result: object
    proposed_snapshot: object
    verification_record: object | None
    satisfaction_result: object


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
    label: str = "candidate",
    verification_result: VerificationResultValue | None = VerificationResultValue.PASS,
) -> CandidateFacts:
    runtime = RuntimeService(database)
    preparation = PreparationService(database)
    execution = ExecutionService(database, preparation=preparation)
    completion = CompletionService(database, observer=execution.observer)
    verification = VerificationService(database, observer=execution.observer)
    governance = CandidateGovernanceService(database)
    try:
        baseline = runtime.current_baseline()
    except RuntimeNotBootstrapped:
        baseline = runtime.bootstrap_trusted_baseline(
            BootstrapRequest(
                repository_path=repository,
                repository_identity="test://s3c-repository",
                repository_ref="refs/heads/main",
                authority_identity="architecture-lead:test",
                scope={"slice": "S3-C"},
            )
        ).snapshot
    contract = CompletionContract(
        required_outputs=(f"docs/{label}.md",),
        required_changes=(f"docs/{label}.md",),
        verification_obligations=(OBLIGATION,),
    )
    spine = runtime.create_initial_runtime_spine(
        InitialRunRequest(
            intent_ref=f"intent:test:s3c:{label}",
            goal="Seal exact governed documentation production",
            production_horizon=ProductionHorizon.DOCUMENTATION,
            initial_work_unit_objective=f"Produce {label}",
            completion_contract=contract,
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
            summary="deterministic S3-C execution",
        )
    )
    execution_result = execution.dispatch_and_observe(attempt.id, executor)
    completion_result = completion.evaluate_observation(execution_result.observation.id)
    proposed = verification.create_proposed_snapshot(completion_result.evaluation.id)
    verification_record = None
    if verification_result is not None:
        verification_record = verification.verify_obligation(
            proposed.id,
            OBLIGATION,
            DeterministicVerificationProvider({OBLIGATION: verification_result}),
        )
    satisfaction = verification.evaluate_admissibility(proposed.id)
    return CandidateFacts(
        database=database,
        repository=repository,
        runtime=runtime,
        governance=governance,
        baseline=baseline,
        spine=spine,
        attempt=attempt,
        execution_result=execution_result,
        completion_result=completion_result,
        proposed_snapshot=proposed,
        verification_record=verification_record,
        satisfaction_result=satisfaction,
    )


def _seal(facts: CandidateFacts):
    return facts.governance.seal_candidate(
        CandidateSealRequest(
            proposed_snapshot_id=facts.proposed_snapshot.id,
            production_admissibility_id=facts.satisfaction_result.admissibility.id,
            expected_work_unit_version=facts.satisfaction_result.work_unit.version,
        )
    )


def _scope(candidate) -> CandidateAuthorizationScope:
    return CandidateAuthorizationScope(
        repository_identity=candidate.repository_identity,
        target_authoritative_ref=candidate.target_authoritative_ref,
        expected_source_repository_revision=candidate.expected_source_repository_revision,
        proposed_repository_revision=candidate.proposed_commit_identity,
    )


def _authorize(facts: CandidateFacts, candidate, *, authority: str = "human:test"):
    return facts.governance.authorize_candidate(
        HumanAuthorizationRequest(
            authority_identity=authority,
            candidate_id=candidate.id,
            candidate_fingerprint=candidate.fingerprint,
            scope=_scope(candidate),
            rationale="exact governed candidate accepted for later integration",
        )
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


def test_s3c_migration_downgrade_and_reupgrade(postgres_database: Database) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260828_05")
    tables = set(inspect(postgres_database.engine).get_table_names())
    assert not {"baseline_candidates", "human_authorizations"} & tables
    command.upgrade(config, "head")
    assert {"baseline_candidates", "human_authorizations"} <= set(
        inspect(postgres_database.engine).get_table_names()
    )


def test_s3c_01_satisfied_pwu_required(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    with facts.database.engine.begin() as connection:
        connection.execute(
            update(production_work_units)
            .where(production_work_units.c.id == facts.spine.work_unit.id)
            .values(condition=WorkUnitCondition.PRODUCED.value)
        )
    with pytest.raises(RuntimeInvariantViolation, match="SATISFIED"):
        _seal(facts)


def test_s3c_02_exact_candidate_basis(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    candidate = _seal(facts)
    assert candidate.production_run_id == facts.spine.run.id
    assert candidate.satisfied_work_unit_ids == (facts.spine.work_unit.id,)
    assert candidate.completion_evaluation_ids == (facts.completion_result.evaluation.id,)
    assert candidate.production_admissibility_id == facts.satisfaction_result.admissibility.id
    assert len(candidate.fingerprint) == 64


def test_s3c_03_candidate_binds_snapshot_commit_tree(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    candidate = _seal(facts)
    assert candidate.proposed_snapshot_id == facts.proposed_snapshot.id
    assert candidate.proposed_commit_identity == facts.proposed_snapshot.proposed_commit_identity
    assert candidate.proposed_tree_identity == facts.proposed_snapshot.tree_identity


def test_s3c_04_candidate_binds_plan_and_source_baseline(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    candidate = _seal(facts)
    assert candidate.plan_revision_id == facts.spine.plan_revision.id
    assert candidate.source_baseline_id == facts.baseline.id


def test_s3c_05_candidate_binds_verification_and_admissibility(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    candidate = _seal(facts)
    assert candidate.verification_record_ids == (facts.verification_record.id,)
    assert candidate.production_admissibility_basis_fingerprint == facts.satisfaction_result.admissibility.basis_fingerprint


def test_s3c_06_candidate_binds_repository_target_and_source(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    candidate = _seal(facts)
    assert candidate.repository_identity == facts.baseline.repository_identity
    assert candidate.target_authoritative_ref == facts.baseline.repository_ref
    assert candidate.expected_source_repository_revision == facts.baseline.repository_revision


def test_s3c_07_candidate_does_not_advance_authoritative_ref(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before = _git(git_repository, "rev-parse", "refs/heads/main")
    candidate = _seal(facts)
    assert _git(git_repository, "rev-parse", "refs/heads/main") == before
    assert candidate.proposed_commit_identity != before


def test_s3c_08_candidate_does_not_advance_trusted_baseline(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before = facts.runtime.current_baseline()
    _seal(facts)
    assert facts.runtime.current_baseline() == before


def test_s3c_09_candidate_immutability(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    candidate = _seal(facts)
    with pytest.raises(ValidationError):
        candidate.fingerprint = "0" * 64
    assert facts.governance.candidate(candidate.id) == candidate


def test_s3c_10_candidate_same_basis_idempotency(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    assert _seal(facts) == _seal(facts)
    assert _count(postgres_database, baseline_candidates) == 1


def test_s3c_11_changed_basis_produces_different_candidate(postgres_database, git_repository, tmp_path) -> None:
    first = _build(postgres_database, git_repository, tmp_path, label="first")
    first_candidate = _seal(first)
    second = _build(postgres_database, git_repository, tmp_path, label="second")
    second_candidate = _seal(second)
    assert first_candidate.id != second_candidate.id
    assert first_candidate.fingerprint != second_candidate.fingerprint


def test_s3c_12_stale_plan_or_baseline_cannot_seal(postgres_database, git_repository, tmp_path) -> None:
    first = _build(postgres_database, git_repository, tmp_path, label="first")
    second = _build(postgres_database, git_repository, tmp_path, label="second")
    with first.database.engine.begin() as connection:
        connection.execute(
            update(production_runs)
            .where(production_runs.c.id == first.spine.run.id)
            .values(current_plan_revision_id=second.spine.plan_revision.id)
        )
    with pytest.raises(RuntimeInvariantViolation, match="stale"):
        _seal(first)


def test_s3c_13_diverged_repository_source_blocks_sealing(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    (git_repository / "divergence.md").write_text("new source\n", encoding="utf-8")
    _git(git_repository, "add", "divergence.md")
    _git(git_repository, "commit", "-m", "diverge source")
    with pytest.raises(RepositoryRealityError, match="authoritative repository ref moved"):
        _seal(facts)
    assert _count(postgres_database, baseline_candidates) == 0


def test_s3c_14_wrong_or_stale_verification_blocks_candidate(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    with facts.database.engine.begin() as connection:
        connection.execute(
            update(verification_records)
            .where(verification_records.c.id == facts.verification_record.id)
            .values(proposed_commit_identity="wrong-subject")
        )
    with pytest.raises(RuntimeInvariantViolation, match="Verification PASS"):
        _seal(facts)


def test_s3c_15_produced_alone_is_insufficient(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path, verification_result=None)
    assert facts.satisfaction_result.work_unit.condition is WorkUnitCondition.PRODUCED
    with pytest.raises(RuntimeInvariantViolation, match="SATISFIED|ADMISSIBLE"):
        _seal(facts)


def test_s3c_16_exact_human_authorization_binding(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    candidate = _seal(facts)
    authorization = _authorize(facts, candidate)
    assert authorization.candidate_id == candidate.id
    assert authorization.candidate_fingerprint == candidate.fingerprint
    assert authorization.authority_identity == "human:test"
    assert authorization.scope == _scope(candidate)


def test_s3c_17_no_approve_latest_semantics() -> None:
    with pytest.raises(ValidationError):
        HumanAuthorizationRequest.model_validate(
            {
                "authority_identity": "human:test",
                "scope": {
                    "repository_identity": "repo",
                    "target_authoritative_ref": "refs/heads/main",
                    "expected_source_repository_revision": "C100",
                    "proposed_repository_revision": "C101",
                },
            }
        )


def test_s3c_18_authorization_requires_exact_sealed_candidate(postgres_database) -> None:
    governance = CandidateGovernanceService(postgres_database)
    with pytest.raises(RuntimeRecordNotFound, match="Candidate not found"):
        governance.authorize_candidate(
            HumanAuthorizationRequest(
                authority_identity="human:test",
                candidate_id=uuid4(),
                candidate_fingerprint="a" * 64,
                scope=CandidateAuthorizationScope(
                    repository_identity="repo",
                    target_authoritative_ref="refs/heads/main",
                    expected_source_repository_revision="C100",
                    proposed_repository_revision="C101",
                ),
            )
        )


def test_s3c_19_authorization_scope_is_exact(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    candidate = _seal(facts)
    wrong_scope = _scope(candidate).model_copy(
        update={"proposed_repository_revision": "different"}
    )
    with pytest.raises(RuntimeInvariantViolation, match="scope"):
        facts.governance.authorize_candidate(
            HumanAuthorizationRequest(
                authority_identity="human:test",
                candidate_id=candidate.id,
                candidate_fingerprint=candidate.fingerprint,
                scope=wrong_scope,
            )
        )


def test_s3c_20_human_authority_cannot_change_production_facts(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        verification_result=VerificationResultValue.FAIL,
    )
    with pytest.raises(RuntimeInvariantViolation):
        _seal(facts)
    assert facts.satisfaction_result.work_unit.condition is WorkUnitCondition.PRODUCED
    assert _count(postgres_database, human_authorizations) == 0


def test_s3c_21_authorization_idempotency(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    candidate = _seal(facts)
    first = _authorize(facts, candidate)
    repeated = _authorize(facts, candidate)
    assert first == repeated
    assert _count(postgres_database, human_authorizations) == 1


def test_s3c_22_authorization_preserves_history(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    candidate = _seal(facts)
    first = _authorize(facts, candidate, authority="human:first")
    second = _authorize(facts, candidate, authority="human:second")
    assert first.id != second.id
    with facts.database.unit_of_work() as unit_of_work:
        records = RuntimeStore(unit_of_work.session).human_authorizations_for_candidate(candidate.id)
    assert {item.id for item in records} == {first.id, second.id}


def test_s3c_23_authorization_does_not_advance_repository_ref(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    candidate = _seal(facts)
    before = _git(git_repository, "rev-parse", "refs/heads/main")
    _authorize(facts, candidate)
    assert _git(git_repository, "rev-parse", "refs/heads/main") == before


def test_s3c_24_authorization_does_not_runtime_commit(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    candidate = _seal(facts)
    _authorize(facts, candidate)
    assert candidate.condition is CandidateCondition.SEALED
    assert not {"repository_integrations"} & set(
        inspect(postgres_database.engine).get_table_names()
    )
    assert _count(postgres_database, runtime_commits) == 0


def test_s3c_25_authorization_does_not_advance_trusted_baseline(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before = facts.runtime.current_baseline()
    _authorize(facts, _seal(facts))
    assert facts.runtime.current_baseline() == before


def test_s3c_26_pwu_remains_satisfied(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    _authorize(facts, _seal(facts))
    assert facts.runtime.inspect_run(facts.spine.run.id).work_unit.condition is WorkUnitCondition.SATISFIED


def test_s3c_27_candidate_and_authorization_atomicity(postgres_database, git_repository, tmp_path, monkeypatch) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    original = RuntimeStore.insert_transition
    with monkeypatch.context() as patcher:
        patcher.setattr(
            RuntimeStore,
            "insert_transition",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("injected history failure")),
        )
        with pytest.raises(RuntimeError, match="injected history failure"):
            _seal(facts)
    assert _count(postgres_database, baseline_candidates) == 0
    candidate = _seal(facts)
    with monkeypatch.context() as patcher:
        patcher.setattr(
            RuntimeStore,
            "insert_transition",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("injected authorization failure")),
        )
        with pytest.raises(RuntimeError, match="injected authorization failure"):
            _authorize(facts, candidate)
    assert _count(postgres_database, human_authorizations) == 0
    assert _count(postgres_database, governance_records) == 1
    assert RuntimeStore.insert_transition is original


def test_s3c_28_optimistic_concurrency_and_lineage_protection(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    request = CandidateSealRequest(
        proposed_snapshot_id=facts.proposed_snapshot.id,
        production_admissibility_id=facts.satisfaction_result.admissibility.id,
        expected_work_unit_version=facts.satisfaction_result.work_unit.version - 1,
    )
    with pytest.raises(OptimisticConcurrencyConflict):
        facts.governance.seal_candidate(request)
    facts.runtime.retry_attempt(facts.attempt.id)
    current = facts.runtime.inspect_run(facts.spine.run.id).work_unit
    with pytest.raises(RuntimeInvariantViolation, match="stale"):
        facts.governance.seal_candidate(
            request.model_copy(update={"expected_work_unit_version": current.version})
        )


def test_s3c_29_documentation_horizon_remains_valid(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path, label="decision-record")
    candidate = _seal(facts)
    assert facts.spine.run.production_horizon is ProductionHorizon.DOCUMENTATION
    assert candidate.condition is CandidateCondition.SEALED


def test_s3c_30_no_trust_score_or_guardian_ownership(postgres_database, git_repository, tmp_path) -> None:
    candidate = _seal(_build(postgres_database, git_repository, tmp_path))
    assert "trust_score" not in type(candidate).model_fields
    assert not {"trust_scores", "guardian_findings", "evidence_graph"} & set(
        inspect(postgres_database.engine).get_table_names()
    )


def test_s3c_31_no_s4_scope_leakage(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before_ref = _git(git_repository, "rev-parse", "refs/heads/main")
    before_baseline = facts.runtime.current_baseline()
    _authorize(facts, _seal(facts))
    tables = set(inspect(postgres_database.engine).get_table_names())
    assert not {
        "repository_integrations",
        "external_effects",
        "production_issues",
    } & tables
    assert _count(postgres_database, runtime_commits) == 0
    assert _git(git_repository, "rev-parse", "refs/heads/main") == before_ref
    assert facts.runtime.current_baseline() == before_baseline


def test_s3c_32_existing_regression_contracts_remain(postgres_database, git_repository, tmp_path) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    candidate = _seal(facts)
    authorization = _authorize(facts, candidate)
    assert {"baseline_candidates", "human_authorizations"} <= set(metadata.tables)
    assert len(runtime_tables) == 25
    assert _count(postgres_database, current_trusted_baseline_pointer) == 1
    assert _count(postgres_database, baseline_candidates) == 1
    assert _count(postgres_database, human_authorizations) == 1
    assert authorization.source_baseline_id == facts.baseline.id
    assert "v0.1" in (PROJECT_ROOT / "docs/architecture/system-architecture-baseline-v0.1.md").read_text(encoding="utf-8")
