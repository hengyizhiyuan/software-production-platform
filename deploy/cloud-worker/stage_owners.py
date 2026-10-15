"""Stage the exact Guardian and ECF Owner sources pinned in owners.lock.

The Watt image is a three-project release unit: Watt source plus the exact
Owner sources it was qualified against. This script resolves each pinned
commit, verifies its canonical source digest, and writes it under
``<output>/<name>/src`` for the image build. It never moves an Owner branch.

    python deploy/cloud-worker/stage_owners.py --output build/owners [--repo-root guardian=PATH ...]
    python deploy/cloud-worker/stage_owners.py --digest PATH   # print digest of a src tree
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "owners.lock"


def tree_digest(src: Path) -> str:
    """Order- and platform-independent digest of every file under ``src``."""
    digest = hashlib.sha256()
    files = [p for p in src.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    for path in sorted(files, key=lambda p: p.relative_to(src).as_posix().encode()):
        digest.update(path.relative_to(src).as_posix().encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _archive(repo: str, commit: str) -> bytes:
    return subprocess.run(["git", "-c", "core.autocrlf=false", "-C", repo, "archive", "--format=tar", commit, "src"],
        check=True, stdout=subprocess.PIPE).stdout


def _fetch(url: str, commit: str, cache: Path) -> str:
    repo = cache / hashlib.sha256(url.encode()).hexdigest()[:16]
    if not (repo / "HEAD").exists():
        subprocess.run(["git", "init", "--bare", "-q", str(repo)], check=True)
    if subprocess.run(["git", "-C", str(repo), "cat-file", "-e", commit + "^{commit}"],
            stderr=subprocess.DEVNULL).returncode != 0:
        subprocess.run(["git", "-C", str(repo), "fetch", "-q", "--depth", "1", url, commit], check=True)
    return str(repo)


def stage(output: Path, local_roots: dict[str, str], cache: Path) -> dict:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    if output.exists():
        shutil.rmtree(output)
    staged = {}
    for name, entry in sorted(lock["owners"].items()):
        repo = local_roots.get(name) or _fetch(entry["repository"], entry["commit"], cache)
        target = output / name
        with tarfile.open(fileobj=io.BytesIO(_archive(repo, entry["commit"]))) as archive:
            for member in archive.getmembers():
                if member.issym() or member.islnk() or member.name.startswith("/") or ".." in Path(member.name).parts:
                    raise SystemExit(f"OWNER_ARCHIVE_UNSAFE_MEMBER {name} {member.name}")
            archive.extractall(target, filter="data")
        actual = tree_digest(target / "src")
        if actual != entry["source_digest"]:
            raise SystemExit(f"OWNER_SOURCE_DIGEST_MISMATCH {name} expected={entry['source_digest']} actual={actual}")
        (target / "OWNER_LOCK.json").write_text(json.dumps({"name": name, **entry}, indent=2) + "\n", encoding="utf-8")
        staged[name] = {"commit": entry["commit"], "source_digest": actual}
    return staged


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--digest", type=Path)
    parser.add_argument("--repo-root", action="append", default=[], help="name=PATH of a local clone")
    parser.add_argument("--cache", type=Path, default=ROOT / ".owner-cache")
    args = parser.parse_args()
    if args.digest:
        print(tree_digest(args.digest))
        return
    if not args.output:
        parser.error("--output or --digest is required")
    roots = dict(item.split("=", 1) for item in args.repo_root)
    args.cache.mkdir(parents=True, exist_ok=True)
    print(json.dumps(stage(args.output, roots, args.cache), indent=2))


if __name__ == "__main__":
    sys.exit(main())
