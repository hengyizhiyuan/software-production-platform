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
    ControlAction,
    ControlRequestCondition,
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
    QueueCondition,
    RecoveryClassification,
    ResultReadyClaimRecord,
    SchedulingDecision,
    SessionCondition,
    WorkerLeaseRecord,
    WorkerOffer,
    canonical_digest,
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
            entry.required_provider_profile in offer.provider_profiles
            and entry.required_resource_profile in offer.resource_profiles
            and set(entry.required_capabilities).issubset(offer.capability_identities)
        )


class NativeExecutorRuntimeService:
    """Coordinate durable native execution commands over existing Attempt authority."""

    scheduler_identity = "watt-native-executor"

    def __init__(
        self,
        database: Database,
        *,
        scheduler: FairCapacityScheduler | None = None,
        now=_utcnow,
    ) -> None:
        self.database = database
        self.scheduler = scheduler or FairCapacityScheduler()
        self._now = now

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
                store.insert_contract(command.contract)
                try:
                    source_vector_id = store.source_vector_id(binding.source_vector.digest or "")
                except NativeExecutionNotFound:
                    source_vector_id = uuid4()
                    store.insert_source_vector(source_vector_id, binding.source_vector)
                store.insert_resource_envelope(binding.pwu_id, binding.resource_envelope)
                store.insert_session(
                    ExecutionSessionRecord(
                        id=binding.session_id,
                        pwu_id=binding.pwu_id,
                        condition=SessionCondition.OPEN,
                        created_at=self._now(),
                    )
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

    def allocate(self, offer: WorkerOffer) -> ExecutionAllocationGrant | None:
        now = self._now()
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
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

    def heartbeat(
        self,
        grant: ExecutionAllocationGrant,
        *,
        lease_seconds: int = 30,
    ) -> None:
        now = self._now()
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
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
            if result.runtime_mode is ExecutionMode.PAUSED:
                next_queue = QueueCondition.CHECKPOINTED
                next_mode = ExecutionMode.PAUSED
                grant_state = AttemptGrantState.GRANTED
                terminal = None
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
                    self._now() + timedelta(seconds=30)
                    if next_queue is QueueCondition.WAITING_RESOURCE
                    and result.resource_retryable
                    else self._now() + timedelta(days=36500)
                    if next_queue is QueueCondition.WAITING_RESOURCE
                    else None
                ),
                increment_resume=next_queue is QueueCondition.WAITING_RESOURCE,
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
            self._append_event(
                store,
                pwu_id=allocation.pwu_id,
                attempt_id=allocation.attempt_id,
                event_type="NativeExecutionWorkerReturned",
                payload={
                    "runtime_mode": result.runtime_mode.value,
                    "terminal_outcome": terminal.value if terminal else None,
                    "checkpoint_id": str(result.final_checkpoint_id) if result.final_checkpoint_id else None,
                },
            )
            uow.commit()

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
            record = store.insert_control_request(
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
            if record.condition is not ControlRequestCondition.REQUESTED:
                return BackendControlReceipt(
                    command_id=command.command_id,
                    accepted=record.condition is ControlRequestCondition.APPLIED,
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
            worker_owned = queue is not None and queue.condition in {
                QueueCondition.ALLOCATED,
                QueueCondition.EXECUTING,
            }
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
            store.set_control_request_condition(
                command.command_id, ControlRequestCondition.APPLIED, applied_at=now
            )
            uow.commit()
            return BackendControlReceipt(
                command_id=command.command_id,
                accepted=True,
                condition=ControlRequestCondition.APPLIED,
                message=f"{command.action.value} request recorded",
                recorded_at=now,
            )

    def reconcile_expired_leases(self) -> tuple[UUID, ...]:
        """Fence crashed workers as UNKNOWN; never convert uncertainty into retry."""

        now = self._now()
        fenced: list[UUID] = []
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            for lease in store.expired_leases_locked(now):
                state = store.attempt_state(lease.attempt_id, lock=True)
                allocation = store.allocation(lease.allocation_id, lock=True)
                if state.worker_epoch != lease.epoch:
                    store.release_allocation(allocation.id, expired=True)
                    continue
                store.release_allocation(allocation.id, expired=True)
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
                fenced.append(lease.attempt_id)
            uow.commit()
        return tuple(fenced)

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
