"""R1 complete exact-tree CREATE proofs; controlled semantic candidates, no live model."""
from dataclasses import replace
from datetime import datetime, timezone
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from spg.application.planning import ProductionPlanningService
from spg.application.production_intelligence import TaskContractRequest, default_task_contract_builder
from spg.application.refinement import RepositoryChangeProposalService
from spg.application.semantic_steps import SemanticStepApplicationService
from spg.application.work import WorkApplicationService
from spg.domain.change import ChangeOperation, CodeVerificationKind, ProductionTargetKind
from spg.domain.model_runtime import ModelUsage
from spg.domain.refinement import (
    RepositoryChangeProposalRequest, RepositoryScopeValidation,
    RepositoryTargetNecessityProof, ScopeRequirementCoverage,
)
from spg.domain.steering import (RealityReference, RealityReferenceKind, SemanticProductionProposal,
    SemanticStepInput, SemanticStepResultCandidate, SteeringStepRecord, SteeringStepState, SteeringStepType)
from spg.providers.deepseek_semantic import DeepSeekSemanticStepCapability
from spg.providers.repository_change_proposal import RepositoryAwareChangeProposalProvider
from spg.providers.rule_based_planner import RuleBasedProductionPlanner
from tests.test_deepseek_semantic_provider import _Runtime
from tests.test_dogfood_repository_scope import _git


@pytest.fixture
def exact_source(tmp_path):
    repo = tmp_path / "source"
    repo.mkdir()
    (repo / "README.md").write_text("A governed source baseline; implementation is not present.\n")
    _git(repo, "init", "-b", "main")
    _git(repo, "add", ".")
    _git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "baseline")
    return repo, _git(repo, "rev-parse", "HEAD"), _git(repo, "rev-parse", "HEAD^{tree}")


def new_proof(revision, tree, path="ui/entry.ts", human="Provide an interactive production workspace"):
    return RepositoryTargetNecessityProof(path=path, evidence_kind="NEW_TARGET",
        source_revision=revision, source_tree=tree, human_clause=human,
        necessity="The governed working-software behavior needs this minimum new implementation surface.")


def request_for(source, proof, **updates):
    repo, revision, tree = source
    return RepositoryChangeProposalRequest(work_id=uuid4(), engineering_resource_id=uuid4(),
        repository_identity="fixture://r1", repository_location=str(repo), source_baseline_id=uuid4(),
        source_ref="refs/heads/main", source_revision=revision,
        refined_code_intent=proof.human_clause, human_authority_text=proof.human_clause,
        governed_semantic_ir_id=uuid4(), candidate_targets=(proof.path,), necessity_proofs=(proof,)).model_copy(update=updates)


@pytest.mark.parametrize("path,human", [
    ("ui/entry.ts", "Provide an interactive production workspace"),
    ("surface/工作台.html", "建立可以实际操作的生产工作台"),
])
def test_new_target_needs_no_existing_code_quote_and_preserves_exact_authority(exact_source, path, human):
    repo, revision, tree = exact_source
    proof = new_proof(revision, tree, path, human)
    request = request_for(exact_source, proof)
    before = (_git(repo, "rev-parse", "HEAD"), _git(repo, "status", "--porcelain"), _git(repo, "show-ref"))
    proposal = RepositoryChangeProposalService(RepositoryAwareChangeProposalProvider()).propose(request)
    assert [(t.path, t.operation) for t in proposal.required_targets] == [(path, ChangeOperation.CREATE)]
    assert proposal.allowed_areas == () and not proposal.conditional_targets
    assert proposal.source_baseline_id == request.source_baseline_id and proposal.source_revision == revision
    assert tree in proposal.required_targets[0].evidence
    assert proof.repository_quote is None and proof.source_path is None
    assert (_git(repo, "rev-parse", "HEAD"), _git(repo, "status", "--porcelain"), _git(repo, "show-ref")) == before


