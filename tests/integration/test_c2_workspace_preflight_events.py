"""C2 preflight diagnosis reaches the existing durable event Owner."""

import asyncio
import errno
from pathlib import Path
import subprocess
from uuid import uuid4

import pytest

from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.domain.native_execution import (
    AttemptTerminalOutcome, NativeExecutionConflict, ProductionExecutionContext,
)
from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.executor_runtime.production_evidence import observe_production_workspace
from spg.infrastructure.executor_runtime.worker import NativeExecutionWorker
from tests.integration.test_native_executor_runtime import (
    _admission, _git, _offer, clean_native_runtime, git_repository,
)

pytestmark = pytest.mark.postgresql


def _production_admission(database, repository: Path, isolated: Path):
    subprocess.run(["git", "clone", str(repository), str(isolated)],
                   check=True, capture_output=True)
    admission = _admission(database, repository)
    binding = admission.binding
    manifest = binding.workspace.model_copy(update={
        "host_storage_id": str(isolated),
        "mounts": (binding.workspace.mounts[0].model_copy(update={"host_path": str(isolated)}),),
    })
    context = ProductionExecutionContext(
        work_id=binding.work_id, task_contract_id=uuid4(), ecf_context_fingerprint="a" * 64,
        irk_semantic_ir_id=uuid4(), repository_identity=str(repository),
        repository_revision=_git(repository, "rev-parse", "HEAD"),
        workspace_id=manifest.workspace_id, verification_requirements=("exact repository check",),
        work_reality_revision_id=uuid4(),
    )
    return admission.model_copy(update={
        "binding": binding.model_copy(update={"workspace": manifest, "production_context": context}),
        "materialization_path": str(isolated),
    })


def test_missing_workspace_rejection_persists_exact_diagnosis_before_terminal(
    postgres_database, git_repository: Path, tmp_path: Path,
) -> None:
    isolated = tmp_path / "isolated-workspace"
    admission = _production_admission(postgres_database, git_repository, isolated)
    service = NativeExecutorRuntimeService(postgres_database)
    service.admit(admission)
    isolated.rename(tmp_path / "retained-workspace")

    def never_run(_grant):
        raise AssertionError("preflight failure reached the kernel")

    worker = NativeExecutionWorker(service, never_run,
        production_evidence_store=ContentAddressedStorage(tmp_path / "evidence"))
    offer = _offer()
    assert asyncio.run(worker.run_once(offer)) is True
    events = service.execution_evidence(admission.binding.attempt_id)
    rejected = [event for event in events if event["event_type"] == "ExecutionWorkspacePreflightRejected"]
    assert len(rejected) == 1
    payload = rejected[0]["payload"]
    assert payload["failure"] == "VERIFICATION_FAILED: workspace unavailable"
    assert payload["worker_id"] == offer.worker_id
    assert payload["runtime_version"] == offer.runtime_version
    diagnostic = payload["workspace_diagnosis"]
    assert diagnostic["check"] == "WORKSPACE_DIRECTORY"
    assert diagnostic["stat_errno"] == errno.ENOENT
    assert diagnostic["host_path"] == str(isolated)
    assert diagnostic["attempt_id"] == str(admission.binding.attempt_id)
    assert diagnostic["expected_revision"] == admission.binding.production_context.repository_revision
    assert diagnostic["source_vector_digest"] == admission.binding.source_vector.digest
    assert diagnostic["hostname"]
    assert diagnostic["mount_namespace"].startswith("mnt:[")
    assert not any(event["event_type"] == "ExecutionWorkspacePrepared" for event in events)
    with postgres_database.unit_of_work() as uow:
        state = NativeExecutionStore(uow.session).attempt_state(admission.binding.attempt_id)
    assert state.terminal_outcome is AttemptTerminalOutcome.UNABLE_TO_COMPLETE
    assert not list((tmp_path / "evidence").rglob("*.json"))


def test_preflight_event_rejects_unbound_and_arbitrary_metadata(
    postgres_database, git_repository: Path, tmp_path: Path,
) -> None:
    admission = _production_admission(postgres_database, git_repository, tmp_path / "isolated")
    service = NativeExecutorRuntimeService(postgres_database)
    service.admit(admission)
    grant = service.allocate(_offer())
    assert grant is not None
    service.activate_allocation(grant)
    observation = observe_production_workspace(admission.binding,
        ContentAddressedStorage(tmp_path / "evidence"), require_change=False)
    diagnosis = observation["workspace_diagnosis"]
    with pytest.raises(NativeExecutionConflict, match="metadata binding differs"):
        service.record_production_preflight_rejection(grant,
            failure="VERIFICATION_FAILED: workspace unavailable",
            diagnosis={**diagnosis, "attempt_id": str(uuid4())})
    with pytest.raises(NativeExecutionConflict, match="metadata binding differs"):
        service.record_production_preflight_rejection(grant,
            failure="VERIFICATION_FAILED: workspace unavailable",
            diagnosis={**diagnosis, "expected_tree": "0" * len(diagnosis["expected_tree"])})
    with pytest.raises(ValueError, match="unsupported production preflight metadata"):
        service.record_production_preflight_rejection(grant,
            failure="VERIFICATION_FAILED: workspace unavailable",
            diagnosis={**diagnosis, "environment": "must not be accepted"})
    assert not any(event["event_type"] == "ExecutionWorkspacePreflightRejected"
                   for event in service.execution_evidence(admission.binding.attempt_id))
    # The old fixed-message call remains compatible, without inventing a
    # structured observation that it did not supply.
    service.record_production_preflight_rejection(grant,
        failure="VERIFICATION_FAILED: workspace unavailable")
    rejected = [event for event in service.execution_evidence(admission.binding.attempt_id)
                if event["event_type"] == "ExecutionWorkspacePreflightRejected"]
    assert len(rejected) == 1
    assert "workspace_diagnosis" not in rejected[0]["payload"]
