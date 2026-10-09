"""Owner boundaries for admitted Facts, exact effects and ECF coverage."""

from __future__ import annotations

from hashlib import sha256
import json
from contextlib import contextmanager
from pathlib import Path
import subprocess
from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.application.governed_obligations import (
    materialize_continuous_gates, validate_continuous_gates,
    denied_execution_capabilities, evaluate_continuous_gates,
    evaluate_candidate_handoffs, evaluate_constraint_routes,
    assert_delivery_effect_permitted,
)
from spg.domain.governed_obligation import (
    FulfillmentOwner, FulfillmentPhase, bind_admitted_fact,
)
from spg.domain.intent_realization import SemanticClause, SemanticItem, SemanticKind
from spg.domain.semantic_provenance import SemanticOrigin, SemanticProvenance
from spg.domain.engineering_semantics import (
    EngineeringSemanticFact, SemanticFactAuthority, SemanticEpistemicStatus,
    SemanticFactProvenance, SemanticRelation, SemanticRoleOrigin,
    semantic_fact_reference,
)
from spg.domain.production_intelligence import ProtectedContextObligation
from spg.providers.managed_context_fulfillment import verify_managed_context


def fact(subject, relation, value, source, *, qualifiers=None):
    return EngineeringSemanticFact(
        id=uuid4(), subject=subject, relation=relation, value=value,
        scope="index.html", qualifiers=qualifiers or {},
        authority=SemanticFactAuthority.HUMAN_EXPLICIT,
        epistemic_status=SemanticEpistemicStatus.CONFIRMED,
        provenance=SemanticFactProvenance(
            source_record_ids=(uuid4(),), source_text=source,
            role_origin=SemanticRoleOrigin.EXPLICIT))


def work(*facts):
    return SimpleNamespace(id=uuid4(), work_id=uuid4(),
        engineering_semantic_facts=facts, source_revision="a" * 40,
        revision_fingerprint="b" * 64)


def ir(*exclusions):
    goal = SimpleNamespace(exclusions=exclusions, preview_required=False,
                           delivery_authorized=False, acceptance_required=True,
                           target_paths=())
    return SimpleNamespace(current_production=(goal,))


def constraint_route(effects=("PROHIBIT_DEPLOY", "PROHIBIT_PUBLISH"), *,
                     polarity="NEGATED"):
    source_id = uuid4()
    quote = "Do not release this artifact to any outside environment."
    statement = "No external release is permitted."
    item = SemanticItem(item_id="c-1", kind=SemanticKind.CONSTRAINT,
                        statement=statement, subject="external-effects",
                        provenance=(SemanticProvenance(
                            origin=SemanticOrigin.HUMAN_EXPLICIT,
                            source_record_id=source_id, source_text=quote),),
                        confidence=1.0)
    clause = SemanticClause(clause_id="cl-1", source_record_id=source_id,
                            source_text=quote, semantic_item_ids=(item.item_id,),
                            polarity=polarity, requested_effects=effects)
    revision = work()
    revision.constraints = (statement,)
    revision.source_assessment_id = uuid4()
    revision.source_record_ids = (source_id,)
    typed = SimpleNamespace(id=uuid4(), items=(item,), clauses=(clause,),
                            current_production=ir().current_production)
    return revision, typed


def test_prohibitions_bind_typed_constraint_without_inventing_fact_identity():
    revision, typed = constraint_route()
    bindings = materialize_continuous_gates(revision, typed)
    assert [(item.fact_id, item.constraint_item_id, item.component)
            for item in bindings] == [(None, "c-1", "deploy"),
                                     (None, "c-1", "publish")]
    assert denied_execution_capabilities(bindings) == frozenset()
    assert revision.engineering_semantic_facts == ()
    with pytest.raises(ValueError, match="BINDING_DRIFT"):
        validate_continuous_gates(bindings[:-1], revision, typed)
    revision.constraints = ()
    with pytest.raises(ValueError, match="SOURCE_MISMATCH"):
        materialize_continuous_gates(revision, typed)
    revision.constraints = ("No external release is permitted.",)
    with pytest.raises(ValueError, match="SOURCE_MISMATCH"):
        materialize_continuous_gates(revision,
            SimpleNamespace(**{**vars(typed), "clauses": (
                typed.clauses[0].model_copy(update={"polarity": "AFFIRMATIVE"}),)}))
    with pytest.raises(ValueError, match="UNRESOLVED"):
        materialize_continuous_gates(revision,
            SimpleNamespace(**{**vars(typed), "clauses": (
                typed.clauses[0].model_copy(update={
                    "requested_effects": ("PROHIBIT_UNMAPPED_EFFECT",)}),)}))


