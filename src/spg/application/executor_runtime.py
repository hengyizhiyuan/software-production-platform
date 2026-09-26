"""Capacity scheduling and lifecycle coordination for Watt-native execution."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets
from uuid import UUID, uuid4

from spg.domain.native_execution import (
    AllocationCondition,
    AttemptGrantState,
    AttemptTerminalOutcome,
    BackendControlCommand,
    BackendControlReceipt,
    BackendObservation,
    CheckpointCondition,
    ControlAction,
    ControlRequestCondition,
    EffectCondition,
    ExecutionAllocationGrant,
    ExecutionAllocationRecord,
    ExecutionEventRecord,
    ExecutionMode,
    ExecutionControlRequestRecord,
    ExecutionHandle,
    ExecutionRecoveryCaseRecord,
    KernelRunResult,
    ExecutionQueueEntryRecord,
    ExecutionSessionRecord,
    NativeAttemptBindingRecord,
    NativeAttemptStateRecord,
    NativeExecutionAdmission,
    NativeExecutionConflict,
    NativeExecutionNotFound,
    NativeExecutionNotRunnable,
    ObservationConfidence,
    QueueCondition,
    QueueCapacityObservation,
    QueueProgressionState,
    RecoveryClassification,
    RepairabilityClassification,
    ResultReadyClaimRecord,
    SelfRefineActionRecord,
    SelfRefineEventRecord,
    SchedulingDecision,
    SessionCondition,
    StepCondition,
    WorkerLeaseRecord,
    WorkerOffer,
    canonical_digest,
)
from spg.domain.refinement_contract import (
    RefinementClass, RefinementSignalKind, classify_refinement,
)
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.persistence import Database


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FairCapacityScheduler:
    """Pure fair-round-robin scheduler with FIFO groups and starvation aging."""

    policy_version = "fair-round-robin-v1"

    def __init__(self, *, aging_threshold: timedelta = timedelta(minutes=5)) -> None:
        if aging_threshold.total_seconds() <= 0:
            raise ValueError("aging threshold must be positive")
        self.aging_threshold = aging_threshold

    def choose(
        self,
        entries: list[ExecutionQueueEntryRecord],
        offer: WorkerOffer,
        *,
        now: datetime,
        last_fairness_group: str | None,
    ) -> SchedulingDecision:
        eligible = [item for item in entries if self._eligible(item, offer)]
        considered = tuple(item.id for item in entries)
        if not eligible:
            return SchedulingDecision(
                selected_queue_entry_id=None,
                selected_fairness_group=None,
                reason="no runnable entry matches worker capabilities and resource profile",
                considered_entry_ids=considered,
            )

        oldest = min(eligible, key=lambda item: (item.enqueued_at, str(item.id)))
        if now - oldest.enqueued_at >= self.aging_threshold:
            return SchedulingDecision(
                selected_queue_entry_id=oldest.id,
                selected_fairness_group=oldest.fairness_group,
                reason="aging threshold selected the oldest eligible entry",
                considered_entry_ids=considered,
            )

        groups: dict[str, list[ExecutionQueueEntryRecord]] = defaultdict(list)
        for entry in eligible:
            groups[entry.fairness_group].append(entry)
        names = sorted(groups)
        if last_fairness_group in names:
            selected_group = names[(names.index(last_fairness_group) + 1) % len(names)]
        else:
            selected_group = names[0]
        selected = min(groups[selected_group], key=lambda item: (item.enqueued_at, str(item.id)))
        return SchedulingDecision(
            selected_queue_entry_id=selected.id,
            selected_fairness_group=selected_group,
            reason="fair round-robin between groups; FIFO within selected group",
            considered_entry_ids=considered,
        )

    @staticmethod
    def _eligible(entry: ExecutionQueueEntryRecord, offer: WorkerOffer) -> bool:
        return (
            (offer.requested_attempt_id is None or entry.attempt_id == offer.requested_attempt_id)
            and entry.required_provider_profile in offer.provider_profiles
            and entry.required_resource_profile in offer.resource_profiles
            and set(entry.required_capabilities).issubset(offer.capability_identities)
        )


class NativeExecutorRuntimeService:
    """Coordinate durable native execution commands over existing Attempt authority."""

    scheduler_identity = "watt-native-executor"
    infrastructure_wait_prefix = "Execution infrastructure unavailable:"

    def __init__(
        self,
        database: Database,
        *,
        scheduler: FairCapacityScheduler | None = None,
        now=_utcnow,
        self_refine_attempt_budget: int = 3,
        same_failure_threshold: int = 2,
        self_refine_time_budget_seconds: int = 300,
        self_refine_inference_budget: int = 12,
        self_refine_token_budget: int = 20000,
    ) -> None:
        if min(
            self_refine_attempt_budget, same_failure_threshold,
            self_refine_time_budget_seconds, self_refine_inference_budget,
            self_refine_token_budget,
        ) < 1:
            raise ValueError("Self-Refine budgets must be positive")
        self.database = database
        self.scheduler = scheduler or FairCapacityScheduler()
        self._now = now
        self.self_refine_attempt_budget = self_refine_attempt_budget
        self.same_failure_threshold = same_failure_threshold
        self.self_refine_time_budget_seconds = self_refine_time_budget_seconds
        self.self_refine_inference_budget = self_refine_inference_budget
        self.self_refine_token_budget = self_refine_token_budget

    def admit(self, command: NativeExecutionAdmission) -> ExecutionQueueEntryRecord:
        binding = command.binding
        if command.contract.id != binding.pwu_contract_version_id:
            raise NativeExecutionConflict("PWU contract version does not match binding")
        if command.contract.pwu_id != binding.pwu_id:
            raise NativeExecutionConflict("PWU contract belongs to another PWU")
        if command.contract.contract_digest != binding.pwu_contract_digest:
            raise NativeExecutionConflict("PWU contract digest does not match binding")
        if canonical_digest(command.contract.contract_payload) != command.contract.contract_digest:
            raise NativeExecutionConflict("PWU contract payload digest is invalid")

        request_digest = canonical_digest(
            {
                "actor_identity": command.actor_identity,
                "fairness_group": command.fairness_group,
                "binding": binding.model_dump(mode="json"),
                "required_resource_profile": command.required_resource_profile,
            }
        )
        entry = ExecutionQueueEntryRecord(
            id=uuid4(),
            command_id=command.command_id,
            request_digest=request_digest,
            actor_identity=command.actor_identity,
            work_id=binding.work_id,
            pwu_id=binding.pwu_id,
            attempt_id=binding.attempt_id,
            grant_revision=binding.generation,
            fairness_group=command.fairness_group,
            condition=QueueCondition.QUEUED,
            required_capabilities=tuple(grant.identity for grant in binding.capability_grants),
            required_provider_profile=binding.resource_envelope.provider_profile,
            required_resource_profile=command.required_resource_profile,
            wait_reason=None,
            enqueued_at=self._now(),
            available_at=command.available_at,
            resume_count=0,
            version=1,
        )
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            try:
                store.attempt_binding(binding.attempt_id)
            except NativeExecutionNotFound:
                try:
                    persisted_contract = store.contract(command.contract.id)
                except NativeExecutionNotFound:
                    store.insert_contract(command.contract)
                else:
                    if persisted_contract != command.contract:
                        raise NativeExecutionConflict(
                            "PWU contract identity was reused with different content"
                        )
                try:
                    source_vector_id = store.source_vector_id(binding.source_vector.digest or "")
                except NativeExecutionNotFound:
                    source_vector_id = uuid4()
                    store.insert_source_vector(source_vector_id, binding.source_vector)
                store.insert_resource_envelope(binding.pwu_id, binding.resource_envelope)
                session = store.execution_session(binding.session_id)
                if session is None:
                    store.insert_session(
                        ExecutionSessionRecord(
                            id=binding.session_id,
                            pwu_id=binding.pwu_id,
                            condition=SessionCondition.OPEN,
                            created_at=self._now(),
                        )
                    )
                elif (
                    session.pwu_id != binding.pwu_id
                    or session.condition is not SessionCondition.OPEN
                ):
                    raise NativeExecutionConflict(
                        "execution Session is closed or belongs to another PWU"
                    )
                store.insert_workspace(
                    binding.workspace,
                    condition="READY",
                    materialization_path=command.materialization_path,
                )
                store.insert_attempt_binding(
                    NativeAttemptBindingRecord(
                        attempt_id=binding.attempt_id,
                        pwu_id=binding.pwu_id,
                        session_id=binding.session_id,
                        pwu_contract_version_id=binding.pwu_contract_version_id,
                        source_vector_id=source_vector_id,
                        workspace_id=binding.workspace.workspace_id,
                        resource_envelope_id=binding.resource_envelope.envelope_id,
                        binding=binding,
                        binding_digest=canonical_digest(binding),
                        created_at=self._now(),
                    )
                )
                store.insert_attempt_state(
                    NativeAttemptStateRecord(
                        attempt_id=binding.attempt_id,
                        generation=binding.generation,
                        grant_state=AttemptGrantState.GRANTED,
                        runtime_mode=ExecutionMode.QUEUED,
                        updated_at=self._now(),
                    )
                )
            persisted = store.enqueue(entry)
            if persisted.attempt_id != binding.attempt_id:
                raise NativeExecutionConflict("idempotent admission resolved to another Attempt")
            if persisted.id == entry.id:
                self._append_event(
                    store,
                    pwu_id=binding.pwu_id,
                    attempt_id=binding.attempt_id,
                    event_type="NativeExecutionQueued",
                    payload={"queue_entry_id": str(entry.id), "fairness_group": entry.fairness_group},
                    causation_id=command.command_id,
                )
            uow.commit()
            return persisted

    def fork_session(
        self,
        *,
        source_session_id: UUID,
        checkpoint_id: UUID,
        actor_identity: str,
    ) -> ExecutionSessionRecord:
        del actor_identity  # Identity is represented by the caller's governed command.
        now = self._now()
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            source = store.execution_session(source_session_id)
            checkpoint = store.checkpoint(checkpoint_id)
            if source is None:
                raise NativeExecutionNotFound(
                    f"execution session not found: {source_session_id}"
                )
            if source.condition is not SessionCondition.OPEN:
                raise NativeExecutionConflict("only an open Session can be forked")
            if (
                checkpoint is None
                or checkpoint.session_id != source.id
                or checkpoint.condition is not CheckpointCondition.COMMITTED
            ):
                raise NativeExecutionConflict(
                    "Session fork requires an exact committed source checkpoint"
                )
            child = ExecutionSessionRecord(
                id=uuid4(),
                pwu_id=source.pwu_id,
                condition=SessionCondition.OPEN,
                parent_checkpoint_id=checkpoint.id,
                current_checkpoint_id=checkpoint.id,
                current_working_state_version=source.current_working_state_version,
                created_at=now,
            )
            store.insert_session(child)
            uow.commit()
            return child

    def close_session(self, session_id: UUID) -> ExecutionSessionRecord:
        now = self._now()
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            current = store.execution_session(session_id)
            if current is None:
                raise NativeExecutionNotFound(f"execution session not found: {session_id}")
            if current.condition is SessionCondition.CLOSED:
                return current
            store.close_session(session_id, closed_at=now)
            uow.commit()
            return current.model_copy(
                update={
                    "condition": SessionCondition.CLOSED,
                    "closed_at": now,
                    "version": current.version + 1,
                }
            )

    def allocate(self, offer: WorkerOffer) -> ExecutionAllocationGrant | None:
        now = self._now()
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            store.register_worker(
                offer,
                heartbeat_at=now,
                expires_at=now + timedelta(seconds=offer.lease_seconds),
            )
            entries = store.runnable_queue_locked(now)
            cursor, cursor_version = store.scheduler_cursor_locked(
                self.scheduler_identity, self.scheduler.policy_version
            )
            decision = self.scheduler.choose(
                entries,
                offer,
                now=now,
                last_fairness_group=cursor,
            )
            if decision.selected_queue_entry_id is None:
                uow.commit()
                return None
            selected = next(
                item for item in entries if item.id == decision.selected_queue_entry_id
            )
            state = store.attempt_state(selected.attempt_id, lock=True)
            if state.grant_state is not AttemptGrantState.GRANTED:
                raise NativeExecutionNotRunnable("Attempt no longer holds execution authority")
            if state.generation != selected.grant_revision:
                raise NativeExecutionNotRunnable("queue entry uses stale Attempt generation")

            token = secrets.token_urlsafe(32)
            token_digest = sha256(token.encode("utf-8")).hexdigest()
            allocation_id = uuid4()
            epoch = state.worker_epoch + 1
            deadline = now + timedelta(seconds=offer.lease_seconds)
            allocation = ExecutionAllocationRecord(
                id=allocation_id,
                queue_entry_id=selected.id,
                pwu_id=selected.pwu_id,
                attempt_id=selected.attempt_id,
                grant_revision=selected.grant_revision,
                worker_id=offer.worker_id,
                worker_profile=offer.worker_profile,
                provider_profile=selected.required_provider_profile,
                lease_epoch=epoch,
                lease_token_digest=token_digest,
                condition=AllocationCondition.ISSUED,
                policy_version=self.scheduler.policy_version,
                decision_reason=decision.reason,
                issued_at=now,
                start_deadline=deadline,
                expires_at=deadline,
            )
            store.insert_allocation(allocation)
            store.insert_lease(
                uuid4(),
                WorkerLeaseRecord(
                    attempt_id=selected.attempt_id,
                    allocation_id=allocation_id,
                    worker_id=offer.worker_id,
                    epoch=epoch,
                    token_digest=token_digest,
                    deadline=deadline,
                    heartbeat_at=now,
                ),
            )
            store.set_queue_condition(
                selected.id,
                expected_version=selected.version,
                condition=QueueCondition.ALLOCATED,
            )
            store.update_attempt_state(
                selected.attempt_id,
                expected_version=state.version,
                values={"worker_epoch": epoch, "runtime_mode": ExecutionMode.QUEUED},
            )
            store.advance_scheduler_cursor(
                self.scheduler_identity,
                expected_version=cursor_version,
                fairness_group=decision.selected_fairness_group or selected.fairness_group,
            )
            self._append_event(
                store,
                pwu_id=selected.pwu_id,
                attempt_id=selected.attempt_id,
                event_type="ExecutionCapacityAllocated",
                payload={
                    "allocation_id": str(allocation_id),
                    "worker_id": offer.worker_id,
                    "decision_reason": decision.reason,
                },
            )
            uow.commit()
            return ExecutionAllocationGrant(
                allocation=allocation,
                queue_entry=selected.model_copy(
                    update={"condition": QueueCondition.ALLOCATED, "version": selected.version + 1}
                ),
                lease_token=token,
            )

    @staticmethod
    def _registration_matches(entry, registration) -> bool:
        return (
            entry.required_provider_profile in registration.provider_profiles
            and entry.required_resource_profile in registration.resource_profiles
            and set(entry.required_capabilities).issubset(
                registration.capability_identities
            )
        )

    def _capacity_observation(
        self,
        entry: ExecutionQueueEntryRecord,
        registrations,
        occupied_worker_ids: set[str],
        *,
        now: datetime,
        unavailable_after: timedelta,
    ) -> QueueCapacityObservation:
        compatible = tuple(
            registration
            for registration in registrations
            if self._registration_matches(entry, registration)
        )
        occupied = sum(
            registration.worker_id in occupied_worker_ids
            for registration in compatible
        )
        pending_conditions = {
            QueueCondition.QUEUED,
            QueueCondition.RETURNED_TO_QUEUE,
        }
        infrastructure_wait = (
            entry.condition is QueueCondition.WAITING_RESOURCE
            and (entry.wait_reason or "").startswith(self.infrastructure_wait_prefix)
        )
        if entry.condition not in pending_conditions and not infrastructure_wait:
            return QueueCapacityObservation(
                progression_state=QueueProgressionState.NOT_APPLICABLE,
                reason=entry.wait_reason or "Queue allocation is not currently pending.",
                scheduler_alive=bool(compatible),
                compatible_worker_count=len(compatible),
                occupied_worker_count=occupied,
                observed_at=now,
            )
        if not compatible:
            within_startup_grace = now - entry.enqueued_at < unavailable_after
            return QueueCapacityObservation(
                progression_state=(
                    QueueProgressionState.SCHEDULING
                    if within_startup_grace
                    else QueueProgressionState.INFRASTRUCTURE_UNAVAILABLE
                ),
                reason=(
                    "Waiting for the execution scheduler to observe compatible capacity."
                    if within_startup_grace
                    else "No live compatible execution worker is available. Watt will recover automatically when one returns."
                ),
                scheduler_alive=False,
                compatible_worker_count=0,
                occupied_worker_count=0,
                observed_at=now,
            )
        if occupied >= len(compatible):
            return QueueCapacityObservation(
                progression_state=QueueProgressionState.CAPACITY_WAIT,
                reason="All compatible execution slots are currently occupied.",
                scheduler_alive=True,
                compatible_worker_count=len(compatible),
                occupied_worker_count=occupied,
                observed_at=now,
            )
        return QueueCapacityObservation(
            progression_state=QueueProgressionState.SCHEDULING,
            reason="Compatible execution capacity is available and Watt is assigning it.",
            scheduler_alive=True,
            compatible_worker_count=len(compatible),
            occupied_worker_count=occupied,
            observed_at=now,
        )

    def list_queue_reality(
        self,
        *,
        work_id: UUID | None = None,
        unavailable_after: timedelta = timedelta(seconds=5),
    ) -> tuple[tuple[ExecutionQueueEntryRecord, QueueCapacityObservation], ...]:
        now = self._now()
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            records = store.list_queue(work_id=work_id)
            registrations = store.live_worker_registrations(now)
            occupied = store.active_allocation_worker_ids()
            return tuple(
                (
                    record,
                    self._capacity_observation(
                        record,
                        registrations,
                        occupied,
                        now=now,
                        unavailable_after=unavailable_after,
                    ),
                )
                for record in records
            )

    def reconcile_queue_ownership(
        self,
        *,
        unavailable_after: timedelta = timedelta(seconds=5),
    ) -> tuple[UUID, ...]:
        """Expose absent scheduler ownership while keeping recovery automatic."""

        now = self._now()
        changed: list[UUID] = []
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            entries = store.runnable_queue_locked(now)
            registrations = store.live_worker_registrations(now)
            occupied = store.active_allocation_worker_ids()
            for entry in entries:
                infrastructure_wait = (
                    entry.condition is QueueCondition.WAITING_RESOURCE
                    and (entry.wait_reason or "").startswith(
                        self.infrastructure_wait_prefix
                    )
                )
                if (
                    entry.condition is QueueCondition.WAITING_RESOURCE
                    and not infrastructure_wait
                ):
                    continue
                observation = self._capacity_observation(
                    entry,
                    registrations,
                    occupied,
                    now=now,
                    unavailable_after=unavailable_after,
                )
                if (
                    observation.progression_state
                    is QueueProgressionState.INFRASTRUCTURE_UNAVAILABLE
                    and not infrastructure_wait
                ):
                    store.set_queue_condition(
                        entry.id,
                        expected_version=entry.version,
                        condition=QueueCondition.WAITING_RESOURCE,
                        wait_reason=(
                            f"{self.infrastructure_wait_prefix} no live compatible worker; "
                            "automatic recovery remains armed"
                        ),
                        available_at=now,
                    )
                    changed.append(entry.id)
                elif infrastructure_wait and observation.compatible_worker_count > 0:
                    store.set_queue_condition(
                        entry.id,
                        expected_version=entry.version,
                        condition=QueueCondition.QUEUED,
                        wait_reason=None,
                        available_at=now,
                    )
                    changed.append(entry.id)
            uow.commit()
        return tuple(changed)

    def heartbeat(
        self,
        grant: ExecutionAllocationGrant,
        *,
        lease_seconds: int = 30,
        offer: WorkerOffer | None = None,
    ) -> None:
        now = self._now()
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            if offer is not None:
                store.register_worker(
                    offer,
                    heartbeat_at=now,
                    expires_at=now + timedelta(seconds=lease_seconds),
                )
            valid = store.heartbeat_lease(
                grant.allocation.attempt_id,
                worker_id=grant.allocation.worker_id,
                epoch=grant.allocation.lease_epoch,
                token_digest=sha256(grant.lease_token.encode("utf-8")).hexdigest(),
                heartbeat_at=now,
                deadline=now + timedelta(seconds=lease_seconds),
            )
            if not valid:
                raise NativeExecutionConflict("worker lease is stale, expired, or fenced")
            uow.commit()

    def activate_allocation(self, grant: ExecutionAllocationGrant) -> None:
        """Fence-check and activate one issued allocation before kernel execution."""

        now = self._now()
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            allocation = store.allocation(grant.allocation.id, lock=True)
            if allocation.condition is not AllocationCondition.ISSUED:
                raise NativeExecutionConflict("allocation is not awaiting worker start")
            if allocation.start_deadline < now:
                raise NativeExecutionConflict("allocation start deadline expired")
            valid = store.heartbeat_lease(
                allocation.attempt_id,
                worker_id=allocation.worker_id,
                epoch=allocation.lease_epoch,
                token_digest=sha256(grant.lease_token.encode("utf-8")).hexdigest(),
                heartbeat_at=now,
                deadline=allocation.expires_at,
            )
            if not valid:
                raise NativeExecutionConflict("allocation lease is stale or fenced")
            queue = store.queue_entry(allocation.queue_entry_id)
            state = store.attempt_state(allocation.attempt_id, lock=True)
            store.set_allocation_condition(allocation.id, AllocationCondition.ACTIVE)
            store.set_queue_condition(
                queue.id,
                expected_version=queue.version,
                condition=QueueCondition.EXECUTING,
            )
            store.update_attempt_state(
                allocation.attempt_id,
                expected_version=state.version,
                values={"runtime_mode": ExecutionMode.RUNNING},
            )
            self._append_event(
                store,
                pwu_id=allocation.pwu_id,
                attempt_id=allocation.attempt_id,
                event_type="NativeExecutionStarted",
                payload={"allocation_id": str(allocation.id), "worker_epoch": allocation.lease_epoch},
            )
            uow.commit()

    def finish_allocation(
        self,
        grant: ExecutionAllocationGrant,
        result: KernelRunResult,
    ) -> None:
        """Persist worker outcome while keeping Completion/Verification downstream."""

        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            allocation = store.allocation(grant.allocation.id, lock=True)
            state = store.attempt_state(allocation.attempt_id, lock=True)
            queue = store.queue_entry(allocation.queue_entry_id)
            if state.worker_epoch != allocation.lease_epoch:
                raise NativeExecutionConflict("worker epoch was fenced before completion")
            retry_terminal, observation_confidence = self._record_self_refine(
                store, allocation=allocation, queue=queue, result=result,
            )
            retry_exhausted = retry_terminal is not None
            if result.runtime_mode is ExecutionMode.PAUSED:
                next_queue = QueueCondition.CHECKPOINTED
                next_mode = ExecutionMode.PAUSED
                grant_state = AttemptGrantState.GRANTED
                terminal = None
            elif retry_terminal is not None:
                next_queue = QueueCondition.COMPLETED
                next_mode = ExecutionMode.FINISHED
                grant_state = AttemptGrantState.RELEASED
                terminal = retry_terminal
            elif result.runtime_mode is ExecutionMode.WAITING_RESOURCE:
                next_queue = QueueCondition.WAITING_RESOURCE
                next_mode = ExecutionMode.WAITING_RESOURCE
                grant_state = AttemptGrantState.GRANTED
                terminal = None
            elif result.runtime_mode is ExecutionMode.FINISHED:
                next_queue = (
                    QueueCondition.CANCELLED
                    if result.terminal_outcome is AttemptTerminalOutcome.CANCELLED
                    else QueueCondition.COMPLETED
                )
                next_mode = ExecutionMode.FINISHED
                grant_state = AttemptGrantState.RELEASED
                terminal = result.terminal_outcome
            else:
                raise NativeExecutionConflict("worker returned an unsupported lifecycle mode")
            store.release_allocation(allocation.id)
            store.set_queue_condition(
                queue.id,
                expected_version=queue.version,
                condition=next_queue,
                wait_reason=result.summary if next_queue is QueueCondition.WAITING_RESOURCE else None,
                available_at=(
                    self._now()
                    + timedelta(seconds=min(30, 2 ** queue.resume_count))
                    if next_queue is QueueCondition.WAITING_RESOURCE
                    and result.resource_retryable
                    else self._now() + timedelta(days=36500)
                    if next_queue is QueueCondition.WAITING_RESOURCE
                    else None
                ),
                increment_resume=(
                    next_queue is QueueCondition.WAITING_RESOURCE
                    and result.resource_retryable
                ),
            )
            store.update_attempt_state(
                allocation.attempt_id,
                expected_version=state.version,
                values={
                    "runtime_mode": next_mode,
                    "grant_state": grant_state,
                    "terminal_outcome": terminal,
                    "current_step_sequence": result.step_count,
                    "current_checkpoint_id": result.final_checkpoint_id,
                },
            )
            if (
                terminal is AttemptTerminalOutcome.RESULT_READY
                and result.final_checkpoint_id is not None
                and result.result_claim is not None
            ):
                binding = store.attempt_binding(allocation.attempt_id)
                raw_evidence = result.result_claim.get("evidence_ids", [])
                evidence_ids = tuple(UUID(item) for item in raw_evidence)
                store.insert_result_ready_claim(
                    ResultReadyClaimRecord(
                        id=uuid4(),
                        pwu_id=allocation.pwu_id,
                        attempt_id=allocation.attempt_id,
                        checkpoint_bundle_id=result.final_checkpoint_id,
                        contract_digest=binding.binding.pwu_contract_digest,
                        output_vector=dict(result.result_claim.get("output_vector", {})),
                        evidence_ids=evidence_ids,
                        residual_obligations=result.residual_obligations,
                        claimant_identity=allocation.worker_id,
                        created_at=self._now(),
                    )
                )
            applied_control = {
                ExecutionMode.PAUSED: ControlAction.PAUSE,
                ExecutionMode.FINISHED: (
                    ControlAction.STOP
                    if terminal is AttemptTerminalOutcome.STOPPED
                    else ControlAction.CANCEL
                    if terminal is AttemptTerminalOutcome.CANCELLED
                    else None
                ),
            }.get(result.runtime_mode)
            if applied_control is not None:
                pending = store.pending_control_request(
                    allocation.attempt_id,
                    action=applied_control.value,
                )
                if pending is not None:
                    store.set_control_request_condition(
                        pending.command_id,
                        ControlRequestCondition.APPLIED,
                        applied_at=self._now(),
                    )
            self._append_event(
                store,
                pwu_id=allocation.pwu_id,
                attempt_id=allocation.attempt_id,
                event_type="NativeExecutionWorkerReturned",
                payload={
                    "runtime_mode": next_mode.value,
                    "terminal_outcome": terminal.value if terminal else None,
                    "checkpoint_id": str(result.final_checkpoint_id) if result.final_checkpoint_id else None,
                    "automatic_retry_exhausted": retry_exhausted,
                    "observation_confidence": observation_confidence.value,
                },
            )
            uow.commit()

    def _record_self_refine(
        self, store, *, allocation, queue, result: KernelRunResult,
    ) -> tuple[AttemptTerminalOutcome | None, ObservationConfidence]:
        """Classify observed Reality before any repair, then persist the applied decision."""

        now = self._now()
        prior_observation = store.latest_native_observation(allocation.attempt_id)
        confidence = self._observation_confidence(result, prior_observation)
        event = store.open_self_refine_event(allocation.attempt_id)
        if result.runtime_mode is ExecutionMode.WAITING_RESOURCE and result.resource_retryable:
            family = result.failure_family or "RUNTIME_PROVIDER_FAILURE"
            signature = sha256(f"{family}:{result.summary}".encode("utf-8")).hexdigest()
            if confidence is ObservationConfidence.TRANSIENT_ANOMALY:
                self._append_event(
                    store, pwu_id=allocation.pwu_id, attempt_id=allocation.attempt_id,
                    event_type="NativeObservationClassified",
                    payload={"classification": confidence.value, "failure_family": family,
                             "failure_signature": signature, "self_refine_started": False},
                )
                return None, confidence

            if event is not None and event.failure_signature != signature:
                prior_actions = store.self_refine_actions(event.id)
                store.append_self_refine_action(SelfRefineActionRecord(
                    id=uuid4(), event_id=event.id, sequence=len(prior_actions) + 1,
                    created_at=now,
                    repair_action="Close the prior diagnosis after a distinct runtime failure",
                    observed_reality={"next_failure_signature": signature},
                    evidence_references=(f"native-attempt:{allocation.attempt_id}",),
                    outcome="SUPERSEDED_BY_NEW_FAILURE",
                ))
                store.complete_self_refine_event(
                    event.id, result="FAILED", resume_result="NOT_RESUMED",
                    status="MITIGATED",
                    elapsed_seconds=max(0, int((now - event.created_at).total_seconds())),
                    updated_at=now,
                    compute_overhead={"tool_effects": len(prior_actions)},
                )
                event = None

            binding = store.attempt_binding(allocation.attempt_id).binding
            contract = store.contract(binding.pwu_contract_version_id)
            repairability = self._runtime_repairability(family, contract.contract_payload)
            actions = () if event is None else store.self_refine_actions(event.id)
            checkpoint = (
                store.checkpoint(result.final_checkpoint_id)
                if result.final_checkpoint_id else None
            )
            material_reality_digest = canonical_digest({
                "source_vector": binding.source_vector.digest,
                "tool_results": (
                    checkpoint.execution_manifest.get("tool_results", [])
                    if checkpoint else []
                ),
            })
            same_failures = sum(
                action.observed_reality.get("failure_signature") == signature
                and action.observed_reality.get("material_reality_digest") == material_reality_digest
                for action in actions
            ) + 1
            inference_total = result.inference_submissions + sum(
                int(action.observed_reality.get("inference_submissions", 0))
                for action in actions
            )
            tool_total = result.tool_effects + sum(
                int(action.observed_reality.get("tool_effects", 0))
                for action in actions
            )
            elapsed = 0 if event is None else max(0, int((now - event.created_at).total_seconds()))
            observed_tokens = (
                0 if event is None else int(store.observed_repair_model_usage(
                    allocation.attempt_id, since=event.created_at,
                ).get("total_tokens", 0))
            )
            prior_occurrences = store.prior_self_refine_matches(
                signature, before_event_id=event.id if event is not None else UUID(int=0),
            )
            provisional_class = classify_refinement(
                converged=False, same_signature_count=same_failures,
                prior_occurrences=prior_occurrences,
                nonconvergence_threshold=self.same_failure_threshold,
            )
            decision = self._adaptive_budget(
                binding=binding, contract_payload=contract.contract_payload,
                family=family, repairability=repairability, queue_resume_count=queue.resume_count,
                same_failures=same_failures, elapsed=elapsed,
                inference_total=inference_total, tool_total=tool_total,
                observed_tokens=observed_tokens,
                refinement_class=provisional_class,
            )
            exhausted = not decision["allow_retry"]
            if event is None:
                event_id = uuid4()
                event = SelfRefineEventRecord(
                    id=event_id, work_id=binding.work_id,
                    operation_id=allocation.attempt_id, created_at=now,
                    failure_family=family, failure_signature=signature,
                    refinement_class=classify_refinement(
                        converged=False, same_signature_count=same_failures,
                        prior_occurrences=prior_occurrences,
                        budget_exhausted=exhausted,
                        nonconvergence_threshold=self.same_failure_threshold,
                    ),
                    signal_kind=(
                        RefinementSignalKind.REALITY_MISMATCH
                        if family in {"REPOSITORY_REALITY_MISMATCH", "SOURCE_VECTOR_MISMATCH"}
                        else RefinementSignalKind.VERIFICATION_CONTRADICTION
                        if family == "VERIFICATION_FAILURE"
                        else RefinementSignalKind.EXECUTION_FAILURE
                    ),
                    affected_component="native-executor/provider",
                    expected_reality={"outcome": "RESULT_READY", "contract_digest": binding.pwu_contract_digest},
                    observed_reality={
                        "runtime_mode": result.runtime_mode.value,
                        "checkpoint_id": str(result.final_checkpoint_id) if result.final_checkpoint_id else None,
                        "failure_signature": signature,
                        "material_reality_digest": material_reality_digest,
                        "observation_evidence": self._safe_observation_evidence(result.observation_evidence),
                    },
                    diagnosis_summary="The admitted Native Attempt did not reach its expected result.",
                    root_cause_classification=family,
                    repair_hypothesis=(
                        "Reconcile the durable checkpoint and retry the same admitted contract "
                        "only while current authority and adaptive budget permit."
                    ),
                    evidence_references=(f"native-attempt:{allocation.attempt_id}",),
                    repairability=repairability,
                    observation_confidence=confidence,
                    budget_decision=decision,
                    diagnostic_evidence={
                        "native_attempt_ref": f"native-attempt:{allocation.attempt_id}",
                        "checkpoint_ref": (
                            f"native-checkpoint:{result.final_checkpoint_id}"
                            if result.final_checkpoint_id else None
                        ),
                        "failure_signature": signature,
                        "failure_family": family,
                    },
                    model_token_usage={},
                    compute_overhead={
                        "inference_submissions": result.inference_submissions,
                        "tool_effects": result.tool_effects,
                    },
                    known_failure_match=store.prior_self_refine_matches(
                        signature, before_event_id=event_id,
                    ) > 0,
                    updated_at=now,
                )
                store.insert_self_refine_event(event)
            else:
                store.update_self_refine_budget(event.id, decision, updated_at=now)
            store.append_self_refine_action(SelfRefineActionRecord(
                id=uuid4(), event_id=event.id, sequence=len(actions) + 1,
                created_at=now,
                repair_action=(
                    "Stop same-layer replay and preserve the governing failure"
                    if exhausted else "Resume from the durable checkpoint under the applied budget"
                ),
                observed_reality={
                    "runtime_mode": result.runtime_mode.value,
                    "checkpoint_id": str(result.final_checkpoint_id) if result.final_checkpoint_id else None,
                    "failure_signature": signature,
                    "material_reality_digest": material_reality_digest,
                    "same_failure_count": same_failures,
                    "queue_resume_count": queue.resume_count,
                    "inference_submissions": result.inference_submissions,
                    "tool_effects": result.tool_effects,
                    "observation_confidence": confidence.value,
                    "repairability": repairability.value,
                    "budget_decision": decision,
                },
                evidence_references=(f"native-attempt:{allocation.attempt_id}",),
                outcome="ESCALATED" if exhausted else "RETRY_SCHEDULED",
            ))
            if exhausted:
                store.complete_self_refine_event(
                    event.id, result="ESCALATED", resume_result="NOT_RESUMED",
                    status="MITIGATED", elapsed_seconds=elapsed,
                    updated_at=now,
                    compute_overhead={"inference_submissions": inference_total, "tool_effects": tool_total},
                    model_token_usage=store.observed_repair_model_usage(
                        allocation.attempt_id, since=event.created_at,
                    ),
                )
                human_owned = repairability in {
                    RepairabilityClassification.REQUIRES_HUMAN_INPUT,
                    RepairabilityClassification.REQUIRES_HUMAN_DECISION,
                }
                return (
                    AttemptTerminalOutcome.BOUNDARY_CROSSING_REQUIRED
                    if human_owned else AttemptTerminalOutcome.UNABLE_TO_COMPLETE,
                    confidence,
                )
            return None, confidence

        if event is not None and result.runtime_mode is ExecutionMode.FINISHED:
            actions = store.self_refine_actions(event.id)
            recovered = result.terminal_outcome is AttemptTerminalOutcome.RESULT_READY
            store.append_self_refine_action(SelfRefineActionRecord(
                id=uuid4(), event_id=event.id, sequence=len(actions) + 1,
                created_at=now,
                repair_action="Re-observe the resumed Native Attempt outcome",
                observed_reality={
                    "runtime_mode": result.runtime_mode.value,
                    "terminal_outcome": result.terminal_outcome.value if result.terminal_outcome else None,
                    "checkpoint_id": str(result.final_checkpoint_id) if result.final_checkpoint_id else None,
                    "observation_confidence": confidence.value,
                },
                evidence_references=(f"native-attempt:{allocation.attempt_id}",),
                outcome="RECOVERED" if recovered else "FAILED",
            ))
            store.complete_self_refine_event(
                event.id,
                result="RECOVERED" if recovered else "FAILED",
                resume_result="RESUMED" if recovered else "NOT_RESUMED",
                status="VERIFIED" if recovered else "MITIGATED",
                elapsed_seconds=max(0, int((now - event.created_at).total_seconds())),
                updated_at=now,
                model_token_usage=store.observed_repair_model_usage(
                    allocation.attempt_id, since=event.created_at,
                ),
                compute_overhead={
                    "inference_submissions": result.inference_submissions + sum(
                        int(action.observed_reality.get("inference_submissions", 0))
                        for action in actions
                    ),
                    "tool_effects": result.tool_effects + sum(
                        int(action.observed_reality.get("tool_effects", 0))
                        for action in actions
                    ),
                },
            )
        return None, confidence

    @staticmethod
    def _observation_confidence(
        result: KernelRunResult, prior_observation: dict | None,
    ) -> ObservationConfidence:
        if result.runtime_mode is ExecutionMode.FINISHED:
            return (
                ObservationConfidence.OBSERVED_SUCCESS
                if result.terminal_outcome is AttemptTerminalOutcome.RESULT_READY
                else ObservationConfidence.CONFIRMED_FAILURE
            )
        if result.runtime_mode is not ExecutionMode.WAITING_RESOURCE:
            return ObservationConfidence.INCONCLUSIVE
        signal = result.observation_evidence
        if signal.get("authoritative_state_mismatch") is True:
            return ObservationConfidence.CONFIRMED_FAILURE
        if result.failure_family in {"REPOSITORY_REALITY_MISMATCH", "SOURCE_VECTOR_MISMATCH"}:
            return ObservationConfidence.CONFIRMED_FAILURE
        if result.failure_family in {"RUNTIME_HEALTH", "STARTUP_HEALTH"}:
            if signal.get("process_exit_code") is not None or signal.get("stable_failure") is True:
                return ObservationConfidence.CONFIRMED_FAILURE
            signature = sha256(
                f"{result.failure_family}:{result.summary}".encode("utf-8")
            ).hexdigest()
            return (
                ObservationConfidence.CONFIRMED_FAILURE
                if prior_observation is not None
                and prior_observation.get("failure_signature") == signature
                and prior_observation.get("classification") == ObservationConfidence.TRANSIENT_ANOMALY.value
                else ObservationConfidence.TRANSIENT_ANOMALY
            )
        return ObservationConfidence.CONFIRMED_FAILURE

    @staticmethod
    def _safe_observation_evidence(signal: dict) -> dict[str, object]:
        """Persist authoritative observation facts, not free-form runtime log text."""

        allowed = {
            "authoritative_state_mismatch", "stable_failure", "process_exit_code",
            "expected_revision", "observed_revision", "health_probe_count",
            "source_reference", "evidence_digest",
        }
        return {
            key: value[:255] if isinstance(value, str) else value
            for key, value in signal.items()
            if key in allowed and isinstance(value, (str, int, bool))
        }

    @staticmethod
    def _runtime_repairability(
        family: str, contract_payload: dict,
    ) -> RepairabilityClassification:
        if family in {"PROVIDER_TRANSPORT", "PROVIDER_CAPACITY", "RUNTIME_HEALTH", "STARTUP_HEALTH"}:
            return RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE
        if family in {"AUTH_REQUIRED", "MISSING_HUMAN_INPUT"}:
            return RepairabilityClassification.REQUIRES_HUMAN_INPUT
        if family in {"PRODUCT_AMBIGUITY", "PRODUCT_INTENT_CHANGE"}:
            return RepairabilityClassification.REQUIRES_HUMAN_DECISION
        if family in {"REPOSITORY_REALITY_MISMATCH", "SOURCE_VECTOR_MISMATCH"}:
            operation = contract_payload.get("git_operation")
            if isinstance(operation, dict) and operation.get("operation") == "branch.create":
                return RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE
            return RepairabilityClassification.REPAIRABLE_WITH_SUFFICIENT_EVIDENCE
        return RepairabilityClassification.REPAIRABLE_WITH_SUFFICIENT_EVIDENCE

    def _adaptive_budget(
        self, *, binding, contract_payload: dict, family: str,
        repairability: RepairabilityClassification, queue_resume_count: int,
        same_failures: int, elapsed: int, inference_total: int,
        tool_total: int, observed_tokens: int,
        refinement_class: RefinementClass = RefinementClass.ROUTINE_STOCHASTIC_REFINEMENT,
    ) -> dict[str, object]:
        """Bound retry by admitted Work/PWU resources and observed failure cost."""

        envelope = binding.resource_envelope
        task = contract_payload.get("task_contract")
        if not isinstance(task, dict):
            completion = contract_payload.get("completion_contract")
            task = completion.get("task_contract") if isinstance(completion, dict) else None
        task = task if isinstance(task, dict) else {}
        complexity_points = sum(
            len(task.get(key, [])) if isinstance(task.get(key), list) else 0
            for key in ("scope", "acceptance_meaning", "evidence_requirements", "required_capabilities")
        )
        complexity = "LARGE" if complexity_points >= 12 else "SMALL"
        writable_mounts = sum(mount.writable for mount in binding.workspace.mounts)
        risk_factors = [
            *(["high_impact_engineering_activity"]
              if task.get("activity") in {"MIGRATION", "REFACTORING", "RELEASE", "ARCHITECTURE_DECISION"}
              else []),
            *(["multiple_writable_mounts"] if writable_mounts > 1 else []),
            *(["authoritative_source_or_intent_mismatch"]
              if family in {"SOURCE_VECTOR_MISMATCH", "PRODUCT_INTENT_CHANGE"} else []),
        ]
        risk = "HIGH" if risk_factors else "NORMAL"
        reversible = family in {
            "PROVIDER_TRANSPORT", "PROVIDER_CAPACITY", "RUNTIME_PROVIDER_FAILURE",
            "RUNTIME_HEALTH", "STARTUP_HEALTH",
            "REPOSITORY_REALITY_MISMATCH",
        }
        attempt_limit = min(
            self.self_refine_attempt_budget,
            envelope.max_successor_recoveries + 1,
            1 if risk == "HIGH" else 3 if complexity == "LARGE" else 2 if reversible else 1,
        )
        time_limit = min(self.self_refine_time_budget_seconds, envelope.max_active_seconds)
        inference_limit = min(self.self_refine_inference_budget, envelope.max_inference_submissions)
        remaining = {
            "attempts": max(0, attempt_limit - queue_resume_count),
            "same_signature": max(0, self.same_failure_threshold - same_failures),
            "active_seconds": max(0, time_limit - elapsed),
            "inference_submissions": max(0, inference_limit - inference_total),
            "tool_effects": max(0, envelope.max_tool_effects - tool_total),
            "model_tokens": max(0, self.self_refine_token_budget - observed_tokens),
        }
        allowed_classifications = {
            RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE,
            RepairabilityClassification.REPAIRABLE_WITH_SUFFICIENT_EVIDENCE,
        }
        allow_retry = (
            repairability in allowed_classifications
            and refinement_class is not RefinementClass.SYSTEMIC_OR_NON_CONVERGING_INCIDENT
            and remaining["attempts"] > 0
            and remaining["same_signature"] > 0
            and remaining["active_seconds"] > 0
            and remaining["inference_submissions"] > 0
            and remaining["tool_effects"] > 0
            and remaining["model_tokens"] > 0
            and envelope.max_cost_units != 0
        )
        return {
            "policy_version": "adaptive-self-converge-v1",
            "allow_retry": allow_retry,
            "repairability": repairability.value,
            "human_escalated": (
                not allow_retry and repairability in {
                    RepairabilityClassification.REQUIRES_HUMAN_INPUT,
                    RepairabilityClassification.REQUIRES_HUMAN_DECISION,
                }
            ),
            "refinement_class": refinement_class.value,
            "complexity": complexity,
            "complexity_points": complexity_points,
            "risk": risk,
            "risk_factors": risk_factors,
            "reversible": reversible,
            "failure_family": family,
            "limits": {
                "attempts": attempt_limit,
                "same_signature": self.same_failure_threshold,
                "active_seconds": time_limit,
                "inference_submissions": inference_limit,
                "tool_effects": envelope.max_tool_effects,
                "model_tokens": self.self_refine_token_budget,
                "cost_units": envelope.max_cost_units,
            },
            "observed": {
                "prior_retries": queue_resume_count,
                "same_signature_failures": same_failures,
                "elapsed_seconds": elapsed,
                "inference_submissions": inference_total,
                "tool_effects": tool_total,
                "model_tokens": observed_tokens,
            },
            "remaining": remaining,
        }

    def observe(self, handle: ExecutionHandle) -> BackendObservation:
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            state = store.attempt_state(handle.attempt_id)
            if state.generation != handle.generation:
                raise NativeExecutionConflict("execution handle refers to stale generation")
            queue = store.queue_for_attempt(handle.attempt_id)
            summary = queue.wait_reason if queue and queue.wait_reason else (
                queue.condition.value if queue else state.runtime_mode.value
            )
            return BackendObservation(
                handle=handle,
                runtime_mode=state.runtime_mode,
                terminal_outcome=state.terminal_outcome,
                current_checkpoint_id=state.current_checkpoint_id,
                progress_summary=summary,
                observed_at=self._now(),
            )

    def control(self, command: BackendControlCommand) -> BackendControlReceipt:
        now = self._now()
        digest = canonical_digest(command)
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            state = store.attempt_state(command.handle.attempt_id, lock=True)
            record, inserted = store.insert_control_request(
                ExecutionControlRequestRecord(
                    id=uuid4(),
                    command_id=command.command_id,
                    attempt_id=command.handle.attempt_id,
                    actor_identity=command.actor_identity,
                    action=command.action,
                    expected_control_version=command.expected_control_version,
                    request_digest=digest,
                    condition=ControlRequestCondition.REQUESTED,
                    reason=command.reason,
                    created_at=now,
                )
            )
            if not inserted:
                return BackendControlReceipt(
                    command_id=command.command_id,
                    accepted=record.condition is not ControlRequestCondition.REJECTED,
                    condition=record.condition,
                    message="idempotent control result",
                    recorded_at=record.applied_at or record.created_at,
                )
            if state.control_version != command.expected_control_version:
                store.set_control_request_condition(command.command_id, ControlRequestCondition.REJECTED)
                uow.commit()
                return BackendControlReceipt(
                    command_id=command.command_id,
                    accepted=False,
                    condition=ControlRequestCondition.REJECTED,
                    message="control version is stale",
                    recorded_at=now,
                )
            target = {
                ControlAction.PAUSE: ExecutionMode.PAUSE_REQUESTED,
                ControlAction.RESUME: ExecutionMode.RESUME_REQUESTED,
                ControlAction.STOP: ExecutionMode.STOP_REQUESTED,
                ControlAction.CANCEL: ExecutionMode.CANCEL_REQUESTED,
            }[command.action]
            if command.action is ControlAction.RESUME and state.runtime_mode is not ExecutionMode.PAUSED:
                store.set_control_request_condition(command.command_id, ControlRequestCondition.REJECTED)
                uow.commit()
                return BackendControlReceipt(
                    command_id=command.command_id,
                    accepted=False,
                    condition=ControlRequestCondition.REJECTED,
                    message="resume requires a paused Attempt",
                    recorded_at=now,
                )
            queue = store.queue_for_attempt(state.attempt_id)
            worker_owned = (
                queue is not None
                and queue.condition in {
                    QueueCondition.ALLOCATED,
                    QueueCondition.EXECUTING,
                }
                and store.allocation_for_attempt(state.attempt_id) is not None
            )
            if not worker_owned and command.action is ControlAction.PAUSE:
                target = ExecutionMode.PAUSED
            terminal = None
            grant_state = state.grant_state
            if not worker_owned and command.action in {
                ControlAction.STOP,
                ControlAction.CANCEL,
            }:
                target = ExecutionMode.FINISHED
                terminal = (
                    AttemptTerminalOutcome.STOPPED
                    if command.action is ControlAction.STOP
                    else AttemptTerminalOutcome.CANCELLED
                )
                grant_state = AttemptGrantState.RELEASED
            store.update_attempt_state(
                state.attempt_id,
                expected_version=state.version,
                values={
                    "runtime_mode": target,
                    "control_version": state.control_version + 1,
                    "terminal_outcome": terminal,
                    "grant_state": grant_state,
                },
            )
            if command.action is ControlAction.RESUME:
                if queue is None:
                    raise NativeExecutionConflict("paused Attempt has no queue entry")
                store.set_queue_condition(
                    queue.id,
                    expected_version=queue.version,
                    condition=QueueCondition.RETURNED_TO_QUEUE,
                )
            elif queue is not None and not worker_owned and command.action is ControlAction.PAUSE:
                store.set_queue_condition(
                    queue.id,
                    expected_version=queue.version,
                    condition=QueueCondition.CHECKPOINTED,
                    wait_reason="paused before capacity allocation",
                )
            elif queue is not None and not worker_owned and command.action in {
                ControlAction.STOP,
                ControlAction.CANCEL,
            }:
                store.set_queue_condition(
                    queue.id,
                    expected_version=queue.version,
                    condition=(
                        QueueCondition.CANCELLED
                        if command.action is ControlAction.CANCEL
                        else QueueCondition.COMPLETED
                    ),
                    wait_reason=f"{command.action.value.lower()} applied before allocation",
                )
            applied_immediately = not worker_owned or command.action is ControlAction.RESUME
            if applied_immediately:
                store.set_control_request_condition(
                    command.command_id, ControlRequestCondition.APPLIED, applied_at=now
                )
            uow.commit()
            return BackendControlReceipt(
                command_id=command.command_id,
                accepted=True,
                condition=(
                    ControlRequestCondition.APPLIED
                    if applied_immediately
                    else ControlRequestCondition.REQUESTED
                ),
                message=f"{command.action.value} request recorded",
                recorded_at=now,
            )

    def reconcile_expired_leases(self) -> tuple[UUID, ...]:
        """Requeue only settled crash frontiers; fence every unresolved effect."""

        now = self._now()
        reconciled: list[UUID] = []
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            for lease in store.expired_leases_locked(now):
                state = store.attempt_state(lease.attempt_id, lock=True)
                allocation = store.allocation(lease.allocation_id, lock=True)
                if state.worker_epoch != lease.epoch:
                    store.release_allocation(allocation.id, expired=True)
                    continue
                effects = tuple(store.effects_for_attempt(lease.attempt_id))
                steps = tuple(store.steps_for_attempt(lease.attempt_id))
                checkpoint = store.latest_checkpoint(lease.attempt_id)
                unresolved = any(
                    effect.condition not in {
                        EffectCondition.SETTLED,
                        EffectCondition.FAILED,
                    }
                    for effect in effects
                ) or any(step.condition is StepCondition.RUNNING for step in steps)
                store.release_allocation(allocation.id, expired=True)
                if not unresolved:
                    queue = store.queue_entry(allocation.queue_entry_id)
                    store.set_queue_condition(
                        queue.id,
                        expected_version=queue.version,
                        condition=QueueCondition.RETURNED_TO_QUEUE,
                        wait_reason="worker lost; settled journal permits same-Attempt restart",
                        available_at=now,
                        increment_resume=True,
                    )
                    store.update_attempt_state(
                        lease.attempt_id,
                        expected_version=state.version,
                        values={
                            "grant_state": AttemptGrantState.GRANTED,
                            "runtime_mode": ExecutionMode.QUEUED,
                            "terminal_outcome": None,
                            "effect_uncertainty": False,
                            "blocker_reasons": (),
                        },
                    )
                    residual = tuple(
                        store.attempt_binding(lease.attempt_id).binding.obligation_references
                    )
                    if checkpoint is not None:
                        saved = checkpoint.semantic_manifest.get("residual_obligations")
                        if isinstance(saved, list) and all(
                            isinstance(item, str) for item in saved
                        ):
                            residual = tuple(saved)
                    store.insert_recovery_case(
                        ExecutionRecoveryCaseRecord(
                            id=uuid4(),
                            pwu_id=allocation.pwu_id,
                            attempt_id=allocation.attempt_id,
                            classification=(
                                RecoveryClassification.NO_EFFECT
                                if not effects
                                else RecoveryClassification.PARTIAL
                            ),
                            basis_checkpoint_id=(checkpoint.id if checkpoint else None),
                            observed_reality={
                                "worker_id": lease.worker_id,
                                "lease_epoch": lease.epoch,
                                "settled_effect_count": len(effects),
                            },
                            residual_obligations=residual,
                            effect_uncertainty=False,
                            resolution="same-Attempt restart admitted from settled journal",
                            created_at=now,
                            resolved_at=now,
                        )
                    )
                    self._append_event(
                        store,
                        pwu_id=allocation.pwu_id,
                        attempt_id=allocation.attempt_id,
                        event_type="NativeExecutionWorkerRestartAdmitted",
                        payload={
                            "expired_worker_epoch": lease.epoch,
                            "checkpoint_id": str(checkpoint.id) if checkpoint else None,
                            "settled_effect_count": len(effects),
                        },
                    )
                    reconciled.append(lease.attempt_id)
                    continue
                store.update_attempt_state(
                    lease.attempt_id,
                    expected_version=state.version,
                    values={
                        "grant_state": AttemptGrantState.FENCED,
                        "runtime_mode": ExecutionMode.RECONCILING,
                        "terminal_outcome": AttemptTerminalOutcome.UNKNOWN,
                        "effect_uncertainty": True,
                        "blocker_reasons": ("worker lease expired; effect reconciliation required",),
                    },
                )
                store.insert_recovery_case(
                    ExecutionRecoveryCaseRecord(
                        id=uuid4(),
                        pwu_id=allocation.pwu_id,
                        attempt_id=allocation.attempt_id,
                        classification=RecoveryClassification.EFFECT_UNRESOLVED,
                        observed_reality={
                            "worker_id": lease.worker_id,
                            "lease_epoch": lease.epoch,
                            "deadline": lease.deadline.isoformat(),
                        },
                        residual_obligations=("reconcile every in-flight effect",),
                        effect_uncertainty=True,
                        created_at=now,
                    )
                )
                reconciled.append(lease.attempt_id)
            uow.commit()
        return tuple(reconciled)

    @staticmethod
    def _append_event(
        store: NativeExecutionStore,
        *,
        pwu_id: UUID,
        attempt_id: UUID,
        event_type: str,
        payload: dict[str, object],
        causation_id: UUID | None = None,
    ) -> None:
        store.append_event(
            ExecutionEventRecord(
                id=uuid4(),
                pwu_id=pwu_id,
                attempt_id=attempt_id,
                sequence=store.next_event_sequence(pwu_id),
                event_type=event_type,
                payload=payload,
                causation_id=causation_id,
                correlation_id=attempt_id,
                created_at=_utcnow(),
            )
        )
