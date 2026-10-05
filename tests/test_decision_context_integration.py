"""Executable Watt ↔ canonical ECF v0.1 decisions over real Watt sources."""

from pathlib import Path
from dataclasses import replace
from hashlib import sha256
import os
import shutil
import subprocess
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.application.decision_context import (
    DecisionContextChanged,
    DecisionContextNotReady,
    DecisionContextRequirement,
    ECS_SURFACE,
    MILESTONE_SURFACE,
    MANAGED_WEB_SURFACE,
    WORKSPACE_SURFACE,
    WattDecisionContextGateway,
    MilestoneClosureContextService,
    policy_for_targets,
)
from spg.application.production_intelligence import (
    TaskContractRequest, default_task_contract_builder,
)
from spg.application.verification import _project_decision_context_evidence
from spg.application.guardian_assurance import _protected_context_for_guardian
from spg.domain.verification import (
    VerificationCapabilityRequest, VerificationCapabilityResult,
    VerificationEvidence, VerificationResultValue,
)


pytestmark = pytest.mark.cross_repository
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def canonical_ecf():
    from tests.qualification_owner_sources import owner_source_root
    source = owner_source_root("ecf", ROOT.parent / "engineering-context-fabric" / "src")
    if not (source / "ecf" / "decision_context.py").is_file():
        pytest.skip("BLOCKED_EXTERNAL_DEPENDENCY: canonical ECF v0.1 unavailable")
    sys.path.insert(0, str(source))
    yield
    sys.path.remove(str(source))


def git(repository: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repository), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture
def source_repo(tmp_path: Path) -> Path:
    repository = tmp_path / "software-production-platform"
    repository.mkdir()
    git(repository, "init", "-b", "main")
    git(repository, "config", "user.name", "ECF integration test")
    git(repository, "config", "user.email", "ecf@example.invalid")
    for name in (
        "docs/product/workspace-first-experience-principles.md",
        "docs/operations/aliyun-ecs-delivery.md",
        "docs/architecture/watt-product-north-star.md",
    ):
        target = repository / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    git(repository, "add", ".")
    git(repository, "commit", "-m", "snapshot current governed Watt sources")
    return repository


def requirement(repository: Path, surface: str, *, product_id=None, work_id=None):
    return DecisionContextRequirement(
        surface=surface, product_id=product_id or uuid4(),
        work_id=work_id if work_id is not None else
            (None if surface == MILESTONE_SURFACE else uuid4()),
        subject="src/spg/web/experience.js" if surface == WORKSPACE_SURFACE
            else "src/spg/application/cloud_delivery.py" if surface == ECS_SURFACE
            else "October Product milestone",
        repository_path=repository, repository_revision=git(repository, "rev-parse", "HEAD"),
    )


def task(lineage):
    return default_task_contract_builder().build(TaskContractRequest(
        objective="Implement the exact governed change", scope=("UPDATE:source",),
        acceptance_meaning=("Run relevant verification",),
        out_of_scope=("Unrelated source",),
        authority_lineage=("work:1", "governance:1"),
        work_reality_references=("work:1",),
        ecf_references=("repository:one",),
        decision_reference="governance:1", governed_surface=lineage.surface,
        decision_context=lineage,
    ))


def test_exact_registry_keeps_unrelated_tasks_legacy():
    assert policy_for_targets(("README.md",)) is None
    assert policy_for_targets(("src/spg/web/experience.js",)) == WORKSPACE_SURFACE
    assert policy_for_targets(("src/spg/application/cloud_delivery.py",)) == ECS_SURFACE
    with pytest.raises(ValueError, match="cannot cross"):
        policy_for_targets(("src/spg/web/experience.js",
                            "src/spg/application/cloud_delivery.py"))
    with pytest.raises(ValueError, match="READY ECF package"):
        default_task_contract_builder().build(TaskContractRequest(
            objective="Modify Workspace", scope=("UPDATE:src/spg/web/experience.js",),
            acceptance_meaning=("Verify quadrants",), out_of_scope=("Other paths",),
            authority_lineage=("work:one",),
            work_reality_references=("work:one",),
            ecf_references=("repository:one",),
            decision_reference="work:one", governed_surface=WORKSPACE_SURFACE,
        ))


