"""Executable Watt ↔ canonical ECF v0.1 decisions over real Watt sources."""

from pathlib import Path
from dataclasses import replace
from hashlib import sha256
import os
import shutil
import subprocess
import sys
from uuid import uuid4

import pytest

from spg.application.decision_context import (
    DecisionContextChanged,
    DecisionContextNotReady,
    DecisionContextRequirement,
    ECS_SURFACE,
    MILESTONE_SURFACE,
    WORKSPACE_SURFACE,
    WattDecisionContextGateway,
    policy_for_targets,
)
from spg.application.production_intelligence import (
    TaskContractRequest, default_task_contract_builder,
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
    assert "Agenda" in invariant.content and "Production" in invariant.content
    assert any(item.reference == invariant.source_ref for item in formed.relevant_context)
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
