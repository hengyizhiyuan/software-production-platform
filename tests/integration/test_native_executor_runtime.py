from __future__ import annotations

import asyncio
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Barrier
from types import SimpleNamespace
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, inspect, insert, select, update

from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.api.http import create_http_application
from spg.application.native_vector import NativeCandidateVectorService
from spg.application.native_retention import NativeRetentionService
from spg.application.runtime import RuntimeService
from spg.domain.native_execution import (
    AttemptGrantState,
    AttemptTerminalOutcome,
    BackendObservation,
    BackendControlCommand,
    CapabilityGrant,
    ControlAction,
    EffectCondition,
    ExecutionHandle,
    ExecutionEventRecord,
    ExecutionMode,
    InferenceAction,
    InferenceDecisionRejected,
    InferenceProviderObservation,
    InferenceRequest,
    InferenceResponse,
    InferenceUsage,
    KernelCheckpoint,
    KernelRunResult,
    NativeExecutionAdmission,
    NativeExecutionConflict,
    ObservationConfidence,
    PWUContractVersionRecord,
    QueueCondition,
    QueueProgressionState,
    ResourceEnvelope,
    RepairabilityClassification,
    ResourceReservationCondition,
    ResourceUsageEntryRecord,
    SourceMember,
    SourceVector,
    ToolCallProposal,
    ToolExecutionRequest,
    ToolExecutionResult,
    UsageCertainty,
    WorkerOffer,
    WorkingPlan,
    WorkspaceManifest,
    WorkspaceMount,
    canonical_digest,
)
from spg.domain.native_vector import (
    CandidateVectorAuthorizationRequest,
    CandidateVectorSealRequest,
    CandidateVectorTarget,
    NativeVectorVerificationRecord,
    VectorCondition,
    VectorTargetCondition,
)
from spg.domain.runtime import (
    AttemptRequest,
    BootstrapAlreadyInitialized,
    BootstrapRequest,
    CompletionContract,
    InitialRunRequest,
    ProductionHorizon,
)
from spg.domain.planning import PlannedArtifactOperation, ProductionPlanArtifactTarget, ProductionPlanningRequest
from spg.providers.rule_based_planner import RuleBasedProductionPlanner
from spg.infrastructure.executor_runtime.local_storage import (
    ContentAddressedStorage,
    WorkspaceArchiveStore,
)
from spg.infrastructure.executor_runtime.backends import (
    NativeExecutionBackend,
    PinnedExecutionBackendRouter,
)
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.executor_runtime.inference import (
    InferenceFailureCode,
    InferenceTransportUnknown,
)
from spg.infrastructure.executor_runtime.runtime_ports import DurableCheckpointPort
from spg.infrastructure.executor_runtime.runtime_ports import DurableKernelAudit
from spg.infrastructure.executor_runtime.worker import NativeExecutionWorker
from spg.executor.kernel import NativeExecutorKernel
from spg.executor.tools import NativeToolRegistry, ToolDefinition
from spg.infrastructure.executor_runtime.inference import ScriptedInferenceAdapter
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.native_execution_schema import (
    checkpoint_bundles,
    event_outbox,
    execution_control_requests,
    execution_events,
    execution_evidence,
    execution_resource_usage,
    execution_workspaces,
    executor_leases,
    native_execution_tables,
    native_trusted_source_pointers,
    result_ready_claims,
    self_refine_events,
)
from spg.domain.refinement_contract import RefinementClass, RefinementSignalKind
from spg.infrastructure.persistence.runtime_schema import runtime_tables


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALL_RUNTIME_TABLES = {table.name for table in (*native_execution_tables, *runtime_tables)}


def _migration_config(database: Database) -> Config:
    os.environ["SPG_DATABASE_URL"] = database.engine.url.render_as_string(hide_password=False)
    return Config(PROJECT_ROOT / "alembic.ini")


@pytest.fixture(autouse=True)
def clean_native_runtime(postgres_database: Database) -> Iterator[None]:
    command.upgrade(_migration_config(postgres_database), "head")
    names = ", ".join(f'"{name}"' for name in ALL_RUNTIME_TABLES)
    with postgres_database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {names} CASCADE")
    yield
    with postgres_database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {names} CASCADE")


@pytest.fixture
def git_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "source"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Native Executor Test")
    _git(repository, "config", "user.email", "native@example.invalid")
    (repository / "README.md").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "baseline")
    return repository


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _authority(database: Database, repository: Path):
    runtime = RuntimeService(database)
    try:
        runtime.bootstrap_trusted_baseline(
            BootstrapRequest(
                repository_path=repository,
                repository_identity=str(repository),
                repository_ref="refs/heads/main",
                authority_identity="architecture-lead:native-test",
                scope={"qualification": "native-executor"},
                rationale="isolated native qualification baseline",
            )
        )
    except BootstrapAlreadyInitialized:
        pass
    spine = runtime.create_initial_runtime_spine(
        InitialRunRequest(
            intent_ref="intent:native-executor-test",
            goal="qualify native execution",
            production_horizon=ProductionHorizon.CODE,
            initial_work_unit_objective="change one bounded file",
            completion_contract=CompletionContract(
                required_outputs=("bounded file",),
                required_changes=("record observable change",),
                forbidden_changes=("outside scope",),
                verification_obligations=("targeted test",),
            ),
        )
    )
    attempt = runtime.create_initial_attempt(
        spine.work_unit.id,
        AttemptRequest(provider_ref="watt-native:qualification"),
    )
    return spine, attempt


def _admission(
    database: Database, repository: Path, *, command_id=None, actor="human:test",
    contract_payload: dict | None = None,
    spine_attempt=None, work_id=None,
):
    spine, attempt = spine_attempt or _authority(database, repository)
    commit = _git(repository, "rev-parse", "HEAD")
    tree = _git(repository, "rev-parse", "HEAD^{tree}")
    vector = SourceVector(
        members=(
            SourceMember(
                mount_id="primary",
                repository_identity=str(repository),
                source_baseline_ref="refs/heads/main",
                source_commit_oid=commit,
                source_tree_oid=tree,
                container_path="/workspace/primary",
                read_scope=("README.md",),
                write_scope=("README.md",),
                forbidden_paths=(".git",),
            ),
        )
    )
    work_id = work_id or uuid4()
    workspace = WorkspaceManifest(
        workspace_id=uuid4(), work_id=work_id, pwu_id=spine.work_unit.id,
        attempt_id=attempt.id, source_vector_digest=vector.digest or "",
        host_storage_id="qualification-host", environment_profile_digest="b" * 64,
        mounts=(WorkspaceMount(mount_id="primary", host_path=str(repository), container_path="/workspace/primary", writable=True, write_scope=("README.md",), forbidden_paths=(".git",)),),
        evidence_namespace="qualification", retention_policy="test",
    )
    payload = contract_payload or {"objective": "change one bounded file", "verification": ["targeted test"]}
    contract = PWUContractVersionRecord(
        id=uuid4(), pwu_id=spine.work_unit.id, revision=1,
        objective="change one bounded file", contract_payload=payload,
        contract_digest=canonical_digest(payload), created_at=datetime.now(timezone.utc),
    )
    envelope = ResourceEnvelope(
        envelope_id=uuid4(), policy_version="qualification-v1",
        max_inference_submissions=3, max_tool_effects=3, max_active_seconds=60,
        provider_profile="scripted",
    )
    from spg.domain.native_execution import ExecutionBindingV2
    binding = ExecutionBindingV2(
        work_id=work_id, steering_decision_id=uuid4(), pwu_id=spine.work_unit.id,
        pwu_contract_version_id=contract.id, pwu_contract_digest=contract.contract_digest,
        attempt_id=attempt.id, generation=attempt.generation, session_id=uuid4(),
        source_vector=vector, workspace=workspace, context_package_ref="context:qualification",
        materialized_input_digest="c" * 64, backend_implementation="watt-native",
        backend_version="1", inference_profile="scripted",
        capability_grants=(CapabilityGrant(identity="file.write", version="1", scope={"paths": ["README.md"]}),),
        resource_envelope=envelope, obligation_references=("targeted test",),
    )
    return NativeExecutionAdmission(
        command_id=command_id or uuid4(), actor_identity=actor,
        fairness_group="user:test", binding=binding, contract=contract,
        materialization_path=str(repository), required_resource_profile="standard",
        available_at=datetime.now(timezone.utc),
    )


def _offer(*, lease_seconds: int = 30) -> WorkerOffer:
    return WorkerOffer(
        worker_id="worker:qualification", worker_profile="local-container-v1",
        provider_profiles=("scripted",), resource_profiles=("standard",),
        capability_identities=("file.write",), lease_seconds=lease_seconds,
    )


def test_native_migration_is_additive_and_at_head(postgres_database: Database) -> None:
    tables = set(inspect(postgres_database.engine).get_table_names())
    assert {table.name for table in native_execution_tables} <= tables
    assert {"execution_attempts", "production_work_units", "provider_execution_reports"} <= tables


def test_contract_content_lookup_reuses_the_existing_pwu_version(
    postgres_database: Database,
    git_repository: Path,
) -> None:
    admission = _admission(postgres_database, git_repository)
    NativeExecutorRuntimeService(postgres_database).admit(admission)

    with postgres_database.unit_of_work() as unit_of_work:
        stored = NativeExecutionStore(unit_of_work.session).contract_for_pwu_digest(
            admission.contract.pwu_id,
            admission.contract.contract_digest,
        )

    assert stored == admission.contract


def test_checkpoint_schema_migration_round_trip_preserves_existing_bundle(
    postgres_database: Database, git_repository: Path, tmp_path: Path
) -> None:
    service = NativeExecutorRuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    service.admit(admission)
    grant = service.allocate(_offer())
    assert grant is not None
    service.activate_allocation(grant)
    checkpoint = asyncio.run(
        DurableCheckpointPort(
            postgres_database,
            ContentAddressedStorage(tmp_path / "checkpoint-schema-migration"),
            attempt_id=admission.binding.attempt_id,
            session_id=admission.binding.session_id,
            worker_epoch=grant.allocation.lease_epoch,
        ).commit(
            KernelCheckpoint(
                step_sequence=1,
                working_plan=WorkingPlan(
                    version=1,
                    objective_reference=str(admission.contract.id),
                    chosen_approach="preserve checkpoint across migration",
                    approach_rationale="reader compatibility qualification",
                ),
                tool_results=(),
                source_vector_digest=admission.binding.source_vector.digest or "",
                residual_obligations=("resume safely",),
            )
        )
    )
    config = _migration_config(postgres_database)

    command.downgrade(config, "20260912_38")
    assert "schema_version" not in {
        column["name"]
        for column in inspect(postgres_database.engine).get_columns("checkpoint_bundles")
    }

    command.upgrade(config, "head")
    with postgres_database.engine.connect() as connection:
        restored = connection.execute(
            select(checkpoint_bundles).where(checkpoint_bundles.c.id == checkpoint.id)
        ).mappings().one()
    assert restored["id"] == checkpoint.id
    assert restored["schema_version"] == 1


def test_successor_attempt_does_not_inherit_previous_attempt_checkpoint(
    postgres_database: Database, git_repository: Path, tmp_path: Path
) -> None:
    service = NativeExecutorRuntimeService(postgres_database)
    first = _admission(postgres_database, git_repository)
    service.admit(first)
    first_grant = service.allocate(_offer())
    assert first_grant is not None
    service.activate_allocation(first_grant)
    first_checkpoint = asyncio.run(
        DurableCheckpointPort(
            postgres_database,
            ContentAddressedStorage(tmp_path / "successor-checkpoints"),
            attempt_id=first.binding.attempt_id,
            session_id=first.binding.session_id,
            worker_epoch=first_grant.allocation.lease_epoch,
        ).commit(
            KernelCheckpoint(
                step_sequence=1,
                working_plan=WorkingPlan(
                    version=1,
                    objective_reference=str(first.contract.id),
                    chosen_approach="first attempt output",
                    approach_rationale="prove checkpoint isolation",
                ),
                tool_results=(),
                source_vector_digest=first.binding.source_vector.digest or "",
                result_claim={"output_vector": {"files": ["README.md"]}},
                residual_obligations=(),
            )
        )
    )
    service.finish_allocation(
        first_grant,
        KernelRunResult(
            runtime_mode=ExecutionMode.FINISHED,
            terminal_outcome=AttemptTerminalOutcome.RESULT_READY,
            final_checkpoint_id=first_checkpoint.id,
            step_count=1,
            inference_submissions=1,
            tool_effects=0,
            summary="first attempt completed",
            result_claim={"output_vector": {"files": ["README.md"]}},
        ),
    )

    successor_attempt = RuntimeService(postgres_database).retry_attempt(
        first.binding.attempt_id
    )
    successor_workspace = first.binding.workspace.model_copy(
        update={"workspace_id": uuid4(), "attempt_id": successor_attempt.id}
    )
    successor_binding = first.binding.model_copy(
        update={
            "attempt_id": successor_attempt.id,
            "generation": successor_attempt.generation,
            "workspace": successor_workspace,
            "resource_envelope": first.binding.resource_envelope.model_copy(
                update={"envelope_id": uuid4()}
            ),
        }
    )
    successor = first.model_copy(
        update={
            "command_id": uuid4(),
            "binding": successor_binding,
            "available_at": datetime.now(timezone.utc),
        }
    )
    service.admit(successor)
    successor_grant = service.allocate(_offer())
    assert successor_grant is not None

    worker = NativeExecutionWorker(service, lambda grant: None)
    _, _, loaded_checkpoint, session_frontier = worker._load_execution_reality(
        successor_grant
    )

    assert loaded_checkpoint is None
    assert session_frontier == 0