def test_managed_web_change_requires_project_intent_invariant_and_decision(
    tmp_path: Path,
):
    repository = tmp_path / "managed-web"
    repository.mkdir()
    git(repository, "init", "-b", "accepted")
    git(repository, "config", "user.name", "ECF integration test")
    git(repository, "config", "user.email", "ecf@example.invalid")
    readme = repository / "README.md"
    readme.write_text(
        "# Company website\n\n## Product Intent\nPublic company identity.\n\n"
        "## Product Invariant\nKeep the existing navigation available.\n\n"
        "## Approved Decision\nAdd one bounded page entry.\n",
        encoding="utf-8",
    )
    (repository / "index.html").write_text("<main>Home</main>\n")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "managed website baseline")
    req = DecisionContextRequirement(
        MANAGED_WEB_SURFACE, uuid4(), uuid4(), "index.html",
        repository, git(repository, "rev-parse", "HEAD"), "watt://web-test",
    )
    gateway = WattDecisionContextGateway()
    package = gateway.require_ready(req, work_statement="Add a page entry",
                                    work_revision="work-1")
    lineage = gateway.lineage(package, req)
    assert {item.context_class for item in lineage.protected_obligations} == {
        "PRODUCT_INTENT", "PRODUCT_INVARIANT", "APPROVED_DECISION",
    }
    readme.write_text(readme.read_text().replace(
        "## Product Invariant", "## Missing invariant"))
    git(repository, "add", ".")
    git(repository, "commit", "-m", "remove invariant")
    changed = DecisionContextRequirement(
        MANAGED_WEB_SURFACE, req.product_id, req.work_id, req.subject,
        repository, git(repository, "rev-parse", "HEAD"), req.repository_identity,
    )
    with pytest.raises(DecisionContextNotReady) as error:
        gateway.require_ready(changed, work_statement="Add a page entry",
                              work_revision="work-1")
    assert "PRODUCT_INVARIANT" in error.value.missing_classes


def test_workspace_invariant_is_required_before_task_formation(source_repo: Path):
    gateway = WattDecisionContextGateway()
    req = requirement(source_repo, WORKSPACE_SURFACE)
    package = gateway.require_ready(req, work_statement="Change Workspace UI",
                                    work_revision="work-revision-1")
    lineage = gateway.lineage(package, req)
    formed = task(lineage)
    invariant = next(item for item in formed.decision_context.protected_obligations
                     if item.context_class == "PRODUCT_INVARIANT")
    assert invariant.source_ref == "git:docs/product/workspace-first-experience-principles.md"
    assert invariant.source_revision == git(source_repo, "rev-parse",
        f"{req.repository_revision}:docs/product/workspace-first-experience-principles.md")
    assert invariant.verification_ref == "tests/js/test_product_workspace_quadrants.cjs"
    assert {item.context_class for item in lineage.protected_obligations} == {
        "PRODUCT_INTENT", "PRODUCT_INVARIANT", "APPROVED_DECISION",
    }
    assert "Agenda" in invariant.content and "Production" in invariant.content
    assert any(item.reference == invariant.source_ref for item in formed.relevant_context)
    assert any(trace.source_ref == invariant.source_ref
               and trace.source_revision == invariant.source_revision
               and trace.provenance.startswith("git:")
               for trace in lineage.generated_from)
    document = source_repo / "docs/product/workspace-first-experience-principles.md"
    document.write_text(document.read_text().replace(
        "## 11. Workspace Four-Quadrant Invariant", "## 11. Unapproved replacement"))
    git(source_repo, "add", ".")
    git(source_repo, "commit", "-m", "remove canonical invariant")
    missing = requirement(source_repo, WORKSPACE_SURFACE,
                          product_id=req.product_id, work_id=req.work_id)
    with pytest.raises(DecisionContextNotReady) as error:
        gateway.require_ready(missing, work_statement="Change Workspace UI",
                              work_revision="work-revision-1")
    assert "PRODUCT_INVARIANT" in error.value.missing_classes


