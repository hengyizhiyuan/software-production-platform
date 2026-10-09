"""Verify public delivery hashes and known-secret absence; never print values."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-dir", required=True)
    parser.add_argument("--private-env", action="append", default=[])
    args = parser.parse_args()
    root = Path(args.public_dir).resolve()
    manifest = json.loads((root / "public-file-manifest.json").read_text(encoding="utf-8"))
    expected = {row["path"]: row for row in manifest["files"]}
    actual = {str(p.relative_to(root)).replace("\\", "/"): p for p in root.rglob("*") if p.is_file()}
    if set(actual) != set(expected) | {"public-file-manifest.json"}:
        raise SystemExit("PUBLIC_DELIVERY_FILE_SET_MISMATCH")
    secret_values = set()
    for env_path in args.private_env:
        path = Path(env_path)
        if not path.is_file():
            raise SystemExit("PRIVATE_SCAN_INPUT_MISSING")
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if any(marker in key.upper() for marker in ("PASSWORD", "TOKEN", "API_KEY", "SECRET")):
                value = value.strip().strip("\"'")
                if len(value) >= 8:
                    secret_values.add(value.encode("utf-8"))
    total = 0
    for name, path in sorted(actual.items()):
        if path.is_symlink() or "private" in path.relative_to(root).parts or path.suffix == ".env":
            raise SystemExit("PUBLIC_DELIVERY_PRIVATE_OR_SYMLINK_INPUT")
        data = path.read_bytes()
        if any(value in data for value in secret_values):
            raise SystemExit("PUBLIC_DELIVERY_KNOWN_SECRET_MATCH")
        total += len(data)
        if name in expected:
            row = expected[name]
            if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise SystemExit("PUBLIC_DELIVERY_ARTIFACT_HASH_MISMATCH")
    print(json.dumps({
        "status": "PASS", "file_count": len(actual), "bytes": total,
        "hash_integrity": "PASS", "known_secret_literal_scan": "PASS",
        "private_env_input_count": len(args.private_env),
        "limits": "Only known secret literals checked; not a universal semantic privacy proof.",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
