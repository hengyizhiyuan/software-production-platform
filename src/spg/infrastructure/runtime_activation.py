"""Bounded local-Docker activation and active Runtime inspection."""

from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import json
import subprocess

from spg.config import Settings
from spg.infrastructure.content_identity import tree_fingerprint

from spg.domain.runtime_activation import (
    ActiveRuntimeEvidence,
    HumanReviewRuntimeVersion,
    RuntimeActivationProjection,
    RuntimeActivationState,
)


RUNTIME_ACTIVATION_BLOCKED = "RUNTIME_ACTIVATION_BLOCKED"
IMAGE_REBUILD_REQUIRED = "IMAGE_REBUILD_REQUIRED"

_IMAGE_BOUND_PATHS = frozenset(
    {
        ".dockerignore",
        "Dockerfile",
        "alembic.ini",
        "pyproject.toml",
        "uv.lock",
    }
)
_IMAGE_BOUND_PREFIXES = ("docker/", "migrations/")
_COMPOSE_PREFIX = "compose"
_COMPOSE_SUFFIXES = (".yaml", ".yml")
_REVIEW_CACHE_NAMES = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})


def review_runtime_configuration(settings: Settings) -> dict[str, object]:
    """Non-secret behavior/worker binding inputs; credentials are never serialized."""

    names = (
        "runtime_profile", "executor_adapter", "verification_adapter",
        "native_executor_enabled", "native_executor_backend",
        "native_executor_worker_profile", "native_executor_resource_profile",
        "native_executor_inference_provider", "native_executor_inference_model",
        "native_executor_inference_reasoning_effort", "wic_provider_adapter",
        "wic_provider_model", "conversation_provider_adapter",
        "conversation_provider_model", "delivery_runtime_enabled",
    )
    return {name: getattr(settings, name) for name in names}


def _digest(value: dict[str, object]) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class RuntimeActivationError(RuntimeError):
    """A safe local activation could not be proven."""


