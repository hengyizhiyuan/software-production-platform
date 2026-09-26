"""Transactional PostgreSQL store for Watt-native execution Reality."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from math import ceil
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
    ObservationConfidence,
    PWUContractVersionRecord,
    QueueCondition,
    RepairabilityClassification,
    ResourceEnvelope,
    ResourceReservationCondition,
    ResourceUsageEntryRecord,
    ResultReadyClaimRecord,
    SelfRefineActionRecord,
    SelfRefineEventRecord,
    SourceVector,
    StepCondition,
    StepKind,
    ToolExecutionResult,
    UsageCertainty,
    WorkerLeaseRecord,
    WorkerOffer,
    WorkerRegistrationRecord,
    WorkspaceManifest,
    canonical_digest,
)
from spg.domain.refinement_contract import (
    RefinementClass, RefinementSignalKind, classify_refinement,
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
    executor_worker_registrations,
    native_attempt_bindings,
    native_attempt_states,
    pwu_contract_versions,
    result_ready_claims,
    self_refine_actions,
    self_refine_events,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json(model: Any) -> Any:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json", exclude_none=False)
    return model


def _p95(values: list[int]) -> int:
    return sorted(values)[ceil(0.95 * len(values)) - 1] if values else 0


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

    def execution_session(self, session_id: UUID) -> ExecutionSessionRecord | None:
        row = self.session.execute(
            select(execution_sessions).where(execution_sessions.c.id == session_id)
        ).mappings().one_or_none()
        return (
            ExecutionSessionRecord.model_validate(dict(row))
            if row is not None
            else None
        )

    def close_session(self, session_id: UUID, *, closed_at: datetime) -> None:
        row = self.session.execute(
            select(execution_sessions.c.version)
            .where(execution_sessions.c.id == session_id)
            .with_for_update()
        ).one_or_none()
        if row is None:
            raise NativeExecutionNotFound(f"execution session not found: {session_id}")
        update_versioned_row(
            self.session,
            execution_sessions,
            identity={"id": session_id},
            expected_version=row[0],
            values={"condition": "CLOSED", "closed_at": closed_at},
        )

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
                # resume_count is incremented when a retry is scheduled.  A
                # value of 3 therefore represents the third (and final)
                # automatic retry, which must remain runnable.
                executor_queue.c.resume_count <= 3,
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

    def register_worker(
        self,
        offer: WorkerOffer,
        *,
        heartbeat_at: datetime,
        expires_at: datetime,
    ) -> WorkerRegistrationRecord:
        values = {
            "worker_id": offer.worker_id,
            "worker_profile": offer.worker_profile,
            "provider_profiles": list(offer.provider_profiles),
            "resource_profiles": list(offer.resource_profiles),
            "capability_identities": list(offer.capability_identities),
            "heartbeat_at": heartbeat_at,
            "expires_at": expires_at,
        }
        self.session.execute(
            pg_insert(executor_worker_registrations)
            .values(**values, version=1)
            .on_conflict_do_update(
                index_elements=[executor_worker_registrations.c.worker_id],
                set_={
                    **values,
                    "version": executor_worker_registrations.c.version + 1,
                },
            )
        )
        row = self.session.execute(
            select(executor_worker_registrations).where(
                executor_worker_registrations.c.worker_id == offer.worker_id
            )
        ).mappings().one()
        return WorkerRegistrationRecord.model_validate(dict(row))

    def live_worker_registrations(self, now: datetime) -> list[WorkerRegistrationRecord]:
        rows = self.session.execute(
            select(executor_worker_registrations)
            .where(executor_worker_registrations.c.expires_at > now)
            .order_by(executor_worker_registrations.c.worker_id)
        ).mappings()
        return [WorkerRegistrationRecord.model_validate(dict(row)) for row in rows]

    def active_allocation_worker_ids(self) -> set[str]:
        rows = self.session.scalars(
            select(execution_allocations.c.worker_id).where(
                execution_allocations.c.condition.in_(
                    [AllocationCondition.ISSUED.value, AllocationCondition.ACTIVE.value]
                )
            )
        )
        return set(rows)

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
        existing_row = self.session.execute(
            select(execution_resource_usage).where(
                execution_resource_usage.c.envelope_id == record.envelope_id,
                execution_resource_usage.c.reservation_key == record.reservation_key,
                execution_resource_usage.c.resource_type == record.resource_type,
            )
        ).mappings().one_or_none()
        if existing_row is not None:
            existing = ResourceUsageEntryRecord.model_validate(dict(existing_row))
            if existing.amount != record.amount:
                raise NativeExecutionConflict("resource reservation key was reused")
            return existing

        envelope = self.session.execute(
            select(execution_resource_envelopes)
            .where(execution_resource_envelopes.c.id == record.envelope_id)
        ).mappings().one_or_none()
        if envelope is None:
            raise NativeExecutionNotFound(
                f"resource envelope not found: {record.envelope_id}"
            )
        pwu_id = envelope["pwu_id"]
        # Serialize every envelope for the PWU so a successor cannot reset or
        # race the finite resource pool with a new envelope identity.
        self.session.execute(
            select(execution_resource_envelopes.c.id)
            .where(execution_resource_envelopes.c.pwu_id == pwu_id)
            .order_by(execution_resource_envelopes.c.id)
            .with_for_update()
        ).all()
        cap_column = {
            "inference_submission": execution_resource_envelopes.c.max_inference_submissions,
            "tool_effect": execution_resource_envelopes.c.max_tool_effects,
            "cost_unit": execution_resource_envelopes.c.max_cost_units,
        }.get(record.resource_type)
        caps = ()
        if cap_column is not None:
            caps = tuple(
                value
                for value in self.session.scalars(
                    select(cap_column).where(
                        execution_resource_envelopes.c.pwu_id == pwu_id,
                        cap_column.is_not(None),
                    )
                )
                if value is not None
            )
        if caps:
            consumed = self.session.scalar(
                select(func.coalesce(func.sum(execution_resource_usage.c.amount), 0))
                .select_from(
                    execution_resource_usage.join(
                        execution_resource_envelopes,
                        execution_resource_usage.c.envelope_id
                        == execution_resource_envelopes.c.id,
                    )
                )
                .where(
                    execution_resource_envelopes.c.pwu_id == pwu_id,
                    execution_resource_usage.c.resource_type == record.resource_type,
                    execution_resource_usage.c.condition
                    != ResourceReservationCondition.RELEASED.value,
                )
            )
            if int(consumed or 0) + record.amount > min(caps):
                raise NativeExecutionConflict("PWU resource pool is exhausted")
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
    ) -> tuple[ExecutionControlRequestRecord, bool]:
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
            return existing, False
        return record, True

    def pending_control_request(
        self,
        attempt_id: UUID,
        *,
        action: str | None = None,
    ) -> ExecutionControlRequestRecord | None:
        statement = select(execution_control_requests).where(
            execution_control_requests.c.attempt_id == attempt_id,
            execution_control_requests.c.condition
            == ControlRequestCondition.REQUESTED.value,
        )
        if action is not None:
            statement = statement.where(execution_control_requests.c.action == action)
        row = self.session.execute(
            statement.order_by(execution_control_requests.c.created_at.desc())
        ).mappings().first()
        return (
            ExecutionControlRequestRecord.model_validate(dict(row))
            if row is not None
            else None
        )

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

    def open_self_refine_event(self, operation_id: UUID) -> SelfRefineEventRecord | None:
        row = self.session.execute(
            select(self_refine_events)
            .where(self_refine_events.c.operation_id == operation_id)
            .where(self_refine_events.c.status == "OPEN")
            .order_by(self_refine_events.c.created_at.desc())
            .limit(1)
        ).mappings().first()
        return None if row is None else SelfRefineEventRecord.model_validate(dict(row))

    def insert_self_refine_event(self, event: SelfRefineEventRecord) -> None:
        self.session.execute(insert(self_refine_events).values(**event.model_dump(mode="json")))

    def record_bounded_refinement(
        self, *, work_id: UUID, operation_id: UUID, component: str,
        signal_kind: RefinementSignalKind, signature_basis: str,
        evidence_references: tuple[str, ...], converged: bool,
        attempt_count: int, elapsed_seconds: int = 0,
        model_token_usage: dict[str, Any] | None = None,
        authority_required: bool = False,
        diagnostic_evidence: dict[str, Any] | None = None,
        superseded: bool = False,
    ) -> SelfRefineEventRecord:
        """Persist a completed candidate correction without inventing an incident.

        The caller retains its candidate, validator and authority policy. Only
        bounded diagnostic metadata crosses into the shared observation store.
        """
        if attempt_count < 2:
            raise ValueError("A refinement observation requires at least two candidate attempts")
        now = _utcnow()
        event_id = uuid4()
        signature = sha256(
            f"{component}:{signal_kind.value}:{signature_basis}".encode("utf-8")
        ).hexdigest()
        prior = self.prior_self_refine_matches(signature, before_event_id=event_id)
        refinement_class = classify_refinement(
            converged=converged, same_signature_count=1,
            prior_occurrences=prior, budget_exhausted=not converged and not superseded,
            authority_required=authority_required,
        )
        event = SelfRefineEventRecord(
            id=event_id, work_id=work_id, operation_id=operation_id,
            created_at=now, updated_at=now,
            failure_family=signal_kind.value,
            failure_signature=signature,
            refinement_class=refinement_class, signal_kind=signal_kind,
            affected_component=component,
            expected_reality={}, observed_reality={},
            diagnosis_summary="A model candidate required bounded validation feedback.",
            root_cause_classification=signal_kind.value,
            repair_hypothesis="Revalidate a revised candidate against the unchanged governed basis.",
            evidence_references=evidence_references,
            repairability=(
                RepairabilityClassification.REQUIRES_HUMAN_DECISION
                if authority_required else RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE
            ),
            observation_confidence=(
                ObservationConfidence.OBSERVED_SUCCESS if converged else
                ObservationConfidence.INCONCLUSIVE if superseded else
                ObservationConfidence.CONFIRMED_FAILURE
            ),
            diagnostic_evidence=diagnostic_evidence or {},
            known_failure_match=prior > 0,
            final_result="RECOVERED" if converged else "SUPERSEDED" if superseded else "ESCALATED",
            work_resume_result="RESUMED" if converged else "REORIENTED" if superseded else "NOT_RESUMED",
            extra_elapsed_seconds=max(0, elapsed_seconds),
            budget_decision={
                "attempt_count": attempt_count, "bounded": True,
                "human_escalated": authority_required and not converged,
            },
            model_token_usage=model_token_usage or {}, compute_overhead={},
            platform_improvement_candidate_ref=(
                f"refinement-signature:{signature}"
                if refinement_class in {
                    RefinementClass.DEGRADING_OR_RECURRING_REFINEMENT,
                    RefinementClass.SYSTEMIC_OR_NON_CONVERGING_INCIDENT,
                }
                else None
            ),
            status="VERIFIED" if converged else "MITIGATED",
        )
        self.insert_self_refine_event(event)
        self.append_self_refine_action(SelfRefineActionRecord(
            id=uuid4(), event_id=event_id, sequence=1, created_at=now,
            repair_action="Attempt bounded candidate refinement against the same input",
            observed_reality={"attempt_count": attempt_count, "signal_kind": signal_kind.value},
            evidence_references=evidence_references,
            outcome="RECOVERED" if converged else "SUPERSEDED" if superseded else "ESCALATED",
        ))
        return event

    def prior_self_refine_matches(self, signature: str, *, before_event_id: UUID) -> int:
        return int(self.session.scalar(
            select(func.count())
            .select_from(self_refine_events)
            .where(self_refine_events.c.failure_signature == signature)
            .where(self_refine_events.c.id != before_event_id)
        ) or 0)

    def append_self_refine_action(self, action: SelfRefineActionRecord) -> None:
        self.session.execute(insert(self_refine_actions).values(**action.model_dump(mode="json")))

    def update_self_refine_budget(self, event_id: UUID, decision: dict[str, Any], *, updated_at: datetime) -> None:
        changed = self.session.execute(
            update(self_refine_events)
            .where(self_refine_events.c.id == event_id)
            .where(self_refine_events.c.status == "OPEN")
            .values(budget_decision=decision, updated_at=updated_at)
        )
        if changed.rowcount != 1:
            raise NativeExecutionConflict("Self-Refine event is no longer open")

    def advance_self_refine_repairability(
        self, event_id: UUID, *, repairability: RepairabilityClassification,
        diagnostic_evidence: dict[str, Any], updated_at: datetime,
    ) -> None:
        changed = self.session.execute(
            update(self_refine_events)
            .where(self_refine_events.c.id == event_id)
            .where(self_refine_events.c.status == "OPEN")
            .where(self_refine_events.c.repairability ==
                   RepairabilityClassification.REPAIRABLE_WITH_SUFFICIENT_EVIDENCE.value)
            .values(repairability=repairability.value,
                    diagnostic_evidence=diagnostic_evidence, updated_at=updated_at)
        )
        if changed.rowcount != 1:
            raise NativeExecutionConflict("Self-Refine evidence boundary changed")

    def self_refine_actions(self, event_id: UUID) -> tuple[SelfRefineActionRecord, ...]:
        rows = self.session.execute(
            select(self_refine_actions)
            .where(self_refine_actions.c.event_id == event_id)
            .order_by(self_refine_actions.c.sequence)
        ).mappings().all()
        return tuple(SelfRefineActionRecord.model_validate(dict(row)) for row in rows)

    def complete_self_refine_event(
        self, event_id: UUID, *, result: str, resume_result: str,
        status: str, elapsed_seconds: int, updated_at: datetime,
        compute_overhead: dict[str, Any],
        model_token_usage: dict[str, Any] | None = None,
    ) -> None:
        event = self.self_refine_event(event_id)
        values: dict[str, Any] = {
            "final_result": result,
            "work_resume_result": resume_result,
            "status": status,
            "extra_elapsed_seconds": elapsed_seconds,
            "compute_overhead": compute_overhead,
            "updated_at": updated_at,
        }
        if model_token_usage is not None:
            values["model_token_usage"] = model_token_usage
        if event.semantic_version >= 2:
            actions = self.self_refine_actions(event_id)
            same_signature_count = max(
                (int(action.observed_reality.get("same_failure_count", 1))
                 for action in actions), default=1,
            )
            same_signature_count = max(
                same_signature_count,
                sum(action.observed_reality.get("failure_signature") == event.failure_signature
                    for action in actions),
            )
            prior_occurrences = self.prior_self_refine_matches(
                event.failure_signature, before_event_id=event_id,
            )
            refinement_class = classify_refinement(
                converged=result == "RECOVERED",
                same_signature_count=same_signature_count,
                prior_occurrences=prior_occurrences,
                budget_exhausted=result in {"ESCALATED", "FAILED"},
                nonconvergence_threshold=int(
                    event.budget_decision.get("limits", {}).get("same_signature", 2)
                ),
                authority_required=event.repairability in {
                    RepairabilityClassification.REQUIRES_HUMAN_INPUT,
                    RepairabilityClassification.REQUIRES_HUMAN_DECISION,
                    RepairabilityClassification.UNSAFE_TO_AUTOREPAIR,
                },
            )
            values["refinement_class"] = refinement_class.value
            if refinement_class in {
                RefinementClass.DEGRADING_OR_RECURRING_REFINEMENT,
                RefinementClass.SYSTEMIC_OR_NON_CONVERGING_INCIDENT,
            }:
                values["platform_improvement_candidate_ref"] = (
                    f"refinement-signature:{event.failure_signature}"
                )
        changed = self.session.execute(
            update(self_refine_events)
            .where(self_refine_events.c.id == event_id)
            .where(self_refine_events.c.status == "OPEN")
            .values(**values)
        )
        if changed.rowcount != 1:
            raise NativeExecutionConflict("Self-Refine event is no longer open")

    def observed_repair_model_usage(
        self, attempt_id: UUID, *, since: datetime,
    ) -> dict[str, Any]:
        """Sum only provider-observed token usage after the repair began."""

        totals: dict[str, int] = {}
        observed = 0
        for step in self.steps_for_attempt(attempt_id):
            if (
                step.kind is not StepKind.INFERENCE
                or step.condition is not StepCondition.COMPLETED
                or step.started_at < since
            ):
                continue
            provider = step.result_payload.get("provider_observation")
            usage = provider.get("usage") if isinstance(provider, dict) else None
            if not isinstance(usage, dict):
                continue
            observed += 1
            for key in (
                "input_tokens", "output_tokens", "total_tokens",
                "cached_input_tokens", "reasoning_tokens",
            ):
                value = usage.get(key)
                if isinstance(value, int) and not isinstance(value, bool):
                    totals[key] = totals.get(key, 0) + value
        return {**totals, "observed_response_count": observed} if observed else {}

    def list_self_refine_events(
        self, *, work_id: UUID | None = None,
        failure_family: str | None = None,
        component: str | None = None,
        result: str | None = None,
        refinement_class: RefinementClass | None = None,
        limit: int = 100,
    ) -> tuple[SelfRefineEventRecord, ...]:
        query = select(self_refine_events)
        if work_id is not None:
            query = query.where(self_refine_events.c.work_id == work_id)
        if failure_family is not None:
            query = query.where(self_refine_events.c.failure_family == failure_family)
        if component is not None:
            query = query.where(self_refine_events.c.affected_component == component)
        if result is not None:
            query = query.where(self_refine_events.c.final_result == result)
        if refinement_class is not None:
            query = query.where(self_refine_events.c.refinement_class == refinement_class.value)
        rows = self.session.execute(
            query.order_by(self_refine_events.c.created_at.desc()).limit(limit)
        ).mappings().all()
        return tuple(SelfRefineEventRecord.model_validate(dict(row)) for row in rows)

    def self_refine_event(self, event_id: UUID) -> SelfRefineEventRecord:
        row = self.session.execute(
            select(self_refine_events).where(self_refine_events.c.id == event_id)
        ).mappings().one_or_none()
        if row is None:
            raise NativeExecutionNotFound(f"Self-Refine event not found: {event_id}")
        return SelfRefineEventRecord.model_validate(dict(row))

    def self_refine_metrics(self, *, work_id: UUID | None = None) -> dict[str, Any]:
        attempts_query = select(func.count(func.distinct(executor_queue.c.attempt_id)))
        events_query = select(self_refine_events)
        if work_id is not None:
            attempts_query = attempts_query.where(executor_queue.c.work_id == work_id)
            events_query = events_query.where(self_refine_events.c.work_id == work_id)
        attempts = int(self.session.scalar(attempts_query) or 0)
        attempt_outcomes_query = select(
            executor_queue.c.attempt_id, native_attempt_states.c.terminal_outcome,
        ).join(native_attempt_states,
               native_attempt_states.c.attempt_id == executor_queue.c.attempt_id).distinct()
        if work_id is not None:
            attempt_outcomes_query = attempt_outcomes_query.where(executor_queue.c.work_id == work_id)
        attempt_outcomes = self.session.execute(attempt_outcomes_query).all()
        records = [SelfRefineEventRecord.model_validate(dict(row)) for row in
                   self.session.execute(events_query).mappings().all()]
        results = [record.final_result for record in records]
        count = len(results)
        native_count = sum(record.affected_component.startswith("native-executor/") for record in records)
        refined_native_attempts = {
            record.operation_id for record in records
            if record.affected_component.startswith("native-executor/")
        }
        completed_attempts = [(attempt_id, outcome) for attempt_id, outcome in attempt_outcomes if outcome]
        first_pass_successes = sum(
            outcome == "RESULT_READY" and attempt_id not in refined_native_attempts
            for attempt_id, outcome in completed_attempts
        )
        completed = [record for record in records if record.final_result is not None]
        settled = [record for record in completed if record.final_result != "SUPERSEDED"]
        human_escalation_observations = [
            record for record in settled
            if "human_escalated" in record.budget_decision
        ]
        durations = sorted(record.extra_elapsed_seconds or 0 for record in completed)
        action_counts = [int(record.budget_decision.get("attempt_count") or
            self.session.scalar(select(func.count()).select_from(self_refine_actions).where(
                self_refine_actions.c.event_id == record.id,
            )) or 0) for record in completed]
        signature_counts: dict[str, int] = {}
        for record in records:
            signature_counts[record.failure_signature] = signature_counts.get(record.failure_signature, 0) + 1
        improvement_candidates = []
        for signature in sorted({
            record.failure_signature for record in records
            if record.platform_improvement_candidate_ref
        }):
            cluster = [record for record in records if record.failure_signature == signature]
            improvement_candidates.append({
                "reference": f"refinement-signature:{signature}",
                "signature": signature,
                "component": cluster[-1].affected_component,
                "occurrences": len(cluster),
                "affected_works": len({record.work_id for record in cluster}),
                "observed_tokens": sum(int(record.model_token_usage.get("total_tokens", 0)) for record in cluster),
                "observed_seconds": sum(record.extra_elapsed_seconds or 0 for record in cluster),
                "systemic": any(record.refinement_class is RefinementClass.SYSTEMIC_OR_NON_CONVERGING_INCIDENT for record in cluster),
                "status": "PROPOSED",
            })
        return {
            "native_attempts": attempts,
            "native_self_refine_events": native_count,
            "self_refine_events": count,
            "self_refine_rate": len(refined_native_attempts) / attempts if attempts else 0.0,
            "first_pass_success_rate": first_pass_successes / len(completed_attempts) if completed_attempts else 0.0,
            "recovered": results.count("RECOVERED"),
            "escalated": results.count("ESCALATED"),
            "failed": results.count("FAILED"),
            "active": results.count(None),
            "classification_counts": {
                item.value: sum(record.refinement_class is item for record in records)
                for item in RefinementClass
            },
            "convergence_success_rate": results.count("RECOVERED") / len(settled) if settled else 0.0,
            "average_refinement_attempts": sum(action_counts) / len(action_counts) if action_counts else 0.0,
            "p95_refinement_attempts": _p95(action_counts),
            "average_refinement_seconds": sum(durations) / len(durations) if durations else 0.0,
            "p95_refinement_seconds": _p95(durations),
            "observed_refinement_tokens": sum(int(record.model_token_usage.get("total_tokens", 0)) for record in records),
            "observed_refinement_tool_effects": sum(int(record.compute_overhead.get("tool_effects", 0)) for record in records),
            "unsafe_repair_blocks": sum(record.repairability is RepairabilityClassification.UNSAFE_TO_AUTOREPAIR for record in records),
            "recurring_signatures": {signature: occurrences for signature, occurrences in signature_counts.items() if occurrences > 1},
            "improvement_candidates": improvement_candidates,
            "human_escalation_observation_count": len(human_escalation_observations),
            "human_escalation_rate": sum(
                record.budget_decision["human_escalated"] is True
                for record in human_escalation_observations
            ) / len(human_escalation_observations) if human_escalation_observations else None,
            "systemic_incident_rate": sum(record.refinement_class is RefinementClass.SYSTEMIC_OR_NON_CONVERGING_INCIDENT for record in records) / count if count else 0.0,
        }

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

    def latest_native_observation(self, attempt_id: UUID) -> dict[str, Any] | None:
        payload = self.session.execute(
            select(execution_events.c.payload)
            .where(execution_events.c.attempt_id == attempt_id)
            .where(execution_events.c.event_type == "NativeObservationClassified")
            .order_by(execution_events.c.sequence.desc())
            .limit(1)
        ).scalar_one_or_none()
        return dict(payload) if isinstance(payload, dict) else None

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

    def event_sequence_window(self, pwu_id: UUID) -> tuple[int | None, int | None]:
        row = self.session.execute(
            select(
                func.min(execution_events.c.sequence),
                func.max(execution_events.c.sequence),
            ).where(execution_events.c.pwu_id == pwu_id)
        ).one()
        return (
            int(row[0]) if row[0] is not None else None,
            int(row[1]) if row[1] is not None else None,
        )

    def claim_outbox(
        self,
        *,
        now: datetime,
        lease_seconds: int = 30,
        limit: int = 100,
    ) -> Sequence[ExecutionEventRecord]:
        event_ids = tuple(
            self.session.scalars(
                select(event_outbox.c.event_id)
                .where(
                    event_outbox.c.condition == "PENDING",
                    event_outbox.c.available_at <= now,
                )
                .order_by(event_outbox.c.available_at, event_outbox.c.event_id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        if not event_ids:
            return ()
        self.session.execute(
            update(event_outbox)
            .where(event_outbox.c.event_id.in_(event_ids))
            .values(
                attempt_count=event_outbox.c.attempt_count + 1,
                available_at=now + timedelta(seconds=lease_seconds),
            )
        )
        rows = self.session.execute(
            select(execution_events)
            .where(execution_events.c.id.in_(event_ids))
            .order_by(execution_events.c.pwu_id, execution_events.c.sequence)
        ).mappings()
        return tuple(ExecutionEventRecord.model_validate(dict(row)) for row in rows)

    def acknowledge_outbox(self, event_id: UUID, *, published_at: datetime) -> None:
        result = self.session.execute(
            update(event_outbox)
            .where(
                event_outbox.c.event_id == event_id,
                event_outbox.c.condition == "PENDING",
            )
            .values(condition="PUBLISHED", published_at=published_at)
        )
        if result.rowcount != 1:
            raise NativeExecutionConflict("outbox event is missing or already acknowledged")

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

    def attempt_ids_for_pwu(self, pwu_id: UUID) -> tuple[UUID, ...]:
        return tuple(
            self.session.scalars(
                select(native_attempt_bindings.c.attempt_id)
                .where(native_attempt_bindings.c.pwu_id == pwu_id)
                .order_by(native_attempt_bindings.c.created_at)
            )
        )

    def contract(self, contract_id: UUID) -> PWUContractVersionRecord:
        row = self.session.execute(
            select(pwu_contract_versions).where(pwu_contract_versions.c.id == contract_id)
        ).mappings().one_or_none()
        if row is None:
            raise NativeExecutionNotFound(f"PWU contract not found: {contract_id}")
        return PWUContractVersionRecord.model_validate(dict(row))

    def contract_for_pwu_digest(
        self,
        pwu_id: UUID,
        contract_digest: str,
    ) -> PWUContractVersionRecord | None:
        """Return the immutable contract version already naming this content."""

        row = self.session.execute(
            select(pwu_contract_versions).where(
                pwu_contract_versions.c.pwu_id == pwu_id,
                pwu_contract_versions.c.contract_digest == contract_digest,
            )
        ).mappings().one_or_none()
        return (
            None
            if row is None
            else PWUContractVersionRecord.model_validate(dict(row))
        )

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

    def latest_step_sequence_for_session(self, session_id: UUID) -> int:
        value = self.session.scalar(
            select(func.coalesce(func.max(execution_steps.c.sequence), 0)).where(
                execution_steps.c.session_id == session_id
            )
        )
        return int(value or 0)

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

    def tool_results_after(
        self,
        attempt_id: UUID,
        *,
        after_step_sequence: int,
    ) -> tuple[ToolExecutionResult, ...]:
        rows = self.session.execute(
            select(
                execution_steps.c.sequence,
                execution_effects.c.proposal_index,
                execution_effects.c.tool_identity,
                effect_receipts.c.delivery_id,
                effect_receipts.c.condition,
                effect_receipts.c.output,
                effect_receipts.c.output_digest,
            )
            .select_from(
                execution_steps.join(
                    execution_effects,
                    execution_steps.c.id == execution_effects.c.step_id,
                ).join(
                    effect_receipts,
                    execution_effects.c.id == effect_receipts.c.effect_id,
                )
            )
            .where(
                execution_steps.c.attempt_id == attempt_id,
                execution_steps.c.sequence > after_step_sequence,
            )
            .order_by(
                execution_steps.c.sequence,
                execution_effects.c.proposal_index,
                effect_receipts.c.created_at,
            )
        ).mappings()
        return tuple(
            ToolExecutionResult(
                delivery_id=row["delivery_id"],
                tool_identity=row["tool_identity"],
                condition=row["condition"],
                output=row["output"],
                output_digest=row["output_digest"],
            )
            for row in rows
        )

    def latest_checkpoint(self, attempt_id: UUID) -> CheckpointBundleRecord | None:
        row = self.session.execute(
            select(checkpoint_bundles)
            .where(checkpoint_bundles.c.attempt_id == attempt_id)
            .order_by(checkpoint_bundles.c.step_sequence.desc())
        ).mappings().first()
        return CheckpointBundleRecord.model_validate(dict(row)) if row else None

    def checkpoint(self, checkpoint_id: UUID) -> CheckpointBundleRecord | None:
        row = self.session.execute(
            select(checkpoint_bundles).where(checkpoint_bundles.c.id == checkpoint_id)
        ).mappings().one_or_none()
        return (
            CheckpointBundleRecord.model_validate(dict(row))
            if row is not None
            else None
        )

    def timing_projection(self, attempt_id: UUID) -> dict[str, object]:
        allocation = self.session.execute(
            select(execution_allocations)
            .where(execution_allocations.c.attempt_id == attempt_id)
            .order_by(execution_allocations.c.issued_at.desc())
        ).mappings().first()
        queue = self.queue_for_attempt(attempt_id)
        workspace = self.session.execute(
            select(execution_workspaces).where(
                execution_workspaces.c.attempt_id == attempt_id
            )
        ).mappings().one_or_none()
        inference_rows = self.session.execute(
            select(
                execution_steps.c.id,
                execution_steps.c.sequence,
                execution_steps.c.started_at,
                execution_steps.c.finished_at,
            ).where(
                execution_steps.c.attempt_id == attempt_id,
                execution_steps.c.kind == "INFERENCE",
            ).order_by(execution_steps.c.sequence)
        ).mappings()
        tool_rows = self.session.execute(
            select(
                execution_effects.c.id,
                execution_effects.c.tool_identity,
                execution_effects.c.created_at,
                effect_receipts.c.created_at.label("receipt_at"),
            )
            .select_from(
                execution_steps.join(
                    execution_effects,
                    execution_steps.c.id == execution_effects.c.step_id,
                ).outerjoin(
                    effect_receipts,
                    execution_effects.c.id == effect_receipts.c.effect_id,
                )
            )
            .where(execution_steps.c.attempt_id == attempt_id)
            .order_by(execution_steps.c.sequence, execution_effects.c.proposal_index)
        ).mappings()
        checkpoint_rows = self.session.execute(
            select(
                checkpoint_bundles.c.id,
                checkpoint_bundles.c.created_at,
                checkpoint_bundles.c.committed_at,
            ).where(checkpoint_bundles.c.attempt_id == attempt_id)
            .order_by(checkpoint_bundles.c.step_sequence)
        ).mappings()
        event_rows = self.session.execute(
            select(
                execution_events.c.id,
                execution_events.c.event_type,
                execution_events.c.created_at,
                event_outbox.c.published_at,
            )
            .select_from(
                execution_events.join(
                    event_outbox, execution_events.c.id == event_outbox.c.event_id
                )
            )
            .where(execution_events.c.attempt_id == attempt_id)
            .order_by(execution_events.c.sequence)
        ).mappings()
        first_step_started = self.session.scalar(
            select(func.min(execution_steps.c.started_at)).where(
                execution_steps.c.attempt_id == attempt_id
            )
        )

        def span(latency_class: str, kind: str, identity: object, start, end):
            return {
                "latency_class": latency_class,
                "kind": kind,
                "identity": str(identity),
                "started_at": start.isoformat() if start else None,
                "finished_at": end.isoformat() if end else None,
                "duration_ms": (
                    round((end - start).total_seconds() * 1000, 3)
                    if start is not None and end is not None
                    else None
                ),
            }

        spans: list[dict[str, object]] = []
        if queue is not None:
            spans.append(
                span(
                    "RUNTIME_ORCHESTRATION",
                    "QUEUE",
                    queue.id,
                    queue.enqueued_at,
                    allocation["issued_at"] if allocation else None,
                )
            )
            spans.append(
                span(
                    "PERCEIVED_HUMAN",
                    "FIRST_MEANINGFUL_ACTION",
                    attempt_id,
                    queue.enqueued_at,
                    first_step_started,
                )
            )
        if allocation is not None:
            spans.append(
                span(
                    "RUNTIME_ORCHESTRATION",
                    "ALLOCATION",
                    allocation["id"],
                    allocation["issued_at"],
                    allocation["released_at"],
                )
            )
        if workspace is not None:
            spans.append(
                span(
                    "TOOL_WORKSPACE",
                    "WORKSPACE_RECORDED_LIFETIME",
                    workspace["id"],
                    workspace["created_at"],
                    workspace["updated_at"],
                )
            )
        spans.extend(
            span(
                "MODEL_PROVIDER", "INFERENCE", row["id"],
                row["started_at"], row["finished_at"]
            )
            for row in inference_rows
        )
        spans.extend(
            span(
                "TOOL_WORKSPACE", "TOOL", row["id"],
                row["created_at"], row["receipt_at"]
            )
            for row in tool_rows
        )
        spans.extend(
            span(
                "RUNTIME_ORCHESTRATION", "CHECKPOINT", row["id"],
                row["created_at"], row["committed_at"]
            )
            for row in checkpoint_rows
        )
        spans.extend(
            span(
                "PERCEIVED_HUMAN", f"EVENT:{row['event_type']}", row["id"],
                row["created_at"], row["published_at"]
            )
            for row in event_rows
        )
        return {
            "spans": spans,
            "latency_classes": {
                "MODEL_PROVIDER": "measured per completed inference step",
                "RUNTIME_ORCHESTRATION": "queue, allocation, and checkpoint spans",
                "TOOL_WORKSPACE": "tool receipts and recorded workspace lifetime",
                "INFRASTRUCTURE": "unavailable without host/container trace ingestion",
                "PERCEIVED_HUMAN": "durable admission to first action and event publish",
            },
            "unavailable": {
                "admission_transport": "HTTP receive timestamp is not persisted",
                "worker_activation": "allocation activation timestamp is not persisted",
                "workspace_materialization": "materialization start/finish timestamps are not persisted",
                "context": "context assembly timing is not persisted",
                "verification": "independent Verification is owned downstream",
                "infrastructure": "container, disk, network, and DB spans require host trace ingestion",
                "event_delivery": "publish is measured when acked; subscriber render acknowledgement is unavailable",
                "reconnect": "client reconnect timing is not persisted",
            },
            "aggregate_duration_ms": None,
            "aggregate_reason": "phase spans may overlap and are not summed",
        }

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
