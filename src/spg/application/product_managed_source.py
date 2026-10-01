"""Product-owned Managed Source and accepted baseline continuity."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import subprocess
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update

from spg.config import Settings
from spg.domain.preparation import ContextSemanticRole
from spg.domain.product import EngineeringContextReference, ProductInvariantViolation
from spg.domain.runtime import BootstrapRequest
from spg.infrastructure.managed_source_provider import GiteaManagedSourceProvider, ManagedSourceError
from spg.infrastructure.persistence.product_schema import (
    engineering_resources, product_managed_sources, product_source_versions,
    software_product_assets, software_products, work_source_bases,
    work_runtime_bindings,
)
from spg.infrastructure.persistence.runtime_schema import runtime_commits


def _git(path: Path, *args: str) -> str:
    result = subprocess.run(["git", "--no-replace-objects", "-C", str(path), *args],
        capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise ProductInvariantViolation("Exact managed source revision is unavailable")
    return result.stdout.strip()


class ProductManagedSourceService:
    def __init__(self, database, settings: Settings | None = None):
        self.database = database
        self.settings = settings or Settings()
        self.provider = GiteaManagedSourceProvider(self.settings)
        self.root = self.settings.managed_source_workspace_root.resolve()

    @staticmethod
    def _verify_checkout(checkout: Path, revision: str, tree: str) -> None:
        if (_git(checkout, "rev-parse", "HEAD"), _git(checkout, "rev-parse", "HEAD^{tree}")) != (revision, tree):
            raise ProductInvariantViolation("Managed source checkout differs from its exact bound revision")

    def _source(self, session, product_id: UUID, *, lock: bool = False):
        statement = select(product_managed_sources).where(
            product_managed_sources.c.product_id == product_id)
        if lock:
            statement = statement.with_for_update()
        return session.execute(statement).mappings().one_or_none()

    def _attach(self, product_id: UUID, owner_id: str, revision, *, origin: dict,
                provider_reference: str, checkout: Path) -> dict:
        from spg.application.runtime import RuntimeService
        from spg.application.work import WorkApplicationService
        identity = f"watt://repositories/products/{product_id}"
        paths = _git(checkout, "ls-tree", "-r", "--name-only", revision.revision).splitlines()
        context = next((path for path in paths if Path(path).name.lower().startswith("readme")),
                       next((path for path in paths if path.endswith(".md")), paths[0] if paths else None))
        if context is None:
            raise ProductInvariantViolation("Managed source requires at least one tracked file")
        self._verify_checkout(checkout, revision.revision, revision.tree)
        with self.database.unit_of_work() as uow:
            if self._source(uow.session, product_id) is not None:
                return self.describe(product_id, owner_id)
            product = uow.session.execute(select(software_products).where(
                software_products.c.id == product_id,
                software_products.c.owner_id == owner_id)).mappings().one_or_none()
            if product is None:
                raise ProductInvariantViolation("Product is unavailable to source owner")
        with self.database.unit_of_work() as uow:
            resource_id = uow.session.execute(select(engineering_resources.c.id).where(
                engineering_resources.c.repository_identity == identity)).scalar_one_or_none()
        if resource_id is None:
            resource_id = WorkApplicationService(self.database).register_engineering_resource(
                repository_identity=identity, location_ref=str(checkout),
                authoritative_ref="refs/heads/accepted",
                context_references=(EngineeringContextReference(
                    semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                    repository_relative_path=context),), is_default=False).id
        runtime = RuntimeService(self.database)
        from spg.infrastructure.persistence.runtime_store import RuntimeStore
        with self.database.unit_of_work() as uow:
            pointer = RuntimeStore(uow.session).current_pointer(
                repository_identity=identity, repository_ref="refs/heads/accepted")
        if pointer is None:
            runtime.bootstrap_trusted_baseline(BootstrapRequest(
                repository_path=checkout, repository_identity=identity,
                repository_ref="refs/heads/accepted", authority_identity=owner_id,
                scope={"product_id": str(product_id), "purpose": "managed-source-initial-baseline"}))
        elif runtime.current_baseline(repository_identity=identity,
                repository_ref="refs/heads/accepted").repository_revision != revision.revision:
            raise ProductInvariantViolation("Product source bootstrap differs from provider revision")
        now = datetime.now(UTC)
        with self.database.unit_of_work() as uow:
            uow.session.execute(insert(product_managed_sources).values(
                product_id=product_id, repository_identity=identity,
                provider_kind=self.provider.kind, provider_reference=provider_reference,
                accepted_ref="refs/heads/accepted", accepted_revision=revision.revision,
                accepted_tree=revision.tree, origin=origin, version=0, updated_at=now))
            uow.session.execute(insert(product_source_versions).values(
                id=uuid4(), product_id=product_id, version=0,
                revision=revision.revision, tree=revision.tree,
                authority_identity=owner_id, created_at=now))
            uow.session.execute(insert(software_product_assets).values(
                id=uuid4(), product_id=product_id, asset_kind="REPOSITORY",
                reference=identity, resource_id=resource_id,
                metadata={"source": "WATT_MANAGED", "origin": origin}, created_at=now))
            uow.commit()
        return self.describe(product_id, owner_id)

    def provision(self, product_id: UUID, owner_id: str, name: str) -> dict:
        reference = "product-" + product_id.hex
        initial = f"# {name}\n\nManaged by Watt.\n"
        revision = self.provider.provision(reference, initial)
        checkout = self.root / "products" / str(product_id) / "accepted"
        if not checkout.exists():
            self.provider.materialize(reference, revision.revision, checkout, "accepted")
        self._verify_checkout(checkout, revision.revision, revision.tree)
        return self._attach(product_id, owner_id, revision, origin={},
                            provider_reference=reference, checkout=checkout)

    def import_existing(self, product_id: UUID, owner_id: str, origin_identity: str,
                        origin_path: Path, expected_revision: str, expected_tree: str) -> dict:
        if not origin_path.is_dir():
            raise ManagedSourceError("EXTERNAL_ORIGIN_UNAVAILABLE", "Import origin is unavailable")
        if (_git(origin_path, "rev-parse", "HEAD"),
                _git(origin_path, "rev-parse", "HEAD^{tree}")) != (expected_revision, expected_tree):
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH", "Observed import origin changed before capture")
        reference = "product-" + product_id.hex
        revision = self.provider.import_repository(reference, origin_path)
        if (revision.revision, revision.tree) != (expected_revision, expected_tree):
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH", "Imported source differs from observed origin")
        checkout = self.root / "products" / str(product_id) / "accepted"
        if not checkout.exists():
            self.provider.materialize(reference, revision.revision, checkout, "accepted")
        self._verify_checkout(checkout, revision.revision, revision.tree)
        return self._attach(product_id, owner_id, revision,
            origin={"repository_identity": origin_identity, "revision": expected_revision,
                    "tree": expected_tree},
            provider_reference=reference, checkout=checkout)

    def prepare_work(self, work_id: UUID, product_id: UUID) -> dict | None:
        with self.database.unit_of_work() as uow:
            source = self._source(uow.session, product_id, lock=True)
            if source is None:
                return None
            existing = uow.session.execute(select(work_source_bases).where(
                work_source_bases.c.work_id == work_id)).mappings().one_or_none()
            if existing is not None:
                return dict(existing)
            source = dict(source)
        branch = "work-" + work_id.hex
        work_ref = "refs/heads/" + branch
        checkout = self.root / "works" / str(work_id)
        if checkout.exists():
            self._verify_checkout(checkout, source["accepted_revision"], source["accepted_tree"])
            from spg.infrastructure.managed_source_provider import SourceRevision
            observed = SourceRevision(source["accepted_revision"], source["accepted_tree"])
        else:
            observed = self.provider.materialize(source["provider_reference"],
                source["accepted_revision"], checkout, branch)
        if observed.tree != source["accepted_tree"]:
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH", "Work source tree differs from Product accepted baseline")
        self.provider.create_work_lineage(source["provider_reference"], checkout,
            observed.revision, work_ref)
        from spg.application.work import WorkApplicationService
        from spg.application.runtime import RuntimeService
        from spg.application.managed_git_source import ManagedGitSource
        paths = _git(checkout, "ls-tree", "-r", "--name-only", observed.revision).splitlines()
        context = next((path for path in paths if Path(path).name.lower().startswith("readme")),
                       next((path for path in paths if path.endswith(".md")), paths[0]))
        identity = f"watt://work-branches/{work_id}"
        with self.database.unit_of_work() as uow:
            resource_id = uow.session.execute(select(engineering_resources.c.id).where(
                engineering_resources.c.repository_identity == identity)).scalar_one_or_none()
        if resource_id is None:
            resource_id = WorkApplicationService(self.database).register_engineering_resource(
                repository_identity=identity, location_ref=str(checkout),
                authoritative_ref=work_ref,
                context_references=(EngineeringContextReference(
                    semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                    repository_relative_path=context),), is_default=False).id
        runtime = RuntimeService(self.database)
        from spg.infrastructure.persistence.runtime_store import RuntimeStore
        with self.database.unit_of_work() as uow:
            pointer = RuntimeStore(uow.session).current_pointer(
                repository_identity=identity, repository_ref=work_ref)
        if pointer is None:
            runtime.bootstrap_trusted_baseline(BootstrapRequest(
                repository_path=checkout, repository_identity=identity,
                repository_ref=work_ref, authority_identity="system:watt-managed-source",
                scope={"work_id": str(work_id), "product_id": str(product_id),
                       "product_source_version": source["version"]}))
        elif runtime.current_baseline(repository_identity=identity,
                repository_ref=work_ref).repository_revision != observed.revision:
            raise ProductInvariantViolation("Work source bootstrap differs from Product accepted revision")
        ManagedGitSource(self.database).sync(identity, checkout, internal_branch=True)
        values = dict(work_id=work_id, product_id=product_id, resource_id=resource_id,
            source_version=source["version"], source_revision=observed.revision,
            source_tree=observed.tree, work_ref=work_ref, created_at=datetime.now(UTC))
        with self.database.unit_of_work() as uow:
            current = self._source(uow.session, product_id, lock=True)
            if current["version"] != source["version"]:
                raise ProductInvariantViolation("Product accepted source changed during Work preparation")
            uow.session.execute(insert(work_source_bases).values(**values))
            uow.commit()
        return values

    def persist_candidate(self, session, run_id: UUID,
                          repository_identity: str, revision: str, tree: str,
                          repository: Path) -> None:
        row = session.execute(select(work_source_bases, product_managed_sources.c.provider_reference)
            .join(work_runtime_bindings, work_runtime_bindings.c.work_id == work_source_bases.c.work_id)
            .join(product_managed_sources, product_managed_sources.c.product_id == work_source_bases.c.product_id)
            .where(work_runtime_bindings.c.production_run_id == run_id)).mappings().one_or_none()
        if row is None:
            return
        resource = session.execute(select(engineering_resources.c.repository_identity).where(
            engineering_resources.c.id == row["resource_id"])).scalar_one()
        if resource != repository_identity:
            raise ProductInvariantViolation("Candidate source identity differs from Work source basis")
        observed = self.provider.persist_candidate(row["provider_reference"], repository,
            revision, row["work_ref"])
        if observed.tree != tree:
            raise ProductInvariantViolation("Candidate tree differs from persisted provider source")

    def promote_acceptance(self, session, work_id: UUID, commit, acceptance) -> None:
        basis = session.execute(select(work_source_bases).where(
            work_source_bases.c.work_id == work_id)).mappings().one_or_none()
        if basis is None:
            return
        source = self._source(session, basis["product_id"], lock=True)
        if (source["version"] != basis["source_version"]
                or source["accepted_revision"] != basis["source_revision"]):
            raise ProductInvariantViolation("Product accepted source advanced since this Work began")
        if commit.repository_identity != session.execute(select(engineering_resources.c.repository_identity).where(
                engineering_resources.c.id == basis["resource_id"])).scalar_one():
            raise ProductInvariantViolation("Accepted Candidate does not belong to Work source")
        observed = self.provider.promote(source["provider_reference"],
            commit.repository_revision, source["accepted_revision"])
        if observed.tree != commit.repository_tree_identity:
            raise ProductInvariantViolation("Accepted Candidate source tree differs from provider")
        now = datetime.now(UTC)
        version = source["version"] + 1
        session.execute(insert(product_source_versions).values(
            id=uuid4(), product_id=basis["product_id"], version=version,
            revision=observed.revision, tree=observed.tree, work_id=work_id,
            candidate_id=commit.candidate_id, acceptance_id=acceptance.id,
            authority_identity=acceptance.authority_identity, created_at=now))
        session.execute(update(product_managed_sources).where(
            product_managed_sources.c.product_id == basis["product_id"],
            product_managed_sources.c.version == source["version"])
            .values(accepted_revision=observed.revision, accepted_tree=observed.tree,
                    version=version, updated_at=now))

    def describe(self, product_id: UUID, owner_id: str) -> dict:
        with self.database.unit_of_work() as uow:
            product = uow.session.execute(select(software_products.c.id).where(
                software_products.c.id == product_id,
                software_products.c.owner_id == owner_id)).scalar_one_or_none()
            if product is None:
                raise ProductInvariantViolation("Product source is unavailable to this owner")
            source = self._source(uow.session, product_id)
            if source is None:
                raise ProductInvariantViolation("Product has no managed source")
            versions = uow.session.execute(select(product_source_versions).where(
                product_source_versions.c.product_id == product_id)
                .order_by(product_source_versions.c.version)).mappings().all()
            candidates = uow.session.execute(select(runtime_commits.c.candidate_id,
                runtime_commits.c.repository_revision, runtime_commits.c.repository_tree_identity,
                work_source_bases.c.work_id, work_source_bases.c.source_version).join(work_runtime_bindings,
                    work_runtime_bindings.c.production_run_id == runtime_commits.c.production_run_id)
                .join(work_source_bases, work_source_bases.c.work_id == work_runtime_bindings.c.work_id)
                .where(work_source_bases.c.product_id == product_id)
                .order_by(runtime_commits.c.committed_at)).mappings().all()
        candidate_rows = [{"work_id": str(row["work_id"]),
                           "candidate_id": str(row["candidate_id"]),
                           "revision": row["repository_revision"],
                           "tree": row["repository_tree_identity"],
                           "source_version": row["source_version"]} for row in candidates]
        current_candidates = [item for item in candidate_rows
                              if item["source_version"] == source["version"]
                              and item["revision"] != source["accepted_revision"]]
        return {"repository_identity": source["repository_identity"],
                "provider_kind": source["provider_kind"],
                "accepted": {"version": source["version"],
                             "revision": source["accepted_revision"], "tree": source["accepted_tree"]},
                "origin": source["origin"],
                "versions": [{"version": row["version"], "revision": row["revision"],
                              "tree": row["tree"], "work_id": str(row["work_id"]) if row["work_id"] else None,
                              "candidate_id": str(row["candidate_id"]) if row["candidate_id"] else None,
                              "acceptance_id": str(row["acceptance_id"]) if row["acceptance_id"] else None}
                             for row in versions],
                "candidates": candidate_rows,
                "current_candidate": current_candidates[-1] if current_candidates else None,
                "access": self.provider.clone_access(source["provider_reference"])}

    def inspect_files(self, product_id: UUID, owner_id: str, revision: str | None = None) -> dict:
        details = self.describe(product_id, owner_id)
        selected = revision or details["accepted"]["revision"]
        allowed = {item["revision"] for item in details["versions"] + details["candidates"]}
        if selected not in allowed:
            raise ProductInvariantViolation("Source revision is not part of this Product lineage")
        with self.database.unit_of_work() as uow:
            source = self._source(uow.session, product_id)
        from tempfile import TemporaryDirectory
        with TemporaryDirectory(prefix="watt-code-assets-") as temporary:
            repo = Path(temporary) / "source"
            observed = self.provider.materialize(source["provider_reference"], selected, repo, "inspection")
            paths = _git(repo, "ls-tree", "-r", "--name-only", selected).splitlines()
            if len(paths) > 2000:
                raise ProductInvariantViolation("Source tree exceeds the bounded inspection limit")
            parent = _git(repo, "rev-list", "--parents", "-n", "1", selected).split()
            changed = [] if len(parent) < 2 else _git(repo, "diff", "--name-only", parent[1], selected).splitlines()
            diff = "" if len(parent) < 2 else _git(repo, "diff", "--no-ext-diff", "--unified=3", parent[1], selected)
            if len(diff.encode()) > 1024 * 1024:
                diff = "Diff exceeds the 1 MiB inspection limit."
            return {"revision": selected, "tree": observed.tree, "files": paths,
                    "changed_files": changed[:200], "diff": diff}

    def inspect_file(self, product_id: UUID, owner_id: str, path: str,
                     revision: str | None = None) -> dict:
        """Read one exact, bounded text blob from an admitted Product version."""
        listing = self.inspect_files(product_id, owner_id, revision)
        if path not in listing["files"]:
            raise ProductInvariantViolation("File is outside this Product source version")
        with self.database.unit_of_work() as uow:
            source = self._source(uow.session, product_id)
        from tempfile import TemporaryDirectory
        with TemporaryDirectory(prefix="watt-code-file-") as temporary:
            repo = Path(temporary) / "source"
            self.provider.materialize(source["provider_reference"], listing["revision"],
                                      repo, "inspection")
            blob = subprocess.run(["git", "-C", str(repo), "show",
                f"{listing['revision']}:{path}"], capture_output=True, timeout=30)
            if blob.returncode or len(blob.stdout) > 256 * 1024 or b"\x00" in blob.stdout:
                raise ProductInvariantViolation("File is not safely displayable as text")
            try:
                content = blob.stdout.decode("utf-8")
            except UnicodeDecodeError as error:
                raise ProductInvariantViolation(
                    "File is not safely displayable as text") from error
            return {"revision": listing["revision"], "path": path,
                    "content": content}

    def export_archive(self, product_id: UUID, owner_id: str, revision: str | None = None) -> tuple[bytes, str]:
        details = self.describe(product_id, owner_id)
        selected = revision or details["accepted"]["revision"]
        allowed = {item["revision"] for item in details["versions"] + details["candidates"]}
        if selected not in allowed:
            raise ProductInvariantViolation("Source revision is not part of this Product lineage")
        with self.database.unit_of_work() as uow:
            source = self._source(uow.session, product_id)
        from tempfile import TemporaryDirectory
        with TemporaryDirectory(prefix="watt-source-export-") as temporary:
            repo = Path(temporary) / "source"
            self.provider.materialize(source["provider_reference"], selected, repo, "export")
            archive = subprocess.run(["git", "-C", str(repo), "archive", "--format=zip", selected],
                capture_output=True, timeout=120)
            if archive.returncode or len(archive.stdout) > 128 * 1024 * 1024:
                raise ProductInvariantViolation("Exact source export is unavailable or exceeds the limit")
            return archive.stdout, selected
