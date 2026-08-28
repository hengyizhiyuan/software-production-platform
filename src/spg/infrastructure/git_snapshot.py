"""Non-authoritative exact Git snapshot construction for S3-B."""

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import subprocess
import tempfile

from spg.domain.execution import ArtifactChangeType, ObservedArtifactChange
from spg.domain.preparation import WorkspaceBinding
from spg.domain.runtime import RepositoryRealityError
from spg.infrastructure.git_workspace import GitExactReality


@dataclass(frozen=True, slots=True)
class ProposedGitSnapshot:
    proposed_commit_identity: str
    tree_identity: str
    authoritative_ref_revision: str


class GitProposedSnapshotBuilder:
    """Create detached commit/tree objects without updating any Git ref."""

    def create(
        self,
        workspace: WorkspaceBinding,
        *,
        repository_ref: str,
        expected_authoritative_ref_revision: str,
        expected_changes: tuple[ObservedArtifactChange, ...],
        created_at: datetime,
    ) -> ProposedGitSnapshot:
        repository = GitExactReality._repository_root(workspace.repository_path)
        before = self.current_ref_revision(repository, repository_ref)
        if before != expected_authoritative_ref_revision:
            raise RepositoryRealityError(
                "authoritative repository ref moved before proposed snapshot creation"
            )

        descriptor, index_name = tempfile.mkstemp(prefix="spg-proposed-index-")
        os.close(descriptor)
        Path(index_name).unlink()
        environment = os.environ.copy()
        environment["GIT_INDEX_FILE"] = index_name
        try:
            self._run(workspace.workspace_path, "read-tree", workspace.source_revision, env=environment)
            self._run(workspace.workspace_path, "add", "-A", "--", env=environment)
            tree_identity = self._run(
                workspace.workspace_path,
                "write-tree",
                env=environment,
            ).stdout.decode().strip()
            commit_environment = dict(environment)
            timestamp = created_at.isoformat()
            commit_environment.update(
                {
                    "GIT_AUTHOR_NAME": "SPG Runtime",
                    "GIT_AUTHOR_EMAIL": "spg-runtime@example.invalid",
                    "GIT_AUTHOR_DATE": timestamp,
                    "GIT_COMMITTER_NAME": "SPG Runtime",
                    "GIT_COMMITTER_EMAIL": "spg-runtime@example.invalid",
                    "GIT_COMMITTER_DATE": timestamp,
                }
            )
            commit_identity = self._run(
                workspace.workspace_path,
                "commit-tree",
                tree_identity,
                "-p",
                workspace.source_revision,
                env=commit_environment,
                input_data=b"SPG proposed repository snapshot\n",
            ).stdout.decode().strip()
        finally:
            Path(index_name).unlink(missing_ok=True)

        actual_tree = GitExactReality._git(
            repository,
            "rev-parse",
            f"{commit_identity}^{{tree}}",
        )
        if actual_tree != tree_identity:
            raise RepositoryRealityError("proposed commit/tree identity mismatch")
        actual_changes = self._commit_changes(
            repository,
            workspace.source_revision,
            commit_identity,
        )
        if actual_changes != expected_changes:
            raise RepositoryRealityError(
                "proposed snapshot does not match accepted Repository Observation"
            )
        after = self.current_ref_revision(repository, repository_ref)
        if after != before:
            raise RepositoryRealityError(
                "authoritative repository ref moved during proposed snapshot creation"
            )
        return ProposedGitSnapshot(
            proposed_commit_identity=commit_identity,
            tree_identity=tree_identity,
            authoritative_ref_revision=after,
        )

    def validate(
        self,
        repository_path: Path,
        *,
        repository_ref: str,
        expected_authoritative_ref_revision: str,
        proposed_commit_identity: str,
        tree_identity: str,
    ) -> None:
        repository = GitExactReality._repository_root(repository_path)
        GitExactReality._git(
            repository,
            "cat-file",
            "-e",
            f"{proposed_commit_identity}^{{commit}}",
        )
        actual_tree = GitExactReality._git(
            repository,
            "rev-parse",
            f"{proposed_commit_identity}^{{tree}}",
        )
        if actual_tree != tree_identity:
            raise RepositoryRealityError("stored proposed snapshot tree changed")
        if self.current_ref_revision(repository, repository_ref) != expected_authoritative_ref_revision:
            raise RepositoryRealityError("authoritative repository ref moved")

    @staticmethod
    def current_ref_revision(repository_path: Path, repository_ref: str) -> str:
        return GitExactReality._git(
            repository_path,
            "rev-parse",
            "--verify",
            f"{repository_ref}^{{commit}}",
        )

    @classmethod
    def _commit_changes(
        cls,
        repository: Path,
        source_revision: str,
        proposed_commit_identity: str,
    ) -> tuple[ObservedArtifactChange, ...]:
        raw = cls._run(
            repository,
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            "-z",
            "--no-renames",
            source_revision,
            proposed_commit_identity,
            "--",
        ).stdout
        tokens = raw.decode(errors="surrogateescape").split("\0")
        changes: list[ObservedArtifactChange] = []
        index = 0
        while index < len(tokens) and tokens[index]:
            status = tokens[index]
            path = tokens[index + 1]
            index += 2
            code = status[0]
            if code == "A":
                change_type = ArtifactChangeType.ADDED
            elif code == "D":
                change_type = ArtifactChangeType.DELETED
            elif code in {"M", "T"}:
                change_type = ArtifactChangeType.MODIFIED
            else:
                raise RepositoryRealityError(
                    f"unsupported proposed snapshot status: {status}"
                )
            source_fingerprint = None
            observed_fingerprint = None
            if change_type is not ArtifactChangeType.ADDED:
                source_fingerprint = GitExactReality._git(
                    repository,
                    "rev-parse",
                    f"{source_revision}:{path}",
                )
            if change_type is not ArtifactChangeType.DELETED:
                observed_fingerprint = GitExactReality._git(
                    repository,
                    "rev-parse",
                    f"{proposed_commit_identity}:{path}",
                )
            changes.append(
                ObservedArtifactChange(
                    repository_relative_path=path,
                    change_type=change_type,
                    source_fingerprint=source_fingerprint,
                    observed_fingerprint=observed_fingerprint,
                )
            )
        return tuple(sorted(changes, key=lambda item: item.repository_relative_path))

    @staticmethod
    def _run(
        repository: Path,
        *arguments: str,
        env: dict[str, str] | None = None,
        input_data: bytes | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
            env=env,
            input=input_data,
        )
        if result.returncode != 0:
            message = result.stderr.decode(errors="replace").strip() or "Git snapshot operation failed"
            raise RepositoryRealityError(message)
        return result
