"""Local Git factual adapter for the single S4-A repository-ref effect."""

from pathlib import Path
import subprocess

from spg.domain.runtime import RepositoryRealityError


class GitRepositoryIntegrationAdapter:
    """Read exact Git facts and execute one old-value guarded ref update."""

    def read_ref(self, repository_path: Path, repository_ref: str) -> str:
        repository = self._repository_root(repository_path)
        return self._git(
            repository,
            "rev-parse",
            "--verify",
            f"{repository_ref}^{{commit}}",
        )

    def commit_exists(self, repository_path: Path, commit_identity: str) -> bool:
        repository = self._repository_root(repository_path)
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "cat-file",
                "-e",
                f"{commit_identity}^{{commit}}",
            ],
            check=False,
            capture_output=True,
        )
        return result.returncode == 0

    def read_commit_tree(self, repository_path: Path, commit_identity: str) -> str:
        repository = self._repository_root(repository_path)
        return self._git(
            repository,
            "rev-parse",
            f"{commit_identity}^{{tree}}",
        )

    def compare_and_swap_ref(
        self,
        repository_path: Path,
        repository_ref: str,
        expected_old_revision: str,
        proposed_new_revision: str,
    ) -> bool:
        """Apply only exact old -> new; never force, merge, rebase, or push."""

        repository = self._repository_root(repository_path)
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "update-ref",
                repository_ref,
                proposed_new_revision,
                expected_old_revision,
            ],
            check=False,
            capture_output=True,
        )
        return result.returncode == 0

    @classmethod
    def _repository_root(cls, repository_path: Path) -> Path:
        path = repository_path.resolve()
        top_level = Path(cls._git(path, "rev-parse", "--show-toplevel")).resolve()
        if top_level != path:
            raise RepositoryRealityError(
                "repository integration path must be the Git repository root"
            )
        return path

    @staticmethod
    def _git(path: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(path), *arguments],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or "Git repository integration failed"
            raise RepositoryRealityError(message)
        return result.stdout.strip()
