"""Content-addressed local storage for checkpoint and evidence payloads."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any


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
