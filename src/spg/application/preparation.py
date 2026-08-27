"""S2-A governed Context Package assembly and Attempt preparation services."""

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from uuid import UUID, uuid4

from spg.domain.preparation import (
    AttemptPreparationRecord,
    AttemptPreparationResult,
    ContextArtifactManifestEntry,
    ContextPackageManifest,
    ContextPackageRecord,
    ContextPackageRequest,
    ExecutorBinding,
    PreparedExecutionRequest,
    WorkspaceBinding,
)
from spg.domain.runtime import (
    AttemptCondition,
    CompletionContract,
    RuntimeDomainError,
    RuntimeInvariantViolation,
    RuntimeRecordNotFound,
)
from spg.infrastructure.git_workspace import GitAttemptWorkspace, GitExactReality
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore


PREPARATION_ACTOR = "spg-runtime:preparation"


def completion_contract_fingerprint(contract: CompletionContract) -> str:
    """Return a stable identity for the exact typed Completion Contract."""

    return _fingerprint(contract.model_dump(mode="json"))


class PreparationService:
    """Own S2-A preparation decisions and stop before Executor dispatch."""

    def __init__(
        self,
        database: Database,
        exact_reality: GitExactReality | None = None,
        workspaces: GitAttemptWorkspace | None = None,
    ) -> None:
        self.database = database
        self.exact_reality = exact_reality or GitExactReality()
        self.workspaces = workspaces or GitAttemptWorkspace()

    def assemble_context_package(
        self,
        work_unit_id: UUID,
        repository_path: Path,
        request: ContextPackageRequest,
    ) -> ContextPackageRecord:
        """Assemble immutable manifest references from the PWU Source Baseline."""

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            work_unit, run, plan, snapshot = self._required_work_unit_lineage(
                store,
                work_unit_id,
            )
            contract_fingerprint = completion_contract_fingerprint(
                work_unit.completion_contract
            )

        entries: list[ContextArtifactManifestEntry] = []
        selections = sorted(
            request.artifacts,
            key=lambda item: (item.semantic_role.value, item.repository_relative_path),
        )
        if len({item.repository_relative_path for item in selections}) != len(selections):
            raise RuntimeInvariantViolation(
                "Context Package cannot select the same repository path twice"
            )
        for selection in selections:
            _, blob_identity = self.exact_reality.read_blob(
                repository_path,
                snapshot.repository_revision,
                selection.repository_relative_path,
            )
            entries.append(
                ContextArtifactManifestEntry(
                    semantic_role=selection.semantic_role,
                    repository_relative_path=selection.repository_relative_path,
                    source_revision=snapshot.repository_revision,
                    blob_fingerprint=blob_identity,
                )
            )

        manifest = ContextPackageManifest(artifacts=tuple(entries))
        package_fingerprint = _fingerprint(
            {
                "production_run_id": str(run.id),
                "work_unit_id": str(work_unit.id),
                "plan_revision_id": str(plan.id),
                "source_baseline_id": str(snapshot.id),
                "repository_identity": snapshot.repository_identity,
                "repository_revision": snapshot.repository_revision,
                "manifest": manifest.model_dump(mode="json"),
                "completion_contract_fingerprint": contract_fingerprint,
            }
        )

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            current_work_unit, current_run, current_plan, current_snapshot = (
                self._required_work_unit_lineage(store, work_unit_id)
            )
            if (
                current_run.id != run.id
                or current_plan.id != plan.id
                or current_snapshot.id != snapshot.id
                or completion_contract_fingerprint(
                    current_work_unit.completion_contract
                )
                != contract_fingerprint
            ):
                raise RuntimeInvariantViolation(
                    "PWU lineage changed during Context Package assembly"
                )

            latest = store.latest_context_package(work_unit_id)
            if latest is not None and latest.content_fingerprint == package_fingerprint:
                return latest

            package_id = uuid4()
            version = 1 if latest is None else latest.version + 1
            timestamp = datetime.now(UTC)
            store.insert_context_package(
                {
                    "id": package_id,
                    "version": version,
                    "production_run_id": run.id,
                    "work_unit_id": work_unit.id,
                    "plan_revision_id": plan.id,
                    "source_baseline_id": snapshot.id,
                    "manifest": manifest.model_dump(mode="json"),
                    "content_fingerprint": package_fingerprint,
                    "completion_contract_fingerprint": contract_fingerprint,
                    "created_at": timestamp,
                }
            )
            self._append_transition(
                store,
                entity_type="CONTEXT_PACKAGE",
                entity_id=package_id,
                from_condition=None,
                to_condition="CREATED",
                reason="CONTEXT_PACKAGE_ASSEMBLED",
                correlation=work_unit.id,
                timestamp=timestamp,
            )
            package = store.context_package(package_id)
            if package is None:
                raise RuntimeInvariantViolation("Context Package was not constructed")
            unit_of_work.commit()
            return package

    def prepare_attempt(
        self,
        attempt_id: UUID,
        context_package_id: UUID,
        executor_binding: ExecutorBinding,
        repository_path: Path,
        workspace_root: Path,
    ) -> AttemptPreparationResult:
        """Create/reconcile exact preparation facts without dispatching an Executor."""

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            facts = self._required_preparation_lineage(
                store,
                attempt_id,
                context_package_id,
            )
            existing = store.attempt_preparation(attempt_id)

        attempt, work_unit, run, _, snapshot, package = facts
        if existing is not None:
            self._require_matching_preparation(
                existing,
                package,
                executor_binding,
                repository_path,
                snapshot.repository_revision,
            )
            self.workspaces.validate(existing.workspace)
            return self._result(existing, package, attempt, work_unit, run)

        workspace = self.workspaces.prepare(
            repository_path=repository_path,
            workspace_root=workspace_root,
            attempt_id=attempt.id,
            repository_identity=snapshot.repository_identity,
            source_revision=snapshot.repository_revision,
        )

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            attempt, work_unit, run, _, snapshot, package = (
                self._required_preparation_lineage(
                    store,
                    attempt_id,
                    context_package_id,
                )
            )
            existing = store.attempt_preparation(attempt_id)
            if existing is not None:
                self._require_matching_preparation(
                    existing,
                    package,
                    executor_binding,
                    repository_path,
                    snapshot.repository_revision,
                )
                self.workspaces.validate(existing.workspace)
                return self._result(existing, package, attempt, work_unit, run)

            timestamp = datetime.now(UTC)
            store.insert_attempt_preparation(
                {
                    "attempt_id": attempt.id,
                    "context_package_id": package.id,
                    "executor_binding": executor_binding.model_dump(mode="json"),
                    "workspace_identity": workspace.workspace_identity,
                    "workspace_path": str(workspace.workspace_path),
                    "repository_identity": workspace.repository_identity,
                    "repository_path": str(workspace.repository_path),
                    "source_revision": workspace.source_revision,
                    "prepared_at": timestamp,
                }
            )
            self._append_transition(
                store,
                entity_type="EXECUTION_ATTEMPT",
                entity_id=attempt.id,
                from_condition=AttemptCondition.CREATED.value,
                to_condition=AttemptCondition.CREATED.value,
                reason="ATTEMPT_PREPARATION_BOUND",
                correlation=work_unit.id,
                timestamp=timestamp,
            )
            preparation = store.attempt_preparation(attempt.id)
            if preparation is None:
                raise RuntimeInvariantViolation("Attempt preparation was not constructed")
            result = self._result(preparation, package, attempt, work_unit, run)
            unit_of_work.commit()
            return result

    def prepared_execution_request(self, attempt_id: UUID) -> PreparedExecutionRequest:
        """Revalidate and return exact S2-B input without performing dispatch."""

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            preparation = store.attempt_preparation(attempt_id)
            if preparation is None:
                raise RuntimeRecordNotFound(
                    f"Attempt preparation not found: {attempt_id}"
                )
            attempt, work_unit, run, _, _, package = (
                self._required_preparation_lineage(
                    store,
                    attempt_id,
                    preparation.context_package_id,
                )
            )
        self.workspaces.validate(preparation.workspace)
        return self._execution_request(
            preparation,
            package,
            attempt,
            work_unit,
            run,
        )

    def is_execution_ready(self, attempt_id: UUID) -> bool:
        try:
            self.prepared_execution_request(attempt_id)
        except RuntimeDomainError:
            return False
        return True

    def context_package(self, package_id: UUID) -> ContextPackageRecord:
        with self.database.unit_of_work() as unit_of_work:
            package = RuntimeStore(unit_of_work.session).context_package(package_id)
            if package is None:
                raise RuntimeRecordNotFound(f"Context Package not found: {package_id}")
            return package

    @staticmethod
    def _required_work_unit_lineage(store: RuntimeStore, work_unit_id: UUID):
        work_unit = store.work_unit(work_unit_id)
        if work_unit is None:
            raise RuntimeRecordNotFound(f"PWU not found: {work_unit_id}")
        run = store.run(work_unit.production_run_id)
        plan = store.plan_revision(work_unit.plan_revision_id)
        snapshot = store.snapshot(work_unit.source_baseline_id)
        if run is None or plan is None or snapshot is None:
            raise RuntimeInvariantViolation("PWU Run/Plan/Baseline lineage is incomplete")
        if (
            run.current_plan_revision_id != plan.id
            or plan.production_run_id != run.id
            or plan.source_baseline_id != snapshot.id
            or run.source_baseline_id != snapshot.id
        ):
            raise RuntimeInvariantViolation("PWU Run/Plan/Baseline lineage is stale")
        return work_unit, run, plan, snapshot

    @classmethod
    def _required_preparation_lineage(
        cls,
        store: RuntimeStore,
        attempt_id: UUID,
        context_package_id: UUID,
    ):
        attempt = store.attempt(attempt_id)
        if attempt is None:
            raise RuntimeRecordNotFound(f"Attempt not found: {attempt_id}")
        work_unit, run, plan, snapshot = cls._required_work_unit_lineage(
            store,
            attempt.work_unit_id,
        )
        if attempt.generation != work_unit.current_execution_generation:
            raise RuntimeInvariantViolation("only the current Attempt may be prepared")
        if (
            attempt.plan_revision_id != plan.id
            or attempt.source_baseline_id != snapshot.id
            or attempt.condition is not AttemptCondition.CREATED
        ):
            raise RuntimeInvariantViolation(
                "Attempt Plan/Baseline/condition binding is not current"
            )
        package = store.context_package(context_package_id)
        if package is None:
            raise RuntimeRecordNotFound(
                f"Context Package not found: {context_package_id}"
            )
        if (
            package.production_run_id != run.id
            or package.work_unit_id != work_unit.id
            or package.plan_revision_id != plan.id
            or package.source_baseline_id != snapshot.id
            or package.completion_contract_fingerprint
            != completion_contract_fingerprint(work_unit.completion_contract)
        ):
            raise RuntimeInvariantViolation(
                "Context Package does not match exact PWU/Plan/Baseline/Completion Contract"
            )
        return attempt, work_unit, run, plan, snapshot, package

    @staticmethod
    def _require_matching_preparation(
        preparation: AttemptPreparationRecord,
        package: ContextPackageRecord,
        executor_binding: ExecutorBinding,
        repository_path: Path,
        source_revision: str,
    ) -> None:
        if (
            preparation.context_package_id != package.id
            or preparation.executor_binding != executor_binding
            or preparation.workspace.repository_path != repository_path.resolve()
            or preparation.workspace.source_revision != source_revision
        ):
            raise RuntimeInvariantViolation(
                "existing Attempt preparation does not match requested exact bindings"
            )

    @classmethod
    def _result(cls, preparation, package, attempt, work_unit, run):
        return AttemptPreparationResult(
            context_package=package,
            preparation=preparation,
            execution_request=cls._execution_request(
                preparation,
                package,
                attempt,
                work_unit,
                run,
            ),
        )

    @staticmethod
    def _execution_request(preparation, package, attempt, work_unit, run):
        return PreparedExecutionRequest(
            attempt_id=attempt.id,
            generation=attempt.generation,
            production_run_id=run.id,
            work_unit_id=work_unit.id,
            plan_revision_id=attempt.plan_revision_id,
            source_baseline_id=attempt.source_baseline_id,
            context_package_id=package.id,
            context_package_version=package.version,
            completion_contract_fingerprint=package.completion_contract_fingerprint,
            executor_binding=preparation.executor_binding,
            workspace=preparation.workspace,
        )

    @staticmethod
    def _append_transition(
        store: RuntimeStore,
        *,
        entity_type: str,
        entity_id: UUID,
        from_condition: str | None,
        to_condition: str,
        reason: str,
        correlation: UUID,
        timestamp: datetime,
    ) -> None:
        store.insert_transition(
            {
                "id": uuid4(),
                "entity_type": entity_type,
                "entity_identity": str(entity_id),
                "from_condition": from_condition,
                "to_condition": to_condition,
                "reason": reason,
                "actor_identity": PREPARATION_ACTOR,
                "correlation_identity": str(correlation),
                "created_at": timestamp,
            }
        )


def _fingerprint(value: object) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return sha256(canonical).hexdigest()
