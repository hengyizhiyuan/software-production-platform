"""Retire bounded, completed synthetic holdout Previews without deleting volumes.

The live holdout runner can finish an action case before its background Work
creates a Preview. This command may be rerun between batches: it reads the
durable Preview session from the owner, requires a completed PASS result for
the exact Work, and delegates label-checked Docker cleanup to ``retire.py``.
It never changes Work, Candidate, database rows, or source volumes.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from uuid import UUID


def owner_previews(container: str, store_root: str, work_ids: list[str]) -> dict[str, dict]:
    code = """
import json, pathlib, sys
root = pathlib.Path(sys.argv[1]) / 'candidate-previews'
sessions = {}
for work_id in sys.argv[2:]:
    pointer = root / 'by-work' / (work_id + '.json')
    if not pointer.exists():
        continue
    identity = json.loads(pointer.read_text())['id']
    session = root / 'sessions' / identity / 'current.json'
    if session.exists():
        sessions[work_id] = json.loads(session.read_text())
print(json.dumps(sessions))
"""
    completed = subprocess.run(["docker", "exec", container, "python", "-c", code,
        store_root, *work_ids], capture_output=True, text=True, check=True, timeout=30)
    return json.loads(completed.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--owner-container", required=True)
    parser.add_argument("--store-root", default="/var/lib/spg/production-environments")
    parser.add_argument("--max-previews", type=int, default=4)
    parser.add_argument("--min-age-seconds", type=int, default=120)
    args = parser.parse_args()
    if not 1 <= args.max_previews <= 32 or args.min_age_seconds < 0:
        raise SystemExit("Expected 1..32 previews and a nonnegative minimum age")
    root = args.root.resolve(strict=True)
    if not (root / "plan.json").is_file():
        raise SystemExit("The synthetic cohort has no immutable qualification plan")
    planned_cases = set(json.loads((root / "plan.json").read_text(encoding="utf-8"))["case_ids"])
    candidates = []
    for directory in sorted(p for p in root.iterdir() if p.is_dir()):
        if directory.resolve(strict=True).parent != root or directory.name not in planned_cases:
            continue
        if any((directory / "retirement-preview").glob("*/runtime-retirement.json")):
            continue
        result_path = directory / "result.json"
        if not result_path.is_file():
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("status") != "PASS":
            continue
        # Review and delivery cases keep their Candidate Work under
        # setup_work_id; their final Turn has no new production Work.
        result_work_id = result.get("work_id") or result.get("setup_work_id")
        if not result_work_id:
            continue
        work_id = str(UUID(result_work_id))
        candidates.append((directory, result_path, result, work_id))
    sessions = owner_previews(args.owner_container, args.store_root,
        [work_id for _, _, _, work_id in candidates]) if candidates else {}
    retired: list[str] = []
    for directory, result_path, result, work_id in candidates:
        if len(retired) >= args.max_previews:
            break
        session = sessions.get(work_id)
        if not session or session.get("work_id") != work_id or session.get("status") != "READY":
            continue
        preview_id = str(UUID(session["id"]))
        updated_at = datetime.fromisoformat(session["updated_at"].replace("Z", "+00:00"))
        if datetime.now(UTC) - updated_at < timedelta(seconds=args.min_age_seconds):
            continue
        evidence = directory / "retirement-preview" / preview_id
        if (evidence / "runtime-retirement.json").exists():
            continue
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "latest.json").write_text(json.dumps({"preview": {"session": {
            "id": preview_id, "work_id": work_id, "status": "READY"}}},
            ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (evidence / "origin.json").write_text(json.dumps({
            "completed_result": str(result_path.resolve(strict=True)),
            "completed_result_sha256": sha256(result_path.read_bytes()).hexdigest(),
            "result_status": result["status"], "work_id": work_id,
            "preview_id": preview_id, "owner_container": args.owner_container,
            "owner_session_sha256": sha256(json.dumps(session, sort_keys=True).encode()).hexdigest(),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        subprocess.run([sys.executable, str(Path(__file__).with_name("retire.py")),
            "--directory", str(evidence)], check=True)
        retired.append(preview_id)
    print(json.dumps({"retired_count": len(retired), "preview_ids": retired,
        "batch_limit": args.max_previews, "volumes_preserved": True}))


if __name__ == "__main__":
    main()
