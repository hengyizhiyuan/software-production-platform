"""Retire a bounded batch of completed Golden Preview runtimes.

Only explicitly named qualification directories with final business/browser
evidence are eligible. Historical volumes, Work state and unrelated Docker
resources are untouched. Re-run the command to process the next batch.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--max-previews", type=int, default=8)
    args = parser.parse_args()
    if args.max_previews < 1 or args.max_previews > 32:
        raise SystemExit("max-previews must be between 1 and 32")
    root = args.root.resolve(strict=True)
    retired = []
    for latest in sorted(root.rglob("latest.json")):
        directory = latest.parent.resolve(strict=True)
        if (directory != root and root not in directory.parents) or len(retired) >= args.max_previews:
            continue
        if (directory / "runtime-retirement.json").exists():
            continue
        if not (directory / "result.json").exists() or not any(
            (directory / name).exists() for name in ("business-oracle.json", "browser-oracle.json")
        ):
            continue
        try:
            state = json.loads(latest.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            state = json.loads(latest.read_text(encoding="gbk"))
        session = state.get("preview", {}).get("session") or {}
        if session.get("status") not in {"READY", "FAILED"}:
            continue
        subprocess.run([sys.executable, str(Path(__file__).with_name("retire.py")),
            "--directory", str(directory)], check=True)
        retired.append(str(directory))
    print(json.dumps({"retired_count": len(retired), "retired_directories": retired,
        "batch_limit": args.max_previews}, ensure_ascii=False))


if __name__ == "__main__":
    main()
