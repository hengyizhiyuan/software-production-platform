"""Deterministic local Docker product bootstrap and ASGI startup."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

from spg.application import bootstrap
from spg.domain.integration import RepositoryEffectState
from spg.domain.preparation import ContextSemanticRole
from spg.domain.product import EngineeringContextReference
from spg.domain.runtime import BootstrapRequest, RuntimeNotBootstrapped, SnapshotCondition
from spg.infrastructure.git_checkout import GitTrustedCheckoutSynchronizer
from spg.infrastructure.git_integration import GitRepositoryIntegrationAdapter
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.runtime_activation import (
    GitLocalRuntimeActivation,
    RuntimeActivationError,
)
from spg.domain.runtime_activation import ActiveRuntimeEvidence


PRODUCT_DATABASE = "spg_dev"
REQUIRED_LOCAL_DATABASES = ("spg_dev", "spg_test")
SOURCE_REPOSITORY = Path("/source")
RUNTIME_REPOSITORY = Path("/var/lib/spg/repository")
REPOSITORY_IDENTITY = "local://software-production-platform"
LOCAL_AUTHORITY = "local-docker-bootstrap"
CODEX_AUTH_SOURCE_VARIABLE = "SPG_CODEX_AUTH_SOURCE"
ACTIVATION_EVIDENCE_FILE = Path("/var/lib/spg/runtime-activation.json")
PREVIOUS_ACTIVE_REVISION_VARIABLE = "SPG_PREVIOUS_ACTIVE_RUNTIME_REVISION"


def _run(*arguments: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        arguments,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise RuntimeError(f"{arguments[0]} failed: {message}")
    return result.stdout.strip()


def ensure_local_databases() -> None:
    """Create only the two admitted local databases when they are absent."""

    configured = os.environ.get("SPG_DATABASE_URL")
    if not configured:
        raise RuntimeError("SPG_DATABASE_URL is required")
    target = make_url(configured)
    if target.database != PRODUCT_DATABASE:
        raise RuntimeError("Docker product SPG_DATABASE_URL must target spg_dev")
    admin = target.set(drivername="postgresql", database="postgres")
    with psycopg.connect(
        admin.render_as_string(hide_password=False),
        autocommit=True,
    ) as connection:
        for database_name in REQUIRED_LOCAL_DATABASES:
            exists = connection.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (database_name,),
            ).fetchone()
            if exists is None:
                connection.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(database_name)
                    )
                )
    print("local databases ready: spg_dev, spg_test", flush=True)


def prepare_optional_codex_state() -> None:
    """Expose only an authorized auth cache to a container-native state root."""

    codex_home_value = os.environ.get("CODEX_HOME")
    auth_source_value = os.environ.get(CODEX_AUTH_SOURCE_VARIABLE)
    if codex_home_value is None and auth_source_value is None:
        return
    if not codex_home_value or not auth_source_value:
        raise RuntimeError(
            "Codex E2E requires both CODEX_HOME and SPG_CODEX_AUTH_SOURCE"
        )

    codex_home = Path(codex_home_value)
    auth_source = Path(auth_source_value)
    codex_home.mkdir(parents=True, exist_ok=True)
    if not auth_source.is_file():
        raise RuntimeError("authorized Codex authentication input is unavailable")

    auth_target = codex_home / "auth.json"
    if auth_target.is_symlink():
        if auth_target.readlink() != auth_source:
            raise RuntimeError("Codex authentication link targets an unexpected input")
    elif auth_target.exists():
        if not auth_target.is_file():
            raise RuntimeError("container-native Codex auth target is not a file")
    else:
        auth_target.symlink_to(auth_source)
    print("container-native Codex state root ready", flush=True)


def migrate_product_database() -> None:
    """Fail startup unless the interactive product database reaches head."""

    _run(sys.executable, "-m", "alembic", "upgrade", "head", cwd=Path("/app"))
    print("spg_dev migration complete", flush=True)


def prepare_repository_snapshot() -> Path:
    """Locate or clone committed host Git reality without interpreting Runtime state."""

    if not (SOURCE_REPOSITORY / ".git").is_dir():
        raise RuntimeError("read-only local Git metadata mount is required")
    if not (RUNTIME_REPOSITORY / ".git").is_dir():
        RUNTIME_REPOSITORY.parent.mkdir(parents=True, exist_ok=True)
        for safe_path in (SOURCE_REPOSITORY, SOURCE_REPOSITORY / ".git"):
            _run(
                "git",
                "config",
                "--global",
                "--add",
                "safe.directory",
                str(safe_path),
            )
        _run(
            "git",
            "clone",
            "--no-hardlinks",
            str(SOURCE_REPOSITORY),
            str(RUNTIME_REPOSITORY),
        )
    return RUNTIME_REPOSITORY


def synchronize_repository_checkout(repository: Path) -> None:
    """Safely materialize an already-committed Trusted Baseline checkout."""

    application = bootstrap()
    database = application.persistence()
    git = GitRepositoryIntegrationAdapter()
    synchronizer = GitTrustedCheckoutSynchronizer()
    try:
        with database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            pointer = store.current_pointer()
            if pointer is None:
                current_ref = _current_repository_ref(repository)
                current_revision = git.read_ref(repository, current_ref)
                current_tree = git.read_commit_tree(repository, current_revision)
                result = synchronizer.synchronize(
                    repository_path=repository,
                    authoritative_ref=current_ref,
                    source_revision=current_revision,
                    trusted_revision=current_revision,
                    trusted_tree_identity=current_tree,
                )
            else:
                baseline = store.snapshot(pointer.snapshot_id)
                if baseline is None or baseline.condition is not SnapshotCondition.TRUSTED:
                    raise RuntimeError(
                        "REPOSITORY_CHECKOUT_DIVERGENCE: current Baseline is unavailable"
                    )
                if baseline.repository_identity != REPOSITORY_IDENTITY:
                    raise RuntimeError(
                        "REPOSITORY_CHECKOUT_DIVERGENCE: Baseline repository identity differs"
                    )
                resource = ProductStore(unit_of_work.session).default_resource()
                if resource is None and pointer.version != 0:
                    raise RuntimeError(
                        "REPOSITORY_CHECKOUT_DIVERGENCE: default Engineering Resource is unavailable"
                    )
                if resource is not None and (
                    resource.repository_identity != REPOSITORY_IDENTITY
                    or resource.location_ref != str(repository)
                    or resource.authoritative_ref != baseline.repository_ref
                ):
                    raise RuntimeError(
                        "REPOSITORY_CHECKOUT_DIVERGENCE: Engineering Resource identity differs"
                    )

                runtime_commit = store.runtime_commit_for_new_baseline(baseline.id)
                if runtime_commit is None:
                    if pointer.version != 0 or baseline.source_baseline_id is not None:
                        raise RuntimeError(
                            "REPOSITORY_CHECKOUT_DIVERGENCE: current Baseline has no Runtime Commit"
                        )
                    trusted_tree = git.read_commit_tree(
                        repository,
                        baseline.repository_revision,
                    )
                    result = synchronizer.synchronize(
                        repository_path=repository,
                        authoritative_ref=baseline.repository_ref,
                        source_revision=baseline.repository_revision,
                        trusted_revision=baseline.repository_revision,
                        trusted_tree_identity=trusted_tree,
                    )
                else:
                    source = store.snapshot(runtime_commit.source_baseline_id)
                    effect = store.repository_integration_effect(
                        runtime_commit.repository_integration_effect_id
                    )
                    if (
                        source is None
                        or source.condition is not SnapshotCondition.TRUSTED
                        or baseline.source_baseline_id != source.id
                        or source.repository_identity != REPOSITORY_IDENTITY
                        or source.repository_ref != baseline.repository_ref
                        or source.repository_revision
                        != runtime_commit.expected_source_repository_revision
                        or runtime_commit.new_baseline_id != baseline.id
                        or runtime_commit.repository_identity != REPOSITORY_IDENTITY
                        or runtime_commit.target_authoritative_ref
                        != baseline.repository_ref
                        or runtime_commit.repository_revision
                        != baseline.repository_revision
                        or effect is None
                        or effect.state is not RepositoryEffectState.CONVERGED
                        or effect.id
                        != runtime_commit.repository_integration_effect_id
                        or effect.repository_identity != REPOSITORY_IDENTITY
                        or effect.target_authoritative_ref
                        != baseline.repository_ref
                        or effect.expected_source_repository_revision
                        != source.repository_revision
                        or effect.proposed_repository_revision
                        != baseline.repository_revision
                        or effect.proposed_tree_identity
                        != runtime_commit.repository_tree_identity
                        or effect.observed_repository_revision
                        != baseline.repository_revision
                    ):
                        raise RuntimeError(
                            "REPOSITORY_CHECKOUT_DIVERGENCE: Runtime integration lineage differs"
                        )
                    result = synchronizer.synchronize(
                        repository_path=repository,
                        authoritative_ref=baseline.repository_ref,
                        source_revision=source.repository_revision,
                        trusted_revision=baseline.repository_revision,
                        trusted_tree_identity=runtime_commit.repository_tree_identity,
                    )
    finally:
        database.dispose()

    outcome = "synchronized" if result.synchronized else "already current"
    print(f"repository checkout {outcome} at Trusted Baseline", flush=True)


def _current_repository_ref(repository: Path) -> str:
    symbolic = subprocess.run(
        ["git", "symbolic-ref", "HEAD"],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    if symbolic.returncode == 0 and symbolic.stdout.strip():
        return symbolic.stdout.strip()
    return _run("git", "rev-parse", "HEAD", cwd=repository)


def ensure_local_product_foundation(repository: Path) -> None:
    """Idempotently establish the local Baseline and default Resource."""

    application = bootstrap()
    database = application.persistence()
    runtime = application.runtime(database)
    try:
        try:
            baseline = runtime.current_baseline()
        except RuntimeNotBootstrapped:
            repository_ref = _current_repository_ref(repository)
            baseline = runtime.bootstrap_trusted_baseline(
                BootstrapRequest(
                    repository_path=repository,
                    repository_identity=REPOSITORY_IDENTITY,
                    repository_ref=repository_ref,
                    authority_identity=LOCAL_AUTHORITY,
                    scope={"runtime_profile": "local-docker-mvp"},
                    rationale="Initialize the local Docker MVP product baseline",
                )
            ).snapshot

        if baseline.repository_identity != REPOSITORY_IDENTITY:
            raise RuntimeError("existing Baseline belongs to another repository")
        observed_revision = _run(
            "git",
            "rev-parse",
            "--verify",
            f"{baseline.repository_revision}^{{commit}}",
            cwd=repository,
        )
        if observed_revision != baseline.repository_revision:
            raise RuntimeError("persisted Baseline revision is unavailable")

        with database.unit_of_work() as unit_of_work:
            resource = ProductStore(unit_of_work.session).default_resource()
        if resource is None:
            application.work(database).register_engineering_resource(
                repository_identity=REPOSITORY_IDENTITY,
                location_ref=str(repository),
                authoritative_ref=baseline.repository_ref,
                context_references=(
                    EngineeringContextReference(
                        semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                        repository_relative_path="AI_context.md",
                    ),
                    EngineeringContextReference(
                        semantic_role=ContextSemanticRole.EXECUTION_CONTRACT,
                        repository_relative_path=(
                            "docs/architecture/spg-fvs-1-implementation-contract.md"
                        ),
                    ),
                ),
            )
        elif (
            resource.repository_identity != REPOSITORY_IDENTITY
            or resource.location_ref != str(repository)
            or resource.authoritative_ref != baseline.repository_ref
        ):
            raise RuntimeError("existing default Engineering Resource is incompatible")
    finally:
        database.dispose()
    print("local product foundation ready", flush=True)


def prepare_local_runtime_activation(repository: Path) -> ActiveRuntimeEvidence:
    """Bind one whole application process to the exact Current Trusted Baseline."""

    application = bootstrap()
    database = application.persistence()
    try:
        with database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            pointer = store.current_pointer()
            if pointer is None:
                raise RuntimeActivationError(
                    "RUNTIME_ACTIVATION_BLOCKED: Current Trusted Baseline is unavailable"
                )
            baseline = store.snapshot(pointer.snapshot_id)
            if baseline is None or baseline.condition is not SnapshotCondition.TRUSTED:
                raise RuntimeActivationError(
                    "RUNTIME_ACTIVATION_BLOCKED: Current Trusted Baseline is invalid"
                )
        trusted_tree = _run(
            "git",
            "rev-parse",
            f"{baseline.repository_revision}^{{tree}}",
            cwd=repository,
        )
        previous = _previous_active_revision(
            pointer_version=pointer.version,
            trusted_revision=baseline.repository_revision,
        )
        evidence = GitLocalRuntimeActivation().prepare(
            repository_path=repository,
            trusted_revision=baseline.repository_revision,
            trusted_tree_identity=trusted_tree,
            previous_active_revision=previous,
        )
        _write_activation_evidence(evidence)
        return evidence
    finally:
        database.dispose()


def _previous_active_revision(*, pointer_version: int, trusted_revision: str) -> str:
    override = os.environ.get(PREVIOUS_ACTIVE_REVISION_VARIABLE)
    if override:
        return override
    if ACTIVATION_EVIDENCE_FILE.is_file() and not ACTIVATION_EVIDENCE_FILE.is_symlink():
        try:
            return ActiveRuntimeEvidence.model_validate_json(
                ACTIVATION_EVIDENCE_FILE.read_text(encoding="utf-8")
            ).active_application_revision
        except (OSError, ValueError) as error:
            raise RuntimeActivationError(
                "RUNTIME_ACTIVATION_BLOCKED: active Runtime evidence is invalid"
            ) from error
    if pointer_version == 0:
        return trusted_revision
    raise RuntimeActivationError(
        "RUNTIME_ACTIVATION_BLOCKED: previous active revision evidence is required"
    )


def _write_activation_evidence(evidence: ActiveRuntimeEvidence) -> None:
    if ACTIVATION_EVIDENCE_FILE.is_symlink():
        raise RuntimeActivationError(
            "RUNTIME_ACTIVATION_BLOCKED: activation evidence path is a symlink"
        )
    ACTIVATION_EVIDENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = ACTIVATION_EVIDENCE_FILE.with_suffix(".json.tmp")
    temporary.write_text(evidence.model_dump_json(), encoding="utf-8")
    temporary.replace(ACTIVATION_EVIDENCE_FILE)


def _activated_environment(evidence: ActiveRuntimeEvidence) -> dict[str, str]:
    environment = dict(os.environ)
    existing_python_path = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        evidence.active_source_root
        if not existing_python_path
        else f"{evidence.active_source_root}{os.pathsep}{existing_python_path}"
    )
    environment["SPG_ACTIVE_RUNTIME_REVISION"] = evidence.active_application_revision
    environment["SPG_ACTIVE_RUNTIME_TREE_IDENTITY"] = (
        evidence.active_repository_tree_identity
    )
    environment["SPG_ACTIVE_RUNTIME_PACKAGE_FINGERPRINT"] = (
        evidence.active_source_package_fingerprint
    )
    environment["SPG_ACTIVE_RUNTIME_STATIC_ASSET_FINGERPRINT"] = (
        evidence.active_static_asset_fingerprint
    )
    environment["SPG_ACTIVE_RUNTIME_SOURCE_ROOT"] = evidence.active_source_root
    environment.pop(PREVIOUS_ACTIVE_REVISION_VARIABLE, None)
    return environment


def main() -> None:
    prepare_optional_codex_state()
    ensure_local_databases()
    migrate_product_database()
    repository = prepare_repository_snapshot()
    synchronize_repository_checkout(repository)
    ensure_local_product_foundation(repository)
    activation = prepare_local_runtime_activation(repository)
    print(
        "runtime activation prepared at Current Trusted Baseline "
        f"{activation.active_application_revision}",
        flush=True,
    )
    os.execvpe(
        sys.executable,
        (
            sys.executable,
            "-m",
            "uvicorn",
            "spg.api.http:create_http_application",
            "--factory",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ),
        _activated_environment(activation),
    )


if __name__ == "__main__":
    main()
