from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from spg.application.measurement import ProductionMeasurementService
from spg.domain.measurement import (
    MeasurementAvailability,
    MeasurementDerivation,
    MeasurementSourceReference,
    ProductionMeasurementKind,
    ProductionMeasurementScope,
    ProductionMeasurementV0,
    ProductionPhase,
)
from spg.domain.planning import (
    OnePwuFitClassification,
    PlannedArtifactOperation,
    ProductionPlanArtifactTarget,
    ProductionPlanningRequest,
)
from spg.providers.rule_based_planner import RuleBasedProductionPlanner


def test_dcp2_observed_derived_and_unavailable_semantics_are_distinct() -> None:
    start = datetime(2026, 9, 6, 10, 0, tzinfo=UTC)
    source_id = uuid4()
    measurement = ProductionMeasurementService._interval(
        kind=ProductionMeasurementKind.MACHINE_EXECUTION,
        scope=ProductionMeasurementScope.AGGREGATE_PROVIDER_EXECUTION,
        phase=ProductionPhase.EXECUTION,
        subject_type="PROVIDER_EXECUTION_REPORT",
        subject_id=source_id,
        work_id=uuid4(),
        work_unit_id=uuid4(),
        attempt_id=uuid4(),
        started_at=start,
        finished_at=start + timedelta(seconds=2, microseconds=345),
        source_facts=(
            MeasurementSourceReference(
                fact_type="PROVIDER_EXECUTION_REPORT",
                fact_id=source_id,
                field_name="started_at",
                observed_at=start,
            ),
            MeasurementSourceReference(
                fact_type="PROVIDER_EXECUTION_REPORT",
                fact_id=source_id,
                field_name="finished_at",
                observed_at=start + timedelta(seconds=2, microseconds=345),
            ),
        ),
        internal_turn_count=2,
        self_refine_occurred=True,
    )

    assert measurement.availability is MeasurementAvailability.AVAILABLE
    assert measurement.derivation is MeasurementDerivation.DERIVED_INTERVAL
    assert measurement.duration_microseconds == 2_000_345
    assert measurement.internal_turn_count == 2
    assert measurement.self_refine_occurred is True
    assert "task_duration" not in ProductionMeasurementV0.model_fields


def test_dcp2_unavailable_measurement_cannot_carry_fabricated_timing() -> None:
    with pytest.raises(ValidationError, match="cannot contain timing values"):
        ProductionMeasurementV0(
            measurement_id=uuid4(),
            kind=ProductionMeasurementKind.VERIFICATION,
            scope=ProductionMeasurementScope.PWU_VERIFICATION_TOTAL,
            phase=ProductionPhase.VERIFICATION,
            availability=MeasurementAvailability.UNAVAILABLE,
            derivation=MeasurementDerivation.UNAVAILABLE,
            subject_type="PRODUCTION_WORK_UNIT",
            subject_id=uuid4(),
            work_id=uuid4(),
            duration_microseconds=1,
            unavailable_reason="No authoritative aggregate start/end boundary",
            basis_fingerprint="a" * 64,
        )


def test_dcp2_import_does_not_change_plan_1b_classification() -> None:
    resource_id = uuid4()
    baseline_id = uuid4()
    request = ProductionPlanningRequest(
        work_id=uuid4(),
        admitted_requirement="Create the admitted architecture note",
        desired_outcome="The architecture note exists",
        production_objective="Create one bounded architecture note",
        artifact_targets=(
            ProductionPlanArtifactTarget(
                path="docs/architecture/note.md",
                operation=PlannedArtifactOperation.CREATE,
            ),
        ),
        verification_expectation="Verify the exact admitted artifact",
        engineering_scope_summary="docs/architecture",
        engineering_resource_id=resource_id,
        repository_identity="test://dcp2",
        source_baseline_id=baseline_id,
        source_revision="a" * 40,
    )
    planner = RuleBasedProductionPlanner()

    before = planner.propose(request)
    _ = ProductionMeasurementV0.model_fields
    after = planner.propose(request)

    assert before.fit_classification is OnePwuFitClassification.ONE_PWU_FIT
    assert after.fit_classification is before.fit_classification
    assert after.artifact_targets == before.artifact_targets
