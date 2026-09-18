"""Content-addressed local storage for checkpoint and evidence payloads."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
import tempfile
from threading import Lock
from typing import Any
from uuid import UUID

from spg.infrastructure.content_identity import tree_fingerprint


class ContentAddressedStorage:
    """Write immutable UTF-8 JSON blobs atomically under a bounded root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put_json(self, namespace: str, value: Any) -> tuple[str, Path]:
        data = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        digest = sha256(data).hexdigest()
        target = self._target(namespace, digest)
        if target.exists():
            if target.read_bytes() != data:
                raise RuntimeError("content-address collision")
            return digest, target
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            dir=target.parent,
            prefix=f".{digest}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return digest, target

    def get_json(self, namespace: str, digest: str) -> Any:
        target = self._target(namespace, digest)
        data = target.read_bytes()
        if sha256(data).hexdigest() != digest:
            raise RuntimeError("stored content digest differs")
        return json.loads(data.decode("utf-8"))

    def _target(self, namespace: str, digest: str) -> Path:
        if not namespace or any(part in {"", ".", ".."} for part in namespace.split("/")):
            raise ValueError("storage namespace must be bounded and relative")
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("invalid content digest")
        target = (self.root / namespace / digest[:2] / f"{digest}.json").resolve()
        if self.root not in target.parents:
            raise ValueError("storage target escapes configured root")
        return target


class DeliveryReceiptSpool:
    """Durable Tool Host receipts, independent of application database health."""

    def __init__(self, root: Path, *, max_bytes: int = 128 * 1024 * 1024) -> None:
        if max_bytes < 1024:
            raise ValueError("receipt spool capacity is too small")
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        self._lock = Lock()

    def ensure_capacity(self, *, reserve_bytes: int = 128 * 1024) -> None:
        """Reject new effects before launch when a bounded receipt cannot be retained."""

        if reserve_bytes < 1:
            raise ValueError("receipt reserve must be positive")
        with self._lock:
            if self._used_bytes() + reserve_bytes > self.max_bytes:
                raise OSError(28, "Tool receipt spool capacity exhausted")

    def get(self, delivery_id: UUID) -> dict[str, Any] | None:
        target = self._target(delivery_id)
        if not target.exists():
            return None
        payload = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError("Tool receipt spool record is not an object")
        return payload

    def put(
        self,
        delivery_id: UUID,
        *,
        request_digest: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "delivery_id": str(delivery_id),
            "request_digest": request_digest,
            "result": result,
        }
        data = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        target = self._target(delivery_id)
        if target.exists():
            existing = self.get(delivery_id)
            if existing != payload:
                raise RuntimeError("delivery identity has different durable meaning")
            return payload
        with self._lock:
            if target.exists():
                existing = self.get(delivery_id)
                if existing != payload:
                    raise RuntimeError("delivery identity has different durable meaning")
                return payload
            if self._used_bytes() + len(data) > self.max_bytes:
                raise OSError(28, "Tool receipt spool capacity exhausted")
            target.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(
                dir=target.parent, prefix=f".{delivery_id}.", suffix=".tmp"
            )
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, target)
                directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        return payload

    def _used_bytes(self) -> int:
        return sum(
            path.stat().st_size for path in self.root.glob("*/*.json") if path.is_file()
        )

    def _target(self, delivery_id: UUID) -> Path:
        value = str(delivery_id)
        target = (self.root / value[:2] / f"{value}.json").resolve()
        if self.root not in target.parents:
            raise ValueError("receipt spool target escapes configured root")
        return target


