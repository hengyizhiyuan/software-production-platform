from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import subprocess

from alembic import command
from alembic.config import Config
from pydantic import ValidationError
import pytest
from sqlalchemy import func, inspect, select

from spg.application.execution import ExecutionService
from spg.application.maintenance_recovery import VerifiedMaintenanceRecoveryService
from spg.application.preparation import PreparationService
from spg.application.recovery import RecoveryAssessmentService
from spg.application.runtime import RuntimeService
from spg.domain.execution import ArtifactChangeType, ProviderReportedOutcome
from spg.domain.maintenance_recovery import (
    MaintenanceCheckEvidence,
    MaintenanceEvidenceResult,
    MaintenanceRecoveryAuthority,
    MaintenanceVerificationEvidence,
    MaintenanceVerificationSuiteEvidence,
    NewProductionLineageAdmission,
    VerifiedMaintenanceRecoveryRequest,
    maintenance_authority_fingerprint,
    maintenance_evidence_fingerprint,
)
from spg.domain.preparation import (
    ContextArtifactSelection,
    ContextPackageRequest,
    ContextSemanticRole,
    ExecutorBinding,
)
from spg.domain.recovery import (
    AttemptRecoveryAssessmentRequest,
    RecoveryClassification,
    RecoveryGuidance,
)
from spg.domain.runtime import (
    BootstrapRequest,
    CompletionContract,
    InitialRunRequest,
    PlanCondition,
    ProductionHorizon,
    RunCondition,
    RuntimeInvariantViolation,
    WorkUnitCondition,
)
from spg.infrastructure.git_maintenance import GitMaintenanceObserver
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_schema import (
    baseline_candidates,
    completion_evaluations,
    execution_attempts,
    maintenance_recovery_admissions,
    recovery_action_records,
    repository_integration_effects,
    runtime_commits,
    runtime_tables,
    verification_records,
)
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.providers.deterministic_executor import (
    DeterministicExecutionSpecification,
    DeterministicTestExecutor,
)


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TABLE_NAMES = {table.name for table in runtime_tables}
AUTHORITY_SCOPE = ("VERIFIED_MAINTENANCE_RECOVERY",)
GOVERNANCE_FINGERPRINT = "7" * 64


MR_TEST_MAP = {
    "MR-01": "test_mr_success_exact_authority_handoff_and_immutable_history",
    "MR-02": "test_mr_stale_pointer_or_lineage_version_rejected",
    "MR-03": "test_mr_git_target_tree_ref_ancestry_and_scope_are_exact",
    "MR-04": "test_mr_git_target_tree_ref_ancestry_and_scope_are_exact",
    "MR-05": "test_mr_git_target_tree_ref_ancestry_and_scope_are_exact",
    "MR-06": "test_mr_evidence_authority_and_raw_conversation_rejected",
    "MR-07": "test_mr_evidence_identity_and_failed_terminal_result",
    "MR-08": "test_mr_evidence_authority_and_raw_conversation_rejected",
    "MR-09": "test_mr_evidence_authority_and_raw_conversation_rejected",
    "MR-10": "test_mr_success_creates_no_ordinary_production_side_effects",
    "MR-11": "test_mr_git_is_read_only_and_second_observation_detects_movement",
    "MR-12": "test_mr_success_exact_authority_handoff_and_immutable_history",
    "MR-13": "test_mr_success_exact_authority_handoff_and_immutable_history",
    "MR-14": "test_mr_idempotent_exact_request_returns_same_logical_result",
    "MR-15": "test_mr_success_exact_authority_handoff_and_immutable_history",
    "MR-16": "test_mr_success_exact_authority_handoff_and_immutable_history",
    "MR-17": "test_mr_success_exact_authority_handoff_and_immutable_history",
    "MR-18": "test_mr_success_exact_authority_handoff_and_immutable_history",
    "MR-19": "test_mr_success_exact_authority_handoff_and_immutable_history",
    "MR-20": "test_mr_success_exact_authority_handoff_and_immutable_history",
    "MR-21": "test_mr_success_exact_authority_handoff_and_immutable_history",
    "MR-22": "test_mr_success_exact_authority_handoff_and_immutable_history",
    "MR-23": "test_mr_success_exact_authority_handoff_and_immutable_history",
    "MR-24": "test_mr_success_exact_authority_handoff_and_immutable_history",
    "MR-25": "test_mr_success_exact_authority_handoff_and_immutable_history",
    "MR-26": "test_mr_success_creates_no_ordinary_production_side_effects",
    "MR-27": "test_mr_atomic_failure_boundaries_roll_back_every_local_fact",
    "MR-28": "test_mr_idempotent_exact_request_returns_same_logical_result",
    "MR-29": "test_mr_competing_recovery_rejects_stale_pointer",
    "MR-30": "test_mr_material_work_blocks_supersession",
    "MR-31": "test_mr_success_creates_no_ordinary_production_side_effects",
    "MR-32": "test_mr_success_creates_no_ordinary_production_side_effects",
    "MR-33": "test_mr_atomic_failure_boundaries_roll_back_every_local_fact",
    "MR-34": "test_mr_migration_round_trip_and_schema_inventory",
}


