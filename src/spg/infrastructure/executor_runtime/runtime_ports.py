"""Durable audit and checkpoint ports used by the native Executor kernel."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from spg.domain.native_execution import (
    CheckpointBundleRecord,
    CheckpointCondition,
    EffectClassification,
    EffectCondition,
    EffectReceiptRecord,
    ExecutionEffectRecord,
    ExecutionEvidenceRecord,
    ExecutionStepRecord,
    InferenceRequest,
    InferenceResponse,
    KernelCheckpoint,
    NativeExecutionConflict,
    ResourceReservationCondition,
    ResourceUsageEntryRecord,
    StepCondition,
    StepKind,
    ToolExecutionRequest,
    ToolExecutionResult,
    UsageCertainty,
    canonical_digest,
)
from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.persistence import Database


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DurableKernelAudit:
    """Write intent-before-effect and receipt-after-effect execution evidence."""

    def __init__(
        self,
        database: Database,
        *,
        attempt_id: UUID,
        session_id: UUID,
        pwu_id: UUID,
        envelope_id: UUID,
    ) -> None:
        self.database = database
        self.attempt_id = attempt_id
        self.session_id = session_id
        self.pwu_id = pwu_id
        self.envelope_id = envelope_id

    async def begin_inference(self, request: InferenceRequest) -> UUID:
        step_id = uuid4()
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            store.insert_step(
                ExecutionStepRecord(
                    id=step_id,
                    session_id=self.session_id,
                    attempt_id=self.attempt_id,
                    sequence=request.step_sequence,
                    kind=StepKind.INFERENCE,
                    condition=StepCondition.RUNNING,
                    request_payload=request.model_dump(mode="json"),
                    request_digest=canonical_digest(request),
                    context_revision=request.working_plan.version,
                    started_at=_utcnow(),
                )
            )
            store.insert_resource_usage(
                ResourceUsageEntryRecord(
                    id=uuid4(), envelope_id=self.envelope_id,
                    attempt_id=self.attempt_id,
                    reservation_key=f"inference:{step_id}",
                    resource_type="inference_submission", amount=1,
                    certainty=UsageCertainty.ESTIMATED,
                    condition=ResourceReservationCondition.RESERVED,
                    evidence={"step_id": str(step_id)}, created_at=_utcnow(),
                )
            )
            uow.commit()
        return step_id

    async def finish_inference(
        self,
        step_id: UUID,
        response: InferenceResponse | None,
        error: BaseException | None,
    ) -> None:
        if response is not None:
            payload = response.model_dump(mode="json")
            condition = StepCondition.COMPLETED
        else:
            payload = {"error_type": type(error).__name__ if error else "UnknownError"}
            condition = StepCondition.FAILED
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            store.finish_step(
                step_id,
                condition=condition.value,
                result_payload=payload,
                result_digest=canonical_digest(payload),
                finished_at=_utcnow(),
            )
            store.settle_resource_usage(
                envelope_id=self.envelope_id,
                reservation_key=f"inference:{step_id}",
                resource_type="inference_submission",
                certainty=(UsageCertainty.ACTUAL if response is not None else UsageCertainty.UNKNOWN),
                condition=(ResourceReservationCondition.CONSUMED if response is not None else ResourceReservationCondition.UNKNOWN),
                evidence={"step_id": str(step_id), "response_observed": response is not None},
            )
            uow.commit()

    async def begin_tool(self, step_id: UUID, request: ToolExecutionRequest) -> UUID:
        effect_id = uuid4()
        semantic_input = request.proposal.arguments
        classification = {
            "file.read": EffectClassification.READ,
            "file.write": EffectClassification.LOCAL_MUTATION,
            "process.run": EffectClassification.PROCESS,
            "git.status": EffectClassification.READ,
            "git.diff": EffectClassification.READ,
            "test.run": EffectClassification.PROCESS,
            "build.run": EffectClassification.PROCESS,
            "dependency.sync": EffectClassification.PROCESS,
            "preview.inspect": EffectClassification.READ,
        }.get(request.proposal.tool_identity, EffectClassification.LOCAL_MUTATION)
        conflict_domains = tuple(
            str(value)
            for key, value in semantic_input.items()
            if key in {"path", "cwd"} and isinstance(value, str)
        )
        with self.database.unit_of_work() as uow:
            NativeExecutionStore(uow.session).insert_effect(
                ExecutionEffectRecord(
                    id=effect_id,
                    step_id=step_id,
                    proposal_index=request.proposal.proposal_index,
                    tool_identity=request.proposal.tool_identity,
                    tool_version="1",
                    semantic_input=semantic_input,
                    semantic_input_digest=canonical_digest(semantic_input),
                    classification=classification,
                    conflict_domains=conflict_domains,
                    condition=EffectCondition.INTENDED,
                    created_at=_utcnow(),
                )
            )
            NativeExecutionStore(uow.session).insert_resource_usage(
                ResourceUsageEntryRecord(
                    id=uuid4(), envelope_id=self.envelope_id,
                    attempt_id=self.attempt_id,
                    reservation_key=f"tool:{effect_id}", resource_type="tool_effect",
                    amount=1, certainty=UsageCertainty.ESTIMATED,
                    condition=ResourceReservationCondition.RESERVED,
                    evidence={"effect_id": str(effect_id)}, created_at=_utcnow(),
                )
            )
            uow.commit()
        return effect_id

    async def finish_tool(
        self,
        effect_id: UUID,
        request: ToolExecutionRequest,
        result: ToolExecutionResult | None,
        error: BaseException | None,
    ) -> None:
        if result is not None:
            condition = result.condition
            output = result.output
            digest = result.output_digest
        else:
            condition = EffectCondition.UNKNOWN
            output = {"error_type": type(error).__name__ if error else "UnknownError"}
            digest = canonical_digest(output)
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            store.set_effect_condition(effect_id, condition.value)
            store.insert_effect_receipt(
                EffectReceiptRecord(
                    id=uuid4(),
                    effect_id=effect_id,
                    delivery_id=request.delivery_id,
                    host_identity="native-tool-host",
                    host_nonce=str(request.delivery_id),
                    condition=condition,
                    output=output,
                    output_digest=digest,
                    created_at=_utcnow(),
                )
            )
            store.settle_resource_usage(
                envelope_id=self.envelope_id,
                reservation_key=f"tool:{effect_id}",
                resource_type="tool_effect",
                certainty=(UsageCertainty.ACTUAL if result is not None else UsageCertainty.UNKNOWN),
                condition=(ResourceReservationCondition.CONSUMED if result is not None else ResourceReservationCondition.UNKNOWN),
                evidence={"effect_id": str(effect_id), "receipt_observed": result is not None},
            )
            for evidence_payload in result.evidence if result else ():
                store.insert_evidence(
                    ExecutionEvidenceRecord(
                        id=uuid4(),
                        pwu_id=self.pwu_id,
                        attempt_id=self.attempt_id,
                        step_id=request.step_id,
                        effect_id=effect_id,
                        evidence_type=str(evidence_payload.get("type", "TOOL_RECEIPT")),
                        producer_identity="native-tool-host",
                        subject_digest=digest,
                        payload=evidence_payload,
                        content_digest=canonical_digest(evidence_payload),
                        created_at=_utcnow(),
                    )
                )
            uow.commit()


class DurableCheckpointPort:
    """Commit content-addressed checkpoint payload plus authoritative DB pointer."""

    def __init__(
        self,
        database: Database,
        storage: ContentAddressedStorage,
        *,
        attempt_id: UUID,
        session_id: UUID,
        worker_epoch: int,
    ) -> None:
        self.database = database
        self.storage = storage
        self.attempt_id = attempt_id
        self.session_id = session_id
        self.worker_epoch = worker_epoch

    async def commit(self, checkpoint: KernelCheckpoint) -> CheckpointBundleRecord:
        payload = checkpoint.model_dump(mode="json")
        digest, path = self.storage.put_json(f"attempts/{self.attempt_id}", payload)
        now = _utcnow()
        record = CheckpointBundleRecord(
            id=uuid4(),
            session_id=self.session_id,
            attempt_id=self.attempt_id,
            step_sequence=checkpoint.step_sequence,
            worker_epoch=self.worker_epoch,
            condition=CheckpointCondition.COMMITTED,
            source_vector_digest=checkpoint.source_vector_digest,
            repository_manifest={"storage": "content-addressed", "path": str(path)},
            execution_manifest={
                "tool_results": [item.model_dump(mode="json") for item in checkpoint.tool_results]
            },
            semantic_manifest={
                "working_plan": checkpoint.working_plan.model_dump(mode="json"),
                "result_claim": checkpoint.result_claim,
                "residual_obligations": list(checkpoint.residual_obligations),
            },
            content_digest=digest,
            consistency_class="APPLICATION_CONSISTENT",
            created_at=now,
            committed_at=now,
        )
        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            state = store.attempt_state(self.attempt_id, lock=True)
            if state.worker_epoch != self.worker_epoch:
                raise NativeExecutionConflict("checkpoint writer has been fenced")
            store.insert_checkpoint(record)
            store.advance_session_checkpoint(
                self.session_id,
                checkpoint_id=record.id,
                working_state_version=checkpoint.working_plan.version,
            )
            store.update_attempt_state(
                self.attempt_id,
                expected_version=state.version,
                values={
                    "current_checkpoint_id": record.id,
                    "current_step_sequence": checkpoint.step_sequence,
                },
            )
            uow.commit()
        return record