def test_current_gate_requires_the_persisted_attempt_to_lack_the_capability():
    preview = fact("release.preview_requested", SemanticRelation.EQUALITY,
                   False, "No preview is requested.")
    revision = work(preview)
    binding = bind_admitted_fact(
        reference=semantic_fact_reference(preview, work_revision_id=revision.id),
        admitted=preview, component="preview", owner=FulfillmentOwner.EXECUTION_GATE,
        phase=FulfillmentPhase.CONTINUOUS_FROM_ADMISSION,
        evidence_method="EXACT_PERMISSION_GATE",
        gate_ref="execution-capability:preview.inspect:denied",
        source_quote=preview.provenance.source_text,
        source_revision=revision.source_revision)
    validate_continuous_gates((binding,), revision,
                              SimpleNamespace(current_production=()))
    with pytest.raises(ValueError, match="BINDING_DRIFT"):
        validate_continuous_gates((binding.model_copy(update={
            "source_revision": "0" * 40}),), revision,
            SimpleNamespace(current_production=()))
    attempt = uuid4()
    base = dict(attempt_id=attempt, pwu_id=uuid4(),
        production_context=SimpleNamespace(work_reality_revision_id=revision.id),
        obligation_references=(f"semantic-fact:{preview.id}",),
        source_vector=SimpleNamespace(members=(
            SimpleNamespace(source_commit_oid=revision.source_revision),)))
    check = {"fact_id": str(preview.id), "disposition": "UNVERIFIABLE_CURRENT",
             "passed": False}
    safe = SimpleNamespace(attempt_id=attempt, binding_digest="c" * 64,
        binding=SimpleNamespace(**base, capability_grants=()))
    assert evaluate_continuous_gates((check,), (binding,), safe,
        source_revision=revision.source_revision)[0]["disposition"] == "GATED_CONTINUOUS"
    unsafe = SimpleNamespace(attempt_id=attempt, binding_digest="d" * 64,
        binding=SimpleNamespace(**base, capability_grants=(
            SimpleNamespace(identity="preview.inspect"),)))
    assert evaluate_continuous_gates((check,), (binding,), unsafe,
        source_revision=revision.source_revision)[0]["passed"] is False


def test_constraint_route_needs_exact_native_reference_and_no_forbidden_grant():
    revision, typed = constraint_route()
    bindings = materialize_continuous_gates(revision, typed)
    attempt = uuid4()
    native = SimpleNamespace(attempt_id=attempt, pwu_id=uuid4(),
        production_context=SimpleNamespace(work_reality_revision_id=revision.id),
        obligation_references=("ir-constraint:c-1:cl-1",),
        source_vector=SimpleNamespace(members=(
            SimpleNamespace(source_commit_oid=revision.source_revision),)),
        capability_grants=())
    record = SimpleNamespace(attempt_id=attempt, binding_digest="d" * 64,
                             binding=native)
    assert all(check["passed"] for check in evaluate_constraint_routes(
        bindings, record, source_revision=revision.source_revision,
        path_scope_passed=True))
    native.obligation_references = ()
    assert not any(check["passed"] for check in evaluate_constraint_routes(
        bindings, record, source_revision=revision.source_revision,
        path_scope_passed=True))
    native.obligation_references = ("ir-constraint:c-1:cl-1",)
    native.capability_grants = (SimpleNamespace(identity="cloud.deploy"),)
    assert not evaluate_constraint_routes(bindings, record,
        source_revision=revision.source_revision,
        path_scope_passed=True)[0]["passed"]