@dataclass(frozen=True)
class RecoveryFacts:
    database: Database
    repository: Path
    runtime: RuntimeService
    baseline: object
    old_spine: object
    attempt: object
    dispatch: object
    report: object
    observation: object
    assessment: object
    target_commit: str
    target_tree: str
    request: VerifiedMaintenanceRecoveryRequest


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
    repository = tmp_path / "maintenance-repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "docs").mkdir()
    (repository / "AI_context.md").write_text("baseline context\n", encoding="utf-8")
    (repository / "docs" / "contract.md").write_text(
        "governance contract\n", encoding="utf-8"
    )
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    return repository


@pytest.fixture
def facts(postgres_database, git_repository, tmp_path) -> RecoveryFacts:
    return _build_facts(postgres_database, git_repository, tmp_path)


def _build_facts(database, repository, tmp_path) -> RecoveryFacts:
    runtime = RuntimeService(database)
    preparation = PreparationService(database)
    execution = ExecutionService(database, preparation=preparation)
    recovery = RecoveryAssessmentService(database)
    baseline = runtime.bootstrap_trusted_baseline(
        BootstrapRequest(
            repository_path=repository,
            repository_identity="test://s6c2-r4b",
            repository_ref="refs/heads/main",
            authority_identity="architecture-lead:test",
            scope={"slice": "S6-C2-R4-B"},
        )
    ).snapshot
    initial = runtime.create_initial_runtime_spine(
        InitialRunRequest(
            intent_ref="PI-S6C-DOGFOOD-001",
            goal="Produce the first governed dogfood artifact",
            production_horizon=ProductionHorizon.DOCUMENTATION,
            initial_work_unit_objective="Produce governed operator guide",
            completion_contract=CompletionContract(
                required_outputs=("docs/operations/operator-guide.md",),
                required_changes=("docs/operations/operator-guide.md",),
                verification_obligations=("operator guide is governed",),
            ),
        )
    )
    attempt = runtime.create_initial_attempt(initial.work_unit.id)
    package = preparation.assemble_context_package(
        initial.work_unit.id,
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
            binding_ref="binding:test-r4b",
            capability_identity="capability:test-executor",
            profile_identity="profile:test-only",
        ),
        repository,
        tmp_path / "attempt-workspaces",
    )
    execution_result = execution.dispatch_and_observe(
        attempt.id,
        DeterministicTestExecutor(
            DeterministicExecutionSpecification(
                operations=(),
                reported_outcome=ProviderReportedOutcome.UNKNOWN,
                summary="historical pre-provider transport failure",
            )
        ),
    )
    assessment = recovery.assess_recovery(
        AttemptRecoveryAssessmentRequest(
            attempt_id=attempt.id,
            expected_work_unit_id=initial.work_unit.id,
            expected_generation=1,
        )
    )
    assert assessment.classification is RecoveryClassification.UNKNOWN
    assert assessment.guidance is RecoveryGuidance.REOBSERVE
    assert assessment.recovery_barrier is True

    (repository / "src").mkdir()
    (repository / "src" / "maintenance.py").write_text(
        "TRANSPORT_ENCODING = 'utf-8'\n", encoding="utf-8"
    )
    _git(repository, "add", "src/maintenance.py")
    _git(repository, "commit", "-m", "verified maintenance repair")
    target_commit = _git(repository, "rev-parse", "HEAD")
    target_tree = _git(repository, "rev-parse", "HEAD^{tree}")
    old_spine = runtime.inspect_run(initial.run.id)
    request = _request(
        repository,
        baseline,
        old_spine,
        attempt,
        assessment,
        target_commit,
        target_tree,
        objective=old_spine.work_unit.objective,
        evidence_time=datetime.now(UTC),
    )
    return RecoveryFacts(
        database=database,
        repository=repository,
        runtime=runtime,
        baseline=baseline,
        old_spine=old_spine,
        attempt=attempt,
        dispatch=execution_result.dispatch,
        report=execution_result.provider_report,
        observation=execution_result.observation,
        assessment=assessment,
        target_commit=target_commit,
        target_tree=target_tree,
        request=request,
    )


