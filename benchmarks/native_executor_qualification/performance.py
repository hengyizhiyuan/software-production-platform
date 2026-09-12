"""Measure 30 cold and 30 warm container actions for Q48."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import time
from uuid import uuid4


ACTION = (
    "from spg.domain.native_execution import WorkingPlan; "
    "WorkingPlan(version=1,objective_reference='q48',"
    "chosen_approach='load exact runtime',approach_rationale='qualification'); "
    "print('MEANINGFUL_ACTION_READY',flush=True)"
)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(max(int((len(ordered) - 1) * fraction), 0), len(ordered) - 1)
    return ordered[index]


def timed(command: list[str]) -> dict[str, float]:
    started = time.monotonic()
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    assert process.stdout is not None
    first = process.stdout.readline().strip()
    first_at = time.monotonic()
    stderr = process.stderr.read() if process.stderr else ""
    returncode = process.wait()
    finished = time.monotonic()
    if returncode or first != "MEANINGFUL_ACTION_READY":
        raise RuntimeError(
            f"Q48 action failed rc={returncode} marker={first!r} stderr={stderr[-300:]}"
        )
    return {
        "first_meaningful_action_seconds": first_at - started,
        "total_seconds": finished - started,
    }


def summary(samples: list[dict[str, float]]) -> dict[str, object]:
    first = [item["first_meaningful_action_seconds"] for item in samples]
    total = [item["total_seconds"] for item in samples]
    return {
        "count": len(samples),
        "first_meaningful_action_seconds": {
            "p50": round(percentile(first, 0.50), 6),
            "p95": round(percentile(first, 0.95), 6),
            "min": round(min(first), 6),
            "max": round(max(first), 6),
        },
        "total_seconds": {
            "p50": round(percentile(total, 0.50), 6),
            "p95": round(percentile(total, 0.95), 6),
            "min": round(min(total), 6),
            "max": round(max(total), 6),
        },
        "samples": [{key: round(value, 6) for key, value in item.items()} for item in samples],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repetitions", type=int, default=30)
    args = parser.parse_args()
    if args.repetitions < 30:
        raise ValueError("Q48 requires at least 30 repetitions")
    source = str(Path(args.source).resolve())
    constraints = ["--cpus=2", "--memory=4g", "--network=none", "--read-only", "--tmpfs=/tmp"]
    mount = ["-v", f"{source}:/acceptance-source:ro", "-e", "PYTHONPATH=/acceptance-source"]
    action = ["python", "-c", ACTION]
    cold = [timed(["docker", "run", "--rm", *constraints, *mount, args.image, *action]) for _ in range(args.repetitions)]
    name = f"watt-q48-warm-{uuid4().hex[:10]}"
    subprocess.run([
        "docker", "run", "-d", "--name", name, *constraints, *mount,
        args.image, "python", "-c", "import time; time.sleep(900)",
    ], check=True, capture_output=True, text=True)
    try:
        warm = [timed(["docker", "exec", name, *action]) for _ in range(args.repetitions)]
    finally:
        subprocess.run(["docker", "rm", "-f", name], check=False, capture_output=True)
    inspect = subprocess.run(
        ["docker", "image", "inspect", args.image, "--format", "{{.Id}} {{.Created}}"],
        check=True, capture_output=True, text=True,
    ).stdout.strip().split(maxsplit=1)
    result = {
        "schema_version": 1,
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "fixture": {
            "action": "import the current native domain and construct a validated WorkingPlan",
            "source": source,
            "profile": "2 vCPU / 4 GiB / network none / read-only image / tmpfs scratch",
            "image_id": inspect[0],
            "image_created": inspect[1] if len(inspect) > 1 else None,
            "database": "not used by this container setup measurement",
        },
        "host": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "logical_cpu_count": os.cpu_count(),
            "docker_version": subprocess.run(
                ["docker", "version", "--format", "{{.Server.Version}}"],
                check=True, capture_output=True, text=True,
            ).stdout.strip(),
        },
        "cold": summary(cold),
        "warm": summary(warm),
    }
    cold_p50=result["cold"]["first_meaningful_action_seconds"]["p50"]
    warm_p50=result["warm"]["first_meaningful_action_seconds"]["p50"]
    result["warm_vs_cold_first_action_change_percent"] = round(
        ((warm_p50 - cold_p50) / cold_p50) * 100, 3,)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "cold_p50":cold_p50,
        "cold_p95":result["cold"]["first_meaningful_action_seconds"]["p95"],
        "warm_p50":warm_p50,
        "warm_p95":result["warm"]["first_meaningful_action_seconds"]["p95"],
        "change_percent":result["warm_vs_cold_first_action_change_percent"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
