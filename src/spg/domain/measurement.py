"""DCP-2 normalized production measurement and planning-time shape contracts."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from spg.domain.change import ProductionTargetKind


PRODUCTION_MEASUREMENT_VERSION = "DCP2_PRODUCTION_MEASUREMENT_V0"
TASK_SHAPE_VERSION = "DCP2_TASK_SHAPE_V0"


class ProductionPhase(StrEnum):
    ADMISSION = "ADMISSION"
    EXECUTION = "EXECUTION"
    VERIFICATION = "VERIFICATION"
    HUMAN_WAIT = "HUMAN_WAIT"
    INTEGRATION = "INTEGRATION"
    TRUSTED_COMPLETION = "TRUSTED_COMPLETION"


class ProductionMeasurementKind(StrEnum):
    MACHINE_EXECUTION = "MACHINE_EXECUTION"
    VERIFICATION = "VERIFICATION"
    HUMAN_WAIT = "HUMAN_WAIT"
    INTEGRATION = "INTEGRATION"
    TOTAL_STEERING_CYCLE = "TOTAL_STEERING_CYCLE"


class ProductionMeasurementScope(StrEnum):
    AGGREGATE_PROVIDER_EXECUTION = "AGGREGATE_PROVIDER_EXECUTION"
    VERIFICATION_OBLIGATION = "VERIFICATION_OBLIGATION"
    PWU_VERIFICATION_TOTAL = "PWU_VERIFICATION_TOTAL"
    CANDIDATE_AUTHORIZATION_WAIT = "CANDIDATE_AUTHORIZATION_WAIT"
    INTEGRATION_CONVERGENCE = "INTEGRATION_CONVERGENCE"
    LONG_LIVED_WORK_CYCLE = "LONG_LIVED_WORK_CYCLE"


class MeasurementAvailability(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class MeasurementDerivation(StrEnum):
    DERIVED_INTERVAL = "DERIVED_INTERVAL"
    OBSERVED_DURATION = "OBSERVED_DURATION"
    UNAVAILABLE = "UNAVAILABLE"


class MeasurementSourceReference(BaseModel):
    """Exact authoritative field used as a measurement basis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_type: str = Field(min_length=1)
    fact_id: UUID
    field_name: str = Field(min_length=1)
    observed_at: datetime


class ProductionMeasurementV0(BaseModel):
    """Reconstructable measurement projection; never production Authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    measurement_id: UUID
    semantic_version: str = PRODUCTION_MEASUREMENT_VERSION
    kind: ProductionMeasurementKind
    scope: ProductionMeasurementScope
    phase: ProductionPhase
    availability: MeasurementAvailability
    derivation: MeasurementDerivation
    subject_type: str = Field(min_length=1)
    subject_id: UUID
    work_id: UUID
    work_unit_id: UUID | None = None
    attempt_id: UUID | None = None
    observed_start_at: datetime | None = None
    observed_end_at: datetime | None = None
    duration_microseconds: int | None = Field(default=None, ge=0)
    source_facts: tuple[MeasurementSourceReference, ...] = ()
    internal_turn_count: int | None = Field(default=None, ge=1)
    self_refine_occurred: bool | None = None
    unavailable_reason: str | None = None
    basis_fingerprint: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def require_truthful_availability(self) -> "ProductionMeasurementV0":
        if self.availability is MeasurementAvailability.UNAVAILABLE:
            if self.derivation is not MeasurementDerivation.UNAVAILABLE:
                raise ValueError("unavailable measurement must use UNAVAILABLE derivation")
            if any(
                value is not None
                for value in (
                    self.observed_start_at,
                    self.observed_end_at,
                    self.duration_microseconds,
                )
            ):
                raise ValueError("unavailable measurement cannot contain timing values")
            if not self.unavailable_reason or not self.unavailable_reason.strip():
                raise ValueError("unavailable measurement requires a reason")
            return self

        if self.derivation is MeasurementDerivation.UNAVAILABLE:
            raise ValueError("available measurement requires a timing derivation")
        if self.duration_microseconds is None:
            raise ValueError("available measurement requires a duration")
        if self.unavailable_reason is not None:
            raise ValueError("available measurement cannot have an unavailable reason")
        if not self.source_facts:
            raise ValueError("available measurement requires exact source facts")
        if self.derivation is MeasurementDerivation.DERIVED_INTERVAL:
            if self.observed_start_at is None or self.observed_end_at is None:
                raise ValueError("derived interval requires observed start and end")
            if self.observed_end_at < self.observed_start_at:
                raise ValueError("measurement end cannot precede start")
        elif self.observed_start_at is not None or self.observed_end_at is not None:
            raise ValueError("observed duration does not invent start/end timestamps")
        return self


class TaskShapeSourceReference(BaseModel):
    """Immutable planning fact from which a shape field is reconstructed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_type: str = Field(min_length=1)
    fact_id: UUID
    field_name: str = Field(min_length=1)


class TaskShapeSnapshotV0(BaseModel):
    """Planning-time PWU shape reconstructed only from admitted immutable facts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: UUID
    semantic_version: str = TASK_SHAPE_VERSION
    captured_at: datetime
    work_id: UUID
    production_plan_revision_id: UUID
    production_plan_proposal_id: UUID | None = None
    work_unit_id: UUID
    resource_id: UUID
    source_baseline_id: UUID
    repository_identity: str = Field(min_length=1)
    target_kind: ProductionTargetKind | None = None
    target_path_count: int = Field(ge=0)
    create_count: int = Field(ge=0)
    update_count: int = Field(ge=0)
    allowed_scope_count: int = Field(ge=0)
    forbidden_scope_count: int = Field(ge=0)
    required_output_count: int = Field(ge=0)
    required_change_count: int = Field(ge=0)
    verification_obligation_count: int = Field(ge=0)
    ordered_planning_step_count: int = Field(ge=0)
    context_reference_count: int | None = Field(default=None, ge=0)
    executor_capability_identity: str | None = None
    executor_profile_identity: str | None = None
    unavailable_facts: tuple[str, ...] = ()
    source_facts: tuple[TaskShapeSourceReference, ...] = Field(min_length=1)
    basis_fingerprint: str = Field(min_length=64, max_length=64)


class ProductionMeasurementSampleV0(BaseModel):
    """Internal analysis view for one PWU; no scheduling or admission effect."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_shape: TaskShapeSnapshotV0
    measurements: tuple[ProductionMeasurementV0, ...]
