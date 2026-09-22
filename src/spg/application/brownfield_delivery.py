"""Governed Brownfield Feature Delivery vertical slice.

The service composes existing ownership boundaries. Watt orchestrates Work and
the Production Environment; ECF owns admitted Reality; the provider owns where
commands run; Human decisions own acceptance and delivery authorization; and
Guardian receives evidence references without issuing an assurance decision.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import subprocess
from typing import Callable, Protocol
from uuid import UUID, uuid4

from spg.application.production_environment import (
    DeliveryAuthorizationService,
    ProductionEnvironmentLifecycle,
    production_resource_references,
    preview_runtime_from_observation,
)
from spg.application.production_environment_contracts import (
    change_reality_v1_payload,
    delivery_reality_v1_payload,
    guardian_assurance_intake_v1_payload,
    workspace_reality_v1_payload,
)
from spg.domain.brownfield_delivery import (
    BrownfieldDeliveryCompletionV1,
    BrownfieldFeatureDeliveryRequest,
    BrownfieldReviewSessionV1,
)
from spg.domain.production_environment import (
    DeliveryIntentKind,
    DeliveryIntentV1,
    DeliveryResultReference,
    EnvironmentConfiguration,
    EnvironmentLifecycleState,
    EnvironmentProvisionRequest,
    EnvironmentRuntimeState,
    HumanDeliveryAction,
    HumanDeliveryDecision,
    LifecycleDecisionContext,
    ProductionChangeReference,
    ProductionChangeType,
    ProductionDeliveryState,
    ProductionEnvironmentError,
    ProductionEnvironmentProvider,
    ProductionEnvironmentV1,
    ProductionRecordV1,
    ProductionWorkspaceV1,
    RepositoryAcquisitionPolicyV1,
    RepositoryAssetBinding,
    RepositoryRevisionReference,
    RuntimeConfiguration,
    VerificationOutcome,
    VerificationResultReference,
    canonical_digest,
)
from spg.infrastructure.production_environment import (
    GitDeliveryPreparer,
    GitIsolatedWorkspacePreparer,
    StaticPreviewRuntime,
)
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore


class RealityGateway(Protocol):
    def discover_repository_payload(self, *args, **kwargs) -> dict: ...

    def admit_workspace_payload(self, payload: dict) -> dict: ...

    def admit_change_payload(self, payload: dict) -> dict: ...

    def admit_delivery_payload(self, payload: dict) -> dict: ...


class GuardianIntakeGateway(Protocol):
    def admit_payload(self, payload: dict) -> dict: ...


class BrownfieldDeliveryError(ProductionEnvironmentError):
    pass


class BrownfieldFeatureDeliveryService:
    """Run one exact-revision, one-repository Brownfield delivery journey."""

    def __init__(
        self,
        *,
        store: JsonProductionEnvironmentStore,
        reality: RealityGateway,
        guardian: GuardianIntakeGateway,
        workspace_preparer: GitIsolatedWorkspacePreparer,
        provider: ProductionEnvironmentProvider,
        preview_runtime: StaticPreviewRuntime,
        work_exists: Callable[[UUID], bool],
        lifecycle: ProductionEnvironmentLifecycle | None = None,
        delivery_authorization: DeliveryAuthorizationService | None = None,
        delivery_preparer: GitDeliveryPreparer | None = None,
    ) -> None:
        self.store = store
        self.reality = reality
        self.guardian = guardian
        self.workspace_preparer = workspace_preparer
        self.provider = provider
        self.preview_runtime = preview_runtime
        self.work_exists = work_exists
        self.lifecycle = lifecycle or ProductionEnvironmentLifecycle()
        self.delivery_authorization = delivery_authorization or DeliveryAuthorizationService()
        self.delivery_preparer = delivery_preparer or GitDeliveryPreparer()

    def prepare_for_human_review(
        self,
        request: BrownfieldFeatureDeliveryRequest,
    ) -> BrownfieldReviewSessionV1:
        if not self.work_exists(request.work_id):
            raise BrownfieldDeliveryError("Production Environment requires an admitted Work")

        repository_reality = self.reality.discover_repository_payload(
            request.repository_source,
            repository_identity=request.repository_identity,
            requested_branch=request.requested_branch,
        )
        now = datetime.now(UTC)
        workspace = ProductionWorkspaceV1(
            id=uuid4(),
            work_id=request.work_id,
            repository_assets=(
                RepositoryAssetBinding(
                    asset_id=uuid4(),
                    repository_identity=request.repository_identity,
                    source=repository_reality["source"],
                    branch=repository_reality["selected_branch"],
                    default_branch=repository_reality["default_branch"],
                    requested_branch=repository_reality.get("requested_branch"),
                    source_revision=repository_reality["selected_revision"],
                    source_tree_identity=repository_reality["tree_identity"],
                    acquisition_policy=RepositoryAcquisitionPolicyV1.model_validate(
                        repository_reality["acquisition_policy"]
                    ),
                    mount_path=request.repository_mount_path,
                    writable=True,
                    provenance_reference=(
                        f"ecf:repository-reality:{repository_reality['reality_id']}"
                    ),
                ),
            ),
            environment_configuration=EnvironmentConfiguration(
                provider_profile="container-v1",
                dependency_profile_reference="task-contract:dependency-boundary:v1",
                lifecycle_policy_references=(
                    "watt:production-environment:structural-lifecycle:v1",
                ),
            ),
            runtime_configuration=RuntimeConfiguration(
                runtime_profile="brownfield-static-preview-v1",
                preview_enabled=True,
                network_policy_reference="network:none",
                resource_policy_reference="single-host-bounded-v1",
            ),
            created_at=now,
        )
        self.store.create_workspace(workspace)

        environment = ProductionEnvironmentV1(
            id=uuid4(),
            work_id=request.work_id,
            workspace_id=workspace.id,
            lifecycle_state=EnvironmentLifecycleState.CREATED,
            runtime_state=EnvironmentRuntimeState.NOT_PROVISIONED,
            created_at=now,
            updated_at=now,
        )
        self.store.create_environment(environment)
        environment = self._transition(
            environment,
            EnvironmentLifecycleState.INITIALIZING,
            work_state="ADMITTED",
            human_review_pending=False,
            reason="prepare exact-revision Brownfield Workspace",
        )

        prepared = self.workspace_preparer.prepare(workspace)
        repository_path = self._repository_path(prepared, request.repository_identity)
        handle = None
        preview_id = None
        try:
            handle = self.provider.create_workspace_environment(
                EnvironmentProvisionRequest(
                    environment=environment,
                    workspace=workspace,
                    prepared_workspace=prepared,
                    image_reference=request.container_image,
                )
            )
            dependency_results = self.provider.prepare_dependencies(
                handle,
                request.dependency_commands,
            )
            implementation_results = self.provider.execute_commands(
                handle,
                request.implementation_commands,
            )
            self._require_success(implementation_results, "implementation")

            candidate = self.delivery_preparer.prepare_candidate(
                repository_path,
                repository_identity=request.repository_identity,
                base_revision=repository_reality["revision"],
                commit_message=request.commit_message,
                author_name=request.commit_author_name,
                author_email=request.commit_author_email,
            )
            verification_results = self.provider.execute_commands(
                handle,
                request.verification_commands,
            )
            self._require_success(verification_results, "verification")
            if self._git(repository_path, "status", "--porcelain"):
                raise BrownfieldDeliveryError(
                    "verification mutated the reviewed Candidate Workspace"
                )
            outputs = self.provider.collect_outputs(handle, request.artifact_paths)
            artifact_references = tuple(item.artifact_reference for item in outputs)
            evidence_references = tuple(
                f"verification:sha256:{canonical_digest(result)}"
                for result in verification_results
            )
            environment = self._transition(
                environment,
                EnvironmentLifecycleState.ACTIVE,
                work_state="IN_PROGRESS",
                human_review_pending=True,
                reason="Candidate produced and verified for Human review",
                provider_reference=(
                    f"{handle.provider_identity}:{handle.opaque_reference}"
                ),
                artifact_references=artifact_references,
                evidence_references=evidence_references,
            )

            preview_id = uuid4()
            observation = self.preview_runtime.start(
                preview_id,
                repository_path,
                request.preview_entrypoint,
            )
            preview = preview_runtime_from_observation(
                environment,
                preview_id=preview_id,
                preview_reference=f"preview-runtime:{preview_id}",
                artifact_references=artifact_references,
                observation=observation,
                created_at=datetime.now(UTC),
                observed_at=datetime.now(UTC),
            )
            self.store.save_preview(preview)

            delivery_intent = DeliveryIntentV1(
                id=uuid4(),
                work_id=request.work_id,
                environment_id=environment.id,
                repository_identity=request.repository_identity,
                kinds=(
                    DeliveryIntentKind.BRANCH_CREATION,
                    DeliveryIntentKind.COMMIT,
                    DeliveryIntentKind.PULL_REQUEST_PREPARATION,
                ),
                target_branch=request.target_branch,
                commit=candidate.current_commit,
                state=ProductionDeliveryState.READY_FOR_HUMAN_ACCEPTANCE,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self.store.create_delivery_intent(delivery_intent)
            workspace_reality = workspace_reality_v1_payload(
                workspace,
                environment,
                reality_id=uuid4(),
                repository_reality_references={
                    request.repository_identity: (
                        f"ecf:repository-reality:{repository_reality['reality_id']}"
                    )
                },
                observed_at=datetime.now(UTC),
                source_reference=f"review-session:{delivery_intent.id}",
                observed_by="watt:brownfield-delivery:v1",
            )
            self.reality.admit_workspace_payload(workspace_reality)
            self.store.save_resource_references(
                production_resource_references(
                    environment,
                    delivery_reference=f"delivery-intent:{delivery_intent.id}",
                    created_at=datetime.now(UTC),
                )
            )
            session = BrownfieldReviewSessionV1(
                id=uuid4(),
                work_id=request.work_id,
                task_contract_reference=request.task_contract_reference,
                repository_identity=request.repository_identity,
                repository_reality_reference=(
                    f"ecf:repository-reality:{repository_reality['reality_id']}"
                ),
                source_revision=repository_reality["revision"],
                candidate_revision=candidate.current_commit,
                target_branch=request.target_branch,
                workspace=workspace,
                prepared_workspace=prepared,
                environment=environment,
                provider_handle=handle,
                preview=preview,
                delivery_intent=delivery_intent,
                execution_results=(*dependency_results, *implementation_results),
                verification_results=verification_results,
                outputs=outputs,
                created_at=datetime.now(UTC),
            )
            return self.store.save_review_session(session)
        except Exception:
            if preview_id is not None:
                self.preview_runtime.stop(preview_id)
            if handle is not None:
                self.provider.cleanup(handle)
            raise

    def accept_candidate(
        self,
        session_id: UUID,
        decision: HumanDeliveryDecision,
    ) -> DeliveryIntentV1:
        session = self._session(session_id)
        if decision.action is not HumanDeliveryAction.ACCEPT:
            raise BrownfieldDeliveryError("candidate acceptance requires ACCEPT")
        current = self._delivery_intent(session)
        updated = self.delivery_authorization.apply(current, decision)
        return self.store.apply_delivery_decision(current, updated, decision)

    def authorize_delivery(
        self,
        session_id: UUID,
        decision: HumanDeliveryDecision,
    ) -> BrownfieldDeliveryCompletionV1:
        session = self._session(session_id)
        if decision.action is not HumanDeliveryAction.AUTHORIZE_DELIVERY:
            raise BrownfieldDeliveryError(
                "delivery authorization requires AUTHORIZE_DELIVERY"
            )
        current = self._delivery_intent(session)
        authorized = self.delivery_authorization.apply(current, decision)
        authorized = self.store.apply_delivery_decision(current, authorized, decision)

        repository_path = self._repository_path(
            session.prepared_workspace,
            session.repository_identity,
        )
        continuity = self.delivery_preparer.authorize_branch(
            repository_path,
            repository_identity=session.repository_identity,
            base_revision=session.source_revision,
            candidate_revision=session.candidate_revision,
            target_branch=session.target_branch,
        )
        changes = self._changes(session, repository_path)
        verification = tuple(
            VerificationResultReference(
                reference=f"verification:sha256:{canonical_digest(result)}",
                outcome=VerificationOutcome.PASS,
            )
            for result in session.verification_results
        )
        record = ProductionRecordV1(
            id=uuid4(),
            work_reference=f"work:{session.work_id}",
            task_contract_reference=session.task_contract_reference,
            repository_revisions=(
                RepositoryRevisionReference(
                    repository_identity=session.repository_identity,
                    branch=continuity.branch,
                    before_revision=session.source_revision,
                    after_revision=session.candidate_revision,
                    diff_reference=continuity.diff_reference,
                ),
            ),
            environment_reference=f"production-environment:{session.environment.id}",
            changes=changes,
            verification_results=verification,
            delivery_result=DeliveryResultReference(
                reference=f"delivery-intent:{authorized.id}",
                state=authorized.state,
            ),
            created_at=datetime.now(UTC),
        )
        self.store.save_production_record(record)

        refreshed_repository = self.reality.discover_repository_payload(
            repository_path,
            repository_identity=session.repository_identity,
        )
        change = self.reality.admit_change_payload(
            change_reality_v1_payload(
                record,
                reality_id=uuid4(),
                observed_at=datetime.now(UTC),
                source_reference=f"production-record:{record.id}",
                observed_by="watt:brownfield-delivery:v1",
            )
        )
        delivery = self.reality.admit_delivery_payload(
            delivery_reality_v1_payload(
                record,
                reality_id=uuid4(),
                repository_identity=session.repository_identity,
                observed_at=datetime.now(UTC),
                source_reference=f"production-record:{record.id}",
                observed_by="watt:brownfield-delivery:v1",
            )
        )
        guardian_intake = self.guardian.admit_payload(
            guardian_assurance_intake_v1_payload(
                record,
                intake_id=uuid4(),
                submitted_by="watt:brownfield-delivery:v1",
                submitted_at=datetime.now(UTC),
            )
        )

        self.preview_runtime.stop(session.preview.id)
        self.provider.cleanup(session.provider_handle)
        environment = self.store.get_environment(session.environment.id)
        if environment is None:
            raise BrownfieldDeliveryError("Production Environment disappeared")
        environment = self._transition(
            environment,
            EnvironmentLifecycleState.SUSPENDED,
            work_state="DELIVERY_AUTHORIZED",
            human_review_pending=False,
            reason="authorized Candidate recorded and runtime suspended",
        )
        return BrownfieldDeliveryCompletionV1(
            review_session_id=session.id,
            environment=environment,
            delivery_intent=authorized,
            production_record=record,
            refreshed_repository_reality_reference=(
                f"ecf:repository-reality:{refreshed_repository['reality_id']}"
            ),
            change_reality_reference=f"ecf:change-reality:{change['reality_id']}",
            delivery_reality_reference=f"ecf:delivery-reality:{delivery['reality_id']}",
            guardian_intake_reference=(
                f"guardian:assurance-intake:{guardian_intake['intake_id']}"
            ),
            completed_at=datetime.now(UTC),
        )

    def archive_environment(self, session_id: UUID) -> ProductionEnvironmentV1:
        session = self._session(session_id)
        environment = self.store.get_environment(session.environment.id)
        if environment is None:
            raise BrownfieldDeliveryError("Production Environment disappeared")
        return self._transition(
            environment,
            EnvironmentLifecycleState.ARCHIVED,
            work_state="COMPLETED",
            human_review_pending=False,
            reason="retain completed Production Environment history",
        )

    def _transition(
        self,
        environment: ProductionEnvironmentV1,
        target: EnvironmentLifecycleState,
        *,
        work_state: str,
        human_review_pending: bool,
        reason: str,
        provider_reference: str | None = None,
        artifact_references: tuple[str, ...] | None = None,
        evidence_references: tuple[str, ...] | None = None,
    ) -> ProductionEnvironmentV1:
        after, record = self.lifecycle.transition(
            environment,
            target=target,
            context=LifecycleDecisionContext(
                work_state=work_state,
                human_review_pending=human_review_pending,
            ),
            actor_reference="watt:brownfield-delivery:v1",
            reason=reason,
            decided_at=datetime.now(UTC),
            provider_reference=provider_reference,
            artifact_references=artifact_references,
            evidence_references=evidence_references,
        )
        return self.store.apply_transition(environment, after, record)

    def _session(self, session_id: UUID) -> BrownfieldReviewSessionV1:
        session = self.store.get_review_session(session_id)
        if session is None:
            raise BrownfieldDeliveryError("Brownfield review session is unavailable")
        return session

    def _delivery_intent(self, session: BrownfieldReviewSessionV1) -> DeliveryIntentV1:
        intent = self.store.get_delivery_intent(session.delivery_intent.id)
        if intent is None:
            raise BrownfieldDeliveryError("Delivery intent is unavailable")
        return intent

    @staticmethod
    def _repository_path(prepared, repository_identity: str) -> Path:
        mount = next(
            (
                item
                for item in prepared.repository_mounts
                if item.repository_identity == repository_identity
            ),
            None,
        )
        if mount is None:
            raise BrownfieldDeliveryError("prepared repository binding is unavailable")
        return mount.host_path.resolve()

    @staticmethod
    def _require_success(results, phase: str) -> None:
        failed = [result for result in results if result.exit_code != 0]
        if failed:
            raise BrownfieldDeliveryError(f"{phase} failed inside Production Environment")

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
            raise BrownfieldDeliveryError(result.stderr.strip() or "Git inspection failed")
        return result.stdout.strip()

    def _changes(
        self,
        session: BrownfieldReviewSessionV1,
        repository: Path,
    ) -> tuple[ProductionChangeReference, ...]:
        output_references = {
            item.path.removeprefix(session.workspace.repository_assets[0].mount_path)
            .removeprefix("/"): item.artifact_reference
            for item in session.outputs
        }
        status_map = {
            "A": ProductionChangeType.ADDED,
            "M": ProductionChangeType.MODIFIED,
            "D": ProductionChangeType.DELETED,
        }
        changes = []
        raw = self._git(
            repository,
            "diff",
            "--name-status",
            session.source_revision,
            session.candidate_revision,
        )
        for line in raw.splitlines():
            fields = line.split("\t")
            code = fields[0][0]
            path = fields[-1]
            changes.append(
                ProductionChangeReference(
                    repository_identity=session.repository_identity,
                    path=path,
                    change_type=status_map.get(code, ProductionChangeType.MODIFIED),
                    artifact_reference=output_references.get(path),
                )
            )
        if not changes:
            raise BrownfieldDeliveryError("Candidate contains no production changes")
        return tuple(changes)
