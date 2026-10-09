"""Drive one explicitly labelled isolated GOF qualification through the public API.

Runs only inside the N1 API container; reads its configured token without logging it.
"""

import json
import sys
import time
import urllib.error
import urllib.request

from spg.config import Settings

BASE = "http://127.0.0.1:8000"
PROMPT = (
    "GOF isolated G0 software production qualification. In this newly managed Product "
    "repository, create exactly one static web page at index.html. This is CODE_WORK "
    "producing a software artifact. Use semantic HTML with exactly one h1 whose text "
    "is Governed Obligation Qualification and one paragraph whose text is Isolated "
    "qualification only. Only index.html may change. Verify the exact heading and "
    "paragraph and leave a reviewable Candidate. Do not deploy, publish, add pages, "
    "or change README.md."
)
TOKEN = Settings().operator_token.get_secret_value()
HEADERS = {"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"}


def call(method, path, data=None):
    body = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request(BASE + path, body, HEADERS, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        try:
            detail = json.load(error)
        except Exception:
            detail = {"code": "HTTP_ERROR"}
        return error.code, detail


def emit(kind, **fields):
    print(json.dumps({"kind": kind, **fields}, ensure_ascii=False, sort_keys=True), flush=True)


def main():
    mode = sys.argv[1]
    if mode == "inspect-old":
        status, result = call("GET", "/api/interactions/d93adc24-5227-465d-9ba5-b46717572b49")
        emit("old-input", status=status, human_said=result.get("human_said"),
             current_work_id=result.get("current_work_id"))
        return
    if mode == "create":
        stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        status, product = call("POST", "/api/products", {
            "name": "GOF G0 isolated qualification " + stamp,
            "description": "Agent-authored isolated N1 GOF capability qualification; no Human acceptance",
            "source_mode": "managed",
        })
        if status != 201:
            emit("product-error", status=status, code=product.get("code"), message=product.get("message"))
            return
        product_id = product["id"]
        emit("product", status=status, product_id=product_id,
             source_revision=product.get("source_revision"), source_version=product.get("source_version"))
        status, turn = call("POST", "/api/experience/products/" + product_id + "/turns", {"text": PROMPT})
        emit("turn-submit", status=status, interaction_id=turn.get("interaction_id"),
             turn_id=turn.get("turn_id"), code=turn.get("code"), message=turn.get("message"))
        return
    if mode == "poll":
        interaction_id, turn_id = sys.argv[2:4]
        for i in range(90):
            status, turn = call("GET", "/api/interactions/" + interaction_id + "/turns/" + turn_id)
            state = turn.get("status")
            if i == 0 or i % 10 == 0 or state in {"COMPLETED", "FAILED"}:
                emit("turn", status=status, state=state, failure_code=turn.get("failure_code"),
                     assessment_id=turn.get("assessment_id"), iteration=i)
            if state in {"COMPLETED", "FAILED"} or status != 200:
                break
            time.sleep(10)
        status, interaction = call("GET", "/api/interactions/" + interaction_id)
        assessment = interaction.get("latest_assessment") or {}
        readiness = interaction.get("readiness") or {}
        emit("interaction", status=status, condition=interaction.get("condition"),
             assessment_id=assessment.get("assessment_id") or assessment.get("id"),
             basis_fingerprint=assessment.get("basis_fingerprint"),
             readiness=readiness.get("status"), current_work_id=interaction.get("current_work_id"),
             governed_work_id=interaction.get("governed_work_id"),
             admission=interaction.get("production_admission_state"),
             next_step=interaction.get("production_next_step"))
        return
    if mode == "inspect-work":
        work_id = sys.argv[2]
        for path in ("/api/works/" + work_id, "/api/works/" + work_id + "/steering",
                     "/api/works/" + work_id + "/result",
                     "/api/attention?work_id=" + work_id):
            status, result = call("GET", path)
            if isinstance(result, list):
                emit("attention", status=status, items=[{
                    "id": item.get("attention_id") or item.get("id"),
                    "subject": item.get("governed_subject_ref"),
                    "actions": item.get("available_actions"),
                    "reason": item.get("reason"),
                } for item in result])
                continue
            emit("work-inspect", path=path, status=status, keys=sorted(result),
                 state=result.get("status"), code=result.get("code"),
                 condition=result.get("condition"),
                 stage=result.get("stage"),
                 next_action=result.get("next_action"),
                 failure_code=result.get("failure_code"),
                 work_reality_revision_id=result.get("current_work_reality_revision_id"),
                 next_owner=result.get("next_owner"),
                 what_happens_next=result.get("what_happens_next"),
                 last_stop_reason=result.get("last_stop_reason"),
                 human_attention_required=result.get("human_attention_required"))
        return
    if mode == "inspect-decision":
        work_id = sys.argv[2]
        _, steering = call("GET", "/api/works/" + work_id + "/steering")
        _, attention = call("GET", "/api/attention?work_id=" + work_id)
        emit("decision", current_step=steering.get("current_step"),
             latest_decision=steering.get("latest_decision"),
             attention=attention)
        return
    if mode == "inspect-failure":
        work_id = sys.argv[2]
        for path in ("/api/works/" + work_id,
                     "/api/works/" + work_id + "/operations",
                     "/api/works/" + work_id + "/self-refine"):
            status, result = call("GET", path)
            if path.endswith(work_id) and isinstance(result, dict):
                result = {key: result.get(key) for key in (
                    "status", "execution_progress", "production_plan_runtime",
                    "current_production_run_id", "current_production_step",
                    "most_recent_meaningful_event", "result_summary")}
            emit("failure", path=path, status=status, result=result)
        return
    if mode == "inspect-provider":
        from sqlalchemy import create_engine, text
        engine = create_engine(Settings().database_url)
        with engine.connect() as connection:
            rows = connection.execute(text("""
                SELECT id, dispatch_id, attempt_id, outcome, summary, metadata
                FROM provider_execution_reports
                WHERE attempt_id IN (SELECT id FROM execution_attempts WHERE work_unit_id = :pwu)
                ORDER BY recorded_at
            """), {"pwu": sys.argv[2]}).mappings().all()
        for row in rows:
            metadata = row["metadata"] or {}
            emit("provider", id=str(row["id"]), dispatch_id=str(row["dispatch_id"]),
                 attempt_id=str(row["attempt_id"]), outcome=row["outcome"],
                 summary=row["summary"], metadata_keys=sorted(metadata),
                 terminal_executor_outcome=metadata.get("terminal_executor_outcome"),
                 failure_code=metadata.get("failure_code"))
        return
    if mode == "inspect-native":
        from sqlalchemy import create_engine, text
        engine = create_engine(Settings().database_url)
        attempt = sys.argv[2]
        with engine.connect() as connection:
            state = connection.execute(text("""
                SELECT terminal_outcome, blocker_reasons, effect_uncertainty,
                       current_step_sequence FROM native_attempt_states
                WHERE attempt_id = :attempt
            """), {"attempt": attempt}).mappings().first()
            steps = connection.execute(text("""
                SELECT sequence, kind, condition, result_payload
                FROM execution_steps WHERE attempt_id = :attempt ORDER BY sequence
            """), {"attempt": attempt}).mappings().all()
            events = connection.execute(text("""
                SELECT id, sequence, event_type, payload FROM execution_events
                WHERE attempt_id = :attempt ORDER BY sequence
            """), {"attempt": attempt}).mappings().all()
        emit("native-state", state=dict(state) if state else None)
        for step in steps:
            payload = step["result_payload"] or {}
            emit("native-step", sequence=step["sequence"], kind_name=step["kind"],
                 condition=step["condition"], result_keys=sorted(payload),
                 error_code=payload.get("error_code"), failure_code=payload.get("failure_code"),
                 outcome=payload.get("outcome"))
        for event in events:
            payload = event["payload"] or {}
            emit("native-event", id=str(event["id"]), sequence=event["sequence"],
                 event_type=event["event_type"], payload_keys=sorted(payload),
                 preflight_failure=(payload.get("failure") if event["event_type"]
                                    == "ExecutionWorkspacePreflightRejected" else None),
                 failure_family=payload.get("failure_family"),
                 signal=payload.get("signal"),
                 terminal_outcome=payload.get("terminal_outcome"),
                 stage=payload.get("stage"))
        return
    if mode == "inspect-workspace":
        from sqlalchemy import create_engine, text
        engine = create_engine(Settings().database_url)
        with engine.connect() as connection:
            row = connection.execute(text("""
                SELECT materialization_path, condition, host_storage_id,
                       manifest FROM execution_workspaces WHERE attempt_id = :attempt
            """), {"attempt": sys.argv[2]}).mappings().first()
        if row:
            manifest = row["manifest"] or {}
            emit("workspace", path=row["materialization_path"],
                 condition=row["condition"], host_storage_id=row["host_storage_id"],
                 manifest_keys=sorted(manifest), mounts=[{
                     "host_path": item.get("host_path"), "writable": item.get("writable")}
                     for item in manifest.get("mounts", [])])
        return
    if mode == "reproduce-observation":
        import tempfile
        from pathlib import Path
        from sqlalchemy import create_engine, text
        from spg.domain.native_execution import ExecutionBindingV2
        from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
        from spg.infrastructure.executor_runtime.production_evidence import observe_production_workspace
        engine = create_engine(Settings().database_url)
        with engine.connect() as connection:
            row = connection.execute(text("""
                SELECT binding_payload FROM native_attempt_bindings WHERE attempt_id = :attempt
            """), {"attempt": sys.argv[2]}).mappings().first()
        binding = ExecutionBindingV2.model_validate(row["binding_payload"])
        emit("binding-workspace", mounts=[{
            "host_path": item.host_path, "writable": item.writable,
            "mount_id": item.mount_id} for item in binding.workspace.mounts],
            source_mount_id=binding.source_vector.members[0].mount_id)
        with tempfile.TemporaryDirectory(prefix="gof-observe-") as temp:
            evidence_root = (Settings().native_executor_storage_root / "production-evidence"
                             if len(sys.argv) > 3 and sys.argv[3] == "actual-store"
                             else Path(temp))
            try:
                result = observe_production_workspace(binding,
                    ContentAddressedStorage(evidence_root), require_change=False)
                emit("observation", result="PASS", repository_revision=result["repository_revision"],
                     files_changed=result["files_changed"])
            except Exception as error:
                emit("observation", result="FAIL", exception=type(error).__name__,
                     message=str(error))
        return
    if mode == "timeline":
        from sqlalchemy import create_engine, text
        engine = create_engine(Settings().database_url)
        attempt = sys.argv[2]
        with engine.connect() as connection:
            rows = connection.execute(text("""
                SELECT event_type, created_at FROM execution_events
                WHERE attempt_id = :attempt ORDER BY sequence
            """), {"attempt": attempt}).mappings().all()
            prep = connection.execute(text("""
                SELECT prepared_at, workspace_path FROM attempt_preparations
                WHERE attempt_id = :attempt
            """), {"attempt": attempt}).mappings().first()
        emit("preparation", at=str(prep["prepared_at"]) if prep else None,
             path=prep["workspace_path"] if prep else None)
        for row in rows:
            emit("timeline", event_type=row["event_type"], at=str(row["created_at"]))
        return
    raise SystemExit("unknown mode")


if __name__ == "__main__":
    main()
