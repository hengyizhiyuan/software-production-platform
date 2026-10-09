"""Validate and package this public evidence only; no Runtime/model execution."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    archive = Path(args.archive).resolve()
    if archive.exists():
        raise SystemExit("PUBLIC_ARCHIVE_ALREADY_EXISTS")
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "public-file-manifest.json":
            continue
        relative = path.relative_to(root)
        if path.is_symlink() or "private" in relative.parts or path.suffix == ".env":
            raise SystemExit("PRIVATE_INPUT_REJECTED")
        data = path.read_bytes()
        if path.suffix == ".json":
            json.loads(data)
        if path.suffix == ".py":
            ast.parse(data.decode("utf-8"), filename=str(relative))
        rows.append({"path": relative.as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "branch": "codex/c3-open-semantic-obligation-convergence",
        "application_source": "e0df8196cb51480f542af13b40cfa77fca6b6a6e",
        "application_tree": "d479d61f5fcac075a5af3a274f60cbe3f6e9f53f",
        "actual_image_id": "sha256:7a4ac00e3599bda2dbcebe46b15dd0b45f3be86552021023ebd288eb732f7b35",
        "status": "C3 PARTIAL; controlled mechanisms qualified; no live model calls",
        "manifest_self_hash": "EXCLUDED_TO_AVOID_SELF_REFERENCE",
        "files": rows,
    }
    (root / "public-file-manifest.json").write_bytes((json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(str(archive), "w:gz") as output:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                output.add(str(path), arcname=root.name + "/" + path.relative_to(root).as_posix(), recursive=False)
    data = archive.read_bytes()
    print(json.dumps({"status": "PREPARED", "archive": str(archive), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "manifest_artifacts": len(rows), "json_python_syntax": "PASS"}, sort_keys=True))


if __name__ == "__main__":
    main()
