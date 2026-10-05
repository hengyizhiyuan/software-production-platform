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
    ExecutionContextNotReady,
    NativeExecutionNotFound,
    NativeExecutionNotRunnable,
    ObservationConfidence,
    QueueCondition,
    QueueCapacityObservation,
    QueueProgressionState,
    RecoveryClassification,
    RepairabilityClassification,
    ResultReadyClaimRecord,
    validate_result_claim_evidence,
    SelfRefineActionRecord,
    SelfRefineEventRecord,
    SchedulingDecision,
    SessionCondition,
    StepCondition,
    StepKind,
    ResourceReservationCondition,
    UsageCertainty,
    WorkerLeaseRecord,
    WorkerOffer,
    WorkerRegistrationRecord,
    WorkerStatus,
    CloudExecutionRequest,
    CloudExecutionStatus,
    canonical_digest,
)
from spg.domain.refinement_contract import (
    RefinementClass, RefinementSignalKind, classify_refinement,
)
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.domain.production_intelligence import TaskContract
from spg.domain.verification import VerificationResultValue


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FairCapacityScheduler:
    """Pure fair-round-robin scheduler with FIFO groups and starvation aging."""

    policy_version = "fair-round-robin-v2"

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

        groups: dict[str, list[ExecutionQueueEntryRecord]] = defaultdict(list)
        for entry in eligible:
            groups[entry.fairness_group].append(entry)
        aged = {name: [item for item in items
                       if now - item.enqueued_at >= self.aging_threshold]
                for name, items in groups.items()}
        aged = {name: items for name, items in aged.items() if items}
        # Rotate aged Works too: a large old backlog cannot monopolize aging.
        selected_groups = aged or groups
        names = sorted(selected_groups)
        selected_group = next((name for name in names
                               if last_fairness_group is None or name > last_fairness_group), names[0])
        selected = min(selected_groups[selected_group], key=lambda item: (
            0 if aged else -item.priority, item.enqueued_at, str(item.id)))
        return SchedulingDecision(
            selected_queue_entry_id=selected.id,
            selected_fairness_group=selected_group,
            reason=("aging precedence; fair round-robin between Works; oldest aged entry within Work"
                    if aged else "fair round-robin between Works; explicit priority then FIFO within Work"),
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
        enforce_product_context: bool = True,
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
        self.enforce_product_context = enforce_product_context

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

        binding_basis = binding.model_dump(mode="json")
        if binding.production_context is None:
            binding_basis.pop("production_context")
        envelope_basis = binding_basis["resource_envelope"]
        if binding.resource_envelope.max_log_bytes == 65536:
            envelope_basis.pop("max_log_bytes")
        if binding.resource_envelope.max_artifact_bytes == 67108864:
            envelope_basis.pop("max_artifact_bytes")
        if binding.resource_envelope.max_workspace_bytes == 536870912:
            envelope_basis.pop("max_workspace_bytes")
        digest_basis = {
            "actor_identity": command.actor_identity,
            "fairness_group": command.fairness_group,
            "binding": binding_basis,
            "required_resource_profile": command.required_resource_profile,
        }
        # Preserve the pre-v1 digest for existing priority-zero commands so
        # retries across an upgrade remain idempotent.
        if command.priority:
            digest_basis["priority"] = command.priority
        request_digest = canonical_digest(digest_basis)
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
            priority=command.priority,
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
            product = ProductStore(uow.session)
            product_binding = product.runtime_binding_for_work_unit(binding.pwu_id)
            if product_binding is not None and self.enforce_product_context:
                context = binding.production_context
                payload = command.contract.contract_payload.get("completion_contract", {})
                task_payload = payload.get("task_contract") if isinstance(payload, dict) else None
                if context is None or not isinstance(task_payload, dict):
                    raise ExecutionContextNotReady("EXECUTION_CONTEXT_NOT_READY: Product Task Context missing")
                task = TaskContract.model_validate(task_payload)
                lineage = task.decision_context
                revision = product.current_work_reality_revision(product_binding.work_id)
                if (
                    lineage is None or revision is None
                    or context.work_id != product_binding.work_id
                    or context.work_reality_revision_id != revision.id
                    or context.task_contract_id != task.task_contract_id
                    or context.ecf_context_fingerprint != lineage.package_fingerprint
                    or context.irk_semantic_ir_id is None
                    or context.verification_requirements != tuple(
                        payload.get("verification_obligations", ())
                    )
                ):
                    raise ExecutionContextNotReady("EXECUTION_CONTEXT_NOT_READY: Product context changed")
                irk_ids = set()
                from spg.infrastructure.persistence.interaction_store import InteractionStore
                interactions = InteractionStore(uow.session)
                for source_revision in product.work_reality_revisions(product_binding.work_id):
                    if source_revision.source_assessment_id is None:
                        continue
                    assessment = interactions.assessment(source_revision.source_assessment_id)
                    if assessment is not None and assessment.semantic_ir is not None:
                        irk_ids.add(assessment.semantic_ir.id)
                if context.irk_semantic_ir_id not in irk_ids:
                    raise ExecutionContextNotReady("EXECUTION_CONTEXT_NOT_READY: IRK identity is not Work lineage")
                from spg.application.decision_context import assert_task_context_fresh
                assert_task_context_fresh(self.database, task)
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
                    store, pwu_id=binding.pwu_id, attempt_id=binding.attempt_id,
                    event_type="ExecutionRequestCreated",
                    payload={"execution_id": str(binding.attempt_id),
                             "task_contract_reference": str(binding.pwu_contract_version_id),
                             "priority": command.priority,
                             **({} if binding.production_context is None else {
                                 "irk_semantic_ir_id": str(binding.production_context.irk_semantic_ir_id),
                                 "ecf_context_fingerprint": binding.production_context.ecf_context_fingerprint,
                                 "task_contract_id": str(binding.production_context.task_contract_id),
                                 "repository_identity": binding.production_context.repository_identity,
                                 "repository_revision": binding.production_context.repository_revision,
                                 "workspace_id": str(binding.production_context.workspace_id),
                                 "verification_requirements": list(binding.production_context.verification_requirements),
                             })},
                    causation_id=command.command_id,
                )
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

    def register_worker(self, offer: WorkerOffer) -> WorkerRegistrationRecord:
        now = self._now()
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            record = store.register_worker(
                offer, heartbeat_at=now,
                expires_at=now + timedelta(seconds=offer.lease_seconds),
                status=WorkerStatus.REGISTERING,
            )
            uow.commit()
            return self._worker_capacity(store, record)

    def heartbeat_worker(self, offer: WorkerOffer) -> WorkerRegistrationRecord:
        now = self._now()
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            existing = store.worker_registration(offer.worker_id, lock=True)
            status = (
                WorkerStatus.DRAINING
                if existing and existing.status is WorkerStatus.DRAINING
                else WorkerStatus.BUSY
                if store.active_allocation_count(offer.worker_id)
                else WorkerStatus.READY
            )
            record = store.register_worker(
                offer, heartbeat_at=now,
                expires_at=now + timedelta(seconds=offer.lease_seconds),
                status=status,
            )
            uow.commit()
            return self._worker_capacity(store, record)

    def reconcile_worker_liveness(self) -> tuple[str, ...]:
        with self.database.unit_of_work() as uow:
            result = NativeExecutionStore(uow.session).offline_expired_workers(self._now())
            uow.commit()
            return result

    def record_runtime_limit(self, attempt_id: UUID, limit_seconds: int) -> None:
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            binding = store.attempt_binding(attempt_id)
            self._append_event(
                store, pwu_id=binding.pwu_id, attempt_id=attempt_id,
                event_type="ExecutionRuntimeLimitExceeded",
                payload={"max_active_seconds": limit_seconds,
                         "recovery": "lease expiry and effect reconciliation required"},
            )
            uow.commit()

    def record_production_observation(
        self, grant: ExecutionAllocationGrant, *, stage: str,
        worker_version: str, change_request: str,
        observation: dict[str, object],
    ) -> None:
        if stage not in {"WORKSPACE_PREPARED", "RESULT_OBSERVED"}:
            raise ValueError("unsupported production observation stage")
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            state = store.attempt_state(grant.allocation.attempt_id, lock=True)
            if state.worker_epoch != grant.allocation.lease_epoch:
                raise NativeExecutionConflict("production evidence worker epoch was fenced")
            self._append_event(
                store, pwu_id=grant.allocation.pwu_id,
                attempt_id=grant.allocation.attempt_id,
                event_type=("ExecutionWorkspacePrepared" if stage == "WORKSPACE_PREPARED"
                            else "ExecutionResultObserved"),
                payload={"worker_id": grant.allocation.worker_id,
                         "runtime_version": worker_version,
                         "change_request": change_request,
                         **observation},
            )
            uow.commit()

    def list_workers(self) -> tuple[WorkerRegistrationRecord, ...]:
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            return tuple(self._worker_capacity(store, item)
                         for item in store.all_worker_registrations())

    def _worker_capacity(self, store, record):
        execution_ids = store.active_execution_ids(record.worker_id)
        active = len(execution_ids)
        accepts = (record.expires_at > self._now() and record.status in {
            WorkerStatus.READY, WorkerStatus.BUSY})
        return record.model_copy(update={
            "active_execution_count": active,
            "active_execution_ids": execution_ids,
            "current_task_id": execution_ids[0] if active == 1 else None,
            "available_slots": max(0, record.capacity["max_concurrency"] - active) if accepts else 0,
            "safe_to_restart": record.status is WorkerStatus.DRAINING and active == 0,
        })

    def set_worker_draining(self, worker_id: str, *, draining: bool) -> WorkerRegistrationRecord:
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            previous = store.worker_registration(worker_id, lock=True)
            if previous is None:
                raise NativeExecutionNotFound(f"worker not registered: {worker_id}")
            if draining:
                status = WorkerStatus.DRAINING
            elif previous.expires_at <= self._now():
                status = WorkerStatus.OFFLINE
            elif store.active_allocation_count(worker_id):
                status = WorkerStatus.BUSY
            else:
                status = WorkerStatus.READY
            store.set_worker_status(worker_id, status,
                                    current_task_id=previous.current_task_id if status in {
                                        WorkerStatus.BUSY, WorkerStatus.DRAINING,
                                    } else None,
                                    now=self._now())
            result = store.worker_registration(worker_id)
            uow.commit()
            assert result is not None
            return self._worker_capacity(store, result)

    def worker_evidence(self, worker_id: str) -> tuple[dict[str, object], ...]:
        with self.database.unit_of_work() as uow:
            return tuple(NativeExecutionStore(uow.session).worker_events(worker_id))

    def execution_evidence(self, execution_id: UUID) -> tuple[dict[str, object], ...]:
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            binding = store.attempt_binding(execution_id)
            evidence: list[dict[str, object]] = []
            cursor = 0
            while True:
                batch = store.events_since(binding.pwu_id, after_sequence=cursor, limit=256)
                for event in batch:
                    if event.attempt_id == execution_id:
                        evidence.append({
                            "timestamp": event.created_at,
                            "source": "watt-native-executor",
                            "entity_id": execution_id,
                            "sequence": event.sequence,
                            "event_type": event.event_type,
                            "payload_reference": f"sha256:{canonical_digest(event.payload)}",
                            "payload": event.payload,
                        })
                if len(batch) < 256:
                    for record in self._attempt_verifications(
                        RuntimeStore(uow.session), binding.pwu_id, execution_id
                    ):
                        evidence.append({
                            "timestamp": record.created_at,
                            "source": record.provider.provider_identity,
                            "entity_id": execution_id,
                            "event_type": (
                                "ExecutionVerificationPassed"
                                if record.result is VerificationResultValue.PASS
                                else "ExecutionVerificationFailed"
                                if record.result is VerificationResultValue.FAIL
                                else "ExecutionVerificationUnknown"
                            ),
                            "payload_reference": f"sha256:{canonical_digest(record.model_dump(mode='json'))}",
                            "payload": {
                                "verification_record_id": str(record.id),
                                "obligation": record.obligation,
                                "result": record.result.value,
                                "subject_commit": record.proposed_commit_identity,
                            },
                        })
                    return tuple(evidence)
                cursor = batch[-1].sequence

    @staticmethod
    def _attempt_verifications(runtime: RuntimeStore, pwu_id: UUID, attempt_id: UUID):
        records = runtime.verification_records_for_work_unit(pwu_id)
        return tuple(record for record in records
                     if (snapshot := runtime.proposed_snapshot(record.proposed_snapshot_id)) is not None
                     and snapshot.attempt_id == attempt_id)

    def execution_request(self, execution_id: UUID) -> CloudExecutionRequest:
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            queue = store.latest_queue_for_attempt(execution_id)
            binding = store.attempt_binding(execution_id)
            state = store.attempt_state(execution_id)
            allocation = store.allocation_for_attempt(execution_id)
            lease = store.lease_for_attempt(execution_id)
            context = binding.binding.production_context
            verification_state = None
            if context is not None:
                records = self._attempt_verifications(
                    RuntimeStore(uow.session), queue.pwu_id, execution_id
                )
                observed = {item.obligation: item.result for item in records}
                if any(value is VerificationResultValue.FAIL for value in observed.values()):
                    verification_state = "FAILED"
                elif all(observed.get(item) is VerificationResultValue.PASS
                         for item in context.verification_requirements):
                    verification_state = "VERIFIED"
            if state.grant_state is AttemptGrantState.FENCED or state.runtime_mode is ExecutionMode.RECONCILING:
                status = CloudExecutionStatus.RECOVERY_REQUIRED
            elif queue.condition is QueueCondition.ALLOCATED:
                status = CloudExecutionStatus.ASSIGNED
            elif queue.condition in {QueueCondition.EXECUTING, QueueCondition.CHECKPOINTED}:
                status = CloudExecutionStatus.RUNNING
            elif queue.condition is QueueCondition.CANCELLED:
                status = CloudExecutionStatus.CANCELLED
            elif queue.condition is QueueCondition.COMPLETED:
                status = (
                    CloudExecutionStatus.FAILED
                    if verification_state == "FAILED"
                    else CloudExecutionStatus.COMPLETED
                    if store.work_unit_condition(queue.pwu_id) == "SATISFIED"
                    and (context is None or verification_state == "VERIFIED")
                    else CloudExecutionStatus.VERIFIED
                    if verification_state == "VERIFIED"
                    else
                    CloudExecutionStatus.VERIFYING
                    if state.terminal_outcome is AttemptTerminalOutcome.RESULT_READY
                    else CloudExecutionStatus.CANCELLED
                    if state.terminal_outcome in {AttemptTerminalOutcome.CANCELLED, AttemptTerminalOutcome.STOPPED}
                    else CloudExecutionStatus.FAILED
                )
            else:
                status = CloudExecutionStatus.QUEUED
            return CloudExecutionRequest(
                execution_id=execution_id, work_id=queue.work_id,
                task_contract_reference=binding.pwu_contract_version_id,
                priority=queue.priority, status=status, created_at=queue.enqueued_at,
                worker_id=allocation.worker_id if allocation else None,
                lease_expire_at=lease.deadline if lease else None,
                queue_entry_id=queue.id,
                recovery_reason=("VERIFICATION_FAILED" if verification_state == "FAILED"
                                 else "; ".join(state.blocker_reasons) or None),
                queue_condition=queue.condition, wait_reason=queue.wait_reason,
                wait_age_seconds=max(0, int((self._now() - queue.enqueued_at).total_seconds())),
                fairness_group=queue.fairness_group,
                scheduling_policy_version=self.scheduler.policy_version,
                scheduling=self._capacity_observation(
                    queue, store.live_worker_registrations(self._now()),
                    store.active_allocation_counts(), now=self._now(),
                    unavailable_after=timedelta(seconds=5)),
            )

    def allocate(self, offer: WorkerOffer) -> ExecutionAllocationGrant | None:
        now = self._now()
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            registration = store.worker_registration(offer.worker_id, lock=True)
            if registration is not None and registration.status is WorkerStatus.DRAINING:
                store.observe_worker_wait(offer.worker_id, "DRAINING", now=now)
                uow.commit()
                return None
            if registration is None or registration.expires_at <= now:
                registration = store.register_worker(
                    offer, heartbeat_at=now,
                    expires_at=now + timedelta(seconds=offer.lease_seconds),
                )
            if store.active_allocation_count(offer.worker_id) >= registration.capacity["max_concurrency"]:
                store.observe_worker_wait(offer.worker_id, "CAPACITY_FULL", now=now)
                uow.commit()
                return None
            cursor, cursor_version = store.scheduler_cursor_locked(
                self.scheduler_identity, self.scheduler.policy_version
            )
            # Serialize fairness decisions before locking candidates. Otherwise
            # another allocator's SKIP LOCKED rows can distort group rotation.
            entries = store.runnable_queue_locked(now, limit=None)
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
            store.set_worker_status(
                offer.worker_id, WorkerStatus.BUSY,
                current_task_id=selected.attempt_id, now=now,
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
                    "policy_version": self.scheduler.policy_version,
                    "work_id": str(selected.work_id), "pwu_id": str(selected.pwu_id),
                    "fairness_group": selected.fairness_group, "priority": selected.priority,
                    "queue_entry_id": str(selected.id), "enqueued_at": selected.enqueued_at.isoformat(),
                    "required_capabilities": list(selected.required_capabilities),
                    "lease_epoch": epoch, "lease_expires_at": deadline.isoformat(),
                    "active_execution_count_at_grant": store.active_allocation_count(offer.worker_id),
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
        occupied_counts: dict[str, int],
        *,
        now: datetime,
        unavailable_after: timedelta,
    ) -> QueueCapacityObservation:
        matching = tuple(
            registration
            for registration in registrations
            if self._registration_matches(entry, registration)
        )
        compatible = tuple(item for item in matching if item.status is not WorkerStatus.DRAINING)
        occupied = sum(occupied_counts.get(item.worker_id, 0) > 0 for item in compatible)
        slots = sum(item.capacity["max_concurrency"] for item in compatible)
        used = sum(occupied_counts.get(item.worker_id, 0) for item in compatible)
        available = sum(max(0, item.capacity["max_concurrency"] - occupied_counts.get(item.worker_id, 0))
                        for item in compatible)
        metrics = {"compatible_slots": slots, "occupied_slots": used,
                   "available_slots": available,
                   "draining_worker_count": len(matching) - len(compatible)}
        pending_conditions = {
            QueueCondition.QUEUED,
            QueueCondition.RETURNED_TO_QUEUE,
        }
        infrastructure_wait = (
            entry.condition is QueueCondition.WAITING_RESOURCE
            and (entry.wait_reason or "").startswith(self.infrastructure_wait_prefix)
        )
        if (entry.condition not in pending_conditions and not infrastructure_wait) or entry.available_at > now:
            return QueueCapacityObservation(
                progression_state=QueueProgressionState.NOT_APPLICABLE,
                reason=entry.wait_reason or "Queue allocation is not currently pending.",
                scheduler_alive=bool(compatible),
                compatible_worker_count=len(compatible),
                occupied_worker_count=occupied,
                observed_at=now,
                **metrics,
            )
        if not compatible:
            if matching:
                return QueueCapacityObservation(
                    progression_state=QueueProgressionState.CAPACITY_WAIT,
                    reason="Compatible execution workers are draining; new allocations wait.",
                    scheduler_alive=True, compatible_worker_count=0, occupied_worker_count=0,
                    observed_at=now, **metrics)
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
                **metrics,
            )
        if available == 0:
            return QueueCapacityObservation(
                progression_state=QueueProgressionState.CAPACITY_WAIT,
                reason="All compatible execution slots are currently occupied.",
                scheduler_alive=True,
                compatible_worker_count=len(compatible),
                occupied_worker_count=occupied,
                observed_at=now,
                **metrics,
            )
        return QueueCapacityObservation(
            progression_state=QueueProgressionState.SCHEDULING,
            reason="Compatible execution capacity is available and Watt is assigning it.",
            scheduler_alive=True,
            compatible_worker_count=len(compatible),
            occupied_worker_count=occupied,
            observed_at=now,
            **metrics,
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
            occupied = store.active_allocation_counts()
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
            occupied = store.active_allocation_counts()
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
                    self._append_event(store, pwu_id=entry.pwu_id, attempt_id=entry.attempt_id,
                        event_type="ExecutionCapacityUnavailable", payload={"reason": observation.reason,
                            "queue_entry_id": str(entry.id)})
                elif infrastructure_wait and observation.compatible_worker_count > 0:
                    store.set_queue_condition(
                        entry.id,
                        expected_version=entry.version,
                        condition=QueueCondition.QUEUED,
                        wait_reason=None,
                        available_at=now,
                    )
                    changed.append(entry.id)
                    self._append_event(store, pwu_id=entry.pwu_id, attempt_id=entry.attempt_id,
                        event_type="ExecutionCapacityRestored", payload={"queue_entry_id": str(entry.id)})
                elif entry.condition in {QueueCondition.QUEUED, QueueCondition.RETURNED_TO_QUEUE}:
                    reason = observation.reason if observation.progression_state is QueueProgressionState.CAPACITY_WAIT else None
                    if entry.wait_reason != reason:
                        store.set_queue_condition(entry.id, expected_version=entry.version,
                                                  condition=entry.condition, wait_reason=reason)
                        changed.append(entry.id)
                        self._append_event(store, pwu_id=entry.pwu_id, attempt_id=entry.attempt_id,
                            event_type="ExecutionCapacityWait" if reason else "ExecutionCapacityRestored",
                            payload={"queue_entry_id": str(entry.id), "reason": reason,
                                     "available_slots": observation.available_slots,
                                     "draining_worker_count": observation.draining_worker_count})
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
                    status=WorkerStatus.BUSY,
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
            try:
                validate_result_claim_evidence(result.result_claim)
            except ValueError:
                # Historical checkpoints and direct kernel ports must not crash
                # the Worker or turn a malformed provider claim into RESULT_READY.
                binding = store.attempt_binding(allocation.attempt_id)
                self._append_event(store, pwu_id=allocation.pwu_id, attempt_id=allocation.attempt_id,
                    event_type="NativeResultClaimRejected",
                    payload={"signal": "RESULT_CLAIM_EVIDENCE_INVALID",
                        "checkpoint_id": str(result.final_checkpoint_id) if result.final_checkpoint_id else None,
                        "tool_effects_preserved": True, "blind_tool_replay": False})
                result = result.model_copy(update={"runtime_mode": ExecutionMode.FINISHED,
                    "terminal_outcome": AttemptTerminalOutcome.UNABLE_TO_COMPLETE,
                    "result_claim": None, "resource_retryable": True,
                    "failure_family": "INVALID_PROVIDER_RESPONSE",
                    "summary": "Native result claim has invalid evidence references or output vector; no result-ready claim was admitted.",
                    "residual_obligations": tuple(binding.binding.obligation_references)})
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
            self._append_event(store, pwu_id=queue.pwu_id, attempt_id=queue.attempt_id,
                event_type="ExecutionCapacityReleased", payload={
                    "allocation_id": str(allocation.id), "worker_id": allocation.worker_id,
                    "lease_epoch": allocation.lease_epoch, "reason": result.runtime_mode.value})
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
                evidence_ids = tuple(UUID(str(item)) for item in raw_evidence)
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
            if terminal is not None:
                self._append_event(
                    store, pwu_id=allocation.pwu_id, attempt_id=allocation.attempt_id,
                    event_type=(
                        "ExecutionWorkerCompleted"
                        if terminal is AttemptTerminalOutcome.RESULT_READY
                        else "ExecutionCancelled"
                        if terminal is AttemptTerminalOutcome.CANCELLED
                        else "ExecutionFailed"
                    ),
                    payload={"terminal_outcome": terminal.value,
                             "verification_required": terminal is AttemptTerminalOutcome.RESULT_READY},
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
                if event.failure_family == "WORKER_LEASE_LOST":
                    # The original worker has been fenced and the same Attempt
                    # resumed. A subsequent repairable failure is part of that
                    # recovery trajectory, not proof that restart failed.
                    store.append_self_refine_action(SelfRefineActionRecord(
                        id=uuid4(), event_id=event.id, sequence=len(prior_actions) + 1,
                        created_at=now,
                        repair_action="Observe the resumed Attempt's distinct runtime failure",
                        observed_reality={"next_failure_family": family,
                                          "next_failure_signature": signature},
                        evidence_references=(f"native-attempt:{allocation.attempt_id}",),
                        outcome="RECOVERY_IN_PROGRESS",
                    ))
                    self._append_event(store, pwu_id=allocation.pwu_id,
                        attempt_id=allocation.attempt_id,
                        event_type="NativeExecutionWorkerRecoveryProgress",
                        payload={"refinement_event_id": str(event.id),
                            "resumed_attempt_id": str(allocation.attempt_id),
                            "next_failure_family": family,
                            "checkpoint_id": str(result.final_checkpoint_id)
                                if result.final_checkpoint_id else None})
                else:
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
                    affected_component=("native-executor/lease-recovery"
                        if family == "WORKER_LEASE_LOST" else "native-executor/provider"),
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
            if recovered and event.failure_family == "WORKER_LEASE_LOST":
                self._append_event(store, pwu_id=allocation.pwu_id,
                    attempt_id=allocation.attempt_id,
                    event_type="NativeExecutionWorkerRecoveryConfirmed",
                    payload={"refinement_event_id": str(event.id),
                        "resumed_attempt_id": str(allocation.attempt_id),
                        "checkpoint_id": str(result.final_checkpoint_id)
                            if result.final_checkpoint_id else None,
                        "terminal_outcome": result.terminal_outcome.value})
        self._confirm_closed_worker_recovery(
            store, allocation=allocation, queue=queue, result=result)
        return None, confidence

    def _confirm_closed_worker_recovery(self, store, *, allocation, queue,
        result: KernelRunResult) -> None:
        """Append recovery after an intervening tool failure closed the lease diagnosis.

        Tool receipt refinement owns its own failure event. It may close an open
        worker-loss event as historically FAILED while the same Attempt continues.
        Final Attempt Reality therefore needs a separate positive trajectory;
        the original failure row remains untouched.
        """
        if (result.runtime_mode is not ExecutionMode.FINISHED
                or result.terminal_outcome is not AttemptTerminalOutcome.RESULT_READY
                or queue.resume_count < 1):
            return
        events = store.self_refine_events_for_operation(
            allocation.attempt_id, failure_family="WORKER_LEASE_LOST")
        failed = next((item for item in events if item.final_result == "FAILED"), None)
        if failed is None or any(item.final_result == "LOCAL_OBLIGATION_RECOVERED"
                                 for item in events):
            return
        state = store.attempt_state(allocation.attempt_id)
        effects = store.effects_for_attempt(allocation.attempt_id)
        if (state.effect_uncertainty or any(effect.condition not in {
                EffectCondition.SETTLED, EffectCondition.FAILED} for effect in effects)):
            return
        now = self._now()
        recovery = SelfRefineEventRecord(
            id=uuid4(), work_id=failed.work_id, operation_id=allocation.attempt_id,
            created_at=now, updated_at=now,
            failure_family="WORKER_LEASE_LOST",
            failure_signature=sha256(
                f"WORKER_LEASE_LOST:recovery:{failed.id}".encode("utf-8")
            ).hexdigest(),
            signal_kind=RefinementSignalKind.EXECUTION_FAILURE,
            affected_component="native-executor/lease-recovery",
            expected_reality=failed.expected_reality,
            observed_reality={"historical_failure_event_id": str(failed.id),
                "resumed_attempt_id": str(allocation.attempt_id),
                "resume_count": queue.resume_count,
                "terminal_outcome": result.terminal_outcome.value,
                "effect_uncertainty": False,
                "settled_effect_count": sum(effect.condition is EffectCondition.SETTLED
                    for effect in effects)},
            diagnosis_summary="Same Attempt recovered after Worker loss and a distinct tool failure.",
            root_cause_classification="WORKER_LEASE_RECOVERY_CONFIRMED",
            repair_hypothesis="Use durable checkpoint and reconciled effects to resume the same Attempt.",
            evidence_references=(f"native-attempt:{allocation.attempt_id}",
                f"self-refine-event:{failed.id}"),
            repairability=RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE,
            observation_confidence=ObservationConfidence.OBSERVED_SUCCESS,
            diagnostic_evidence={"historical_failure_event_id": str(failed.id),
                "checkpoint_id": str(result.final_checkpoint_id)
                    if result.final_checkpoint_id else None},
        )
        store.insert_self_refine_event(recovery)
        for sequence, outcome in enumerate(("SAME_ATTEMPT_RESUMED",
                "EFFECTS_RECONCILED", "VERIFIED_PROGRESS", "RECOVERY_CONFIRMED"), 1):
            store.append_self_refine_action(SelfRefineActionRecord(
                id=uuid4(), event_id=recovery.id, sequence=sequence, created_at=now,
                repair_action=outcome.replace("_", " ").title(),
                observed_reality={"attempt_id": str(allocation.attempt_id),
                    "resume_count": queue.resume_count,
                    "terminal_outcome": result.terminal_outcome.value,
                    "effect_uncertainty": False},
                evidence_references=(f"native-attempt:{allocation.attempt_id}",),
                outcome=outcome,
            ))
        store.complete_self_refine_event(
            recovery.id, result="RECOVERED", resume_result="RESUMED",
            status="VERIFIED", elapsed_seconds=max(0, int((now - failed.created_at).total_seconds())),
            updated_at=now,
            compute_overhead={"inference_submissions": result.inference_submissions,
                "tool_effects": result.tool_effects},
            model_token_usage=store.observed_repair_model_usage(
                allocation.attempt_id, since=failed.created_at),
        )
        self._append_event(store, pwu_id=allocation.pwu_id,
            attempt_id=allocation.attempt_id,
            event_type="NativeExecutionWorkerRecoveryConfirmed",
            payload={"refinement_event_id": str(recovery.id),
                "historical_failure_event_id": str(failed.id),
                "resumed_attempt_id": str(allocation.attempt_id),
                "checkpoint_id": str(result.final_checkpoint_id)
                    if result.final_checkpoint_id else None,
                "terminal_outcome": result.terminal_outcome.value})

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
        if family in {"PROVIDER_TRANSPORT", "PROVIDER_CAPACITY", "RUNTIME_HEALTH", "STARTUP_HEALTH", "WORKER_LEASE_LOST"}:
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
            "WORKER_LEASE_LOST",
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
                self._append_event(
                    store, pwu_id=allocation.pwu_id, attempt_id=lease.attempt_id,
                    event_type="ExecutionRecoveryRequired",
                    payload={"worker_id": lease.worker_id, "lease_epoch": lease.epoch,
                             "lease_deadline": lease.deadline.isoformat()},
                )
                effects = tuple(store.effects_for_attempt(lease.attempt_id))
                steps = tuple(store.steps_for_attempt(lease.attempt_id))
                checkpoint = store.latest_checkpoint(lease.attempt_id)
                unresolved = any(
                    effect.condition not in {
                        EffectCondition.SETTLED,
                        EffectCondition.FAILED,
                    }
                    for effect in effects
                ) or any(
                    step.condition is StepCondition.RUNNING
                    and step.kind is not StepKind.INFERENCE
                    for step in steps
                )
                store.release_allocation(allocation.id, expired=True)
                if not unresolved:
                    # An interrupted inference has no Tool effect to reconcile.
                    # Retain unknown Provider consumption and reject late results;
                    # do not refund its budget or replay settled deliveries.
                    interrupted = tuple(
                        step for step in steps
                        if step.condition is StepCondition.RUNNING
                        and step.kind is StepKind.INFERENCE
                    )
                    binding = store.attempt_binding(lease.attempt_id).binding
                    for step in interrupted:
                        evidence = {"reason": "WORKER_LEASE_EXPIRED",
                                    "worker_epoch": lease.epoch,
                                    "response_observed": False,
                                    "tool_effect_uncertainty": False}
                        store.finish_step(
                            step.id, condition=StepCondition.INTERRUPTED.value,
                            result_payload=evidence,
                            result_digest=canonical_digest(evidence), finished_at=now,
                        )
                        store.settle_resource_usage(
                            envelope_id=binding.resource_envelope.envelope_id,
                            reservation_key=f"inference:{step.id}",
                            resource_type="inference_submission",
                            certainty=UsageCertainty.UNKNOWN,
                            condition=ResourceReservationCondition.UNKNOWN,
                            evidence=evidence,
                        )
                    queue = store.queue_entry(allocation.queue_entry_id)
                    restart_terminal, _ = self._record_self_refine(
                        store, allocation=allocation, queue=queue,
                        result=KernelRunResult(
                            runtime_mode=ExecutionMode.WAITING_RESOURCE,
                            final_checkpoint_id=checkpoint.id if checkpoint else None,
                            step_count=max((step.sequence for step in steps), default=0),
                            inference_submissions=len(interrupted), tool_effects=0,
                            summary="Worker lease expired with a settled effect journal",
                            failure_family="WORKER_LEASE_LOST",
                            observation_evidence={"stable_failure": True},
                        ),
                    )
                    if restart_terminal is not None:
                        store.set_queue_condition(queue.id, expected_version=queue.version,
                            condition=QueueCondition.COMPLETED,
                            wait_reason="Worker restart convergence budget exhausted")
                        store.update_attempt_state(lease.attempt_id,
                            expected_version=state.version, values={
                                "grant_state": AttemptGrantState.RELEASED,
                                "runtime_mode": ExecutionMode.FINISHED,
                                "terminal_outcome": restart_terminal,
                                "effect_uncertainty": False,
                                "blocker_reasons": ("Worker restart convergence budget exhausted",),
                            })
                        self._append_event(store, pwu_id=allocation.pwu_id,
                            attempt_id=allocation.attempt_id,
                            event_type="NativeExecutionWorkerRestartBudgetExhausted",
                            payload={"expired_worker_epoch":lease.epoch,
                                "checkpoint_id":str(checkpoint.id) if checkpoint else None})
                        reconciled.append(lease.attempt_id)
                        continue
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
                                "interrupted_inference_ids": [str(step.id) for step in interrupted],
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
                            "interrupted_inference_ids": [str(step.id) for step in interrupted],
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
