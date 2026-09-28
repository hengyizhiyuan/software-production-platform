"""Unseen messages through public Interaction, with real qualified Git effects.

Starting repository/branch/Work context is established by ordinary authorized Turns.
The tester never clones, creates branches, repairs Work or injects implementation
hints. Every generated message is submitted unchanged. Physical owner state is
read independently of the obligation ledger, including after blocked effects.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from hashlib import sha256
import argparse
import json
from pathlib import Path, PurePosixPath
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
    parser.add_argument("--seen-regression",action="store_true",
        help="Run previously exposed cases as diagnostic regression, never as unseen qualification")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    freeze = json.loads(args.freeze.read_text(encoding="utf-8"))
    verify_freeze(root,freeze)
    runtime = json.loads((args.runtime_identity/"source.json").read_text(encoding="utf-8"))
    if runtime["source_fingerprint"] != freeze["source_fingerprint"]:
        raise SystemExit("Live image identity does not match the implementation freeze")
    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    corpus_digest = sha256(args.corpus.read_bytes()).hexdigest()
    trial_digest = sha256((corpus_digest + str(args.directory.resolve())).encode()).hexdigest()[:12]
    if args.seen_regression:
        if corpus.get("holdout"):
            raise SystemExit("Seen regression must be explicitly labelled holdout=false")
    elif not corpus.get("holdout") or corpus["generated_at"] <= freeze["frozen_at"]:
        raise SystemExit("Only unseen post-freeze wording is qualified here")
    if args.directory.exists():
        raise SystemExit("Live holdout identity is immutable")
    args.directory.mkdir(parents=True)
    env = dict(line.split("=",1) for line in args.env_file.read_text(encoding="utf-8").splitlines() if "=" in line)
    chosen = corpus["cases"]
    (args.directory/"plan.json").write_text(json.dumps({"case_ids":[c["id"] for c in chosen],
        "corpus_sha256":corpus_digest,"trial_source_id":trial_digest,
        "runtime_identity":runtime,"manual_git":False,"implementation_hints":False,
        "seen_regression":args.seen_regression},indent=2)+"\n",encoding="utf-8")

    def run(case):
        directory = args.directory/case["id"]
        directory.mkdir()
        def save(name,value):
            (directory/(name+".json")).write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        def git_observation(state, name):
            observation = state.get("repository_observation") or {}
            intake_id = observation.get("intake_request_id")
            if not intake_id:
                return None
            workspace = (observation.get("operation_evidence") or {}).get("workspace_reference")
            target = PurePosixPath(workspace or args.asset_root+"/"+intake_id)
            if not target.is_relative_to(PurePosixPath(args.asset_root)):
                raise RuntimeError("Owner workspace reference is outside repository assets")
            # Read actual owner storage even if an obligation blocked after a
            # partial write. A blocked ledger is not proof that no write occurred.
            code = "import json,subprocess,sys; p=sys.argv[1]; g=lambda *a:subprocess.check_output(['git','-C',p,*a],text=True).strip(); print(json.dumps({'revision':g('rev-parse','HEAD'),'tree':g('rev-parse','HEAD^{tree}'),'repository_ref':g('symbolic-ref','HEAD'),'branches':g('for-each-ref','--format=%(refname:short)','refs/heads/').splitlines()}))"
            result = subprocess.run(["docker", "exec", args.git_owner_container, "python", "-c", code,
                str(target)], capture_output=True, text=True, timeout=30)
            value = {"read_only":True,"owner_storage_intake_id":intake_id,"exit_code":result.returncode,
                "owner_storage_path":str(target),
                "facts":json.loads(result.stdout) if result.returncode==0 else None}
            save(name,value)
            return value["facts"]
        client = ProductClient(args.base,env["SPG_OPERATOR_TOKEN"])
        def attention_for(work_id, kind):
            entries = client.request("/api/attention?work_id="+work_id)
            if isinstance(entries, dict):
                entries = [entries]
            if not isinstance(entries, list):
                raise RuntimeError("Attention owner returned an invalid projection")
            return next((entry for entry in entries if entry.get("kind")==kind), None)
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
            if case["group"] == "acquisition_future_goal":
                after,projection,status = turn(case["text"],"unseen")
                actual_after = git_observation(after,"actual-git-after")
                effects = [o for o in projection.get("obligations",[]) if o["plane"]=="ACTION"]
                expected_source = case["expected_repository_source"]
                observation = after.get("repository_observation") or {}
                semantic_items = ((after.get("latest_assessment") or {}).get("semantic_ir") or {}).get("items",[])
                checks = {"turn_completed":status=="COMPLETED",
                    "acquisition_satisfied":any(o["operation"]=="ACQUIRE_REPOSITORY"
                        and o["state"]=="SATISFIED" for o in effects),
                    "exact_human_source":after.get("repository_source")==expected_source
                        and observation.get("source")==expected_source,
                    "actual_git_observed":actual_after is not None,
                    "source_ready":observation.get("condition")=="READY",
                    "future_goal_not_admitted":after.get("governed_work_id") is None,
                    "action_intents":set(case.get("action_intents",())) <= {
                        (item.get("action") or {}).get("operation") for item in semantic_items}}
                result.update(checks=checks,status="PASS" if all(checks.values()) else "FAIL",
                    false_execution=after.get("governed_work_id") is not None,
                    actual_git_observation_available=actual_after is not None,
                    effect_satisfaction=checks["acquisition_satisfied"] and checks["actual_git_observed"],
                    observed_operations=[o["operation"] for o in effects if o["state"]=="SATISFIED"])
                save("result",result)
                print(json.dumps(result,ensure_ascii=False),flush=True)
                return result
            source = args.source
            if "/trials/" in source:
                parent, filename = source.rsplit("/",1)
                source = parent+"-"+trial_digest+"-"+case["id"]+"/"+filename
            baseline,_,status = turn("先获取这个仓库："+source+"。暂不开始生产。","setup-repository")
            if status!="COMPLETED" or (baseline.get("repository_observation") or {}).get("condition")!="READY":
                raise RuntimeError("Starting repository was not actually acquired by Watt")
            if case["group"] in {"branch_switch_only","colloquial_punctuation"}:
                baseline,_,status = turn("创建本地分支 feat_existing，保持当前分支，不切换。","setup-existing-branch")
                if status!="COMPLETED":
                    raise RuntimeError("Existing branch context could not be established")
            setup_work_id = None
            setup_attention = None
            if case["group"] in {"acceptance_without_delivery","explicit_delivery_authorization"}:
                baseline,_,status = turn("把首页“开始使用”改为“立即体验”，给我预览。我确认以后再决定是否交付。",
                    "setup-review-candidate")
                setup_work_id = baseline.get("governed_work_id")
                if status!="COMPLETED" or not setup_work_id:
                    raise RuntimeError("Candidate setup did not admit a real Work")
                deadline=time.monotonic()+args.timeout
                while time.monotonic()<deadline:
                    preview=client.request("/api/works/"+setup_work_id+"/functional-preview")
                    setup_attention=attention_for(setup_work_id,"CANDIDATE_AUTHORIZATION")
                    if preview.get("status")=="READY" and (setup_attention or {}).get("kind")=="CANDIDATE_AUTHORIZATION":
                        break
                    time.sleep(4)
                save("setup-review-preview",preview)
                save("setup-review-attention",setup_attention)
                if preview.get("status")!="READY" or (setup_attention or {}).get("kind")!="CANDIDATE_AUTHORIZATION":
                    raise RuntimeError("Exact Candidate was not review-ready")
                if case["group"]=="explicit_delivery_authorization":
                    baseline,accepted_projection,status=turn(
                        "我接受当前预览的候选版本，但暂不交付。","setup-accepted-candidate")
                    save("setup-accepted-realization",accepted_projection)
                    if status!="COMPLETED" or not any(o["operation"]=="ACCEPT_CANDIDATE"
                            and o["state"]=="SATISFIED" for o in accepted_projection.get("obligations",[])):
                        raise RuntimeError("Accepted-Candidate precondition did not settle")
            if case["group"]=="work_scope_answer":
                baseline,_,status=turn(
                    "给系统增加搜索。需要尽快完成；搜索范围涉及用户、客户、订单，请根据现有仓库确认需要我决定的覆盖范围。",
                    "setup-search-work")
                setup_work_id=baseline.get("governed_work_id")
                if status!="COMPLETED" or not setup_work_id:
                    raise RuntimeError("Search Work was not admitted")
                deadline=time.monotonic()+args.timeout
                while time.monotonic()<deadline:
                    setup_attention=attention_for(setup_work_id,"STEERING_DECISION_REQUIRED")
                    if (setup_attention or {}).get("kind")=="STEERING_DECISION_REQUIRED":
                        break
                    # A sealed Candidate means production passed the decision
                    # boundary. Waiting longer cannot make this setup valid.
                    if attention_for(setup_work_id,"CANDIDATE_AUTHORIZATION"):
                        save("failed-setup-observation",{"work_id":setup_work_id,
                            "reason":"Candidate reached before required scope decision",
                            "attention":client.request("/api/attention?work_id="+setup_work_id)})
                        break
                    time.sleep(4)
                save("setup-scope-attention",setup_attention)
                if (setup_attention or {}).get("kind")!="STEERING_DECISION_REQUIRED":
                    raise RuntimeError("Current Work did not ask its scope question")
            for index,text in enumerate(case.get("context",[])):
                baseline,_,status = turn(text,f"prior-context-{index+1}")
                if status!="COMPLETED":
                    raise RuntimeError("Declared prior Human context did not settle")
            pre_answer_attention=(attention_for(setup_work_id,"STEERING_DECISION_REQUIRED")
                if case["group"]=="work_scope_answer" else None)
            if case["group"]=="work_scope_answer":
                save("pre-answer-attention",pre_answer_attention)
            save("before",baseline)
            actual_before = git_observation(baseline,"actual-git-before")
            after,projection,status = turn(case["text"],"unseen")
            actual_after = git_observation(after,"actual-git-after")
            before_repo,after_repo = baseline.get("repository_observation"),after.get("repository_observation")
            effects = [o for o in projection.get("obligations",[]) if o["plane"]=="ACTION"]
            actual = [o["operation"] for o in effects if o["state"]=="SATISFIED"]
            expected = case["expected_operations"]
            semantic_items = ((after.get("latest_assessment") or {}).get("semantic_ir") or {}).get("items",[])
            observed_kinds = {item.get("kind") for item in semantic_items}
            observed_action_intents = {(item.get("action") or {}).get("operation")
                for item in semantic_items if item.get("action")}
            unexpected = unexpected_branch_effect(case, actual_before, actual_after)
            physical_observed = actual_before is not None and actual_after is not None
            if case["group"] == "search_positive":
                answer = next((m["content"] for m in reversed(after.get("conversation_messages",[]))
                    if m["actor"]=="WATT"),"")
                checks = {"turn_completed":status=="COMPLETED",
                    "github_owner_satisfied":actual==["SEARCH_GITHUB"],
                    "source_cited":("https://github.com/" in answer and "external-search:" in answer),
                    "no_repository_write":actual_before==actual_after,
                    "no_production_work":after.get("governed_work_id") is None,
                    "actual_git_observed":physical_observed}
                result.update(checks=checks,status="PASS" if all(checks.values()) else "FAIL",
                    false_execution=bool(unexpected or after.get("governed_work_id") is not None),
                    actual_git_observation_available=physical_observed,
                    effect_satisfaction=checks["github_owner_satisfied"] and checks["source_cited"],
                    observed_operations=actual)
                save("result",result)
                print(json.dumps(result,ensure_ascii=False),flush=True)
                return result
            if case["group"] in {"acceptance_without_delivery","explicit_delivery_authorization"}:
                delivery=client.request("/api/works/"+setup_work_id+"/delivery")
                save("review-delivery",delivery)
                intended=case["action_intents"][0]
                matching=[o for o in effects if o["operation"]==intended]
                if case["group"]=="acceptance_without_delivery":
                    realized=any(o["state"]=="SATISFIED"
                        and (o.get("observed_effect") or {}).get("owner")=="candidate-human-governance"
                        for o in matching)
                else:
                    realized=bool(matching and all(o["state"] in {
                        "BLOCKED_WITH_EVIDENCE","REQUIRES_HUMAN"} for o in matching))
                reviewed_revision=preview.get("candidate_revision")
                exact_candidate_only=bool(physical_observed and reviewed_revision
                    and actual_after["revision"]==reviewed_revision
                    and actual_after["repository_ref"]==actual_before["repository_ref"]
                    and actual_after["branches"]==actual_before["branches"])
                checks={"turn_completed":status=="COMPLETED",
                    "declared_intent_compiled":intended in observed_action_intents,
                    "owner_boundary_reconciled":realized,
                    "no_delivery":not bool(delivery.get("deliveries")),
                    "only_reviewed_candidate_commit":exact_candidate_only,
                    "actual_git_observed":physical_observed}
                result.update(checks=checks,status="PASS" if all(checks.values()) else "FAIL",
                    false_execution=bool((actual_before != actual_after and not exact_candidate_only)
                        or delivery.get("deliveries")),
                    actual_git_observation_available=physical_observed,
                    effect_satisfaction=realized,observed_operations=actual,
                    setup_work_id=setup_work_id)
                save("result",result)
                print(json.dumps(result,ensure_ascii=False),flush=True)
                return result
            if case["group"] in {"production_correction","work_scope_answer"}:
                work_id=after.get("governed_work_id")
                attention=(attention_for(work_id,"STEERING_DECISION_REQUIRED")
                    if work_id and case["group"]=="work_scope_answer" else None)
                save("realization-attention",attention)
                checks={"turn_completed":status=="COMPLETED",
                    "required_kinds":set(case.get("required_kinds",())) <= observed_kinds,
                    "same_real_work":bool(work_id and work_id==baseline.get("governed_work_id")),
                    "no_repository_write":actual_before==actual_after,
                    "actual_git_observed":physical_observed}
                if case["group"]=="work_scope_answer":
                    checks["question_pending_before_answer"]=(setup_attention is not None
                        and pre_answer_attention is not None
                        and pre_answer_attention.get("attention_id")==setup_attention.get("attention_id"))
                    checks["work_question_resolved"]=(checks["question_pending_before_answer"]
                        and (not attention or attention.get("attention_id")!=setup_attention.get("attention_id")))
                else:
                    checks["current_production_compiled"]=any((i.get("production") or {}).get("current")
                        for i in semantic_items)
                    checks["work_revision_advanced"]=(after.get("governed_revision")!=baseline.get("governed_revision"))
                result.update(checks=checks,status="PASS" if all(checks.values()) else "FAIL",
                    false_execution=bool(unexpected),actual_git_observation_available=physical_observed,
                    effect_satisfaction=checks.get("work_question_resolved",checks.get("work_revision_advanced")),
                    observed_operations=actual,work_id=work_id)
                save("result",result)
                print(json.dumps(result,ensure_ascii=False),flush=True)
                return result
            if case["group"] == "production":
                work_id = after.get("governed_work_id")
                work = client.request("/api/works/"+work_id) if work_id else None
                preview = client.request("/api/works/"+work_id+"/functional-preview") if work_id else None
                save("production-work",work)
                save("production-preview",preview)
                checks = {"turn_completed":status=="COMPLETED",
                    "current_production_compiled":any((i.get("production") or {}).get("current")
                        for i in semantic_items),
                    "real_work_admitted":bool(work_id and work and work.get("work_id")==work_id),
                    "no_branch_write":actual_before==actual_after,
                    "actual_git_observed":physical_observed,
                    "no_delivery_authorization":True}
                if work_id:
                    delivery = client.request("/api/works/"+work_id+"/delivery")
                    save("production-delivery",delivery)
                    checks["no_delivery_authorization"] = not bool(delivery.get("deliveries"))
                result.update(checks=checks,status="PASS" if all(checks.values()) else "FAIL",
                    false_execution=bool(unexpected or not checks["no_delivery_authorization"]),
                    actual_git_observation_available=physical_observed,
                    effect_satisfaction=checks["real_work_admitted"],
                    observed_operations=actual,work_id=work_id)
                save("result",result)
                print(json.dumps(result,ensure_ascii=False),flush=True)
                return result
            erroneous_effect = bool(unexpected or after.get("governed_work_id") is not None
                or (not expected and actual))
            result.update(false_execution=erroneous_effect if physical_observed else None,
                actual_git_observation_available=physical_observed,
                unexpected_branch_effect=unexpected)
            checks = {"turn_completed":status=="COMPLETED","no_production_work":after.get("governed_work_id") is None,
                "actual_git_observed":physical_observed,
                "no_unrequested_branch_effect":unexpected is False,
                "actual_operations":sorted(actual)==sorted(expected),
                "all_requested_effects_reconciled":all(o["state"]=="SATISFIED" for o in effects),
                "required_kinds":set(case.get("required_kinds",())) <= observed_kinds,
                "action_intents":set(case.get("action_intents",())) <= observed_action_intents}
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
        "source_fingerprint":freeze["source_fingerprint"],"human_acceptance":"PENDING",
        "seen_regression":args.seen_regression}
    (args.directory/"report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
