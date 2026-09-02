"""Read-only Git qualification for verified maintenance recovery."""

from pathlib import Path
import subprocess

from spg.domain.maintenance_recovery import MaintenanceRepositoryReality
from spg.domain.runtime import RepositoryRealityError


class GitMaintenanceObserver:
    """Observe exact ref, commit, tree, ancestry, and changed paths without mutation."""

    def observe(
        self,
        repository_path: Path,
        *,
        repository_identity: str,
        authoritative_ref: str,
        old_revision: str,
        target_commit: str,
        target_tree: str,
    ) -> MaintenanceRepositoryReality:
        repository = self._repository_root(repository_path)
        if self._git(repository, "status", "--porcelain"):
            raise RepositoryRealityError(
                "verified maintenance recovery requires a clean repository"
            )
        observed_ref = self._git(
            repository,
            "rev-parse",
            "--verify",
            f"{authoritative_ref}^{{commit}}",
        )
        if observed_ref != target_commit:
            raise RepositoryRealityError(
                "authoritative ref does not equal exact maintenance target"
            )
        if not self._commit_exists(repository, target_commit):
            raise RepositoryRealityError("maintenance target commit does not exist")
        observed_tree = self._git(repository, "rev-parse", f"{target_commit}^{{tree}}")
        if observed_tree != target_tree:
            raise RepositoryRealityError("maintenance target tree mismatch")
        if not self._is_ancestor(repository, old_revision, target_commit):
            raise RepositoryRealityError(
                "maintenance target is not a descendant of the old Baseline"
            )
        changed = self._git_bytes(
            repository,
            "diff",
            "--name-only",
            "-z",
            old_revision,
            target_commit,
        )
        changed_paths = tuple(
            sorted(
                path.decode("utf-8")
                for path in changed.split(b"\0")
                if path
            )
        )
        return MaintenanceRepositoryReality(
            repository_identity=repository_identity,
            authoritative_ref=authoritative_ref,
            target_commit=target_commit,
            target_tree=observed_tree,
            old_revision=old_revision,
            changed_paths=changed_paths,
        )

    @classmethod
    def _repository_root(cls, repository_path: Path) -> Path:
        path = repository_path.resolve()
        top_level = Path(cls._git(path, "rev-parse", "--show-toplevel")).resolve()
        if top_level != path:
            raise RepositoryRealityError(
                "maintenance repository_path must be the Git repository root"
            )
        return path

    @staticmethod
    def _commit_exists(path: Path, commit_identity: str) -> bool:
        result = subprocess.run(
            ["git", "-C", str(path), "cat-file", "-e", f"{commit_identity}^{{commit}}"],
            check=False,
            capture_output=True,
        )
        return result.returncode == 0

    @staticmethod
    def _is_ancestor(path: Path, old_revision: str, target_commit: str) -> bool:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(path),
                "merge-base",
                "--is-ancestor",
                old_revision,
                target_commit,
            ],
            check=False,
            capture_output=True,
        )
        return result.returncode == 0

    @staticmethod
    def _git(path: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(path), *arguments],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or "Git maintenance observation failed"
            raise RepositoryRealityError(message)
        return result.stdout.strip()

    @staticmethod
    def _git_bytes(path: Path, *arguments: str) -> bytes:
        result = subprocess.run(
            ["git", "-C", str(path), *arguments],
            check=False,
            capture_output=True,
        )
        if result.returncode != 0:
            message = result.stderr.decode(errors="replace").strip()
            raise RepositoryRealityError(message or "Git maintenance observation failed")
        return result.stdout