def test_admission_allocation_checkpoint_and_result_ready_are_durable(
    postgres_database: Database, git_repository: Path, tmp_path: Path
) -> None:
    service = NativeExecutorRuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    queued = service.admit(admission)
    assert queued.condition is QueueCondition.QUEUED
    assert service.admit(admission).id == queued.id
    grant = service.allocate(_offer())
    assert grant is not None
    assert grant.queue_entry.id == queued.id
    assert grant.lease_token not in grant.allocation.lease_token_digest
    service.activate_allocation(grant)
    service.heartbeat(grant)

    checkpoint = asyncio.run(
        DurableCheckpointPort(
            postgres_database,
            ContentAddressedStorage(tmp_path / "checkpoints"),
            attempt_id=admission.binding.attempt_id,
            session_id=admission.binding.session_id,
            worker_epoch=grant.allocation.lease_epoch,
        ).commit(
            KernelCheckpoint(
                step_sequence=1,
                working_plan=WorkingPlan(
                    version=1, objective_reference=str(admission.contract.id),
                    chosen_approach="bounded change", approach_rationale="contract",
                ),
                tool_results=(), source_vector_digest=admission.binding.source_vector.digest or "",
                result_claim={"output_vector": {"files": ["README.md"]}, "evidence_ids": []},
                residual_obligations=(),
            )
        )
    )
    service.finish_allocation(
        grant,
        KernelRunResult(
            runtime_mode=ExecutionMode.FINISHED,
            terminal_outcome=AttemptTerminalOutcome.RESULT_READY,
            final_checkpoint_id=checkpoint.id,
            step_count=1, inference_submissions=1, tool_effects=1,
            summary="bounded output is ready",
            result_claim={"output_vector": {"files": ["README.md"]}, "evidence_ids": []},
        ),
    )
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        state = store.attempt_state(admission.binding.attempt_id)
        final_queue = store.queue_for_attempt(admission.binding.attempt_id)
        lease_row = uow.session.execute(select(executor_leases)).mappings().one()
        assert state.grant_state is AttemptGrantState.RELEASED
        assert state.terminal_outcome is AttemptTerminalOutcome.RESULT_READY
        assert final_queue is not None and final_queue.condition is QueueCondition.COMPLETED
        assert lease_row["released_at"] is not None
        assert grant.lease_token not in str(dict(lease_row))
        assert uow.session.scalar(select(func.count()).select_from(result_ready_claims)) == 1
        assert uow.session.scalar(select(func.count()).select_from(execution_events)) == uow.session.scalar(select(func.count()).select_from(event_outbox))
        timing = store.timing_projection(admission.binding.attempt_id)
        assert {item["kind"] for item in timing["spans"]} >= {
            "QUEUE", "CHECKPOINT"
        }
        assert timing["aggregate_duration_ms"] is None
        assert "worker_activation" in timing["unavailable"]


def test_command_idempotency_rejects_changed_semantics(
    postgres_database: Database, git_repository: Path
) -> None:
    service = NativeExecutorRuntimeService(postgres_database)
    command_id = uuid4()
    original = _admission(postgres_database, git_repository, command_id=command_id)
    service.admit(original)
    changed = original.model_copy(update={"actor_identity": "human:different"})
    with pytest.raises(NativeExecutionConflict, match="different semantics"):
        service.admit(changed)


def test_multi_repository_vector_preserves_partial_reality_and_commits_atomically(
    postgres_database: Database, tmp_path: Path
) -> None:
    repositories = []
    members = []
    mounts = []
    candidate_facts = []
    for mount_id in ("api", "client"):
        repository = tmp_path / mount_id
        repository.mkdir()
        _git(repository, "init", "-b", "main")
        _git(repository, "config", "user.name", "Native Vector Test")
        _git(repository, "config", "user.email", "native-vector@example.invalid")
        (repository / "artifact.txt").write_text(f"{mount_id} baseline\n", encoding="utf-8")
        _git(repository, "add", "artifact.txt")
        _git(repository, "commit", "-m", "baseline")
        base = _git(repository, "rev-parse", "HEAD")
        base_tree = _git(repository, "rev-parse", "HEAD^{tree}")
        _git(repository, "checkout", "-b", "candidate")
        (repository / "artifact.txt").write_text(f"{mount_id} candidate\n", encoding="utf-8")
        _git(repository, "add", "artifact.txt")
        _git(repository, "commit", "-m", "candidate")
        proposed = _git(repository, "rev-parse", "HEAD")
        proposed_tree = _git(repository, "rev-parse", "HEAD^{tree}")
        _git(repository, "checkout", "main")
        repositories.append(repository)
        members.append(
            SourceMember(
                mount_id=mount_id,
                repository_identity=str(repository),
                source_baseline_ref="refs/heads/main",
                source_commit_oid=base,
                source_tree_oid=base_tree,
                container_path=f"/workspace/{mount_id}",
                read_scope=("artifact.txt",),
                write_scope=("artifact.txt",),
                forbidden_paths=(".git",),
            )
        )
        mounts.append(
            WorkspaceMount(
                mount_id=mount_id,
                host_path=str(repository),
                container_path=f"/workspace/{mount_id}",
                writable=True,
                write_scope=("artifact.txt",),
                forbidden_paths=(".git",),
            )
        )
        candidate_facts.append((mount_id, repository, base, proposed, proposed_tree))

    runtime = NativeExecutorRuntimeService(postgres_database)
    admission = _admission(postgres_database, repositories[0])
    source_vector = SourceVector(members=tuple(members))
    workspace = admission.binding.workspace.model_copy(
        update={
            "source_vector_digest": source_vector.digest,
            "mounts": tuple(mounts),
        }
    )
    binding = admission.binding.model_copy(
        update={"source_vector": source_vector, "workspace": workspace}
    )
    admission = admission.model_copy(update={"binding": binding})
    runtime.admit(admission)
    grant = runtime.allocate(_offer())
    assert grant is not None
    runtime.activate_allocation(grant)
    checkpoint = asyncio.run(
        DurableCheckpointPort(
            postgres_database,
            ContentAddressedStorage(tmp_path / "vector-checkpoints"),
            attempt_id=binding.attempt_id,
            session_id=binding.session_id,
            worker_epoch=grant.allocation.lease_epoch,
        ).commit(
            KernelCheckpoint(
                step_sequence=1,
                working_plan=WorkingPlan(
                    version=1,
                    objective_reference=str(admission.contract.id),
                    chosen_approach="coordinated API and client change",
                    approach_rationale="exact cross-repository contract",
                ),
                tool_results=(),
                source_vector_digest=source_vector.digest or "",
                result_claim={"candidate": "two-repository"},
                residual_obligations=(),
            )
        )
    )

    targets = tuple(
        CandidateVectorTarget(
            mount_id=mount_id,
            repository_identity=str(repository),
            repository_path=str(repository),
            target_authoritative_ref="refs/heads/main",
            expected_source_revision=base,
            proposed_revision=proposed,
            proposed_tree_identity=proposed_tree,
            verification_obligations=("cross-repository contract",),
            verification_evidence_ids=(uuid4(),),
        )
        for mount_id, repository, base, proposed, proposed_tree in candidate_facts
    )
    vectors = NativeCandidateVectorService(postgres_database)
    seal_request = CandidateVectorSealRequest(
        pwu_id=binding.pwu_id,
        source_vector_digest=source_vector.digest or "",
        checkpoint_id=checkpoint.id,
        targets=targets,
    )
    with pytest.raises(NativeExecutionConflict, match="evidence is missing"):
        vectors.seal(seal_request)
    with pytest.raises(NativeExecutionConflict, match="not independent"):
        vectors.record_verification(
            NativeVectorVerificationRecord(
                id=uuid4(), pwu_id=binding.pwu_id, mount_id=targets[0].mount_id,
                proposed_revision=targets[0].proposed_revision,
                proposed_tree_identity=targets[0].proposed_tree_identity,
                obligation="cross-repository contract", provider_identity="model:forged",
                result="PASS", evidence={"claim": "self-issued"},
                created_at=datetime.now(timezone.utc),
            ),
            repository_path=Path(targets[0].repository_path),
        )
    for target in targets:
        vectors.record_verification(
            NativeVectorVerificationRecord(
                id=target.verification_evidence_ids[0],
                pwu_id=binding.pwu_id,
                mount_id=target.mount_id,
                proposed_revision=target.proposed_revision,
                proposed_tree_identity=target.proposed_tree_identity,
                obligation="cross-repository contract",
                provider_identity="independent-verifier:test",
                result="PASS",
                evidence={"command": "isolated deterministic cross-check"},
                created_at=datetime.now(timezone.utc),
            ),
            repository_path=Path(target.repository_path),
        )
    source_trust_digest = "d" * 64
    for target in targets:
        vectors.register_trusted_source(
            target, trusted_vector_digest=source_trust_digest
        )
    sealed = vectors.seal(seal_request)
    vectors.authorize(
        CandidateVectorAuthorizationRequest(
            vector_id=sealed.vector.id,
            manifest_digest=sealed.vector.manifest_digest,
            authority_identity="human:native-vector-test",
            rationale="authorize exact cross-repository candidate",
        )
    )

    second_repository = repositories[1]
    (second_repository / "drift.txt").write_text("unrelated drift\n", encoding="utf-8")
    _git(second_repository, "add", "drift.txt")
    _git(second_repository, "commit", "-m", "drift")
    drift_revision = _git(second_repository, "rev-parse", "HEAD")
    partial = vectors.integrate(sealed.vector.id)
    assert partial.vector.condition is VectorCondition.PARTIAL
    assert tuple(item.condition for item in partial.targets) == (
        VectorTargetCondition.CONVERGED,
        VectorTargetCondition.FAILED,
    )
    assert _git(repositories[0], "rev-parse", "main") == targets[0].proposed_revision
    with postgres_database.unit_of_work() as uow:
        before_commit = tuple(
            uow.session.execute(
                select(native_trusted_source_pointers)
                .order_by(native_trusted_source_pointers.c.repository_identity)
            ).mappings()
        )
    assert {row["repository_revision"] for row in before_commit} == {
        target.expected_source_revision for target in targets
    }
    with pytest.raises(NativeExecutionConflict, match="every exact target"):
        vectors.commit(sealed.vector.id)

    _git(
        second_repository,
        "update-ref",
        "refs/heads/main",
        targets[1].expected_source_revision,
        drift_revision,
    )
    converged = vectors.integrate(sealed.vector.id)
    assert converged.vector.condition is VectorCondition.CONVERGED
    assert all(
        item.condition is VectorTargetCondition.CONVERGED
        for item in converged.targets
    )
    aggregate = vectors.commit(sealed.vector.id)
    assert vectors.commit(sealed.vector.id).id == aggregate.id
    assert vectors.integrate(sealed.vector.id).vector.condition is VectorCondition.COMMITTED
    with postgres_database.unit_of_work() as uow:
        after_commit = tuple(
            uow.session.execute(
                select(native_trusted_source_pointers)
                .order_by(native_trusted_source_pointers.c.repository_identity)
            ).mappings()
        )
    assert {row["repository_revision"] for row in after_commit} == {
        target.proposed_revision for target in targets
    }
    assert {row["trusted_vector_digest"] for row in after_commit} == {
        aggregate.trusted_vector_digest
    }