def _request(
    repository,
    baseline,
    old_spine,
    attempt,
    assessment,
    target_commit,
    target_tree,
    *,
    objective,
    evidence_time,
    terminal_result=MaintenanceEvidenceResult.PASS,
):
    failed = 0 if terminal_result is MaintenanceEvidenceResult.PASS else 1
    suite = MaintenanceVerificationSuiteEvidence(
        suite_identity="S6-C2-R4-B MR-01-MR-34",
        command_identity="pytest focused-r4b",
        collected=34,
        selected=34,
        passed=34 - failed,
        failed=failed,
        skipped=0,
        deselected=0,
        terminal_result=terminal_result,
    )
    evidence_values = {
        "repository_identity": "test://s6c2-r4b",
        "authoritative_ref": "refs/heads/main",
        "target_commit": target_commit,
        "target_tree": target_tree,
        "accepted_changed_paths": ("src/maintenance.py",),
        "suites": (suite,),
        "focused_evidence": ("MR-01 through MR-34 deterministic evidence",),
        "checks": tuple(
            MaintenanceCheckEvidence(
                check_identity=name,
                command_identity=command,
                terminal_result=MaintenanceEvidenceResult.PASS,
            )
            for name, command in (
                ("compile", "python import validation"),
                ("diff", "git diff --check"),
                ("lock", "uv lock --check"),
                ("migration", "alembic downgrade/upgrade"),
            )
        ),
        "produced_at": evidence_time,
    }
    evidence_draft = MaintenanceVerificationEvidence.model_construct(
        **evidence_values, evidence_fingerprint="0" * 64
    )
    evidence = MaintenanceVerificationEvidence(
        **evidence_values,
        evidence_fingerprint=maintenance_evidence_fingerprint(evidence_draft),
    )
    purpose = "Admit verified UTF-8 maintenance repair"
    authority_values = {
        "authority_identity": "architecture-lead:test",
        "authorization_scope": AUTHORITY_SCOPE,
        "authorized_at": evidence_time,
        "old_trusted_baseline_id": baseline.id,
        "repository_identity": "test://s6c2-r4b",
        "authoritative_ref": "refs/heads/main",
        "target_commit": target_commit,
        "target_tree": target_tree,
        "maintenance_purpose": purpose,
        "approved_changed_paths": ("src/maintenance.py",),
        "maintenance_evidence_fingerprint": evidence.evidence_fingerprint,
        "recovery_assessment_id": assessment.id,
        "old_run_id": old_spine.run.id,
        "old_plan_revision_id": old_spine.plan_revision.id,
        "old_work_unit_id": old_spine.work_unit.id,
        "old_attempt_id": attempt.id,
        "new_lineage_objective": objective,
    }
    authority_draft = MaintenanceRecoveryAuthority.model_construct(
        **authority_values, authority_fingerprint="0" * 64
    )
    authority = MaintenanceRecoveryAuthority(
        **authority_values,
        authority_fingerprint=maintenance_authority_fingerprint(authority_draft),
    )
    return VerifiedMaintenanceRecoveryRequest(
        repository_path=repository,
        expected_old_trusted_baseline_id=baseline.id,
        expected_current_pointer_version=0,
        repository_identity="test://s6c2-r4b",
        authoritative_ref="refs/heads/main",
        target_maintenance_commit=target_commit,
        target_maintenance_tree=target_tree,
        maintenance_purpose=purpose,
        approved_changed_paths=("src/maintenance.py",),
        verification_evidence=evidence,
        authority=authority,
        recovery_assessment_id=assessment.id,
        expected_recovery_assessment_fingerprint=assessment.basis_fingerprint,
        old_run_id=old_spine.run.id,
        expected_old_run_version=old_spine.run.version,
        old_plan_revision_id=old_spine.plan_revision.id,
        expected_old_plan_version=old_spine.plan_revision.version,
        old_work_unit_id=old_spine.work_unit.id,
        expected_old_work_unit_version=old_spine.work_unit.version,
        old_attempt_id=attempt.id,
        governance_contract_snapshot_identity="S6-C1-GOVERNANCE-CONTRACT",
        governance_contract_snapshot_fingerprint=GOVERNANCE_FINGERPRINT,
        new_lineage=NewProductionLineageAdmission(
            intent_ref=old_spine.run.intent_ref,
            goal=old_spine.run.goal,
            production_horizon=old_spine.run.production_horizon,
            work_unit_objective=objective,
            completion_contract=old_spine.work_unit.completion_contract,
        ),
    )