@pytest.mark.parametrize("removed,missing", (
    ("## Product Intent", "PRODUCT_INTENT"),
    ("## Approved Safety Constraint", "APPROVED_CONSTRAINT"),
))
def test_ecs_intent_and_safety_are_independently_required(
    source_repo: Path, removed: str, missing: str,
):
    document = source_repo / "docs/operations/aliyun-ecs-delivery.md"
    document.write_text(document.read_text().replace(removed, "## Missing authority"))
    git(source_repo, "add", ".")
    git(source_repo, "commit", "-m", "remove one governed ECS source")
    with pytest.raises(DecisionContextNotReady) as error:
        WattDecisionContextGateway().require_ready(
            requirement(source_repo, ECS_SURFACE),
            work_statement="Change ECS delivery", work_revision="work-1",
        )
    assert missing in error.value.missing_classes


def test_ecs_ready_task_carries_both_protected_obligations(source_repo: Path):
    gateway = WattDecisionContextGateway()
    req = requirement(source_repo, ECS_SURFACE)
    package = gateway.require_ready(req, work_statement="Change ECS delivery",
                                    work_revision="work-1")
    formed = task(gateway.lineage(package, req))
    classes = {item.context_class for item in
               formed.decision_context.protected_obligations}
    assert classes == {"PRODUCT_INTENT", "APPROVED_CONSTRAINT"}
    obligations = {item.context_class: item.content for item in
                   formed.decision_context.protected_obligations}
    assert "automatically prepares a supported host" in obligations["PRODUCT_INTENT"]
    assert "does not need to" in obligations["PRODUCT_INTENT"]
    assert "Human-selected exact" in obligations["APPROVED_CONSTRAINT"]
    assert "PUBLIC exposure" in obligations["APPROVED_CONSTRAINT"]
    assert formed.decision_context.package_fingerprint == package.fingerprint
    assert all(item.package_fingerprint == package.fingerprint for item in
               formed.decision_context.protected_obligations)


def test_superseded_source_invalidates_stale_task_before_execution(source_repo: Path):
    gateway = WattDecisionContextGateway()
    req = requirement(source_repo, WORKSPACE_SURFACE)
    lineage = gateway.lineage(gateway.require_ready(
        req, work_statement="Change Workspace UI", work_revision="work-1"), req)
    gateway.assert_fresh(lineage, work_statement="Change Workspace UI",
                         work_revision="work-1")
    document = source_repo / "docs/product/workspace-first-experience-principles.md"
    document.write_text(document.read_text().replace(
        "Agenda remains above Actions", "Agenda remains permanently above Actions"))
    git(source_repo, "add", ".")
    git(source_repo, "commit", "-m", "governed invariant revision")
    with pytest.raises(DecisionContextChanged) as error:
        gateway.assert_fresh(lineage, work_statement="Change Workspace UI",
                             work_revision="work-1")
    assert error.value.previous_fingerprint != error.value.current_fingerprint
    renewed = requirement(source_repo, WORKSPACE_SURFACE,
                          product_id=req.product_id, work_id=req.work_id)
    current = gateway.require_ready(renewed, work_statement="Change Workspace UI",
                                    work_revision="work-1")
    assert task(gateway.lineage(current, renewed)).decision_context.package_fingerprint == current.fingerprint


def test_qualified_pwu_context_freshness_uses_exact_input_not_accepted_head(source_repo: Path):
    gateway = WattDecisionContextGateway()
    accepted = git(source_repo, "rev-parse", "HEAD")
    (source_repo / "qualified-result.txt").write_text("Qualified predecessor output\n")
    git(source_repo, "add", ".")
    git(source_repo, "commit", "-m", "qualified internal PWU output")
    req = requirement(source_repo, WORKSPACE_SURFACE)
    qualified = req.repository_revision
    lineage = gateway.lineage(gateway.require_ready(req,
        work_statement="Change Workspace UI", work_revision="work-1"), req)
    git(source_repo, "reset", "--hard", accepted)
    # The accepted ref remains unchanged; the active PWU consumes a different
    # exact qualified revision, which the application must independently prove.
    with pytest.raises(DecisionContextChanged):
        gateway.assert_fresh(lineage, work_statement="Change Workspace UI", work_revision="work-1")
    gateway.assert_fresh(lineage, work_statement="Change Workspace UI", work_revision="work-1",
                         repository_revision=qualified)
    with pytest.raises(DecisionContextChanged):
        gateway.assert_fresh(lineage, work_statement="Revised Work intent", work_revision="work-2",
                             repository_revision=qualified)