@pytest.mark.parametrize("change,reason", [
    ("revision", "stale source revision"), ("tree", "stale source tree"),
    ("existing", "existing exact-tree"), ("candidate", "outside observed candidate"),
    ("authority", "no exact repository/Human witness"), ("duplicate", "duplicate candidate"),
    ("forbidden", "forbidden area"), ("ancestor-file", "existing exact-tree"),
])
def test_new_target_rejects_wrong_basis_or_authority_without_fallback(exact_source, change, reason):
    _, revision, tree = exact_source
    proof = new_proof(revision, tree)
    if change == "revision": proof = proof.model_copy(update={"source_revision": "a" * 40})
    if change == "tree": proof = proof.model_copy(update={"source_tree": "b" * 40})
    if change == "existing": proof = proof.model_copy(update={"path": "README.md"})
    if change == "ancestor-file": proof = proof.model_copy(update={"path": "README.md/child.ts"})
    updates = {}
    if change == "candidate": updates["candidate_targets"] = ()
    if change == "authority": updates["human_authority_text"] = "Discuss a future possibility only"
    if change == "duplicate": updates["necessity_proofs"] = (proof, proof)
    if change == "forbidden": updates["explicit_forbidden_areas"] = ("ui/**",)
    with pytest.raises(ValueError, match=reason):
        RepositoryAwareChangeProposalProvider().propose(request_for(exact_source, proof, **updates))


@pytest.mark.parametrize("change", ["missing-revision", "missing-tree", "invented-quote", "unsafe-path"])
def test_new_target_wire_rejects_incomplete_identity_and_fake_existing_evidence(exact_source, change):
    _, revision, tree = exact_source
    values = new_proof(revision, tree).model_dump()
    if change == "missing-revision": values["source_revision"] = None
    if change == "missing-tree": values["source_tree"] = None
    if change == "invented-quote": values.update(source_path="README.md", repository_quote="imaginary implementation")
    if change == "unsafe-path": values["path"] = "../outside.ts"
    with pytest.raises(ValidationError):
        RepositoryTargetNecessityProof.model_validate(values)


def test_existing_implementation_still_requires_real_source_quote(exact_source):
    with pytest.raises(ValidationError, match="Existing implementation proof"):
        RepositoryTargetNecessityProof(path="README.md", human_clause="Update the current documentation",
            necessity="This current documentation surface must carry the admitted behavior.")
    proof = RepositoryTargetNecessityProof(path="README.md", source_path="README.md",
        repository_quote="fictional behavior", human_clause="Update the current documentation",
        necessity="This current documentation surface must carry the admitted behavior.")
    with pytest.raises(ValueError, match="no exact repository/Human witness"):
        RepositoryAwareChangeProposalProvider().propose(request_for(exact_source, proof))


def scope_fixture(exact_source, *, omit_requirement=False, downstream=False):
    repo, revision, tree = exact_source
    human = "Provide an interactive production workspace"
    requirement = "The workspace must retain entered records"
    proof = new_proof(revision, tree, human=human)
    coverage = tuple(ScopeRequirementCoverage(requirement=text,
        disposition="DOWNSTREAM" if downstream else "REQUIRED_TARGET",
        target_paths=() if downstream else (proof.path,),
        explanation="Declared independent semantic fixture maps the full requested behavior to this target.")
        for text in ((human,) if omit_requirement else (human, requirement)))
    validation = RepositoryScopeValidation(required_targets=(proof,), rejected_behaviors=(),
        explanation="Independent controlled semantic judgment; not runtime behavior or Human authorization.",
        requirement_coverage=coverage)
    class ScopeRuntime(_Runtime):
        def generate(self, **options):
            result = super().generate(**options)
            return replace(result, output_text=validation.model_dump_json(), usage=ModelUsage(unknown=True))
    runtime = ScopeRuntime()
    capability = DeepSeekSemanticStepCapability(runtime)
    work_id, plan_revision_id = uuid4(), uuid4()
    step = SteeringStepRecord(id=uuid4(), steering_plan_revision_id=plan_revision_id,
        type=SteeringStepType.DESIGN, objective=human, completion_condition="A complete governed production proposal",
        position=1, state=SteeringStepState.CURRENT, elaborates_step_id=None,
        created_at=datetime.now(timezone.utc))
    semantic_input = SemanticStepInput(work_id=work_id, desired_outcome=human,
        steering_plan_revision_id=plan_revision_id, step=step, basis_fingerprint="a" * 64,
        engineering_scope_id=uuid4(), engineering_scope_fingerprint="b" * 64,
        reality_refs=(RealityReference(kind=RealityReferenceKind.WORK, identity=work_id),), governance_decisions=(),
        constraints=(requirement,), work_requests=(human,), human_explicit_requests=(human + "; " + requirement,),
        governed_semantic_ir_id=uuid4(), canonical_explicit_targets=(), canonical_allowed_areas=(),
        repository_tree_paths=("README.md",), engineering_resource_id=uuid4(), source_baseline_id=uuid4(),
        repository_identity="fixture://r1", repository_location=str(repo), repository_ref="refs/heads/main",
        source_revision=revision, source_tree=tree, engineering_scope_summary="one exact tree", context_materials=())
    proposal = SemanticProductionProposal(target_kind=ProductionTargetKind.CODE_WORK,
        objective=human, code_targets=(proof.path,), verification_expectation="All original behaviors must verify")
    return semantic_input, proposal, capability, runtime


