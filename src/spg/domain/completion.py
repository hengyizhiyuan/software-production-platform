"""S3-A Completion Evaluation contracts and Produced semantics."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from spg.domain.execution import ArtifactChangeType
from spg.domain.runtime import WorkUnitRecord


class CompletionEvaluationOutcome(StrEnum):
    """Factual output-obligation result, independent from provider outcome."""

    PRODUCED = "PRODUCED"
    NOT_PRODUCED = "NOT_PRODUCED"


class CompletionObligationType(StrEnum):
    REQUIRED_ARTIFACT = "REQUIRED_ARTIFACT"
    REQUIRED_CHANGE = "REQUIRED_CHANGE"
    REQUIRED_CHANGE_SCOPE = "REQUIRED_CHANGE_SCOPE"
    REQUIRED_MARKER = "REQUIRED_MARKER"
    FORBIDDEN_CHANGE = "FORBIDDEN_CHANGE"
    BLOCKING_CONDITION = "BLOCKING_CONDITION"


class CompletionObligationResultValue(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class CompletionObligationResult(BaseModel):
    """Lightweight deterministic explanation; not Assurance Evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    obligation_type: CompletionObligationType
    subject: str
    expected: str
    observed: str
    result: CompletionObligationResultValue
    reason: str


class CompletionWorkProductLineage(BaseModel):
    """Exact Work Product reference identity included in an evaluation basis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reference_id: UUID
    artifact_path: str
    change_type: ArtifactChangeType
    source_fingerprint: str | None
    observed_fingerprint: str | None


class CompletionEvaluationRecord(BaseModel):
    """Immutable durable Completion Evaluation bound to one exact observation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    production_run_id: UUID
    work_unit_id: UUID
    plan_revision_id: UUID
    source_baseline_id: UUID
    attempt_id: UUID
    generation: int
    completion_contract_fingerprint: str
    repository_observation_id: UUID
    repository_observation_fingerprint: str
    work_product_lineage: tuple[CompletionWorkProductLineage, ...]
    work_product_set_fingerprint: str
    basis_fingerprint: str
    outcome: CompletionEvaluationOutcome
    obligation_results: tuple[CompletionObligationResult, ...]
    created_at: datetime


class CompletionEvaluationResult(BaseModel):
    """Application result exposing the evaluation and resulting PWU projection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation: CompletionEvaluationRecord
    work_unit: WorkUnitRecord
