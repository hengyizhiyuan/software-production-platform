"""Read sealed predecessor artifacts for comparison, without promoting their source."""
from pathlib import PurePosixPath
from uuid import UUID

from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore


def predecessor_candidate_sources(database, work_revision_id, contract):
    """The immediate prior Work revision is the only comparison lineage here.

    Its last already-sealed Candidate can explain a requested refinement. It is
    neither the current source baseline nor permission, acceptance or current PASS.
    """
    if work_revision_id is None:
        return ()
    with database.unit_of_work() as uow:
        product, runtime = ProductStore(uow.session), RuntimeStore(uow.session)
        revision = product.work_reality_revision(UUID(str(work_revision_id)))
        if revision is None or revision.previous_revision_id is None:
            return ()
        bindings = [b for b in product.runtime_bindings(revision.work_id)
            if b.work_reality_revision_id == revision.previous_revision_id]
        candidates = [(b, candidate) for b in bindings
            for candidate in runtime.baseline_candidates_for_work_unit(b.work_unit_id)
            if candidate.sealed_at <= revision.created_at]
        if not candidates:
            return ()
        binding, candidate = max(candidates, key=lambda pair: (pair[1].sealed_at, str(pair[1].id)))
        if candidate.repository_identity != contract.repository_identity:
            raise ValueError("VERIFICATION_COMPARISON_REPOSITORY_MISMATCH")
        snapshot = runtime.proposed_snapshot(candidate.proposed_snapshot_id)
        if (snapshot is None or snapshot.proposed_commit_identity != candidate.proposed_commit_identity
                or snapshot.tree_identity != candidate.proposed_tree_identity
                or not candidate.verification_record_ids):
            raise ValueError("VERIFICATION_COMPARISON_SUBJECT_MISMATCH")
        for identity in candidate.verification_record_ids:
            record = runtime.verification_record(identity)
            if (record is None or record.result.value != "PASS"
                    or record.proposed_commit_identity != candidate.proposed_commit_identity
                    or record.tree_identity != candidate.proposed_tree_identity):
                raise ValueError("VERIFICATION_COMPARISON_EVIDENCE_MISMATCH")
        dispatch = runtime.execution_dispatch_for_attempt(snapshot.attempt_id)
        if dispatch is None:
            raise ValueError("VERIFICATION_COMPARISON_WORKSPACE_MISSING")
        repository = dispatch.workspace.repository_path
    from spg.providers.protected_context_verifier import git, TEXT_SUFFIXES
    from hashlib import sha256
    if git(repository, "rev-parse", candidate.proposed_commit_identity + "^{tree}").decode().strip() != candidate.proposed_tree_identity:
        raise ValueError("VERIFICATION_COMPARISON_TREE_MISMATCH")
    targets = {target.path for target in contract.exact_targets}
    sources = {}
    total = 0
    for entry in git(repository, "ls-tree", "-r", "-z", candidate.proposed_commit_identity).split(b"\0"):
        if not entry:
            continue
        meta, raw_path = entry.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        path = raw_path.decode()
        if path not in targets or PurePosixPath(path).suffix not in TEXT_SUFFIXES:
            continue
        if mode not in {"100644", "100755"} or kind != "blob":
            raise ValueError("VERIFICATION_COMPARISON_NONREGULAR_SOURCE")
        size = int(git(repository, "cat-file", "-s", oid))
        total += size
        if size > 100000 or total > 1000000 or len(sources) >= 128:
            raise ValueError("VERIFICATION_COMPARISON_SOURCE_LIMIT")
        body = git(repository, "cat-file", "blob", oid)
        sources[path] = {"sha256": sha256(body).hexdigest(), "content": body.decode("utf-8")}
    return ({"work_id": str(revision.work_id), "work_reality_revision_id": str(revision.previous_revision_id),
        "candidate_id": str(candidate.id), "candidate_fingerprint": candidate.fingerprint,
        "candidate_revision": candidate.proposed_commit_identity, "candidate_tree": candidate.proposed_tree_identity,
        "verification_refs": [str(identity) for identity in candidate.verification_record_ids],
        "comparison_only": True, "grants_current_pass_or_authority": False, "sources": sources},)