def test_delivery_owner_rechecks_current_admitted_prohibition(monkeypatch):
    from spg.infrastructure.persistence.product_store import ProductStore
    from spg.infrastructure.persistence.interaction_store import InteractionStore

    revision, typed = constraint_route()
    @contextmanager
    def unit_of_work():
        yield SimpleNamespace(session=object())
    database = SimpleNamespace(unit_of_work=unit_of_work)
    monkeypatch.setattr(ProductStore, "current_work_reality_revision",
                        lambda self, work_id: revision)
    monkeypatch.setattr(InteractionStore, "assessment",
                        lambda self, assessment_id: SimpleNamespace(semantic_ir=typed))
    with pytest.raises(ValueError, match="DELIVERY_PROHIBITED"):
        assert_delivery_effect_permitted(database, revision.work_id, "deploy")
    with pytest.raises(ValueError, match="DELIVERY_PROHIBITED"):
        assert_delivery_effect_permitted(database, revision.work_id, "publish")
    typed.items = ()
    typed.clauses = ()
    monkeypatch.setattr(ProductStore, "runtime_binding", lambda self, work_id: None)
    # Fresh admitted IR cannot silently release a prohibition when its persisted
    # same-revision fulfillment projection is missing.
    with pytest.raises(ValueError, match="DELIVERY_PROJECTION_MISSING_OR_STALE"):
        assert_delivery_effect_permitted(database, revision.work_id, "deploy")
    # Historical pre-open typed projections keep their explicit compatibility.
    typed.legacy_typed_projection = True
    assert_delivery_effect_permitted(database, revision.work_id, "deploy") is None


def test_delivery_authorization_entrypoints_stop_before_external_effects(monkeypatch):
    from spg.application.cloud_delivery import CloudDeliveryError, CloudDeliveryService
    from spg.application.github_delivery import GitHubDeliveryError, GitHubDeliveryService
    import spg.application.governed_obligations as obligations

    def prohibited(database, work_id, component):
        raise ValueError("OBLIGATION_DELIVERY_PROHIBITED")
    monkeypatch.setattr(obligations, "assert_delivery_effect_permitted", prohibited)
    inert = SimpleNamespace(database=object())
    with pytest.raises(CloudDeliveryError, match="OBLIGATION_DELIVERY_PROHIBITED"):
        CloudDeliveryService.authorize(inert, "human:owner", uuid4(), object())
    with pytest.raises(GitHubDeliveryError) as error:
        GitHubDeliveryService.authorize(inert, "human:owner", work_id=uuid4(),
            manifest_id=uuid4(), expected_revision="a" * 40,
            target_branch="main", expected_remote_revision=None,
            rationale="Exact release review")
    assert error.value.code == "OBLIGATION_DELIVERY_PROHIBITED"


def test_mixed_acceptance_fact_checks_current_content_and_keeps_seal_pending():
    heading = fact("page.h1", SemanticRelation.EQUALITY, "N1",
                   "one h1 reading N1")
    scope = fact("change.scope", SemanticRelation.SCOPE, "index.html",
                 "Only index.html may change.")
    assertion = fact("acceptance.result", SemanticRelation.ACCEPTANCE_ASSERTION,
        "exact text and file scope verified; reviewable Candidate left",
        "Verify exact text and file scope in index.html; leave a reviewable Candidate.")
    revision = work(heading, scope, assertion)
    references = tuple(semantic_fact_reference(item, work_revision_id=revision.id)
                       for item in revision.engineering_semantic_facts)
    checks = tuple({"fact_id": str(item.id),
        "passed": item is not assertion,
        "disposition": ("UNVERIFIABLE_CURRENT" if item is assertion
                        else "VERIFIED_CURRENT")}
        for item in revision.engineering_semantic_facts)
    kwargs = dict(references=references,
        admitted_facts={str(item.id): item for item in revision.engineering_semantic_facts},
        ir=ir(), source_revision=revision.source_revision,
        exact_target_paths=("index.html",))
    result = evaluate_candidate_handoffs(checks, **kwargs)
    assert result[-1]["passed"] is True
    assert result[-1]["future_evidence_status"] == "PENDING_CANDIDATE_SEAL"
    assert set(result[-1]["linked_current_fact_ids"]) == {str(heading.id), str(scope.id)}
    wrong = ({**checks[0], "passed": False}, *checks[1:])
    assert evaluate_candidate_handoffs(wrong, **kwargs)[-1]["passed"] is False