def test_mr_traceability_map_is_complete_and_executable() -> None:
    assert set(MR_TEST_MAP) == {f"MR-{index:02d}" for index in range(1, 35)}
    assert all(
        name in globals() and callable(globals()[name])
        for name in MR_TEST_MAP.values()
    )


def test_mr_success_exact_authority_handoff_and_immutable_history(facts) -> None:
    attempt_before = facts.attempt.model_dump(mode="json")
    report_before = facts.report.model_dump(mode="json")
    observation_before = facts.observation.model_dump(mode="json")
    assessment_before = facts.assessment.model_dump(mode="json")
    service = VerifiedMaintenanceRecoveryService(facts.database)
    result = service.recover_lineage_after_verified_maintenance(facts.request)

    assert result.idempotent_recognition is False
    assert result.old_baseline == facts.baseline
    assert result.new_baseline.id != result.old_baseline.id
    assert result.new_baseline.repository_revision == facts.target_commit
    assert result.pointer.snapshot_id == result.new_baseline.id
    assert result.pointer.version == 1
    assert result.old_run.condition is RunCondition.SUPERSEDED
    assert result.old_plan_revision.condition is PlanCondition.SUPERSEDED
    assert result.old_work_unit.condition is WorkUnitCondition.SUPERSEDED
    assert result.new_lineage.run.id != result.old_run.id
    assert result.new_lineage.plan_revision.id != result.old_plan_revision.id
    assert result.new_lineage.work_unit.id != result.old_work_unit.id
    assert result.new_lineage.run.intent_ref == result.old_run.intent_ref
    assert result.new_lineage.run.source_baseline_id == result.new_baseline.id
    assert result.new_lineage.work_unit.condition is WorkUnitCondition.PROPOSED
    assert result.new_lineage.work_unit.current_execution_generation == 0
    assert result.admission.governance_contract_snapshot_fingerprint == GOVERNANCE_FINGERPRINT

    with facts.database.unit_of_work() as unit_of_work:
        store = RuntimeStore(unit_of_work.session)
        assert store.attempt(facts.attempt.id).model_dump(mode="json") == attempt_before
        assert store.provider_execution_report(facts.dispatch.id).model_dump(mode="json") == report_before
        assert store.repository_observation(facts.dispatch.id).model_dump(mode="json") == observation_before
        assert store.recovery_assessment(facts.assessment.id).model_dump(mode="json") == assessment_before
    service.assert_recovered_lineage_progress_allowed(result.new_lineage.run.id)
    with pytest.raises(RuntimeInvariantViolation):
        service.assert_recovered_lineage_progress_allowed(result.old_run.id)


