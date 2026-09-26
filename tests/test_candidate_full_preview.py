"""Permanent protections for exact Candidate-bound Production Environment Preview."""

from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import time
import urllib.request
from uuid import UUID, uuid4

import pytest

from spg.application.candidate_preview import (
    CandidatePreviewApplicationService, CandidatePreviewUnavailable,
)
from spg.domain.production_environment import (
    CandidatePreviewMode, CandidatePreviewSessionV1, EnvironmentProviderError,
    PreviewRuntimeStatus,
)
from spg.infrastructure.candidate_preview_runtime import DockerCandidatePreviewRuntime
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], check=True,
        capture_output=True, text=True)
    return result.stdout.strip()


def candidate_repository(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "preview@example.invalid")
    git(root, "config", "user.name", "Preview Test")
    for path in ("Dockerfile", "pyproject.toml", "uv.lock", "docker/start_app.py", "alembic.ini", "src/app.py", "migrations/.keep"):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path, encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "candidate")
    return root, git(root, "rev-parse", "HEAD"), git(root, "rev-parse", "HEAD^{tree}")


class CandidateSource:
    def __init__(self, context: dict):
        self.context = context

    def candidate_context(self, _work_id):
        return self.context


class RuntimeProvider:
    definition_version = "test-runtime-v1"

    def __init__(self):
        self.alive = True
        self.stopped = []

    def prepare(self, _preview_id, _repository, revision, tree, *, mode=None):
        return {"revision": revision, "tree": tree}

    def build(self, _preview_id, _revision, _tree, *, mode=None):
        return {"image_id": "sha256:" + "a" * 64, "build_log": "evidence:build"}

    def start(self, _preview_id, revision, tree, *, mode=None):
        return {"endpoint": "http://127.0.0.1:18053/app", "services": ("app", "postgres", "proxy"),
            "resources": ("isolated-database",), "health": {"repository_revision": revision, "repository_tree": tree}}

    def probe(self, _preview_id, _revision, _tree, *, mode=None):
        return self.alive

    def stop(self, preview_id):
        self.stopped.append(preview_id)
        self.alive = False


def context(repository: Path, revision: str, tree: str) -> dict:
    return {"candidate_id": str(uuid4()), "candidate_fingerprint": uuid4().hex,
        "repository_identity": "local://test", "repository_path": repository,
        "repository_revision": revision, "tree": tree, "artifacts": ("src/app.py",),
        "entrypoint": None, "source_revision": revision, "target_branch": "main",
        "task_contract_reference": f"task-contract:{uuid4()}",
        "verification_references": (f"verification:{uuid4()}",)}


def await_ready(service: CandidatePreviewApplicationService, work_id):
    until = time.monotonic() + 20
    while time.monotonic() < until:
        current = service.store.current_candidate_preview(work_id)
        if current and current.status in {PreviewRuntimeStatus.READY, PreviewRuntimeStatus.FAILED}:
            return current
        time.sleep(0.02)
    raise AssertionError("Preview did not reach a terminal preparation state")


def test_exact_candidate_preparation_rejects_tree_mismatch(tmp_path: Path):
    repository, revision, tree = candidate_repository(tmp_path)
    provider = DockerCandidatePreviewRuntime(tmp_path / "preview")
    with pytest.raises(EnvironmentProviderError, match="differs from sealed Candidate"):
        provider.prepare(uuid4(), repository, revision, "a" * 40)
    prepared = provider.prepare(uuid4(), repository, revision, tree)
    assert prepared["revision"] == revision
    assert prepared["tree"] == tree