def test_workspace_hibernation_respects_pins_and_restores_verified_bundle(
    postgres_database: Database, git_repository: Path, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [datetime.now(timezone.utc)]
    runtime = NativeExecutorRuntimeService(postgres_database, now=lambda: clock[0])
    admission = _admission(postgres_database, git_repository).model_copy(
        update={"available_at": clock[0]}
    )
    runtime.admit(admission)
    grant = runtime.allocate(_offer())
    assert grant is not None
    runtime.activate_allocation(grant)
    checkpoint = asyncio.run(
        DurableCheckpointPort(
            postgres_database,
            ContentAddressedStorage(tmp_path / "retention-checkpoints"),
            attempt_id=admission.binding.attempt_id,
            session_id=admission.binding.session_id,
            worker_epoch=grant.allocation.lease_epoch,
        ).commit(
            KernelCheckpoint(
                step_sequence=1,
                working_plan=WorkingPlan(
                    version=1,
                    objective_reference=str(admission.contract.id),
                    chosen_approach="retain exact workspace",
                    approach_rationale="recovery contract",
                ),
                tool_results=(),
                source_vector_digest=admission.binding.source_vector.digest or "",
                result_claim={"retained": True},
                residual_obligations=(),
            )
        )
    )
    runtime.finish_allocation(
        grant,
        KernelRunResult(
            runtime_mode=ExecutionMode.FINISHED,
            terminal_outcome=AttemptTerminalOutcome.RESULT_READY,
            final_checkpoint_id=checkpoint.id,
            step_count=1,
            inference_submissions=1,
            tool_effects=0,
            summary="workspace ready for retention",
            result_claim={"retained": True},
        ),
    )
    clock[0] += timedelta(days=31)
    with postgres_database.unit_of_work() as uow:
        uow.session.execute(
            update(execution_workspaces)
            .where(execution_workspaces.c.id == admission.binding.workspace.workspace_id)
            .values(updated_at=clock[0] - timedelta(days=31))
        )
        uow.commit()

    retention = NativeRetentionService(
        postgres_database,
        WorkspaceArchiveStore(tmp_path / "workspace-archives"),
        now=lambda: clock[0],
    )
    pin = retention.pin_workspace(
        admission.binding.workspace.workspace_id,
        owner_kind="VERIFICATION",
        owner_id="verification:pending",
        reason="independent verification still needs exact files",
    )
    with pytest.raises(NativeExecutionConflict, match="retention pin"):
        retention.hibernate(admission.binding.workspace.workspace_id)
    assert retention.eligibility(admission.binding.workspace.workspace_id)["classification"] == "REFERENCED"
    retention.release_pin(pin.id)

    evidence_id = uuid4()
    with postgres_database.unit_of_work() as uow:
        uow.session.execute(insert(execution_evidence).values(
            id=evidence_id, pwu_id=admission.binding.pwu_id,
            attempt_id=admission.binding.attempt_id, step_id=None, effect_id=None,
            evidence_type="WORKSPACE_REFERENCE", producer_identity="p1-q5",
            subject_digest="a" * 64,
            payload={"workspace_id": str(admission.binding.workspace.workspace_id)},
            content_digest="b" * 64, created_at=clock[0]))
        uow.commit()
    assert retention.eligibility(admission.binding.workspace.workspace_id)["classification"] == "REFERENCED"
    with pytest.raises(NativeExecutionConflict, match="Evidence reference"):
        retention.hibernate(admission.binding.workspace.workspace_id)
    with postgres_database.unit_of_work() as uow:
        uow.session.execute(delete(execution_evidence).where(execution_evidence.c.id == evidence_id))
        uow.commit()

    original = (git_repository / "README.md").read_text(encoding="utf-8")
    assert retention.eligibility(admission.binding.workspace.workspace_id)["classification"] == "ELIGIBLE_FOR_CLEANUP"
    def interrupted_before_removal(_workspace_id):
        raise OSError("simulated restart after verified archive")
    monkeypatch.setattr(retention, "_recheck_before_physical_change", interrupted_before_removal)
    with pytest.raises(OSError, match="simulated restart"):
        retention.hibernate(admission.binding.workspace.workspace_id)
    # A fresh service resumes the persisted action rather than recopying or
    # deleting a workspace without its verified recovery bundle.
    retention = NativeRetentionService(
        postgres_database, WorkspaceArchiveStore(tmp_path / "workspace-archives"),
        now=lambda: clock[0],
    )
    result = next(item for item in retention.cleanup_expired()
                  if item["workspace_id"] == str(admission.binding.workspace.workspace_id))
    assert result["cleanup_result"] == "COMPLETED"
    action = retention.action(UUID(result["action_id"]))
    assert action.condition.value == "COMPLETED"
    assert action.bundle_digest is not None
    assert not git_repository.exists()
    assert retention.hibernate(admission.binding.workspace.workspace_id).id == action.id

    retention.restore(admission.binding.workspace.workspace_id)
    assert (git_repository / "README.md").read_text(encoding="utf-8") == original
    assert _git(git_repository, "rev-parse", "HEAD") == admission.binding.source_vector.members[0].source_commit_oid
    clock[0] += timedelta(days=31)
    with postgres_database.unit_of_work() as uow:
        uow.session.execute(
            update(execution_workspaces)
            .where(execution_workspaces.c.id == admission.binding.workspace.workspace_id)
            .values(updated_at=clock[0] - timedelta(days=31))
        )
        uow.commit()
    cold = retention.hibernate(admission.binding.workspace.workspace_id)
    clock[0] += timedelta(days=181)
    with postgres_database.unit_of_work() as uow:
        uow.session.execute(
            update(execution_workspaces)
            .where(execution_workspaces.c.id == admission.binding.workspace.workspace_id)
            .values(updated_at=clock[0] - timedelta(days=181))
        )
        uow.commit()
    retired = retention.retire(admission.binding.workspace.workspace_id)
    assert retired.physical_receipt == {
        "hot_materialization_absent": True,
        "last_recovery_bundle_retained": True,
    }
    assert Path(cold.bundle_path or "").exists()
    assert retention.retire(admission.binding.workspace.workspace_id).id == retired.id


def test_lost_workspace_restores_only_from_verified_bundle_into_successor(
    postgres_database: Database, git_repository: Path, tmp_path: Path
) -> None:
    native = NativeExecutorRuntimeService(postgres_database)
    runtime = RuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    native.admit(admission)
    grant = native.allocate(_offer())
    assert grant is not None
    native.activate_allocation(grant)
    checkpoint = asyncio.run(DurableCheckpointPort(
        postgres_database,
        ContentAddressedStorage(tmp_path / "lost-checkpoints"),
        attempt_id=admission.binding.attempt_id,
        session_id=admission.binding.session_id,
        worker_epoch=grant.allocation.lease_epoch,
    ).commit(KernelCheckpoint(
        step_sequence=1,
        working_plan=WorkingPlan(
            version=1, objective_reference=str(admission.contract.id),
            chosen_approach="retain exact content",
            approach_rationale="lost workspace recovery qualification",
        ),
        tool_results=(),
        source_vector_digest=admission.binding.source_vector.digest or "",
        result_claim=None,
        residual_obligations=admission.binding.obligation_references,
    )))
    native.finish_allocation(grant, KernelRunResult(
        runtime_mode=ExecutionMode.FINISHED,
        terminal_outcome=AttemptTerminalOutcome.UNABLE_TO_COMPLETE,
        final_checkpoint_id=checkpoint.id,
        step_count=1, inference_submissions=0, tool_effects=0,
        summary="preserve workspace for successor recovery",
        residual_obligations=admission.binding.obligation_references,
    ))
    archives = WorkspaceArchiveStore(tmp_path / "lost-archives")
    retention = NativeRetentionService(postgres_database, archives)
    retained = retention.hibernate(
        admission.binding.workspace.workspace_id,
        minimum_idle=timedelta(0),
    )
    assert retained.bundle_digest is not None
    retention.restore(admission.binding.workspace.workspace_id)
    original_content = (git_repository / "README.md").read_text(encoding="utf-8")
    shutil.rmtree(git_repository)

    successor_attempt = runtime.retry_attempt(
        admission.binding.attempt_id,
        AttemptRequest(provider_ref="watt-native:qualification"),
    )
    successor_path = tmp_path / "lost-successor"
    successor_workspace = admission.binding.workspace.model_copy(update={
        "workspace_id": uuid4(),
        "attempt_id": successor_attempt.id,
        "host_storage_id": str(successor_path),
        "mounts": (admission.binding.workspace.mounts[0].model_copy(update={
            "host_path": str(successor_path),
        }),),
    })
    successor_binding = admission.binding.model_copy(update={
        "attempt_id": successor_attempt.id,
        "generation": successor_attempt.generation,
        "workspace": successor_workspace,
        "resource_envelope": admission.binding.resource_envelope.model_copy(update={
            "envelope_id": uuid4(),
        }),
    })
    successor_admission = admission.model_copy(update={
        "command_id": uuid4(),
        "binding": successor_binding,
        "materialization_path": str(successor_path),
    })
    native.admit(successor_admission)
    recovery = retention.recover_lost_workspace(
        admission.binding.workspace.workspace_id,
        successor_workspace.workspace_id,
    )

    assert recovery.classification.value == "COMPLETE"
    assert recovery.attempt_id == successor_attempt.id
    assert recovery.basis_checkpoint_id == checkpoint.id
    assert recovery.residual_obligations == admission.binding.obligation_references
    assert (successor_path / "README.md").read_text(encoding="utf-8") == original_content


def test_lost_workspace_without_complete_bundle_fails_recovery_promise(
    postgres_database: Database, git_repository: Path, tmp_path: Path
) -> None:
    native = NativeExecutorRuntimeService(postgres_database)
    runtime = RuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    native.admit(admission)
    grant = native.allocate(_offer())
    assert grant is not None
    native.activate_allocation(grant)
    native.finish_allocation(grant, KernelRunResult(
        runtime_mode=ExecutionMode.FINISHED,
        terminal_outcome=AttemptTerminalOutcome.UNABLE_TO_COMPLETE,
        final_checkpoint_id=None,
        step_count=0, inference_submissions=0, tool_effects=0,
        summary="no complete recovery bundle exists",
        residual_obligations=admission.binding.obligation_references,
    ))
    shutil.rmtree(git_repository)
    successor_attempt = runtime.retry_attempt(
        admission.binding.attempt_id,
        AttemptRequest(provider_ref="watt-native:qualification"),
    )
    successor_path = tmp_path / "unrecoverable-successor"
    successor_workspace = admission.binding.workspace.model_copy(update={
        "workspace_id": uuid4(), "attempt_id": successor_attempt.id,
        "host_storage_id": str(successor_path),
        "mounts": (admission.binding.workspace.mounts[0].model_copy(update={
            "host_path": str(successor_path),
        }),),
    })
    native.admit(admission.model_copy(update={
        "command_id": uuid4(),
        "binding": admission.binding.model_copy(update={
            "attempt_id": successor_attempt.id,
            "generation": successor_attempt.generation,
            "workspace": successor_workspace,
            "resource_envelope": admission.binding.resource_envelope.model_copy(update={
                "envelope_id": uuid4(),
            }),
        }),
        "materialization_path": str(successor_path),
    }))

    recovery = NativeRetentionService(
        postgres_database, WorkspaceArchiveStore(tmp_path / "empty-archives")
    ).recover_lost_workspace(
        admission.binding.workspace.workspace_id,
        successor_workspace.workspace_id,
    )

    assert recovery.classification.value == "LOST"
    assert recovery.resolution is not None
    assert recovery.resolution.startswith("RECOVERY_PROMISE_FAILED")
    assert not successor_path.exists()


def test_hundred_round_allocation_race_never_double_grants(
    postgres_database: Database, git_repository: Path
) -> None:
    service = NativeExecutorRuntimeService(postgres_database)
    winners = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        for seed in range(100):
            admission = _admission(
                postgres_database,
                git_repository,
                actor=f"qualification:race-round:{seed}",
            )
            service.admit(admission)
            gate = Barrier(2)

            def compete(lane: int):
                gate.wait()
                return NativeExecutorRuntimeService(postgres_database).allocate(
                    WorkerOffer(
                        worker_id=f"worker:race:{seed}:{lane}",
                        worker_profile="local-container-v1",
                        provider_profiles=("scripted",),
                        resource_profiles=("standard",),
                        capability_identities=("file.write",),
                        lease_seconds=30,
                    )
                )

            round_results = tuple(
                future.result()
                for future in (pool.submit(compete, 0), pool.submit(compete, 1))
            )
            round_winners = tuple(item for item in round_results if item is not None)
            assert len(round_winners) == 1, f"seed {seed} did not have one winner"
            assert round_winners[0].allocation.attempt_id == admission.binding.attempt_id
            assert round_winners[0].allocation.lease_epoch == 1
            winners.append(round_winners[0])
            service.finish_allocation(
                round_winners[0],
                KernelRunResult(
                    runtime_mode=ExecutionMode.FINISHED,
                    terminal_outcome=AttemptTerminalOutcome.STOPPED,
                    final_checkpoint_id=None,
                    step_count=0,
                    inference_submissions=0,
                    tool_effects=0,
                    summary="release completed qualification race round",
                ),
            )

    assert len({grant.allocation.attempt_id for grant in winners}) == 100


def test_expired_worker_before_any_step_restarts_same_attempt_with_new_epoch(
    postgres_database: Database, git_repository: Path
) -> None:
    clock = [datetime.now(timezone.utc)]
    service = NativeExecutorRuntimeService(postgres_database, now=lambda: clock[0])
    admission = _admission(postgres_database, git_repository).model_copy(
        update={"available_at": clock[0]}
    )
    service.admit(admission)
    grant = service.allocate(_offer(lease_seconds=5))
    assert grant is not None
    service.activate_allocation(grant)
    clock[0] += timedelta(seconds=6)
    assert service.reconcile_expired_leases() == (admission.binding.attempt_id,)
    with postgres_database.unit_of_work() as uow:
        state = NativeExecutionStore(uow.session).attempt_state(admission.binding.attempt_id)
        assert state.grant_state is AttemptGrantState.GRANTED
        assert state.terminal_outcome is None
        assert state.runtime_mode is ExecutionMode.QUEUED
        assert state.effect_uncertainty is False
    successor = service.allocate(_offer())
    assert successor is not None
    assert successor.allocation.attempt_id == admission.binding.attempt_id
    assert successor.allocation.lease_epoch == grant.allocation.lease_epoch + 1


def test_expired_worker_with_unresolved_effect_is_fenced_unknown(
    postgres_database: Database, git_repository: Path
) -> None:
    clock = [datetime.now(timezone.utc)]
    service = NativeExecutorRuntimeService(postgres_database, now=lambda: clock[0])
    admission = _admission(postgres_database, git_repository).model_copy(
        update={"available_at": clock[0]}
    )
    service.admit(admission)
    grant = service.allocate(_offer(lease_seconds=5))
    assert grant is not None
    service.activate_allocation(grant)
    audit = DurableKernelAudit(
        postgres_database,
        attempt_id=admission.binding.attempt_id,
        session_id=admission.binding.session_id,
        pwu_id=admission.binding.pwu_id,
        envelope_id=admission.binding.resource_envelope.envelope_id,
    )
    request = InferenceRequest(
        attempt_id=admission.binding.attempt_id,
        session_id=admission.binding.session_id,
        step_sequence=1,
        objective=admission.contract.objective,
        working_plan=WorkingPlan(
            version=1, objective_reference=str(admission.contract.id),
            chosen_approach="write", approach_rationale="contract",
        ),
        context_facts=(), available_tools=(), residual_obligations=("targeted test",),
    )
    step_id = asyncio.run(audit.begin_inference(request))
    asyncio.run(
        audit.finish_inference(
            step_id,
            InferenceResponse(
                action=InferenceAction.CONTINUE,
                summary="write",
                working_plan=request.working_plan,
                tool_calls=(
                    ToolCallProposal(
                        proposal_index=0, tool_identity="file.write",
                        arguments={"path": "README.md", "content": "changed"},
                    ),
                ),
                residual_obligations=("targeted test",),
            ),
            None,
        )
    )
    asyncio.run(
        audit.begin_tool(
            step_id,
            ToolExecutionRequest(
                delivery_id=uuid4(), attempt_id=admission.binding.attempt_id,
                worker_epoch=grant.allocation.lease_epoch, step_id=step_id,
                proposal=ToolCallProposal(
                    proposal_index=0, tool_identity="file.write",
                    arguments={"path": "README.md", "content": "changed"},
                ),
                capability_grants=admission.binding.capability_grants,
                workspace=admission.binding.workspace,
            ),
        )
    )
    clock[0] += timedelta(seconds=6)

    assert service.reconcile_expired_leases() == (admission.binding.attempt_id,)
    with postgres_database.unit_of_work() as uow:
        state = NativeExecutionStore(uow.session).attempt_state(
            admission.binding.attempt_id
        )
        assert state.grant_state is AttemptGrantState.FENCED
        assert state.terminal_outcome is AttemptTerminalOutcome.UNKNOWN
        assert state.runtime_mode is ExecutionMode.RECONCILING
        assert state.effect_uncertainty is True


def test_receipt_before_checkpoint_is_rehydrated_without_replaying_effect(
    postgres_database: Database, git_repository: Path
) -> None:
    clock = [datetime.now(timezone.utc)]
    service = NativeExecutorRuntimeService(postgres_database, now=lambda: clock[0])
    admission = _admission(postgres_database, git_repository).model_copy(
        update={"available_at": clock[0]}
    )
    service.admit(admission)
    grant = service.allocate(_offer(lease_seconds=5))
    assert grant is not None
    service.activate_allocation(grant)
    audit = DurableKernelAudit(
        postgres_database,
        attempt_id=admission.binding.attempt_id,
        session_id=admission.binding.session_id,
        pwu_id=admission.binding.pwu_id,
        envelope_id=admission.binding.resource_envelope.envelope_id,
    )
    inference_request = InferenceRequest(
        attempt_id=admission.binding.attempt_id,
        session_id=admission.binding.session_id,
        step_sequence=1,
        objective=admission.contract.objective,
        working_plan=WorkingPlan(
            version=1, objective_reference=str(admission.contract.id),
            chosen_approach="write", approach_rationale="contract",
        ),
        context_facts=(), available_tools=(), residual_obligations=("targeted test",),
    )
    step_id = asyncio.run(audit.begin_inference(inference_request))
    proposal = ToolCallProposal(
        proposal_index=0, tool_identity="file.write",
        arguments={"path": "README.md", "content": "changed"},
    )
    asyncio.run(
        audit.finish_inference(
            step_id,
            InferenceResponse(
                action=InferenceAction.CONTINUE, summary="write",
                working_plan=inference_request.working_plan,
                tool_calls=(proposal,), residual_obligations=("targeted test",),
            ),
            None,
        )
    )
    tool_request = ToolExecutionRequest(
        delivery_id=uuid4(), attempt_id=admission.binding.attempt_id,
        worker_epoch=grant.allocation.lease_epoch, step_id=step_id,
        proposal=proposal, capability_grants=admission.binding.capability_grants,
        workspace=admission.binding.workspace,
    )
    effect_id = asyncio.run(audit.begin_tool(step_id, tool_request))
    output = {"path": "README.md", "bytes": 7}
    settled = ToolExecutionResult(
        delivery_id=tool_request.delivery_id, tool_identity="file.write",
        condition="SETTLED", output=output, output_digest=canonical_digest(output),
    )
    asyncio.run(audit.finish_tool(effect_id, tool_request, settled, None))
    clock[0] += timedelta(seconds=6)

    assert service.reconcile_expired_leases() == (admission.binding.attempt_id,)
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        recovered = store.tool_results_after(
            admission.binding.attempt_id, after_step_sequence=0
        )
        state = store.attempt_state(admission.binding.attempt_id)
        assert tuple(item.delivery_id for item in recovered) == (
            tool_request.delivery_id,
        )
        assert state.grant_state is AttemptGrantState.GRANTED
        assert state.effect_uncertainty is False
    successor = service.allocate(_offer())
    assert successor is not None
    assert successor.allocation.lease_epoch == grant.allocation.lease_epoch + 1


def test_provider_capacity_wait_releases_worker_and_requeues_after_backoff(
    postgres_database: Database, git_repository: Path
) -> None:
    clock = [datetime.now(timezone.utc)]
    service = NativeExecutorRuntimeService(postgres_database, now=lambda: clock[0])
    admission = _admission(postgres_database, git_repository).model_copy(
        update={"available_at": clock[0]}
    )
    service.admit(admission)
    grant = service.allocate(_offer())
    assert grant is not None
    service.activate_allocation(grant)
    service.finish_allocation(
        grant,
        KernelRunResult(
            runtime_mode=ExecutionMode.WAITING_RESOURCE,
            final_checkpoint_id=None,
            step_count=0,
            inference_submissions=0,
            tool_effects=0,
            summary="provider capacity unavailable",
            resource_retryable=True,
        ),
    )
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        waiting = store.queue_for_attempt(admission.binding.attempt_id)
        lease = uow.session.execute(select(executor_leases)).mappings().one()
        assert waiting is not None
        assert waiting.condition is QueueCondition.WAITING_RESOURCE
        assert waiting.resume_count == 1
        assert lease["released_at"] is not None
    assert service.allocate(_offer()) is None
    clock[0] += timedelta(seconds=31)
    assert service.allocate(_offer()) is not None


def test_self_refine_records_failure_repair_and_verified_resume(
    postgres_database: Database, git_repository: Path,
) -> None:
    clock = [datetime.now(timezone.utc)]
    service = NativeExecutorRuntimeService(postgres_database, now=lambda: clock[0])
    admission = _admission(postgres_database, git_repository).model_copy(
        update={"available_at": clock[0]}
    )
    service.admit(admission)
    first = service.allocate(_offer())
    assert first is not None
    service.activate_allocation(first)
    service.finish_allocation(first, KernelRunResult(
        runtime_mode=ExecutionMode.WAITING_RESOURCE, final_checkpoint_id=None,
        step_count=0, inference_submissions=1, tool_effects=0,
        summary="controlled transient provider disconnect", failure_family="PROVIDER_TRANSPORT",
        resource_retryable=True,
    ))
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        event = store.open_self_refine_event(admission.binding.attempt_id)
        assert event is not None
        assert event.work_id == admission.binding.work_id
        assert event.failure_family == "PROVIDER_TRANSPORT"
        assert event.expected_reality["outcome"] == "RESULT_READY"
        assert event.status == "OPEN"
        assert store.self_refine_actions(event.id)[0].outcome == "RETRY_SCHEDULED"
    clock[0] += timedelta(seconds=31)
    second = service.allocate(_offer())
    assert second is not None
    service.activate_allocation(second)
    service.finish_allocation(second, KernelRunResult(
        runtime_mode=ExecutionMode.FINISHED,
        terminal_outcome=AttemptTerminalOutcome.RESULT_READY,
        final_checkpoint_id=None, step_count=1,
        inference_submissions=1, tool_effects=1,
        summary="verified recovery",
    ))
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        completed = store.self_refine_event(event.id)
        assert completed.final_result == "RECOVERED"
        assert completed.refinement_class is RefinementClass.ROUTINE_STOCHASTIC_REFINEMENT
        assert completed.status == "VERIFIED"
        assert completed.work_resume_result == "RESUMED"
        assert [action.outcome for action in store.self_refine_actions(event.id)] == [
            "RETRY_SCHEDULED", "RECOVERED",
        ]
        metrics = store.self_refine_metrics(work_id=admission.binding.work_id)
        assert metrics["native_attempts"] == 1
        assert metrics["self_refine_events"] == 1
        assert metrics["recovered"] == 1
        assert metrics["self_refine_rate"] == 1.0


def test_routine_refinement_recurrence_promotes_economic_signal_without_incident(
    postgres_database: Database,
) -> None:
    signature_basis = f"repeatable-schema-variance:{uuid4()}"
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        events = [store.record_bounded_refinement(
            work_id=uuid4(), operation_id=uuid4(),
            component="steering/semantic-step",
            signal_kind=RefinementSignalKind.SCHEMA_INVALID,
            signature_basis=signature_basis,
            evidence_references=("semantic-test:bounded",),
            converged=True, attempt_count=2, elapsed_seconds=3,
            model_token_usage={"total_tokens": 7},
        ) for _ in range(4)]
        assert [event.refinement_class for event in events] == [
            RefinementClass.ROUTINE_STOCHASTIC_REFINEMENT,
            RefinementClass.ROUTINE_STOCHASTIC_REFINEMENT,
            RefinementClass.ROUTINE_STOCHASTIC_REFINEMENT,
            RefinementClass.DEGRADING_OR_RECURRING_REFINEMENT,
        ]
        assert all(event.observation_confidence is ObservationConfidence.OBSERVED_SUCCESS
                   for event in events)
        assert events[-1].platform_improvement_candidate_ref == (
            f"refinement-signature:{events[-1].failure_signature}"
        )
        metrics = store.self_refine_metrics()
        assert metrics["recurring_signatures"][events[-1].failure_signature] == 4
        assert metrics["observed_refinement_tokens"] >= 28
        assert any(candidate["reference"] == events[-1].platform_improvement_candidate_ref
                   and candidate["affected_works"] == 4
                   and candidate["status"] == "PROPOSED"
                   for candidate in metrics["improvement_candidates"])
        assert metrics["classification_counts"]["SYSTEMIC_OR_NON_CONVERGING_INCIDENT"] == 0
        assert metrics["human_escalation_rate"] == 0
        uow.commit()


def test_changed_reality_supersedes_refinement_without_false_incident(
    postgres_database: Database,
) -> None:
    with postgres_database.unit_of_work() as uow:
        event = NativeExecutionStore(uow.session).record_bounded_refinement(
            work_id=uuid4(), operation_id=uuid4(), component="steering/semantic-step",
            signal_kind=RefinementSignalKind.REALITY_MISMATCH,
            signature_basis=str(uuid4()), evidence_references=("step:stale",),
            converged=False, superseded=True, attempt_count=2,
        )
        assert event.final_result == "SUPERSEDED"
        assert event.refinement_class is RefinementClass.ROUTINE_STOCHASTIC_REFINEMENT
        assert event.observation_confidence is ObservationConfidence.INCONCLUSIVE
        uow.commit()


def test_human_escalation_metric_requires_explicit_human_boundary(
    postgres_database: Database,
) -> None:
    work_id = uuid4()
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        events = []
        for requires_human in (False, True):
            event = store.record_bounded_refinement(
                work_id=work_id, operation_id=uuid4(), component="semantic-test",
                signal_kind=RefinementSignalKind.CONTRACT_MISMATCH,
                signature_basis=str(uuid4()), evidence_references=("semantic-test:boundary",),
                converged=False, authority_required=requires_human, attempt_count=2,
            )
            assert event.budget_decision["human_escalated"] is requires_human
            events.append(event)
        store.insert_self_refine_event(events[0].model_copy(update={
            "id": uuid4(), "operation_id": uuid4(), "semantic_version": 1,
            "refinement_class": RefinementClass.LEGACY_EXECUTION_INCIDENT,
            "budget_decision": {},
        }))
        metrics = store.self_refine_metrics(work_id=work_id)
        assert metrics["human_escalation_observation_count"] == 2
        assert metrics["human_escalation_rate"] == 0.5
        uow.commit()


def test_legacy_refinement_row_keeps_historical_incident_meaning(
    postgres_database: Database,
) -> None:
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        template = store.record_bounded_refinement(
            work_id=uuid4(), operation_id=uuid4(), component="legacy-test",
            signal_kind=RefinementSignalKind.EXECUTION_FAILURE,
            signature_basis=str(uuid4()), evidence_references=("legacy-test:1",),
            converged=True, attempt_count=2,
        )
        values = template.model_dump(mode="json")
        values.update(id=uuid4(), operation_id=uuid4(), status="OPEN",
                      final_result=None, work_resume_result=None)
        for field in ("semantic_version", "refinement_class", "signal_kind"):
            values.pop(field)
        uow.session.execute(insert(self_refine_events).values(**values))
        historical = store.self_refine_event(values["id"])
        assert historical.semantic_version == 1
        assert historical.refinement_class is RefinementClass.LEGACY_EXECUTION_INCIDENT
        store.complete_self_refine_event(
            historical.id, result="RECOVERED", resume_result="RESUMED",
            status="VERIFIED", elapsed_seconds=1,
            updated_at=datetime.now(timezone.utc), compute_overhead={},
        )
        assert store.self_refine_event(historical.id).refinement_class is (
            RefinementClass.LEGACY_EXECUTION_INCIDENT
        )
        uow.commit()


def test_refinement_semantic_migration_preserves_preexisting_failure_record(
    postgres_database: Database,
) -> None:
    with postgres_database.unit_of_work() as uow:
        template = NativeExecutionStore(uow.session).record_bounded_refinement(
            work_id=uuid4(), operation_id=uuid4(), component="native-executor/provider",
            signal_kind=RefinementSignalKind.EXECUTION_FAILURE,
            signature_basis=str(uuid4()), evidence_references=("attempt:historical",),
            converged=True, attempt_count=2,
        )
        uow.commit()
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260925_47")
    assert "semantic_version" not in {
        column["name"] for column in inspect(postgres_database.engine).get_columns("self_refine_events")
    }
    values = template.model_dump(mode="json")
    values.update(id=uuid4(), operation_id=uuid4(), status="OPEN",
                  final_result=None, work_resume_result=None)
    for field in ("semantic_version", "refinement_class", "signal_kind"):
        values.pop(field)
    with postgres_database.unit_of_work() as uow:
        uow.session.execute(insert(self_refine_events).values(**values))
        uow.commit()
    command.upgrade(config, "head")
    with postgres_database.unit_of_work() as uow:
        restored = NativeExecutionStore(uow.session).self_refine_event(values["id"])
        assert restored.semantic_version == 1
        assert restored.refinement_class is RefinementClass.LEGACY_EXECUTION_INCIDENT


def test_self_refine_api_filters_by_semantic_class_without_rewriting_records(
    postgres_database: Database,
) -> None:
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        event = store.record_bounded_refinement(
            work_id=uuid4(), operation_id=uuid4(), component="steering/semantic-step",
            signal_kind=RefinementSignalKind.CONTRACT_MISMATCH,
            signature_basis=str(uuid4()), evidence_references=("step:bounded",),
            converged=True, attempt_count=2,
        )
        uow.commit()
    app = create_http_application(
        application=object(), database=postgres_database,
        work_service=SimpleNamespace(database=postgres_database),
        orchestrator=SimpleNamespace(shutdown=lambda: None),
        steering_driver=SimpleNamespace(shutdown=lambda: None),
        runtime_activation=SimpleNamespace(project=lambda: None),
    )
    client = TestClient(app)
    response = client.get("/api/self-refine", params={
        "refinement_class": RefinementClass.ROUTINE_STOCHASTIC_REFINEMENT.value,
    })
    assert response.status_code == 200
    assert any(item["id"] == str(event.id) for item in response.json()["events"])
    assert client.get("/api/self-refine", params={"refinement_class": "INVALID"}).status_code == 422


def test_self_converge_stops_repeated_unchanged_failure(
    postgres_database: Database, git_repository: Path,
) -> None:
    clock = [datetime.now(timezone.utc)]
    service = NativeExecutorRuntimeService(
        postgres_database, now=lambda: clock[0], same_failure_threshold=2,
    )
    admission = _admission(postgres_database, git_repository).model_copy(
        update={"available_at": clock[0]}
    )
    service.admit(admission)
    for attempt_number in range(2):
        if attempt_number:
            clock[0] += timedelta(seconds=31)
        grant = service.allocate(_offer())
        assert grant is not None
        service.activate_allocation(grant)
        service.finish_allocation(grant, KernelRunResult(
            runtime_mode=ExecutionMode.WAITING_RESOURCE,
            final_checkpoint_id=None, step_count=0,
            inference_submissions=1, tool_effects=0,
            summary="same controlled failure", failure_family="PROVIDER_TRANSPORT",
            resource_retryable=True,
        ))
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        event = store.list_self_refine_events(work_id=admission.binding.work_id)[0]
        assert event.final_result == "ESCALATED"
        assert event.refinement_class is RefinementClass.SYSTEMIC_OR_NON_CONVERGING_INCIDENT
        assert event.platform_improvement_candidate_ref == (
            f"refinement-signature:{event.failure_signature}"
        )
        assert event.work_resume_result == "NOT_RESUMED"
        assert event.status == "MITIGATED"
        assert event.budget_decision["policy_version"] == "adaptive-self-converge-v1"
        assert event.budget_decision["remaining"]["same_signature"] == 0
        assert event.budget_decision["allow_retry"] is False
        assert [action.outcome for action in store.self_refine_actions(event.id)] == [
            "RETRY_SCHEDULED", "ESCALATED",
        ]
        assert store.self_refine_actions(event.id)[0].observed_reality["budget_decision"]["allow_retry"] is True
        assert store.queue_for_attempt(admission.binding.attempt_id).condition is QueueCondition.COMPLETED
    clock[0] += timedelta(seconds=31)
    assert service.allocate(_offer()) is None


def test_transient_health_noise_resolves_without_self_refine(
    postgres_database: Database, git_repository: Path,
) -> None:
    clock = [datetime.now(timezone.utc)]
    service = NativeExecutorRuntimeService(postgres_database, now=lambda: clock[0])
    admission = _admission(postgres_database, git_repository).model_copy(
        update={"available_at": clock[0]}
    )
    service.admit(admission)
    first = service.allocate(_offer())
    assert first is not None
    service.activate_allocation(first)
    service.finish_allocation(first, KernelRunResult(
        runtime_mode=ExecutionMode.WAITING_RESOURCE, final_checkpoint_id=None,
        step_count=0, inference_submissions=0, tool_effects=0,
        summary="startup health probe timeout", failure_family="RUNTIME_HEALTH",
        observation_evidence={"health_probe_count": 1},
    ))
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        assert store.list_self_refine_events(work_id=admission.binding.work_id) == ()
        assert store.queue_for_attempt(admission.binding.attempt_id).condition is QueueCondition.WAITING_RESOURCE
        events = uow.session.execute(select(execution_events.c.event_type, execution_events.c.payload)).all()
        assert any(
            kind == "NativeObservationClassified"
            and payload["classification"] == ObservationConfidence.TRANSIENT_ANOMALY.value
            for kind, payload in events
        )
    clock[0] += timedelta(seconds=31)
    second = service.allocate(_offer())
    assert second is not None
    service.activate_allocation(second)
    service.finish_allocation(second, KernelRunResult(
        runtime_mode=ExecutionMode.FINISHED,
        terminal_outcome=AttemptTerminalOutcome.RESULT_READY,
        final_checkpoint_id=None, step_count=1,
        inference_submissions=0, tool_effects=0, summary="health recovered",
    ))
    with postgres_database.unit_of_work() as uow:
        assert NativeExecutionStore(uow.session).list_self_refine_events(
            work_id=admission.binding.work_id,
        ) == ()


def test_stable_health_failure_is_confirmed_before_self_refine(
    postgres_database: Database, git_repository: Path,
) -> None:
    clock = [datetime.now(timezone.utc)]
    service = NativeExecutorRuntimeService(postgres_database, now=lambda: clock[0])
    admission = _admission(postgres_database, git_repository).model_copy(
        update={"available_at": clock[0]}
    )
    service.admit(admission)
    for number in range(2):
        if number:
            clock[0] += timedelta(seconds=31)
        grant = service.allocate(_offer())
        assert grant is not None
        service.activate_allocation(grant)
        service.finish_allocation(grant, KernelRunResult(
            runtime_mode=ExecutionMode.WAITING_RESOURCE, final_checkpoint_id=None,
            step_count=0, inference_submissions=0, tool_effects=0,
            summary="startup health probe timeout", failure_family="RUNTIME_HEALTH",
            observation_evidence={"health_probe_count": number + 1},
        ))
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        events = store.list_self_refine_events(work_id=admission.binding.work_id)
        assert len(events) == 1
        assert events[0].observation_confidence is ObservationConfidence.CONFIRMED_FAILURE
        assert events[0].repairability is RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE
        assert store.self_refine_actions(events[0].id)[0].outcome == "RETRY_SCHEDULED"


def test_authoritative_git_mismatch_is_confirmed_without_debounce(
    postgres_database: Database, git_repository: Path,
) -> None:
    observed_branch = _git(git_repository, "branch", "--show-current")
    assert observed_branch == "main"
    service = NativeExecutorRuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    service.admit(admission)
    grant = service.allocate(_offer())
    assert grant is not None
    service.activate_allocation(grant)
    service.finish_allocation(grant, KernelRunResult(
        runtime_mode=ExecutionMode.WAITING_RESOURCE, final_checkpoint_id=None,
        step_count=0, inference_submissions=0, tool_effects=0,
        summary="branch remains main after branch.create",
        failure_family="REPOSITORY_REALITY_MISMATCH",
        observation_evidence={
            "authoritative_state_mismatch": True,
            "expected_revision": "refs/heads/feat_test",
            "observed_revision": f"refs/heads/{observed_branch}",
        },
    ))
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        event = store.list_self_refine_events(work_id=admission.binding.work_id)[0]
        assert event.observation_confidence is ObservationConfidence.CONFIRMED_FAILURE
        assert event.observed_reality["observation_evidence"]["observed_revision"] == "refs/heads/main"
        assert store.self_refine_actions(event.id)[0].outcome == "RETRY_SCHEDULED"


def test_adaptive_repair_budget_uses_scope_risk_and_observed_token_usage(
    postgres_database: Database, git_repository: Path,
) -> None:
    service = NativeExecutorRuntimeService(postgres_database, self_refine_token_budget=100)
    admitted = _admission(postgres_database, git_repository)
    small = {"task_contract": {
        "scope": ["README.md"], "acceptance_meaning": ["README renders"],
        "evidence_requirements": ["preview"], "required_capabilities": ["file.write"],
    }}
    arguments = dict(
        binding=admitted.binding, family="PROVIDER_TRANSPORT",
        repairability=RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE,
        queue_resume_count=0, same_failures=1, elapsed=1,
        inference_total=1, tool_total=1, observed_tokens=20,
    )
    simple = service._adaptive_budget(contract_payload=small, **arguments)
    assert simple["complexity"] == "SMALL"
    assert simple["risk"] == "NORMAL"
    assert simple["limits"]["attempts"] == 2
    assert simple["remaining"]["model_tokens"] == 80
    assert simple["allow_retry"] is True

    large = {"task_contract": {**small["task_contract"],
        "scope": [f"src/module_{index}.py" for index in range(10)],
    }}
    assert service._adaptive_budget(contract_payload=large, **arguments)["limits"]["attempts"] == 3

    migration = {"task_contract": {**large["task_contract"], "activity": "MIGRATION"}}
    migration_budget = service._adaptive_budget(contract_payload=migration, **arguments)
    assert migration_budget["risk"] == "HIGH"
    assert migration_budget["risk_factors"] == ["high_impact_engineering_activity"]
    assert migration_budget["limits"]["attempts"] == 1

    second_mount = admitted.binding.workspace.mounts[0].model_copy(update={
        "mount_id": "secondary", "container_path": "/workspace/secondary",
    })
    higher_risk = admitted.binding.model_copy(update={"workspace":
        admitted.binding.workspace.model_copy(update={"mounts": (
            *admitted.binding.workspace.mounts, second_mount,
        )}),
    })
    constrained = service._adaptive_budget(
        contract_payload=large, **{**arguments, "binding": higher_risk},
    )
    assert constrained["risk"] == "HIGH"
    assert constrained["risk_factors"] == ["multiple_writable_mounts"]
    assert constrained["limits"]["attempts"] == 1
    exhausted = service._adaptive_budget(
        contract_payload=small, **{**arguments, "observed_tokens": 100},
    )
    assert exhausted["allow_retry"] is False
    assert exhausted["remaining"]["model_tokens"] == 0


def _business_admission(
    database: Database, repository: Path, *, acceptance_meaning: str,
) -> NativeExecutionAdmission:
    admitted = _admission(database, repository, contract_payload={
        "objective": "correct the tax result without changing product intent",
        "task_contract": {
            "acceptance_meaning": [acceptance_meaning],
            "authority_lineage": ["human:explicit-tax-requirement"],
            "scope": ["README.md"],
            "evidence_requirements": ["tax assertion must pass"],
        },
    })
    binding = admitted.binding.model_copy(update={
        "capability_grants": (
            *admitted.binding.capability_grants,
            CapabilityGrant(identity="test.run", version="1", scope={}),
        ),
        "resource_envelope": admitted.binding.resource_envelope.model_copy(update={
            "max_inference_submissions": 6,
        }),
    })
    return admitted.model_copy(update={"binding": binding})


def test_explicit_business_oracle_repairs_verifies_and_resumes_without_human(
    postgres_database: Database, git_repository: Path, tmp_path: Path,
) -> None:
    (git_repository / "README.md").write_text("tax=13\n", encoding="utf-8")
    _git(git_repository, "add", "README.md")
    _git(git_repository, "commit", "-m", "initial tax behavior")
    admitted = _business_admission(
        postgres_database, git_repository, acceptance_meaning="tax = 6",
    )
    runtime = NativeExecutorRuntimeService(postgres_database)
    runtime.admit(admitted)
    plan = WorkingPlan(
        version=1, objective_reference=str(admitted.contract.id),
        chosen_approach="verify and correct admitted tax assertion",
        approach_rationale="explicit Human oracle in Task Contract",
    )
    inference = ScriptedInferenceAdapter((
        InferenceResponse(action=InferenceAction.CONTINUE, summary="run tax assertion",
            working_plan=plan, tool_calls=(ToolCallProposal(
                proposal_index=0, tool_identity="test.run", arguments={"recipe": "tax"},
            ),), residual_obligations=("tax assertion",)),
        InferenceResponse(action=InferenceAction.CONTINUE, summary="correct tax implementation",
            working_plan=plan.model_copy(update={"version": 2}), tool_calls=(ToolCallProposal(
                proposal_index=0, tool_identity="file.write",
                arguments={"path": "README.md", "content": "tax=6\n"},
            ),), residual_obligations=("tax assertion",)),
        InferenceResponse(action=InferenceAction.CONTINUE, summary="rerun tax assertion",
            working_plan=plan.model_copy(update={"version": 3}), tool_calls=(ToolCallProposal(
                proposal_index=0, tool_identity="test.run", arguments={"recipe": "tax"},
            ),), residual_obligations=("tax assertion",)),
        InferenceResponse(action=InferenceAction.RESULT_READY, summary="tax oracle verified",
            working_plan=plan.model_copy(update={"version": 4}),
            result_claim={"output_vector": {"files": ["README.md"]}, "evidence_ids": []},
            residual_obligations=()),
    ))

    async def run_tax(request: ToolExecutionRequest) -> ToolExecutionResult:
        observed = int((git_repository / "README.md").read_text(encoding="utf-8").strip().split("=")[1])
        completed = subprocess.run(
            [sys.executable, "-c", "from pathlib import Path; assert Path('README.md').read_text().strip() == 'tax=6'"],
            cwd=git_repository, capture_output=True, text=True, check=False,
        )
        output = {
            "returncode": completed.returncode,
            "test_identity": "tax_is_six",
            "assertion": {"id": "tax", "expected": 6, "observed": observed},
            "stderr": completed.stderr,
        }
        return ToolExecutionResult(
            delivery_id=request.delivery_id, tool_identity="test.run",
            condition=EffectCondition.SETTLED if completed.returncode == 0 else EffectCondition.FAILED,
            output=output, output_digest=canonical_digest(output),
            evidence=({"type": "TEST_ASSERTION", "test_identity": "tax_is_six"},),
        )

    async def write_tax(request: ToolExecutionRequest) -> ToolExecutionResult:
        (git_repository / "README.md").write_text(
            str(request.proposal.arguments["content"]), encoding="utf-8",
        )
        output = {"path": "README.md", "changed_files": ["README.md"]}
        return ToolExecutionResult(
            delivery_id=request.delivery_id, tool_identity="file.write",
            condition=EffectCondition.SETTLED, output=output,
            output_digest=canonical_digest(output),
        )

    tools = NativeToolRegistry((
        ToolDefinition("test.run", "1", "run tax assertion", {}, "PROCESS", run_tax),
        ToolDefinition("file.write", "1", "correct tax file", {}, "LOCAL_MUTATION", write_tax),
    ))

    def kernel_factory(grant):
        return NativeExecutorKernel(
            inference=inference, tools=tools,
            audit=DurableKernelAudit(
                postgres_database, attempt_id=admitted.binding.attempt_id,
                session_id=admitted.binding.session_id,
                pwu_id=admitted.binding.pwu_id,
                envelope_id=admitted.binding.resource_envelope.envelope_id,
            ),
            checkpoints=DurableCheckpointPort(
                postgres_database, ContentAddressedStorage(tmp_path / "tax-checkpoints"),
                attempt_id=admitted.binding.attempt_id,
                session_id=admitted.binding.session_id,
                worker_epoch=grant.allocation.lease_epoch,
            ),
        )

    offer = _offer().model_copy(update={"capability_identities": ("file.write", "test.run")})
    assert asyncio.run(NativeExecutionWorker(runtime, kernel_factory).run_once(offer)) is True
    assert (git_repository / "README.md").read_text(encoding="utf-8") == "tax=6\n"
    assert len(inference.requests) == 4
    assert any(
        fact.get("fact_type") == "RECENT_SELF_REFINE"
        and fact["events"][0]["repairability"] == RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE.value
        for fact in inference.requests[1].context_facts
    )
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        state = store.attempt_state(admitted.binding.attempt_id)
        event = store.list_self_refine_events(work_id=admitted.binding.work_id)[0]
        assert state.terminal_outcome is AttemptTerminalOutcome.RESULT_READY
        assert event.repairability is RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE
        assert event.final_result == "RECOVERED"
        assert event.work_resume_result == "RESUMED"
        assert event.diagnostic_evidence["test_identity"] == "tax_is_six"
        assert event.diagnostic_evidence["assertion_id"] == "tax"
        assert event.diagnostic_evidence["stderr_ref"].startswith("native-receipt:")
        assert len(event.evidence_references) == 3
        assert [action.outcome for action in store.self_refine_actions(event.id)] == [
            "RETRY_SCHEDULED", "RECOVERED",
        ]


def test_ambiguous_business_truth_escalates_without_code_mutation(
    postgres_database: Database, git_repository: Path, tmp_path: Path,
) -> None:
    admitted = _business_admission(
        postgres_database, git_repository, acceptance_meaning="tax depends on product policy",
    )
    runtime = NativeExecutorRuntimeService(postgres_database)
    runtime.admit(admitted)
    plan = WorkingPlan(
        version=1, objective_reference=str(admitted.contract.id),
        chosen_approach="check tax behavior", approach_rationale="product choice is unresolved",
    )
    inference = ScriptedInferenceAdapter((InferenceResponse(
        action=InferenceAction.CONTINUE, summary="observe ambiguous assertion",
        working_plan=plan, tool_calls=(ToolCallProposal(
            proposal_index=0, tool_identity="test.run", arguments={"recipe": "tax"},
        ),), residual_obligations=("Human tax decision",),
    ),))
    writes: list[str] = []

    async def ambiguous_test(request: ToolExecutionRequest) -> ToolExecutionResult:
        output = {"returncode": 1, "test_identity": "tax_policy",
                  "assertion": {"id": "tax", "observed": 13, "alternatives": [6, 8]},
                  "product_choice_required": True}
        return ToolExecutionResult(
            delivery_id=request.delivery_id, tool_identity="test.run",
            condition=EffectCondition.FAILED, output=output,
            output_digest=canonical_digest(output),
        )

    async def forbidden_write(request: ToolExecutionRequest) -> ToolExecutionResult:
        writes.append(str(request.proposal.arguments))
        raise AssertionError("ambiguous truth must not cause a mutation")

    tools = NativeToolRegistry((
        ToolDefinition("test.run", "1", "observe tax", {}, "PROCESS", ambiguous_test),
        ToolDefinition("file.write", "1", "write tax", {}, "LOCAL_MUTATION", forbidden_write),
    ))

    def kernel_factory(grant):
        return NativeExecutorKernel(
            inference=inference, tools=tools,
            audit=DurableKernelAudit(
                postgres_database, attempt_id=admitted.binding.attempt_id,
                session_id=admitted.binding.session_id,
                pwu_id=admitted.binding.pwu_id,
                envelope_id=admitted.binding.resource_envelope.envelope_id,
            ),
            checkpoints=DurableCheckpointPort(
                postgres_database, ContentAddressedStorage(tmp_path / "ambiguous-checkpoints"),
                attempt_id=admitted.binding.attempt_id,
                session_id=admitted.binding.session_id,
                worker_epoch=grant.allocation.lease_epoch,
            ),
        )

    offer = _offer().model_copy(update={"capability_identities": ("file.write", "test.run")})
    assert asyncio.run(NativeExecutionWorker(runtime, kernel_factory).run_once(offer)) is True
    assert writes == []
    assert len(inference.requests) == 1
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        state = store.attempt_state(admitted.binding.attempt_id)
        event = store.list_self_refine_events(work_id=admitted.binding.work_id)[0]
        assert state.terminal_outcome is AttemptTerminalOutcome.BOUNDARY_CROSSING_REQUIRED
        assert event.repairability is RepairabilityClassification.REQUIRES_HUMAN_DECISION
        assert event.final_result == "ESCALATED"
        assert event.work_resume_result == "NOT_RESUMED"


def test_queue_without_live_compatible_worker_becomes_truthful_and_recovers(
    postgres_database: Database, git_repository: Path
) -> None:
    clock = [datetime.now(timezone.utc)]
    service = NativeExecutorRuntimeService(postgres_database, now=lambda: clock[0])
    admission = _admission(postgres_database, git_repository).model_copy(
        update={"available_at": clock[0]}
    )
    queued = service.admit(admission)

    initial = service.list_queue_reality(
        work_id=admission.binding.work_id,
        unavailable_after=timedelta(seconds=5),
    )[0][1]
    assert initial.progression_state is QueueProgressionState.SCHEDULING
    assert initial.scheduler_alive is False

    clock[0] += timedelta(seconds=6)
    assert service.reconcile_queue_ownership(
        unavailable_after=timedelta(seconds=5)
    ) == (queued.id,)
    unavailable = service.list_queue_reality(
        work_id=admission.binding.work_id,
        unavailable_after=timedelta(seconds=5),
    )[0]
    assert unavailable[0].condition is QueueCondition.WAITING_RESOURCE
    assert unavailable[1].progression_state is QueueProgressionState.INFRASTRUCTURE_UNAVAILABLE
    assert "recover automatically" in unavailable[1].reason

    restarted_service = NativeExecutorRuntimeService(
        postgres_database, now=lambda: clock[0]
    )
    recovered = restarted_service.allocate(_offer())
    assert recovered is not None
    assert recovered.queue_entry.id == queued.id


def test_live_busy_worker_is_real_capacity_wait_and_release_advances_next_item(
    postgres_database: Database, git_repository: Path
) -> None:
    clock = [datetime.now(timezone.utc)]
    service = NativeExecutorRuntimeService(postgres_database, now=lambda: clock[0])
    first = _admission(postgres_database, git_repository).model_copy(
        update={"available_at": clock[0]}
    )
    second = _admission(postgres_database, git_repository).model_copy(
        update={"available_at": clock[0]}
    )
    first_queue = service.admit(first)
    second_queue = service.admit(second)
    first_grant = service.allocate(_offer())
    assert first_grant is not None
    service.activate_allocation(first_grant)

    pending_work_id, pending_queue = (
        (second.binding.work_id, second_queue)
        if first_grant.queue_entry.id == first_queue.id
        else (first.binding.work_id, first_queue)
    )

    second_reality = service.list_queue_reality(
        work_id=pending_work_id
    )[0][1]
    assert second_reality.progression_state is QueueProgressionState.CAPACITY_WAIT
    assert second_reality.compatible_worker_count == 1
    assert second_reality.occupied_worker_count == 1

    service.finish_allocation(
        first_grant,
        KernelRunResult(
            runtime_mode=ExecutionMode.FINISHED,
            terminal_outcome=AttemptTerminalOutcome.UNABLE_TO_COMPLETE,
            final_checkpoint_id=None,
            step_count=0,
            inference_submissions=0,
            tool_effects=0,
            summary="bounded capacity test finished",
        ),
    )
    next_grant = service.allocate(_offer())
    assert next_grant is not None
    assert next_grant.queue_entry.id == pending_queue.id


def test_two_ready_pwus_of_one_work_receive_distinct_concurrent_worker_leases(
    postgres_database: Database, git_repository: Path,
) -> None:
    """MPWU-Q2: the existing capacity scheduler actually leases both DAG roots."""

    runtime = RuntimeService(postgres_database)
    baseline = runtime.bootstrap_trusted_baseline(BootstrapRequest(
        repository_path=git_repository, repository_identity=str(git_repository),
        repository_ref="refs/heads/main", authority_identity="human:test",
    )).snapshot
    shared_work_id = uuid4()
    targets = tuple(ProductionPlanArtifactTarget(
        path=f"docs/{name}.md", operation=PlannedArtifactOperation.CREATE,
    ) for name in ("alpha", "beta"))
    plan = RuleBasedProductionPlanner().propose(ProductionPlanningRequest(
        work_id=shared_work_id, admitted_requirement="Produce independent alpha and beta",
        desired_outcome="Both outputs", production_objective="Produce both outputs",
        artifact_targets=targets, verification_expectation="targeted test",
        engineering_scope_summary="one repository", engineering_resource_id=uuid4(),
        repository_identity=str(git_repository), source_baseline_id=baseline.id,
        source_revision=baseline.repository_revision,
    ))
    spine = runtime.create_initial_runtime_spine(InitialRunRequest(
        intent_ref=f"work:{shared_work_id}", goal="Both outputs",
        production_horizon=ProductionHorizon.DOCUMENTATION,
        initial_work_unit_objective="Produce both outputs",
        completion_contract=CompletionContract(
            required_outputs=tuple(item.path for item in targets),
            required_changes=tuple(item.path for item in targets),
            verification_obligations=("targeted test",), production_plan=plan,
        ),
    ))
    with postgres_database.unit_of_work() as uow:
        units = RuntimeStore(uow.session).work_units_for_plan(spine.plan_revision.id)
    roots = tuple(item for item in units if item.node_id in {"pwu:1", "pwu:2"})
    assert len(roots) == 2 and {item.source_baseline_id for item in roots} == {baseline.id}
    admissions = []
    service = NativeExecutorRuntimeService(postgres_database)
    for unit in roots:
        attempt = runtime.create_initial_attempt(unit.id)
        admissions.append(_admission(
            postgres_database, git_repository,
            spine_attempt=(spine.model_copy(update={"work_unit": unit}), attempt),
            work_id=shared_work_id,
        ))
    for admission in admissions:
        service.admit(admission)
    first = service.allocate(_offer())
    assert first is not None
    service.activate_allocation(first)
    second_offer = _offer().model_copy(update={"worker_id": "worker:parallel-two"})
    second = service.allocate(second_offer)
    assert second is not None
    service.activate_allocation(second)
    assert first.allocation.pwu_id != second.allocation.pwu_id
    assert first.queue_entry.work_id == second.queue_entry.work_id == shared_work_id
    assert admissions[0].binding.source_vector.digest == admissions[1].binding.source_vector.digest


def test_retryable_provider_failure_stops_at_adaptive_small_task_budget(
    postgres_database: Database, git_repository: Path
) -> None:
    clock = [datetime.now(timezone.utc)]
    service = NativeExecutorRuntimeService(
        postgres_database, now=lambda: clock[0], same_failure_threshold=5,
    )
    admission = _admission(postgres_database, git_repository).model_copy(
        update={"available_at": clock[0]}
    )
    service.admit(admission)

    for retry_number in range(3):
        grant = service.allocate(_offer())
        assert grant is not None, f"expected retry allocation {retry_number}"
        service.activate_allocation(grant)
        service.finish_allocation(
            grant,
            KernelRunResult(
                runtime_mode=ExecutionMode.WAITING_RESOURCE,
                final_checkpoint_id=None,
                step_count=0,
                inference_submissions=0,
                tool_effects=0,
                summary="provider response transport was interrupted",
                resource_retryable=True,
            ),
        )
        if retry_number < 2:
            clock[0] += timedelta(seconds=31)

    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        queue = store.queue_for_attempt(admission.binding.attempt_id)
        state = store.attempt_state(admission.binding.attempt_id)
        assert queue is not None
        assert queue.condition is QueueCondition.COMPLETED
        assert queue.resume_count == 2
        assert state.runtime_mode is ExecutionMode.FINISHED
        assert state.terminal_outcome is AttemptTerminalOutcome.UNABLE_TO_COMPLETE
        events = store.list_self_refine_events(work_id=admission.binding.work_id)
        assert len(events) == 1
        assert events[0].budget_decision["complexity"] == "SMALL"
        assert events[0].budget_decision["limits"]["attempts"] == 2
        assert events[0].budget_decision["remaining"]["attempts"] == 0
        assert [action.outcome for action in store.self_refine_actions(events[0].id)] == [
            "RETRY_SCHEDULED", "RETRY_SCHEDULED", "ESCALATED",
        ]
    assert service.allocate(_offer()) is None


def test_event_replay_uses_monotonic_pwu_sequence(
    postgres_database: Database, git_repository: Path
) -> None:
    service = NativeExecutorRuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    service.admit(admission)
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        all_events = store.events_since(admission.binding.pwu_id)
        assert [event.sequence for event in all_events] == [1]
        assert store.events_since(
            admission.binding.pwu_id, after_sequence=1
        ) == ()


def test_slow_subscriber_replay_is_bounded_and_loses_no_milestone(
    postgres_database: Database, git_repository: Path
) -> None:
    service = NativeExecutorRuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    service.admit(admission)
    created_at = datetime.now(timezone.utc)
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        for sequence in range(2, 602):
            store.append_event(
                ExecutionEventRecord(
                    id=uuid4(), pwu_id=admission.binding.pwu_id,
                    attempt_id=admission.binding.attempt_id,
                    sequence=sequence,
                    event_type="QualificationMilestone",
                    payload={"sequence": sequence},
                    correlation_id=admission.binding.pwu_id,
                    created_at=created_at + timedelta(microseconds=sequence),
                )
            )
        uow.commit()
    replayed = []
    cursor = 0
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        while True:
            batch = store.events_since(
                admission.binding.pwu_id, after_sequence=cursor
            )
            if not batch:
                break
            assert len(batch) <= 256
            replayed.extend(batch)
            cursor = batch[-1].sequence
    assert [event.sequence for event in replayed] == list(range(1, 602))


def test_outbox_replays_same_event_after_publish_before_ack_crash(
    postgres_database: Database, git_repository: Path
) -> None:
    service = NativeExecutorRuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    service.admit(admission)
    now = datetime.now(timezone.utc)

    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        first = store.claim_outbox(now=now, lease_seconds=5)
        assert len(first) == 1
        event_id = first[0].id
        assert store.event_sequence_window(admission.binding.pwu_id) == (1, 1)
        uow.commit()

    # Simulate relay death after publication and before durable acknowledgement.
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        assert store.claim_outbox(now=now + timedelta(seconds=4)) == ()
        replay = store.claim_outbox(now=now + timedelta(seconds=6))
        assert tuple(item.id for item in replay) == (event_id,)
        store.acknowledge_outbox(
            event_id, published_at=now + timedelta(seconds=6)
        )
        uow.commit()

    with postgres_database.unit_of_work() as uow:
        row = uow.session.execute(select(event_outbox)).mappings().one()
        assert row["condition"] == "PUBLISHED"
        assert row["attempt_count"] == 2


def test_inference_resource_reservation_is_settled_with_durable_evidence(
    postgres_database: Database, git_repository: Path
) -> None:
    service = NativeExecutorRuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    service.admit(admission)
    audit = DurableKernelAudit(
        postgres_database,
        attempt_id=admission.binding.attempt_id,
        session_id=admission.binding.session_id,
        pwu_id=admission.binding.pwu_id,
        envelope_id=admission.binding.resource_envelope.envelope_id,
    )
    plan = WorkingPlan(
        version=1,
        objective_reference=str(admission.contract.id),
        chosen_approach="observe first",
        approach_rationale="bounded qualification",
    )
    request = InferenceRequest(
        attempt_id=admission.binding.attempt_id,
        session_id=admission.binding.session_id,
        step_sequence=1,
        objective=admission.contract.objective,
        working_plan=plan,
        context_facts=(),
        available_tools=(),
        residual_obligations=(),
    )
    step_id = asyncio.run(audit.begin_inference(request))
    response = InferenceResponse(
        action=InferenceAction.RESULT_READY,
        summary="qualification inference complete",
        working_plan=plan,
        result_claim={"output_vector": {"files": []}},
    )
    asyncio.run(audit.finish_inference(step_id, response, None))
    with postgres_database.unit_of_work() as uow:
        row = uow.session.execute(select(execution_resource_usage)).mappings().one()
        assert row["reservation_key"] == f"inference:{step_id}"
        assert row["resource_type"] == "inference_submission"
        assert row["certainty"] == "ACTUAL"
        assert row["condition"] == "CONSUMED"
        assert row["evidence"]["response_observed"] is True


def test_structural_decision_repair_is_durable_and_recovers_same_attempt(
    postgres_database: Database, git_repository: Path,
) -> None:
    service = NativeExecutorRuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    service.admit(admission)
    grant = service.allocate(_offer())
    assert grant is not None
    service.activate_allocation(grant)
    audit = DurableKernelAudit(
        postgres_database,
        attempt_id=admission.binding.attempt_id,
        session_id=admission.binding.session_id,
        pwu_id=admission.binding.pwu_id,
        envelope_id=admission.binding.resource_envelope.envelope_id,
    )
    request = InferenceRequest(
        attempt_id=admission.binding.attempt_id,
        session_id=admission.binding.session_id,
        step_sequence=1,
        objective=admission.contract.objective,
        working_plan=WorkingPlan(
            version=1, objective_reference=str(admission.contract.id),
            chosen_approach="validate decision", approach_rationale="bounded qualification",
        ),
        context_facts=(), available_tools=(), residual_obligations=(),
    )
    step_id = asyncio.run(audit.begin_inference(request))
    asyncio.run(audit.finish_inference(
        step_id, None,
        InferenceDecisionRejected("TOOL_ARGUMENTS_NOT_OBJECT", "invalid provider shape"),
    ))
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        event = store.open_self_refine_event(admission.binding.attempt_id)
        assert event is not None
        assert event.work_id == admission.binding.work_id
        assert event.failure_family == "SEMANTIC_BINDING_FAILURE"
        assert event.expected_reality["outcome"] == "VALID_GOVERNED_DECISION"
        actions = store.self_refine_actions(event.id)
        assert len(actions) == 1
        assert actions[0].outcome == "RETRY_SCHEDULED"
        assert actions[0].evidence_references == (f"native-inference-step:{step_id}",)
    service.finish_allocation(grant, KernelRunResult(
        runtime_mode=ExecutionMode.FINISHED,
        terminal_outcome=AttemptTerminalOutcome.RESULT_READY,
        final_checkpoint_id=None,
        step_count=2, inference_submissions=2, tool_effects=0,
        summary="validated constrained decision without tool replay",
    ))
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        recovered = store.self_refine_event(event.id)
        assert recovered.final_result == "RECOVERED"
        assert recovered.status == "VERIFIED"
        assert recovered.work_resume_result == "RESUMED"
        assert [action.outcome for action in store.self_refine_actions(event.id)] == [
            "RETRY_SCHEDULED", "RECOVERED",
        ]
        assert store.attempt_state(admission.binding.attempt_id).terminal_outcome is (
            AttemptTerminalOutcome.RESULT_READY
        )
    repair_history = audit.recent_repair_reality()
    assert len(repair_history) == 1
    assert repair_history[0]["event_id"] == str(event.id)
    assert repair_history[0]["failure_signature"] == event.failure_signature
    assert len(repair_history[0]["failure_signature"]) == 64
    assert repair_history[0]["result"] == "RECOVERED"


def test_failed_verification_effect_creates_safe_self_refine_evidence(
    postgres_database: Database, git_repository: Path,
) -> None:
    service = NativeExecutorRuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    service.admit(admission)
    grant = service.allocate(_offer())
    assert grant is not None
    service.activate_allocation(grant)
    audit = DurableKernelAudit(
        postgres_database,
        attempt_id=admission.binding.attempt_id,
        session_id=admission.binding.session_id,
        pwu_id=admission.binding.pwu_id,
        envelope_id=admission.binding.resource_envelope.envelope_id,
    )
    plan = WorkingPlan(
        version=1, objective_reference=str(admission.contract.id),
        chosen_approach="test the admitted change",
        approach_rationale="independent tool receipt",
    )
    request = InferenceRequest(
        attempt_id=admission.binding.attempt_id,
        session_id=admission.binding.session_id,
        step_sequence=1,
        objective=admission.contract.objective,
        working_plan=plan,
        context_facts=(), available_tools=(), residual_obligations=("targeted test",),
    )
    step_id = asyncio.run(audit.begin_inference(request))
    proposal = ToolCallProposal(
        proposal_index=0, tool_identity="test.run",
        arguments={"recipe": "node --test"},
    )
    asyncio.run(audit.finish_inference(step_id, InferenceResponse(
        action=InferenceAction.CONTINUE, summary="run admitted test",
        working_plan=plan, tool_calls=(proposal,),
        residual_obligations=("targeted test",),
    ), None))
    tool_request = ToolExecutionRequest(
        delivery_id=uuid4(), attempt_id=admission.binding.attempt_id,
        worker_epoch=grant.allocation.lease_epoch, step_id=step_id,
        proposal=proposal, capability_grants=admission.binding.capability_grants,
        workspace=admission.binding.workspace,
    )
    effect_id = asyncio.run(audit.begin_tool(step_id, tool_request))
    output = {"returncode": 1, "stderr": "sensitive details must not enter diagnosis"}
    asyncio.run(audit.finish_tool(effect_id, tool_request, ToolExecutionResult(
        delivery_id=tool_request.delivery_id, tool_identity="test.run",
        condition=EffectCondition.FAILED, output=output,
        output_digest=canonical_digest(output),
    ), None))
    with postgres_database.unit_of_work() as uow:
        native = NativeExecutionStore(uow.session)
        event = native.open_self_refine_event(admission.binding.attempt_id)
        assert event is not None
        assert event.failure_family == "VERIFICATION_FAILURE"
        assert event.expected_reality["effect_condition"] == "SETTLED"
        assert event.observed_reality["failure_code"] == 1
        assert "sensitive details" not in event.model_dump_json()
        references = native.self_refine_actions(event.id)[0].evidence_references
        assert references[0] == f"native-effect:{effect_id}"
        assert len(references) == 2
        assert references[1].startswith("native-receipt:")
        assert event.diagnostic_evidence["receipt_ref"] == references[1]
        assert event.diagnostic_evidence["stderr_ref"] == f"{references[1]}#stderr"
        assert event.diagnostic_evidence["stderr_bytes"] == len(output["stderr"].encode("utf-8"))
    repair_request = request.model_copy(update={"step_sequence": 2})
    repair_step_id = asyncio.run(audit.begin_inference(repair_request))
    asyncio.run(audit.finish_inference(repair_step_id, InferenceResponse(
        action=InferenceAction.RESULT_READY,
        summary="corrected after observed verification failure",
        working_plan=plan.model_copy(update={"version": 2}),
        result_claim={"output_vector": {"files": []}},
        provider_observation=InferenceProviderObservation(
            provider_identity="deepseek-responses",
            requested_model="deepseek-flash",
            response_status="completed",
            usage=InferenceUsage(
                input_tokens=24, output_tokens=9, total_tokens=33,
            ),
        ),
    ), None))
    service.finish_allocation(grant, KernelRunResult(
        runtime_mode=ExecutionMode.FINISHED,
        terminal_outcome=AttemptTerminalOutcome.RESULT_READY,
        final_checkpoint_id=None,
        step_count=2, inference_submissions=2, tool_effects=1,
        summary="corrected and re-observed within the same attempt",
    ))
    with postgres_database.unit_of_work() as uow:
        recovered = NativeExecutionStore(uow.session).self_refine_event(event.id)
        assert recovered.final_result == "RECOVERED"
        assert recovered.model_token_usage == {
            "input_tokens": 24,
            "output_tokens": 9,
            "total_tokens": 33,
            "observed_response_count": 1,
        }


def test_compiler_diagnostic_requires_source_evidence_before_bounded_repair(
    postgres_database: Database, git_repository: Path,
) -> None:
    admitted = _business_admission(
        postgres_database, git_repository, acceptance_meaning="README compiles",
    )
    binding = admitted.binding.model_copy(update={"capability_grants": (
        *admitted.binding.capability_grants,
        CapabilityGrant(identity="file.read", version="1", scope={"paths": ["README.md"]}),
        CapabilityGrant(identity="build.run", version="1", scope={}),
    )})
    admitted = admitted.model_copy(update={"binding": binding})
    service = NativeExecutorRuntimeService(postgres_database)
    service.admit(admitted)
    offer = _offer().model_copy(update={"capability_identities": (
        "file.write", "file.read", "build.run", "test.run",
    )})
    grant = service.allocate(offer)
    assert grant is not None
    service.activate_allocation(grant)
    audit = DurableKernelAudit(
        postgres_database, attempt_id=binding.attempt_id,
        session_id=binding.session_id, pwu_id=binding.pwu_id,
        envelope_id=binding.resource_envelope.envelope_id,
    )
    plan = WorkingPlan(
        version=1, objective_reference=str(admitted.contract.id),
        chosen_approach="diagnose compiler failure", approach_rationale="bounded source scope",
    )

    def observed_tool(sequence: int, identity: str, arguments: dict,
                      condition: EffectCondition, output: dict) -> RepairabilityClassification | None:
        proposal = ToolCallProposal(proposal_index=0, tool_identity=identity, arguments=arguments)
        inference_request = InferenceRequest(
            attempt_id=binding.attempt_id, session_id=binding.session_id,
            step_sequence=sequence, objective=admitted.contract.objective,
            working_plan=plan.model_copy(update={"version": sequence}),
            context_facts=(), available_tools=(), residual_obligations=("compile",),
        )
        step_id = asyncio.run(audit.begin_inference(inference_request))
        asyncio.run(audit.finish_inference(step_id, InferenceResponse(
            action=InferenceAction.CONTINUE, summary="observe diagnostic",
            working_plan=inference_request.working_plan,
            tool_calls=(proposal,), residual_obligations=("compile",),
        ), None))
        tool_request = ToolExecutionRequest(
            delivery_id=uuid4(), attempt_id=binding.attempt_id,
            worker_epoch=grant.allocation.lease_epoch, step_id=step_id,
            proposal=proposal, capability_grants=binding.capability_grants,
            workspace=binding.workspace,
        )
        effect_id = asyncio.run(audit.begin_tool(step_id, tool_request))
        return asyncio.run(audit.finish_tool(effect_id, tool_request, ToolExecutionResult(
            delivery_id=tool_request.delivery_id, tool_identity=identity,
            condition=condition, output=output, output_digest=canonical_digest(output),
        ), None))

    assert observed_tool(1, "build.run", {"recipe": "compile"}, EffectCondition.FAILED, {
        "diagnostic_code": "E0425", "path": "README.md", "stderr": "symbol not found",
        "returncode": 1,
    }) is RepairabilityClassification.REPAIRABLE_WITH_SUFFICIENT_EVIDENCE
    assert observed_tool(2, "file.read", {"path": "README.md"}, EffectCondition.SETTLED, {
        "path": "README.md", "exists": True,
        "content": (git_repository / "README.md").read_text(encoding="utf-8"),
    }) is RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        event = store.open_self_refine_event(binding.attempt_id)
        assert event is not None
        assert event.repairability is RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE
        assert event.diagnostic_evidence["source_read_receipt_ref"].startswith("native-receipt:")
        actions = store.self_refine_actions(event.id)
        assert [action.outcome for action in actions] == ["RETRY_SCHEDULED", "EVIDENCE_SUFFICIENT"]
        assert actions[0].observed_reality["initial_repairability"] == (
            RepairabilityClassification.REPAIRABLE_WITH_SUFFICIENT_EVIDENCE.value
        )
        for index in range(4):
            later = event.model_copy(update={
                "id": uuid4(), "operation_id": uuid4(),
                "created_at": event.created_at + timedelta(seconds=index + 1),
                "updated_at": event.created_at + timedelta(seconds=index + 1),
                "status": "MITIGATED", "final_result": "FAILED",
            })
            store.insert_self_refine_event(later)
        uow.commit()
    assert audit.recent_repair_reality()[0]["event_id"] == str(event.id)


def test_inference_transport_failure_persists_safe_structured_diagnostics(
    postgres_database: Database, git_repository: Path
) -> None:
    admission = _admission(postgres_database, git_repository)
    NativeExecutorRuntimeService(postgres_database).admit(admission)
    audit = DurableKernelAudit(
        postgres_database,
        attempt_id=admission.binding.attempt_id,
        session_id=admission.binding.session_id,
        pwu_id=admission.binding.pwu_id,
        envelope_id=admission.binding.resource_envelope.envelope_id,
    )
    request = InferenceRequest(
        attempt_id=admission.binding.attempt_id,
        session_id=admission.binding.session_id,
        step_sequence=1,
        objective=admission.contract.objective,
        working_plan=WorkingPlan(
            version=1,
            objective_reference=str(admission.contract.id),
            chosen_approach="observe provider transport",
            approach_rationale="retain a safe failure fingerprint",
        ),
        context_facts=(),
        available_tools=(),
        residual_obligations=("provider response",),
    )
    step_id = asyncio.run(audit.begin_inference(request))
    diagnostics = {
        "mode": "stream",
        "response_headers_received": True,
        "response_status_code": 200,
        "headers_elapsed_ms": 1200,
        "first_byte_elapsed_ms": None,
        "elapsed_ms": 60660,
        "received_bytes": 0,
        "received_events": 0,
        "terminal_received": False,
        "syntactically_complete": False,
        "failure_code": InferenceFailureCode.INCOMPLETE_RESPONSE.value,
    }
    error = InferenceTransportUnknown(
        "deepseek response was incomplete",
        failure_code=InferenceFailureCode.INCOMPLETE_RESPONSE,
        transport_diagnostics=diagnostics,
        request_sent=True,
    )
    asyncio.run(audit.finish_inference(step_id, None, error))

    with postgres_database.unit_of_work() as uow:
        step = NativeExecutionStore(uow.session).steps_for_attempt(
            admission.binding.attempt_id
        )[0]

    assert step.condition.value == "FAILED"
    assert step.result_payload == {
        "error_type": "InferenceTransportUnknown",
        "request_sent": True,
        "failure_code": "INCOMPLETE_RESPONSE",
        "transport_diagnostics": diagnostics,
    }
    assert "authorization" not in str(step.result_payload).lower()


def test_pwu_resource_pool_does_not_reset_or_double_debit(
    postgres_database: Database, git_repository: Path
) -> None:
    service = NativeExecutorRuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    envelope = admission.binding.resource_envelope.model_copy(
        update={"max_inference_submissions": 1}
    )
    admission = admission.model_copy(
        update={
            "binding": admission.binding.model_copy(
                update={"resource_envelope": envelope}
            )
        }
    )
    service.admit(admission)
    first = ResourceUsageEntryRecord(
        id=uuid4(),
        envelope_id=envelope.envelope_id,
        attempt_id=admission.binding.attempt_id,
        reservation_key="qualification:first",
        resource_type="inference_submission",
        amount=1,
        certainty=UsageCertainty.UNKNOWN,
        condition=ResourceReservationCondition.UNKNOWN,
        evidence={"response_observed": False},
        created_at=datetime.now(timezone.utc),
    )
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        assert store.insert_resource_usage(first).id == first.id
        assert store.insert_resource_usage(first).id == first.id
        successor_envelope = envelope.model_copy(
            update={"envelope_id": uuid4()}
        )
        store.insert_resource_envelope(
            admission.binding.pwu_id, successor_envelope
        )
        with pytest.raises(NativeExecutionConflict, match="resource pool is exhausted"):
            store.insert_resource_usage(
                first.model_copy(
                    update={
                        "id": uuid4(),
                        "envelope_id": successor_envelope.envelope_id,
                        "reservation_key": "qualification:second",
                    }
                )
            )
        uow.commit()


def test_cancel_before_allocation_releases_grant_and_prevents_execution(
    postgres_database: Database, git_repository: Path
) -> None:
    service = NativeExecutorRuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    queue = service.admit(admission)
    receipt = service.control(
        BackendControlCommand(
            command_id=uuid4(),
            handle=ExecutionHandle(
                backend_identity="watt-native", dispatch_id=queue.id,
                attempt_id=admission.binding.attempt_id,
                generation=admission.binding.generation,
                opaque_reference=f"queue:{queue.id}",
            ),
            action=ControlAction.CANCEL,
            expected_control_version=0,
            actor_identity="human:qualification",
            reason="cancel before native capacity allocation",
        )
    )
    assert receipt.accepted is True
    assert service.allocate(_offer()) is None
    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        state = store.attempt_state(admission.binding.attempt_id)
        final_queue = store.queue_for_attempt(admission.binding.attempt_id)
        assert state.grant_state is AttemptGrantState.RELEASED
        assert state.terminal_outcome is AttemptTerminalOutcome.CANCELLED
        assert final_queue is not None
        assert final_queue.condition is QueueCondition.CANCELLED


def test_running_pause_is_requested_before_it_is_safely_applied(
    postgres_database: Database, git_repository: Path
) -> None:
    service = NativeExecutorRuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    queue = service.admit(admission)
    grant = service.allocate(_offer())
    assert grant is not None
    service.activate_allocation(grant)
    command_id = uuid4()

    requested = service.control(
        BackendControlCommand(
            command_id=command_id,
            handle=ExecutionHandle(
                backend_identity="watt-native",
                dispatch_id=queue.id,
                attempt_id=admission.binding.attempt_id,
                generation=admission.binding.generation,
                opaque_reference=f"queue:{queue.id}",
            ),
            action=ControlAction.PAUSE,
            expected_control_version=0,
            actor_identity="human:qualification",
            reason="pause during process qualification",
        )
    )
    assert requested.accepted is True
    assert requested.condition.value == "REQUESTED"
    assert service.observe(
        ExecutionHandle(
            backend_identity="watt-native",
            dispatch_id=queue.id,
            attempt_id=admission.binding.attempt_id,
            generation=admission.binding.generation,
            opaque_reference=f"queue:{queue.id}",
        )
    ).runtime_mode is ExecutionMode.PAUSE_REQUESTED

    service.finish_allocation(
        grant,
        KernelRunResult(
            runtime_mode=ExecutionMode.PAUSED,
            final_checkpoint_id=None,
            step_count=1,
            inference_submissions=1,
            tool_effects=1,
            summary="process tree terminated and checkpoint committed",
            residual_obligations=("targeted test",),
        ),
    )
    with postgres_database.unit_of_work() as uow:
        control = uow.session.execute(
            select(execution_control_requests).where(
                execution_control_requests.c.command_id == command_id
            )
        ).mappings().one()
        state = NativeExecutionStore(uow.session).attempt_state(
            admission.binding.attempt_id
        )
        assert control["condition"] == "APPLIED"
        assert control["applied_at"] is not None
        assert state.runtime_mode is ExecutionMode.PAUSED
        assert state.grant_state is AttemptGrantState.GRANTED


def test_session_fork_binds_exact_checkpoint_and_close_does_not_complete_pwu(
    postgres_database: Database, git_repository: Path, tmp_path: Path
) -> None:
    service = NativeExecutorRuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    service.admit(admission)
    grant = service.allocate(_offer())
    assert grant is not None
    service.activate_allocation(grant)
    checkpoint = asyncio.run(
        DurableCheckpointPort(
            postgres_database,
            ContentAddressedStorage(tmp_path / "session-checkpoints"),
            attempt_id=admission.binding.attempt_id,
            session_id=admission.binding.session_id,
            worker_epoch=grant.allocation.lease_epoch,
        ).commit(
            KernelCheckpoint(
                step_sequence=1,
                working_plan=WorkingPlan(
                    version=2,
                    objective_reference=str(admission.contract.id),
                    chosen_approach="continue from exact bundle",
                    approach_rationale="checkpointed work",
                ),
                tool_results=(),
                source_vector_digest=admission.binding.source_vector.digest or "",
                residual_obligations=("targeted test",),
            )
        )
    )
    service.finish_allocation(
        grant,
        KernelRunResult(
            runtime_mode=ExecutionMode.PAUSED,
            final_checkpoint_id=checkpoint.id,
            step_count=1,
            inference_submissions=1,
            tool_effects=0,
            summary="checkpointed",
            residual_obligations=("targeted test",),
        ),
    )
    with postgres_database.unit_of_work() as uow:
        before = RuntimeStore(uow.session).work_unit(admission.binding.pwu_id)

    child = service.fork_session(
        source_session_id=admission.binding.session_id,
        checkpoint_id=checkpoint.id,
        actor_identity="human:qualification",
    )
    assert child.id != admission.binding.session_id
    assert child.parent_checkpoint_id == checkpoint.id
    assert child.current_checkpoint_id == checkpoint.id
    assert child.current_working_state_version == 2
    closed = service.close_session(child.id)
    assert closed.condition.value == "CLOSED"

    with postgres_database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        source = store.execution_session(admission.binding.session_id)
        saved_child = store.execution_session(child.id)
        after = RuntimeStore(uow.session).work_unit(admission.binding.pwu_id)
        assert source is not None and source.condition.value == "OPEN"
        assert saved_child is not None and saved_child.condition.value == "CLOSED"
        assert before is not None and after is not None
        assert after.condition == before.condition
