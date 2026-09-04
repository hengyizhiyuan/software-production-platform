"""Bounded local-Docker activation and active Runtime inspection."""

from __future__ import annotations

from pathlib import Path
import subprocess

from spg.domain.runtime_activation import (
    ActiveRuntimeEvidence,
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
