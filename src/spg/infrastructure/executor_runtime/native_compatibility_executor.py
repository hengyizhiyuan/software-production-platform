"""Compatibility seam from the current synchronous Work flow to native v2."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import subprocess
import time
from uuid import NAMESPACE_URL, UUID, uuid5

from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.application.connectors import ConnectorResolver
from spg.application.native_connector_qualification import NativeConnectorQualificationService
from spg.application.native_production_environment import (
    NativeProductionEnvironmentRuntime,
)
from spg.domain.execution import (
    ExecutorDispatchRequest,
    ExecutorDispatchResult,
    ExecutorReturnControl,
    ProviderReportedOutcome,
)
from spg.domain.native_execution import (
    AttemptTerminalOutcome,
    CapabilityGrant,
    ExecutionBindingV2,
    ExecutionMode,
    NativeExecutionAdmission,
    NativeExecutionNotFound,
    PWUContractVersionRecord,
    ResourceEnvelope,
    SourceMember,
    SourceVector,
    WorkspaceManifest,
    WorkspaceMount,
    canonical_digest,
)
from spg.domain.connectors import CapabilityRequirement, SideEffectLevel
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore


class NativeQueuedExecutorCapability:
    """Submit current v1 prepared Reality to native v2 during controlled migration.

    The adapter blocks only the existing process-local orchestrator thread. Native
    execution, queue state, checkpoints, controls, and recovery remain durable and
    independently observable. Completion and trust stay with the existing owners.
    """

    def __init__(
        self,
        database: Database,
        runtime: NativeExecutorRuntimeService,
        *,
        provider_profile: str,
        resource_profile: str,
        environment_profile: str,
        poll_seconds: float = 1.0,
        wait_seconds: float = 3600.0,
        production_environment: NativeProductionEnvironmentRuntime | None = None,
    ) -> None:
        self.database = database
        self.runtime = runtime
        self.provider_profile = provider_profile
        self.resource_profile = resource_profile
        self.environment_profile = environment_profile
        self.poll_seconds = poll_seconds
        self.wait_seconds = wait_seconds
        self.production_environment = production_environment

    def dispatch(self, request: ExecutorDispatchRequest) -> ExecutorDispatchResult:
        started = datetime.now(UTC)
        admission = self._admission(request)
        entry = self.runtime.admit(admission)
        deadline = time.monotonic() + self.wait_seconds
        while time.monotonic() < deadline:
            observation = self.runtime.observe(
                self._handle(request, entry.id)
            )
            if observation.runtime_mode is ExecutionMode.FINISHED:
                return self._terminal_result(
                    request,
                    observation.terminal_outcome,
                    started,
                    observation.current_checkpoint_id,
                )
            if observation.runtime_mode is ExecutionMode.STOPPED:
                return self._terminal_result(
                    request,
                    observation.terminal_outcome,
                    started,
                    observation.current_checkpoint_id,
                )
            time.sleep(self.poll_seconds)
        return ExecutorDispatchResult(
            provider_reference=f"watt-native:{request.execution.attempt_id}",
            outcome=ProviderReportedOutcome.UNKNOWN,
            started_at=started,
            finished_at=datetime.now(UTC),
            metadata={
                "backend": "watt-native",
                "queue_entry_id": str(entry.id),
                "wait_timeout": True,
            },
            summary="Native execution remains durable but the compatibility wait expired.",
            return_control=ExecutorReturnControl.EXECUTION_CONTINUITY_LOST,
        )

    def terminal_result(self, attempt_id: UUID) -> ExecutorDispatchResult | None:
        """Return a terminal native claim for restart reconciliation, if available."""

        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            try:
                state = store.attempt_state(attempt_id)
            except NativeExecutionNotFound:
                return None
        if state.runtime_mode not in {ExecutionMode.FINISHED, ExecutionMode.RECONCILING}:
            return None
        with self.database.unit_of_work() as uow:
            dispatch = RuntimeStore(uow.session).execution_dispatch_for_attempt(attempt_id)
        if dispatch is None:
            return None
        result = self._result_for_attempt(
            attempt_id,
            state.terminal_outcome,
            dispatch.dispatched_at,
        )
        if (
            state.terminal_outcome is AttemptTerminalOutcome.RESULT_READY
            and state.current_checkpoint_id is not None
        ):
            try:
                with self.database.unit_of_work() as uow:
                    attempt = RuntimeStore(uow.session).attempt(attempt_id)
                if attempt is None:
                    raise RuntimeError("Native retention Attempt lineage is missing")
                retained = self._retain_successful_capabilities_for_work_unit(
                    attempt.work_unit_id, state.current_checkpoint_id,
                )
            except Exception as error:
                result = result.model_copy(update={"metadata": {
                    **result.metadata,
                    "connector_retention_condition": "RETRY_REQUIRED",
                    "connector_retention_error_type": type(error).__name__,
                }})
            else:
                if retained:
                    result = result.model_copy(update={"metadata": {
                        **result.metadata, "retained_user_capabilities": list(retained),
                    }})
        production_environment = getattr(self, "production_environment", None)
        if production_environment is not None:
            environment = production_environment.suspend(
                attempt_id,
                evidence_references=self._environment_evidence_references(
                    attempt_id,
                    state.current_checkpoint_id,
                ),
            )
            result = self._with_environment_metadata(result, environment)
        return result

    def _admission(self, request: ExecutorDispatchRequest) -> NativeExecutionAdmission:
        execution = request.execution
        with self.database.unit_of_work() as uow:
            runtime_store = RuntimeStore(uow.session)
            product_store = ProductStore(uow.session)
            work_unit = runtime_store.work_unit(execution.work_unit_id)
            attempt = runtime_store.attempt(execution.attempt_id)
            snapshot = runtime_store.snapshot(execution.source_baseline_id)
            package = runtime_store.context_package(execution.context_package_id)
            product_binding = product_store.runtime_binding_for_work_unit(
                execution.work_unit_id
            )
            work_revision = (
                None if product_binding is None
                else product_store.current_work_reality_revision(product_binding.work_id)
            )
        if any(item is None for item in (work_unit, attempt, snapshot, package)):
            raise RuntimeError("native compatibility admission lineage is incomplete")
        work_id = (
            product_binding.work_id
            if product_binding is not None
            else execution.production_run_id
        )
        work_authority = (
            work_revision.admitted_by if work_revision is not None
            else product_binding.admitted_by if product_binding is not None
            else "system"
        )
        repository = Path(execution.workspace.repository_path).resolve()
        workspace = Path(execution.workspace.workspace_path).resolve()
        commit = self._git(repository, "rev-parse", execution.workspace.source_revision)
        tree = self._git(repository, "rev-parse", f"{commit}^{{tree}}")
        write_paths, forbidden_paths = self._path_policy(
            work_unit.completion_contract
        )
        source_vector = SourceVector(
            members=(
                SourceMember(
                    mount_id="primary",
                    repository_identity=execution.workspace.repository_identity,
                    source_baseline_ref=snapshot.repository_ref,
                    source_commit_oid=commit,
                    source_tree_oid=tree,
                    container_path="/workspace/primary",
                    read_scope=(),
                    write_scope=write_paths,
                    forbidden_paths=forbidden_paths,
                    integration_target=snapshot.repository_ref,
                ),
            )
        )
        contract_payload = {
            "objective": work_unit.objective,
            "completion_contract": work_unit.completion_contract.model_dump(mode="json"),
            "context_package_id": str(package.id),
            "context_package_fingerprint": package.content_fingerprint,
        }
        contract_digest = canonical_digest(contract_payload)
        with self.database.unit_of_work() as uow:
            contract = NativeExecutionStore(uow.session).contract_for_pwu_digest(
                execution.work_unit_id,
                contract_digest,
            )
        if contract is None:
            contract = PWUContractVersionRecord(
                id=uuid5(
                    NAMESPACE_URL,
                    f"watt-native:contract:{execution.work_unit_id}:{contract_digest}",
                ),
                pwu_id=execution.work_unit_id,
                revision=execution.generation,
                objective=work_unit.objective,
                contract_payload=contract_payload,
                contract_digest=contract_digest,
                created_at=started_at(request),
            )
        session_id = uuid5(NAMESPACE_URL, f"watt-native:session:{execution.work_unit_id}")
        workspace_id = uuid5(NAMESPACE_URL, f"watt-native:workspace:{execution.attempt_id}")
        envelope = ResourceEnvelope(
            envelope_id=uuid5(NAMESPACE_URL, f"watt-native:envelope:{execution.attempt_id}"),
            policy_version="watt-native-mvp-v1",
            max_inference_submissions=120,
            max_tool_effects=400,
            max_active_seconds=int(self.wait_seconds),
            provider_profile=self.provider_profile,
        )
        environment_binding = None
        production_environment = getattr(self, "production_environment", None)
        if production_environment is not None:
            task_contract = work_unit.completion_contract.task_contract
            task_contract_reference = (
                f"task-contract:{task_contract.task_contract_id}"
                if task_contract is not None
                else f"pwu-contract:{contract.id}"
            )
            environment_binding = production_environment.ensure(
                execution,
                work_id=work_id,
                task_contract_reference=task_contract_reference,
                selected_branch=snapshot.repository_ref.removeprefix("refs/heads/"),
            )
        workspace_manifest = WorkspaceManifest(
            workspace_id=workspace_id,
            work_id=work_id,
            pwu_id=execution.work_unit_id,
            attempt_id=execution.attempt_id,
            source_vector_digest=source_vector.digest or "",
            host_storage_id=str(workspace),
            environment_profile_digest=canonical_digest(
                {"profile": self.environment_profile}
            ),
            mounts=(
                WorkspaceMount(
                    mount_id="primary",
                    host_path=str(workspace),
                    container_path="/workspace/primary",
                    writable=True,
                    write_scope=write_paths,
                    forbidden_paths=forbidden_paths,
                ),
            ),
            service_resources=(
                ()
                if environment_binding is None
                else production_environment.service_resources(
                    environment_binding
                )
            ),
            evidence_namespace=f"native:{execution.attempt_id}",
            retention_policy="native-hot-30d",
        )
        capability_ids = (
            "file.read", "file.write", "process.run", "git.status", "git.diff",
            "test.run", "build.run", "dependency.sync", "preview.inspect",
        )
        task_contract = work_unit.completion_contract.task_contract
        required_capabilities = tuple(
            () if task_contract is None else task_contract.required_capabilities
        )
        git_capabilities = tuple(
            item for item in (
                required_capabilities
            )
            if item.startswith("git.")
        )
        filesystem_capabilities = tuple(
            item for item in required_capabilities
            if item.startswith("filesystem.") and item not in {"filesystem.read", "filesystem.write"}
        )
        if git_capabilities and environment_binding is None:
            raise RuntimeError("Governed Git operations require an assigned Production Environment")
        if filesystem_capabilities and environment_binding is None:
            raise RuntimeError("Governed filesystem operations require an assigned Production Environment")
        resolver = ConnectorResolver(self.database)
        for capability_id in required_capabilities:
            requirement = CapabilityRequirement(
                    capability_id=capability_id,
                    work_id=work_id,
                    user_id=work_authority,
                    operation_ref=f"task-contract:{task_contract.task_contract_id}",
                    resume_point={
                        "pwu_id": str(execution.work_unit_id),
                        "attempt_id": str(execution.attempt_id),
                    },
                )
            resolution = resolver.resolve(requirement)
            if not resolution.executable and environment_binding is not None:
                candidate = resolver.propose_generic_candidate(requirement)
                if candidate is not None:
                    permissions = tuple(
                        item.removeprefix("permission:")
                        for item in (() if task_contract is None else task_contract.scope)
                        if item.startswith("permission:")
                    )
                    qualified = NativeConnectorQualificationService(
                        self.database, self.runtime,
                        provider=production_environment.provider,
                        checkpoint_root=production_environment.store.root.parent.parent / "nqc",
                    ).qualify(
                        candidate,
                        source_baseline_id=execution.source_baseline_id,
                        source_vector=source_vector,
                        workspace=workspace_manifest,
                        authority_identity=work_authority,
                        admitted_permissions=permissions,
                    )
                    if qualified:
                        resolution = resolver.resolve(requirement)
            if not resolution.executable:
                raise RuntimeError(
                    f"Required capability {capability_id} is unavailable; Work gap {resolution.gap_id} is resumable"
                )
            if resolution.capability is not None and resolution.capability.side_effect_level is SideEffectLevel.DESTRUCTIVE:
                required_permissions = resolution.capability.permissions_required
                if work_revision is None or any(
                    f"permission:{permission}" not in task_contract.scope
                    for permission in required_permissions
                ):
                    raise RuntimeError("Destructive Connector operation lacks explicit Work permission")
        if git_capabilities:
            capability_ids = (*capability_ids, "git.operation")
        if filesystem_capabilities:
            capability_ids = (*capability_ids, "filesystem.operation")
        binding = ExecutionBindingV2(
            work_id=work_id,
            steering_decision_id=execution.plan_revision_id,
            pwu_id=execution.work_unit_id,
            pwu_contract_version_id=contract.id,
            pwu_contract_digest=contract.contract_digest,
            attempt_id=execution.attempt_id,
            generation=execution.generation,
            session_id=session_id,
            source_vector=source_vector,
            workspace=workspace_manifest,
            context_package_ref=f"context-package:{execution.context_package_id}",
            materialized_input_digest=canonical_digest(execution),
            backend_implementation="watt-native",
            backend_version="1",
            inference_profile=self.provider_profile,
            capability_grants=tuple(
                CapabilityGrant(
                    identity=identity,
                    version="1",
                    scope={
                        "paths": list(write_paths),
                        "forbidden_paths": list(forbidden_paths),
                        "capabilities": (
                            list(git_capabilities) if identity == "git.operation"
                            else list(filesystem_capabilities) if identity == "filesystem.operation"
                            else []
                        ),
                        "permissions": [
                            item.removeprefix("permission:")
                            for item in (() if task_contract is None else task_contract.scope)
                            if item.startswith("permission:")
                        ],
                    },
                )
                for identity in capability_ids
            ),
            resource_envelope=envelope,
            stop_conditions=tuple(work_unit.completion_contract.blocking_conditions),
            obligation_references=tuple(
                (
                    *(
                        ()
                        if work_unit.completion_contract.task_contract is None
                        else (
                            "task-contract:"
                            f"{work_unit.completion_contract.task_contract.task_contract_id}",
                        )
                    ),
                    *work_unit.completion_contract.verification_obligations,
                    *(
                        f"semantic-fact:{item.fact_id}"
                        for item in work_unit.completion_contract.semantic_fact_obligations
                    ),
                )
            ),
        )
        return NativeExecutionAdmission(
            command_id=request.dispatch_id,
            actor_identity="spg-runtime:native-compatibility",
            fairness_group=f"work:{work_id}",
            binding=binding,
            contract=contract,
            materialization_path=str(workspace),
            required_resource_profile=self.resource_profile,
            available_at=datetime.now(UTC),
        )

    def _terminal_result(
        self,
        request: ExecutorDispatchRequest,
        outcome: AttemptTerminalOutcome | None,
        started: datetime,
        checkpoint_id: UUID | None,
    ) -> ExecutorDispatchResult:
        result = self._result(request, outcome, started)
        if outcome is AttemptTerminalOutcome.RESULT_READY and checkpoint_id is not None:
            try:
                retained = self._retain_successful_capabilities(request, checkpoint_id)
            except Exception as error:
                result = result.model_copy(update={
                    "metadata": {
                        **result.metadata,
                        "connector_retention_condition": "RETRY_REQUIRED",
                        "connector_retention_error_type": type(error).__name__,
                    }
                })
            else:
                if retained:
                    result = result.model_copy(update={
                        "metadata": {
                            **result.metadata,
                            "retained_user_capabilities": list(retained),
                        }
                    })
        production_environment = getattr(self, "production_environment", None)
        if production_environment is None:
            return result
        environment = production_environment.suspend(
            request.execution.attempt_id,
            evidence_references=self._environment_evidence_references(
                request.execution.attempt_id,
                checkpoint_id,
            ),
        )
        return self._with_environment_metadata(result, environment)

    def _retain_successful_capabilities(
        self,
        request: ExecutorDispatchRequest,
        checkpoint_id: UUID,
    ) -> tuple[str, ...]:
        return self._retain_successful_capabilities_for_work_unit(
            request.execution.work_unit_id, checkpoint_id,
        )

    def _retain_successful_capabilities_for_work_unit(
        self,
        work_unit_id: UUID,
        checkpoint_id: UUID,
    ) -> tuple[str, ...]:
        with self.database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            binding = product.runtime_binding_for_work_unit(work_unit_id)
            work_unit = RuntimeStore(uow.session).work_unit(work_unit_id)
            revision = (
                None if binding is None
                else product.current_work_reality_revision(binding.work_id)
            )
        if binding is None or work_unit is None:
            return ()
        contract = work_unit.completion_contract.task_contract
        if contract is None:
            return ()
        resolver = ConnectorResolver(self.database)
        retained = []
        for capability_id in contract.required_capabilities:
            requirement = CapabilityRequirement(
                capability_id=capability_id,
                work_id=binding.work_id,
                user_id=(revision.admitted_by if revision is not None else binding.admitted_by),
                operation_ref=f"task-contract:{contract.task_contract_id}",
            )
            result = resolver.retain_successful_work_capability_for_user(
                requirement,
                successful_execution_evidence=f"native-checkpoint:{checkpoint_id}",
            )
            if result is not None:
                retained.append(capability_id)
        return tuple(retained)

    def _environment_evidence_references(
        self,
        attempt_id: UUID,
        checkpoint_id: UUID | None,
    ) -> tuple[str, ...]:
        with self.database.unit_of_work() as uow:
            evidence = NativeExecutionStore(uow.session).evidence_for_attempt(attempt_id)
        return (
            f"native-attempt:{attempt_id}",
            *((f"native-checkpoint:{checkpoint_id}",) if checkpoint_id else ()),
            *(
                f"native-evidence:{item.id}:{item.content_digest}"
                for item in evidence
            ),
        )

    @staticmethod
    def _with_environment_metadata(result, environment):
        return result.model_copy(
            update={
                "metadata": {
                    **result.metadata,
                    "production_environment_id": str(environment.id),
                    "production_workspace_id": str(environment.workspace_id),
                    "environment_reference": f"production-environment:{environment.id}",
                    "environment_lifecycle_state": environment.lifecycle_state.value,
                    "environment_evidence_references": list(
                        environment.evidence_references
                    ),
                }
            }
        )

    @staticmethod
    def _handle(request: ExecutorDispatchRequest, queue_id: UUID):
        from spg.domain.native_execution import ExecutionHandle

        return ExecutionHandle(
            backend_identity="watt-native",
            dispatch_id=queue_id,
            attempt_id=request.execution.attempt_id,
            generation=request.execution.generation,
            opaque_reference=f"queue:{queue_id}",
        )

    @staticmethod
    def _result(
        request: ExecutorDispatchRequest,
        outcome: AttemptTerminalOutcome | None,
        started: datetime,
    ) -> ExecutorDispatchResult:
        return NativeQueuedExecutorCapability._result_for_attempt(
            request.execution.attempt_id, outcome, started
        )

    @staticmethod
    def _result_for_attempt(
        attempt_id: UUID,
        outcome: AttemptTerminalOutcome | None,
        started: datetime,
    ) -> ExecutorDispatchResult:
        success = outcome is AttemptTerminalOutcome.RESULT_READY
        known_failure = outcome in {
            AttemptTerminalOutcome.UNABLE_TO_COMPLETE,
            AttemptTerminalOutcome.BOUNDARY_CROSSING_REQUIRED,
            AttemptTerminalOutcome.BUDGET_EXHAUSTED,
            AttemptTerminalOutcome.STOPPED,
            AttemptTerminalOutcome.CANCELLED,
        }
        return_control = {
            AttemptTerminalOutcome.RESULT_READY: ExecutorReturnControl.RESULT_READY,
            AttemptTerminalOutcome.BOUNDARY_CROSSING_REQUIRED: ExecutorReturnControl.BOUNDARY_CROSSING_REQUIRED,
            AttemptTerminalOutcome.BUDGET_EXHAUSTED: ExecutorReturnControl.BUDGET_EXHAUSTED,
        }.get(outcome, ExecutorReturnControl.UNABLE_TO_COMPLETE if known_failure else ExecutorReturnControl.EXECUTION_CONTINUITY_LOST)
        return ExecutorDispatchResult(
            provider_reference=f"watt-native:{attempt_id}",
            outcome=(
                ProviderReportedOutcome.SUCCESS
                if success
                else ProviderReportedOutcome.FAILURE
                if known_failure
                else ProviderReportedOutcome.UNKNOWN
            ),
            started_at=started,
            finished_at=datetime.now(UTC),
            metadata={
                "backend": "watt-native",
                "terminal_outcome": outcome.value if outcome else None,
            },
            summary=f"Watt-native Executor returned {outcome.value if outcome else 'UNKNOWN'}.",
            return_control=return_control,
        )

    @staticmethod
    def _path_policy(completion_contract) -> tuple[tuple[str, ...], tuple[str, ...]]:
        if completion_contract.change_contract is not None:
            change = completion_contract.change_contract
            allowed = tuple(
                dict.fromkeys(
                    tuple(target.path for target in change.exact_targets)
                    + tuple(change.allowed_areas)
                )
            )
            return allowed, tuple(dict.fromkeys((".git",) + change.forbidden_areas))
        if completion_contract.artifact_contract is not None:
            return (completion_contract.artifact_contract.artifact_path,), (".git",)
        return ("src", "tests", "docs"), (".git",)

    @staticmethod
    def _git(repository: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode:
            raise RuntimeError(f"native source observation failed: {result.stderr.strip()}")
        return result.stdout.strip()


def started_at(request: ExecutorDispatchRequest) -> datetime:
    """Return deterministic persisted dispatch time when not exposed in v1 input."""

    del request
    return datetime.now(UTC)
