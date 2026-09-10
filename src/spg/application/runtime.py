"""Governed application operations for the S1-C durable Runtime spine."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from spg.domain.runtime import (
    AttemptCondition,
    AttemptRequest,
    BootstrapAlreadyInitialized,
    BootstrapRequest,
    BootstrapResult,
    InitialRunRequest,
    InitialRuntimeSpine,
    PlanCondition,
    RunCondition,
    RuntimeInvariantViolation,
    RuntimeNotBootstrapped,
    RuntimeRecordNotFound,
    SnapshotCondition,
    SnapshotRecord,
    ExecutionAttemptRecord,
    WorkUnitCondition,
)
from spg.infrastructure.git_repository import GitRepositoryObserver
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore


RUNTIME_ACTOR = "spg-runtime"


class RuntimeService:
    """Sole S1-C owner of authoritative Runtime lifecycle transitions."""

    def __init__(
        self,
        database: Database,
        repository_observer: GitRepositoryObserver | None = None,
    ) -> None:
        self.database = database
        self.repository_observer = repository_observer or GitRepositoryObserver()

    def bootstrap_trusted_baseline(self, request: BootstrapRequest) -> BootstrapResult:
        """Explicitly observe and admit one initial trusted repository reality."""

        with self.database.unit_of_work() as unit_of_work:
            if RuntimeStore(unit_of_work.session).current_pointer(repository_identity=request.repository_identity, repository_ref=request.repository_ref) is not None:
                raise BootstrapAlreadyInitialized(
                    "a Current Trusted Baseline already exists"
                )

        reality = self.repository_observer.observe(
            request.repository_path,
            request.repository_identity,
            request.repository_ref,
        )
        timestamp = datetime.now(UTC)
        snapshot_id = uuid4()
        governance_id = uuid4()

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            if store.current_pointer(repository_identity=request.repository_identity, repository_ref=request.repository_ref) is not None:
                raise BootstrapAlreadyInitialized(
                    "a Current Trusted Baseline already exists"
                )

            store.insert_snapshot(
                {
                    "id": snapshot_id,
                    "condition": SnapshotCondition.TRUSTED.value,
                    "repository_identity": reality.repository_identity,
                    "repository_ref": reality.repository_ref,
                    "repository_revision": reality.exact_revision,
                    "source_baseline_id": None,
                    "created_at": timestamp,
                }
            )
            store.insert_governance(
                {
                    "id": governance_id,
                    "decision_type": "BOOTSTRAP_INITIAL_BASELINE",
                    "authority_identity": request.authority_identity,
                    "subject_type": "PRODUCTION_SNAPSHOT",
                    "subject_identity": str(snapshot_id),
                    "scope": {
                        **request.scope,
                        "repository_identity": reality.repository_identity,
                        "repository_ref": reality.repository_ref,
                        "repository_revision": reality.exact_revision,
                    },
                    "rationale": request.rationale,
                    "created_at": timestamp,
                }
            )
            store.insert_baseline_pointer(
                {
                    "singleton_id": 1,
                    "snapshot_id": snapshot_id,
                    "version": 0,
                    "updated_at": timestamp,
                }
            )
            self._append_transition(
                store,
                entity_type="PRODUCTION_SNAPSHOT",
                entity_id=snapshot_id,
                from_condition=None,
                to_condition=SnapshotCondition.TRUSTED.value,
                reason="BOOTSTRAP_TRUSTED_BASELINE",
                actor=request.authority_identity,
                correlation=snapshot_id,
                timestamp=timestamp,
            )

            snapshot = self._required_snapshot(store, snapshot_id)
            pointer = store.current_pointer(repository_identity=request.repository_identity, repository_ref=request.repository_ref)
            governance = store.governance_for_subject(str(snapshot_id))
            if pointer is None or len(governance) != 1:
                raise RuntimeInvariantViolation("bootstrap records were not constructed")
            result = BootstrapResult(
                snapshot=snapshot,
                pointer=pointer,
                governance=governance[0],
            )
            unit_of_work.commit()
            return result

    def current_baseline(self, *, repository_identity: str | None = None, repository_ref: str | None = None, source_baseline_id: UUID | None = None) -> SnapshotRecord:
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            pointer = store.current_pointer(repository_identity=repository_identity, repository_ref=repository_ref, source_baseline_id=source_baseline_id)
            if pointer is None:
                raise RuntimeNotBootstrapped("no Current Trusted Baseline exists")
            return self._required_snapshot(store, pointer.snapshot_id)

    def create_initial_runtime_spine(
        self,
        request: InitialRunRequest,
    ) -> InitialRuntimeSpine:
        """Atomically construct Run -> active Plan R1 -> proposed generic PWU."""

        timestamp = datetime.now(UTC)
        run_id, plan_id, work_unit_id = uuid4(), uuid4(), uuid4()
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            contract = request.completion_contract
            exact_source = request.source_baseline_id
            for boundary in (contract.artifact_contract, contract.change_contract, contract.production_plan):
                if boundary is not None:
                    if exact_source is not None and exact_source != boundary.source_baseline_id:
                        raise RuntimeInvariantViolation("Run contracts disagree on Source Baseline")
                    exact_source = boundary.source_baseline_id
            pointer = store.current_pointer(source_baseline_id=exact_source, for_update=True)
            if pointer is not None and exact_source is not None and pointer.snapshot_id != exact_source:
                raise RuntimeInvariantViolation("Run Source Baseline is stale")
            if pointer is None:
                raise RuntimeNotBootstrapped("bootstrap is required before Run creation")
            baseline = self._required_snapshot(store, pointer.snapshot_id)
            if baseline.condition is not SnapshotCondition.TRUSTED:
                raise RuntimeInvariantViolation("Current Baseline must be TRUSTED")

            store.insert_run(
                {
                    "id": run_id,
                    "intent_ref": request.intent_ref,
                    "goal": request.goal,
                    "production_horizon": request.production_horizon.value,
                    "source_baseline_id": baseline.id,
                    "current_plan_revision_id": None,
                    "condition": RunCondition.OPEN.value,
                    "version": 0,
                    "created_at": timestamp,
                }
            )
            store.insert_plan_revision(
                {
                    "id": plan_id,
                    "production_run_id": run_id,
                    "revision_number": 1,
                    "source_baseline_id": baseline.id,
                    "condition": PlanCondition.ACTIVE.value,
                    "version": 0,
                    "created_at": timestamp,
                }
            )
            store.bind_run_to_plan(run_id, expected_version=0, plan_id=plan_id)
            store.insert_work_unit(
                {
                    "id": work_unit_id,
                    "production_run_id": run_id,
                    "plan_revision_id": plan_id,
                    "source_baseline_id": baseline.id,
                    "objective": request.initial_work_unit_objective,
                    "completion_contract": request.completion_contract.model_dump(
                        mode="json"
                    ),
                    "condition": WorkUnitCondition.PROPOSED.value,
                    "version": 0,
                    "current_execution_generation": 0,
                    "created_at": timestamp,
                }
            )
            for entity_type, entity_id, condition, reason in (
                ("PRODUCTION_RUN", run_id, RunCondition.OPEN.value, "RUN_CREATED"),
                (
                    "PLAN_REVISION",
                    plan_id,
                    PlanCondition.ACTIVE.value,
                    "INITIAL_PLAN_ACTIVATED",
                ),
                (
                    "PRODUCTION_WORK_UNIT",
                    work_unit_id,
                    WorkUnitCondition.PROPOSED.value,
                    "WORK_UNIT_PROPOSED",
                ),
            ):
                self._append_transition(
                    store,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    from_condition=None,
                    to_condition=condition,
                    reason=reason,
                    actor=RUNTIME_ACTOR,
                    correlation=run_id,
                    timestamp=datetime.now(UTC),
                )

            result = self._required_spine(store, run_id)
            unit_of_work.commit()
            return result

    def inspect_run(self, run_id: UUID) -> InitialRuntimeSpine:
        with self.database.unit_of_work() as unit_of_work:
            return self._required_spine(RuntimeStore(unit_of_work.session), run_id)

    def create_initial_attempt(
        self,
        work_unit_id: UUID,
        request: AttemptRequest | None = None,
    ) -> ExecutionAttemptRecord:
        """Create Attempt generation 1 without dispatching an Executor."""

        return self._create_attempt(
            work_unit_id=work_unit_id,
            retry_of=None,
            request=request or AttemptRequest(),
        )

    def retry_attempt(
        self,
        attempt_id: UUID,
        request: AttemptRequest | None = None,
    ) -> ExecutionAttemptRecord:
        """Create a new Attempt identity and generation; never rewrite history."""

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            previous = store.attempt(attempt_id)
            if previous is None:
                raise RuntimeRecordNotFound(f"Attempt not found: {attempt_id}")
            work_unit = store.work_unit(previous.work_unit_id)
            if work_unit is None:
                raise RuntimeInvariantViolation("Attempt refers to a missing PWU")
            if previous.generation != work_unit.current_execution_generation:
                raise RuntimeInvariantViolation("only the current Attempt may be retried")
            supplied = request or AttemptRequest(
                context_ref=previous.context_ref,
                provider_ref=previous.provider_ref,
                workspace_ref=previous.workspace_ref,
            )
            return self._insert_attempt(
                unit_of_work,
                store,
                work_unit,
                supplied,
                retry_of=previous.id,
                reason="ATTEMPT_RETRY_CREATED",
            )

    def attempt_is_current(self, attempt_id: UUID) -> bool:
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            attempt = store.attempt(attempt_id)
            if attempt is None:
                raise RuntimeRecordNotFound(f"Attempt not found: {attempt_id}")
            work_unit = store.work_unit(attempt.work_unit_id)
            if work_unit is None:
                raise RuntimeInvariantViolation("Attempt refers to a missing PWU")
            return attempt.generation == work_unit.current_execution_generation

    def get_attempt(self, attempt_id: UUID) -> ExecutionAttemptRecord:
        with self.database.unit_of_work() as unit_of_work:
            attempt = RuntimeStore(unit_of_work.session).attempt(attempt_id)
            if attempt is None:
                raise RuntimeRecordNotFound(f"Attempt not found: {attempt_id}")
            return attempt

    def _create_attempt(
        self,
        *,
        work_unit_id: UUID,
        retry_of: UUID | None,
        request: AttemptRequest,
    ) -> ExecutionAttemptRecord:
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            work_unit = store.work_unit(work_unit_id)
            if work_unit is None:
                raise RuntimeRecordNotFound(f"PWU not found: {work_unit_id}")
            if work_unit.current_execution_generation != 0 or retry_of is not None:
                raise RuntimeInvariantViolation("initial Attempt already exists")
            return self._insert_attempt(
                unit_of_work,
                store,
                work_unit,
                request,
                retry_of=None,
                reason="INITIAL_ATTEMPT_CREATED",
            )

    def _insert_attempt(
        self,
        unit_of_work,
        store: RuntimeStore,
        work_unit,
        request: AttemptRequest,
        *,
        retry_of: UUID | None,
        reason: str,
        commit: bool = True,
    ) -> ExecutionAttemptRecord:
        run = store.run(work_unit.production_run_id)
        plan = store.plan_revision(work_unit.plan_revision_id)
        if run is None or plan is None:
            raise RuntimeInvariantViolation("PWU Run/Plan binding is incomplete")
        if (
            run.current_plan_revision_id != work_unit.plan_revision_id
            or plan.production_run_id != work_unit.production_run_id
            or plan.source_baseline_id != work_unit.source_baseline_id
            or run.source_baseline_id != work_unit.source_baseline_id
        ):
            raise RuntimeInvariantViolation("PWU Run/Plan/Baseline bindings do not match")

        timestamp = datetime.now(UTC)
        attempt_id = uuid4()
        generation = work_unit.current_execution_generation + 1
        store.advance_work_unit_generation(
            work_unit.id,
            expected_version=work_unit.version,
            generation=generation,
        )
        store.insert_attempt(
            {
                "id": attempt_id,
                "work_unit_id": work_unit.id,
                "generation": generation,
                "plan_revision_id": work_unit.plan_revision_id,
                "source_baseline_id": work_unit.source_baseline_id,
                "context_ref": request.context_ref,
                "provider_ref": request.provider_ref,
                "workspace_ref": request.workspace_ref,
                "condition": AttemptCondition.CREATED.value,
                "retry_of": retry_of,
                "created_at": timestamp,
            }
        )
        self._append_transition(
            store,
            entity_type="EXECUTION_ATTEMPT",
            entity_id=attempt_id,
            from_condition=None,
            to_condition=AttemptCondition.CREATED.value,
            reason=reason,
            actor=RUNTIME_ACTOR,
            correlation=work_unit.id,
            timestamp=timestamp,
        )
        attempt = store.attempt(attempt_id)
        if attempt is None:
            raise RuntimeInvariantViolation("Attempt was not constructed")
        if commit:
            unit_of_work.commit()
        return attempt

    @staticmethod
    def _required_snapshot(store: RuntimeStore, snapshot_id: UUID) -> SnapshotRecord:
        snapshot = store.snapshot(snapshot_id)
        if snapshot is None:
            raise RuntimeInvariantViolation("Baseline pointer refers to a missing Snapshot")
        return snapshot

    @staticmethod
    def _required_spine(store: RuntimeStore, run_id: UUID) -> InitialRuntimeSpine:
        run = store.run(run_id)
        if run is None:
            raise RuntimeRecordNotFound(f"Run not found: {run_id}")
        plan = store.plan_revision(run.current_plan_revision_id)
        work_unit = store.work_unit_for_run(run.id)
        if plan is None or work_unit is None:
            raise RuntimeInvariantViolation("Run spine is incomplete")
        if (
            plan.production_run_id != run.id
            or work_unit.production_run_id != run.id
            or work_unit.plan_revision_id != plan.id
            or plan.source_baseline_id != run.source_baseline_id
            or work_unit.source_baseline_id != run.source_baseline_id
        ):
            raise RuntimeInvariantViolation("Run spine bindings do not match")
        return InitialRuntimeSpine(run=run, plan_revision=plan, work_unit=work_unit)

    @staticmethod
    def _append_transition(
        store: RuntimeStore,
        *,
        entity_type: str,
        entity_id: UUID,
        from_condition: str | None,
        to_condition: str,
        reason: str,
        actor: str,
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
                "actor_identity": actor,
                "correlation_identity": str(correlation),
                "created_at": timestamp,
            }
        )