def test_ready_requires_exact_candidate_and_stale_preview_is_invalidated(tmp_path: Path):
    repository, revision, tree = candidate_repository(tmp_path)
    source = CandidateSource(context(repository, revision, tree))
    provider = RuntimeProvider()
    store = JsonProductionEnvironmentStore(tmp_path / "production-environments")
    service = CandidatePreviewApplicationService(source, store, provider)
    work_id = uuid4()
    requested = service.request(work_id)
    ready = await_ready(service, work_id)
    assert ready.status is PreviewRuntimeStatus.READY
    assert ready.candidate_id == requested.candidate_id
    assert ready.repository_revision == revision
    assert ready.repository_tree == tree
    assert store.get_environment(ready.environment_id).lifecycle_state.value == "ACTIVE"
    record = next(item for item in ready.evidence if item["kind"] == "PRODUCTION_RECORD")
    assert store.get_production_record(UUID(record["reference"].split(":", 1)[1])) is not None
    boundary = store.root / "candidate-previews" / "evidence" / str(ready.id)
    assert (boundary / "ecf-change-reality.json").is_file()
    assert (boundary / "guardian-intake.json").is_file()
    ready_reality = json.loads((boundary / "preview-reality" / f"{ready.version}.json").read_text())
    assert ready_reality["runtime_state"] == "READY"
    assert ready_reality["preview_endpoint"] == ready.endpoint
    assert ready_reality["candidate_revision"] == revision
    assert service.require_ready(work_id, ready.candidate_id).id == ready.id
    assert service.request(work_id).id == ready.id
    source.context = {**source.context, "candidate_id": str(uuid4()), "candidate_fingerprint": uuid4().hex}
    stale = service.current(work_id)
    assert stale.status is PreviewRuntimeStatus.STALE
    assert stale.endpoint is None
    assert provider.stopped == [ready.id]
    assert store.get_environment(ready.environment_id).lifecycle_state.value == "DESTROYED"
    stale_reality = json.loads((boundary / "preview-reality" / f"{stale.version}.json").read_text())
    assert stale_reality["runtime_state"] == "STALE"
    assert stale_reality["preview_endpoint"] is None
    with pytest.raises(CandidatePreviewUnavailable):
        service.require_ready(work_id, ready.candidate_id)
    assert store.get_candidate_preview(ready.id).version > 1


def test_full_application_delivery_requires_exact_served_runtime_evidence(tmp_path: Path):
    repository, revision, tree = candidate_repository(tmp_path)
    source = CandidateSource(context(repository, revision, tree))
    work_id = uuid4()
    unverified = CandidatePreviewApplicationService(source,
        JsonProductionEnvironmentStore(tmp_path / "unverified"), RuntimeProvider())
    unverified.request(work_id)
    first = await_ready(unverified, work_id)
    with pytest.raises(CandidatePreviewUnavailable, match="served-runtime"):
        unverified.require_served_for_delivery(work_id, first.candidate_id,
            revision, tree)

    class ServedProvider(RuntimeProvider):
        def verify_served(self, _preview_id, observed_revision, observed_tree,
            *, mode=None):
            return {"result": "PASS", "candidate_revision": observed_revision,
                "candidate_tree": observed_tree,
                "database_round_trip": {"created_status": 201,
                    "observed_status": 200}}

    verified = CandidatePreviewApplicationService(source,
        JsonProductionEnvironmentStore(tmp_path / "verified"), ServedProvider())
    verified.request(work_id)
    second = await_ready(verified, work_id)
    assert verified.require_served_for_delivery(work_id, second.candidate_id,
        revision, tree).id == second.id
    with pytest.raises(CandidatePreviewUnavailable, match="served-runtime"):
        verified.require_served_for_delivery(work_id, second.candidate_id,
            revision, "0" * 40)


def test_restart_reconciles_missing_runtime_without_claiming_ready(tmp_path: Path):
    repository, revision, tree = candidate_repository(tmp_path)
    source = CandidateSource(context(repository, revision, tree))
    provider = RuntimeProvider()
    store = JsonProductionEnvironmentStore(tmp_path / "production-environments")
    service = CandidatePreviewApplicationService(source, store, provider)
    work_id = uuid4()
    service.request(work_id)
    ready = await_ready(service, work_id)
    assert ready.status is PreviewRuntimeStatus.READY
    provider.alive = False
    recovered = CandidatePreviewApplicationService(source, store, provider)
    recovered.restore()
    after = store.current_candidate_preview(work_id)
    assert after.status is PreviewRuntimeStatus.FAILED
    assert after.endpoint is None
    assert after.failure_code == "RESTART_RECONCILIATION"
    with pytest.raises(CandidatePreviewUnavailable):
        recovered.require_ready(work_id, ready.candidate_id)


