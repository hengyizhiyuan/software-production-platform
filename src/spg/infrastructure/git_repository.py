"""Read-only Git repository reality observation for explicit bootstrap."""

from pathlib import Path
import subprocess

from spg.domain.runtime import RepositoryReality, RepositoryRealityError


class GitRepositoryObserver:
    """Observe exact committed Git reality without mutating repository state."""

    def observe(
        self,
        repository_path: Path,
        repository_identity: str,
        repository_ref: str,
    ) -> RepositoryReality:
        path = repository_path.resolve()
        top_level = self._git(path, "rev-parse", "--show-toplevel")
        if Path(top_level).resolve() != path:
            raise RepositoryRealityError(
                "bootstrap repository_path must be the Git repository root"
            )

        if self._git(path, "status", "--porcelain"):
            raise RepositoryRealityError(
                "bootstrap refuses a dirty repository because HEAD is incomplete reality"
            )

        revision = self._git(
            path,
            "rev-parse",
            "--verify",
            f"{repository_ref}^{{commit}}",
        )
        return RepositoryReality(
            repository_identity=repository_identity,
            repository_ref=repository_ref,
            exact_revision=revision,
        )

    @staticmethod
    def _git(path: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(path), *arguments],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or "Git observation failed"
            raise RepositoryRealityError(message)
        return result.stdout.strip()
