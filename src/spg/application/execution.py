"""S2-B Runtime-controlled dispatch and independent observation orchestration."""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.application.preparation import (
    PreparationService,
    completion_contract_fingerprint,
)
from spg.domain.execution import (
    ExecutionDispatchRecord,
    ExecutorDispatchRequest,
    ExecutorDispatchResult,
    GovernedExecutionResult,
    ProviderExecutionReportRecord,
    ProviderReportedOutcome,
    RepositoryObservationRecord,
    WorkProductReferenceRecord,
)
from spg.domain.executor import ExecutorCapabilityContract
from spg.domain.runtime import (
    AttemptCondition,
    RuntimeInvariantViolation,
    RuntimeRecordNotFound,
)
from spg.infrastructure.git_observation import GitWorkspaceObserver
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore


EXECUTION_ACTOR = "spg-runtime:execution"


class ExecutionService:
    """Own dispatch authority and stop at independently observed Work Products."""

    def __init__(
        self,
        database: Database,
        preparation: PreparationService | None = None,
        observer: GitWorkspaceObserver | None = None,
    ) -> None:
        self.database = database
        self.preparation = preparation or PreparationService(database)
        self.observer = observer or GitWorkspaceObserver(self.preparation.workspaces)

    def dispatch_and_observe(
        self,
        attempt_id: UUID,
        executor: ExecutorCapabilityContract,
    ) -> GovernedExecutionResult:
        """Persist authority, execute through the capability, then observe Reality."""

        with self.database.unit_of_work() as unit_of_work:
            existing = RuntimeStore(unit_of_work.session).execution_dispatch_for_attempt(
                attempt_id
            )
            if existing is not None:
                raise RuntimeInvariantViolation(
                    "current Attempt generation already has a dispatch fact"
                )
        request = self.preparation.prepared_execution_request(attempt_id)
        dispatch = self._persist_dispatch(request)
        capability_request = ExecutorDispatchRequest(
            dispatch_id=dispatch.id,
            execution=request,
        )
        try:
            provider_result = executor.dispatch(capability_request)
        except Exception as error:  # provider failure is a durable claim/fact boundary
            timestamp = datetime.now(UTC)
            provider_result = ExecutorDispatchResult(
                provider_reference=f"provider-exception:{dispatch.id}",
                outcome=ProviderReportedOutcome.UNKNOWN,
                started_at=dispatch.dispatched_at,
                finished_at=timestamp,
                metadata={"exception_type": type(error).__name__},
                summary=str(error),
            )
        report = self._persist_provider_report(dispatch, provider_result)
        observation, work_products = self.observe_dispatch(dispatch.id)
        return GovernedExecutionResult(
            dispatch=dispatch,
            provider_report=report,
            observation=observation,
            work_products=work_products,
        )

    def observe_dispatch(
        self,
        dispatch_id: UUID,
    ) -> tuple[RepositoryObservationRecord, tuple[WorkProductReferenceRecord, ...]]:
        """Observe independently; identical re-observation returns one durable fact."""

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            dispatch = store.execution_dispatch(dispatch_id)
            if dispatch is None:
                raise RuntimeRecordNotFound(f"Execution dispatch not found: {dispatch_id}")
            attempt = store.attempt(dispatch.attempt_id)
            snapshot = store.snapshot(dispatch.source_baseline_id)
            if attempt is None or snapshot is None:
                raise RuntimeInvariantViolation("dispatch Attempt/Baseline lineage is incomplete")
            work_unit = store.work_unit(attempt.work_unit_id)
            if work_unit is None:
                raise RuntimeInvariantViolation("dispatch PWU lineage is incomplete")
            run = store.run(work_unit.production_run_id)
            plan = store.plan_revision(attempt.plan_revision_id)
            if run is None or plan is None:
                raise RuntimeInvariantViolation("dispatch Run/Plan lineage is incomplete")

        reality = self.observer.observe(
            dispatch.workspace,
            repository_ref=snapshot.repository_ref,
            expected_authoritative_ref_revision=dispatch.authoritative_ref_revision,
        )
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            existing = store.repository_observation(dispatch.id)
            if existing is not None:
                if existing.observation_fingerprint != reality.observation_fingerprint:
                    raise RuntimeInvariantViolation(
                        "Attempt workspace changed after its authoritative observation"
                    )
                return existing, store.work_product_references(existing.id)

            timestamp = reality.observed_at
            observation_id = uuid4()
            store.insert_repository_observation(
                {
                    "id": observation_id,
                    "dispatch_id": dispatch.id,
                    "attempt_id": dispatch.attempt_id,
                    "generation": dispatch.generation,
                    "source_baseline_id": dispatch.source_baseline_id,
                    "repository_identity": reality.repository_identity,
                    "source_revision": reality.source_revision,
                    "workspace_identity": reality.workspace_identity,
                    "workspace_path": reality.workspace_path,
                    "authoritative_ref_revision": reality.authoritative_ref_revision,
                    "change_manifest": [
                        item.model_dump(mode="json") for item in reality.changes
                    ],
                    "observation_fingerprint": reality.observation_fingerprint,
                    "observed_at": timestamp,
                }
            )
            for change in reality.changes:
                store.insert_work_product_reference(
                    {
                        "id": uuid5(
                            NAMESPACE_URL,
                            f"spg:{observation_id}:{change.repository_relative_path}",
                        ),
                        "production_run_id": run.id,
                        "work_unit_id": work_unit.id,
                        "plan_revision_id": attempt.plan_revision_id,
                        "attempt_id": dispatch.attempt_id,
                        "generation": dispatch.generation,
                        "source_baseline_id": dispatch.source_baseline_id,
                        "repository_observation_id": observation_id,
                        "artifact_path": change.repository_relative_path,
                        "change_type": change.change_type.value,
                        "source_fingerprint": change.source_fingerprint,
                        "observed_fingerprint": change.observed_fingerprint,
                        "created_at": timestamp,
                    }
                )
            self._append_history(
                store,
                entity_type="REPOSITORY_OBSERVATION",
                entity_id=observation_id,
                to_condition="OBSERVED",
                reason="ATTEMPT_WORKSPACE_OBSERVED",
                correlation=dispatch.attempt_id,
                timestamp=timestamp,
            )
            observation = store.repository_observation(dispatch.id)
            if observation is None:
                raise RuntimeInvariantViolation("Repository Observation was not constructed")
            work_products = store.work_product_references(observation.id)
            unit_of_work.commit()
            return observation, work_products

    def complete_existing_dispatch(
        self,
        dispatch_id: UUID,
        provider_result: ExecutorDispatchResult,
    ) -> GovernedExecutionResult:
        """Complete a previously durable native dispatch after process recovery."""

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            dispatch = store.execution_dispatch(dispatch_id)
            if dispatch is None:
                raise RuntimeRecordNotFound(f"Execution dispatch not found: {dispatch_id}")
            existing = store.provider_execution_report(dispatch_id)
        report = existing or self._persist_provider_report(dispatch, provider_result)
        observation, work_products = self.observe_dispatch(dispatch_id)
        return GovernedExecutionResult(
            dispatch=dispatch,
            provider_report=report,
            observation=observation,
            work_products=work_products,
        )

    def _persist_dispatch(self, request) -> ExecutionDispatchRecord:
        dispatch_id = uuid4()
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            if store.execution_dispatch_for_attempt(request.attempt_id) is not None:
                raise RuntimeInvariantViolation(
                    "current Attempt generation already has a dispatch fact"
                )
            snapshot = self._require_current_dispatch_binding(store, request)
            self.preparation.workspaces.validate(request.workspace)
            authoritative_ref_revision = self.observer.current_ref_revision(
                request.workspace.repository_path,
                snapshot.repository_ref,
            )
            store.insert_execution_dispatch(
                {
                    "id": dispatch_id,
                    "attempt_id": request.attempt_id,
                    "generation": request.generation,
                    "context_package_id": request.context_package_id,
                    "source_baseline_id": request.source_baseline_id,
                    "executor_binding": request.executor_binding.model_dump(mode="json"),
                    "workspace_identity": request.workspace.workspace_identity,
                    "workspace_path": str(request.workspace.workspace_path),
                    "repository_identity": request.workspace.repository_identity,
                    "repository_path": str(request.workspace.repository_path),
                    "source_revision": request.workspace.source_revision,
                    "authoritative_ref_revision": authoritative_ref_revision,
                    "dispatched_at": timestamp,
                }
            )
            self._append_history(
                store,
                entity_type="EXECUTION_DISPATCH",
                entity_id=dispatch_id,
                to_condition="RECORDED",
                reason="EXECUTOR_DISPATCH_RECORDED",
                correlation=request.attempt_id,
                timestamp=timestamp,
            )
            dispatch = store.execution_dispatch(dispatch_id)
            if dispatch is None:
                raise RuntimeInvariantViolation("Execution dispatch was not constructed")
            unit_of_work.commit()
            return dispatch

    def _persist_provider_report(
        self,
        dispatch: ExecutionDispatchRecord,
        provider_result: ExecutorDispatchResult,
    ) -> ProviderExecutionReportRecord:
        timestamp = datetime.now(UTC)
        report_id = uuid4()
        metadata = {
            **provider_result.metadata,
            "terminal_executor_outcome": provider_result.return_control.value,
        }
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            if store.provider_execution_report(dispatch.id) is not None:
                raise RuntimeInvariantViolation("dispatch already has a Provider Report")
            store.insert_provider_execution_report(
                {
                    "id": report_id,
                    "dispatch_id": dispatch.id,
                    "attempt_id": dispatch.attempt_id,
                    "generation": dispatch.generation,
                    "executor_binding": dispatch.executor_binding.model_dump(mode="json"),
                    "provider_reference": provider_result.provider_reference,
                    "outcome": provider_result.outcome.value,
                    "started_at": provider_result.started_at,
                    "finished_at": provider_result.finished_at,
                    "metadata": metadata,
                    "summary": provider_result.summary,
                    "recorded_at": timestamp,
                }
            )
            self._append_history(
                store,
                entity_type="PROVIDER_EXECUTION_REPORT",
                entity_id=report_id,
                to_condition="REPORTED",
                reason="PROVIDER_REPORT_RECORDED",
                correlation=dispatch.attempt_id,
                timestamp=timestamp,
            )
            report = store.provider_execution_report(dispatch.id)
            if report is None:
                raise RuntimeInvariantViolation("Provider Report was not constructed")
            unit_of_work.commit()
            return report

    @staticmethod
    def _require_current_dispatch_binding(store: RuntimeStore, request):
        attempt = store.attempt(request.attempt_id)
        if attempt is None:
            raise RuntimeRecordNotFound(f"Attempt not found: {request.attempt_id}")
        work_unit = store.work_unit(attempt.work_unit_id, for_update=True)
        if work_unit is None:
            raise RuntimeInvariantViolation("Attempt refers to a missing PWU")
        run = store.run(work_unit.production_run_id)
        plan = store.plan_revision(work_unit.plan_revision_id)
        snapshot = store.snapshot(work_unit.source_baseline_id)
        preparation = store.attempt_preparation(attempt.id)
        package = store.context_package(request.context_package_id)
        if any(item is None for item in (run, plan, snapshot, preparation, package)):
            raise RuntimeInvariantViolation("execution preparation lineage is incomplete")
        if (
            attempt.condition is not AttemptCondition.CREATED
            or attempt.generation != work_unit.current_execution_generation
            or attempt.generation != request.generation
            or attempt.plan_revision_id != work_unit.plan_revision_id
            or attempt.source_baseline_id != work_unit.source_baseline_id
            or run.current_plan_revision_id != plan.id
            or run.source_baseline_id != snapshot.id
            or plan.production_run_id != run.id
            or plan.source_baseline_id != snapshot.id
            or request.production_run_id != run.id
            or request.work_unit_id != work_unit.id
            or request.plan_revision_id != plan.id
            or request.source_baseline_id != snapshot.id
            or request.context_package_id != package.id
            or request.context_package_version != package.version
            or request.completion_contract_fingerprint
            != completion_contract_fingerprint(work_unit.completion_contract)
            or package.completion_contract_fingerprint
            != request.completion_contract_fingerprint
            or preparation.context_package_id != package.id
            or preparation.executor_binding != request.executor_binding
            or preparation.workspace != request.workspace
            or request.workspace.repository_identity != snapshot.repository_identity
            or request.workspace.source_revision != snapshot.repository_revision
        ):
            raise RuntimeInvariantViolation(
                "Attempt preparation is no longer an exact current execution binding"
            )
        return snapshot

    @staticmethod
    def _append_history(
        store: RuntimeStore,
        *,
        entity_type: str,
        entity_id: UUID,
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
                "from_condition": None,
                "to_condition": to_condition,
                "reason": reason,
                "actor_identity": EXECUTION_ACTOR,
                "correlation_identity": str(correlation),
                "created_at": timestamp,
            }
        )