def test_closure_north_star_cannot_be_inferred_from_passing_verification(source_repo: Path):
    gateway = WattDecisionContextGateway()
    req = requirement(source_repo, MILESTONE_SURFACE)
    ready = gateway.assemble(req, verification_statement="verification:record-1 PASS")
    assert ready.context_status.value == "READY"
    document = source_repo / "docs/architecture/watt-product-north-star.md"
    document.write_text(document.read_text().replace(
        "## 1. Product identity", "## 1. Unapproved replacement"))
    git(source_repo, "add", ".")
    git(source_repo, "commit", "-m", "remove North Star")
    missing = requirement(source_repo, MILESTONE_SURFACE, product_id=req.product_id)
    package = gateway.assemble(missing, verification_statement="verification:record-1 PASS")
    assert package.context_status.value == "INCOMPLETE"
    assert "PRODUCT_NORTH_STAR" in {item.value for item in package.missing_required_classes}


def test_ecf_scopes_cannot_reuse_product_a_sources_for_product_b(source_repo: Path):
    ecf = pytest.importorskip("ecf.decision_context")
    gateway = WattDecisionContextGateway()
    req_a = requirement(source_repo, WORKSPACE_SURFACE)
    package_a = gateway.require_ready(req_a, work_statement="UI change", work_revision="work-1")
    req_b = ecf.DecisionContextRequest(
        request_id="product-b", consumer_role=package_a.request.consumer_role,
        decision_type=package_a.request.decision_type,
        scope=ecf.DecisionScope("watt", str(uuid4()), str(uuid4()), req_a.subject),
        authority_context=package_a.request.authority_context,
        as_of=package_a.request.as_of,
    )
    snapshot = ecf.SourceSnapshot(tuple(view.record for view in package_a.selected))
    other = ecf.assemble_context(req_b, snapshot)
    assert other.context_status.value == "INCOMPLETE"
    assert "PRODUCT_INTENT" in {item.value for item in other.missing_required_classes}


def test_conflicting_and_stale_governed_sources_block_task_formation(source_repo: Path):
    ecf = pytest.importorskip("ecf.decision_context")
    gateway = WattDecisionContextGateway()
    req = requirement(source_repo, WORKSPACE_SURFACE)
    ready = gateway.require_ready(req, work_statement="UI change", work_revision="work-1")
    records = tuple(view.record for view in ready.selected)
    invariant = next(item for item in records
                     if ecf.ContextClass.PRODUCT_INVARIANT in item.classes)
    changed = replace(invariant, context_id=invariant.context_id + ":conflict",
                      content={"invariant": "conflicting replacement"})
    conflicted = ecf.assemble_context(ready.request,
                                     ecf.SourceSnapshot(records + (changed,)))
    assert conflicted.context_status is ecf.ContextStatus.CONFLICTED
    with pytest.raises(DecisionContextNotReady) as conflict_error:
        gateway.ensure_ready(conflicted)
    assert conflict_error.value.conflict_references
    stale = ecf.assemble_context(ready.request, ecf.SourceSnapshot(tuple(
        replace(item, temporal_state=ecf.TemporalState.STALE)
        if item.context_id == invariant.context_id else item for item in records
    )))
    assert stale.context_status is ecf.ContextStatus.STALE_OR_UNCERTAIN
    with pytest.raises(DecisionContextNotReady) as stale_error:
        gateway.ensure_ready(stale)
    assert "STALE_REQUIRED_CLASS:PRODUCT_INVARIANT" in stale_error.value.stale_risks


def test_required_protected_context_cannot_be_budget_trimmed(source_repo: Path):
    gateway = WattDecisionContextGateway()
    req = requirement(source_repo, WORKSPACE_SURFACE)
    lineage = gateway.lineage(gateway.require_ready(
        req, work_statement="UI change", work_revision="work-1"), req)
    oversized = lineage.model_copy(update={
        "protected_obligations": tuple(item.model_copy(update={
            "content": "x" * 6000,
            "content_digest": sha256(("x" * 6000).encode()).hexdigest(),
        })
                                       for item in lineage.protected_obligations),
    })
    with pytest.raises(ValueError, match="Context Budget"):
        task(oversized)


