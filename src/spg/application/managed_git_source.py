"""Durable Git source for repository-optional Work.

The executable checkout is disposable.  Git's complete reachable history is
stored as a checked bundle in the durable product database and can be cloned
on a different worker host.  Database durability/backup is a deployment
requirement; a local-only PostgreSQL volume does not prove machine-loss safety.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
from tempfile import NamedTemporaryFile
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from spg.domain.product import ProductInvariantViolation
from spg.infrastructure.persistence.managed_repository_schema import managed_repository_sources

MAX_BUNDLE_BYTES = 128 * 1024 * 1024


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C",
        str(repository), *arguments], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise ProductInvariantViolation("Managed Git source operation failed")
    return result.stdout.strip()


class ManagedGitSource:
    def __init__(self, database):
        self.database = database

    def has_source(self, identity: str) -> bool:
        with self.database.unit_of_work() as uow:
            return uow.session.execute(select(
                managed_repository_sources.c.repository_identity).where(
                    managed_repository_sources.c.repository_identity == identity
            )).scalar_one_or_none() is not None

    def export_bundle(self, identity: str) -> tuple[bytes, dict[str, str]]:
        with self.database.unit_of_work() as uow:
            row = uow.session.execute(select(managed_repository_sources).where(
                managed_repository_sources.c.repository_identity == identity
            )).mappings().one_or_none()
        if row is None:
            raise ProductInvariantViolation("Managed repository has no durable canonical source")
        bundle = bytes(row["git_bundle"])
        if sha256(bundle).hexdigest() != row["bundle_sha256"]:
            raise ProductInvariantViolation("Managed repository source integrity check failed")
        return bundle, {"repository_ref": row["repository_ref"],
            "revision": row["revision"], "tree": row["tree"],
            "bundle_sha256": row["bundle_sha256"]}

    def sync(self, identity: str, repository: Path, *, session=None,
        internal_branch: bool = False) -> dict[str, str]:
        managed_branch = identity.startswith("watt://work-branches/")
        if not (identity.startswith("watt://repositories/")
                or (managed_branch and (internal_branch or self.has_source(identity)))):
            raise ProductInvariantViolation("Only Watt-managed repositories can use managed source storage")
        repository = repository.resolve()
        ref = _git(repository, "symbolic-ref", "HEAD")
        revision = _git(repository, "rev-parse", "HEAD")
        tree = _git(repository, "rev-parse", "HEAD^{tree}")
        if _git(repository, "rev-parse", ref) != revision:
            raise ProductInvariantViolation("Managed source ref changed during capture")
        with NamedTemporaryFile(prefix="watt-managed-git-", suffix=".bundle") as temporary:
            _git(repository, "bundle", "create", temporary.name, "--all")
            bundle = Path(temporary.name).read_bytes()
        if not bundle or len(bundle) > MAX_BUNDLE_BYTES:
            raise ProductInvariantViolation("Managed Git source exceeds the bounded storage profile")
        digest = sha256(bundle).hexdigest()
        values = dict(repository_identity=identity, owner_actor_id="human:owner",
            repository_ref=ref, revision=revision, tree=tree,
            bundle_sha256=digest, git_bundle=bundle, updated_at=datetime.now(UTC))

        def persist(selected_session):
            selected_session.execute(insert(managed_repository_sources).values(**values)
                .on_conflict_do_update(index_elements=[managed_repository_sources.c.repository_identity],
                    set_={key: value for key, value in values.items()
                        if key != "repository_identity"}))

        if session is None:
            with self.database.unit_of_work() as uow:
                persist(uow.session)
                uow.commit()
        else:
            persist(session)
        return {"repository_identity": identity, "repository_ref": ref,
            "revision": revision, "tree": tree, "bundle_sha256": digest}

    def recover(self, identity: str, destination: Path) -> dict[str, str]:
        with self.database.unit_of_work() as uow:
            row = uow.session.execute(select(managed_repository_sources).where(
                managed_repository_sources.c.repository_identity == identity
            )).mappings().one_or_none()
        if row is None:
            raise ProductInvariantViolation("Managed repository has no durable canonical source")
        if sha256(row["git_bundle"]).hexdigest() != row["bundle_sha256"]:
            raise ProductInvariantViolation("Managed repository source integrity check failed")
        destination = destination.resolve()
        if destination.exists():
            revision = _git(destination, "rev-parse", row["repository_ref"])
            tree = _git(destination, "rev-parse", f"{revision}^{{tree}}")
            if (revision, tree) != (row["revision"], row["tree"]):
                raise ProductInvariantViolation("Execution checkout differs from canonical managed source")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            staging = destination.parent / f".{destination.name}.restore-{uuid4().hex}"
            try:
                with NamedTemporaryFile(prefix="watt-managed-restore-", suffix=".bundle") as temporary:
                    Path(temporary.name).write_bytes(row["git_bundle"])
                    result = subprocess.run(["git", "clone", "--no-checkout", "--",
                        temporary.name, str(staging)], capture_output=True,
                        text=True, timeout=120)
                    if result.returncode:
                        raise ProductInvariantViolation("Managed Git bundle cannot be cloned")
                branch = row["repository_ref"].removeprefix("refs/heads/")
                _git(staging, "checkout", "-B", branch, row["revision"])
                if (_git(staging, "rev-parse", "HEAD"),
                        _git(staging, "rev-parse", "HEAD^{tree}")) != (
                        row["revision"], row["tree"]):
                    raise ProductInvariantViolation("Restored Git source differs from canonical revision")
                staging.replace(destination)
            finally:
                if staging.exists():
                    shutil.rmtree(staging)
        return {"repository_identity": identity,
            "repository_ref": row["repository_ref"],
            "revision": row["revision"], "tree": row["tree"],
            "bundle_sha256": row["bundle_sha256"]}