class WorkspaceArchiveStore:
    """Create and restore deterministic, verified workspace archives."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def archive(self, workspace: Path) -> tuple[str, Path]:
        source = workspace.resolve()
        if workspace.is_symlink() or not source.is_dir():
            raise RuntimeError("workspace archive source must be a real directory")
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.root, prefix=".workspace.", suffix=".tar"
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            with tarfile.open(temporary, "w", format=tarfile.PAX_FORMAT) as archive:
                for path in sorted(source.rglob("*"), key=lambda item: item.as_posix()):
                    relative = path.relative_to(source)
                    details = path.lstat()
                    if stat.S_ISLNK(details.st_mode) or not (
                        stat.S_ISDIR(details.st_mode) or stat.S_ISREG(details.st_mode)
                    ):
                        raise RuntimeError("workspace archive refuses links and special files")
                    if stat.S_ISREG(details.st_mode) and details.st_nlink != 1:
                        raise RuntimeError("workspace archive refuses hard-linked files")
                    info = tarfile.TarInfo(relative.as_posix())
                    info.mode = stat.S_IMODE(details.st_mode)
                    info.mtime = 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    if stat.S_ISDIR(details.st_mode):
                        info.type = tarfile.DIRTYPE
                        archive.addfile(info)
                    else:
                        info.size = details.st_size
                        with path.open("rb") as stream:
                            archive.addfile(info, stream)
            with temporary.open("rb") as stream:
                os.fsync(stream.fileno())
            digest = sha256(temporary.read_bytes()).hexdigest()
            target = self.root / digest[:2] / f"{digest}.tar"
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if sha256(target.read_bytes()).hexdigest() != digest:
                    raise RuntimeError("workspace archive digest collision")
                temporary.unlink()
            else:
                os.replace(temporary, target)
                directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            self.verify(digest, target)
            return digest, target
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def verify(digest: str, path: Path) -> None:
        if sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError("workspace archive digest differs")
        with tarfile.open(path, "r") as archive:
            for member in archive.getmembers():
                parts = Path(member.name).parts
                if (
                    not parts
                    or Path(member.name).is_absolute()
                    or ".." in parts
                    or not (member.isdir() or member.isreg())
                ):
                    raise RuntimeError("workspace archive contains an unsafe member")

    def restore(self, digest: str, destination: Path) -> None:
        archive_path = self.root / digest[:2] / f"{digest}.tar"
        self.verify(digest, archive_path)
        if destination.exists():
            raise RuntimeError("workspace restore destination already exists")
        destination.mkdir(parents=True)
        try:
            with tarfile.open(archive_path, "r") as archive:
                for member in archive.getmembers():
                    target = destination.joinpath(*Path(member.name).parts)
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                        target.chmod(member.mode)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        stream = archive.extractfile(member)
                        if stream is None:
                            raise RuntimeError("workspace archive member has no payload")
                        with target.open("xb") as output:
                            shutil.copyfileobj(stream, output)
                        target.chmod(member.mode)
        except Exception:
            shutil.rmtree(destination, ignore_errors=True)
            raise


class DirtyInputOverlayStore:
    """Capture explicit dirty Git input without mutating the Human source tree."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.archives = WorkspaceArchiveStore(self.root / "archives")
        self.manifests = ContentAddressedStorage(self.root / "manifests")

    def capture(
        self,
        source: Path,
        *,
        excluded_cache_recipes: dict[str, str] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        source = source.resolve()
        if not (source / ".git").exists():
            raise ValueError("dirty input capture requires a Git working tree")
        exclusions = excluded_cache_recipes or {}
        if any(not path or not recipe for path, recipe in exclusions.items()):
            raise ValueError("excluded caches require a path and recreation recipe")
        before = self._tree_fingerprint(source)
        tracked_changes = set(self._git_paths(source, "diff", "--name-only", "-z"))
        tracked_changes.update(
            self._git_paths(source, "diff", "--cached", "--name-only", "-z")
        )
        untracked = set(
            self._git_paths(source, "ls-files", "--others", "--exclude-standard", "-z")
        )
        ignored = set(
            self._git_paths(
                source, "ls-files", "--others", "--ignored", "--exclude-standard", "-z"
            )
        )
        categories = {
            **{path: "TRACKED_CHANGE" for path in tracked_changes},
            **{path: "UNTRACKED" for path in untracked},
            **{path: "IGNORED_USEFUL" for path in ignored},
        }
        staging = Path(tempfile.mkdtemp(dir=self.root, prefix=".overlay."))
        entries: list[dict[str, Any]] = []
        try:
            for relative in sorted(categories):
                if self._excluded(relative, exclusions):
                    continue
                path = source / relative
                if not path.exists():
                    entries.append({
                        "path": relative,
                        "category": "TRACKED_DELETION",
                        "type": "ABSENT",
                        "digest": None,
                        "size": 0,
                        "mode": None,
                    })
                    continue
                details = path.lstat()
                if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
                    raise RuntimeError(
                        "dirty input overlays accept only non-linked regular files"
                    )
                data = path.read_bytes()
                target = staging / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                target.chmod(stat.S_IMODE(details.st_mode))
                entries.append({
                    "path": relative,
                    "category": categories[relative],
                    "type": "FILE",
                    "digest": sha256(data).hexdigest(),
                    "size": len(data),
                    "mode": stat.S_IMODE(details.st_mode),
                })
            archive_digest, archive_path = self.archives.archive(staging)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        after = self._tree_fingerprint(source)
        if before != after:
            raise RuntimeError("dirty input capture mutated the Human source tree")
        manifest = {
            "schema_version": 1,
            "source_path": str(source),
            "source_fingerprint": before,
            "archive_digest": archive_digest,
            "archive_path": str(archive_path),
            "entries": entries,
            "excluded_caches": [
                {"path": path, "recreation_recipe": recipe}
                for path, recipe in sorted(exclusions.items())
            ],
        }
        reference, _ = self.manifests.put_json("input-overlays", manifest)
        return reference, manifest

    def restore(self, reference: str, destination: Path) -> dict[str, Any]:
        manifest = self.manifests.get_json("input-overlays", reference)
        self.archives.restore(manifest["archive_digest"], destination)
        for entry in manifest["entries"]:
            path = destination / entry["path"]
            if entry["type"] == "ABSENT":
                if path.exists():
                    raise RuntimeError("restored overlay invented a deleted input")
                continue
            if sha256(path.read_bytes()).hexdigest() != entry["digest"]:
                raise RuntimeError("restored dirty input digest differs")
        return manifest

    @staticmethod
    def _git_paths(source: Path, *arguments: str) -> tuple[str, ...]:
        result = subprocess.run(
            ["git", "-C", str(source), *arguments],
            check=True,
            capture_output=True,
        )
        return tuple(
            value.decode("utf-8", errors="surrogateescape")
            for value in result.stdout.split(b"\0")
            if value
        )

    @staticmethod
    def _excluded(relative: str, exclusions: dict[str, str]) -> bool:
        path = Path(relative)
        return any(path == Path(root) or Path(root) in path.parents for root in exclusions)

    @staticmethod
    def _tree_fingerprint(source: Path) -> str:
        return tree_fingerprint(source)
