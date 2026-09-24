"""Durable audit and checkpoint ports used by the native Executor kernel."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID, uuid4

from spg.domain.native_execution import (
    CheckpointBundleRecord,
    CheckpointCondition,
    EffectClassification,
    EffectCondition,
    EffectReceiptRecord,
    ExecutionBindingV2,
    ExecutionEffectRecord,
    ExecutionEvidenceRecord,
    ExecutionStepRecord,
    InferenceRequest,
    InferenceResponse,
    InferenceDecisionRejected,
    KernelCheckpoint,
    NativeExecutionConflict,
    ObservationConfidence,
    RepairabilityClassification,
    ResourceReservationCondition,
    ResourceUsageEntryRecord,
    SelfRefineActionRecord,
    SelfRefineEventRecord,
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

    def recent_repair_reality(self) -> tuple[dict[str, object], ...]:
        """Bounded, safe Work repair history for a resumed decision."""

        with self.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            work_id = store.attempt_binding(self.attempt_id).binding.work_id
            events = store.list_self_refine_events(work_id=work_id, limit=3)
            current_open = store.open_self_refine_event(self.attempt_id)
            if current_open is not None:
                events = (current_open, *(item for item in events if item.id != current_open.id))[:3]
        return tuple({
            "event_id": str(event.id),
            "operation_id": str(event.operation_id),
            "failure_family": event.failure_family,
            "failure_signature": event.failure_signature,
            "expected_reality": event.expected_reality,
            "observed_reality": event.observed_reality,
            "repair_hypothesis": event.repair_hypothesis,
            "repairability": event.repairability.value,
            "diagnostic_evidence": event.diagnostic_evidence,
            "result": event.final_result,
            "status": event.status,
        } for event in events)

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
            reason_code = getattr(error, "reason_code", None)
            if isinstance(reason_code, str) and reason_code:
                payload["reason_code"] = reason_code
            validation_issues = getattr(error, "validation_issues", ())
            if validation_issues:
                payload["validation_issues"] = list(validation_issues)
            request_sent = getattr(error, "request_sent", None)
            if isinstance(request_sent, bool):
                payload["request_sent"] = request_sent
            failure_code = getattr(error, "failure_code", None)
            if isinstance(failure_code, str) and failure_code:
                payload["failure_code"] = failure_code
            transport_diagnostics = getattr(error, "transport_diagnostics", None)
            if isinstance(transport_diagnostics, dict) and transport_diagnostics:
                payload["transport_diagnostics"] = transport_diagnostics
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
            if isinstance(error, InferenceDecisionRejected):
                self._record_structural_repair(store, step_id, error)
            uow.commit()

    def _record_structural_repair(
        self, store: NativeExecutionStore, step_id: UUID, error: InferenceDecisionRejected,
    ) -> None:
        """Persist the kernel's one constrained repair before the next inference."""

        now = _utcnow()
        signature = sha256(
            f"SEMANTIC_BINDING_FAILURE:{error.reason_code}".encode("utf-8")
        ).hexdigest()
        event = store.open_self_refine_event(self.attempt_id)
        if event is None:
            binding = store.attempt_binding(self.attempt_id).binding
            event_id = uuid4()
            event = SelfRefineEventRecord(
                id=event_id, work_id=binding.work_id,
                operation_id=self.attempt_id, created_at=now,
                failure_family="SEMANTIC_BINDING_FAILURE",
                failure_signature=signature,
                affected_component="native-executor/inference-decision",
                expected_reality={"outcome": "VALID_GOVERNED_DECISION",
                                  "contract_digest": binding.pwu_contract_digest},
                observed_reality={"reason_code": error.reason_code,
                                  "inference_step_id": str(step_id)},
                diagnosis_summary="Provider decision failed canonical local validation.",
                root_cause_classification="INVALID_STRUCTURED_RESPONSE",
                repair_hypothesis=(
                    "Make one constrained inference repair against the same Task Contract "
                    "without replaying tool effects or changing authority."
                ),
                evidence_references=(f"native-inference-step:{step_id}",),
                repairability=RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE,
                observation_confidence=ObservationConfidence.CONFIRMED_FAILURE,
                budget_decision={
                    "policy_version": "native-structural-repair-v1",
                    "maximum_same_decision_retries": 1,
                    "authority_boundary": "same admitted Task Contract",
                },
                diagnostic_evidence={
                    "inference_step_ref": f"native-inference-step:{step_id}",
                    "reason_code": error.reason_code,
                    "validation_issue_count": len(getattr(error, "validation_issues", ())),
                },
                known_failure_match=store.prior_self_refine_matches(
                    signature, before_event_id=event_id,
                ) > 0,
                updated_at=now,
            )
            store.insert_self_refine_event(event)
        actions = store.self_refine_actions(event.id)
        store.append_self_refine_action(SelfRefineActionRecord(
            id=uuid4(), event_id=event.id, sequence=len(actions) + 1,
            created_at=now,
            repair_action=(
                "Constrain the next inference to the admitted contract"
                if not actions else "Escalate repeated canonical decision rejection"
            ),
            observed_reality={"reason_code": error.reason_code,
                              "inference_step_id": str(step_id),
                              "same_failure_count": len(actions) + 1,
                              "inference_submissions": 1},
            evidence_references=(f"native-inference-step:{step_id}",),
            outcome="RETRY_SCHEDULED" if not actions else "ESCALATED",
        ))

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
        if request.proposal.tool_identity == "git.operation":
            from spg.executor.git_operations import git_operation_is_read_only

            classification = (
                EffectClassification.READ
                if git_operation_is_read_only(str(semantic_input.get("operation")))
                else EffectClassification.LOCAL_MUTATION
            )
        if request.proposal.tool_identity == "filesystem.operation":
            classification = (
                EffectClassification.READ
                if semantic_input.get("operation") in {"search", "stat", "diff"}
                else EffectClassification.LOCAL_MUTATION
            )
        conflict_domains = tuple(
            str(value)
            for key, value in semantic_input.items()
              if key in {"path", "destination", "cwd"} and isinstance(value, str)
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
    ) -> RepairabilityClassification | None:
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
            receipt_id = uuid4()
            store.insert_effect_receipt(
                EffectReceiptRecord(
                    id=receipt_id,
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
            evidence_ids: list[UUID] = []
            for evidence_payload in result.evidence if result else ():
                evidence_id = uuid4()
                store.insert_evidence(
                    ExecutionEvidenceRecord(
                        id=evidence_id,
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
                evidence_ids.append(evidence_id)
            repairability = None
            if condition in {EffectCondition.FAILED, EffectCondition.UNKNOWN}:
                repairability = self._record_failed_effect(
                    store, effect_id, receipt_id, tuple(evidence_ids),
                    request, condition, output, digest,
                )
            elif condition is EffectCondition.SETTLED and request.proposal.tool_identity == "file.read":
                repairability = self._confirm_build_diagnostic(
                    store, receipt_id=receipt_id, output=output,
                    evidence_ids=tuple(evidence_ids),
                )
            uow.commit()
        return repairability

    def _confirm_build_diagnostic(
        self, store: NativeExecutionStore, *, receipt_id: UUID,
        output: dict, evidence_ids: tuple[UUID, ...],
    ) -> RepairabilityClassification | None:
        """Promote only a bounded compiler finding after a source observation."""

        event = store.open_self_refine_event(self.attempt_id)
        if (
            event is None
            or event.repairability is not RepairabilityClassification.REPAIRABLE_WITH_SUFFICIENT_EVIDENCE
            or event.failure_family != "DEPENDENCY_BUILD_FAILURE"
            or not event.diagnostic_evidence.get("diagnostic_code")
            or output.get("exists") is not True
            or not isinstance(output.get("content"), str)
        ):
            return None
        path = output.get("path")
        if not isinstance(path, str) or path != event.diagnostic_evidence.get("path"):
            return None
        binding = store.attempt_binding(self.attempt_id).binding
        contract = store.contract(binding.pwu_contract_version_id)
        task = contract.contract_payload.get("task_contract")
        if not isinstance(task, dict):
            completion = contract.contract_payload.get("completion_contract")
            task = completion.get("task_contract") if isinstance(completion, dict) else None
        if not isinstance(task, dict) or not task.get("authority_lineage"):
            return None
        task_scopes = task.get("scope")
        if not isinstance(task_scopes, list) or not task_scopes:
            return None
        allowed_scopes = {
            scope for grant in binding.capability_grants
            if grant.identity == "file.write"
            for scope in grant.scope.get("paths", []) if isinstance(scope, str)
        }
        writable_scopes = {
            scope for mount in binding.workspace.mounts if mount.writable
            for scope in mount.write_scope
        }
        def within(target: str, scope: str) -> bool:
            return target == scope or target.startswith(scope.rstrip("/") + "/")
        if (
            path.startswith("/") or "\\" in path or ".." in path.split("/")
            or not any(within(path, scope) for scope in task_scopes if isinstance(scope, str))
            or not any(within(path, scope) for scope in allowed_scopes)
            or not any(within(path, scope) for scope in writable_scopes)
        ):
            return None
        now = _utcnow()
        references = (
            f"native-receipt:{receipt_id}",
            *(f"native-evidence:{identity}" for identity in evidence_ids),
        )
        actions = store.self_refine_actions(event.id)
        store.append_self_refine_action(SelfRefineActionRecord(
            id=uuid4(), event_id=event.id, sequence=len(actions) + 1,
            created_at=now,
            repair_action="Confirm compiler target against admitted source and write scope",
            observed_reality={
                "path": path, "source_content_digest": canonical_digest(output["content"]),
                "repairability_before": event.repairability.value,
                "repairability_after": RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE.value,
            },
            evidence_references=references,
            outcome="EVIDENCE_SUFFICIENT",
        ))
        store.advance_self_refine_repairability(
            event.id,
            repairability=RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE,
            diagnostic_evidence={
                **event.diagnostic_evidence,
                "source_read_receipt_ref": f"native-receipt:{receipt_id}",
                "source_content_digest": canonical_digest(output["content"]),
            },
            updated_at=now,
        )
        return RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE

    def _record_failed_effect(
        self,
        store: NativeExecutionStore,
        effect_id: UUID,
        receipt_id: UUID,
        evidence_ids: tuple[UUID, ...],
        request: ToolExecutionRequest,
        condition: EffectCondition,
        output: dict,
        digest: str,
    ) -> RepairabilityClassification:
        """Classify an observed failed effect without persisting raw tool output."""

        tool = request.proposal.tool_identity
        family = {
            "test.run": "VERIFICATION_FAILURE",
            "preview.inspect": "VERIFICATION_FAILURE",
            "build.run": "DEPENDENCY_BUILD_FAILURE",
            "dependency.sync": "DEPENDENCY_BUILD_FAILURE",
            "git.operation": "REPOSITORY_OPERATION_FAILURE",
            "file.write": "IMPLEMENTATION_EFFECT_FAILURE",
            "process.run": "RUNTIME_PROCESS_FAILURE",
        }.get(tool, "EXECUTION_EFFECT_FAILURE")
        failure_code = output.get("returncode")
        if not isinstance(failure_code, int):
            failure_code = output.get("error_type")
        if not isinstance(failure_code, (int, str)):
            failure_code = condition.value
        signature = sha256(f"{family}:{tool}:{failure_code}".encode("utf-8")).hexdigest()
        now = _utcnow()
        binding = store.attempt_binding(self.attempt_id).binding
        contract = store.contract(binding.pwu_contract_version_id)
        repairability, basis = self._classify_repairability(
            contract.contract_payload, binding=binding, tool=tool,
            condition=condition, output=output,
        )
        references = (
            f"native-effect:{effect_id}", f"native-receipt:{receipt_id}",
            *(f"native-evidence:{identity}" for identity in evidence_ids),
        )
        diagnostic = self._diagnostic_index(
            tool=tool, output=output, digest=digest,
            receipt_id=receipt_id, evidence_ids=evidence_ids,
        )
        event = store.open_self_refine_event(self.attempt_id)
        if event is not None and event.failure_signature != signature:
            prior_actions = store.self_refine_actions(event.id)
            store.append_self_refine_action(SelfRefineActionRecord(
                id=uuid4(), event_id=event.id, sequence=len(prior_actions) + 1,
                created_at=now,
                repair_action="Close the prior diagnosis when a distinct failed effect is observed",
                observed_reality={"next_failure_signature": signature},
                evidence_references=references, outcome="SUPERSEDED_BY_NEW_FAILURE",
            ))
            store.complete_self_refine_event(
                event.id, result="FAILED", resume_result="NOT_RESUMED",
                status="MITIGATED", elapsed_seconds=max(0, int((now - event.created_at).total_seconds())),
                updated_at=now, compute_overhead={"tool_effects": len(prior_actions)},
            )
            event = None
        if (
            event is not None
            and event.repairability is RepairabilityClassification.REPAIRABLE_WITH_SUFFICIENT_EVIDENCE
            and repairability is RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE
        ):
            store.advance_self_refine_repairability(
                event.id, repairability=repairability,
                diagnostic_evidence={**event.diagnostic_evidence, **diagnostic},
                updated_at=now,
            )
        if event is None:
            event_id = uuid4()
            event = SelfRefineEventRecord(
                id=event_id, work_id=binding.work_id,
                operation_id=self.attempt_id, created_at=now,
                failure_family=family,
                failure_signature=signature,
                affected_component=f"native-tool-host/{tool}",
                expected_reality={"effect_condition": EffectCondition.SETTLED.value,
                                  "tool_identity": tool},
                observed_reality={"effect_condition": condition.value,
                                  "output_digest": digest,
                                  "failure_code": failure_code},
                diagnosis_summary="The observed tool effect did not satisfy its admitted operation.",
                root_cause_classification=family,
                repair_hypothesis=(
                    "Use the failed effect receipt to diagnose and repair within the "
                    "same admitted Task Contract; do not replay an uncertain side effect."
                ),
                evidence_references=references,
                repairability=repairability,
                observation_confidence=ObservationConfidence.CONFIRMED_FAILURE,
                budget_decision={"policy_version": "native-effect-repair-v1", "classification_basis": basis},
                diagnostic_evidence=diagnostic,
                known_failure_match=store.prior_self_refine_matches(
                    signature, before_event_id=event_id,
                ) > 0,
                updated_at=now,
            )
            store.insert_self_refine_event(event)
        actions = store.self_refine_actions(event.id)
        store.append_self_refine_action(SelfRefineActionRecord(
            id=uuid4(), event_id=event.id, sequence=len(actions) + 1,
            created_at=now,
            repair_action=(
                "Reconcile effect uncertainty before replay"
                if condition is EffectCondition.UNKNOWN
                else "Diagnose receipt and attempt bounded in-scope correction"
            ),
            observed_reality={"effect_condition": condition.value,
                              "tool_identity": tool,
                              "failure_signature": signature,
                              "output_digest": digest,
                              "failure_code": failure_code,
                              "initial_repairability": repairability.value,
                              "tool_effects": 1},
            evidence_references=references,
            outcome=(
                "RECONCILIATION_REQUIRED" if condition is EffectCondition.UNKNOWN
                else "ESCALATED" if repairability in {
                    RepairabilityClassification.REQUIRES_HUMAN_INPUT,
                    RepairabilityClassification.REQUIRES_HUMAN_DECISION,
                    RepairabilityClassification.UNSAFE_TO_AUTOREPAIR,
                } else "RETRY_SCHEDULED"
            ),
        ))
        if repairability in {
            RepairabilityClassification.REQUIRES_HUMAN_INPUT,
            RepairabilityClassification.REQUIRES_HUMAN_DECISION,
            RepairabilityClassification.UNSAFE_TO_AUTOREPAIR,
        }:
            store.complete_self_refine_event(
                event.id, result="ESCALATED", resume_result="NOT_RESUMED",
                status="MITIGATED", elapsed_seconds=0, updated_at=now,
                compute_overhead={"tool_effects": 1},
            )
        return repairability

    @staticmethod
    def _classify_repairability(
        contract_payload: dict, *, binding: ExecutionBindingV2,
        tool: str, condition: EffectCondition, output: dict,
    ) -> tuple[RepairabilityClassification, str]:
        """Use admitted oracle and effect certainty, never a business/engineering label alone."""

        if condition is EffectCondition.UNKNOWN:
            return RepairabilityClassification.UNSAFE_TO_AUTOREPAIR, "effect outcome is uncertain"
        if output.get("missing_human_input") is True:
            return RepairabilityClassification.REQUIRES_HUMAN_INPUT, "Human-owned input is absent"
        if output.get("product_choice_required") is True:
            return RepairabilityClassification.REQUIRES_HUMAN_DECISION, "multiple valid product outcomes"
        if output.get("product_intent_change") is True:
            return RepairabilityClassification.REQUIRES_HUMAN_DECISION, "repair would change Product Intent"
        assertion = output.get("assertion")
        task = contract_payload.get("task_contract")
        if not isinstance(task, dict):
            completion = contract_payload.get("completion_contract")
            task = completion.get("task_contract") if isinstance(completion, dict) else None
        if isinstance(assertion, dict) and isinstance(task, dict):
            identity = assertion.get("id")
            expected = assertion.get("expected")
            observed = assertion.get("observed")
            meanings = task.get("acceptance_meaning")
            lineage = task.get("authority_lineage")
            scope = task.get("scope")
            granted_paths = {
                path for grant in binding.capability_grants
                if grant.identity == "file.write"
                for path in grant.scope.get("paths", [])
                if isinstance(path, str)
            }
            writable_paths = {
                path for mount in binding.workspace.mounts if mount.writable
                for path in mount.write_scope
            }
            if (
                isinstance(identity, str) and identity
                and expected is not None
                and isinstance(meanings, list)
                and isinstance(lineage, list) and lineage
                and isinstance(scope, list) and scope
                and all(isinstance(path, str) and path in granted_paths
                        and path in writable_paths for path in scope)
                and f"{identity} = {expected}" in meanings
            ):
                if "observed" not in assertion or observed == expected:
                    return RepairabilityClassification.REPAIRABLE_WITH_SUFFICIENT_EVIDENCE, "observed assertion mismatch is not established"
                return RepairabilityClassification.AUTONOMOUSLY_REPAIRABLE, "exact admitted acceptance oracle"
            return RepairabilityClassification.REQUIRES_HUMAN_DECISION, "assertion lacks an admitted unambiguous oracle"
        if tool in {"build.run", "dependency.sync"} and output.get("diagnostic_code"):
            # A compiler error identifies a technical failure, but does not by
            # itself authorize a change to an arbitrary file or dependency.
            return RepairabilityClassification.REPAIRABLE_WITH_SUFFICIENT_EVIDENCE, "build diagnostic requires an in-scope repair target"
        return RepairabilityClassification.REPAIRABLE_WITH_SUFFICIENT_EVIDENCE, "additional authoritative diagnosis required"

    @staticmethod
    def _diagnostic_index(
        *, tool: str, output: dict, digest: str, receipt_id: UUID,
        evidence_ids: tuple[UUID, ...],
    ) -> dict[str, object]:
        """Index durable technical receipts without duplicating raw logs in a Work event."""

        indexed: dict[str, object] = {
            "tool_identity": tool,
            "output_digest": digest,
            "receipt_ref": f"native-receipt:{receipt_id}",
            "evidence_refs": [f"native-evidence:{identity}" for identity in evidence_ids],
        }
        for field in ("test_identity", "diagnostic_code", "returncode", "path", "git_ref"):
            value = output.get(field)
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                indexed[field] = value if isinstance(value, int) else value[:255]
        assertion = output.get("assertion")
        if isinstance(assertion, dict):
            identity = assertion.get("id")
            if isinstance(identity, str):
                indexed["assertion_id"] = identity[:255]
            for field in ("expected", "observed"):
                if field in assertion:
                    indexed[f"{field}_digest"] = canonical_digest(assertion[field])
        for field in ("stdout", "stderr", "stack_trace", "compiler_diagnostics", "runtime_logs"):
            value = output.get(field)
            if isinstance(value, str):
                indexed[f"{field}_bytes"] = len(value.encode("utf-8"))
                indexed[f"{field}_ref"] = f"native-receipt:{receipt_id}#{field}"
        changed = output.get("changed_files")
        if isinstance(changed, list):
            indexed["changed_files"] = [str(item)[:255] for item in changed[:20]]
        return indexed


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
            schema_version=checkpoint.schema_version,
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
