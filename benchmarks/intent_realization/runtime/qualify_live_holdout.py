"""Unseen messages through public Interaction, with real qualified Git effects.

Starting repository/branch context is established by ordinary authorized Turns.
The tester never clones, creates branches, repairs Work or injects implementation
hints. The generated messages are submitted unchanged. Compiler-only acquisition
fixtures and production goals are excluded from this bounded effect cohort.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from hashlib import sha256
import argparse
import json
from pathlib import Path
import subprocess
import time

from benchmarks.golden.runtime.journey import ProductClient
from benchmarks.intent_realization.runtime.evidence import verify_freeze



def unexpected_branch_effect(case, before, after):
    """Classify actual extra writes separately from missed requested effects."""
    if before is None or after is None:
        return None
    expected = case["expected_operations"]
    added = set(after["branches"]) - set(before["branches"])
    removed = set(before["branches"]) - set(after["branches"])
    allowed = {case["expected_branch"]} if expected in (
        ["CREATE_BRANCH"], ["CREATE_AND_SWITCH_BRANCH"]) else set()
    requested_ref = ("refs/heads/" + case["expected_branch"] if expected in (
        ["SWITCH_BRANCH"], ["CREATE_AND_SWITCH_BRANCH"]) else before["repository_ref"])
    head_changed = after["repository_ref"] != before["repository_ref"]
    return bool(added - allowed or removed
        or (head_changed and after["repository_ref"] != requested_ref)
        or any(after[key] != before[key] for key in ("revision", "tree")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus",type=Path,required=True)
    parser.add_argument("--freeze",type=Path,required=True)
    parser.add_argument("--runtime-identity",type=Path,required=True)
    parser.add_argument("--directory",type=Path,required=True)
    parser.add_argument("--env-file",type=Path,required=True)
    parser.add_argument("--base",default="http://127.0.0.1:8078")
    parser.add_argument("--source",default="http://qualified-git:8080/business-app.git")
    parser.add_argument("--workers",type=int,default=1)
    parser.add_argument("--timeout",type=int,default=1800)
    parser.add_argument("--git-owner-container",default="watt-irk-qualification-app-1")
    parser.add_argument("--asset-root",default="/var/lib/spg/repository-assets")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    freeze = json.loads(args.freeze.read_text())
    verify_freeze(root,freeze)
    runtime = json.loads((args.runtime_identity/"source.json").read_text())
    if runtime["source_fingerprint"] != freeze["source_fingerprint"]:
        raise SystemExit("Live image identity does not match the implementation freeze")
    corpus = json.loads(args.corpus.read_text())
    if not corpus.get("holdout") or corpus["generated_at"] <= freeze["frozen_at"]:
        raise SystemExit("Only unseen post-freeze wording is qualified here")
    if args.directory.exists():
        raise SystemExit("Live holdout identity is immutable")
    args.directory.mkdir(parents=True)
    env = dict(line.split("=",1) for line in args.env_file.read_text().splitlines() if "=" in line)
    negatives = {"hard_negative","search_negation","conditional_negative","delivery_negative"}
    groups = {"branch_both","branch_create_only","branch_switch_only","contextual_branch"}
    chosen = []
    for case in corpus["cases"]:
        if case["group"] in negatives or case["group"] in groups:
            chosen.append(case)
            groups.discard(case["group"])
    (args.directory/"plan.json").write_text(json.dumps({"case_ids":[c["id"] for c in chosen],
        "corpus_sha256":sha256(args.corpus.read_bytes()).hexdigest(),
        "runtime_identity":runtime,"manual_git":False,"implementation_hints":False},indent=2)+"\n")

    def run(case):
        directory = args.directory/case["id"]
        directory.mkdir()
        def save(name,value):
            (directory/(name+".json")).write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n")
        def git_observation(state, name):
            observation = state.get("repository_observation") or {}
            intake_id = observation.get("intake_request_id")
            if not intake_id:
                return None
            # Read actual owner storage even if an obligation blocked after a
            # partial write. A blocked ledger is not proof that no write occurred.
            code = "import json,subprocess,sys; p=sys.argv[1]; g=lambda *a:subprocess.check_output(['git','-C',p,*a],text=True).strip(); print(json.dumps({'revision':g('rev-parse','HEAD'),'tree':g('rev-parse','HEAD^{tree}'),'repository_ref':g('symbolic-ref','HEAD'),'branches':g('for-each-ref','--format=%(refname:short)','refs/heads/').splitlines()}))"
            result = subprocess.run(["docker", "exec", args.git_owner_container, "python", "-c", code,
                args.asset_root+"/"+intake_id], capture_output=True, text=True, timeout=30)
            value = {"read_only":True,"owner_storage_intake_id":intake_id,"exit_code":result.returncode,
                "facts":json.loads(result.stdout) if result.returncode==0 else None}
            save(name,value)
            return value["facts"]
        client = ProductClient(args.base,env["SPG_OPERATOR_TOKEN"])
        creation = client.request("/api/interactions",{"human_identity":"human:holdout-operator"})
        identity = creation["interaction_id"]
        save("creation",creation)
        def turn(text,name):
            receipt = client.request(f"/api/interactions/{identity}/turns",{
                "content":text,"human_identity":"human:holdout-operator"})
            save(name+"-submission",receipt)
            deadline = time.monotonic()+args.timeout
            while time.monotonic()<deadline:
                state = client.request(f"/api/interactions/{identity}")
                current = next((t for t in state.get("turns",[]) if t["turn_id"]==receipt.get("turn_id")),None)
                if current and current["status"] in {"COMPLETED","FAILED"}:
                    save(name+"-interaction",state)
                    projection = client.request(f"/api/interactions/{identity}/turns/{current['turn_id']}/realization")
                    save(name+"-realization",projection)
                    return state,projection,current["status"]
                time.sleep(1)
            save(name+"-interaction",state)
            raise RuntimeError("Public Turn did not settle within the qualification budget")
        result = {"case_id":case["id"],"group":case["group"],"interaction_id":identity,
            "status":"FAIL","effect_satisfaction":None,"false_execution":None}
        try:
            source = args.source
            if "/trials/" in source:
                parent, filename = source.rsplit("/",1)
                source = parent+"-"+case["id"]+"/"+filename
            baseline,_,status = turn("先获取这个仓库："+source+"。暂不开始生产。","setup-repository")
            if status!="COMPLETED" or (baseline.get("repository_observation") or {}).get("condition")!="READY":
                raise RuntimeError("Starting repository was not actually acquired by Watt")
            if case["group"]=="branch_switch_only":
                baseline,_,status = turn("创建本地分支 feat_existing，保持当前分支，不切换。","setup-existing-branch")
                if status!="COMPLETED":
                    raise RuntimeError("Existing branch context could not be established")
            for index,text in enumerate(case.get("context",[])):
                baseline,_,status = turn(text,f"prior-context-{index+1}")
                if status!="COMPLETED":
                    raise RuntimeError("Declared prior Human context did not settle")
            save("before",baseline)
            actual_before = git_observation(baseline,"actual-git-before")
            after,projection,status = turn(case["text"],"unseen")
            actual_after = git_observation(after,"actual-git-after")
            before_repo,after_repo = baseline.get("repository_observation"),after.get("repository_observation")
            effects = [o for o in projection.get("obligations",[]) if o["plane"]=="ACTION"]
            actual = [o["operation"] for o in effects if o["state"]=="SATISFIED"]
            expected = case["expected_operations"]
            unexpected = unexpected_branch_effect(case, actual_before, actual_after)
            physical_observed = actual_before is not None and actual_after is not None
            erroneous_effect = bool(unexpected or after.get("governed_work_id") is not None
                or (not expected and actual))
            result.update(false_execution=erroneous_effect if physical_observed else None,
                actual_git_observation_available=physical_observed,
                unexpected_branch_effect=unexpected)
            checks = {"turn_completed":status=="COMPLETED","no_production_work":after.get("governed_work_id") is None,
                "actual_git_observed":physical_observed,
                "no_unrequested_branch_effect":unexpected is False,
                "actual_operations":sorted(actual)==sorted(expected),
                "all_requested_effects_reconciled":all(o["state"]=="SATISFIED" for o in effects)}
            if not expected:
                checks["no_repository_effect"] = before_repo==after_repo
            else:
                checks["exact_branch_argument"] = all(any(e.get("target")==case["expected_branch"]
                    for e in o["expected_effects"]) for o in effects)
                checks["source_revision_tree_unchanged"] = all((before_repo or {}).get(k)==(after_repo or {}).get(k) for k in ("revision","tree"))
                if expected==["CREATE_BRANCH"]:
                    checks["current_branch_preserved"] = (before_repo or {}).get("repository_ref")==(after_repo or {}).get("repository_ref")
                else:
                    checks["actual_current_branch"] = (after_repo or {}).get("repository_ref")=="refs/heads/"+case["expected_branch"]
            result.update(checks=checks,status="PASS" if all(checks.values()) else "FAIL",
                effect_satisfaction=checks["actual_operations"] and checks["all_requested_effects_reconciled"],
                observed_operations=actual)
        except Exception as error:
            result.update(error_type=type(error).__name__,error_code=str(error)[:400])
        save("result",result)
        print(json.dumps(result,ensure_ascii=False),flush=True)
        return result
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(run,chosen))
    verify_freeze(root,freeze)
    observed = [r for r in results if r["false_execution"] is not None]
    report = {"completed_at":datetime.now(UTC).isoformat(),"cases":len(results),
        "passed":sum(r["status"]=="PASS" for r in results),"cases_with_observed_effects":len(observed),
        "false_execution":sum(bool(r["false_execution"]) for r in observed),
        "unobserved_cases":len(results)-len(observed),"failed_cases":[r["case_id"] for r in results if r["status"]!="PASS"],
        "source_fingerprint":freeze["source_fingerprint"],"human_acceptance":"PENDING"}
    (args.directory/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
