"""Seed and verify Q29 across a real retained-volume service restart."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from sqlalchemy import text

from spg.application.bootstrap import bootstrap
from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.application.runtime import RuntimeService
from spg.domain.native_execution import ExecutionMode, KernelRunResult, WorkerOffer
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore

sys.path.insert(0, "/benchmark")
from runner import admission_for, prepare_repositories


PROFILE = "deepseek-responses:deepseek-flash:high"


def tree_digest(root: Path) -> str:
    digest = sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file() and ".git" not in item.parts):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def seed(output: Path) -> None:
    app = bootstrap()
    database = app.persistence()
    spec = json.loads(Path("/benchmark/spec.json").read_text())
    task = next(item for item in spec["tasks"] if item["id"] == "T1")
    root, repositories = prepare_repositories(
        app.settings.native_executor_workspace_root / "q29-host-reboot", task
    )
    runtime_service = RuntimeService(database)
    attempt, session_id, admission = admission_for(
        runtime_service, task, root, repositories, "deepseek-flash", (PROFILE,)
    )
    NativeExecutorRuntimeService(database).admit(admission)
    with database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        state = store.attempt_state(attempt.id)
        queue = store.queue_for_attempt(attempt.id)
        migration = uow.session.scalar(text("SELECT version_num FROM alembic_version"))
    payload = {
        "attempt_id": str(attempt.id),
        "pwu_id": str(admission.binding.pwu_id),
        "work_id": str(admission.binding.work_id),
        "session_id": str(session_id),
        "workspace": str(root),
        "tree_digest_before_reboot": tree_digest(root),
        "runtime_mode_before_reboot": state.runtime_mode.value,
        "queue_condition_before_reboot": queue.condition.value if queue else None,
        "migration_before_reboot": migration,
    }
    output.write_text(json.dumps(payload, indent=2) + "\n")
    database.dispose()
    print(json.dumps({"status": "Q29_SEEDED", **payload}, sort_keys=True))


def verify(output: Path) -> None:
    evidence = json.loads(output.read_text())
    app = bootstrap()
    database = app.persistence()
    runtime = NativeExecutorRuntimeService(database)
    from uuid import UUID
    attempt_id = UUID(evidence["attempt_id"])
    root = Path(evidence["workspace"])
    with database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        state = store.attempt_state(attempt_id)
        queue = store.queue_for_attempt(attempt_id)
        binding = store.attempt_binding(attempt_id).binding
        migration = uow.session.scalar(text("SELECT version_num FROM alembic_version"))
    assert state.runtime_mode is ExecutionMode.QUEUED
    assert queue is not None and queue.condition.value in {"QUEUED", "RETURNED_TO_QUEUE"}
    assert str(binding.session_id) == evidence["session_id"]
    assert tree_digest(root) == evidence["tree_digest_before_reboot"]
    offer = WorkerOffer(
        worker_id="q29-reboot-probe",
        worker_profile="local-container-v1",
        provider_profiles=(PROFILE,),
        resource_profiles=("standard",),
        capability_identities=(
            "file.read", "file.write", "process.run", "git.status", "git.diff",
            "test.run", "build.run", "dependency.sync", "preview.inspect",
        ),
        lease_seconds=30,
    )
    grant = runtime.allocate(offer)
    assert grant is not None and grant.allocation.attempt_id == attempt_id
    runtime.activate_allocation(grant)
    runtime.finish_allocation(grant, KernelRunResult(
        runtime_mode=ExecutionMode.PAUSED,
        final_checkpoint_id=None,
        step_count=0,
        inference_submissions=0,
        tool_effects=0,
        summary="Q29 retained-volume recovery dispatch verified without Provider request",
        residual_obligations=tuple(binding.obligation_references),
    ))
    evidence.update({
        "tree_digest_after_reboot": tree_digest(root),
        "migration_after_reboot": migration,
        "recovered_attempt_id": str(attempt_id),
        "recovered_generation": grant.allocation.grant_revision,
        "recovered_worker_epoch": grant.allocation.lease_epoch,
        "provider_requests": 0,
        "result": "PASS",
    })
    output.write_text(json.dumps(evidence, indent=2) + "\n")
    database.dispose()
    print(json.dumps({"status": "Q29_PASS", **evidence}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("seed", "verify"))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    path = Path(args.output)
    seed(path) if args.mode == "seed" else verify(path)


if __name__ == "__main__":
    main()
