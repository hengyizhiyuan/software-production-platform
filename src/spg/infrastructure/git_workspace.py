"""Exact-revision Git reads and Attempt-specific detached worktree preparation."""

from pathlib import Path
import subprocess
from uuid import UUID

from spg.domain.preparation import WorkspaceBinding
from spg.domain.runtime import RepositoryRealityError


class GitExactReality:
    """Read repository content only from an explicitly supplied commit revision."""

    def read_blob(
        self,
        repository_path: Path,
        source_revision: str,
        repository_relative_path: str,
    ) -> tuple[bytes, str]:
        repository = self._repository_root(repository_path)
        self._git(repository, "cat-file", "-e", f"{source_revision}^{{commit}}")
        blob = self._git_bytes(
            repository,
            "show",
            f"{source_revision}:{repository_relative_path}",
        )
        blob_identity = self._git(
            repository,
            "rev-parse",
            f"{source_revision}:{repository_relative_path}",
        )
        return blob, blob_identity

    def identify_blob_content(
        self,
        repository_path: Path,
        repository_relative_path: str,
        content: bytes,
    ) -> str:
        """Apply Git's path-aware clean filters and return exact blob identity."""

        repository = self._repository_root(repository_path)
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "hash-object",
                f"--path={repository_relative_path}",
                "--stdin",
            ],
            input=content,
            check=False,
            capture_output=True,
        )
        if result.returncode != 0:
            message = (
                result.stderr.decode(errors="replace").strip()
                or "Git blob identification failed"
            )
            raise RepositoryRealityError(message)
        return result.stdout.decode().strip()

    @classmethod
    def _repository_root(cls, repository_path: Path) -> Path:
        repository = repository_path.resolve()
        top_level = Path(cls._git(repository, "rev-parse", "--show-toplevel")).resolve()
        if top_level != repository:
            raise RepositoryRealityError("repository_path must be the Git repository root")
        return repository

    @staticmethod
    def _git(repository: Path, *arguments: str) -> str:
        return GitExactReality._run(repository, *arguments).stdout.decode().strip()

    @staticmethod
    def _git_bytes(repository: Path, *arguments: str) -> bytes:
        return GitExactReality._run(repository, *arguments).stdout

    @staticmethod
    def _run(repository: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
        )
        if result.returncode != 0:
            message = result.stderr.decode(errors="replace").strip() or "Git operation failed"
            raise RepositoryRealityError(message)
        return result


class GitAttemptWorkspace:
    """Prepare/reconcile one detached worktree per authoritative Attempt."""

    def prepare(
        self,
        *,
        repository_path: Path,
        workspace_root: Path,
        attempt_id: UUID,
        repository_identity: str,
        source_revision: str,
    ) -> WorkspaceBinding:
        repository = GitExactReality._repository_root(repository_path)
        root = workspace_root.resolve()
        workspace = root / str(attempt_id)
        identity = f"attempt-worktree:{attempt_id}"
        try:
            workspace.relative_to(repository)
        except ValueError:
            pass
        else:
            raise RepositoryRealityError(
                "Attempt workspace must be outside the authoritative working tree"
            )
        GitExactReality._git(
            repository,
            "rev-parse",
            "--verify",
            f"{source_revision}^{{commit}}",
        )

        if workspace.exists():
            self._validate_existing(repository, workspace, source_revision)
        else:
            root.mkdir(parents=True, exist_ok=True)
            GitExactReality._git(
                repository,
                "worktree",
                "add",
                "--detach",
                str(workspace),
                source_revision,
            )
            self._validate_existing(repository, workspace, source_revision)

        return WorkspaceBinding(
            workspace_identity=identity,
            workspace_path=workspace,
            repository_identity=repository_identity,
            repository_path=repository,
            source_revision=source_revision,
        )

    def validate(self, binding: WorkspaceBinding) -> None:
        """Require exact baseline identity and the clean S2-A preparation fact."""

        self.validate_basis(binding)
        if GitExactReality._git(binding.workspace_path, "status", "--porcelain"):
            raise RepositoryRealityError("Attempt workspace is no longer clean preparation reality")

    def validate_basis(self, binding: WorkspaceBinding) -> None:
        """Require the exact worktree/HEAD binding while allowing produced changes."""

        repository = GitExactReality._repository_root(binding.repository_path)
        workspace = binding.workspace_path.resolve()
        registered = self._registered_worktrees(repository)
        if registered.get(workspace) != binding.source_revision:
            raise RepositoryRealityError(
                "Attempt workspace does not match exact Source Baseline"
            )
        head = GitExactReality._git(workspace, "rev-parse", "HEAD")
        if head != binding.source_revision:
            raise RepositoryRealityError("Attempt workspace HEAD is not the Source Baseline")

    @classmethod
    def _validate_existing(
        cls,
        repository: Path,
        workspace: Path,
        source_revision: str,
    ) -> None:
        cls().validate_basis(
            WorkspaceBinding(
                workspace_identity="validation-only",
                workspace_path=workspace,
                repository_identity="validation-only",
                repository_path=repository,
                source_revision=source_revision,
            )
        )
        if GitExactReality._git(workspace, "status", "--porcelain"):
            raise RepositoryRealityError("Attempt workspace is no longer clean preparation reality")

    @staticmethod
    def _registered_worktrees(repository: Path) -> dict[Path, str]:
        output = GitExactReality._git(repository, "worktree", "list", "--porcelain")
        registered: dict[Path, str] = {}
        current_path: Path | None = None
        for line in output.splitlines():
            if line.startswith("worktree "):
                current_path = Path(line.removeprefix("worktree ")).resolve()
            elif line.startswith("HEAD ") and current_path is not None:
                registered[current_path] = line.removeprefix("HEAD ")
        return registered
