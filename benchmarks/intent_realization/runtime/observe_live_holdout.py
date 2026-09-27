"""Reconcile late owner results without resubmitting or rewriting live trials.

The original submission deadline failures remain failures. This separate receipt
measures eventual effects and distinguishes queue delay from semantic failure.
Known read-only Git observations of wrong targets count as erroneous execution,
even when the original obligation correctly refused to report success.
"""
import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import time

from benchmarks.golden.runtime.journey import ProductClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--base", default="http://127.0.0.1:8078")
    parser.add_argument("--wait-seconds", type=int, default=1800)
    args = parser.parse_args()
    output = args.directory/"eventual-owner-observation"
    if output.exists():
        raise SystemExit("Owner observation identity is immutable")
    output.mkdir()
    env = dict(line.split("=",1) for line in args.env_file.read_text().splitlines() if "=" in line)
    client = ProductClient(args.base,env["SPG_OPERATOR_TOKEN"])
    cases = {c["id"]:c for c in json.loads(args.corpus.read_text())["cases"]}
    plan = json.loads((args.directory/"plan.json").read_text())
    pending = set(plan["case_ids"])
    results = []
    deadline = time.monotonic()+args.wait_seconds
    while pending and time.monotonic()<deadline:
        for identity in sorted(tuple(pending)):
            source = args.directory/identity
            if not (source/"result.json").exists():
                continue
            original = json.loads((source/"result.json").read_text())
            if not (source/"unseen-submission.json").exists() or not (source/"before.json").exists():
                results.append({"case_id":identity,"status":"SETUP_FAILED","effect_observed":False})
                pending.remove(identity)
                continue
            submitted = json.loads((source/"unseen-submission.json").read_text())
            state = client.request("/api/interactions/"+original["interaction_id"])
            turn = next((t for t in state.get("turns",[]) if t["turn_id"]==submitted["turn_id"]),None)
            if not turn or turn["status"] not in {"COMPLETED","FAILED"}:
                continue
            projection = client.request(f"/api/interactions/{original['interaction_id']}/turns/{turn['turn_id']}/realization")
            (output/(identity+"-interaction.json")).write_text(json.dumps(state,ensure_ascii=False,indent=2))
            (output/(identity+"-realization.json")).write_text(json.dumps(projection,ensure_ascii=False,indent=2))
            before = json.loads((source/"before.json").read_text()).get("repository_observation") or {}
            after = state.get("repository_observation") or {}
            obligations = [o for o in projection.get("obligations",[]) if o["plane"]=="ACTION"]
            realized = [o["operation"] for o in obligations if o["state"]=="SATISFIED"]
            expected = cases[identity]["expected_operations"]
            checks = {"turn_completed":turn["status"]=="COMPLETED",
                "no_production_work":state.get("governed_work_id") is None,
                "actual_operations":sorted(realized)==sorted(expected),
                "all_expected_effects":all(o["state"]=="SATISFIED" for o in obligations)}
            if expected:
                target = cases[identity]["expected_branch"]
                checks["exact_target"] = all(any(e.get("target")==target for e in o["expected_effects"]) for o in obligations)
                checks["baseline_preserved"] = all(before.get(k)==after.get(k) for k in ("revision","tree"))
                checks["current_branch"] = after.get("repository_ref")==(
                    before.get("repository_ref") if expected==["CREATE_BRANCH"] else "refs/heads/"+target)
            else:
                checks["no_repository_effect"] = before==after
            negative_effect = bool(not expected and (realized or state.get("governed_work_id") or before!=after))
            git_record = source/"actual-git-wrong-target-observation.json"
            wrong_target = git_record.exists() and json.loads(git_record.read_text()).get("wrong_target_effect_observed") is True
            result = {"case_id":identity,"group":cases[identity]["group"],
                "status":"PASS" if all(checks.values()) else "FAIL","checks":checks,
                "effect_observed":True,"hard_negative":not bool(expected),
                "false_execution":negative_effect or wrong_target,"wrong_target_execution":wrong_target,
                "original_status":original["status"],"turn_created_at":turn["created_at"],
                "turn_started_at":turn.get("started_at"),"turn_completed_at":turn.get("completed_at")}
            results.append(result)
            pending.remove(identity)
            print(json.dumps(result),flush=True)
        if pending:
            time.sleep(10)
    observed = [r for r in results if r["effect_observed"]]
    negatives = [r for r in observed if r["hard_negative"]]
    report = {"observed_at":datetime.now(UTC).isoformat(),"cases":len(plan["case_ids"]),
        "passed":sum(r["status"]=="PASS" for r in results),"observed_cases":len(observed),
        "unobserved_cases":len(plan["case_ids"])-len(observed),"still_pending":sorted(pending),
        "false_execution_cases":[r["case_id"] for r in observed if r["false_execution"]],
        "qualified_negative_cases":len(negatives),
        "negative_false_execution_cases":[r["case_id"] for r in negatives if r["false_execution"]],
        "results":results,"human_acceptance":"PENDING","resubmission":False,
        "original_deadline_failures_rewritten":False}
    (output/"report.json").write_text(json.dumps(report,indent=2)+"\n")


if __name__ == "__main__":
    main()
