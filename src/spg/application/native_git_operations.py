"""Admit one exact Work Git action to the existing PWU/Native Executor runtime."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
import subprocess
from uuid import NAMESPACE_URL, UUID, uuid5
from sqlalchemy import select

from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.application.native_production_environment import NativeProductionEnvironmentRuntime
from spg.application.production_intelligence import TaskContractRequest, default_task_contract_builder
from spg.application.runtime import RuntimeService
from spg.domain.runtime import BootstrapRequest, CompletionContract, InitialRunRequest, ProductionHorizon
from spg.domain.native_execution import (
    AttemptTerminalOutcome, CapabilityGrant, ExecutionBindingV2, ExecutionHandle,
    ExecutionMode, NativeExecutionAdmission, PWUContractVersionRecord,
    NativeExecutionNotFound,
    ResourceEnvelope, SourceMember, SourceVector, WorkerOffer, WorkspaceManifest,
    WorkspaceMount, canonical_digest,
)
from spg.domain.preparation import ExecutorBinding, PreparedExecutionRequest
from spg.domain.production_environment import GitOperationProductionRecordV1
from spg.domain.production_intelligence import EngineeringActivity
from spg.infrastructure.executor_runtime.git_inference import GovernedGitOperationInferenceAdapter
from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.executor_runtime.production_environment_tool_host import ProductionEnvironmentNativeToolHost
from spg.infrastructure.executor_runtime.runtime_ports import DurableCheckpointPort, DurableKernelAudit
from spg.infrastructure.executor_runtime.worker import NativeExecutionWorker
from spg.infrastructure.git_workspace import GitCloneAttemptWorkspace
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_schema import production_runs, production_work_units
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.steering_store import SteeringStore
from spg.executor.kernel import NativeExecutorKernel


class NativeGitOperationRunner:
    """A bounded caller of the existing queue/kernel, not another execution system."""

    provider_profile = "watt-native-git-operation-v1"

    def __init__(
        self,
        database,
        *,
        production_environment: NativeProductionEnvironmentRuntime,
        workspace_root: Path,
        checkpoint_root: Path,
    ) -> None:
        self.database = database
        self.runtime = NativeExecutorRuntimeService(database)
        self.production_environment = production_environment
        self.workspace_root = workspace_root
        self.checkpoint_root = checkpoint_root

    @staticmethod
    def _git(repository: Path, *arguments: str) -> str:
        result = subprocess.run(
            ("git", "-C", str(repository), *arguments),
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode:
            raise RuntimeError("Native Git operation could not verify repository Reality")
        return result.stdout.strip()

    def create_branch(
        self,
        *,
        work_id: UUID,
        intake_id: UUID,
        source_repository: Path,
        source_identity: str,
        source_ref: str,
        source_url: str,
        target_branch: str,
        authority_identity: str,
    ) -> dict[str, object]:
        with self.database.unit_of_work() as uow:
            revision = ProductStore(uow.session).current_work_reality_revision(work_id)
            steering = SteeringStore(uow.session)
            steering_plan = steering.plan_for_work(work_id)
            active_steering = (
                None if steering_plan is None else steering.active_revision(steering_plan.id)
            )
        if revision is None:
            raise RuntimeError("Git action requires an admitted Work Reality revision")
        if active_steering is None:
            raise RuntimeError("Git action requires a current governed Steering Plan")
        if revision.admitted_by != authority_identity:
            raise RuntimeError("Git action authority differs from current Work Reality")
        base_commit = self._git(source_repository, "rev-parse", f"{source_ref}^{{commit}}")
        tree = self._git(source_repository, "rev-parse", f"{base_commit}^{{tree}}")
        session_id = uuid5(NAMESPACE_URL, f"watt:native-git-session:{intake_id}")
        task = default_task_contract_builder().build(TaskContractRequest(
            activity=EngineeringActivity.FEATURE_DELIVERY,
            objective=f"Create isolated Work branch {target_branch}",
            scope=(f"git.branch.create:{target_branch}",),
            acceptance_meaning=(
                f"The current local branch is {target_branch} at exact commit {base_commit}.",
            ),
            out_of_scope=("No remote push or delivery", "Do not alter the source branch"),
            authority_lineage=(
                f"work-reality-revision:{revision.id}",
                f"steering-plan-revision:{active_steering.id}",
                f"human-authority:{authority_identity}",
            ),
            work_reality_references=(f"work-reality-revision:{revision.id}",),
            ecf_references=(
                f"repository:{source_identity}",
                f"source-revision:{base_commit}",
            ),
            decision_reference=f"steering-plan-revision:{active_steering.id}",
            required_capabilities=("git.branch.create",),
        ))
        runtime_reality = RuntimeService(self.database)
        try:
            baseline = runtime_reality.current_baseline(
                repository_identity=source_identity, repository_ref=source_ref,
            )
        except Exception as error:
            from spg.domain.runtime import RuntimeNotBootstrapped
            if not isinstance(error, RuntimeNotBootstrapped):
                raise
            baseline = runtime_reality.bootstrap_trusted_baseline(BootstrapRequest(
                repository_path=source_repository,
                repository_identity=source_identity,
                repository_ref=source_ref,
                authority_identity=authority_identity,
                scope={"work_id": str(work_id), "repository_intake_id": str(intake_id)},
                rationale="Admitted repository asset for an explicit Human Git action",
            )).snapshot
        if baseline.repository_revision != base_commit:
            raise RuntimeError("Git action source differs from Current Trusted Baseline")
        intent_ref = f"repository-intake:{intake_id}"
        with self.database.unit_of_work() as uow:
            existing_run_id = uow.session.execute(
                select(production_runs.c.id).where(production_runs.c.intent_ref == intent_ref)
            ).scalar_one_or_none()
            if existing_run_id is None:
                spine = None
            else:
                existing_unit_id = uow.session.execute(
                    select(production_work_units.c.id).where(
                        production_work_units.c.production_run_id == existing_run_id
                    )
                ).scalar_one()
                existing_unit = RuntimeStore(uow.session).work_unit(existing_unit_id)
                spine = (existing_run_id, existing_unit)
        if spine is None:
            created = runtime_reality.create_initial_runtime_spine(InitialRunRequest(
                source_baseline_id=baseline.id,
                intent_ref=intent_ref,
                goal=task.objective,
                production_horizon=ProductionHorizon.CODE,
                initial_work_unit_objective=task.objective,
                completion_contract=CompletionContract(
                    required_outputs=(f"branch:{target_branch}@{base_commit}",),
                    verification_obligations=("Observe current branch and exact commit",),
                    task_contract=task,
                ),
            ))
            production_run_id = created.run.id
            pwu_id = created.work_unit.id
            plan_revision_id = created.plan_revision.id
            source_baseline_id = baseline.id
        else:
            production_run_id = spine[0]
            pwu_id = spine[1].id
            plan_revision_id = spine[1].plan_revision_id
            source_baseline_id = spine[1].source_baseline_id
        with self.database.unit_of_work() as uow:
            attempts = RuntimeStore(uow.session).attempts_for_work_unit(pwu_id)
        attempt = attempts[-1] if attempts else runtime_reality.create_initial_attempt(pwu_id)
        attempt_id = attempt.id
        workspace = GitCloneAttemptWorkspace().prepare(
            repository_path=source_repository,
            workspace_root=self.workspace_root,
            attempt_id=attempt_id,
            repository_identity=source_identity,
            source_revision=base_commit,
            repository_ref=source_ref,
        )
        # The Work's remote source, not the internal baseline clone, remains origin.
        self._git(workspace.workspace_path, "remote", "set-url", "origin", source_url)
        payload = {
            "task_contract": task.model_dump(mode="json"),
            "git_operation": {
                "operation": "branch.create",
                "arguments": {"branch": target_branch},
                "expected_revision": base_commit,
            },
        }
        contract_digest = canonical_digest(payload)
        contract_id = uuid5(NAMESPACE_URL, f"watt:native-git-contract:{pwu_id}:{contract_digest}")
        with self.database.unit_of_work() as uow:
            native_store = NativeExecutionStore(uow.session)
            try:
                contract = native_store.contract(contract_id)
            except NativeExecutionNotFound:
                contract = PWUContractVersionRecord(
                    id=contract_id, pwu_id=pwu_id, revision=1,
                    objective=task.objective, contract_payload=payload,
                    contract_digest=contract_digest, created_at=datetime.now(UTC),
                )
        prepared = PreparedExecutionRequest(
            attempt_id=attempt_id, generation=attempt.generation,
            production_run_id=production_run_id,
            work_unit_id=pwu_id,
            plan_revision_id=plan_revision_id,
            source_baseline_id=source_baseline_id,
            context_package_id=uuid5(NAMESPACE_URL, f"watt:native-git-context:{intake_id}"),
            context_package_version=1,
            completion_contract_fingerprint=task.content_fingerprint,
            executor_binding=ExecutorBinding(
                binding_ref="binding:watt-native-git-operation",
                capability_identity="capability:watt-native-executor",
                profile_identity="local-container-v1",
            ),
            workspace=workspace,
        )
        environment = self.production_environment.ensure(
            prepared,
            work_id=work_id,
            task_contract_reference=f"task-contract:{task.task_contract_id}",
            selected_branch=source_ref.removeprefix("refs/heads/"),
        )
        source_vector = SourceVector(members=(SourceMember(
            mount_id="primary", repository_identity=source_identity,
            source_baseline_ref=source_ref, source_commit_oid=base_commit,
            source_tree_oid=tree, container_path="/workspace/primary",
            read_scope=(), write_scope=(), forbidden_paths=(".git",),
            integration_target=source_ref,
        ),))
        manifest = WorkspaceManifest(
            workspace_id=uuid5(NAMESPACE_URL, f"watt:native-git-workspace:{intake_id}"),
            work_id=work_id, pwu_id=pwu_id, attempt_id=attempt_id,
            source_vector_digest=source_vector.digest or "",
            host_storage_id=str(workspace.workspace_path),
            environment_profile_digest=canonical_digest({"profile": "native-git-operation-v1"}),
            mounts=(WorkspaceMount(
                mount_id="primary", host_path=str(workspace.workspace_path),
                container_path="/workspace/primary", writable=True,
                write_scope=(), forbidden_paths=(".git",),
            ),),
            service_resources=self.production_environment.service_resources(environment),
            evidence_namespace=f"native-git:{attempt_id}",
            retention_policy="work-repository-asset",
        )
        binding = ExecutionBindingV2(
            work_id=work_id, steering_decision_id=active_steering.id,
            pwu_id=pwu_id, pwu_contract_version_id=contract.id,
            pwu_contract_digest=contract.contract_digest,
            attempt_id=attempt_id, generation=attempt.generation, session_id=session_id,
            source_vector=source_vector, workspace=manifest,
            context_package_ref=f"task-contract:{task.task_contract_id}",
            materialized_input_digest=canonical_digest(payload),
            backend_implementation="watt-native", backend_version="2",
            inference_profile=self.provider_profile,
            capability_grants=(CapabilityGrant(
                identity="git.operation", version="1",
                scope={"capabilities": ["git.branch.create"]},
            ),),
            resource_envelope=ResourceEnvelope(
                envelope_id=uuid5(NAMESPACE_URL, f"watt:native-git-envelope:{intake_id}"),
                policy_version="native-git-operation-v1",
                max_inference_submissions=3, max_tool_effects=2,
                max_active_seconds=300,
                provider_profile=self.provider_profile,
            ),
            obligation_references=(
                f"task-contract:{task.task_contract_id}",
                f"work-reality-revision:{revision.id}",
                f"steering-plan-revision:{active_steering.id}",
            ),
        )
        entry = self.runtime.admit(NativeExecutionAdmission(
            command_id=uuid5(NAMESPACE_URL, f"watt:native-git-command:{intake_id}"),
            actor_identity=authority_identity,
            fairness_group=f"work:{work_id}",
            binding=binding, contract=contract,
            materialization_path=str(workspace.workspace_path),
            required_resource_profile="standard",
            available_at=datetime.now(UTC),
        ))
        provider = self.production_environment.provider
        storage = ContentAddressedStorage(self.checkpoint_root / "native-git")

        def kernel_factory(grant):
            tools = ProductionEnvironmentNativeToolHost.from_manifest(
                manifest, provider=provider,
            )
            assert tools is not None
            return NativeExecutorKernel(
                inference=GovernedGitOperationInferenceAdapter(
                    operation="branch.create",
                    arguments={"branch": target_branch},
                    expected_revision=base_commit,
                ),
                tools=tools.registry(),
                checkpoints=DurableCheckpointPort(
                    self.database, storage, attempt_id=attempt_id,
                    session_id=session_id, worker_epoch=grant.allocation.lease_epoch,
                ),
                audit=DurableKernelAudit(
                    self.database, attempt_id=attempt_id,
                    session_id=session_id, pwu_id=pwu_id,
                    envelope_id=binding.resource_envelope.envelope_id,
                ),
            )

        offer = WorkerOffer(
            worker_id=f"native-git-operation:{work_id}",
            worker_profile="local-container-v1",
            provider_profiles=(self.provider_profile,),
            resource_profiles=("standard",),
            capability_identities=("git.operation",),
            lease_seconds=30,
        )
        handle = ExecutionHandle(
            backend_identity="watt-native", dispatch_id=entry.id,
            attempt_id=attempt_id, generation=attempt.generation,
            opaque_reference=f"queue:{entry.id}",
        )
        observed = self.runtime.observe(handle)
        if observed.runtime_mode is not ExecutionMode.FINISHED:
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix="watt-native-git") as pool:
                pool.submit(
                    lambda: asyncio.run(
                        NativeExecutionWorker(self.runtime, kernel_factory).run_once(offer)
                    )
                ).result()
            observed = self.runtime.observe(handle)
        if observed.terminal_outcome is not AttemptTerminalOutcome.RESULT_READY:
            with self.database.unit_of_work() as uow:
                native_store = NativeExecutionStore(uow.session)
                results = native_store.tool_results_after(attempt_id, after_step_sequence=0)
            return {
                "condition": "RUNNING" if observed.runtime_mode is not ExecutionMode.FINISHED else "FAILED_RETRYABLE",
                "native_attempt_id": str(attempt_id),
                "pwu_id": str(pwu_id),
                "task_contract_id": str(task.task_contract_id),
                "checkpoint_id": None if observed.current_checkpoint_id is None else str(observed.current_checkpoint_id),
                "terminal_outcome": None if observed.terminal_outcome is None else observed.terminal_outcome.value,
                "progress_summary": observed.progress_summary,
                "tool_result_conditions": [result.condition.value for result in results],
            }
        branch = self._git(workspace.workspace_path, "branch", "--show-current")
        revision_after = self._git(workspace.workspace_path, "rev-parse", "HEAD^{commit}")
        if branch != target_branch or revision_after != base_commit:
            raise RuntimeError("Native Git result differs from Work branch obligation")
        if observed.current_checkpoint_id is None:
            raise RuntimeError("Native Git success has no durable checkpoint")
        record_id = uuid5(NAMESPACE_URL, f"watt:git-production-record:{attempt_id}")
        existing_record = self.production_environment.store.get_git_operation_record(record_id)
        record = existing_record or self.production_environment.store.save_git_operation_record(
            GitOperationProductionRecordV1(
                id=record_id,
                work_id=work_id,
                task_contract_id=task.task_contract_id,
                pwu_id=pwu_id,
                attempt_id=attempt_id,
                environment_id=environment.environment.id,
                checkpoint_id=observed.current_checkpoint_id,
                capability_id="git.branch.create",
                operation="branch.create",
                repository_identity=source_identity,
                source_revision=base_commit,
                resulting_branch=branch,
                resulting_revision=revision_after,
                verification_reference=f"native-checkpoint:{observed.current_checkpoint_id}",
                created_at=datetime.now(UTC),
            )
        )
        if (
            record.work_id != work_id or record.pwu_id != pwu_id
            or record.resulting_branch != branch or record.resulting_revision != revision_after
        ):
            raise RuntimeError("Git Production Record differs from current native result")
        self.production_environment.suspend(
            attempt_id,
            evidence_references=(
                f"native-attempt:{attempt_id}",
                f"native-checkpoint:{observed.current_checkpoint_id}",
            ),
        )
        return {
            "condition": "READY",
            "workspace_path": str(workspace.workspace_path),
            "branch": branch,
            "revision": revision_after,
            "native_attempt_id": str(attempt_id),
            "pwu_id": str(pwu_id),
            "task_contract_id": str(task.task_contract_id),
            "checkpoint_id": str(observed.current_checkpoint_id),
            "environment_id": str(environment.environment.id),
            "production_record_id": str(record.id),
        }
