"""Safe checkout materialization for an already-admitted Trusted Baseline."""

from dataclasses import dataclass
from pathlib import Path
import subprocess

from spg.domain.runtime import RepositoryRealityError


CHECKOUT_DIVERGENCE = "REPOSITORY_CHECKOUT_DIVERGENCE"


@dataclass(frozen=True, slots=True)
class CheckoutSynchronizationResult:
    """Observed checkout state after one bounded synchronization decision."""

    repository_ref: str
    repository_revision: str
    repository_tree_identity: str
    synchronized: bool


class GitTrustedCheckoutSynchronizer:
    """Materialize a converged ref only from its exact prior-baseline index."""

    def synchronize(
        self,
        *,
        repository_path: Path,
        authoritative_ref: str,
        source_revision: str,
        trusted_revision: str,
        trusted_tree_identity: str,
    ) -> CheckoutSynchronizationResult:
        repository = self._repository_root(repository_path)
        observed_ref = self._symbolic_head(repository)
        if observed_ref != authoritative_ref:
            self._divergence("checkout does not use the authoritative ref")

        observed_ref_revision = self._git(
            repository,
            "rev-parse",
            "--verify",
            f"{authoritative_ref}^{{commit}}",
        )
        observed_head = self._git(repository, "rev-parse", "HEAD")
        if observed_ref_revision != trusted_revision or observed_head != trusted_revision:
            self._divergence("authoritative ref or HEAD differs from Trusted Baseline")

        observed_tree = self._git(repository, "rev-parse", f"{trusted_revision}^{{tree}}")
        if observed_tree != trusted_tree_identity:
            self._divergence("Trusted Baseline tree identity does not match Git Reality")

        status = self._git(repository, "status", "--porcelain=v1")
        if not status:
            return CheckoutSynchronizationResult(
                repository_ref=observed_ref,
                repository_revision=observed_head,
                repository_tree_identity=observed_tree,
                synchronized=False,
            )

        if source_revision == trusted_revision:
            self._divergence("a non-integrated Trusted Baseline checkout is dirty")
        self._require_commit(repository, source_revision)
        if not self._quiet(repository, "diff-files", "--quiet", "--"):
            self._divergence("checkout contains independent unstaged changes")
        if self._git(repository, "ls-files", "--others", "--exclude-standard"):
            self._divergence("checkout contains independent untracked files")
        if not self._quiet(
            repository,
            "diff-index",
            "--quiet",
            "--cached",
            source_revision,
            "--",
        ):
            self._divergence("checkout index is not the exact source Baseline")

        self._git(repository, "read-tree", "--reset", "-u", trusted_revision)
        if self._git(repository, "status", "--porcelain=v1"):
            self._divergence("checkout did not converge to a clean Trusted Baseline")
        if self._git(repository, "rev-parse", "HEAD") != trusted_revision:
            self._divergence("checkout synchronization changed authoritative HEAD")
        final_tree = self._git(repository, "rev-parse", "HEAD^{tree}")
        if final_tree != trusted_tree_identity:
            self._divergence("synchronized checkout tree differs from Trusted Baseline")

        return CheckoutSynchronizationResult(
            repository_ref=observed_ref,
            repository_revision=trusted_revision,
            repository_tree_identity=final_tree,
            synchronized=True,
        )

    @classmethod
    def _repository_root(cls, repository_path: Path) -> Path:
        repository = repository_path.resolve()
        observed = Path(cls._git(repository, "rev-parse", "--show-toplevel")).resolve()
        if observed != repository:
            cls._divergence("checkout path is not the repository root")
        return repository

    @classmethod
    def _symbolic_head(cls, repository: Path) -> str:
        result = cls._run(repository, "symbolic-ref", "HEAD")
        if result.returncode != 0 or not result.stdout.strip():
            cls._divergence("checkout HEAD is not attached to an authoritative ref")
        return result.stdout.strip()

    @classmethod
    def _require_commit(cls, repository: Path, revision: str) -> None:
        result = cls._run(repository, "cat-file", "-e", f"{revision}^{{commit}}")
        if result.returncode != 0:
            cls._divergence("source Baseline commit is unavailable")

    @classmethod
    def _quiet(cls, repository: Path, *arguments: str) -> bool:
        result = cls._run(repository, *arguments)
        if result.returncode not in (0, 1):
            message = result.stderr.strip() or "Git comparison failed"
            raise RepositoryRealityError(message)
        return result.returncode == 0

    @staticmethod
    def _run(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
            text=True,
        )

    @classmethod
    def _git(cls, repository: Path, *arguments: str) -> str:
        result = cls._run(repository, *arguments)
        if result.returncode != 0:
            message = result.stderr.strip() or "Git checkout synchronization failed"
            raise RepositoryRealityError(message)
        return result.stdout.strip()

    @staticmethod
    def _divergence(reason: str) -> None:
        raise RepositoryRealityError(f"{CHECKOUT_DIVERGENCE}: {reason}")