def test_mr_success_creates_no_ordinary_production_side_effects(facts) -> None:
    before = _selected_counts(facts.database)
    result = VerifiedMaintenanceRecoveryService(facts.database).recover_lineage_after_verified_maintenance(
        facts.request
    )
    after = _selected_counts(facts.database)
    assert after == before == {
        "attempts": 1,
        "completion": 0,
        "verification": 0,
        "candidate": 0,
        "integration": 0,
        "runtime_commit": 0,
        "recovery_action": 0,
    }
    assert result.new_lineage.work_unit.current_execution_generation == 0


def test_mr_idempotent_exact_request_returns_same_logical_result(facts) -> None:
    service = VerifiedMaintenanceRecoveryService(facts.database)
    first = service.recover_lineage_after_verified_maintenance(facts.request)
    counts = _all_runtime_counts(facts.database)
    second = service.recover_lineage_after_verified_maintenance(facts.request)
    assert second.idempotent_recognition is True
    assert second.admission.id == first.admission.id
    assert second.new_baseline.id == first.new_baseline.id
    assert second.new_lineage == first.new_lineage
    assert _all_runtime_counts(facts.database) == counts


def test_mr_evidence_identity_and_failed_terminal_result(facts) -> None:
    same = _request(
        facts.repository,
        facts.baseline,
        facts.old_spine,
        facts.attempt,
        facts.assessment,
        facts.target_commit,
        facts.target_tree,
        objective=facts.old_spine.work_unit.objective,
        evidence_time=facts.request.verification_evidence.produced_at,
    )
    changed = _request(
        facts.repository,
        facts.baseline,
        facts.old_spine,
        facts.attempt,
        facts.assessment,
        facts.target_commit,
        facts.target_tree,
        objective=facts.old_spine.work_unit.objective,
        evidence_time=facts.request.verification_evidence.produced_at
        + timedelta(seconds=1),
    )
    assert same.verification_evidence.evidence_fingerprint == facts.request.verification_evidence.evidence_fingerprint
    assert changed.verification_evidence.evidence_fingerprint != facts.request.verification_evidence.evidence_fingerprint
    failed = _request(
        facts.repository,
        facts.baseline,
        facts.old_spine,
        facts.attempt,
        facts.assessment,
        facts.target_commit,
        facts.target_tree,
        objective=facts.old_spine.work_unit.objective,
        evidence_time=datetime.now(UTC),
        terminal_result=MaintenanceEvidenceResult.FAIL,
    )
    with pytest.raises(RuntimeInvariantViolation, match="failed suite"):
        VerifiedMaintenanceRecoveryService(facts.database).recover_lineage_after_verified_maintenance(failed)


def test_mr_evidence_authority_and_raw_conversation_rejected(facts) -> None:
    without_scope = facts.request.model_copy(
        update={
            "authority": facts.request.authority.model_copy(
                update={"authorization_scope": ("OBSERVE_ONLY",)}
            )
        }
    )
    with pytest.raises(RuntimeInvariantViolation, match="lacks maintenance recovery scope"):
        VerifiedMaintenanceRecoveryService(facts.database).recover_lineage_after_verified_maintenance(without_scope)
    payload = facts.request.model_dump(mode="python")
    payload["raw_conversation"] = "approve everything"
    with pytest.raises(ValidationError):
        VerifiedMaintenanceRecoveryRequest.model_validate(payload)


