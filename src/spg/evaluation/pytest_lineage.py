"""Capture isolated owner evidence before fixture cleanup; never read production DB."""
import json
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from spg.infrastructure.persistence import metadata

TABLES = ("quality_campaign_runs", "quality_case_runs", "quality_run_members", "quality_run_controls", "plan_revisions", "production_runs", "production_admissibility_records", "product_works", "product_managed_sources", "work_source_bases", "production_work_units", "context_packages", "materialized_execution_inputs",
    "interaction_assessments", "interaction_turns", "interaction_turn_realizations", "interaction_turn_obligations",
    "pwu_contract_versions", "execution_attempts", "execution_dispatches", "execution_allocations",
    "executor_worker_registrations", "executor_queue", "production_snapshots", "proposed_repository_snapshots", "completion_evaluations", "verification_records",
    "baseline_candidates", "work_delivery_acceptances", "product_source_versions",
    "product_source_promotion_intents")
SAFE_COLUMNS = {"id", "run_id", "campaign_run_id", "parent_run_id", "case_version_id", "source_case_run_id", "disposition", "action", "work_id", "pwu_id", "work_unit_id", "task_contract_id", "attempt_id",
    "candidate_id", "worker_id", "condition", "status", "state", "generation", "lease_epoch",
    "source_revision", "source_tree", "revision", "tree", "source_baseline_id", "source_version",
    "package_fingerprint", "accepted_revision", "accepted_tree", "decision_id", "decision_version", "fingerprint", "contract_digest", "snapshot_id", "acceptance_id", "product_id", "version",
    "turn_id", "semantic_ir_id", "assessment_id", "basis_fingerprint",
    "context_ref", "content_fingerprint", "completion_contract_fingerprint",
    "context_package_content_fingerprint", "context_package_version", "input_fingerprint",
    "repository_revision", "repository_tree_identity", "context_package_id", "production_run_id", "plan_revision_id", "workspace_identity", "workspace_path", "workspace_id", "workspace_reference",
    "ecf_context_fingerprint", "ecf_context_package_id", "decision_context_id", "contract_id",
    "verified_output_baseline_id", "parent_baseline_ids", "contract_version_id", "contract_fingerprint",
    "result", "outcome", "node_id", "dependency_ids", "required", "kind", "revision_number", "obligation_fingerprint", "proposed_commit_identity", "tree_identity"}


# Project only typed identity/fingerprint facts from owner envelopes. Do not
# copy Human prose, prompts, credentials, tool output or the complete context.
def typed_references(value, path=""):
    out = {}
    if isinstance(value, dict):
        for key, item in value.items():
            location = path + "/" + key
            if key in SAFE_COLUMNS and isinstance(item, (str, int, list)):
                out[location] = item
            elif isinstance(item, (dict, list)):
                out.update(typed_references(item, location))
    elif isinstance(value, list):
        for n, item in enumerate(value[:100]):
            out.update(typed_references(item, path + "/" + str(n)))
    return out


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    # Some canonical tests deliberately delete their owner rows in a function
    # finally block. Observe typed returned owner receipts before that cleanup;
    # do not change owner code, assertions, inputs or returned results.
    import sys
    previous = sys.getprofile()
    receipts = []
    def observe(frame, event, value):
        if event != "return" or value is None or len(receipts) >= 40:
            return
        owner = frame.f_globals.get("__name__")
        name = frame.f_code.co_name
        if not ((owner == "spg.application.decision_context" and name == "lineage_for_work_task")
            or (owner == "spg.application.production_intelligence" and name == "build")):
            return
        if hasattr(value, "model_dump"):
            refs = typed_references(value.model_dump(mode="json"))
            if refs:
                receipts.append({"owner_function": owner + "." + name, "typed_references": refs})
    active = bool(os.environ.get("WATT_QUALITY_LINEAGE_FILE"))
    if active:
        sys.setprofile(observe)
    try:
        yield
    finally:
        if active:
            sys.setprofile(previous)
        item._quality_owner_receipts = receipts


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    result = yield
    report = result.get_result()
    if report.when != "call":
        return
    destination = os.environ.get("WATT_QUALITY_LINEAGE_FILE")
    url = os.environ.get("SPG_TEST_DATABASE_URL")
    if not destination or not url:
        return
    evidence = {"nodeid": item.nodeid, "outcome": report.outcome, "owners": {}}
    receipts = getattr(item, "_quality_owner_receipts", [])
    if receipts:
        evidence["owners"]["canonical_context_receipts"] = receipts
    tmp = item.funcargs.get("tmp_path")
    if tmp is not None:
        guardian = []
        for p in list(Path(tmp).rglob("*.json"))[:500]:
            if "guardian" not in str(p).lower() or p.stat().st_size > 1_000_000:
                continue
            try:
                r = json.loads(p.read_text())
                if isinstance(r, dict) and "gate" in r and "request_id" in r:
                    guardian.append({k: r.get(k) for k in ("request_id", "result_id", "candidate_id",
                        "candidate_fingerprint", "source_revision", "source_tree", "gate", "assessed_at")})
            except (ValueError, OSError):
                pass
        if guardian:
            evidence["guardian_results"] = guardian[:20]
    engine = create_engine(url)
    try:
        with engine.connect() as c:
            for name in TABLES:
                t = metadata.tables.get(name)
                if t is None:
                    continue
                envelopes = {"manifest", "completion_contract", "context_projection", "prepared_execution_request", "graph", "reconciliation_evidence"}
                columns = [x for x in t.columns if x.name in SAFE_COLUMNS or x.name in envelopes]
                if not columns:
                    continue
                rows = c.execute(select(*columns).limit(200)).mappings().all()
                if rows:
                    evidence["owners"][name] = [{k: (typed_references(v, k) if k in envelopes else v)
                        for k, v in dict(r).items()} for r in rows]
        p = Path(destination)
        previous = json.loads(p.read_text()) if p.exists() else []
        previous.append(evidence)
        p.write_text(json.dumps(previous, default=str))
    except Exception as e:
        evidence["capture_status"] = "UNAVAILABLE"
        evidence["error_type"] = type(e).__name__
        Path(destination).write_text(json.dumps([evidence]))
    finally:
        engine.dispose()
