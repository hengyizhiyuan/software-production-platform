"""Render the frozen continuity ledger without changing benchmark facts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median


def _checks(trial: dict) -> str:
    return "PASS" if all(item["returncode"] == 0 for item in trial["checks"]) else "FAIL"


def _fmt(value: float | None) -> str:
    return "UNKNOWN" if value is None else f"{value:.3f}"


def render(results: dict) -> str:
    trials = results["trials"]
    by_id = {item["execution_id"]: item for item in trials}
    lines = [
        "# Watt-native Executor Continuity Benchmark — Frozen Result",
        "",
        f"Plan digest: `{results['spec_digest']}`.",
        "",
        "The frozen run contains 18 A/B pairs and 36 executions. Failed trials remain in place. "
        "This report does not amend the frozen task set, verification commands, profiles, order, or rubric.",
        "",
        "## Gate result",
        "",
        f"- A: {sum(t['passed'] for t in trials if t['arm']=='A')}/18 PASS.",
        f"- B: {sum(t['passed'] for t in trials if t['arm']=='B')}/18 PASS.",
        f"- Total: {sum(t['passed'] for t in trials)}/36 PASS.",
        f"- Known Provider spend: RMB {results['actual_cost_rmb']:.8f}.",
        f"- Reserved uncertain spend: RMB {results['reserved_uncertain_cost_rmb']:.8f}.",
        f"- Conservative spend upper bound: RMB {results['actual_cost_rmb'] + results['reserved_uncertain_cost_rmb']:.8f} / RMB 100.",
        "- `CONTINUITY_QUALIFIED`: **NO**. All 18 B executions were required to pass; 10 failed.",
        "- Engineering-quality equivalence is not scoreable: the frozen spec contains category maxima but no scoring anchors. No post-output scoring rule was invented.",
        "",
        "## Execution outcomes",
        "",
        "| Execution | Type | Arm | Terminal | Frozen checks | Result | Requests known/unknown | Cost known/reserved (RMB) | Checkpoints | Duplicate request/effect digests | Injections consumed |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for trial in trials:
        provider = trial["provider_evidence"]
        runtime = trial["runtime_evidence"]
        continuity = trial["continuity_evidence"]
        lines.append(
            f"| {trial['execution_id']} | {trial['task_id']} | {trial['arm']} | "
            f"{trial['terminal_outcome']} | {_checks(trial)} | {'PASS' if trial['passed'] else 'FAIL'} | "
            f"{provider['completed_request_count']}/{provider['response_unknown_request_count']} | "
            f"{provider['known_cost_rmb']:.8f}/{provider['reserved_unknown_cost_rmb']:.8f} | "
            f"{runtime['checkpoint_count']} | "
            f"{continuity['duplicated_inference_request_digest_count']}/{continuity['duplicated_tool_effect_digest_count']} | "
            f"{', '.join(continuity['consumed_injections']) or 'none'} |"
        )
    lines += [
        "",
        "## Paired comparison",
        "",
        "| Pair | A | B | A/B checks | A/B known cost (RMB) | A/B elapsed seconds | B successors |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    overhead = []
    for task in ["T1", "T2", "T3", "T4", "T5", "T6"]:
        for repetition in range(1, 4):
            a = by_id[f"{task}-{repetition}-A"]
            b = by_id[f"{task}-{repetition}-B"]
            ae = a["continuity_evidence"]["elapsed_seconds"]
            be = b["continuity_evidence"]["elapsed_seconds"]
            if ae is not None and be is not None:
                overhead.append(be - ae)
            lines.append(
                f"| {task}-{repetition} | {'PASS' if a['passed'] else 'FAIL'} | {'PASS' if b['passed'] else 'FAIL'} | "
                f"{_checks(a)}/{_checks(b)} | {a['provider_evidence']['known_cost_rmb']:.8f}/{b['provider_evidence']['known_cost_rmb']:.8f} | "
                f"{_fmt(ae)}/{_fmt(be)} | {b['continuity_evidence']['successor_execution_count']} |"
            )
    lines += [
        "",
        "## Replacement executions",
        "",
        "| Execution | Task type | V4 Pro known requests | V4 Pro response-unknown requests | Outcome |",
        "|---|---|---:|---:|---|",
    ]
    type_by_task = {
        "T3": "constrained_refactor",
        "T4": "new_managed_repository_software",
        "T5": "coordinated_api_client_two_repositories",
    }
    for execution_id in ("T4-1-B", "T3-2-B", "T5-2-B"):
        trial = by_id[execution_id]
        known = sum(
            row.get("execution_id") == execution_id and row.get("model") == "deepseek-v4-pro"
            for row in results["provider_requests"]
        )
        unknown = sum(
            row.get("execution_id") == execution_id and row.get("model") == "deepseek-v4-pro"
            for row in results["pending_provider_requests"]
        )
        lines.append(
            f"| {execution_id} | {type_by_task[trial['task_id']]} | {known} | {unknown} | "
            f"{'PASS' if trial['passed'] else 'FAIL'} ({trial['terminal_outcome']}) |"
        )
    lines += [
        "",
        "## Qualification findings",
        "",
        "- All three preassigned replacement B executions created a `deepseek-v4-pro/high` successor and sent a real request across three task types.",
        "- Eight of 18 recovery-arm executions reached ResultReady and passed every frozen check. Ten B failures therefore fail the zero-tolerance outcome gate.",
        "- Every T5 run failed. The frozen combined pytest command imports two repositories that both define a top-level `tests` package; collection fails before executing either suite. The two suites pass when run independently, but the frozen command was retained unchanged.",
        "- Provider decisions were intermittently inadmissible after working output passed independent checks. These remain terminal failures; no failed real Provider request was automatically retried.",
        "- No benchmark execution recorded a Human technical intervention. Harness defects were repaired without changing task content or accepted outcomes, and their history remains in the ledger.",
        f"- Median raw B-minus-A elapsed difference across available pairs: {_fmt(median(overhead) if overhead else None)} seconds. Raw elapsed includes prescribed waits; detailed per-execution basis is in the JSON ledger.",
        "- Intent/constraint retention is evidenced only where frozen independent checks pass. A full independent criterion-to-output trace and blinded 0–4 scoring remain unavailable because the frozen contract omitted scoring anchors.",
        "",
        "Authoritative machine-readable evidence: `.spg/validation-evidence/native-cont/results.json` and `frozen-plan.json`.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    results = json.loads(Path(args.results).read_text())
    Path(args.output).write_text(render(results), encoding="utf-8")


if __name__ == "__main__":
    main()
