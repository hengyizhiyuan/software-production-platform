"""Exact static review, independent assurance and restart gate regressions."""

from datetime import UTC, datetime
from hashlib import sha256
import subprocess
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen
from uuid import uuid4

import pytest

from guardian.runtime import JsonSoftwareAssuranceStore
from spg.application.guardian_assurance import GuardianAssuranceClient
from spg.domain.production_environment import CandidatePreviewMode, PreviewRuntimeStatus
from spg.domain.runtime import WorkUnitCondition
from spg.infrastructure.candidate_preview_runtime import DockerCandidatePreviewRuntime
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
        capture_output=True, text=True).stdout.strip()


@pytest.fixture
def static_runtime(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    git(root, "init", "-b", "accepted")
    git(root, "config", "user.name", "Assurance qualification")
    git(root, "config", "user.email", "assurance@example.invalid")
    (root / "index.html").write_text('<main>Home <a href="details.html">Details</a></main>')
    (root / "details.html").write_text("<main>Details</main>")
    (root / "secret.env").write_text("must not be served")
    (root / "unsafe.html").symlink_to("/etc/passwd")
    git(root, "add", ".")
    git(root, "commit", "-m", "Exact static result")
    revision, tree = git(root, "rev-parse", "HEAD"), git(root, "rev-parse", "HEAD^{tree}")
    provider = DockerCandidatePreviewRuntime(tmp_path / "preview", docker_binary="must-not-run-docker")
    identity = uuid4()
    provider.prepare(identity, root, revision, tree, mode=CandidatePreviewMode.STATIC_PREVIEW)
    provider.build(identity, revision, tree, mode=CandidatePreviewMode.STATIC_PREVIEW)
    served = provider.start(identity, revision, tree, mode=CandidatePreviewMode.STATIC_PREVIEW)
    yield provider, identity, revision, tree, served, root
    provider.shutdown()


def test_static_observations_use_git_bytes_not_workspace_and_recover(static_runtime):
    provider, identity, revision, tree, served, root = static_runtime
    expected = (root / "index.html").read_bytes()
    (provider._workspace(identity) / "index.html").write_text("uncommitted incorrect content")
    with urlopen(served["endpoint"]) as response:
        assert response.read() == expected
        assert response.headers["X-Candidate-Revision"] == revision
        assert response.headers["X-Candidate-Tree"] == tree
    evidence = provider.verify_served(identity, revision, tree, mode=CandidatePreviewMode.STATIC_PREVIEW)
    assert evidence["entrypoint_sha256"] == sha256(expected).hexdigest()
    provider.shutdown()
    assert not provider.probe(identity, revision, tree, mode=CandidatePreviewMode.STATIC_PREVIEW)
    provider.restore_static(identity, revision, tree)
    assert provider.probe(identity, revision, tree, mode=CandidatePreviewMode.STATIC_PREVIEW)
    assert not provider.probe(identity, revision, "f" * 40, mode=CandidatePreviewMode.STATIC_PREVIEW)


@pytest.mark.parametrize("path", ["secret.env", "unsafe.html", "%2e%2e/etc/passwd", ".git/config"])
def test_static_server_rejects_nonstatic_links_and_traversal(static_runtime, path):
    *_, served, _ = static_runtime
    with pytest.raises(HTTPError) as error:
        urlopen(served["endpoint"] + path)
    assert error.value.code == 404


@pytest.mark.parametrize("missing_second_coverage", [False, True])
def test_real_guardian_covers_each_required_pwu_not_root_context(
    static_runtime, tmp_path, monkeypatch, missing_second_coverage,
):
    provider, preview_id, revision, tree, served, _ = static_runtime
    work_id, scope_id, plan_id, candidate_id = (uuid4() for _ in range(4))
    tasks, units, records = [], [], []
    for index, path in enumerate(("index.html", "details.html")):
        fingerprint = str(index + 1) * 64
        obligation = SimpleNamespace(context_class="PRODUCT_INVARIANT", semantic_key=f"keep-{index}",
            source_ref=f"product-invariant:{index}", source_revision=revision)
        task = SimpleNamespace(task_contract_id=uuid4(), content_fingerprint=fingerprint,
            decision_context=SimpleNamespace(package_fingerprint=fingerprint, protected_obligations=(obligation,)))
        unit = SimpleNamespace(id=uuid4(), source_baseline_id=uuid4(), verified_output_baseline_id=uuid4(),
            condition=WorkUnitCondition.SATISFIED, current_execution_generation=1,
            parent_baseline_ids=(), reconciliation_evidence={"parents": ["qualified-a", "qualified-b"]} if index else None,
            completion_contract=SimpleNamespace(task_contract=task, required_outputs=(path,), required_changes=()))
        record = SimpleNamespace(id=uuid4(), proposed_commit_identity=revision, tree_identity=tree,
            plan_revision_id=plan_id, source_baseline_id=unit.source_baseline_id,
            result=SimpleNamespace(value="PASS"), evidence=SimpleNamespace(metadata={"decision_context": {
                "package_fingerprint": fingerprint,
                "protected_obligations": [{**vars(obligation), "coverage":
                    "UNVERIFIED" if index and missing_second_coverage else "COVERED"}]}}))
        tasks.append(task); units.append(unit); records.append(record)
    work = SimpleNamespace(engineering_scope_id=scope_id, current_work_reality_revision_id=uuid4(),
        desired_outcome="Home and details are available", constraints=())
    binding = SimpleNamespace(work_unit_id=units[0].id, plan_revision_id=plan_id)
    product = SimpleNamespace(work=lambda _: work, scope_for_work=lambda _: SimpleNamespace(id=scope_id),
        runtime_binding=lambda _: binding)
    runtime = SimpleNamespace(baseline_candidate=lambda _: SimpleNamespace(satisfied_work_unit_ids=[unit.id for unit in units]),
        plan_revision=lambda _: SimpleNamespace(id=plan_id, revision_number=1), work_units_for_plan=lambda _: units,
        snapshot=lambda _: SimpleNamespace(repository_revision=revision, repository_tree_identity=tree),
        verification_records_for_work_unit=lambda identity: (records[[u.id for u in units].index(identity)],),
        attempts_for_work_unit=lambda _: ())
    monkeypatch.setattr("spg.application.guardian_assurance.ProductStore", lambda _: product)
    monkeypatch.setattr("spg.application.guardian_assurance.RuntimeStore", lambda _: runtime)
    class Uow:
        session = SimpleNamespace(execute=lambda *_: SimpleNamespace(scalar_one_or_none=lambda: uuid4()))
        def __enter__(self): return self
        def __exit__(self, *_): pass
    context = {"candidate_id": str(candidate_id), "candidate_fingerprint": "a" * 64,
        "repository_revision": revision, "tree": tree, "artifacts": ["index.html", "details.html"],
        "paths": ["index.html", "details.html"], "verification_references": [f"verification:{r.id}" for r in records]}
    delivery = SimpleNamespace(database=SimpleNamespace(unit_of_work=Uow), candidate_context=lambda _: context)
    preview = SimpleNamespace(id=preview_id, work_id=work_id, candidate_id=candidate_id,
        candidate_fingerprint="a" * 64, repository_revision=revision, repository_tree=tree,
        mode=CandidatePreviewMode.STATIC_PREVIEW, status=PreviewRuntimeStatus.READY,
        endpoint=served["endpoint"], created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
    store = JsonProductionEnvironmentStore(tmp_path / "state")
    monkeypatch.setattr(store, "current_candidate_preview", lambda _: preview)
    monkeypatch.setattr(store, "candidate_preview_history", lambda _: ())
    owner = JsonSoftwareAssuranceStore(tmp_path / "guardian")
    client = GuardianAssuranceClient(delivery, store, owner)
    result = client.assess_ready_preview(preview)
    assert len(result["result_refs"]) == 2
    assert result["required_pwu_ids"] == [str(unit.id) for unit in units]
    assert result["gate"] == ("BLOCKED" if missing_second_coverage else "PASS")
    assert result["status"] == ("BLOCKED" if missing_second_coverage else "PASS")
    assert client.passed(work_id, candidate_id) is (not missing_second_coverage)
    assert len(list((owner.root / "requests").glob("*.json"))) == 2
    assert store.guardian_requirements(work_id, work.current_work_reality_revision_id) is not None
    if not missing_second_coverage:
        list((owner.root / "results").glob("*.json"))[1].unlink()
        assert not client.passed(work_id, candidate_id)
        assert client.projection(work_id)["status"] == "BLOCKED"
