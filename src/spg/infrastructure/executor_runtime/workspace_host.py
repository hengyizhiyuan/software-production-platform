"""Private multi-source workspace materialization for native execution."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile

from spg.domain.native_execution import NativeExecutionConflict, SourceVector


class WorkspaceMaterializationError(RuntimeError):
    """Raised when an exact SourceVector cannot be materialized."""


class PrivateWorkspaceHost:
    """Materialize exact repository sources without sharing authoritative checkouts."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def materialize(self, workspace_identity: str, vector: SourceVector) -> Path:
        target = self._workspace_path(workspace_identity)
        if target.exists():
            raise NativeExecutionConflict("workspace identity already exists")
        temporary = Path(tempfile.mkdtemp(prefix=f".{workspace_identity}.", dir=self.root))
        try:
            for member in vector.members:
                relative = self._container_relative(member.container_path)
                destination = (temporary / relative).resolve()
                if temporary not in destination.parents:
                    raise WorkspaceMaterializationError("mount destination escapes workspace")
                destination.parent.mkdir(parents=True, exist_ok=True)
                self._git("clone", "--no-checkout", "--no-hardlinks", member.repository_identity, str(destination))
                self._git("-C", str(destination), "checkout", "--detach", member.source_commit_oid)
                commit = self._git("-C", str(destination), "rev-parse", "HEAD")
                tree = self._git("-C", str(destination), "rev-parse", "HEAD^{tree}")
                if commit != member.source_commit_oid or tree != member.source_tree_oid:
                    raise WorkspaceMaterializationError(
                        f"materialized source differs for mount {member.mount_id}"
                    )
            for asset in vector.non_repository_assets:
                relative = asset.get("workspace_path")
                if isinstance(relative, str):
                    path = self.resolve_path(temporary, relative)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    content = asset.get("content", "")
                    if not isinstance(content, str):
                        raise WorkspaceMaterializationError("inline asset content must be text")
                    path.write_text(content, encoding="utf-8")
            os.replace(temporary, target)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        return target

    def resolve_path(self, workspace: Path, relative: str) -> Path:
        if "\\" in relative:
            raise WorkspaceMaterializationError("workspace paths must use POSIX separators")
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
            raise WorkspaceMaterializationError("workspace path must be safe and relative")
        root = workspace.resolve()
        target = (root / Path(*path.parts)).resolve()
        if root not in target.parents:
            raise WorkspaceMaterializationError("workspace path escapes private root")
        return target

    def _workspace_path(self, identity: str) -> Path:
        if not identity or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in identity):
            raise ValueError("workspace identity contains unsupported characters")
        target = (self.root / identity).resolve()
        if target.parent != self.root:
            raise ValueError("workspace identity escapes configured root")
        return target

    @staticmethod
    def _container_relative(value: str) -> Path:
        parts = PurePosixPath(value).parts
        if len(parts) < 3 or parts[0] != "/" or parts[1] != "workspace":
            raise WorkspaceMaterializationError(
                "source mount must live below /workspace in the Executor container"
            )
        return Path(*parts[2:])

    @staticmethod
    def _git(*arguments: str) -> str:
        result = subprocess.run(
            ["git", *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={
                "PATH": os.environ.get("PATH", ""),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                "GIT_TERMINAL_PROMPT": "0",
                "LANG": "C.UTF-8",
            },
        )
        if result.returncode:
            raise WorkspaceMaterializationError(
                f"git command failed ({result.returncode}): {result.stderr.strip()}"
            )
        return result.stdout.strip()
