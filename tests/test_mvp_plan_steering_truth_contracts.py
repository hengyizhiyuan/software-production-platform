from datetime import UTC, datetime
from uuid import uuid4

import pytest

from spg.domain.planning import ProductionPlanProposal
from spg.domain.runtime import PlanRevisionRecord
from spg.domain.steering import (
    RealityReference,
    RealityReferenceKind,
    SteeringDecisionRecord,
    SteeringOutcome,
    SteeringPlanRecord,
    SteeringPlanRevisionRecord,
    SteeringStepType,
)


def test_steer_truth_01_02_plan_concepts_are_explicitly_distinct() -> None:
    assert SteeringPlanRecord is not ProductionPlanProposal
    assert SteeringPlanRevisionRecord is not PlanRevisionRecord
    assert "production_run_id" not in SteeringPlanRevisionRecord.model_fields
    assert "ordered_steps" not in SteeringPlanRecord.model_fields


def test_steer_truth_12_reality_reference_contains_identity_not_payload() -> None:
    reference = RealityReference(
        kind=RealityReferenceKind.VERIFICATION,
        identity=uuid4(),
    )

    assert set(reference.model_dump()) == {"kind", "identity"}


def test_steer_truth_14_provider_identity_is_optional_metadata_not_authority() -> None:
    decision = SteeringDecisionRecord(
        id=uuid4(),
        steering_plan_revision_id=uuid4(),
        current_step_id=uuid4(),
        next_step_type=SteeringStepType.DESIGN,
        objective="Establish the next design fact",
        reason="Governed Work remains under-specified",
        reality_refs=(
            RealityReference(
                kind=RealityReferenceKind.WORK,
                identity=uuid4(),
            ),
        ),
        human_required=False,
        completion_condition="The design fact is persisted",
        steering_outcome=SteeringOutcome.AUTO_CONTINUE,
        basis_fingerprint="a" * 64,
        reasoning_provider_identity=None,
        created_at=datetime.now(UTC),
    )

    assert decision.reasoning_provider_identity is None
    assert "Codex" not in type(decision).__module__
    assert "OpenAI" not in type(decision).__module__


def test_human_attention_outcome_requires_human() -> None:
    with pytest.raises(ValueError, match="HUMAN_ATTENTION"):
        SteeringDecisionRecord(
            id=uuid4(),
            steering_plan_revision_id=uuid4(),
            current_step_id=uuid4(),
            next_step_type=SteeringStepType.HUMAN_DECISION,
            objective="Choose the material direction",
            reason="The choice belongs to Human Authority",
            reality_refs=(
                RealityReference(
                    kind=RealityReferenceKind.WORK,
                    identity=uuid4(),
                ),
            ),
            human_required=False,
            completion_condition="A governed decision is recorded",
            steering_outcome=SteeringOutcome.HUMAN_ATTENTION,
            basis_fingerprint="b" * 64,
            reasoning_provider_identity="provider-neutral:test",
            created_at=datetime.now(UTC),
        )