def test_complete_new_target_scope_reaches_existing_plan_change_and_task_contract(exact_source):
    semantic_input, proposal, capability, runtime = scope_fixture(exact_source)
    service = SemanticStepApplicationService.__new__(SemanticStepApplicationService)
    service.capability = capability
    service.change_proposals = RepositoryChangeProposalService(RepositoryAwareChangeProposalProvider())
    service.planning = ProductionPlanningService(RuleBasedProductionPlanner())
    plan, change = service._materialize_production_plan(semantic_input,
        SemanticStepResultCandidate.model_construct(proposed_production=proposal))
    assert len(runtime.calls) == 1
    payload = json.loads(runtime.calls[0]["input_text"])
    assert payload["exact_source_tree"] == semantic_input.source_tree
    assert payload["candidate_path_exists"] == {proposal.code_targets[0]: False}
    assert payload["new_target_scope_requirements"] == [semantic_input.desired_outcome, *semantic_input.constraints]
    contract = WorkApplicationService._admit_change_contract(change,
        desired_outcome=semantic_input.desired_outcome, constraints=semantic_input.constraints)
    assert [(t.path, t.operation) for t in contract.exact_targets] == [(proposal.code_targets[0], ChangeOperation.CREATE)]
    assert {v.kind for v in contract.verification_obligations} >= {CodeVerificationKind.PATH_SCOPE, CodeVerificationKind.GIT_DIFF_CHECK}
    assert not contract.allows_path("unrelated/side-effect.ts")
    task = default_task_contract_builder().build(TaskContractRequest(
        objective=plan.objective, scope=tuple(f"{t.operation.value}:{t.path}" for t in contract.exact_targets),
        constraints=contract.constraints, acceptance_meaning=("Original outcome must verify",),
        out_of_scope=("Any target outside the exact contract",), authority_lineage=(f"work:{semantic_input.work_id}",),
        work_reality_references=(f"work:{semantic_input.work_id}",),
        ecf_references=(f"engineering-resource:{semantic_input.engineering_resource_id}",
            f"source-baseline:{semantic_input.source_baseline_id}@{semantic_input.source_revision}"),
        decision_reference="declared-controlled-scope-fixture"))
    assert task.scope == ("CREATE:ui/entry.ts",)
    assert task.constraints == semantic_input.constraints
    assert plan.objective == semantic_input.desired_outcome


@pytest.mark.parametrize("failure", ["missing-behavior", "only-downstream"])
def test_incomplete_new_target_scope_truthfully_stops_after_existing_bounded_feedback(exact_source, failure):
    value, proposal, capability, runtime = scope_fixture(exact_source,
        omit_requirement=failure == "missing-behavior", downstream=failure == "only-downstream")
    validation = capability.validate_production_scope(value, proposal)
    assert validation.missing_acceptance_requirements
    assert len(runtime.calls) == 2
    assert json.loads(runtime.calls[1]["input_text"])["coverage_feedback"]
    service = SemanticStepApplicationService.__new__(SemanticStepApplicationService)
    service.capability = SimpleNamespace(validate_production_scope=lambda *_: validation)
    service.change_proposals = SimpleNamespace(propose=lambda *_: pytest.fail("Incomplete scope must not create Change Proposal"))
    service.planning = SimpleNamespace(propose=lambda *_: pytest.fail("Incomplete scope must not reach Planning"))
    with pytest.raises(ValueError, match="INTENT_COMPLETENESS_MISMATCH"):
        service._materialize_production_plan(value, SemanticStepResultCandidate.model_construct(proposed_production=proposal))


