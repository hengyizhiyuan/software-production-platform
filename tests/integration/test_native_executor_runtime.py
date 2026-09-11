from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, inspect, select

from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.application.runtime import RuntimeService
from spg.domain.native_execution import (
    AttemptGrantState,
    AttemptTerminalOutcome,
    BackendControlCommand,
    CapabilityGrant,
    ControlAction,
    ExecutionHandle,
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
    SourceMember,
    SourceVector,
    WorkerOffer,
    WorkingPlan,
    WorkspaceManifest,
    WorkspaceMount,
    canonical_digest,
)
from spg.domain.runtime import (
    AttemptRequest,
    BootstrapRequest,
    CompletionContract,
    InitialRunRequest,
    ProductionHorizon,
)
from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.executor_runtime.runtime_ports import DurableCheckpointPort
from spg.infrastructure.executor_runtime.runtime_ports import DurableKernelAudit
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.native_execution_schema import (
    event_outbox,
    execution_events,
    execution_resource_usage,
    executor_leases,
    native_execution_tables,
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


def test_expired_worker_is_fenced_unknown_before_any_successor(
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
        assert state.grant_state is AttemptGrantState.FENCED
        assert state.terminal_outcome is AttemptTerminalOutcome.UNKNOWN
        assert state.runtime_mode is ExecutionMode.RECONCILING
        assert state.effect_uncertainty is True


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
