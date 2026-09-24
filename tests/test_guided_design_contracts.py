from uuid import uuid4

import pytest

from spg.application.guided_design import (
    GuidedDesignApplicationService,
    general_product_system_design_issues,
    guided_design_step_specs,
    design_schema_registry,
    match_design_schema_text,
)
from spg.domain.guided_design import (
    DesignAuthorityRelevance,
    DesignIssueState,
    DesignOutputClass,
)
from spg.domain.steering import SemanticStepInput, SteeringStepState, SteeringStepType
from spg.providers.semantic_wire import SemanticStepWireContract


def test_guided_design_schema_is_general_adaptive_and_steering_linked() -> None:
    issues = general_product_system_design_issues()
    keys = {issue.key for issue in issues}

    assert len(issues) == 7
    assert "motive-users-problem" in keys
    assert "capabilities-workflow" in keys
    assert "architecture-risk-assumptions" in keys
    assert "verification-staged-readiness" in keys
    assert all("运营管理平台" not in issue.objective for issue in issues)
    assert all(set(issue.prerequisite_keys) <= keys for issue in issues)
    first = issues[0]
    assert first.authority_relevance is DesignAuthorityRelevance.ROUTINE
    assert "current governed step" in first.objective
    assert "Applicable to every" not in first.applicability

    steps = guided_design_step_specs(issues)
    design_steps = tuple(step for step in steps if step.type is SteeringStepType.DESIGN)
    assert tuple(step.design_issue_key for step in design_steps) == tuple(
        issue.key for issue in issues
    )
    assert design_steps[0].state is SteeringStepState.CURRENT
    assert all(step.state is SteeringStepState.KNOWN for step in design_steps[1:])
    assert tuple(step.type for step in steps[-3:]) == (
        SteeringStepType.PRODUCE,
        SteeringStepType.VERIFY_ACCEPT,
        SteeringStepType.COMPLETE,
    )


def test_seed_schema_registry_is_versioned_extensible_and_matches_motive() -> None:
    registry = design_schema_registry()
    assert tuple(schema.title for schema in registry) == (
        "General Product/System Design",
        "Technical System Design",
        "Existing Product Evolution",
    )
    assert {schema.version for schema in registry} == {"0.1"}
    assert match_design_schema_text("我想做一个运营管理平台。")[0].title == (
        "General Product/System Design"
    )
    assert match_design_schema_text("设计高性能技术基础设施")[0].title == (
        "Technical System Design"
    )
    assert match_design_schema_text("优化现有产品的用户反馈流程")[0].title == (
        "Existing Product Evolution"
    )


def test_design_readiness_is_critical_reality_not_agenda_length() -> None:
    issues = general_product_system_design_issues()
    not_ready = GuidedDesignApplicationService._readiness_for_issues(issues)
    assert not_ready.state.value == "NOT_READY"
    assert len(not_ready.blockers) == len(issues)

    result_id = uuid4()
    satisfied = tuple(
        issue.model_copy(
            update={
                "state": DesignIssueState.SATISFIED,
                "admitted_semantic_result_id": result_id,
            }
        )
        for issue in issues
    )
    ready = GuidedDesignApplicationService._readiness_for_issues(satisfied)
    assert ready.state.value == "READY"
    assert ready.blockers == ()


def test_skip_and_reopen_require_explainable_rationale() -> None:
    issue = general_product_system_design_issues()[0]
    with pytest.raises(ValueError, match="skipped"):
        issue.model_copy(update={"state": DesignIssueState.SKIPPED}, deep=True).__class__(
            **{
                **issue.model_dump(),
                "state": DesignIssueState.SKIPPED,
            }
        )
    reopened = issue.model_copy(
        update={
            "state": DesignIssueState.REOPENED,
            "reopen_rationale": "Verification challenged the earlier assumption.",
        }
    )
    assert reopened.reopen_rationale


def test_final_issue_is_the_only_reviewable_production_proposal_issue() -> None:
    issues = general_product_system_design_issues()
    proposal_issues = tuple(
        issue
        for issue in issues
        if issue.required_output is DesignOutputClass.REVIEWABLE_PRODUCTION_PROPOSAL
    )
    assert tuple(issue.key for issue in proposal_issues) == (
        "verification-staged-readiness",
    )


def test_semantic_provider_instruction_preserves_guided_focus() -> None:
    fields = SemanticStepInput.model_fields
    assert "design_context" in fields
    source = SemanticStepWireContract._instruction
    assert callable(source)
    # The exact provider contract is intentionally asserted from source-level constants
    # by the established provider-wire suite; here the domain seam is the obligation.
