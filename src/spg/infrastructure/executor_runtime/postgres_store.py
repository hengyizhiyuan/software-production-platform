"""Transactional PostgreSQL store for Watt-native execution Reality."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from spg.domain.native_execution import (
    AllocationCondition,
    CheckpointBundleRecord,
    ControlRequestCondition,
    EffectReceiptRecord,
    ExecutionAllocationRecord,
    ExecutionBindingV2,
    ExecutionControlRequestRecord,
    ExecutionEffectRecord,
    ExecutionEventRecord,
    ExecutionEvidenceRecord,
    ExecutionQueueEntryRecord,
    ExecutionRecoveryCaseRecord,
    ExecutionSessionRecord,
    ExecutionStepRecord,
    NativeAttemptBindingRecord,
    NativeAttemptStateRecord,
    NativeExecutionConflict,
    NativeExecutionNotFound,
    PWUContractVersionRecord,
    QueueCondition,
    ResourceEnvelope,
    ResourceReservationCondition,
    ResourceUsageEntryRecord,
    ResultReadyClaimRecord,
    SourceVector,
    UsageCertainty,
    WorkerLeaseRecord,
    WorkspaceManifest,
    canonical_digest,
)
from spg.infrastructure.persistence.concurrency import update_versioned_row
from spg.infrastructure.persistence.native_execution_schema import (
    checkpoint_bundles,
    effect_receipts,
    event_outbox,
    execution_allocations,
    execution_control_requests,
    execution_effects,
    execution_events,
    execution_evidence,
    execution_recovery_cases,
    execution_resource_envelopes,
    execution_resource_usage,
    execution_sessions,
    execution_source_members,
    execution_source_vectors,
    execution_steps,
    execution_workspaces,
    executor_leases,
    executor_queue,
    executor_scheduler_state,
    native_attempt_bindings,
    native_attempt_states,
    pwu_contract_versions,
    result_ready_claims,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json(model: Any) -> Any:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json", exclude_none=False)
    return model


class NativeExecutionStore:
    """Persist native execution facts without owning their policy transitions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_contract(self, record: PWUContractVersionRecord) -> None:
        self.session.execute(insert(pwu_contract_versions).values(**record.model_dump()))

    def insert_source_vector(
        self,
        source_vector_id: UUID,
        vector: SourceVector,
        *,
        created_at: datetime | None = None,
    ) -> None:
        when = created_at or _utcnow()
        self.session.execute(
            insert(execution_source_vectors).values(
                id=source_vector_id,
                schema_version=vector.schema_version,
                digest=vector.digest,
                non_repository_assets=list(vector.non_repository_assets),
                created_at=when,
            )
        )
        for member in vector.members:
            self.session.execute(
                insert(execution_source_members).values(
                    id=uuid4(),
                    source_vector_id=source_vector_id,
                    **member.model_dump(mode="json"),
                )
            )

    def insert_resource_envelope(
        self,
        pwu_id: UUID,
        envelope: ResourceEnvelope,
        *,
        created_at: datetime | None = None,
    ) -> None:
        values = envelope.model_dump()
        values["id"] = values.pop("envelope_id")
        self.session.execute(
            insert(execution_resource_envelopes).values(
                pwu_id=pwu_id,
                created_at=created_at or _utcnow(),
                **values,
            )
        )

    def insert_session(self, record: ExecutionSessionRecord) -> None:
        values = record.model_dump()
        values["condition"] = record.condition.value
        self.session.execute(insert(execution_sessions).values(**values))

    def insert_workspace(
        self,
        manifest: WorkspaceManifest,
        *,
        condition: str,
        materialization_path: str,
        created_at: datetime | None = None,
    ) -> None:
        when = created_at or _utcnow()
        payload = manifest.model_dump(mode="json")
        self.session.execute(
            insert(execution_workspaces).values(
                id=manifest.workspace_id,
                pwu_id=manifest.pwu_id,
                attempt_id=manifest.attempt_id,
                source_vector_id=self.source_vector_id(manifest.source_vector_digest),
                condition=condition,
                host_storage_id=manifest.host_storage_id,
                materialization_path=materialization_path,
                manifest=payload,
                manifest_digest=canonical_digest(payload),
                version=1,
                created_at=when,
                updated_at=when,
            )
        )

    def insert_attempt_binding(self, record: NativeAttemptBindingRecord) -> None:
        values = record.model_dump(exclude={"binding"})
        values["binding_payload"] = record.binding.model_dump(mode="json")
        self.session.execute(insert(native_attempt_bindings).values(**values))

    def insert_attempt_state(self, record: NativeAttemptStateRecord) -> None:
        values = record.model_dump(mode="json")
        self.session.execute(insert(native_attempt_states).values(**values))

    def enqueue(self, record: ExecutionQueueEntryRecord) -> ExecutionQueueEntryRecord:
        values = record.model_dump(mode="json")
        statement = (
            pg_insert(executor_queue)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[executor_queue.c.command_id])
            .returning(executor_queue.c.id)
        )
        inserted_id = self.session.scalar(statement)
        if inserted_id is None:
            existing = self.queue_by_command(record.command_id)
            if existing.request_digest != record.request_digest:
                raise NativeExecutionConflict(
                    "queue command_id was already used with different semantics"
                )
            return existing
        return record

    def queue_by_command(self, command_id: UUID) -> ExecutionQueueEntryRecord:
        row = self.session.execute(
            select(executor_queue).where(executor_queue.c.command_id == command_id)
        ).mappings().one_or_none()
        if row is None:
            raise NativeExecutionNotFound(f"queue command not found: {command_id}")
        return ExecutionQueueEntryRecord.model_validate(dict(row))

    def queue_entry(self, entry_id: UUID) -> ExecutionQueueEntryRecord:
        row = self.session.execute(
            select(executor_queue).where(executor_queue.c.id == entry_id)
        ).mappings().one_or_none()
        if row is None:
            raise NativeExecutionNotFound(f"queue entry not found: {entry_id}")
        return ExecutionQueueEntryRecord.model_validate(dict(row))

    def runnable_queue_locked(
        self,
        now: datetime,
        *,
        limit: int = 256,
    ) -> list[ExecutionQueueEntryRecord]:
        rows = self.session.execute(
            select(executor_queue)
            .where(
                executor_queue.c.condition.in_(
                    [
                        QueueCondition.QUEUED.value,
                        QueueCondition.RETURNED_TO_QUEUE.value,
                        QueueCondition.WAITING_RESOURCE.value,
                    ]
                ),
                executor_queue.c.available_at <= now,
                executor_queue.c.resume_count < 3,
            )
            .order_by(executor_queue.c.enqueued_at, executor_queue.c.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).mappings()
        return [ExecutionQueueEntryRecord.model_validate(dict(row)) for row in rows]

    def set_queue_condition(
        self,
        entry_id: UUID,
        *,
        expected_version: int,
        condition: QueueCondition,
        wait_reason: str | None = None,
        available_at: datetime | None = None,
        increment_resume: bool = False,
    ) -> int:
        values: dict[str, object] = {
            "condition": condition.value,
            "wait_reason": wait_reason,
        }
        if available_at is not None:
            values["available_at"] = available_at
        if increment_resume:
            values["resume_count"] = executor_queue.c.resume_count + 1
        return update_versioned_row(
            self.session,
            executor_queue,
            identity={"id": entry_id},
            expected_version=expected_version,
            values=values,
        )

    def scheduler_cursor_locked(
        self,
        scheduler_identity: str,
        policy_version: str,
    ) -> tuple[str | None, int]:
        self.session.execute(
            pg_insert(executor_scheduler_state)
            .values(
                scheduler_identity=scheduler_identity,
                policy_version=policy_version,
                last_fairness_group=None,
                version=1,
                updated_at=_utcnow(),
            )
            .on_conflict_do_nothing(index_elements=[executor_scheduler_state.c.scheduler_identity])
        )
        row = self.session.execute(
            select(executor_scheduler_state)
            .where(executor_scheduler_state.c.scheduler_identity == scheduler_identity)
            .with_for_update()
        ).mappings().one()
        if row["policy_version"] != policy_version:
            raise NativeExecutionConflict("scheduler policy version differs from durable state")
        return row["last_fairness_group"], row["version"]

    def advance_scheduler_cursor(
        self,
        scheduler_identity: str,
        *,
        expected_version: int,
        fairness_group: str,
    ) -> int:
        return update_versioned_row(
            self.session,
            executor_scheduler_state,
            identity={"scheduler_identity": scheduler_identity},
            expected_version=expected_version,
            values={"last_fairness_group": fairness_group, "updated_at": _utcnow()},
        )

    def insert_allocation(self, record: ExecutionAllocationRecord) -> None:
        self.session.execute(
            insert(execution_allocations).values(**record.model_dump(mode="json"))
        )

    def insert_lease(self, lease_id: UUID, record: WorkerLeaseRecord) -> None:
        self.session.execute(
            insert(executor_leases).values(id=lease_id, **record.model_dump(mode="json"))
        )

    def allocation_for_attempt(self, attempt_id: UUID) -> ExecutionAllocationRecord | None:
        row = self.session.execute(
            select(execution_allocations)
            .where(
                execution_allocations.c.attempt_id == attempt_id,
                execution_allocations.c.condition.in_(
                    [AllocationCondition.ISSUED.value, AllocationCondition.ACTIVE.value]
                ),
            )
            .order_by(execution_allocations.c.issued_at.desc())
        ).mappings().first()
        return ExecutionAllocationRecord.model_validate(dict(row)) if row else None

    def allocation(self, allocation_id: UUID, *, lock: bool = False) -> ExecutionAllocationRecord:
        statement = select(execution_allocations).where(
            execution_allocations.c.id == allocation_id
        )
        if lock:
            statement = statement.with_for_update()
        row = self.session.execute(statement).mappings().one_or_none()
        if row is None:
            raise NativeExecutionNotFound(f"allocation not found: {allocation_id}")
        return ExecutionAllocationRecord.model_validate(dict(row))

    def set_allocation_condition(
        self,
        allocation_id: UUID,
        condition: AllocationCondition,
        *,
        released_at: datetime | None = None,
    ) -> None:
        result = self.session.execute(
            update(execution_allocations)
            .where(execution_allocations.c.id == allocation_id)
            .values(condition=condition.value, released_at=released_at)
        )
        if result.rowcount != 1:
            raise NativeExecutionNotFound(f"allocation not found: {allocation_id}")

    def lease_for_attempt(self, attempt_id: UUID) -> WorkerLeaseRecord | None:
        row = self.session.execute(
            select(executor_leases).where(
                executor_leases.c.attempt_id == attempt_id,
                executor_leases.c.released_at.is_(None),
            )
        ).mappings().one_or_none()
        if row is None:
            return None
        values = dict(row)
        values.pop("id")
        return WorkerLeaseRecord.model_validate(values)

    def heartbeat_lease(
        self,
        attempt_id: UUID,
        *,
        worker_id: str,
        epoch: int,
        token_digest: str,
        heartbeat_at: datetime,
        deadline: datetime,
    ) -> bool:
        result = self.session.execute(
            update(executor_leases)
            .where(
                executor_leases.c.attempt_id == attempt_id,
                executor_leases.c.worker_id == worker_id,
                executor_leases.c.epoch == epoch,
                executor_leases.c.token_digest == token_digest,
                executor_leases.c.released_at.is_(None),
                executor_leases.c.deadline >= heartbeat_at,
            )
            .values(heartbeat_at=heartbeat_at, deadline=deadline)
        )
        return result.rowcount == 1

    def release_allocation(self, allocation_id: UUID, *, expired: bool = False) -> None:
        now = _utcnow()
        condition = AllocationCondition.EXPIRED if expired else AllocationCondition.RELEASED
        self.session.execute(
            update(execution_allocations)
            .where(execution_allocations.c.id == allocation_id)
            .values(condition=condition.value, released_at=now)
        )
        self.session.execute(
            update(executor_leases)
            .where(
                executor_leases.c.allocation_id == allocation_id,
                executor_leases.c.released_at.is_(None),
            )
            .values(released_at=now)
        )

    def attempt_state(self, attempt_id: UUID, *, lock: bool = False) -> NativeAttemptStateRecord:
        statement = select(native_attempt_states).where(
            native_attempt_states.c.attempt_id == attempt_id
        )
        if lock:
            statement = statement.with_for_update()
        row = self.session.execute(statement).mappings().one_or_none()
        if row is None:
            raise NativeExecutionNotFound(f"native Attempt state not found: {attempt_id}")
        return NativeAttemptStateRecord.model_validate(dict(row))

    def update_attempt_state(
        self,
        attempt_id: UUID,
        *,
        expected_version: int,
        values: Mapping[str, Any],
    ) -> int:
        serialized = {
            key: value.value if hasattr(value, "value") else list(value) if isinstance(value, tuple) else value
            for key, value in values.items()
        }
        serialized["updated_at"] = _utcnow()
        return update_versioned_row(
            self.session,
            native_attempt_states,
            identity={"attempt_id": attempt_id},
            expected_version=expected_version,
            values=serialized,
        )

    def insert_step(self, record: ExecutionStepRecord) -> None:
        self.session.execute(insert(execution_steps).values(**record.model_dump(mode="json")))

    def finish_step(
        self,
        step_id: UUID,
        *,
        condition: str,
        result_payload: Mapping[str, Any],
        result_digest: str,
        finished_at: datetime,
    ) -> None:
        result = self.session.execute(
            update(execution_steps)
            .where(execution_steps.c.id == step_id)
            .values(
                condition=condition,
                result_payload=dict(result_payload),
                result_digest=result_digest,
                finished_at=finished_at,
            )
        )
        if result.rowcount != 1:
            raise NativeExecutionNotFound(f"execution step not found: {step_id}")

    def insert_effect(self, record: ExecutionEffectRecord) -> None:
        self.session.execute(insert(execution_effects).values(**record.model_dump(mode="json")))

    def set_effect_condition(self, effect_id: UUID, condition: str) -> None:
        result = self.session.execute(
            update(execution_effects)
            .where(execution_effects.c.id == effect_id)
            .values(condition=condition)
        )
        if result.rowcount != 1:
            raise NativeExecutionNotFound(f"execution effect not found: {effect_id}")

    def insert_effect_receipt(self, record: EffectReceiptRecord) -> EffectReceiptRecord:
        values = record.model_dump(mode="json")
        statement = (
            pg_insert(effect_receipts)
            .values(**values)
            .on_conflict_do_nothing(constraint="uq_effect_receipts_delivery")
            .returning(effect_receipts.c.id)
        )
        inserted_id = self.session.scalar(statement)
        if inserted_id is None:
            row = self.session.execute(
                select(effect_receipts).where(
                    effect_receipts.c.effect_id == record.effect_id,
                    effect_receipts.c.delivery_id == record.delivery_id,
                )
            ).mappings().one()
            existing = EffectReceiptRecord.model_validate(dict(row))
            if existing.output_digest != record.output_digest:
                raise NativeExecutionConflict("effect delivery identity was reused with new output")
            return existing
        return record

    def insert_checkpoint(self, record: CheckpointBundleRecord) -> None:
        self.session.execute(
            insert(checkpoint_bundles).values(**record.model_dump(mode="json"))
        )

    def advance_session_checkpoint(
        self,
        session_id: UUID,
        *,
        checkpoint_id: UUID,
        working_state_version: int,
    ) -> None:
        row = self.session.execute(
            select(execution_sessions.c.version).where(execution_sessions.c.id == session_id).with_for_update()
        ).one_or_none()
        if row is None:
            raise NativeExecutionNotFound(f"execution session not found: {session_id}")
        update_versioned_row(
            self.session,
            execution_sessions,
            identity={"id": session_id},
            expected_version=row[0],
            values={
                "current_checkpoint_id": checkpoint_id,
                "current_working_state_version": working_state_version,
            },
        )

    def insert_evidence(self, record: ExecutionEvidenceRecord) -> None:
        self.session.execute(insert(execution_evidence).values(**record.model_dump(mode="json")))

    def insert_result_ready_claim(self, record: ResultReadyClaimRecord) -> None:
        self.session.execute(
            insert(result_ready_claims).values(**record.model_dump(mode="json"))
        )

    def insert_resource_usage(self, record: ResourceUsageEntryRecord) -> ResourceUsageEntryRecord:
        values = record.model_dump(mode="json")
        statement = (
            pg_insert(execution_resource_usage)
            .values(**values)
            .on_conflict_do_nothing(constraint="uq_execution_resource_usage_reservation")
            .returning(execution_resource_usage.c.id)
        )
        inserted_id = self.session.scalar(statement)
        if inserted_id is None:
            row = self.session.execute(
                select(execution_resource_usage).where(
                    execution_resource_usage.c.envelope_id == record.envelope_id,
                    execution_resource_usage.c.reservation_key == record.reservation_key,
                    execution_resource_usage.c.resource_type == record.resource_type,
                )
            ).mappings().one()
            existing = ResourceUsageEntryRecord.model_validate(dict(row))
            if existing.amount != record.amount:
                raise NativeExecutionConflict("resource reservation key was reused")
            return existing
        return record

    def settle_resource_usage(
        self,
        *,
        envelope_id: UUID,
        reservation_key: str,
        resource_type: str,
        certainty: UsageCertainty,
        condition: ResourceReservationCondition,
        evidence: dict[str, object],
    ) -> None:
        result = self.session.execute(
            update(execution_resource_usage)
            .where(
                execution_resource_usage.c.envelope_id == envelope_id,
                execution_resource_usage.c.reservation_key == reservation_key,
                execution_resource_usage.c.resource_type == resource_type,
                execution_resource_usage.c.condition
                == ResourceReservationCondition.RESERVED.value,
            )
            .values(
                certainty=certainty.value,
                condition=condition.value,
                evidence=evidence,
            )
        )
        if result.rowcount != 1:
            raise NativeExecutionConflict("resource reservation is missing or already settled")

    def insert_control_request(
        self, record: ExecutionControlRequestRecord
    ) -> ExecutionControlRequestRecord:
        statement = (
            pg_insert(execution_control_requests)
            .values(**record.model_dump(mode="json"))
            .on_conflict_do_nothing(index_elements=[execution_control_requests.c.command_id])
            .returning(execution_control_requests.c.id)
        )
        inserted_id = self.session.scalar(statement)
        if inserted_id is None:
            row = self.session.execute(
                select(execution_control_requests).where(
                    execution_control_requests.c.command_id == record.command_id
                )
            ).mappings().one()
            existing = ExecutionControlRequestRecord.model_validate(dict(row))
            if existing.request_digest != record.request_digest:
                raise NativeExecutionConflict("control command_id was reused")
            return existing
        return record

    def set_control_request_condition(
        self,
        command_id: UUID,
        condition: ControlRequestCondition,
        *,
        applied_at: datetime | None = None,
    ) -> None:
        result = self.session.execute(
            update(execution_control_requests)
            .where(execution_control_requests.c.command_id == command_id)
            .values(condition=condition.value, applied_at=applied_at)
        )
        if result.rowcount != 1:
            raise NativeExecutionNotFound(f"control request not found: {command_id}")

    def insert_recovery_case(self, record: ExecutionRecoveryCaseRecord) -> None:
        self.session.execute(
            insert(execution_recovery_cases).values(**record.model_dump(mode="json"))
        )

    def append_event(self, record: ExecutionEventRecord) -> None:
        """Persist event and outbox atomically in the caller's transaction."""

        self.session.execute(insert(execution_events).values(**record.model_dump(mode="json")))
        self.session.execute(
            insert(event_outbox).values(
                event_id=record.id,
                condition="PENDING",
                attempt_count=0,
                available_at=record.created_at,
            )
        )

    def next_event_sequence(self, pwu_id: UUID) -> int:
        value = self.session.scalar(
            select(func.coalesce(func.max(execution_events.c.sequence), 0)).where(
                execution_events.c.pwu_id == pwu_id
            )
        )
        return int(value or 0) + 1

    def events_since(
        self,
        pwu_id: UUID,
        *,
        after_sequence: int = 0,
        limit: int = 256,
    ) -> Sequence[ExecutionEventRecord]:
        rows = self.session.execute(
            select(execution_events)
            .where(
                execution_events.c.pwu_id == pwu_id,
                execution_events.c.sequence > after_sequence,
            )
            .order_by(execution_events.c.sequence)
            .limit(limit)
        ).mappings()
        return tuple(ExecutionEventRecord.model_validate(dict(row)) for row in rows)

    def source_vector_id(self, digest: str) -> UUID:
        value = self.session.scalar(
            select(execution_source_vectors.c.id).where(
                execution_source_vectors.c.digest == digest
            )
        )
        if value is None:
            raise NativeExecutionNotFound(f"source vector not found: {digest}")
        return value

    def attempt_binding(self, attempt_id: UUID) -> NativeAttemptBindingRecord:
        row = self.session.execute(
            select(native_attempt_bindings).where(
                native_attempt_bindings.c.attempt_id == attempt_id
            )
        ).mappings().one_or_none()
        if row is None:
            raise NativeExecutionNotFound(f"native Attempt binding not found: {attempt_id}")
        values = dict(row)
        values["binding"] = values.pop("binding_payload")
        return NativeAttemptBindingRecord.model_validate(values)

    def contract(self, contract_id: UUID) -> PWUContractVersionRecord:
        row = self.session.execute(
            select(pwu_contract_versions).where(pwu_contract_versions.c.id == contract_id)
        ).mappings().one_or_none()
        if row is None:
            raise NativeExecutionNotFound(f"PWU contract not found: {contract_id}")
        return PWUContractVersionRecord.model_validate(dict(row))

    def queue_for_attempt(self, attempt_id: UUID) -> ExecutionQueueEntryRecord | None:
        row = self.session.execute(
            select(executor_queue)
            .where(executor_queue.c.attempt_id == attempt_id)
            .order_by(executor_queue.c.enqueued_at.desc())
        ).mappings().first()
        return ExecutionQueueEntryRecord.model_validate(dict(row)) if row else None

    def list_queue(self, *, work_id: UUID | None = None) -> Sequence[ExecutionQueueEntryRecord]:
        statement = select(executor_queue)
        if work_id is not None:
            statement = statement.where(executor_queue.c.work_id == work_id)
        rows = self.session.execute(
            statement.order_by(executor_queue.c.enqueued_at, executor_queue.c.id)
        ).mappings()
        return tuple(ExecutionQueueEntryRecord.model_validate(dict(row)) for row in rows)

    def steps_for_attempt(self, attempt_id: UUID) -> Sequence[ExecutionStepRecord]:
        rows = self.session.execute(
            select(execution_steps)
            .where(execution_steps.c.attempt_id == attempt_id)
            .order_by(execution_steps.c.sequence)
        ).mappings()
        return tuple(ExecutionStepRecord.model_validate(dict(row)) for row in rows)

    def evidence_for_attempt(self, attempt_id: UUID) -> Sequence[ExecutionEvidenceRecord]:
        rows = self.session.execute(
            select(execution_evidence)
            .where(execution_evidence.c.attempt_id == attempt_id)
            .order_by(execution_evidence.c.created_at)
        ).mappings()
        return tuple(ExecutionEvidenceRecord.model_validate(dict(row)) for row in rows)

    def effects_for_attempt(self, attempt_id: UUID) -> Sequence[ExecutionEffectRecord]:
        rows = self.session.execute(
            select(execution_effects)
            .join(execution_steps, execution_steps.c.id == execution_effects.c.step_id)
            .where(execution_steps.c.attempt_id == attempt_id)
            .order_by(execution_steps.c.sequence, execution_effects.c.proposal_index)
        ).mappings()
        return tuple(ExecutionEffectRecord.model_validate(dict(row)) for row in rows)

    def latest_checkpoint(self, attempt_id: UUID) -> CheckpointBundleRecord | None:
        row = self.session.execute(
            select(checkpoint_bundles)
            .where(checkpoint_bundles.c.attempt_id == attempt_id)
            .order_by(checkpoint_bundles.c.step_sequence.desc())
        ).mappings().first()
        return CheckpointBundleRecord.model_validate(dict(row)) if row else None

    def expired_leases_locked(self, now: datetime) -> list[WorkerLeaseRecord]:
        rows = self.session.execute(
            select(executor_leases)
            .where(
                executor_leases.c.released_at.is_(None),
                executor_leases.c.deadline < now,
            )
            .with_for_update(skip_locked=True)
        ).mappings()
        records: list[WorkerLeaseRecord] = []
        for row in rows:
            values = dict(row)
            values.pop("id")
            records.append(WorkerLeaseRecord.model_validate(values))
        return records