def test_unhealthy_runtime_never_becomes_ready_and_cleanup_is_recorded(tmp_path: Path):
    repository, revision, tree = candidate_repository(tmp_path)
    source = CandidateSource(context(repository, revision, tree))
    provider = RuntimeProvider()
    provider.alive = False
    store = JsonProductionEnvironmentStore(tmp_path / "production-environments")
    service = CandidatePreviewApplicationService(source, store, provider)
    work_id = uuid4()
    requested = service.request(work_id)
    failed = await_ready(service, work_id)
    assert failed.status is PreviewRuntimeStatus.FAILED
    assert failed.endpoint is None
    assert failed.failure_code == "STARTUP_FAILED"
    assert "failed readiness" in failed.failure_reason
    assert any(item.get("technical_evidence", {}).get("sha256")
        for item in failed.evidence if item["kind"] == "FAILURE")
    assert provider.stopped == [requested.id]
    until = time.monotonic() + 5
    while store.get_environment(failed.environment_id).lifecycle_state.value != "DESTROYED" and time.monotonic() < until:
        time.sleep(0.02)
    assert store.get_environment(failed.environment_id).lifecycle_state.value == "DESTROYED"
    with pytest.raises(CandidatePreviewUnavailable):
        service.require_ready(work_id, requested.candidate_id)


def test_stop_removes_runtime_but_retains_record_and_human_evidence(tmp_path: Path):
    repository, revision, tree = candidate_repository(tmp_path)
    source = CandidateSource(context(repository, revision, tree))
    provider = RuntimeProvider()
    store = JsonProductionEnvironmentStore(tmp_path / "production-environments")
    service = CandidatePreviewApplicationService(source, store, provider)
    work_id = uuid4()
    requested = service.request(work_id)
    ready = await_ready(service, work_id)
    authorized = service.record_authorization(work_id, "human:reviewer")
    assert any(item["kind"] == "HUMAN_CANDIDATE_AUTHORIZATION"
        and item["preview_id"] == str(requested.id)
        and item["candidate_revision"] == revision
        and item["readiness_evidence"] == ("BUILD", "RUNTIME")
        and item["production_record_reference"].startswith("production-record:")
        for item in authorized.evidence)
    stopped = service.stop(work_id)
    assert stopped.status is PreviewRuntimeStatus.STOPPED
    assert stopped.endpoint is None
    assert provider.stopped == [requested.id]
    assert store.get_environment(stopped.environment_id).lifecycle_state.value == "DESTROYED"
    assert any(item["kind"] == "PRODUCTION_RECORD" for item in stopped.evidence)
    with pytest.raises(CandidatePreviewUnavailable):
        service.require_ready(work_id, requested.candidate_id)


def test_unobservable_runtime_does_not_falsely_record_failure(tmp_path: Path):
    repository, revision, tree = candidate_repository(tmp_path)
    source = CandidateSource(context(repository, revision, tree))
    provider = RuntimeProvider()
    store = JsonProductionEnvironmentStore(tmp_path / "production-environments")
    service = CandidatePreviewApplicationService(source, store, provider)
    work_id = uuid4()
    service.request(work_id)
    ready = await_ready(service, work_id)

    def unavailable(*_args, **_kwargs):
        raise EnvironmentProviderError("Docker authority unavailable")

    provider.probe = unavailable
    with pytest.raises(CandidatePreviewUnavailable, match="cannot currently be inspected"):
        service.current(work_id)
    assert store.current_candidate_preview(work_id).status is PreviewRuntimeStatus.READY
    assert provider.stopped == []