def test_required_owner_mode_fails_truthfully_without_canonical_ecf():
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run([sys.executable, "-c",
        "from spg.application.bootstrap import bootstrap; "
        "from spg.config import Settings; "
        "bootstrap(Settings(owner_runtime_mode='REQUIRED', "
        "executor_adapter='watt-native'))"],
        cwd=ROOT, env=environment, capture_output=True, text=True)
    assert result.returncode != 0
    assert "REQUIRED owner runtime needs canonical ECF v0.1" in result.stderr


def test_work_note_cannot_supply_product_invariant(source_repo: Path):
    ecf = pytest.importorskip("ecf.decision_context")
    gateway = WattDecisionContextGateway()
    req = requirement(source_repo, WORKSPACE_SURFACE)
    ready = gateway.require_ready(req, work_statement="UI change", work_revision="work-1")
    records = [view.record for view in ready.selected
               if ecf.ContextClass.PRODUCT_INVARIANT not in view.classes]
    local_note = ecf.GovernedContextRecord(
        context_id="work-local-note", classes=(ecf.ContextClass.PRODUCT_INVARIANT,),
        semantic_key="workspace-four-quadrants",
        scope=ecf.DecisionScope("watt", str(req.product_id), str(req.work_id)),
        source=ecf.SourceIdentity(ref="work:note", revision="work-2",
            authority_owner="WATT_PRODUCT_GOVERNOR", authority_ref="work:note",
            provenance="work:note"),
        content={"invariant": "This Work note claims to change Product policy"},
    )
    projected = ecf.assemble_context(ready.request,
                                     ecf.SourceSnapshot(tuple(records) + (local_note,)))
    assert projected.context_status.value == "INCOMPLETE"
    assert ecf.ContextClass.PRODUCT_INVARIANT in projected.missing_required_classes


def test_handoff_summary_projection_cannot_satisfy_session_contract(source_repo: Path):
    ecf = pytest.importorskip("ecf.decision_context")
    gateway = WattDecisionContextGateway()
    req = requirement(source_repo, "GOVERNED_SESSION_BOOTSTRAP")
    base = gateway.assemble(req)
    projected_summary = ecf.GovernedContextRecord(
        context_id="handoff-summary", classes=(ecf.ContextClass.APPROVED_DECISION,),
        semantic_key="handoff", scope=base.request.scope,
        source=ecf.SourceIdentity(ref="handoff:summary", revision="one",
            authority_owner="WATT_GOVERNANCE_GOVERNOR",
            authority_ref="handoff:summary", provenance="session:summary",
            kind=ecf.SourceKind.PROJECTION),
        content={"decision": "A summary is not a governed decision"},
    )
    package = ecf.assemble_context(base.request,
                                   ecf.SourceSnapshot((projected_summary,)))
    assert package.context_status.value == "INCOMPLETE"
    assert ecf.ContextClass.APPROVED_DECISION in package.missing_required_classes


def test_closure_service_requires_same_product_persisted_verification(
    source_repo: Path, monkeypatch,
):
    from spg.domain.verification import VerificationResultValue
    record_id, work_id = uuid4(), uuid4()
    req = requirement(source_repo, MILESTONE_SURFACE, work_id=work_id)
    record = SimpleNamespace(id=record_id, result=VerificationResultValue.PASS,
                             work_unit_id=uuid4(), basis_fingerprint="f" * 64)
    store = SimpleNamespace(
        verification_record=lambda _: record,
        work_unit=lambda _: SimpleNamespace(production_run_id=uuid4()),
        run=lambda _: SimpleNamespace(intent_ref=f"work:{work_id}"),
    )
    monkeypatch.setattr("spg.infrastructure.persistence.runtime_store.RuntimeStore",
                        lambda _: store)
    class Session:
        owner = req.product_id
        def execute(self, _):
            return SimpleNamespace(scalar_one_or_none=lambda: self.owner)
    class Database:
        def __init__(self):
            self.session = Session()
        def unit_of_work(self):
            database = self
            class Unit:
                session = database.session
                def __enter__(self):
                    return self
                def __exit__(self, *_):
                    return False
            return Unit()
    database = Database()
    service = MilestoneClosureContextService(database)
    ready = service.assess(req, verification_record_ids=(record_id,))
    assert ready.status == "CONTEXT_READY_FOR_GOVERNANCE"
    assert ready.context_status == "READY"
    assert not hasattr(ready, "closure_decision")
    database.session.owner = uuid4()
    missing = service.assess(req, verification_record_ids=(record_id,))
    assert missing.status == "DECISION_CONTEXT_NOT_READY"
    assert "VERIFICATION_EVIDENCE" in missing.missing_classes
    database.session.owner = req.product_id
    other_work = service.assess(replace(req, work_id=uuid4()),
                                verification_record_ids=(record_id,))
    assert other_work.status == "DECISION_CONTEXT_NOT_READY"