def image_rebuild_paths(changed_paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return changes that a source-only restart must never claim to activate."""

    return tuple(
        path
        for path in changed_paths
        if path in _IMAGE_BOUND_PATHS
        or path.startswith(_IMAGE_BOUND_PREFIXES)
        or (path.startswith(_COMPOSE_PREFIX) and path.endswith(_COMPOSE_SUFFIXES))
    )


class GitLocalRuntimeActivation:
    """Prepare one internally consistent local process from an exact Git revision."""

    def tree_identity(self, repository_path: Path, revision: str) -> str:
        """Read the exact Git tree identity for a locally available revision."""

        repository = repository_path.resolve()
        self._require_repository(repository)
        self._require_commit(repository, revision)
        return self._git(repository, "rev-parse", f"{revision}^{{tree}}")

    def prepare_review(
        self, *, repository_path: Path, trusted_revision: str,
        trusted_tree_identity: str, source_root: Path,
        configuration_root: Path, settings: Settings,
    ) -> HumanReviewRuntimeVersion:
        """Identify a live review overlay independently from the engineering baseline."""

        repository = repository_path.resolve()
        self._require_repository(repository)
        self._require_commit(repository, trusted_revision)
        if self._git(repository, "rev-parse", "HEAD") != trusted_revision or (
            self.tree_identity(repository, trusted_revision) != trusted_tree_identity
        ) or self._git(repository, "status", "--porcelain=v1"):
            self._blocked("Human Review engineering repository must remain at a clean Trusted Baseline")
        source = source_root.resolve(strict=True)
        config = configuration_root.resolve(strict=True)
        if source_root.is_symlink() or configuration_root.is_symlink():
            self._blocked("Human Review source/config root cannot be a symlink")
        if not (source / "spg" / "web").is_dir() or not (config / "uv.lock").is_file():
            self._blocked("Human Review source or dependency lock is unavailable")
        try:
            fields = {
                "base_revision": trusted_revision,
                "base_tree_identity": trusted_tree_identity,
                "source_root": str(source),
                "configuration_root": str(config),
                "source_digest": tree_fingerprint(source, excluded_names=_REVIEW_CACHE_NAMES),
                "package_digest": tree_fingerprint(source / "spg", excluded_names=_REVIEW_CACHE_NAMES),
                "static_asset_digest": tree_fingerprint(source / "spg" / "web", excluded_names=_REVIEW_CACHE_NAMES),
                "dependency_lock_digest": sha256((config / "uv.lock").read_bytes()).hexdigest(),
                "configuration_digest": _digest({
                    "files": tree_fingerprint(config, excluded_names=_REVIEW_CACHE_NAMES),
                    "runtime": review_runtime_configuration(settings),
                }),
            }
            version = HumanReviewRuntimeVersion(version_id=_digest(fields), **fields)
            if any(fields[key] != value for key, value in self._review_fields(source, config, settings).items()):
                self._blocked("Human Review inputs changed during identity capture")
            return version
        except (OSError, ValueError) as error:
            self._blocked(f"Human Review identity cannot be captured: {error}")

    @staticmethod
    def _review_fields(source: Path, config: Path, settings: Settings) -> dict[str, object]:
        return {
            "source_digest": tree_fingerprint(source, excluded_names=_REVIEW_CACHE_NAMES),
            "package_digest": tree_fingerprint(source / "spg", excluded_names=_REVIEW_CACHE_NAMES),
            "static_asset_digest": tree_fingerprint(source / "spg" / "web", excluded_names=_REVIEW_CACHE_NAMES),
            "dependency_lock_digest": sha256((config / "uv.lock").read_bytes()).hexdigest(),
            "configuration_digest": _digest({
                "files": tree_fingerprint(config, excluded_names=_REVIEW_CACHE_NAMES),
                "runtime": review_runtime_configuration(settings),
            }),
        }

    def inspect_review(
        self, *, repository_path: Path, version: HumanReviewRuntimeVersion | None,
        trusted_revision: str, trusted_tree_identity: str, settings: Settings,
    ) -> RuntimeActivationProjection:
        def blocked(reason: str) -> RuntimeActivationProjection:
            return RuntimeActivationProjection(
                state=RuntimeActivationState.ACTIVATION_BLOCKED,
                current_trusted_baseline_revision=trusted_revision,
                current_trusted_baseline_tree_identity=trusted_tree_identity,
                activation_mode="HUMAN_REVIEW", reason=reason,
            )

        if version is None:
            return blocked("Explicit Human Review Runtime Version evidence is unavailable.")
        try:
            repository = repository_path.resolve()
            self._require_repository(repository)
            self._require_commit(repository, trusted_revision)
            self._require_commit(repository, version.base_revision)
            if (
                self.tree_identity(repository, version.base_revision) != version.base_tree_identity
                or self._git(repository, "status", "--porcelain=v1")
            ):
                self._blocked("Human Review base Git object or engineering checkout is invalid")
            source = Path(version.source_root)
            config = Path(version.configuration_root)
            if source.is_symlink() or config.is_symlink() or (
                not source.is_dir() or not config.is_dir()
            ):
                self._blocked("Human Review source/config root is unavailable or linked")
            fields = version.model_dump(exclude={"version_id"})
            if _digest(fields) != version.version_id:
                self._blocked("Human Review Runtime Version identity differs from its evidence")
            observed = self._review_fields(source, config, settings)
            if any(fields[key] != value for key, value in observed.items()):
                self._blocked("Human Review running source/assets/dependencies/config changed")
            if self._review_fields(source, config, settings) != observed:
                self._blocked("Human Review source changed during inspection")
        except (RuntimeActivationError, OSError, ValueError) as error:
            return blocked(str(error))
        return RuntimeActivationProjection(
            state=RuntimeActivationState.ACTIVE_HUMAN_REVIEW,
            current_trusted_baseline_revision=trusted_revision,
            current_trusted_baseline_tree_identity=trusted_tree_identity,
            activation_mode="HUMAN_REVIEW",
            human_review_version_id=version.version_id,
            reason="Exact Human Review build observed; no application trust or release claim.",
        )

    def prepare(
        self,
        *,
        repository_path: Path,
        trusted_revision: str,
        trusted_tree_identity: str,
        previous_active_revision: str,
    ) -> ActiveRuntimeEvidence:
        repository = repository_path.resolve()
        self._require_repository(repository)
        self._require_commit(repository, trusted_revision)
        self._require_commit(repository, previous_active_revision)

        head = self._git(repository, "rev-parse", "HEAD")
        tree = self._git(repository, "rev-parse", f"{trusted_revision}^{{tree}}")
        if head != trusted_revision or tree != trusted_tree_identity:
            self._blocked("checkout HEAD/tree differs from Current Trusted Baseline")
        if self._git(repository, "status", "--porcelain=v1"):
            self._blocked("checkout is not clean after Trusted Baseline synchronization")

        changed = self._changed_paths(
            repository,
            previous_active_revision,
            trusted_revision,
        )
        rebuild = image_rebuild_paths(changed)
        if rebuild:
            raise RuntimeActivationError(
                f"{IMAGE_REBUILD_REQUIRED}: " + ", ".join(rebuild)
            )

        source_root = repository / "src"
        package_root = source_root / "spg"
        static_root = package_root / "web"
        if not package_root.is_dir() or not static_root.is_dir():
            self._blocked("Trusted Baseline does not contain the SPG package/Web roots")

        return ActiveRuntimeEvidence(
            active_application_revision=trusted_revision,
            active_repository_tree_identity=trusted_tree_identity,
            active_source_package_fingerprint=self._git(
                repository, "rev-parse", f"{trusted_revision}:src/spg"
            ),
            active_static_asset_fingerprint=self._git(
                repository, "rev-parse", f"{trusted_revision}:src/spg/web"
            ),
            active_source_root=str(source_root),
        )

    def inspect(
        self,
        *,
        repository_path: Path,
        active: ActiveRuntimeEvidence | None,
        trusted_revision: str,
        trusted_tree_identity: str,
    ) -> RuntimeActivationProjection:
        if active is None:
            return self._projection(
                RuntimeActivationState.ACTIVATION_BLOCKED,
                None,
                trusted_revision,
                trusted_tree_identity,
                "Active Runtime evidence is unavailable.",
            )

        repository = repository_path.resolve()
        try:
            self._require_repository(repository)
            self._require_commit(repository, active.active_application_revision)
            self._require_commit(repository, trusted_revision)
            active_tree = self._git(
                repository,
                "rev-parse",
                f"{active.active_application_revision}^{{tree}}",
            )
            package_fingerprint = self._git(
                repository,
                "rev-parse",
                f"{active.active_application_revision}:src/spg",
            )
            static_fingerprint = self._git(
                repository,
                "rev-parse",
                f"{active.active_application_revision}:src/spg/web",
            )
            if (
                active_tree != active.active_repository_tree_identity
                or package_fingerprint != active.active_source_package_fingerprint
                or static_fingerprint != active.active_static_asset_fingerprint
            ):
                self._blocked("active Runtime evidence differs from exact Git objects")
            expected_source_root = (repository / "src").resolve()
            if Path(active.active_source_root).resolve() != expected_source_root:
                self._blocked("active source root is not the governed repository source root")
            if not self._quiet_worktree_against(
                repository,
                active.active_application_revision,
                "src/spg",
            ):
                self._blocked("active package/static files differ from active revision")
        except RuntimeActivationError as error:
            return self._projection(
                RuntimeActivationState.ACTIVATION_BLOCKED,
                active,
                trusted_revision,
                trusted_tree_identity,
                str(error),
            )

        if active.active_application_revision == trusted_revision:
            if active.active_repository_tree_identity != trusted_tree_identity:
                return self._projection(
                    RuntimeActivationState.ACTIVATION_BLOCKED,
                    active,
                    trusted_revision,
                    trusted_tree_identity,
                    "Active and Trusted revisions match but tree identities differ.",
                )
            return self._projection(
                RuntimeActivationState.ACTIVE_AT_TRUSTED_BASELINE,
                active,
                trusted_revision,
                trusted_tree_identity,
                "Active Python package and Web assets match Current Trusted Baseline.",
            )

        changed = self._changed_paths(
            repository,
            active.active_application_revision,
            trusted_revision,
        )
        rebuild = image_rebuild_paths(changed)
        if rebuild:
            return self._projection(
                RuntimeActivationState.IMAGE_REBUILD_REQUIRED,
                active,
                trusted_revision,
                trusted_tree_identity,
                "Trusted changes affect the execution image/dependency boundary.",
                rebuild,
            )
        return self._projection(
            RuntimeActivationState.ACTIVATION_REQUIRED,
            active,
            trusted_revision,
            trusted_tree_identity,
            "Trusted repository result is not active in the current application process.",
        )

    @staticmethod
    def _projection(
        state: RuntimeActivationState,
        active: ActiveRuntimeEvidence | None,
        trusted_revision: str,
        trusted_tree_identity: str,
        reason: str,
        rebuild: tuple[str, ...] = (),
    ) -> RuntimeActivationProjection:
        return RuntimeActivationProjection(
            state=state,
            active_application_revision=(
                None if active is None else active.active_application_revision
            ),
            active_repository_tree_identity=(
                None if active is None else active.active_repository_tree_identity
            ),
            active_source_package_fingerprint=(
                None if active is None else active.active_source_package_fingerprint
            ),
            active_static_asset_fingerprint=(
                None if active is None else active.active_static_asset_fingerprint
            ),
            current_trusted_baseline_revision=trusted_revision,
            current_trusted_baseline_tree_identity=trusted_tree_identity,
            activation_mode=None if active is None else active.activation_mode,
            reason=reason,
            image_rebuild_paths=rebuild,
        )

    @classmethod
    def _changed_paths(
        cls,
        repository: Path,
        source_revision: str,
        target_revision: str,
    ) -> tuple[str, ...]:
        if source_revision == target_revision:
            return ()
        output = cls._git(
            repository,
            "diff",
            "--name-only",
            "--no-renames",
            source_revision,
            target_revision,
            "--",
        )
        return tuple(path for path in output.splitlines() if path)

    @staticmethod
    def _quiet_worktree_against(
        repository: Path,
        revision: str,
        path: str,
    ) -> bool:
        result = subprocess.run(
            ["git", "-C", str(repository), "diff", "--quiet", revision, "--", path],
            check=False,
            capture_output=True,
        )
        return result.returncode == 0

    @classmethod
    def _require_repository(cls, repository: Path) -> None:
        if not (repository / ".git").is_dir():
            cls._blocked("active Runtime repository is unavailable")

    @classmethod
    def _require_commit(cls, repository: Path, revision: str) -> None:
        observed = cls._git(repository, "rev-parse", "--verify", f"{revision}^{{commit}}")
        if observed != revision:
            cls._blocked("required Runtime revision is unavailable")

    @staticmethod
    def _git(repository: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip() or "Git failed"
            raise RuntimeActivationError(f"{RUNTIME_ACTIVATION_BLOCKED}: {message}")
        return result.stdout.strip()

    @staticmethod
    def _blocked(message: str) -> None:
        raise RuntimeActivationError(f"{RUNTIME_ACTIVATION_BLOCKED}: {message}")