def test_mr_git_target_tree_ref_ancestry_and_scope_are_exact(facts) -> None:
    wrong_tree = facts.request.model_copy(
        update={"target_maintenance_tree": "0" * 40}
    )
    with pytest.raises(Exception, match="tree mismatch"):
        VerifiedMaintenanceRecoveryService(facts.database).recover_lineage_after_verified_maintenance(wrong_tree)
    wrong_scope = facts.request.model_copy(
        update={"approved_changed_paths": ("src/other.py",)}
    )
    with pytest.raises(RuntimeInvariantViolation, match="changed paths"):
        VerifiedMaintenanceRecoveryService(facts.database).recover_lineage_after_verified_maintenance(wrong_scope)

    unrelated = facts.repository.parent / "unrelated"
    unrelated.mkdir()
    _git(unrelated, "init", "-b", "main")
    _git(unrelated, "config", "user.name", "SPG Test")
    _git(unrelated, "config", "user.email", "spg-test@example.invalid")
    (unrelated / "x.txt").write_text("unrelated\n", encoding="utf-8")
    _git(unrelated, "add", ".")
    _git(unrelated, "commit", "-m", "unrelated")
    with pytest.raises(Exception, match="descendant"):
        GitMaintenanceObserver().observe(
            facts.repository,
            repository_identity=facts.request.repository_identity,
            authoritative_ref=facts.request.authoritative_ref,
            old_revision=_git(unrelated, "rev-parse", "HEAD"),
            target_commit=facts.target_commit,
            target_tree=facts.target_tree,
        )


class MovingRealityObserver:
    def __init__(self) -> None:
        self.delegate = GitMaintenanceObserver()
        self.calls = 0

    def observe(self, *args, **kwargs):
        self.calls += 1
        reality = self.delegate.observe(*args, **kwargs)
        if self.calls == 2:
            return reality.model_copy(
                update={"changed_paths": ("moved-after-qualification",)}
            )
        return reality


def test_mr_git_is_read_only_and_second_observation_detects_movement(facts) -> None:
    observer = MovingRealityObserver()
    ref_before = _git(facts.repository, "rev-parse", "refs/heads/main")
    with pytest.raises(RuntimeInvariantViolation, match="moved before local commit"):
        VerifiedMaintenanceRecoveryService(
            facts.database, git=observer
        ).recover_lineage_after_verified_maintenance(facts.request)
    assert observer.calls == 2
    assert _git(facts.repository, "rev-parse", "refs/heads/main") == ref_before
    assert not hasattr(GitMaintenanceObserver(), "compare_and_swap_ref")
    assert _all_runtime_counts(facts.database)["maintenance_recovery_admissions"] == 0


def test_mr_stale_pointer_or_lineage_version_rejected(facts) -> None:
    stale_pointer = facts.request.model_copy(
        update={"expected_current_pointer_version": 99}
    )
    with pytest.raises(RuntimeInvariantViolation, match="pointer identity/version is stale"):
        VerifiedMaintenanceRecoveryService(facts.database).recover_lineage_after_verified_maintenance(stale_pointer)
    stale_work_unit = facts.request.model_copy(
        update={"expected_old_work_unit_version": 0}
    )
    with pytest.raises(RuntimeInvariantViolation, match="PWU is outside"):
        VerifiedMaintenanceRecoveryService(facts.database).recover_lineage_after_verified_maintenance(stale_work_unit)
    stale_assessment = facts.request.model_copy(
        update={"expected_recovery_assessment_fingerprint": "0" * 64}
    )
    with pytest.raises(RuntimeInvariantViolation, match="Assessment"):
        VerifiedMaintenanceRecoveryService(facts.database).recover_lineage_after_verified_maintenance(stale_assessment)


def test_mr_competing_recovery_rejects_stale_pointer(facts) -> None:
    competing = _request(
        facts.repository,
        facts.baseline,
        facts.old_spine,
        facts.attempt,
        facts.assessment,
        facts.target_commit,
        facts.target_tree,
        objective="Competing new lineage objective",
        evidence_time=datetime.now(UTC) + timedelta(seconds=1),
    )
    service = VerifiedMaintenanceRecoveryService(facts.database)
    service.recover_lineage_after_verified_maintenance(facts.request)
    with pytest.raises(RuntimeInvariantViolation, match="pointer identity/version is stale"):
        service.recover_lineage_after_verified_maintenance(competing)


