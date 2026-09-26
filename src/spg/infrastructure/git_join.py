"""Exact Git tree composition for an explicit Integration/Join PWU.

This adapter only prepares the Join workspace. It never updates a repository
ref or decides that the resulting engineering Reality is verified.
"""

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import re
import subprocess

from spg.domain.runtime import RepositoryRealityError


_OBJECT_ID = re.compile(r"^[0-9a-f]{40,64}$")


@dataclass(frozen=True, slots=True)
class JoinTreeResult:
    input_revision: str
    parent_revisions: tuple[str, ...]
    candidate_tree: str
    strategy: str
    conflicts: tuple[str, ...]
    evidence_digest: str


class GitJoinReconciler:
    """Compose fixed-order verified parent commits into an isolated workspace."""

    @staticmethod
    def _run(repository: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["git", "-C", str(repository), *args], check=False,
            capture_output=True, env=env, timeout=30,
        )

    @classmethod
    def _required(cls, repository: Path, *args: str) -> str:
        result = cls._run(repository, *args)
        if result.returncode:
            raise RepositoryRealityError(result.stderr.decode(errors="replace") or "Git Join operation failed")
        return result.stdout.decode().strip()

    def reconcile(
        self, *, repository: Path, workspace: Path, input_revision: str,
        parent_revisions: tuple[str, ...], parent_trees: tuple[str, ...],
    ) -> JoinTreeResult:
        if len(parent_revisions) < 2 or len(parent_revisions) != len(parent_trees):
            raise RepositoryRealityError("Join requires multiple exact verified parents")
        if any(not _OBJECT_ID.fullmatch(item) for item in (input_revision, *parent_revisions, *parent_trees)):
            raise RepositoryRealityError("Join received a malformed Git object identity")
        if self._required(workspace, "rev-parse", "HEAD") != input_revision:
            raise RepositoryRealityError("Join workspace is not at its exact input baseline")
        for revision, tree in zip(parent_revisions, parent_trees):
            if self._required(repository, "rev-parse", f"{revision}^{{tree}}") != tree:
                raise RepositoryRealityError("verified parent commit/tree Reality changed")
        current = parent_revisions[0]
        conflicts: list[str] = []
        for index, following in enumerate(parent_revisions[1:], start=2):
            result = self._run(repository, "merge-tree", "--write-tree", current, following)
            lines = result.stdout.decode(errors="replace").splitlines()
            tree = lines[0].strip() if lines else ""
            if result.returncode not in (0, 1) or not _OBJECT_ID.fullmatch(tree):
                raise RepositoryRealityError(
                    result.stderr.decode(errors="replace") or "Join merge-tree failed"
                )
            if result.returncode == 1:
                conflicts.extend(line for line in lines[1:] if line.strip())
            if index == len(parent_revisions):
                final_tree = tree
                break
            environment = dict(os.environ)
            environment.update({
                "GIT_AUTHOR_NAME": "SPG Join", "GIT_AUTHOR_EMAIL": "spg-join@example.invalid",
                "GIT_COMMITTER_NAME": "SPG Join", "GIT_COMMITTER_EMAIL": "spg-join@example.invalid",
                "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
                "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
            })
            synthetic = self._run(
                repository, "commit-tree", tree, "-p", current, "-p", following,
                env=environment,
            )
            if synthetic.returncode:
                raise RepositoryRealityError("Join could not preserve intermediate parent lineage")
            current = synthetic.stdout.decode().strip()
        assert _OBJECT_ID.fullmatch(final_tree)
        index_tree = self._required(workspace, "write-tree")
        if index_tree == final_tree:
            # Restart after a crash between Git effect and persistence: the
            # deterministic result is already present, so record it once.
            pass
        elif index_tree == self._required(workspace, "rev-parse", f"{input_revision}^{{tree}}"):
            self._required(workspace, "read-tree", "--reset", "-u", final_tree)
        else:
            raise RepositoryRealityError("Join workspace changed before reconciliation could be recorded")
        if self._required(workspace, "write-tree") != final_tree:
            raise RepositoryRealityError("Join workspace tree differs from deterministic composition")
        evidence = "|".join((input_revision, *parent_revisions, *parent_trees, final_tree, *conflicts))
        return JoinTreeResult(
            input_revision=input_revision, parent_revisions=parent_revisions,
            candidate_tree=final_tree,
            strategy="GIT_MERGE_TREE_WITH_VERIFICATION_REQUIRED",
            conflicts=tuple(conflicts),
            evidence_digest=sha256(evidence.encode()).hexdigest(),
        )
