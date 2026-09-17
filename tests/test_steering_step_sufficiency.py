from uuid import uuid4

import pytest
from pydantic import ValidationError

from spg.domain.steering import (
    RealityReference,
    RealityReferenceKind,
    SemanticResultKind,
    SemanticStepResultCandidate,
    SteeringAuthorityAssessment,
    SteeringStepType,
)


def _candidate(
    *,
    summary: str,
    authority: SteeringAuthorityAssessment,
    unresolved: tuple[str, ...] = (),
    recommendation: str | None = None,
    completion_claimed: bool,
) -> SemanticStepResultCandidate:
    return SemanticStepResultCandidate(
        work_id=uuid4(),
        steering_plan_revision_id=uuid4(),
        step_id=uuid4(),
        step_type=SteeringStepType.DESIGN,
        basis_fingerprint="a" * 64,
        result_kind=SemanticResultKind.DESIGN_DIRECTION,
        bounded_summary=summary,
        decisions=("Apply the step-scoped sufficiency rule.",),
        evidence_refs=(
            RealityReference(kind=RealityReferenceKind.WORK, identity=uuid4()),
        ),
        unresolved_questions=unresolved,
        authority_assessment=authority,
        human_attention_recommendation=recommendation,
        completion_claimed=completion_claimed,
    )


@pytest.mark.parametrize(
    "summary",
    (
        "A button with an observable hello Watt alert is bounded and verifiable.",
        "The existing login button text change is bounded by repository Reality.",
    ),
)
def test_bounded_engineering_work_has_no_product_discovery_blocker(
    summary: str,
) -> None:
    candidate = _candidate(
        summary=summary,
        authority=SteeringAuthorityAssessment.WITHIN_AUTHORITY,
        completion_claimed=True,
    )
    assert candidate.unresolved_questions == ()
    assert candidate.human_attention_recommendation is None


@pytest.mark.parametrize(
    ("authority", "question"),
    (
        (
            SteeringAuthorityAssessment.UNCERTAIN,
            "Should administrator access apply to every user or only accountable owners?",
        ),
        (
            SteeringAuthorityAssessment.EXPANDS_AUTHORITY,
            "May production destroy retained data instead of preserving it?",
        ),
        (
            SteeringAuthorityAssessment.UNCERTAIN,
            "Which materially different audience and outcome should govern the enterprise site?",
        ),
    ),
)
def test_material_human_owned_choice_blocks_truthfully(
    authority: SteeringAuthorityAssessment,
    question: str,
) -> None:
    candidate = _candidate(
        summary="Current governed Reality leaves a material Human-owned decision.",
        authority=authority,
        unresolved=(question,),
        recommendation="Choose the bounded direction before this step continues.",
        completion_claimed=False,
    )
    assert candidate.unresolved_questions == (question,)
    assert candidate.human_attention_recommendation is not None


@pytest.mark.parametrize(
    ("authority", "unresolved", "recommendation"),
    (
        (
            SteeringAuthorityAssessment.WITHIN_AUTHORITY,
            ("Which routine implementation detail should Watt choose?",),
            "Ask the Human to choose.",
        ),
        (
            SteeringAuthorityAssessment.UNCERTAIN,
            (),
            "Ask the Human without a material current-step question.",
        ),
    ),
)
def test_human_attention_requires_both_authority_and_materiality(
    authority: SteeringAuthorityAssessment,
    unresolved: tuple[str, ...],
    recommendation: str,
) -> None:
    with pytest.raises(ValidationError, match="requires both"):
        _candidate(
            summary="An incomplete blocker does not satisfy both required conditions.",
            authority=authority,
            unresolved=unresolved,
            recommendation=recommendation,
            completion_claimed=False,
        )
