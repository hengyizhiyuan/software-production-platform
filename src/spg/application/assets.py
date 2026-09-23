"""Repository observations are evidence; Work admission remains Work-owned."""
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlsplit, urlunsplit
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import insert, select, text, update

from spg.application.runtime import RuntimeService
from spg.application.connectors import ConnectorResolver
from spg.application.native_git_operations import NativeGitOperationRunner
from spg.application.work import WorkApplicationService
from spg.domain.assets import (
    AssetScopeAdmissionRequest,
    RepositoryAcquisitionFailure,
    RepositoryAcquisitionFailureCategory,
    RepositoryIntakeRequest,
)
from spg.domain.connectors import CapabilityRequirement
from spg.domain.engineering_semantics import SemanticFactAuthority, current_semantic_facts
from spg.domain.preparation import ContextSemanticRole
from spg.domain.product import EngineeringContextReference, ProductInvariantViolation, ProductRecordNotFound
from spg.domain.response_contract import production_intent_evidence
from spg.domain.runtime import BootstrapRequest
from spg.infrastructure.persistence.asset_schema import repository_intakes
from spg.infrastructure.persistence.product_schema import engineering_resources
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.production_environment import GitRepositoryAcquirer


def canonical_fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


class RepositoryAssetService:
    _MANAGED_REPOSITORY_EXCLUDES = (
        "__pycache__/",
        "*.py[cod]",
        ".pytest_cache/",
    )

    def __init__(
        self,
        database,
        asset_root: Path,
        import_root: Path,
        repository_acquirer: GitRepositoryAcquirer | None = None,
        native_git_operations: NativeGitOperationRunner | None = None,
    ):
        self.database = database
        self.asset_root = asset_root.resolve()
        self.import_root = import_root.resolve()
        self.repository_acquirer = repository_acquirer or GitRepositoryAcquirer()
        self.native_git_operations = native_git_operations

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

    @staticmethod
    def _identity(source: str | None, request: RepositoryIntakeRequest) -> str:
        if request.operation_kind == "CREATE_BRANCH":
            branch_digest = sha256(
                f"{source}:{request.target_branch}".encode("utf-8")
            ).hexdigest()[:20]
            return f"watt://work-branches/{request.work_id}/{branch_digest}"
        return source or f"watt://repositories/{request.request_id}"

    @staticmethod
    def _attempt_metadata(request: RepositoryIntakeRequest) -> dict[str, object]:
        return {
            "interaction_id": (
                None if request.interaction_id is None else str(request.interaction_id)
            ),
            "work_id": None if request.work_id is None else str(request.work_id),
            "attempt_number": request.attempt_number,
            "previous_attempt_id": (
                None
                if request.previous_attempt_id is None
                else str(request.previous_attempt_id)
            ),
            "operation_kind": request.operation_kind,
            "target_branch": request.target_branch,
            "base_resource_id": (
                None if request.base_resource_id is None
                else str(request.base_resource_id)
            ),
        }

    def start_intake(self, request: RepositoryIntakeRequest) -> dict:
        """Persist an acquisition operation before any Git effect is attempted."""

        if request.operation_kind == "CREATE_BRANCH":
            self._require_current_branch_authority(request)
        source = self._source(request.source)
        identity = self._identity(source, request)
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
                    uow.session.execute(
                        insert(repository_intakes).values(
                            id=request.request_id,
                            request=payload,
                            created_at=datetime.now(UTC),
                        )
                    )
                requested = {
                    "resource_id": None,
                    "repository_identity": identity,
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
                    "condition": "REQUESTED",
                    "failure_category": None,
                    "human_message": (
                        f"Local branch {request.target_branch} creation has been requested."
                        if request.operation_kind == "CREATE_BRANCH"
                        else "Repository acquisition has been requested."
                    ),
                    "technical_evidence": None,
                    **self._attempt_metadata(request),
                }
                requested["fingerprint"] = canonical_fingerprint(requested)
                uow.session.execute(
                    update(repository_intakes)
                    .where(repository_intakes.c.id == request.request_id)
                    .values(observation=requested)
                )
                uow.commit()
                return requested

    def _require_current_branch_authority(self, request: RepositoryIntakeRequest) -> None:
        """A branch request must be backed by current, admitted Human Work truth."""

        if request.work_id is None or request.base_resource_id is None:
            raise ProductInvariantViolation("Branch creation requires a bound Work repository")
        with self.database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            revision = product.current_work_reality_revision(request.work_id)
            base = product.resource_for_work(request.work_id)
        if revision is None or base is None or base.id != request.base_resource_id:
            raise ProductInvariantViolation("Branch creation requires the current Work repository")
        if revision.admitted_by != request.authority_identity:
            raise ProductInvariantViolation("Branch creation authority differs from current Work Reality")
        facts = current_semantic_facts(revision.engineering_semantic_facts)
        target = any(
            fact.subject == "repository.branch_name"
            and fact.value == request.target_branch
            and fact.qualifiers.get("state") == "to_be_created"
            and fact.authority is SemanticFactAuthority.HUMAN_EXPLICIT
            for fact in facts
        )
        action = any(
            fact.subject == "repository.branch_action"
            and fact.value == "创建新分支"
            and fact.authority is SemanticFactAuthority.HUMAN_EXPLICIT
            for fact in facts
        )
        if not target or not action:
            raise ProductInvariantViolation("Branch creation requires the current Human-admitted branch action")

    def intake(self, request: RepositoryIntakeRequest):
        observation = self.start_intake(request)
        if observation.get("condition") not in {"REQUESTED", "RUNNING"}:
            return observation
        return self.execute_intake(request.request_id)

    def record_waiting_source(self, request: RepositoryIntakeRequest) -> dict:
        observation = self.start_intake(request)
        waiting = {
            **observation,
            "condition": "WAITING_FOR_REPOSITORY_SOURCE",
            "human_message": "A repository source is required before acquisition can start.",
            "message": "A repository source is required before acquisition can start.",
        }
        waiting["fingerprint"] = canonical_fingerprint(
            {key: value for key, value in waiting.items() if key != "fingerprint"}
        )
        with self.database.unit_of_work() as uow:
            uow.session.execute(
                update(repository_intakes)
                .where(repository_intakes.c.id == request.request_id)
                .values(observation=waiting)
            )
            uow.commit()
        return waiting

    def execute_intake(self, request_id: UUID) -> dict:
        """Execute exactly one persisted acquisition Attempt."""

        try:
            return self._execute_intake(request_id)
        except ProductRecordNotFound:
            raise
        except Exception as error:
            # Once an Attempt exists, an unexpected adapter, observation, or
            # persistence failure must not leave durable Reality at RUNNING.
            # Preserve the technical cause while exposing only a safe message.
            return self.mark_attempt_failure(
                request_id,
                category=(
                    RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE
                ),
                human_message=(
                    "Repository acquisition could not be completed and can be retried."
                ),
                technical_evidence={
                    "phase": "REPOSITORY_ACQUISITION",
                    "error_type": type(error).__name__,
                    "message": str(error)[:2000],
                },
                retryable=True,
            )

    def _execute_intake(self, request_id: UUID) -> dict:
        """Internal effectful phase; ``execute_intake`` owns terminalization."""

        with self.database.unit_of_work() as uow:
            row = uow.session.execute(
                select(repository_intakes).where(repository_intakes.c.id == request_id)
            ).mappings().one_or_none()
        if row is None:
            raise ProductRecordNotFound("Repository acquisition Attempt does not exist")
        request = RepositoryIntakeRequest.model_validate(row["request"])
        if request.operation_kind == "CREATE_BRANCH":
            self._require_current_branch_authority(request)
        observation = row["observation"]
        if observation is None:
            observation = self.start_intake(request)
        if observation.get("condition") not in {"REQUESTED", "RUNNING"}:
            return observation

        source = self._source(request.source)
        identity = self._identity(source, request)
        with self._lock(identity):
            with self.database.unit_of_work() as uow:
                current = uow.session.execute(
                    select(repository_intakes.c.observation).where(
                        repository_intakes.c.id == request.request_id
                    )
                ).scalar_one()
                if current is not None and current.get("condition") not in {
                    "REQUESTED",
                    "RUNNING",
                }:
                    return current
                if current is not None and current.get("condition") == "REQUESTED":
                    current = {
                        **current,
                        "condition": "RUNNING",
                        "human_message": (
                            f"Creating local branch {request.target_branch}."
                            if request.operation_kind == "CREATE_BRANCH"
                            else "Repository acquisition is running."
                        ),
                        "observed_at": datetime.now(UTC).isoformat(),
                    }
                    current["fingerprint"] = canonical_fingerprint(
                        {
                            key: value
                            for key, value in current.items()
                            if key != "fingerprint"
                        }
                    )
                    uow.session.execute(
                        update(repository_intakes)
                        .where(repository_intakes.c.id == request_id)
                        .values(observation=current)
                    )
                    uow.commit()
                existing = uow.session.execute(
                    select(engineering_resources.c.id).where(
                        engineering_resources.c.repository_identity == identity
                    )
                ).scalar_one_or_none()
            if existing is not None:
                observed = {
                    **self.observation(existing),
                    "condition": "READY",
                    "failure_category": None,
                    "human_message": "Repository is ready.",
                    "technical_evidence": None,
                    "intake_request_id": str(request.request_id),
                    **self._attempt_metadata(request),
                }
                observed["fingerprint"] = canonical_fingerprint(
                    {key: value for key, value in observed.items() if key != "fingerprint"}
                )
                with self.database.unit_of_work() as uow:
                    uow.session.execute(
                        update(repository_intakes)
                        .where(repository_intakes.c.id == request.request_id)
                        .values(observation=observed)
                    )
                    uow.commit()
                return observed
            self.asset_root.mkdir(parents=True, exist_ok=True)
            repository = self.asset_root / str(request.request_id)
            connector_capability = None
            native_result = None
            if not repository.exists():
                if request.operation_kind == "CREATE_BRANCH":
                    requirement = CapabilityRequirement(
                        capability_id="git.branch.create",
                        work_id=request.work_id,
                        user_id=request.authority_identity,
                        operation_ref=f"repository-intake:{request.request_id}",
                        resume_point={
                            "intake_request_id": str(request.request_id),
                            "target_branch": request.target_branch,
                        },
                    )
                    resolution = ConnectorResolver(self.database).resolve(requirement)
                    if not resolution.executable:
                        return self.mark_attempt_failure(
                            request.request_id,
                            category=RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE,
                            human_message="The Git branch capability is unavailable; this Work is resumable after a connector is bound.",
                            technical_evidence={
                                "capability_id": requirement.capability_id,
                                "gap_id": str(resolution.gap_id),
                                "operation_ref": requirement.operation_ref,
                            },
                            retryable=True,
                        )
                    connector_capability = resolution.capability
                    with self.database.unit_of_work() as uow:
                        base = ProductStore(uow.session).resource(
                            request.base_resource_id
                        )
                    if base is None:
                        raise ProductInvariantViolation(
                            "Bound repository baseline is missing"
                        )
                    if self.native_git_operations is None:
                        return self.mark_attempt_failure(
                            request.request_id,
                            category=RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE,
                            human_message="Native Git execution is unavailable; this branch Work remains resumable.",
                            technical_evidence={"phase": "NATIVE_GIT_EXECUTOR_UNCONFIGURED"},
                            retryable=True,
                        )
                    native_result = self.native_git_operations.create_branch(
                        work_id=request.work_id,
                        intake_id=request.request_id,
                        source_repository=Path(base.location_ref),
                        source_identity=base.repository_identity,
                        source_ref=base.authoritative_ref,
                        source_url=source,
                        target_branch=request.target_branch,
                        authority_identity=request.authority_identity,
                    )
                    if native_result["condition"] == "RUNNING":
                        with self.database.unit_of_work() as uow:
                            current = uow.session.execute(
                                select(repository_intakes.c.observation).where(
                                    repository_intakes.c.id == request.request_id
                                )
                            ).scalar_one()
                            running = {
                                **current,
                                "condition": "RUNNING",
                                "human_message": "Native Git branch execution is in progress.",
                                "technical_evidence": {
                                    "native_attempt_id": native_result.get("native_attempt_id"),
                                    "checkpoint_id": native_result.get("checkpoint_id"),
                                },
                                "observed_at": datetime.now(UTC).isoformat(),
                            }
                            running["fingerprint"] = canonical_fingerprint({
                                key: value for key, value in running.items() if key != "fingerprint"
                            })
                            uow.session.execute(
                                update(repository_intakes)
                                .where(repository_intakes.c.id == request.request_id)
                                .values(observation=running)
                            )
                            uow.commit()
                        return running
                    if native_result["condition"] != "READY":
                        return self.mark_attempt_failure(
                            request.request_id,
                            category=RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE,
                            human_message="Native Git branch execution has not established the requested branch; retry remains available.",
                            technical_evidence={
                                "phase": "NATIVE_GIT_EXECUTION",
                                "native_attempt_id": native_result.get("native_attempt_id"),
                                "checkpoint_id": native_result.get("checkpoint_id"),
                                "terminal_outcome": native_result.get("terminal_outcome"),
                                "progress_summary": native_result.get("progress_summary"),
                                "tool_result_conditions": native_result.get("tool_result_conditions"),
                            },
                            retryable=True,
                        )
                    self.repository_acquirer.acquire(
                        self.asset_root,
                        str(native_result["workspace_path"]),
                        repository,
                    )
                    self._git(repository, "remote", "set-url", "origin", source)
                    if (
                        self._git(repository, "branch", "--show-current") != request.target_branch
                        or self._git(repository, "rev-parse", "HEAD") != native_result["revision"]
                    ):
                        raise ProductInvariantViolation("Native Git result changed during repository asset materialization")
                elif source is None:
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
                    if request.work_id is not None:
                        requirement = CapabilityRequirement(
                            capability_id="git.repository.acquire",
                            work_id=request.work_id,
                            user_id=request.authority_identity,
                            operation_ref=f"repository-intake:{request.request_id}",
                            resume_point={
                                "intake_request_id": str(request.request_id),
                                "source": source,
                            },
                        )
                        resolution = ConnectorResolver(self.database).resolve(requirement)
                        if not resolution.executable:
                            return self.mark_attempt_failure(
                                request.request_id,
                                category=RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE,
                                human_message="Repository acquisition capability is unavailable; this Work can resume when a connector is bound.",
                                technical_evidence={
                                    "capability_id": requirement.capability_id,
                                    "gap_id": str(resolution.gap_id),
                                    "operation_ref": requirement.operation_ref,
                                },
                                retryable=True,
                            )
                        connector_capability = resolution.capability
                    try:
                        # Repository intake preserves complete history for the
                        # selected default branch without fetching unrelated
                        # remote branches. Production Environment remains the
                        # owner of the eventual execution Workspace.
                        self.repository_acquirer.acquire(
                            self.asset_root,
                            source,
                            repository,
                        )
                    except RepositoryAcquisitionFailure as failure:
                        if repository.exists() and repository.parent == self.asset_root:
                            shutil.rmtree(repository, ignore_errors=True)
                        condition = (
                            "WAITING_FOR_AUTHORIZATION"
                            if failure.category
                            is RepositoryAcquisitionFailureCategory.AUTH_REQUIRED
                            else "FAILED_RETRYABLE"
                            if failure.retryable
                            else "FAILED_TERMINAL"
                        )
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
                            "condition": condition,
                            "failure_category": failure.category.value,
                            "human_message": failure.human_message,
                            "technical_evidence": failure.technical_evidence,
                            **self._attempt_metadata(request),
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
                            "message": failure.human_message,
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
            context = next(
                (
                    name
                    for name in paths
                    if Path(name).name.casefold().startswith("readme")
                ),
                None,
            )
            if context is None:
                context = next((name for name in paths if name.endswith(".md")), None)
            if context is None:
                context = next(iter(paths), None)
            if context is None:
                raise ProductInvariantViolation(
                    "Repository acquisition requires at least one tracked file"
                )
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
                "description": request.description, "intake_request_id": str(request.request_id),
                "condition": "READY", "failure_category": None,
                "human_message": (
                    f"Local branch {request.target_branch} is ready."
                    if request.operation_kind == "CREATE_BRANCH"
                    else "Repository is ready."
                ), "technical_evidence": None,
                **self._attempt_metadata(request)}
            if request.operation_kind == "CREATE_BRANCH":
                observation["operation_evidence"] = {
                    "capability_id": "git.branch.create",
                    "connector_id": (
                        connector_capability.connector_id
                        if connector_capability is not None
                        else "builtin:git"
                    ),
                    "operation_ref": f"repository-intake:{request.request_id}",
                    "workspace_reference": str(repository),
                    "resulting_branch": ref,
                    "resulting_revision": revision,
                    "base_resource_id": str(request.base_resource_id),
                    "verified": ref == f"refs/heads/{request.target_branch}",
                    "native_attempt_id": None if native_result is None else native_result["native_attempt_id"],
                    "pwu_id": None if native_result is None else native_result["pwu_id"],
                    "task_contract_id": None if native_result is None else native_result["task_contract_id"],
                    "checkpoint_id": None if native_result is None else native_result["checkpoint_id"],
                    "environment_id": None if native_result is None else native_result["environment_id"],
                    "production_record_id": None if native_result is None else native_result["production_record_id"],
                }
                if not observation["operation_evidence"]["verified"]:
                    raise ProductInvariantViolation("Created branch observation differs from the Human-requested branch")
            elif connector_capability is not None:
                observation["operation_evidence"] = {
                    "capability_id": "git.repository.acquire",
                    "connector_id": connector_capability.connector_id,
                    "operation_ref": f"repository-intake:{request.request_id}",
                    "workspace_reference": str(repository),
                    "resulting_branch": ref,
                    "resulting_revision": revision,
                    "verified": bool(ref and revision),
                }
            observation["fingerprint"] = canonical_fingerprint(observation)
            with self.database.unit_of_work() as uow:
                uow.session.execute(update(repository_intakes).where(repository_intakes.c.id == request.request_id).values(resource_id=resource_id, observation=observation))
                uow.commit()
            return observation

    def mark_attempt_failure(
        self,
        request_id: UUID,
        *,
        category: RepositoryAcquisitionFailureCategory,
        human_message: str,
        technical_evidence: dict[str, object],
        retryable: bool,
    ) -> dict:
        with self.database.unit_of_work() as uow:
            observation = uow.session.execute(
                select(repository_intakes.c.observation).where(
                    repository_intakes.c.id == request_id
                )
            ).scalar_one_or_none()
            if observation is None:
                raise ProductRecordNotFound(
                    "Repository acquisition Attempt does not exist"
                )
            failed = {
                **observation,
                "condition": "FAILED_RETRYABLE" if retryable else "FAILED_TERMINAL",
                "failure_category": category.value,
                "human_message": human_message,
                "technical_evidence": technical_evidence,
                "message": human_message,
                "observed_at": datetime.now(UTC).isoformat(),
            }
            failed["fingerprint"] = canonical_fingerprint(
                {key: value for key, value in failed.items() if key != "fingerprint"}
            )
            uow.session.execute(
                update(repository_intakes)
                .where(repository_intakes.c.id == request_id)
                .values(observation=failed)
            )
            uow.commit()
        return failed

    def attempts_for_work(self, work_id: UUID) -> tuple[dict, ...]:
        identity = str(work_id)
        with self.database.unit_of_work() as uow:
            rows = uow.session.execute(
                select(
                    repository_intakes.c.id,
                    repository_intakes.c.request,
                    repository_intakes.c.observation,
                    repository_intakes.c.created_at,
                ).order_by(repository_intakes.c.created_at, repository_intakes.c.id)
            ).mappings().all()
        return tuple(
            {
                **(row["observation"] or {}),
                "intake_request_id": str(row["id"]),
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
            if str(row["request"].get("work_id")) == identity
        )

    def latest_attempt_for_work(self, work_id: UUID) -> dict | None:
        attempts = self.attempts_for_work(work_id)
        return attempts[-1] if attempts else None

    def next_attempt_number(self, work_id: UUID) -> int:
        attempts = self.attempts_for_work(work_id)
        return 1 + max(
            (int(item.get("attempt_number") or 0) for item in attempts),
            default=0,
        )

    def repository_activation_allowed(self, work_id: UUID) -> bool:
        latest = self.latest_attempt_for_work(work_id)
        if latest is not None:
            if latest.get("condition") != "READY":
                return False
            with self.database.unit_of_work() as uow:
                selected = ProductStore(uow.session).resource_for_work(work_id)
            return selected is not None and str(selected.id) == latest.get("resource_id")
        with self.database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            if product.resource_for_work(work_id) is not None:
                return True
            revision = product.current_work_reality_revision(work_id)
        if revision is None:
            return True
        repository_required = any(
            fact.subject == "repository.url"
            for fact in current_semantic_facts(
                revision.engineering_semantic_facts
            )
        ) or any(
            production_intent_evidence(value).repository_source is not None
            for value in (
                *revision.requests,
                *revision.context_facts,
            )
        )
        return not repository_required

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
