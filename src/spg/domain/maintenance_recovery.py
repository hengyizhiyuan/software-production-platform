"""R4-B contracts for verified maintenance and production-lineage recovery."""

from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from spg.domain.runtime import (
    BaselinePointerRecord,
    CompletionContract,
    InitialRuntimeSpine,
    PlanRevisionRecord,
    ProductionHorizon,
    ProductionRunRecord,
    SnapshotRecord,
    WorkUnitRecord,
)


class MaintenanceEvidenceResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class MaintenanceAdmissionOutcome(StrEnum):
    APPLIED = "APPLIED"


class MaintenanceVerificationSuiteEvidence(BaseModel):
    """Exact terminal counts for one deterministic verification command/suite."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    suite_identity: str = Field(min_length=1)
    command_identity: str = Field(min_length=1)
    collected: int = Field(ge=0)
    selected: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    deselected: int = Field(ge=0)
    terminal_result: MaintenanceEvidenceResult

    @model_validator(mode="after")
    def require_coherent_terminal_counts(self) -> "MaintenanceVerificationSuiteEvidence":
        if self.selected != self.passed + self.failed + self.skipped:
            raise ValueError("selected must equal passed + failed + skipped")
        if self.collected != self.selected + self.deselected:
            raise ValueError("collected must equal selected + deselected")
        if self.terminal_result is MaintenanceEvidenceResult.PASS and self.failed:
            raise ValueError("PASS terminal evidence cannot contain failures")
        if self.terminal_result is MaintenanceEvidenceResult.FAIL and not self.failed:
            raise ValueError("FAIL terminal evidence must contain a failure")
        return self


class MaintenanceCheckEvidence(BaseModel):
    """Narrow non-suite terminal evidence such as compile, lock, migration, or diff."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    check_identity: str = Field(min_length=1)
    command_identity: str = Field(min_length=1)
    terminal_result: MaintenanceEvidenceResult


class MaintenanceVerificationEvidence(BaseModel):
    """Canonical evidence for one exact maintenance repository Reality."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_identity: str = Field(min_length=1)
    authoritative_ref: str = Field(min_length=1)
    target_commit: str = Field(min_length=1)
    target_tree: str = Field(min_length=1)
    accepted_changed_paths: tuple[str, ...]
    suites: tuple[MaintenanceVerificationSuiteEvidence, ...] = Field(min_length=1)
    focused_evidence: tuple[str, ...] = Field(min_length=1)
    checks: tuple[MaintenanceCheckEvidence, ...] = ()
    produced_at: datetime
    evidence_fingerprint: str = Field(min_length=64, max_length=64)

    @field_validator("accepted_changed_paths")
    @classmethod
    def require_canonical_paths(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        canonical = tuple(sorted(set(values)))
        if not canonical:
            raise ValueError("maintenance changed-path scope cannot be empty")
        for value in canonical:
            _require_repository_relative_path(value)
        if values != canonical:
            raise ValueError("maintenance changed paths must be unique and sorted")
        return values

    @model_validator(mode="after")
    def require_exact_fingerprint(self) -> "MaintenanceVerificationEvidence":
        if self.evidence_fingerprint != maintenance_evidence_fingerprint(self):
            raise ValueError("maintenance verification evidence fingerprint mismatch")
        return self


class MaintenanceRecoveryAuthority(BaseModel):
    """Exact Human / Architecture Authority; permission only, never evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    authority_identity: str = Field(min_length=1)
    authorization_scope: tuple[str, ...] = Field(min_length=1)
    authorized_at: datetime
    old_trusted_baseline_id: UUID
    repository_identity: str = Field(min_length=1)
    authoritative_ref: str = Field(min_length=1)
    target_commit: str = Field(min_length=1)
    target_tree: str = Field(min_length=1)
    maintenance_purpose: str = Field(min_length=1)
    approved_changed_paths: tuple[str, ...] = Field(min_length=1)
    maintenance_evidence_fingerprint: str = Field(min_length=64, max_length=64)
    recovery_assessment_id: UUID
    old_run_id: UUID
    old_plan_revision_id: UUID
    old_work_unit_id: UUID
    old_attempt_id: UUID
    new_lineage_objective: str = Field(min_length=1)
    authority_fingerprint: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def require_exact_fingerprint(self) -> "MaintenanceRecoveryAuthority":
        if tuple(sorted(set(self.authorization_scope))) != self.authorization_scope:
            raise ValueError("authorization scope must be unique and sorted")
        if tuple(sorted(set(self.approved_changed_paths))) != self.approved_changed_paths:
            raise ValueError("approved changed paths must be unique and sorted")
        for value in self.approved_changed_paths:
            _require_repository_relative_path(value)
        if self.authority_fingerprint != maintenance_authority_fingerprint(self):
            raise ValueError("maintenance recovery authority fingerprint mismatch")
        return self


