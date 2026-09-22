"""PostgreSQL + Native queue + real PE container Brownfield journey proof."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import os
from pathlib import Path
import subprocess
import sys
from threading import Event, Thread
import time
from uuid import UUID

from alembic import command
from alembic.config import Config
import pytest

from spg.application.delivery import DeliveryApplicationService
from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.application.native_production_environment import NativeProductionEnvironmentRuntime
from spg.application.native_production_record import NativeProductionRecordService
from spg.application.preparation import PreparationService
from spg.application.runtime import RuntimeService
from spg.application.work import WorkApplicationService
from spg.domain.native_execution import (
    InferenceAction,
    InferenceResponse,
    ToolCallProposal,
    WorkerOffer,
    WorkingPlan,
)
from spg.domain.preparation import ContextSemanticRole, ExecutorBinding
from spg.domain.product import (
    AttentionAction,
    AttentionKind,
    AttentionResolutionRequest,
    EngineeringContextReference,
    WorkRefinementRequest,
    WorkStatus,
)
from spg.domain.runtime import BootstrapRequest
from spg.executor.kernel import NativeExecutorKernel
from spg.infrastructure.executor_runtime.inference import ScriptedInferenceAdapter
from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
from spg.infrastructure.executor_runtime.native_compatibility_executor import (
    NativeQueuedExecutorCapability,
)
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.executor_runtime.production_environment_tool_host import (
    ProductionEnvironmentNativeToolHost,
)
from spg.infrastructure.executor_runtime.runtime_ports import (
    DurableCheckpointPort,
    DurableKernelAudit,
)
from spg.infrastructure.executor_runtime.worker import NativeExecutionWorker
from spg.infrastructure.git_workspace import GitCloneAttemptWorkspace
from spg.infrastructure.persistence import Database, product_tables, runtime_tables
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.production_environment import (
    ContainerProductionEnvironmentProvider,
    DockerCliContainerRuntime,
)
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore
from spg.providers.repository_code_verifier import RepositoryCodeVerifier


pytestmark = [pytest.mark.postgresql, pytest.mark.real_container]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMAGE = "watt-engineering-semantic-human-retest-app:latest"
CAPABILITIES = (
    "file.read",
    "file.write",
    "process.run",
    "git.status",
    "git.diff",
    "test.run",
    "build.run",
    "dependency.sync",
    "preview.inspect",
)


def load_runtime_owners():
    ecf_src = PROJECT_ROOT.parent / "engineering-context-fabric" / "src"
    guardian_src = PROJECT_ROOT.parent / "guardian" / "src"
    if not ecf_src.is_dir() or not guardian_src.is_dir():
        pytest.skip("sibling ECF and Guardian repositories are unavailable")
    sys.path[:0] = [str(ecf_src), str(guardian_src)]
    from ecf.runtime import ECFRealityRuntime, JsonRealityStore
    from guardian.runtime import JsonAssuranceIntakeStore

    return ECFRealityRuntime, JsonRealityStore, JsonAssuranceIntakeStore


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture(autouse=True)
def clean_runtime(postgres_database: Database):
    previous = os.environ.get("SPG_DATABASE_URL")
    os.environ["SPG_DATABASE_URL"] = postgres_database.engine.url.render_as_string(
        hide_password=False
    )
    command.upgrade(Config(PROJECT_ROOT / "alembic.ini"), "head")
    names = ", ".join(f'"{table.name}"' for table in (*product_tables, *runtime_tables))
    with postgres_database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {names} CASCADE")
    try:
        yield
    finally:
        with postgres_database.engine.begin() as connection:
            connection.exec_driver_sql(f"TRUNCATE TABLE {names} CASCADE")
        if previous is None:
            os.environ.pop("SPG_DATABASE_URL", None)
        else:
            os.environ["SPG_DATABASE_URL"] = previous


def test_real_work_task_contract_pwu_native_pe_preview_and_authorization(
    postgres_database: Database,
    tmp_path: Path,
):
    if subprocess.run(
        ["docker", "image", "inspect", IMAGE],
        check=False,
        capture_output=True,
    ).returncode:
        pytest.skip(f"qualified local image is unavailable: {IMAGE}")
    repository = tmp_path / "repository"
    repository.mkdir()
    git(repository, "init", "-b", "main")
    git(repository, "config", "user.name", "Native PE Test")
    git(repository, "config", "user.email", "native-pe@example.invalid")
    (repository / "AI_context.md").write_text("governed project context\n", encoding="utf-8")
    (repository / "docs").mkdir()
    (repository / "docs" / "contract.md").write_text("bounded delivery contract\n", encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "baseline")

    RuntimeService(postgres_database).bootstrap_trusted_baseline(
        BootstrapRequest(
            repository_path=repository,
            repository_identity="repo:brownfield-native-pe",
            repository_ref="refs/heads/main",
            authority_identity="human:test",
            scope={"journey": "brownfield-native-production-environment"},
        )
    )
    admission = WorkApplicationService(
        postgres_database,
        workspace_root=tmp_path / "workspaces",
    )
    admission.register_engineering_resource(
        repository_identity="repo:brownfield-native-pe",
        location_ref=str(repository),
        authoritative_ref="refs/heads/main",
        context_references=(
            EngineeringContextReference(
                semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                repository_relative_path="AI_context.md",
            ),
            EngineeringContextReference(
                semantic_role=ContextSemanticRole.EXECUTION_CONTRACT,
                repository_relative_path="docs/contract.md",
            ),
        ),
    )
    submitted = admission.submit_work(
        "Create preview/native-production-environment.html describing the completed governed result"
    )
    draft = admission.refine_work(
        submitted.work_id,
        WorkRefinementRequest(
            code_exact_targets=("preview/native-production-environment.html",),
        ),
    )
    admitted = admission.approve_work(
        draft.work_id,
        authority_identity="human:test",
    )
    assert admitted.status is WorkStatus.READY

    runtime = NativeExecutorRuntimeService(postgres_database)
    provider = ContainerProductionEnvironmentProvider(DockerCliContainerRuntime())
    pe_store = JsonProductionEnvironmentStore(tmp_path / "production-environments")
    ECFRealityRuntime, JsonRealityStore, JsonAssuranceIntakeStore = load_runtime_owners()
    ecf_store = JsonRealityStore(tmp_path / "ecf")
    guardian_store = JsonAssuranceIntakeStore(tmp_path / "guardian")
    production_recorder = NativeProductionRecordService(
        postgres_database,
        store=pe_store,
        reality=ECFRealityRuntime(ecf_store),
        guardian=guardian_store,
    )
    pe_runtime = NativeProductionEnvironmentRuntime(
        store=pe_store,
        provider=provider,
        image_reference=IMAGE,
    )
    queued_executor = NativeQueuedExecutorCapability(
        postgres_database,
        runtime,
        provider_profile="scripted-native-pe",
        resource_profile="standard",
        environment_profile="local-container-v1",
        poll_seconds=0.05,
        wait_seconds=30,
        production_environment=pe_runtime,
    )
    preparation = PreparationService(
        postgres_database,
        workspaces=GitCloneAttemptWorkspace(),
    )
    service = WorkApplicationService(
        postgres_database,
        workspace_root=tmp_path / "workspaces",
        executor=queued_executor,
        verifier=RepositoryCodeVerifier(postgres_database),
        executor_binding=ExecutorBinding(
            binding_ref="binding:watt-native-queue-v2",
            capability_identity="capability:watt-native-executor",
            profile_identity="local-container-v1",
        ),
        preparation=preparation,
        production_recorder=production_recorder,
    )

    def kernel_factory(grant):
        with postgres_database.unit_of_work() as uow:
            binding = NativeExecutionStore(uow.session).attempt_binding(
                grant.allocation.attempt_id
            )
        target = "preview/native-production-environment.html"
        inference = ScriptedInferenceAdapter(
            (
                InferenceResponse(
                    action=InferenceAction.CONTINUE,
                    summary="produce exact Task Contract output",
                    working_plan=WorkingPlan(
                        version=2,
                        objective_reference=str(binding.pwu_contract_version_id),
                        chosen_approach="Write the admitted artifact inside assigned PE",
                        approach_rationale="Native Executor owns HOW; PE owns WHERE",
                    ),
                    tool_calls=(
                        ToolCallProposal(
                            proposal_index=0,
                            tool_identity="file.write",
                            arguments={
                                "path": target,
                                "content": "<!doctype html><title>Native Production Environment</title><h1>Governed Brownfield result</h1>\n",
                            },
                        ),
                    ),
                    residual_obligations=(),
                ),
                InferenceResponse(
                    action=InferenceAction.RESULT_READY,
                    summary="Task Contract output is ready for independent verification",
                    working_plan=WorkingPlan(
                        version=3,
                        objective_reference=str(binding.pwu_contract_version_id),
                        chosen_approach="Return observed bounded result",
                        approach_rationale="The admitted artifact mutation settled",
                    ),
                    result_claim={"output_vector": {"files": [target]}},
                    residual_obligations=(),
                ),
            )
        )
        tools = ProductionEnvironmentNativeToolHost.from_manifest(
            binding.binding.workspace,
            provider=provider,
        )
        assert tools is not None
        return NativeExecutorKernel(
            inference=inference,
            tools=tools.registry(),
            checkpoints=DurableCheckpointPort(
                postgres_database,
                ContentAddressedStorage(tmp_path / "checkpoints"),
                attempt_id=binding.attempt_id,
                session_id=binding.session_id,
                worker_epoch=grant.allocation.lease_epoch,
            ),
            audit=DurableKernelAudit(
                postgres_database,
                attempt_id=binding.attempt_id,
                session_id=binding.session_id,
                pwu_id=binding.pwu_id,
                envelope_id=binding.resource_envelope_id,
            ),
        )

    worker = NativeExecutionWorker(runtime, kernel_factory, heartbeat_seconds=1)
    offer = WorkerOffer(
        worker_id="worker:native-pe-test",
        worker_profile="local-container-v1",
        provider_profiles=("scripted-native-pe",),
        resource_profiles=("standard",),
        capability_identities=CAPABILITIES,
        lease_seconds=10,
    )
    stop = Event()

    def worker_loop():
        while not stop.is_set():
            if asyncio.run(worker.run_once(offer)):
                return
            time.sleep(0.05)

    thread = Thread(target=worker_loop, daemon=True)
    thread.start()
    try:
        for _ in range(16):
            projection = service.advance_work(admitted.work_id)
            if projection.status in {WorkStatus.NEEDS_ATTENTION, WorkStatus.BLOCKED}:
                break
        assert (
            projection.status is WorkStatus.NEEDS_ATTENTION
        ), projection.model_dump_json(indent=2)
        attention = next(
            item
            for item in service.list_attention(work_id=admitted.work_id)
            if item.kind is AttentionKind.CANDIDATE_AUTHORIZATION
        )
        context = DeliveryApplicationService(postgres_database).candidate_context(
            admitted.work_id
        )
        assert context is not None and context["authorization_pending"]
        assert DeliveryApplicationService(postgres_database).candidate_artifact(
            admitted.work_id,
            context["candidate_fingerprint"],
            "preview/native-production-environment.html",
        ).startswith(b"<!doctype html>")
        service.resolve_attention(
            attention.id,
            AttentionResolutionRequest(
                action=AttentionAction.AUTHORIZE,
                authority_identity="human:test",
            ),
        )
        for _ in range(8):
            projection = service.advance_work(admitted.work_id)
            if service.get_work_result(admitted.work_id).trusted_result:
                break
        assert service.get_work_result(admitted.work_id).trusted_result
    finally:
        stop.set()
        thread.join(timeout=5)

    with postgres_database.unit_of_work() as uow:
        product = ProductStore(uow.session)
        binding = product.runtime_binding(admitted.work_id)
        assert binding is not None
        summary = product.runtime_summary(binding)
        work_unit = RuntimeStore(uow.session).work_unit(binding.work_unit_id)
        native_binding = NativeExecutionStore(uow.session).attempt_binding(summary.attempt_id)
        evidence = NativeExecutionStore(uow.session).evidence_for_attempt(summary.attempt_id)
    assert work_unit is not None and work_unit.completion_contract.task_contract is not None
    assert native_binding.binding.work_id == admitted.work_id
    assert native_binding.binding.pwu_id == binding.work_unit_id
    pe_binding = pe_store.get_native_execution_binding(summary.attempt_id)
    assert pe_binding is not None
    assert pe_binding.task_contract_reference == (
        f"task-contract:{work_unit.completion_contract.task_contract.task_contract_id}"
    )
    assert pe_binding.environment.lifecycle_state.value == "ACTIVE"
    current_environment = pe_store.get_environment(pe_binding.environment.id)
    assert current_environment is not None
    assert current_environment.lifecycle_state.value == "SUSPENDED"
    assert any(
        item.startswith("native-evidence:")
        for item in current_environment.evidence_references
    )
    assert any(
        item.payload.get("environment_reference")
        == f"production-environment:{pe_binding.environment.id}"
        for item in evidence
    )
    completion = production_recorder.record_authorized_work(admitted.work_id)
    record = completion.production_record
    assert record.task_contract_reference == pe_binding.task_contract_reference
    assert record.environment_reference == f"production-environment:{pe_binding.environment.id}"
    assert record.repository_revisions[0].after_revision == git(repository, "rev-parse", "HEAD")
    assert record.changes[0].artifact_reference is not None
    assert all(item.outcome.value == "PASS" for item in record.verification_results)
    assert ecf_store.latest("change", f"work:{admitted.work_id}") is not None
    assert guardian_store.get(
        UUID(completion.guardian_intake_reference.rsplit(":", 1)[-1])
    ) is not None