def test_mr_material_work_blocks_supersession(facts) -> None:
    with facts.database.unit_of_work() as unit_of_work:
        RuntimeStore(unit_of_work.session).insert_work_product_reference(
            {
                "id": facts.observation.id,
                "production_run_id": facts.old_spine.run.id,
                "work_unit_id": facts.old_spine.work_unit.id,
                "plan_revision_id": facts.old_spine.plan_revision.id,
                "attempt_id": facts.attempt.id,
                "generation": facts.attempt.generation,
                "source_baseline_id": facts.baseline.id,
                "repository_observation_id": facts.observation.id,
                "artifact_path": "docs/material.md",
                "change_type": ArtifactChangeType.ADDED.value,
                "source_fingerprint": None,
                "observed_fingerprint": "1" * 64,
                "created_at": datetime.now(UTC),
            }
        )
        unit_of_work.commit()
    with pytest.raises(RuntimeInvariantViolation, match="disqualifying production facts"):
        VerifiedMaintenanceRecoveryService(facts.database).recover_lineage_after_verified_maintenance(facts.request)


@pytest.mark.parametrize(
    "boundary",
    [
        "new_baseline",
        "baseline_pointer",
        "old_run_superseded",
        "old_plan_superseded",
        "old_work_unit_superseded",
        "new_run",
        "new_plan",
        "new_work_unit",
        "governance",
        "recovery_admission",
        "before_commit",
    ],
)
def test_mr_atomic_failure_boundaries_roll_back_every_local_fact(
    facts, boundary
) -> None:
    before = _all_runtime_counts(facts.database)
    assessment_before = facts.assessment.model_dump(mode="json")

    def inject(selected: str) -> None:
        if selected == boundary:
            raise RuntimeError(f"injected:{boundary}")

    with pytest.raises(RuntimeError, match=f"injected:{boundary}"):
        VerifiedMaintenanceRecoveryService(
            facts.database, failure_injector=inject
        ).recover_lineage_after_verified_maintenance(facts.request)
    assert _all_runtime_counts(facts.database) == before
    spine = facts.runtime.inspect_run(facts.old_spine.run.id)
    assert spine.run.condition is RunCondition.OPEN
    assert spine.plan_revision.condition is PlanCondition.ACTIVE
    assert spine.work_unit.condition is WorkUnitCondition.PROPOSED
    with facts.database.unit_of_work() as unit_of_work:
        store = RuntimeStore(unit_of_work.session)
        assert store.current_pointer().snapshot_id == facts.baseline.id
        current = store.recovery_assessment(facts.assessment.id)
        assert current.model_dump(mode="json") == assessment_before


def test_mr_migration_round_trip_and_schema_inventory(postgres_database) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260829_12")
    inspector = inspect(postgres_database.engine)
    assert "maintenance_recovery_admissions" not in inspector.get_table_names()
    columns = {item["name"] for item in inspector.get_columns("plan_revisions")}
    assert "version" not in columns
    command.upgrade(config, "20260902_13")
    inspector = inspect(postgres_database.engine)
    assert "maintenance_recovery_admissions" in inspector.get_table_names()
    columns = {item["name"] for item in inspector.get_columns("plan_revisions")}
    assert "version" in columns
    assert maintenance_recovery_admissions.name in RUNTIME_TABLE_NAMES


def _selected_counts(database: Database) -> dict[str, int]:
    tables = {
        "attempts": execution_attempts,
        "completion": completion_evaluations,
        "verification": verification_records,
        "candidate": baseline_candidates,
        "integration": repository_integration_effects,
        "runtime_commit": runtime_commits,
        "recovery_action": recovery_action_records,
    }
    with database.engine.connect() as connection:
        return {
            name: int(
                connection.scalar(select(func.count()).select_from(table)) or 0
            )
            for name, table in tables.items()
        }


def _all_runtime_counts(database: Database) -> dict[str, int]:
    with database.engine.connect() as connection:
        return {
            table.name: int(
                connection.scalar(select(func.count()).select_from(table)) or 0
            )
            for table in runtime_tables
        }


def _truncate_runtime(database: Database) -> None:
    table_names = ", ".join(f'"{name}"' for name in RUNTIME_TABLE_NAMES)
    with database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {table_names} CASCADE")


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