def test_verification_preserves_exact_lineage_without_fabricating_coverage(source_repo: Path):
    gateway = WattDecisionContextGateway()
    req = requirement(source_repo, WORKSPACE_SURFACE)
    lineage = gateway.lineage(gateway.require_ready(
        req, work_statement="UI change", work_revision="work-1"), req)
    verification = VerificationCapabilityRequest(
        verification_identity=uuid4(), obligation="NODE_TEST_TARGET",
        task_contract_id=uuid4(), snapshot_id=uuid4(),
        proposed_commit_identity="a" * 40, tree_identity="b" * 40,
        completion_evaluation_id=uuid4(), plan_revision_id=uuid4(),
        source_baseline_id=uuid4(),
        decision_context_fingerprint=lineage.package_fingerprint,
        protected_context_obligations=lineage.protected_obligations,
    )
    result = VerificationCapabilityResult(
        result=VerificationResultValue.PASS,
        evidence=VerificationEvidence(
            obligation="NODE_TEST_TARGET", subject_commit_identity="a" * 40,
            subject_tree_identity="b" * 40, expected="quadrants preserved",
            observed="PASS", metadata={
                "kind": "NODE_TEST_TARGET",
                "target": "tests/js/test_product_workspace_quadrants.cjs",
            },
        ),
    )
    context = _project_decision_context_evidence(verification, result)["metadata"]["decision_context"]
    assert context["package_fingerprint"] == lineage.package_fingerprint
    coverage = {item["context_class"]: item for item in context["protected_obligations"]}
    assert coverage["PRODUCT_INVARIANT"]["coverage"] == "COVERED"
    assert coverage["PRODUCT_INVARIANT"]["source_revision"] == next(
        item.source_revision for item in lineage.protected_obligations
        if item.context_class == "PRODUCT_INVARIANT")
    assert coverage["PRODUCT_INTENT"]["coverage"] == "UNVERIFIED"
    failed = result.model_copy(update={"result": VerificationResultValue.FAIL})
    failed_context = _project_decision_context_evidence(
        verification, failed)["metadata"]["decision_context"]
    assert all(item["coverage"] == "UNVERIFIED" for item in
               failed_context["protected_obligations"])


def test_guardian_receives_only_exact_covered_context_evidence(source_repo: Path):
    gateway = WattDecisionContextGateway()
    req = requirement(source_repo, WORKSPACE_SURFACE)
    lineage = gateway.lineage(gateway.require_ready(
        req, work_statement="UI change", work_revision="work-1"), req)
    obligation = next(item for item in lineage.protected_obligations
                      if item.context_class == "PRODUCT_INVARIANT")
    covered = {**obligation.model_dump(mode="json"), "coverage": "COVERED"}
    record = SimpleNamespace(id=uuid4(), result=VerificationResultValue.PASS,
        evidence=SimpleNamespace(metadata={"decision_context": {
            "package_fingerprint": lineage.package_fingerprint,
            "protected_obligations": [covered],
        }}))
    task_contract = SimpleNamespace(decision_context=lineage)
    projected = _protected_context_for_guardian(task_contract, (record,))
    invariant = next(item for item in projected
                     if item.context_class == "PRODUCT_INVARIANT")
    assert invariant.coverage == "COVERED"
    assert invariant.verification_refs == (f"verification:{record.id}",)
    assert all(not item.verification_refs for item in projected
               if item.context_class != "PRODUCT_INVARIANT")
    wrong_package = SimpleNamespace(id=uuid4(), result=VerificationResultValue.PASS,
        evidence=SimpleNamespace(metadata={"decision_context": {
            "package_fingerprint": "0" * 64, "protected_obligations": [covered],
        }}))
    assert all(item.coverage == "GUARDIAN_REQUIRED" for item in
               _protected_context_for_guardian(task_contract, (wrong_package,)))
