from uuid import uuid4

from pydantic import ValidationError
import pytest

from spg.api.dto import AttentionResponse
from spg.domain.product import AttentionItem, AttentionKind
from spg.domain.steering import (
    NextStepCandidate,
    PlanFrame,
    PlanSteeringCapability,
    RealityReference,
    RealityReferenceKind,
    SteeringAttentionReason,
    SteeringAuthorityAssessment,
    SteeringOutcome,
    SteeringStepType,
)


def _candidate(
    *,
    reason: str = "Governed Work and Step Reality support the next direction",
    provider: str | None = None,
) -> NextStepCandidate:
    return NextStepCandidate(
        type=SteeringStepType.PRODUCE,
        objective="Produce the admitted bounded capability",
        reason=reason,
        reality_refs=(
            RealityReference(kind=RealityReferenceKind.WORK, identity=uuid4()),
        ),
        human_required=False,
        completion_condition="The bounded production result is trusted",
        proposed_outcome=SteeringOutcome.AUTO_CONTINUE,
        basis_fingerprint="a" * 64,
        authority_assessment=SteeringAuthorityAssessment.WITHIN_AUTHORITY,
        proposed_engineering_scope_fingerprint="b" * 64,
        reasoning_provider_identity=provider,
    )


def test_steer_dec_01_02_03_04_plan_frame_is_ephemeral_and_provider_neutral() -> None:
    assert "id" not in PlanFrame.model_fields
    assert "created_at" not in PlanFrame.model_fields
    assert PlanSteeringCapability.__module__ == "spg.domain.steering"
    assert NextStepCandidate.__module__ == "spg.domain.steering"
    assert "openai" not in repr(PlanSteeringCapability).casefold()
    assert "codex" not in repr(NextStepCandidate.model_fields).casefold()


def test_steer_dec_08_provider_metadata_and_reason_wording_are_not_material_direction() -> None:
    first = _candidate(reason="Persisted Reality supports production", provider="fake:a")
    second = _candidate(
        reason="The governed facts make bounded production appropriate",
        provider="fake:b",
    )
    assert first.material_direction_fingerprint == second.material_direction_fingerprint


@pytest.mark.parametrize("attention_reason", tuple(SteeringAttentionReason))
def test_steer_dec_10_all_five_mvp_attention_reasons_are_representable(
    attention_reason: SteeringAttentionReason,
) -> None:
    candidate = NextStepCandidate(
        type=SteeringStepType.HUMAN_DECISION,
        objective=f"Resolve {attention_reason.value}",
        reason="Current governed Reality leaves a material Human-owned decision",
        reality_refs=(
            RealityReference(kind=RealityReferenceKind.WORK, identity=uuid4()),
        ),
        human_required=True,
        completion_condition="Human Authority records the material direction",
        proposed_outcome=SteeringOutcome.HUMAN_ATTENTION,
        basis_fingerprint="c" * 64,
        authority_assessment=SteeringAuthorityAssessment.UNCERTAIN,
        attention_reason=attention_reason,
        recommendation="Choose the bounded option that preserves the admitted objective",
        alternatives=("Narrow the direction", "Revise the admitted scope"),
        trade_offs=("Scope versus delivery cost",),
        expected_impact="The decision controls subsequent Steering",
    )
    assert candidate.attention_reason is attention_reason


def test_steer_dec_11_12_attention_is_material_and_authority_uncertainty_stops() -> None:
    with pytest.raises(ValidationError, match="Authority uncertainty"):
        NextStepCandidate(
            **_candidate().model_dump(exclude={"authority_assessment"}),
            authority_assessment=SteeringAuthorityAssessment.UNCERTAIN,
        )
    with pytest.raises(ValidationError, match="material decision"):
        NextStepCandidate(
            type=SteeringStepType.HUMAN_DECISION,
            objective="Continue?",
            reason="A material decision is required",
            reality_refs=(
                RealityReference(kind=RealityReferenceKind.WORK, identity=uuid4()),
            ),
            human_required=True,
            completion_condition="Human decision recorded",
            proposed_outcome=SteeringOutcome.HUMAN_ATTENTION,
            basis_fingerprint="d" * 64,
            authority_assessment=SteeringAuthorityAssessment.UNCERTAIN,
            attention_reason=SteeringAttentionReason.SCOPE_OR_AUTHORITY_EXPANSION,
            recommendation="Clarify authority",
            expected_impact="Determines whether activity is permitted",
        )


def test_steer_dec_14_candidate_authorization_is_not_steering_attention() -> None:
    assert AttentionKind.CANDIDATE_AUTHORIZATION is not AttentionKind.STEERING_DECISION_REQUIRED


def test_steering_attention_api_projection_exposes_decision_context() -> None:
    work_id = uuid4()
    revision_id = uuid4()
    step_id = uuid4()
    reference = RealityReference(kind=RealityReferenceKind.WORK, identity=work_id)
    item = AttentionItem(
        id=uuid4(),
        work_id=work_id,
        kind=AttentionKind.STEERING_DECISION_REQUIRED,
        decision="Choose the product direction",
        reason="Persisted Reality leaves a material Human-owned decision",
        available_actions=(),
        recommended_action=None,
        governed_subject_ref="steering-decision:test",
        steering_reason=(
            SteeringAttentionReason.MAJOR_PRODUCT_OR_ARCHITECTURE_DECISION
        ),
        recommendation="Choose the bounded direction",
        alternatives=("Narrow option",),
        trade_offs=("Delivery cost",),
        expected_impact="Controls subsequent Steering",
        reality_refs=(reference,),
        steering_plan_revision_id=revision_id,
        steering_step_id=step_id,
    )
    response = AttentionResponse.from_projection(item)
    assert response.steering_reason is item.steering_reason
    assert response.recommendation == item.recommendation
    assert response.reality_refs == (reference,)
    assert response.steering_plan_revision_id == revision_id
    assert response.steering_step_id == step_id
