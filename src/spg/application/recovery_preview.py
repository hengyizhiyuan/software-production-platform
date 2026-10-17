"""Explicitly authorized inspection of a retained, unaccepted static snapshot.

This uses existing Work governance and Preview ownership. It creates no Candidate,
Verification PASS, delivery, acceptance or automatic production continuation.
"""
from hashlib import sha256
from pathlib import Path, PurePosixPath
from uuid import UUID

from spg.domain.product import ProductInvariantViolation
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore


def recovery_preview_context(database, work_id: UUID):
    with database.unit_of_work() as uow:
        work = ProductStore(uow.session).work(work_id)
        if work is None:
            return None
        records = [r for r in RuntimeStore(uow.session).governance_for_subject(str(work_id))
                   if r.decision_type in {"WORK_RECOVERY_PREVIEW", "WORKING_PREVIEW_OBSERVED"}]
        if records and records[-1].decision_type == "WORKING_PREVIEW_OBSERVED":
            binding = ProductStore(uow.session).runtime_binding(work_id)
            if (binding is None or records[-1].scope.get("production_run_id") != str(binding.production_run_id)
                    or records[-1].scope.get("plan_revision_id") != str(binding.plan_revision_id)):
                return None
    if not records:
        return None
    record = records[-1]
    scope = record.scope
    if (scope.get("work_reality_revision_id") != str(work.current_work_reality_revision_id)
            or scope.get("work_id") != str(work_id)):
        return None
    snapshot = scope.get("snapshot", "")
    files = scope.get("files", {})
    if (not isinstance(snapshot, str) or len(snapshot) != 64
            or any(c not in "0123456789abcdef" for c in snapshot)
            or not isinstance(files, dict) or "index.html" not in files):
        raise ProductInvariantViolation("Recovery preview snapshot is invalid")
    import json
    if sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest() != snapshot:
        raise ProductInvariantViolation("Recovery preview manifest identity differs")
    return {"status": "AVAILABLE", "work_id": str(work_id), "snapshot": snapshot,
            "url": f"/api/works/{work_id}/recovery-preview/{snapshot}/index.html",
            "verification": "NOT_QUALIFIED", "authorization_pending": True,
            "governance_record_id": str(record.id), "files": files}


def capture_working_preview(database, root: Path, work_id: UUID, snapshot_id: UUID):
    """Expose an exact observed static artifact before semantic qualification.

    Cheap source/scope checks protect inspection. This records an observation,
    never a Human decision or a replacement for final verification/assurance.
    """
    from datetime import datetime, UTC
    import json
    import subprocess
    from uuid import uuid5, NAMESPACE_URL
    def git(repository, *args):
        return subprocess.check_output(["git", "--no-replace-objects", "-C", str(repository), *args],
                                       timeout=15, stderr=subprocess.DEVNULL)
    with database.unit_of_work() as uow:
        runtime = RuntimeStore(uow.session)
        work = ProductStore(uow.session).work(work_id)
        binding = ProductStore(uow.session).runtime_binding(work_id)
        proposed = runtime.proposed_snapshot(snapshot_id)
        if work is None or binding is None or proposed is None:
            return None
        unit = runtime.work_unit(proposed.work_unit_id)
        if (unit.production_run_id != binding.production_run_id
                or unit.plan_revision_id != binding.plan_revision_id
                or binding.work_reality_revision_id != work.current_work_reality_revision_id):
            return None
        contract = unit.completion_contract.change_contract
        if contract is None or not any(t.path.endswith(".html") for t in contract.exact_targets):
            return None
        dispatch = runtime.execution_dispatch_for_attempt(proposed.attempt_id)
        repository = dispatch.workspace.repository_path
        revision, tree = proposed.proposed_commit_identity, proposed.tree_identity
        if git(repository, "rev-parse", revision + "^{tree}").decode().strip() != tree:
            raise ProductInvariantViolation("Working preview source tree differs")
        changed = git(repository, "diff", "--name-only", contract.source_revision, revision, "--").decode().splitlines()
        if not changed or any(not contract.allows_path(p) for p in changed):
            return None
        work_revision = str(work.current_work_reality_revision_id)
    content = {}
    total = 0
    for entry in git(repository, "ls-tree", "-r", "-z", revision).split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        path = path.decode()
        if (PurePosixPath(path).suffix not in {".html", ".js", ".mjs", ".css", ".json", ".svg", ".png", ".ico"}
                or any(part.startswith(".") for part in PurePosixPath(path).parts)):
            continue
        if mode not in {"100644", "100755"} or kind != "blob":
            return None
        data = git(repository, "cat-file", "blob", oid)
        total += len(data)
        if total > 1024 * 1024 or len(content) >= 128:
            return None
        content[path] = data
    if "index.html" not in content:
        return None
    files = {p: sha256(data).hexdigest() for p, data in content.items()}
    snapshot = sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    directory = root / str(work_id) / snapshot
    for path, data in content.items():
        file = directory / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)
    identity = uuid5(NAMESPACE_URL, f"watt:working-preview:{work_id}:{work_revision}:{snapshot_id}")
    with database.unit_of_work() as uow:
        # A concurrently revised request cannot expose an old working artifact.
        if str(ProductStore(uow.session).work(work_id).current_work_reality_revision_id) != work_revision:
            return None
        runtime = RuntimeStore(uow.session)
        if not any(r.id == identity for r in runtime.governance_for_subject(str(work_id))):
            runtime.insert_governance({"id": identity, "decision_type": "WORKING_PREVIEW_OBSERVED",
                "authority_identity": "system:preview-owner", "subject_type": "WORK",
                "subject_identity": str(work_id), "scope": {"work_id": str(work_id),
                    "work_reality_revision_id": work_revision, "snapshot": snapshot, "files": files,
                    "proposed_snapshot_id": str(snapshot_id), "repository_revision": revision,
                    "production_run_id": str(binding.production_run_id), "plan_revision_id": str(binding.plan_revision_id),
                    "repository_tree": tree, "verification": "NOT_QUALIFIED"},
                "rationale": "Exact observed artifact available for inspection; qualification and acceptance pending",
                "created_at": datetime.now(UTC)})
            uow.commit()
    return recovery_preview_context(database, work_id)


def recovery_preview_artifact(database, root: Path, work_id: UUID, snapshot: str, path: str):
    context = recovery_preview_context(database, work_id)
    relative = PurePosixPath(path)
    if (context is None or snapshot != context["snapshot"] or path not in context["files"]
            or relative.is_absolute() or ".." in relative.parts
            or relative.suffix not in {".html", ".js", ".mjs", ".css", ".json", ".svg", ".png", ".ico"}):
        raise ProductInvariantViolation("Recovery preview artifact is unavailable")
    directory = root / str(work_id) / snapshot
    file = directory / path
    if (file.is_symlink() or not file.resolve().is_relative_to(directory.resolve())
            or not file.is_file() or file.stat().st_size > 5 * 1024 * 1024):
        raise ProductInvariantViolation("Recovery preview artifact is unavailable")
    data = file.read_bytes()
    if sha256(data).hexdigest() != context["files"][path]:
        raise ProductInvariantViolation("Recovery preview artifact identity differs")
    return data
