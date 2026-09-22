"""Bind the existing Native Executor Attempt to a Production Environment."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import subprocess
from uuid import UUID, uuid4

from spg.application.production_environment import ProductionEnvironmentLifecycle
from spg.domain.preparation import PreparedExecutionRequest
from spg.domain.production_environment import (
    EnvironmentConfiguration,
    EnvironmentLifecycleState,
    EnvironmentProvisionRequest,
    EnvironmentRuntimeState,
    LifecycleDecisionContext,
    NativeExecutionEnvironmentBindingV1,
    PreparedRepositoryMount,
    PreparedWorkspaceV1,
    ProductionEnvironmentError,
    ProductionEnvironmentProvider,
    ProductionEnvironmentV1,
    ProductionWorkspaceV1,
    RepositoryAcquisitionPolicyV1,
    RepositoryAssetBinding,
    RepositoryBranchSelection,
    RuntimeConfiguration,
)
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore


class NativeProductionEnvironmentRuntime:
    """Own WHERE for an already-governed Work/PWU/Native Attempt."""

    def __init__(
        self,
        *,
        store: JsonProductionEnvironmentStore,
        provider: ProductionEnvironmentProvider,
        image_reference: str,
        lifecycle: ProductionEnvironmentLifecycle | None = None,
    ) -> None:
        self.store = store
        self.provider = provider
        self.image_reference = image_reference
        self.lifecycle = lifecycle or ProductionEnvironmentLifecycle()

    def ensure(
        self,
        execution: PreparedExecutionRequest,
        *,
        work_id: UUID,
        task_contract_reference: str,
        selected_branch: str,
        requested_branch: str | None = None,
    ) -> NativeExecutionEnvironmentBindingV1:
        existing = self.store.get_native_execution_binding(execution.attempt_id)
        if existing is not None:
            if (
                existing.work_id != work_id
                or existing.pwu_id != execution.work_unit_id
                or existing.task_contract_reference != task_contract_reference
            ):
                raise ProductionEnvironmentError(
                    "Native Attempt already has a different Production Environment binding"
                )
            return existing

        now = datetime.now(UTC)
        repository = execution.workspace.repository_path.resolve()
        workspace_path = execution.workspace.workspace_path.resolve()
        tree = self._git(repository, "rev-parse", f"{execution.workspace.source_revision}^{{tree}}")
        workspace = ProductionWorkspaceV1(
            id=uuid4(),
            work_id=work_id,
            repository_assets=(
                RepositoryAssetBinding(
                    asset_id=uuid4(),
                    repository_identity=execution.workspace.repository_identity,
                    source=str(repository),
                    branch=selected_branch,
                    default_branch=selected_branch,
                    requested_branch=requested_branch,
                    source_revision=execution.workspace.source_revision,
                    source_tree_identity=tree,
                    acquisition_policy=RepositoryAcquisitionPolicyV1(
                        branch_selection=(
                            RepositoryBranchSelection.HUMAN_REQUESTED
                            if requested_branch is not None
                            else RepositoryBranchSelection.REPOSITORY_DEFAULT
                        )
                    ),
                    mount_path="/workspace/primary",
                    writable=True,
                    provenance_reference=f"source-baseline:{execution.source_baseline_id}",
                ),
            ),
            environment_configuration=EnvironmentConfiguration(
                provider_profile="container-v1",
                dependency_profile_reference="native-executor:task-contract",
                lifecycle_policy_references=(
                    "watt:production-environment:structural-lifecycle:v1",
                ),
            ),
            runtime_configuration=RuntimeConfiguration(
                runtime_profile="watt-native-executor-v2",
                network_policy_reference="network:none",
                resource_policy_reference="native-resource-envelope",
            ),
            created_at=now,
        )
        prepared = PreparedWorkspaceV1(
            workspace_id=workspace.id,
            root_path=workspace_path.parent,
            repository_mounts=(
                PreparedRepositoryMount(
                    repository_identity=execution.workspace.repository_identity,
                    host_path=workspace_path,
                    container_path="/workspace/primary",
                    source_revision=execution.workspace.source_revision,
                    writable=True,
                ),
            ),
            prepared_at=now,
        )
        environment = ProductionEnvironmentV1(
            id=uuid4(),
            work_id=work_id,
            workspace_id=workspace.id,
            lifecycle_state=EnvironmentLifecycleState.CREATED,
            runtime_state=EnvironmentRuntimeState.NOT_PROVISIONED,
            created_at=now,
            updated_at=now,
        )
        self.store.create_workspace(workspace)
        self.store.create_environment(environment)
        environment = self._transition(
            environment,
            EnvironmentLifecycleState.INITIALIZING,
            work_state="EXECUTOR_ADMITTED",
            reason="prepare Production Environment for Native Executor Attempt",
        )
        handle = None
        try:
            handle = self.provider.create_workspace_environment(
                EnvironmentProvisionRequest(
                    environment=environment,
                    workspace=workspace,
                    prepared_workspace=prepared,
                    image_reference=self.image_reference,
                )
            )
            environment = self._transition(
                environment,
                EnvironmentLifecycleState.ACTIVE,
                work_state="EXECUTING",
                reason="Native Executor runtime is ready",
                provider_reference=(
                    f"{handle.provider_identity}:{handle.opaque_reference}"
                ),
            )
            return self.store.save_native_execution_binding(
                NativeExecutionEnvironmentBindingV1(
                    work_id=work_id,
                    pwu_id=execution.work_unit_id,
                    attempt_id=execution.attempt_id,
                    task_contract_reference=task_contract_reference,
                    workspace=workspace,
                    prepared_workspace=prepared,
                    environment=environment,
                    provider_handle=handle,
                    created_at=datetime.now(UTC),
                )
            )
        except Exception:
            if handle is not None:
                self.provider.cleanup(handle)
            raise

    def suspend(
        self,
        attempt_id: UUID,
        *,
        artifact_references: tuple[str, ...] = (),
        evidence_references: tuple[str, ...] = (),
    ) -> ProductionEnvironmentV1:
        binding = self.store.get_native_execution_binding(attempt_id)
        if binding is None:
            raise ProductionEnvironmentError("Native Production Environment is unavailable")
        current = self.store.get_environment(binding.environment.id)
        if current is None:
            raise ProductionEnvironmentError("Native Production Environment disappeared")
        if current.lifecycle_state is EnvironmentLifecycleState.SUSPENDED:
            return current
        self.provider.cleanup(binding.provider_handle)
        return self._transition(
            current,
            EnvironmentLifecycleState.SUSPENDED,
            work_state="EXECUTOR_RETURNED",
            reason="Native Executor returned control and container runtime stopped",
            artifact_references=artifact_references,
            evidence_references=evidence_references,
        )

    @staticmethod
    def service_resources(
        binding: NativeExecutionEnvironmentBindingV1,
    ) -> tuple[str, ...]:
        return (
            f"production-environment:{binding.environment.id}",
            f"production-workspace:{binding.workspace.id}",
            f"production-environment-provider:{binding.provider_handle.provider_identity}",
            f"production-environment-handle:{binding.provider_handle.opaque_reference}",
        )

    def _transition(
        self,
        environment: ProductionEnvironmentV1,
        target: EnvironmentLifecycleState,
        *,
        work_state: str,
        reason: str,
        provider_reference: str | None = None,
        artifact_references: tuple[str, ...] | None = None,
        evidence_references: tuple[str, ...] | None = None,
    ) -> ProductionEnvironmentV1:
        updated, transition = self.lifecycle.transition(
            environment,
            target=target,
            context=LifecycleDecisionContext(work_state=work_state),
            actor_reference="watt:native-executor-production-environment:v1",
            reason=reason,
            decided_at=datetime.now(UTC),
            provider_reference=provider_reference,
            artifact_references=artifact_references,
            evidence_references=evidence_references,
        )
        return self.store.apply_transition(environment, updated, transition)

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
            raise ProductionEnvironmentError(
                result.stderr.strip() or "Native repository observation failed"
            )
        return result.stdout.strip()
