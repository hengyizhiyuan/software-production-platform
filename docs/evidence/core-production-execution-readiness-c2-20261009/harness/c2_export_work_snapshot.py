#!/usr/bin/env python3
"""Passive Work-scoped C2 Owner export; raw records remain private 0600."""
import argparse
import hashlib
import json
import os
import re
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def private_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    raw=(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, default=str)+"\n").encode()
    fd=os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    with os.fdopen(fd,"wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(raw).hexdigest()


def uid(value):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def safe_record(row):
    result={}
    for key,value in row.items():
        if key=="id" or key.endswith("_id"):
            if (parsed:=uid(value)):
                result[key]=parsed
        elif key in {"condition","state","result","status","outcome","runtime_mode","terminal_outcome","grant_state","kind","event_type","failure_code","error_code","failure_family","root_cause_classification","refinement_class","signal_kind","final_result","work_resume_result"}:
            if value is None:
                result[key]=None
            elif isinstance(value,str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}",value):
                result[key]=value
        elif key.endswith("_at") and isinstance(value,str):
            try:
                datetime.fromisoformat(value.replace("Z","+00:00"))
                result[key]=value
            except ValueError:
                pass
        elif key in {"sequence","generation","current_execution_generation","version","revision_number","current_step_sequence"} and isinstance(value,int):
            result[key]=value
    return result


def execute(args, snapshot):
    from sqlalchemy import bindparam, create_engine, text
    from spg.config import Settings
    # Settings stay in memory. No ENV/URL/settings output and no application service construction.
    engine=create_engine(Settings().database_url)
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(text("SET LOCAL statement_timeout = '20s'"))
            identity=connection.execute(text("SELECT current_database() AS database_name, clock_timestamp() AS captured_at_utc, current_setting('transaction_read_only') AS read_only, txid_current_snapshot()::text AS transaction_snapshot")).mappings().one()
            if identity["database_name"]!=args.expected_database or "c2" not in identity["database_name"].lower():
                raise ValueError("EXACT_C2_DATABASE_REQUIRED")
            snapshot["database_snapshot"]=dict(identity)
            available=connection.execute(text("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema='public'")).mappings().all()
            columns={}
            for row in available:
                columns.setdefault(row["table_name"],set()).add(row["column_name"])
            datasets=snapshot["datasets"]
            def collect(table,column,values):
                if not re.fullmatch(r"[a-z_]+",table+column):
                    raise ValueError("FIXED_QUERY_IDENTIFIER_REQUIRED")
                vals=sorted({str(v) for v in values if v is not None})
                if table not in columns:
                    datasets[table]={"query_status":"TABLE_UNAVAILABLE","scope_column":column,"rows":[]}
                elif column not in columns[table]:
                    datasets[table]={"query_status":"SCOPE_COLUMN_UNAVAILABLE","scope_column":column,"rows":[]}
                elif not vals:
                    datasets[table]={"query_status":"NO_SCOPED_IDENTITIES_NOT_QUERIED","scope_column":column,"rows":[]}
                else:
                    sql=text(f'SELECT to_jsonb(t) AS owner_row FROM public."{table}" AS t WHERE CAST(t."{column}" AS text) IN :ids LIMIT 10001').bindparams(bindparam("ids",expanding=True))
                    rows=[r["owner_row"] for r in connection.execute(sql,{"ids":vals}).mappings()]
                    if len(rows)>10000:
                        raise ValueError("SCOPED_EXPORT_ROW_LIMIT")
                    datasets[table]={"query_status":"QUERIED","scope_column":column,"scope_ids":vals,"rows":rows}
                return datasets[table]["rows"]
            def values(table,*keys):
                return {str(row[key]) for row in datasets.get(table,{}).get("rows",[]) for key in keys if row.get(key) is not None}
            state=snapshot["driver_state"]
            wid=uid(args.work_id)
            if wid is None or state.get("work_id")!=wid:
                raise ValueError("STATE_WORK_IDENTITY_MISMATCH")
            product=uid(state.get("product_id")); interaction=uid(state.get("interaction_id")); turn=uid(state.get("turn_id"))
            if not all((product,interaction,turn)):
                raise ValueError("STATE_ENTRY_IDENTITIES_REQUIRED")
            work=collect("product_works","id",[wid])
            if len(work)!=1 or str(work[0].get("product_id"))!=product:
                raise ValueError("WORK_PRODUCT_SCOPE_MISMATCH")
            linkage=collect("product_workspace_interactions","interaction_id",[interaction])
            if len(linkage)!=1 or str(linkage[0].get("product_id"))!=product:
                raise ValueError("INTERACTION_PRODUCT_SCOPE_MISMATCH")
            for table in ("software_products","product_managed_sources","product_source_versions","software_product_assets"):
                collect(table,"id" if table=="software_products" else "product_id",[product])
            for table in ("product_interactions",):
                collect(table,"id",[interaction])
            for table in ("interaction_records","interaction_turns","interaction_assessments"):
                collect(table,"interaction_id",[interaction])
            for table in ("interaction_turn_realizations","interaction_turn_semantic_envelopes","interaction_turn_obligations","interaction_turn_realization_refinements"):
                collect(table,"turn_id",[turn])
            turns=[r for r in datasets["interaction_turns"]["rows"] if str(r["id"])==turn]
            request_id=str(turns[0].get("request_record_id")) if len(turns)==1 else None
            record=next((r for r in datasets["interaction_records"]["rows"] if str(r["id"])==request_id),None)
            if record is None or hashlib.sha256(str(record.get("content","")).encode()).hexdigest()!=state["input_sha256"]:
                raise ValueError("ORIGINAL_INPUT_REQUEST_RECORD_HASH_MISMATCH")
            snapshot["new_request_record_id"]=request_id
            for table in ("work_reality_revisions","engineering_scopes","work_source_bases","work_runtime_bindings","steering_plans","steering_plan_revisions","semantic_step_results","work_convergence_observations","self_refine_events","work_delivery_targets","work_delivery_manifests","product_source_promotion_intents"):
                collect(table,"work_id",[wid])
            collect("engineering_resource_bindings","engineering_scope_id",values("engineering_scopes","id"))
            resource_ids=values("engineering_resource_bindings","resource_id")|values("work_source_bases","resource_id")|values("work_reality_revisions","engineering_resource_id")
            collect("engineering_resources","id",resource_ids)
            collect("steering_steps","steering_plan_revision_id",values("steering_plan_revisions","id"))
            collect("steering_decisions","steering_plan_revision_id",values("steering_plan_revisions","id"))
            collect("steering_history_events","steering_plan_id",values("steering_plans","id"))
            runs=values("work_runtime_bindings","production_run_id")
            for table in ("production_runs","plan_revisions","production_work_units","context_packages","completion_evaluations","proposed_repository_snapshots","verification_records","production_admissibility_records","baseline_candidates"):
                collect(table,"id" if table=="production_runs" else "production_run_id",runs)
            pwus=values("production_work_units","id")
            collect("execution_attempts","work_unit_id",pwus)
            attempts=values("execution_attempts","id")
            for table in ("pwu_contract_versions","execution_sessions","execution_events","executor_queue","execution_workspaces","native_attempt_bindings","result_ready_claims"):
                collect(table,"pwu_id",pwus)
            for table in ("native_attempt_states","execution_steps","execution_allocations","executor_leases","checkpoint_bundles","execution_evidence","execution_resource_usage","execution_control_requests","execution_recovery_cases","attempt_preparations","execution_dispatches","provider_execution_reports","repository_observations","work_product_references"):
                collect(table,"attempt_id",attempts)
            collect("execution_effects","step_id",values("execution_steps","id"))
            collect("effect_receipts","effect_id",values("execution_effects","id"))
            collect("self_refine_actions","event_id",values("self_refine_events","id"))
            collect("event_outbox","event_id",values("execution_events","id"))
            vector_ids=values("native_attempt_bindings","source_vector_id")|values("execution_workspaces","source_vector_id")
            collect("execution_source_vectors","id",vector_ids)
            collect("execution_source_members","source_vector_id",vector_ids)
            collect("execution_resource_envelopes","id",values("native_attempt_bindings","resource_envelope_id"))
            workers=values("execution_allocations","worker_id")|values("executor_leases","worker_id")
            collect("executor_worker_registrations","worker_id",workers)
            # Worker registration is shared Owner state, scoped to workers actually allocated here.
            collect("executor_worker_events","worker_id",workers)
            baseline_ids=set()
            for table in ("production_runs","production_work_units","plan_revisions","execution_attempts","work_reality_revisions","baseline_candidates"):
                baseline_ids|=values(table,"source_baseline_id","integrated_baseline_id","verified_output_baseline_id")
            collect("production_snapshots","id",baseline_ids)
            candidates=values("baseline_candidates","id")
            for table in ("human_authorizations","repository_integration_effects","runtime_commits"):
                collect(table,"candidate_id",candidates)
            manifests=values("work_delivery_manifests","id")
            collect("work_delivery_acceptances","manifest_id",manifests)
            collect("work_delivery_runtimes","manifest_id",manifests)
            governed_ids={wid,product}|runs|pwus|attempts|candidates|values("work_reality_revisions","id")|values("steering_decisions","id")
            governance=collect("governance_records","subject_identity",governed_ids)
            referenced=values("work_reality_revisions","governance_record_id")
            if referenced:
                other=connection.execute(text('SELECT to_jsonb(t) AS owner_row FROM public.governance_records t WHERE CAST(t.id AS text) IN :ids').bindparams(bindparam("ids",expanding=True)),{"ids":sorted(referenced)}).mappings()
                by_id={row["id"]:row for row in governance}
                by_id.update({r["owner_row"]["id"]:r["owner_row"] for r in other})
                datasets["governance_records"]["rows"]=list(by_id.values())
            collect("transition_history","entity_identity",governed_ids)
            snapshot["db_export_completed_at_utc"]=now()
    # Read filesystem Owner objects directly, never instantiate an application service.
    environment_root=Settings().native_executor_production_environment_store_root.resolve()
    files=[]
    def owner_file(path):
        resolved=path.resolve()
        if not resolved.is_relative_to(environment_root):
            raise ValueError("OWNER_FILE_OUTSIDE_ROOT")
        if not resolved.is_file():
            return
        raw=resolved.read_bytes()
        files.append({"relative_path":str(resolved.relative_to(environment_root)),"sha256":hashlib.sha256(raw).hexdigest(),"observed_at_utc":now(),"payload":json.loads(raw)})
    wid=args.work_id
    for row in snapshot["datasets"].get("work_reality_revisions",{}).get("rows",[]):
        owner_file(environment_root/"guardian-requirements"/(wid+"-"+str(row["id"])+".json"))
    owner_file(environment_root/"candidate-previews"/"by-work"/(wid+".json"))
    sessions_root=environment_root/"candidate-previews"/"sessions"
    for current in sessions_root.glob("*/current.json") if sessions_root.exists() else []:
        data=json.loads(current.read_bytes())
        if str(data.get("work_id"))!=wid:
            continue
        owner_file(current)
        preview_id=uid(data.get("id"))
        if preview_id:
            for folder in ("guardian-projections","guardian-feedback-errors"):
                owner_file(environment_root/folder/(preview_id+".json"))
            # Targeted preview evidence only; no global logs or ENV reads.
            directory=environment_root/"candidate-previews"/"evidence"/preview_id
            for entry in directory.glob("*.json") if directory.exists() else []:
                owner_file(entry)
    snapshot["filesystem_owner_observations"]={"observed_at_utc":now(),"consistency":"FILES_CAPTURED_AFTER_DB_SNAPSHOT_NOT_ATOMIC_WITH_DATABASE","files":files}
    snapshot["completed_at_utc"]=now()


def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-file",required=True,type=Path)
    parser.add_argument("--work-id",required=True)
    parser.add_argument("--expected-database",required=True)
    parser.add_argument("--private-output-dir",required=True,type=Path)
    args=parser.parse_args()
    private=args.private_output_dir.resolve()
    if "private" not in private.parts or private==private.anchor:
        raise ValueError("PRIVATE_OUTPUT_DIRECTORY_REQUIRED")
    private.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(private,0o700)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+"-"+uuid.uuid4().hex
    snapshot={"schema":"c2-work-canonical-private-snapshot-v1","started_at_utc":now(),"work_id":args.work_id,"datasets":{},"authority":"READ_ONLY_OWNER_OBSERVATION_NO_QUALIFICATION_PASS","raw_records_publication":"PRIVATE_0600_ROOT_REDACTION_REQUIRED"}
    try:
        snapshot["driver_state"]=json.loads(args.state_file.read_bytes())
        if snapshot["driver_state"]["runtime_identity"]["database_name"]!=args.expected_database:
            raise ValueError("STATE_DATABASE_IDENTITY_MISMATCH")
        execute(args,snapshot)
    except Exception as failure:
        snapshot["export_error"]={"type":type(failure).__name__,"private_raw_message":str(failure),"private_traceback":traceback.format_exc()}
    raw_path=private/(stamp+"-canonical-work.json")
    sha=private_json(raw_path,snapshot)
    safe={"schema":"c2-work-canonical-summary-draft-v1","captured_at_utc":now(),"work_id":args.work_id,"raw_private_sha256":sha,"raw_private_file":raw_path.name,"export_complete":"export_error" not in snapshot,"public_release":"ROOT_REDACTION_APPROVAL_REQUIRED","datasets":{table:{"query_status":entry["query_status"],"row_count":len(entry["rows"]),"rows":[safe_record(row) for row in entry["rows"]]} for table,entry in snapshot["datasets"].items()},"filesystem_file_count":len(snapshot.get("filesystem_owner_observations",{}).get("files",[]))}
    draft_path=private/(stamp+"-summary-draft.json")
    private_json(draft_path,safe)
    print(json.dumps({"work_id":args.work_id,"raw_private_file":raw_path.name,"raw_private_sha256":sha,"summary_private_file":draft_path.name,"export_complete":safe["export_complete"],"export_error_type":snapshot.get("export_error",{}).get("type"),"public_release":"ROOT_REDACTION_APPROVAL_REQUIRED"}))
    return 0 if safe["export_complete"] else 2


if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as failure:
        print(json.dumps({"export_complete":False,"export_error_type":type(failure).__name__,"raw_message_omitted":True}),file=sys.stderr)
        sys.exit(3)