def test_full_git_tree_proof_does_not_trust_sampled_context_absence(exact_source):
    value, proposal, capability, runtime = scope_fixture(exact_source)
    # The declared repository sample omits README, but the exact Git object still owns it.
    value = value.model_copy(update={"repository_tree_paths": ()})
    proof = new_proof(value.source_revision, value.source_tree, path="README.md")
    validation = RepositoryScopeValidation(required_targets=(proof,), rejected_behaviors=(),
        explanation="Deliberately forged absent-target fixture", requirement_coverage=())
    original = runtime.generate
    def generate(**options):
        return replace(original(**options), output_text=validation.model_dump_json())
    runtime.generate = generate
    proposal = proposal.model_copy(update={"code_targets": ("README.md",)})
    result = capability.validate_production_scope(value, proposal)
    assert any("existing exact-tree" in issue for issue in result.missing_acceptance_requirements)
    assert len(runtime.calls) == 2


def test_new_target_cannot_claim_existing_non_ascii_git_path_absent(exact_source):
    repo, _, _ = exact_source
    (repo / "既有页面.html").write_text("<main>Existing exact source</main>")
    _git(repo, "add", ".")
    _git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "existing non-ascii path")
    source = repo, _git(repo, "rev-parse", "HEAD"), _git(repo, "rev-parse", "HEAD^{tree}")
    proof = new_proof(source[1], source[2], path="既有页面.html")
    with pytest.raises(ValueError, match="existing exact-tree"):
        RepositoryAwareChangeProposalProvider().propose(request_for(source, proof))


def test_existing_source_witness_cannot_hide_new_target_behavior_coverage(exact_source):
    value, proposal, capability, runtime = scope_fixture(exact_source)
    value = value.model_copy(update={"context_materials": (SimpleNamespace(repository_relative_path="README.md"),)})
    proof = RepositoryTargetNecessityProof(path=proposal.code_targets[0], source_path="README.md",
        repository_quote="A governed source baseline", human_clause=value.desired_outcome,
        necessity="Controlled existing-source necessity witness for a new implementation target.")
    validation = RepositoryScopeValidation(required_targets=(proof,), rejected_behaviors=(),
        explanation="Deliberately incomplete coverage despite a legitimate exact source witness.",
        requirement_coverage=(ScopeRequirementCoverage(requirement=value.constraints[0],
            disposition="REQUIRED_TARGET", target_paths=proposal.code_targets,
            explanation="Only one constraint is covered; the full canonical outcome is omitted."),))
    original = runtime.generate
    def generate(**options):
        return replace(original(**options), output_text=validation.model_dump_json())
    runtime.generate = generate
    result = capability.validate_production_scope(value, proposal)
    assert result.missing_acceptance_requirements
    assert not any("no exact repository/Human witness" in issue for issue in result.missing_acceptance_requirements)
    assert len(runtime.calls) == 2


def test_proposal_independently_revalidates_new_target_identity_shape(exact_source):
    _, revision, tree = exact_source
    valid_proof = new_proof(revision, tree)
    proof = valid_proof.model_copy(update={"source_tree": None})
    # The normal wire rejects before the independent consumer is called.
    with pytest.raises(ValueError, match="New target proof requires exact revision/tree"):
        request_for(exact_source, proof)
    # A copied/stored request must not bypass the consumer's own proof guard.
    request = request_for(exact_source, valid_proof).model_copy(update={"necessity_proofs": (proof,)})
    with pytest.raises(ValueError, match="evidence contract is invalid"):
        RepositoryAwareChangeProposalProvider().propose(request)