def test_ready_contract_rejects_missing_runtime_identity():
    now = datetime.now(UTC)
    with pytest.raises(ValueError, match="READY Preview requires"):
        CandidatePreviewSessionV1(id=uuid4(), work_id=uuid4(), candidate_id=uuid4(),
            candidate_fingerprint="fingerprint", repository_identity="local://test",
            repository_revision="a" * 40, repository_tree="b" * 40,
            workspace_id=uuid4(), environment_id=uuid4(),
            mode=CandidatePreviewMode.FULL_APPLICATION_RUNTIME,
            status=PreviewRuntimeStatus.READY, definition_version="test",
            created_at=now, updated_at=now)


def test_mode_selection_uses_candidate_runtime_and_changed_artifacts(tmp_path: Path):
    root = tmp_path / "frontend"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "preview@example.invalid")
    git(root, "config", "user.name", "Preview Test")
    (root / "Dockerfile").write_text("FROM nginx:alpine\nCOPY index.html /usr/share/nginx/html/index.html\nEXPOSE 80\n")
    (root / "package.json").write_text('{"name":"preview-test","version":"1.0.0"}')
    (root / "index.html").write_text("<h1>Changed frontend</h1>")
    git(root, "add", ".")
    git(root, "commit", "-m", "frontend candidate")
    candidate = context(root, git(root, "rev-parse", "HEAD"), git(root, "rev-parse", "HEAD^{tree}"))
    candidate["artifacts"] = ("index.html",)
    assert CandidatePreviewApplicationService.mode_for(candidate) is CandidatePreviewMode.FRONTEND_RUNTIME
    candidate["artifacts"] = ("docs/guide.md",)
    assert CandidatePreviewApplicationService.mode_for(candidate) is None
    candidate["entrypoint"] = "index.html"
    assert CandidatePreviewApplicationService.mode_for(candidate) is CandidatePreviewMode.STATIC_PREVIEW


@pytest.mark.real_container
def test_frontend_runtime_has_real_endpoint_and_deterministic_cleanup(tmp_path: Path):
    if subprocess.run(["docker", "info"], capture_output=True, check=False).returncode:
        pytest.skip("local Docker Engine is unavailable")
    if subprocess.run(["docker", "image", "inspect", "watt-native-executor-runtime:local"],
        capture_output=True, check=False).returncode:
        pytest.skip("qualified source-verification image is unavailable")
    root = tmp_path / "frontend"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "preview@example.invalid")
    git(root, "config", "user.name", "Preview Test")
    (root / "Dockerfile").write_text("FROM nginx:1.27-alpine\nCOPY index.html /usr/share/nginx/html/index.html\nEXPOSE 80\n")
    (root / "package.json").write_text('{"name":"preview-test","version":"1.0.0"}')
    (root / "index.html").write_text("<h1>Candidate frontend is running</h1>")
    git(root, "add", ".")
    git(root, "commit", "-m", "frontend candidate")
    revision, tree = git(root, "rev-parse", "HEAD"), git(root, "rev-parse", "HEAD^{tree}")
    preview_id = uuid4()
    provider = DockerCandidatePreviewRuntime(tmp_path / "runtime")
    names = provider._names(preview_id)
    try:
        assert provider.prepare(preview_id, root, revision, tree,
            mode=CandidatePreviewMode.FRONTEND_RUNTIME)["revision"] == revision
        assert provider.build(preview_id, revision, tree,
            mode=CandidatePreviewMode.FRONTEND_RUNTIME)["image_id"].startswith("sha256:")
        runtime = provider.start(preview_id, revision, tree,
            mode=CandidatePreviewMode.FRONTEND_RUNTIME)
        assert provider.probe(preview_id, revision, tree, mode=CandidatePreviewMode.FRONTEND_RUNTIME)
        with urllib.request.urlopen(runtime["endpoint"], timeout=10) as response:
            assert b"Candidate frontend is running" in response.read()
    finally:
        provider.stop(preview_id)
    for command in (("inspect", names["app"]), ("network", "inspect", names["internal"]),
        ("volume", "inspect", names["source"])):
        assert subprocess.run(["docker", *command], capture_output=True, check=False).returncode != 0
