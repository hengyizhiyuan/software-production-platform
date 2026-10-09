"""Bounded Verification candidate receipts on existing Owner evidence records.

This local recorder is neither an authority nor a new trace/state machine.
It retains candidate observations before validation and append-only predicates
before repair; replay consumes the same two-attempt budget.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from uuid import uuid4

MAX_CANDIDATE_BYTES = 65536
_SECRET_ENV = ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
    "SPG_DEEPSEEK_API_KEY", "SPG_NATIVE_EXECUTOR_DEEPSEEK_API_KEY", "SPG_OPERATOR_API_KEY",
    "SPG_OPERATOR_TOKEN", "SPG_TOOL_HOST_TOKEN", "SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN",
    "SPG_MANAGED_SOURCE_PASSWORD", "SPG_DATABASE_PASSWORD", "SPG_DATABASE_URL")


def _sensitive_values():
    # Read only authentication categories into memory; values are never emitted.
    values = {value for name, value in os.environ.items() if value and
        (name in _SECRET_ENV or name.endswith(("_API_KEY", "_PASSWORD", "_TOKEN", "_SECRET")))}
    from urllib.parse import urlsplit, unquote
    for name, value in os.environ.items():
        if not value or not name.endswith(("_DATABASE_URL", "_DSN")):
            continue
        values.add(value)
        try:
            password = urlsplit(value).password
            if password:
                values.update((password, unquote(password)))
        except ValueError:
            pass
    return sorted(values, key=len, reverse=True)


def _safe_value(value, secrets=None):
    secrets = _sensitive_values() if secrets is None else secrets
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, "[REDACTED]")
        return value
    if isinstance(value, dict):
        return {key: _safe_value(item, secrets) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_safe_value(item, secrets) for item in value]
    return value


def _safe_output(text):
    value = _safe_value(str(text))
    raw = value.encode("utf-8")
    if len(raw) > MAX_CANDIDATE_BYTES:
        return None, sha256(raw).hexdigest(), len(raw)
    return value, sha256(raw).hexdigest(), len(raw)


def _metrics(value):
    return asdict(value) if is_dataclass(value) else {}


class VerificationCandidateReceipts:
    def __init__(self, request, *, database=None, work_id=None,
                 work_revision_id=None, pwu_id=None, attempt_id=None):
        self.request = request
        self.database = database
        self.work_id = work_id
        self.work_revision_id = work_revision_id
        self.pwu_id = pwu_id
        self.attempt_id = attempt_id
        self.records = []
        if database is not None:
            from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
            with database.unit_of_work() as uow:
                for item in NativeExecutionStore(uow.session).evidence_for_attempt(attempt_id):
                    if (item.evidence_type == "VERIFICATION_CANDIDATE_RECEIPT"
                            and item.payload.get("verification_identity") == str(request.verification_identity)):
                        self.records.append({**item.payload, "receipt_ref": f"native-evidence:{item.id}"})

    def _append(self, component, attempt, stage, **values):
        rid = uuid4()
        payload = {"schema": "verification-candidate-receipt-v1",
            "verification_identity": str(self.request.verification_identity),
            "work_id": None if self.work_id is None else str(self.work_id),
            "work_reality_revision_id": None if self.work_revision_id is None else str(self.work_revision_id),
            "pwu_id": None if self.pwu_id is None else str(self.pwu_id),
            "attempt_id": None if self.attempt_id is None else str(self.attempt_id),
            "snapshot_id": str(self.request.snapshot_id),
            "source_baseline_id": str(self.request.source_baseline_id),
            "candidate_revision": self.request.proposed_commit_identity,
            "candidate_tree": self.request.tree_identity,
            "decision_context_fingerprint": self.request.decision_context_fingerprint,
            "fact_refs": [str(item.fact_id) for item in self.request.semantic_fact_obligations],
            "context_refs": [{key: getattr(item, key) for key in
                ("context_class", "semantic_key", "source_ref", "source_revision", "content_digest", "package_fingerprint")}
                for item in self.request.protected_context_obligations],
            "component": component, "attempt": attempt, "stage": stage,
            "recorded_at_utc": datetime.now(UTC).isoformat(), "budget_limit": 2,
            "candidate_is_authority": False, **_safe_value(values)}
        payload = _safe_value(payload)
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
        if len(encoded) > MAX_CANDIDATE_BYTES * 2:
            payload = {key: value for key, value in payload.items() if key not in
                {"candidate_output", "candidate_checks", "feedback"}}
            payload.update(receipt_truncated=True, candidate_retained=False,
                failed_predicate="CANDIDATE_RECEIPT_LIMIT", terminal=True, validation_passed=False,
                terminal_reason="CANDIDATE_RECEIPT_LIMIT", omitted_payload_sha256=sha256(encoded).hexdigest())
        if self.database is not None:
            from spg.domain.native_execution import ExecutionEvidenceRecord
            from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
            raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
            record = ExecutionEvidenceRecord(id=rid, pwu_id=self.pwu_id,
                attempt_id=self.attempt_id, evidence_type="VERIFICATION_CANDIDATE_RECEIPT",
                producer_identity="spg-runtime:verification", subject_digest=sha256(
                    f"{self.request.proposed_commit_identity}:{self.request.tree_identity}".encode()).hexdigest(),
                payload=payload, content_digest=sha256(raw).hexdigest(), created_at=datetime.now(UTC))
            with self.database.unit_of_work() as uow:
                NativeExecutionStore(uow.session).insert_evidence(record)
                uow.commit()
        row = {**payload, "receipt_ref": f"native-evidence:{rid}" if self.database is not None else f"verification-metadata:{rid}"}
        self.records.append(row)
        return row

    def completed(self, component):
        rows = [r for r in self.records if r["component"] == component]
        terminal = [r for r in rows if r["stage"] == "CANDIDATE_VALIDATED" and r.get("terminal")]
        if terminal:
            row = terminal[-1]
            if not row.get("validation_passed"):
                raise VerificationCandidateFailure(row.get("terminal_reason") or "VERIFICATION_CANDIDATE_TERMINAL", self)
            return row
        pending = [r for r in rows if r["stage"] == "MODEL_REQUEST_PENDING"]
        validated = {r["attempt"] for r in rows if r["stage"] == "CANDIDATE_VALIDATED"}
        if any(r["attempt"] not in validated for r in pending):
            raise VerificationCandidateFailure("VERIFICATION_CANDIDATE_PENDING_OUTCOME_UNKNOWN", self)
        return None

    def begin(self, component, *, feedback=None):
        if self.completed(component) is not None:
            raise VerificationCandidateFailure("VERIFICATION_CANDIDATE_ALREADY_TERMINAL", self)
        prior = [r for r in self.records if r["component"] == component and r["stage"] == "MODEL_REQUEST_PENDING"]
        if len(prior) >= 2:
            raise ValueError("VERIFICATION_CANDIDATE_BUDGET_EXHAUSTED")
        attempt = len(prior) + 1
        self._append(component, attempt, "MODEL_REQUEST_PENDING", feedback=feedback)
        return attempt

    def observed(self, component, attempt, response):
        output, digest, size = _safe_output(response.output_text)
        row = self._append(component, attempt, "CANDIDATE_OBSERVED",
            candidate_output=output, candidate_output_sha256=digest,
            candidate_bytes=size, candidate_retained=output is not None,
            provider=response.provider.value, requested_model=getattr(response, "requested_model", None),
            effective_model=response.effective_model, request_id=response.request_id,
            usage=_metrics(response.usage), timing=_metrics(getattr(response, "timing", None)),
            transport_retry_count=getattr(response, "retry_count", None))
        if output is None:
            self.validated(component, attempt, predicate="CANDIDATE_RECEIPT_LIMIT", terminal=True)
            raise ValueError("VERIFICATION_CANDIDATE_RECEIPT_LIMIT")
        return row

    def validated(self, component, attempt, *, predicate=None, feedback=None,
                  checks=None, terminal=False, refinement_converged=None):
        row = self._append(component, attempt, "CANDIDATE_VALIDATED",
            failed_predicate=predicate, feedback=feedback,
            candidate_checks=checks, terminal=terminal,
            terminal_reason=predicate if terminal else None,
            validation_passed=predicate is None)
        if terminal and self.database is not None and self.work_id is not None:
            prior = [record for record in self.records if record["component"] == component
                and record["stage"] == "CANDIDATE_VALIDATED" and record.get("failed_predicate")]
            observed = [record for record in self.records if record["component"] == component
                and record["stage"] == "MODEL_REQUEST_PENDING"]
            completed = [record for record in self.records if record["component"] == component
                and record["stage"] == "BOUNDED_REFINEMENT_RECORDED"]
            if prior and not completed:
                from spg.domain.refinement_contract import RefinementSignalKind
                from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
                converged = predicate is None and len(observed) >= 2 and refinement_converged is not False
                with self.database.unit_of_work() as uow:
                    event = NativeExecutionStore(uow.session).record_bounded_refinement(
                        work_id=self.work_id, operation_id=self.request.verification_identity,
                        component=component, signal_kind=RefinementSignalKind.CONTRACT_MISMATCH,
                        signature_basis=prior[0].get("failed_predicate") or "VERIFICATION_CANDIDATE_INVALID",
                        evidence_references=tuple(item["receipt_ref"] for item in self.records
                            if item["component"] == component), converged=converged,
                        attempt_count=len(observed), diagnostic_evidence={
                            "candidate_is_authority": False, "current_work_pass": False,
                            "candidate_receipt_refs": [item["receipt_ref"] for item in self.records
                                if item["component"] == component]})
                    uow.commit()
                self._append(component, attempt, "BOUNDED_REFINEMENT_RECORDED",
                    self_refine_event_ref=f"self-refine-event:{event.id}",
                    converged=converged, local_obligation_only=True)
        if row.get("receipt_truncated"):
            raise ValueError("VERIFICATION_CANDIDATE_RECEIPT_LIMIT")
        return row

    def previous_checks(self, component):
        rows = [r for r in self.records if r["component"] == component
                and r["stage"] == "CANDIDATE_VALIDATED" and r.get("candidate_checks")]
        return () if not rows else rows[-1]["candidate_checks"]

    def metadata(self):
        return {"schema": "verification-candidate-receipts-v1", "attempt_budget": 2,
            "receipt_refs": [r["receipt_ref"] for r in self.records], "records": list(self.records)}


class VerificationCandidateFailure(ValueError):
    def __init__(self, code, recorder):
        super().__init__(code)
        self.verification_metadata = {"failure_code": code,
                                     "verification_candidate_receipts": recorder.metadata()}
