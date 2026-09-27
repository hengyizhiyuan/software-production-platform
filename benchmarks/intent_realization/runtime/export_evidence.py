"""Archive qualification receipts without exporting runtime credentials.

Original receipts remain immutable locally. The manifest identifies both the
original bytes and exported bytes; credential redaction never rewrites history.
Build contexts, runtime configuration, caches and arbitrary scripts are excluded.
"""
import argparse
from datetime import UTC, datetime
from hashlib import sha256
import io
import json
from pathlib import Path
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, action="append", default=[])
    args = parser.parse_args()
    if args.destination.exists():
        raise SystemExit("Evidence archive identities are immutable")
    credentials = set()
    for path in args.env_file:
        for line in path.read_text().splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            key, value = line.split("=", 1)
            if any(marker in key.upper() for marker in ("TOKEN", "KEY", "PASSWORD", "SECRET")):
                value = value.strip().strip("\"'")
                if len(value) >= 12:
                    credentials.add(value.encode())
    args.destination.mkdir(parents=True)
    allowed = {".json", ".xml", ".log", ".md", ".txt", ".diff", ".png", ".html"}
    excluded = {"node_modules", "__pycache__", "fixture-sources", "fixture-checkouts"}
    manifest = []
    with tarfile.open(args.destination/"receipts.tar.gz", "w:gz") as archive:
        for path in sorted(args.source.rglob("*")):
            relative = path.relative_to(args.source)
            if (not path.is_file() or path.is_symlink() or path.suffix not in allowed
                    or any(part in excluded or part.startswith("build-context") for part in relative.parts)
                    or any(part in {"src", "migrations", "tests", ".git", ".venv"} for part in relative.parts)
                    or path.name.endswith(".env") or ".env." in path.name):
                continue
            original = path.read_bytes()
            exported = original
            if path.suffix != ".png":
                for credential in credentials:
                    exported = exported.replace(credential, b"[REDACTED_RUNTIME_CREDENTIAL]")
            info = tarfile.TarInfo(str(relative))
            info.size = len(exported)
            info.mode = 0o644
            info.mtime = int(path.stat().st_mtime)
            archive.addfile(info, io.BytesIO(exported))
            manifest.append({"local_path":str(path.resolve()),"archive_path":str(relative),
                "original_sha256":sha256(original).hexdigest(),
                "exported_sha256":sha256(exported).hexdigest(),"bytes":len(exported),
                "credential_redaction":original != exported})
    record = {"created_at":datetime.now(UTC).isoformat(),"files":manifest,
        "archive_sha256":sha256((args.destination/"receipts.tar.gz").read_bytes()).hexdigest(),
        "historical_receipts_rewritten":False,"credentials_exported":False}
    (args.destination/"manifest.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({"files":len(manifest),"archive_sha256":record["archive_sha256"],
        "archive_bytes":(args.destination/"receipts.tar.gz").stat().st_size}))


if __name__ == "__main__":
    main()
