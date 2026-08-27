"""Independent exact-baseline Git/filesystem observation for S2-B."""

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path

from spg.domain.execution import (
    ArtifactChangeType,
    ObservedArtifactChange,
    ObservedRepositoryReality,
)
from spg.domain.preparation import WorkspaceBinding
from spg.domain.runtime import RepositoryRealityError
from spg.infrastructure.git_workspace import GitAttemptWorkspace, GitExactReality


class GitWorkspaceObserver:
    """Observe workspace facts independently from every Executor report."""

    def __init__(self, workspaces: GitAttemptWorkspace | None = None) -> None:
        self.workspaces = workspaces or GitAttemptWorkspace()

    def current_ref_revision(self, repository_path: Path, repository_ref: str) -> str:
        repository = GitExactReality._repository_root(repository_path)
        return GitExactReality._git(
            repository,
            "rev-parse",
            "--verify",
            f"{repository_ref}^{{commit}}",
        )

    def observe(
        self,
        workspace: WorkspaceBinding,
        *,
        repository_ref: str,
        expected_authoritative_ref_revision: str,
    ) -> ObservedRepositoryReality:
        self.workspaces.validate_basis(workspace)
        current_ref = self.current_ref_revision(
            workspace.repository_path,
            repository_ref,
        )
        if current_ref != expected_authoritative_ref_revision:
            raise RepositoryRealityError(
                "authoritative repository ref moved during Executor dispatch"
            )

        changes = self._changes(workspace.workspace_path, workspace.source_revision)
        fingerprint = self._fingerprint(
            {
                "repository_identity": workspace.repository_identity,
                "source_revision": workspace.source_revision,
                "workspace_identity": workspace.workspace_identity,
                "authoritative_ref_revision": current_ref,
                "changes": [item.model_dump(mode="json") for item in changes],
            }
        )
        return ObservedRepositoryReality(
            repository_identity=workspace.repository_identity,
            source_revision=workspace.source_revision,
            workspace_identity=workspace.workspace_identity,
            workspace_path=str(workspace.workspace_path),
            authoritative_ref_revision=current_ref,
            observed_at=datetime.now(UTC),
            changes=changes,
            observation_fingerprint=fingerprint,
        )

    @classmethod
    def _changes(
        cls,
        workspace: Path,
        source_revision: str,
    ) -> tuple[ObservedArtifactChange, ...]:
        raw = GitExactReality._run(
            workspace,
            "diff",
            "--name-status",
            "-z",
            "--no-renames",
            source_revision,
            "--",
        ).stdout
        tokens = raw.decode(errors="surrogateescape").split("\0")
        tracked: dict[str, ArtifactChangeType] = {}
        index = 0
        while index < len(tokens) and tokens[index]:
            status = tokens[index]
            if index + 1 >= len(tokens) or not tokens[index + 1]:
                raise RepositoryRealityError("Git returned an incomplete change manifest")
            path = tokens[index + 1]
            index += 2
            code = status[0]
            if code == "A":
                tracked[path] = ArtifactChangeType.ADDED
            elif code == "D":
                tracked[path] = ArtifactChangeType.DELETED
            elif code in {"M", "T"}:
                tracked[path] = ArtifactChangeType.MODIFIED
            else:
                raise RepositoryRealityError(
                    f"unsupported Git workspace status during observation: {status}"
                )

        untracked = GitExactReality._run(
            workspace,
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
        ).stdout.decode(errors="surrogateescape").split("\0")
        for path in untracked:
            if path:
                tracked[path] = ArtifactChangeType.ADDED

        observed: list[ObservedArtifactChange] = []
        for path, change_type in sorted(tracked.items()):
            source_fingerprint = None
            observed_fingerprint = None
            if change_type is not ArtifactChangeType.ADDED:
                source_fingerprint = GitExactReality._git(
                    workspace,
                    "rev-parse",
                    f"{source_revision}:{path}",
                )
            if change_type is not ArtifactChangeType.DELETED:
                observed_fingerprint = GitExactReality._git(
                    workspace,
                    "hash-object",
                    "--",
                    path,
                )
            observed.append(
                ObservedArtifactChange(
                    repository_relative_path=path,
                    change_type=change_type,
                    source_fingerprint=source_fingerprint,
                    observed_fingerprint=observed_fingerprint,
                )
            )
        return tuple(observed)

    @staticmethod
    def _fingerprint(value: object) -> str:
        canonical = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
        return sha256(canonical).hexdigest()