class NewProductionLineageAdmission(BaseModel):
    """Exact admitted inputs for a new internal Run/Plan/PWU lineage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    intent_ref: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    production_horizon: ProductionHorizon
    work_unit_objective: str = Field(min_length=1)
    completion_contract: CompletionContract


class VerifiedMaintenanceRecoveryRequest(BaseModel):
    """No-latest contract for one exact blocked lineage and maintenance target."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_path: Path
    expected_old_trusted_baseline_id: UUID
    expected_current_pointer_version: int = Field(ge=0)
    repository_identity: str = Field(min_length=1)
    authoritative_ref: str = Field(min_length=1)
    target_maintenance_commit: str = Field(min_length=1)
    target_maintenance_tree: str = Field(min_length=1)
    maintenance_purpose: str = Field(min_length=1)
    approved_changed_paths: tuple[str, ...] = Field(min_length=1)
    verification_evidence: MaintenanceVerificationEvidence
    authority: MaintenanceRecoveryAuthority
    recovery_assessment_id: UUID
    expected_recovery_assessment_fingerprint: str = Field(min_length=64, max_length=64)
    old_run_id: UUID
    expected_old_run_version: int = Field(ge=0)
    old_plan_revision_id: UUID
    expected_old_plan_version: int = Field(ge=0)
    old_work_unit_id: UUID
    expected_old_work_unit_version: int = Field(ge=0)
    old_attempt_id: UUID
    governance_contract_snapshot_identity: str = Field(min_length=1)
    governance_contract_snapshot_fingerprint: str = Field(min_length=64, max_length=64)
    new_lineage: NewProductionLineageAdmission

    @model_validator(mode="after")
    def require_exact_cross_contract_bindings(self) -> "VerifiedMaintenanceRecoveryRequest":
        expected_paths = tuple(sorted(set(self.approved_changed_paths)))
        if expected_paths != self.approved_changed_paths:
            raise ValueError("approved changed paths must be unique and sorted")
        for value in self.approved_changed_paths:
            _require_repository_relative_path(value)
        evidence = self.verification_evidence
        authority = self.authority
        exact_repository = (
            self.repository_identity,
            self.authoritative_ref,
            self.target_maintenance_commit,
            self.target_maintenance_tree,
        )
        if exact_repository != (
            evidence.repository_identity,
            evidence.authoritative_ref,
            evidence.target_commit,
            evidence.target_tree,
        ):
            raise ValueError("maintenance evidence repository target mismatch")
        if exact_repository != (
            authority.repository_identity,
            authority.authoritative_ref,
            authority.target_commit,
            authority.target_tree,
        ):
            raise ValueError("maintenance authority repository target mismatch")
        if self.approved_changed_paths != evidence.accepted_changed_paths:
            raise ValueError("maintenance evidence changed-path scope mismatch")
        if self.approved_changed_paths != authority.approved_changed_paths:
            raise ValueError("maintenance authority changed-path scope mismatch")
        if self.maintenance_purpose != authority.maintenance_purpose:
            raise ValueError("maintenance authority purpose mismatch")
        if evidence.evidence_fingerprint != authority.maintenance_evidence_fingerprint:
            raise ValueError("maintenance authority evidence mismatch")
        if self.expected_old_trusted_baseline_id != authority.old_trusted_baseline_id:
            raise ValueError("maintenance authority old Baseline mismatch")
        exact_lineage = (
            self.recovery_assessment_id,
            self.old_run_id,
            self.old_plan_revision_id,
            self.old_work_unit_id,
            self.old_attempt_id,
            self.new_lineage.work_unit_objective,
        )
        if exact_lineage != (
            authority.recovery_assessment_id,
            authority.old_run_id,
            authority.old_plan_revision_id,
            authority.old_work_unit_id,
            authority.old_attempt_id,
            authority.new_lineage_objective,
        ):
            raise ValueError("maintenance authority lineage mismatch")
        return self


class MaintenanceRepositoryReality(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_identity: str
    authoritative_ref: str
    target_commit: str
    target_tree: str
    old_revision: str
    changed_paths: tuple[str, ...]


class MaintenanceRecoveryAdmissionRecord(BaseModel):
    """One immutable admission and append-only resolution across two lineages."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    operation_fingerprint: str
    old_trusted_baseline_id: UUID
    new_trusted_baseline_id: UUID
    expected_pointer_version: int
    repository_identity: str
    authoritative_ref: str
    target_commit: str
    target_tree: str
    maintenance_purpose: str
    approved_changed_paths: tuple[str, ...]
    verification_evidence: MaintenanceVerificationEvidence
    maintenance_evidence_fingerprint: str
    authority: MaintenanceRecoveryAuthority
    maintenance_authority_fingerprint: str
    governance_record_id: UUID
    recovery_assessment_id: UUID
    recovery_assessment_fingerprint: str
    old_run_id: UUID
    old_plan_revision_id: UUID
    old_work_unit_id: UUID
    old_attempt_id: UUID
    new_run_id: UUID
    new_plan_revision_id: UUID
    new_work_unit_id: UUID
    governance_contract_snapshot_identity: str
    governance_contract_snapshot_fingerprint: str
    external_intent_ref: str
    outcome: MaintenanceAdmissionOutcome
    admitted_at: datetime


class VerifiedMaintenanceRecoveryResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    admission: MaintenanceRecoveryAdmissionRecord
    old_baseline: SnapshotRecord
    new_baseline: SnapshotRecord
    pointer: BaselinePointerRecord
    old_run: ProductionRunRecord
    old_plan_revision: PlanRevisionRecord
    old_work_unit: WorkUnitRecord
    new_lineage: InitialRuntimeSpine
    idempotent_recognition: bool


def maintenance_evidence_fingerprint(evidence: MaintenanceVerificationEvidence) -> str:
    return canonical_fingerprint(
        evidence.model_dump(mode="json", exclude={"evidence_fingerprint"})
    )


def maintenance_authority_fingerprint(authority: MaintenanceRecoveryAuthority) -> str:
    return canonical_fingerprint(
        authority.model_dump(mode="json", exclude={"authority_fingerprint"})
    )


def recovery_operation_fingerprint(request: VerifiedMaintenanceRecoveryRequest) -> str:
    basis = request.model_dump(mode="json", exclude={"repository_path"})
    return canonical_fingerprint(basis)


def canonical_fingerprint(value: Any) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(canonical).hexdigest()


def _require_repository_relative_path(value: str) -> None:
    if "\\" in value:
        raise ValueError("repository paths must use POSIX separators")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value in {"", "."}:
        raise ValueError("maintenance path must be repository-relative")