def git(repository, *args):
    return subprocess.check_output(["git", "-C", str(repository), *args],
                                   text=True).strip()


def protected(context_class, key, content, revision, fingerprint):
    return ProtectedContextObligation(
        context_class=context_class, semantic_key=key,
        source_ref=f"work-reality:{revision.work_id}:{key}",
        source_revision="e" * 64, authority="WATT_WORK",
        content=content, content_digest=sha256(content.encode()).hexdigest(),
        package_fingerprint=fingerprint)


def test_managed_ecf_routes_diff_content_candidate_and_gates_without_dropping_items(tmp_path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.name", "Qualification")
    git(tmp_path, "config", "user.email", "qualification@example.invalid")
    (tmp_path / "README.md").write_text("source")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "source")
    base = git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "index.html").write_text("<h1>N1</h1>")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "candidate")
    candidate = git(tmp_path, "rev-parse", "HEAD")
    tree = git(tmp_path, "rev-parse", "HEAD^{tree}")
    goal = SimpleNamespace(exclusions=("deployment",), acceptance_required=True,
        model_dump=lambda mode: {"exclusions": ["deployment"],
                                  "acceptance_required": True})
    typed_ir = SimpleNamespace(current_production=(goal,))
    constraints = ("index.html is the only artifact changed",
                   "h1 text exactly N1",
                   "A reviewable Candidate left for Human acceptance",
                   "Excluded from this Work: deployment")
    revision = SimpleNamespace(id=uuid4(), work_id=uuid4(),
        desired_outcome="Create N1", constraints=constraints)
    fp = "f" * 64
    items = tuple(protected("APPROVED_CONSTRAINT", f"greenfield-constraint:{i}",
                            value, revision, fp) for i, value in enumerate(constraints))
    intent = json.dumps({"desired_outcome": "Create N1",
        "governed_production_intents": [goal.model_dump("json")]})
    items += (protected("PRODUCT_INTENT", "greenfield-product-intent",
                        intent, revision, fp),)
    request = SimpleNamespace(protected_context_obligations=items,
        proposed_commit_identity=candidate, tree_identity=tree)
    task = SimpleNamespace(task_contract_id=uuid4(),
        decision_context=SimpleNamespace(work_id=str(revision.work_id),
            repository_revision=base, package_fingerprint=fp))
    contract = SimpleNamespace(exact_targets=(SimpleNamespace(path="index.html"),))
    semantic_checks = ({"fact_id": str(uuid4()), "passed": True,
        "disposition": "VERIFIED_CURRENT"},
        {"fact_id": str(uuid4()), "passed": True,
         "disposition": "GATED_CONTINUOUS",
         "fulfillment_bindings": [{"component": "deploy",
             "gate_ref": "cloud-delivery:human-authorization-required"}],
         "gate_evidence": {"native_binding_digest": "d" * 64}})
    class SourceVerifier:
        @staticmethod
        def supports(_): return True
        @staticmethod
        def verify(req, _task, _contract, _repo, _base, *, obligations, **_):
            assert obligations == (items[1],)
            return [{**items[1].model_dump(mode="json"), "coverage": "COVERED",
                     "candidate_revision": req.proposed_commit_identity,
                     "candidate_tree": req.tree_identity,
                     "witnesses": [{"path": "index.html", "quote": "<h1>N1</h1>"}]}]
    kwargs = dict(request=request, task=task, contract=contract, repository=tmp_path,
        baseline=base, revision=revision, ir=typed_ir,
        semantic_checks=semantic_checks, static_verifier=SourceVerifier())
    checks = verify_managed_context(**kwargs)
    assert len(checks) == len(items)
    assert [item["coverage"] for item in checks] == ["UNVERIFIED"] * len(items)
    no_gate = (semantic_checks[0],)
    assert verify_managed_context(**{**kwargs, "semantic_checks": no_gate})[3]["coverage"] == "UNVERIFIED"
    bad = items[0].model_copy(update={"content": "wrong source"})
    with pytest.raises(ValueError, match="NOT_ADMITTED_WORK"):
        verify_managed_context(**{**kwargs, "request": SimpleNamespace(
            protected_context_obligations=(bad, *items[1:]),
            proposed_commit_identity=candidate, tree_identity=tree)})
