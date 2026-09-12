from __future__ import annotations

import asyncio
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import shutil
import subprocess
from threading import Barrier
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, inspect, select, update

from spg.application.executor_runtime import NativeExecutorRuntimeService
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
    ExecutionHandle,
    ExecutionEventRecord,
    ExecutionMode,
    InferenceAction,
    InferenceRequest,
    InferenceResponse,
    KernelCheckpoint,
    KernelRunResult,
    NativeExecutionAdmission,
    NativeExecutionConflict,
    PWUContractVersionRecord,
    QueueCondition,
    ResourceEnvelope,
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
from spg.infrastructure.executor_runtime.local_storage import (
    ContentAddressedStorage,
    WorkspaceArchiveStore,
)
from spg.infrastructure.executor_runtime.backends import (
    LegacyCodexExecutionBackend,
    NativeExecutionBackend,
    PinnedExecutionBackendRouter,
)
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.executor_runtime.runtime_ports import DurableCheckpointPort
from spg.infrastructure.executor_runtime.runtime_ports import DurableKernelAudit
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.native_execution_schema import (
    checkpoint_bundles,
    event_outbox,
    execution_control_requests,
    execution_events,
    execution_resource_usage,
    execution_workspaces,
    executor_leases,
    native_execution_tables,
    native_trusted_source_pointers,
    result_ready_claims,
)
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


def _admission(database: Database, repository: Path, *, command_id=None, actor="human:test"):
    spine, attempt = _authority(database, repository)
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
    work_id = uuid4()
    workspace = WorkspaceManifest(
        workspace_id=uuid4(), work_id=work_id, pwu_id=spine.work_unit.id,
        attempt_id=attempt.id, source_vector_digest=vector.digest or "",
        host_storage_id="qualification-host", environment_profile_digest="b" * 64,
        mounts=(WorkspaceMount(mount_id="primary", host_path=str(repository), container_path="/workspace/primary", writable=True, write_scope=("README.md",), forbidden_paths=(".git",)),),
        evidence_namespace="qualification", retention_policy="test",
    )
    payload = {"objective": "change one bounded file", "verification": ["targeted test"]}
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
    postgres_database: Database, git_repository: Path, tmp_path: Path
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
    retention.release_pin(pin.id)

    original = (git_repository / "README.md").read_text(encoding="utf-8")
    action = retention.hibernate(admission.binding.workspace.workspace_id)
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


def test_operational_backend_cutover_and_rollback_preserve_active_native_reader(
    postgres_database: Database, git_repository: Path
) -> None:
    runtime = NativeExecutorRuntimeService(postgres_database)
    admission = _admission(postgres_database, git_repository)
    legacy_handles: dict[UUID, ExecutionHandle] = {}

    async def legacy_start(command):
        handle = ExecutionHandle(
            backend_identity="legacy-codex",
            dispatch_id=uuid4(),
            attempt_id=command.binding.attempt_id,
            generation=command.binding.generation,
            opaque_reference=f"legacy:{command.binding.attempt_id}",
        )
        legacy_handles[handle.attempt_id] = handle
        return handle

    async def legacy_observe(handle):
        assert legacy_handles[handle.attempt_id] == handle
        return BackendObservation(
                handle=handle,
                runtime_mode=ExecutionMode.QUEUED,
                terminal_outcome=None,
                current_checkpoint_id=None,
                progress_summary="legacy handle remains readable",
            observed_at=datetime.now(timezone.utc),
        )

    router = PinnedExecutionBackendRouter(
        (
            NativeExecutionBackend(runtime),
            LegacyCodexExecutionBackend(legacy_start, legacy_observe),
        ),
        default_backend="watt-native",
    )
    native_handle = asyncio.run(router.start(admission))
    assert asyncio.run(router.observe(native_handle)).runtime_mode is ExecutionMode.QUEUED

    router.set_default("legacy-codex")
    assert asyncio.run(router.observe(native_handle)).handle == native_handle
    with pytest.raises(NativeExecutionConflict, match="pinned"):
        asyncio.run(router.start(admission))
    legacy_admission = admission.model_copy(update={
        "binding": admission.binding.model_copy(update={
            "backend_implementation": "legacy-codex",
        }),
    })
    legacy_handle = asyncio.run(router.start(legacy_admission))
    assert asyncio.run(router.observe(legacy_handle)).handle == legacy_handle

    router.set_default("watt-native")
    after_rollback = asyncio.run(router.observe(native_handle))
    assert after_rollback.runtime_mode is ExecutionMode.QUEUED
    assert after_rollback.handle.backend_identity == "watt-native"
    assert asyncio.run(router.observe(legacy_handle)).handle.backend_identity == "legacy-codex"


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
