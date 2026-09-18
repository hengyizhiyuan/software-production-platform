"""Content identity shared by dirty input capture and review Runtime evidence."""

from hashlib import sha256
import json
from pathlib import Path
import stat


def tree_fingerprint(source: Path, *, excluded_names: frozenset[str] = frozenset()) -> str:
    """Hash paths, bytes, sizes and modes; refuse links and unsupported files."""

    entries = []
    for path in sorted(source.rglob("*"), key=lambda value: value.as_posix()):
        relative = path.relative_to(source)
        if ".git" in relative.parts or any(part in excluded_names for part in relative.parts):
            continue
        details = path.lstat()
        if stat.S_ISDIR(details.st_mode):
            continue
        if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
            raise ValueError(f"content identity requires non-linked regular files: {relative}")
        data = path.read_bytes()
        entries.append({
            "path": relative.as_posix(),
            "digest": sha256(data).hexdigest(),
            "size": len(data),
            "mode": stat.S_IMODE(details.st_mode),
        })
    return sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
