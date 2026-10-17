"""Document scope uses typed artifact paths and preserves exact proof admission."""
from dataclasses import replace
import json

import pytest

from spg.application.planning import ProductionPlanningService
from spg.application.semantic_steps import SemanticStepApplicationService
from spg.domain.change import ProductionTargetKind
from spg.domain.planning import PlannedArtifactOperation, ProductionPlanArtifactTarget
from spg.domain.steering import SemanticProductionProposal, SemanticStepResultCandidate
from spg.providers.rule_based_planner import RuleBasedProductionPlanner
from tests.test_c3_greenfield_target_proof import exact_source, scope_fixture
from tests.test_dogfood_repository_scope import _git


def document_fixture(source, path, *, existing=False):
    value, _, capability, runtime = scope_fixture(source)
    human = "先给出活动报名系统的设计方案供审阅，确认后再实施"
    value = value.model_copy(update={
        "desired_outcome": "Create a working browser registration application",
        "work_requests": ("Present a design plan",),
        "constraints": ("Do not implement before Human review",),
        "human_explicit_requests": (human,),
    })
    proposal = SemanticProductionProposal(target_kind=ProductionTargetKind.DOCUMENTATION_WORK,
        objective="Produce the registration system design for review before implementation",
        artifact_targets=(ProductionPlanArtifactTarget(path=path,
            operation=PlannedArtifactOperation.UPDATE if existing else PlannedArtifactOperation.CREATE),),
        verification_expectation="Review the plan's completeness and preserve the implementation hold")
    proof = {"path": path, "human_clause": human,
        "necessity": "The requested reviewable design needs the single document artifact.",
        **({"evidence_kind": "EXISTING_IMPLEMENTATION", "source_path": path,
            "repository_quote": "Existing design to revise"} if existing else
           {"evidence_kind": "NEW_TARGET", "source_revision": value.source_revision,
            "source_tree": value.source_tree})}
    validation = {"required_targets": [proof], "rejected_behaviors": [],
        "explanation": "Controlled semantic fixture for the authorized documentation phase.",
        "requirement_coverage": [{"requirement": text, "disposition": "REQUIRED_TARGET",
            "target_paths": [path], "explanation": "The document must cover this unchanged requirement."}
            for text in dict.fromkeys((*value.work_requests, value.desired_outcome, *value.constraints))]}
    if existing:
        validation["requirement_coverage"] = validation["requirement_coverage"][-1:]
    original = runtime.generate
    runtime.generate = lambda **options: replace(original(**options), output_text=json.dumps(validation))
    return value, proposal, capability, runtime, validation


@pytest.mark.parametrize("path", ["docs/design/registration.md", "方案/报名设计.md"])
def test_new_document_scope_materializes_only_authorized_artifact(exact_source, path):
    value, proposal, capability, runtime, _ = document_fixture(exact_source, path)
    service = SemanticStepApplicationService.__new__(SemanticStepApplicationService)
    service.capability = capability
    service.planning = ProductionPlanningService(RuleBasedProductionPlanner())
    plan, change = service._materialize_production_plan(value,
        SemanticStepResultCandidate.model_construct(proposed_production=proposal))
    assert len(runtime.calls) == 1
    payload = json.loads(runtime.calls[0]["input_text"])
    assert payload["candidate_paths"] == [path]
    assert payload["candidate_path_exists"] == {path: False}
    assert payload["canonical_outcome"] == value.desired_outcome
    assert payload["constraints"] == list(value.constraints)
    assert plan.artifact_targets == proposal.artifact_targets
    assert plan.objective == proposal.objective
    assert plan.desired_outcome == value.desired_outcome
    assert plan.inherited_constraints == value.constraints
    assert plan.target_kind is ProductionTargetKind.DOCUMENTATION_WORK
    assert change is None and proposal.code_targets == ()


def test_existing_document_supplies_exact_source_for_necessity_witness(exact_source):
    repo, _, _ = exact_source
    path = "docs/design.md"
    (repo / "docs").mkdir()
    (repo / path).write_text("Existing design to revise\n")
    _git(repo, "add", ".")
    _git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-m", "existing design")
    source = repo, _git(repo, "rev-parse", "HEAD"), _git(repo, "rev-parse", "HEAD^{tree}")
    value, proposal, capability, runtime, _ = document_fixture(source, path, existing=True)
    result = capability.validate_production_scope(value, proposal)
    assert not result.missing_acceptance_requirements
    payload = json.loads(runtime.calls[0]["input_text"])
    assert payload["candidate_path_exists"] == {path: True}
    assert payload["observed_sources"][path] == "Existing design to revise\n"
    assert len(runtime.calls) == 1


@pytest.mark.parametrize("failure", ["outside-target", "stale-revision", "stale-tree", "missing-requirement"])
def test_document_scope_keeps_proof_and_coverage_negatives(exact_source, failure):
    value, proposal, capability, runtime, validation = document_fixture(exact_source, "plans/review.md")
    if failure == "outside-target":
        validation["required_targets"][0]["path"] = "unrequested/other.md"
    elif failure == "stale-revision":
        validation["required_targets"][0]["source_revision"] = "0" * 40
    elif failure == "stale-tree":
        validation["required_targets"][0]["source_tree"] = "0" * 40
    else:
        validation["requirement_coverage"].pop()
    result = capability.validate_production_scope(value, proposal)
    assert result.missing_acceptance_requirements
    assert len(runtime.calls) == 2
    assert json.loads(runtime.calls[1]["input_text"])["coverage_feedback"]
