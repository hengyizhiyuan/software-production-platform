"""Repository observations are evidence; Work admission remains Work-owned."""
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit, urlunsplit
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import insert, select, text, update

from spg.application.runtime import RuntimeService
from spg.application.work import WorkApplicationService
from spg.domain.assets import AssetScopeAdmissionRequest, RepositoryIntakeRequest
from spg.domain.preparation import ContextSemanticRole
from spg.domain.product import EngineeringContextReference, ProductInvariantViolation, ProductRecordNotFound
from spg.domain.runtime import BootstrapRequest
from spg.infrastructure.persistence.asset_schema import repository_intakes
from spg.infrastructure.persistence.product_schema import engineering_resources
from spg.infrastructure.persistence.product_store import ProductStore


def canonical_fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


class RepositoryAssetService:
    _MANAGED_REPOSITORY_EXCLUDES = (
        "__pycache__/",
        "*.py[cod]",
        ".pytest_cache/",
    )

    def __init__(self, database, asset_root: Path, import_root: Path):
        self.database = database
        self.asset_root = asset_root.resolve()
        self.import_root = import_root.resolve()

    @contextmanager
    def _lock(self, identity):
        key = int(sha256(identity.encode()).hexdigest()[:15], 16)
        with self.database.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": key})
            try:
                yield
            finally:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})

    @staticmethod
    def _git(path, *args):
        try:
            return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(path), *args],
                check=True, capture_output=True, timeout=90).stdout.decode("utf-8").strip()
        except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
            raise ProductInvariantViolation("Repository operation failed; inspect the intake receipt and repository availability") from exc

    def _source(self, source):
        if source is None:
            return None
        url = urlsplit(source)
        if url.scheme in {"http", "https"}:
            if not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ProductInvariantViolation("Use a Git HTTPS address without embedded credentials, query or fragment")
            return urlunsplit((url.scheme, url.netloc.lower(), url.path.rstrip("/"), "", ""))
        path = Path(source).resolve()
        if not path.is_relative_to(self.import_root) or not path.is_dir():
            raise ProductInvariantViolation("Local repository imports must be inside the configured import directory")
        return str(path)

    def intake(self, request: RepositoryIntakeRequest):
        source = self._source(request.source)
        identity = source or f"watt://repositories/{request.request_id}"
        payload = request.model_dump(mode="json")
        with self._lock(identity):
            with self.database.unit_of_work() as uow:
                row = uow.session.execute(select(repository_intakes).where(repository_intakes.c.id == request.request_id)).mappings().one_or_none()
                if row is not None:
                    if row["request"] != payload:
                        raise ProductInvariantViolation("Intake request identity already belongs to a different request")
                    if row["observation"] is not None:
                        return row["observation"]
                else:
                    existing = uow.session.execute(select(engineering_resources.c.id).where(engineering_resources.c.repository_identity == identity)).scalar_one_or_none()
                    if existing is not None:
                        return self.observation(existing)
                    uow.session.execute(insert(repository_intakes).values(id=request.request_id, request=payload, created_at=datetime.now(UTC)))
                    uow.commit()
            self.asset_root.mkdir(parents=True, exist_ok=True)
            repository = self.asset_root / str(request.request_id)
            if not repository.exists():
                if source is None:
                    repository.mkdir()
                    self._git(repository, "init", "-b", "main")
                    exclude = repository / ".git" / "info" / "exclude"
                    existing_excludes = exclude.read_text(encoding="utf-8")
                    additions = tuple(
                        pattern
                        for pattern in self._MANAGED_REPOSITORY_EXCLUDES
                        if pattern not in existing_excludes.splitlines()
                    )
                    if additions:
                        exclude.write_text(
                            existing_excludes.rstrip("\n")
                            + "\n"
                            + "\n".join(additions)
                            + "\n",
                            encoding="utf-8",
                        )
                    # Only initialization facts; design is produced later through SPG.
                    (repository / "README.md").write_text("# Work Repository\n\nInitialized for governed Work production.\n", encoding="utf-8")
                    self._git(repository, "add", "--", "README.md")
                    self._git(repository, "-c", "user.name=Watt", "-c", "user.email=watt@localhost", "commit", "-m", "Initialize repository asset")
                else:
                    try:
                        # Repository intake preserves complete history for the
                        # selected default branch without fetching unrelated
                        # remote branches. Production Environment remains the
                        # owner of the eventual execution Workspace.
                        self._git(
                            self.asset_root,
                            "clone",
                            "--no-local",
                            "--single-branch",
                            "--",
                            source,
                            str(repository),
                        )
                    except ProductInvariantViolation:
                        candidate = {
                            "resource_id": None,
                            "repository_identity": source,
                            "repository_ref": None,
                            "revision": None,
                            "tree": None,
                            "paths": [],
                            "context_path": None,
                            "observed_at": datetime.now(UTC).isoformat(),
                            "source": source,
                            "title": request.title,
                            "description": request.description,
                            "intake_request_id": str(request.request_id),
                            "condition": "UNRESOLVED",
                            "authorization": {
                                capability: "UNKNOWN"
                                for capability in (
                                    "READ",
                                    "WRITE",
                                    "CREATE_BRANCH",
                                    "CREATE_PR",
                                    "PUSH",
                                )
                            },
                            "message": (
                                "Repository access was not confirmed. Work may continue "
                                "without this Asset; authorization and integration are "
                                "required before production can use it."
                            ),
                        }
                        candidate["fingerprint"] = canonical_fingerprint(candidate)
                        with self.database.unit_of_work() as uow:
                            uow.session.execute(
                                update(repository_intakes)
                                .where(repository_intakes.c.id == request.request_id)
                                .values(observation=candidate)
                            )
                            uow.commit()
                        return candidate
            # A previous interrupted intake may leave a valid repository: observe, never overwrite.
            ref = self._git(repository, "symbolic-ref", "HEAD")
            revision = self._git(repository, "rev-parse", "HEAD")
            tree = self._git(repository, "rev-parse", "HEAD^{tree}")
            paths = self._git(repository, "ls-tree", "-r", "--name-only", revision).splitlines()
            context = next((name for name in paths if name.lower() == "readme.md"), None)
            if context is None:
                context = next((name for name in paths if name.endswith(".md")), None)
            if context is None:
                raise ProductInvariantViolation("This repository adapter requires an existing Markdown context document")
            runtime = RuntimeService(self.database)
            with self.database.unit_of_work() as uow:
                from spg.infrastructure.persistence.runtime_store import RuntimeStore
                pointer = RuntimeStore(uow.session).current_pointer(repository_identity=identity, repository_ref=ref)
            if pointer is None:
                runtime.bootstrap_trusted_baseline(BootstrapRequest(repository_path=repository, repository_identity=identity,
                    repository_ref=ref, authority_identity=request.authority_identity,
                    scope={"intake_request_id": str(request.request_id), "purpose": "Repository Asset baseline observation"}))
            with self.database.unit_of_work() as uow:
                resource_id = uow.session.execute(select(engineering_resources.c.id).where(engineering_resources.c.repository_identity == identity)).scalar_one_or_none()
            if resource_id is None:
                resource = WorkApplicationService(self.database).register_engineering_resource(
                    repository_identity=identity, location_ref=str(repository), authoritative_ref=ref,
                    context_references=(EngineeringContextReference(semantic_role=ContextSemanticRole.PROJECT_CONTEXT, repository_relative_path=context),), is_default=False)
                resource_id = resource.id
            observation = {"resource_id": str(resource_id), "repository_identity": identity, "repository_ref": ref,
                "revision": revision, "tree": tree, "paths": paths[:200], "context_path": context,
                "observed_at": datetime.now(UTC).isoformat(), "source": source, "title": request.title,
                "description": request.description, "intake_request_id": str(request.request_id)}
            observation["fingerprint"] = canonical_fingerprint(observation)
            with self.database.unit_of_work() as uow:
                uow.session.execute(update(repository_intakes).where(repository_intakes.c.id == request.request_id).values(resource_id=resource_id, observation=observation))
                uow.commit()
            return observation

    def ensure_managed_execution_workspace(
        self,
        work_service: WorkApplicationService,
        work_id: UUID,
    ):
        """Allocate one local Git-backed execution workspace within admitted Work authority."""
        with self.database.unit_of_work() as uow:
            selected = ProductStore(uow.session).resource_for_work(work_id)
        if selected is not None:
            return work_service.get_work(work_id)

        request_id = uuid5(
            NAMESPACE_URL,
            f"watt:managed-execution-workspace:{work_id}",
        )
        authority = "system:watt-managed-execution-workspace"
        observation = self.intake(
            RepositoryIntakeRequest(
                request_id=request_id,
                title="Watt-managed execution workspace",
                description=(
                    "Local execution substrate allocated only when this admitted Work "
                    "reaches production readiness."
                ),
                authority_identity=authority,
            )
        )
        projection = work_service.get_work(work_id)
        with self.database.unit_of_work() as uow:
            selected = ProductStore(uow.session).resource_for_work(work_id)
        if selected is not None:
            return projection
        if observation.get("resource_id") is None:
            raise ProductInvariantViolation(
                "Watt-managed execution workspace could not be observed"
            )
        return work_service.admit_asset_scope(
            work_id,
            AssetScopeAdmissionRequest(
                resource_id=UUID(observation["resource_id"]),
                expected_work_revision_id=projection.current_work_reality_revision_id,
                observation_fingerprint=observation["fingerprint"],
                authority_identity=authority,
                rationale=(
                    "Allocate Watt-owned local execution substrate within the already "
                    "admitted Work authority; no external repository authority is implied."
                ),
            ),
            observation,
            managed_execution_workspace=True,
        )

    def observation(self, resource_id: UUID):
        with self.database.unit_of_work() as uow:
            row = uow.session.execute(select(repository_intakes.c.observation).where(repository_intakes.c.resource_id == resource_id)).scalar_one_or_none()
            if row is None:
                raise ProductRecordNotFound("Repository has no product intake observation")
            return row

    def list_assets(self, work_id=None):
        with self.database.unit_of_work() as uow:
            observations = uow.session.execute(select(repository_intakes.c.observation).where(repository_intakes.c.observation.is_not(None))).scalars().all()
            product = ProductStore(uow.session)
            scope = None if work_id is None else product.scope_for_work(work_id)
            bound = set() if scope is None else {str(item.resource_id) for item in scope.bindings}
            selected = None if work_id is None else product.resource_for_work(work_id)
            return [{**row, "bound": row["resource_id"] is not None and row["resource_id"] in bound,
                "selected_for_production": selected is not None and str(selected.id) == row["resource_id"]} for row in observations]
