"""Native investigation gates, evidence fidelity, replay and failure receipts."""
import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest

from spg.application.trace_analysis import TraceAnalysisService
from spg.config import Settings
from spg.domain.native_execution import InferenceAction, InferenceResponse, ToolCallProposal, canonical_digest
from spg.domain.trace_analysis import AnalysisReport, AnalysisTrigger, REGRESSION_CRITERIA, IssueClass
from spg.evaluation.contracts import QualityError
from spg.infrastructure.trace_analysis_evidence import EvidenceCatalog, RepositorySnapshot, time_boundary


def snapshot(work_id=None):
    wid = work_id or uuid4()
    return {"work_id": str(wid), "capture": {"consistency": "NON_ATOMIC_ACROSS_OWNERS"},
            "capture_warnings": ["raw failed response missing"],
            "lifecycle": {"work": {"work_id": str(wid), "state": "COMPLETED",
                "raw_user_requirement": "Create a static page", "desired_outcome": "static page"},
                "first_human_input": "Create a static page",
                "advanced": {"owners": {"execution_steps": [{"id": "failed-step",
                    "result_payload": {"reason_code": "NATIVE_DECISION_SCHEMA_REJECTED"}}]}}}}


def report(catalog):
    row = next(r for r in catalog.records.values() if r["group"] == "work")
    catalog.read(row["evidence_id"])
    inspection = catalog.inspect(row["evidence_id"])
    fact = {"statement": "Work is completed", "citations": [
        {"evidence_id": row["evidence_id"], "quote": "COMPLETED"}]}
    return {"work_id": catalog.snapshot["work_id"], "original_objective": fact,
            "expected_outcome": fact, "actual_execution_path": fact, "current_state": fact,
            "timeline": [dict(fact, stage="FINAL_STATE", timestamp=None)],
            "findings": [{"finding_id": "missing-raw", "classification": "UNKNOWN",
                "subject_evidence_id": row["evidence_id"],
                "inspection_id": inspection["inspection_id"],
                "epistemic_status": "UNKNOWN", "fact": fact, "analysis": "Exact invalid text unavailable",
                "repository_citations": [], "uncertainty": inspection["bounded_conclusion"],
                "recommendation": "Inspect existing owner evidence", "handling": "INVESTIGATE",
                "regression_qualification": REGRESSION_CRITERIA[IssueClass.UNKNOWN]}],
            "deferred_items": [{"statement": "Raw log investigation", "finding_ids": ["missing-raw"]}],
            "evidence_assessments": [{"family": c["family"], "check_id": c["check_id"],
                "availability": c["availability"], "statement": "Snapshot scope reviewed"}
                for c in catalog.reality()["families"]], "missing_evidence": []}


class Registry:
    def __init__(self, snapshot):
        self.snapshot, self.calls = snapshot, []
        self.state = "COMPLETED"

    def get(self, owner, wid):
        self.calls.append((owner, wid))
        if owner != "human:owner" or str(wid) != self.snapshot["work_id"]:
            raise QualityError("TRACE_SOURCE_NOT_FOUND")
        return {"work_id": str(wid), "product_id": str(uuid4()), "state": self.state}


class Exporter:
    def __init__(self, snapshot):
        self.snapshot, self.calls = snapshot, 0

    def capture(self, *args, **kwargs):
        self.calls += 1
        return {"trace.json": json.dumps(self.snapshot).encode()}


class NativeModel:
    """Scripted test model; never represented as live-model qualification."""
    def __init__(self, snap, *, reject_first=False, bad_terminal=False):
        self.catalog = EvidenceCatalog(snap)
        self.reject_first, self.bad_terminal = reject_first, bad_terminal
        self.requests = []

    async def infer(self, req):
        self.requests.append(req)
        candidate = report(self.catalog)
        if len(self.requests) == 1 and self.reject_first:
            candidate["current_state"]["citations"][0]["quote"] = "unobserved fabricated quote"
        if not req.previous_results or req.previous_results[-1]["condition"] == "FAILED":
            return InferenceResponse(action=InferenceAction.CONTINUE, summary="Verify report",
                working_plan=req.working_plan, tool_calls=(ToolCallProposal(proposal_index=0,
                    tool_identity="analysis.submit", arguments={"report": candidate}),))
        return InferenceResponse(action=InferenceAction.RESULT_READY, summary="Advisory report submitted",
            working_plan=req.working_plan, result_claim={"evidence_ids": [], "output_vector": {
                "report_digest": "wrong" if self.bad_terminal else canonical_digest(AnalysisReport.model_validate(candidate).model_dump(mode="json"))}})


def service(tmp_path, *, reject_first=False, bad_terminal=False):
    snap = snapshot()
    registry, exporter = Registry(snap), Exporter(snap)
    model = NativeModel(snap, reject_first=reject_first, bad_terminal=bad_terminal)
    s = TraceAnalysisService(None, Settings(native_executor_storage_root=tmp_path,
        native_executor_inference_model="scripted-test-only"), exporter=exporter, registry=registry,
        inference_factory=lambda: model, repository_factory=lambda *_: ({}, ["historical source unavailable"]))
    return s, snap, model


def test_native_kernel_report_and_durable_history_without_new_work(tmp_path):
    s, snap, model = service(tmp_path)
    trigger = AnalysisTrigger(request_id=uuid4(), rationale="Investigate")
    r = asyncio.run(s.analyze("human:owner", uuid4_from(snap), trigger))
    assert r["status"] == "COMPLETED" and r["verification"] == "CITATIONS_AND_STRUCTURE_PASS"
    assert r["semantic_qualification"] == "HUMAN_REVIEW_REQUIRED"
    assert r["production_work_created"] is False and r["authority"] == "ADVISORY_ONLY"
    detail = s.read("human:owner", uuid4_from(snap), trigger.request_id, detail=True)
    kinds = {event["kind"] for event in detail["execution_history"]}
    assert {"INVESTIGATION_BASIS", "INFERENCE_STARTED", "INFERENCE_FINISHED", "TOOL_FINISHED", "CHECKPOINT"} <= kinds
    assert "report_schema" in model.requests[0].context_facts[0]["payload"]
    assert s.list("human:owner", uuid4_from(snap))["items"][0]["request_id"] == str(trigger.request_id)


def uuid4_from(snap):
    from uuid import UUID
    return UUID(snap["work_id"])


def timed_report():
    catalog = EvidenceCatalog(snapshot())
    candidate = report(catalog)
    event_ids = []
    for index, timestamp in enumerate(("2026-10-05T16:58:12+00:00", "2026-10-05T16:59:24+00:00")):
        eid = catalog.add("execution_events", f"/fixture/events/{index}",
                          {"id": str(uuid4()), "created_at": timestamp, "signal": "FAILED"})
        catalog.read(eid)
        event_ids.append(eid)
    candidate["timeline"] = [{"stage": "FAILURE", "statement": "Recorded failure",
        "citations": [{"evidence_id": eid, "quote": "FAILED"}],
        "timestamp": catalog.values[eid]["created_at"],
        "timestamp_evidence_id": eid, "timestamp_field": "created_at"} for eid in event_ids]
    for item in candidate["timeline"]:
        item["time_interpretation"] = time_boundary("created_at")
    return catalog, candidate, event_ids


def test_timeline_times_are_original_observed_and_chronological():
    catalog, candidate, _ = timed_report()
    # Equivalent timezone representations identify the same original instant.
    candidate["timeline"][0]["timestamp"] = "2026-10-06T00:58:12+08:00"
    catalog.validate(AnalysisReport.model_validate(candidate))
    candidate["timeline"].reverse()
    with pytest.raises(ValueError, match="TIMELINE_EVENTS_MUST_BE_CHRONOLOGICAL"):
        catalog.validate(AnalysisReport.model_validate(candidate))


def test_one_incident_time_cannot_be_attached_to_another_incident():
    catalog, candidate, ids = timed_report()
    candidate["timeline"][0]["citations"].append({"evidence_id": ids[1], "quote": "FAILED"})
    with pytest.raises(ValueError, match="TIMELINE_DISTINCT_EVENTS_REQUIRE_SEPARATE_ENTRIES"):
        catalog.validate(AnalysisReport.model_validate(candidate))
    # An explicit undated composite is legal, without pretending a shared time.
    candidate["timeline"][0].update(timestamp=None, timestamp_evidence_id=None, timestamp_field=None)
    catalog.validate(AnalysisReport.model_validate(candidate))


@pytest.mark.parametrize("timestamp", ["2026-10-05T16:58:13+00:00", "2026-10-05T16:58:12", "not-a-time"])
def test_timeline_rejects_wrong_or_unzoned_original_time(timestamp):
    catalog, candidate, _ = timed_report()
    candidate["timeline"][0]["timestamp"] = timestamp
    with pytest.raises(ValueError, match="TIMELINE_TIME_DOES_NOT_MATCH_OWNER_FIELD"):
        catalog.validate(AnalysisReport.model_validate(candidate))


def test_timeline_unread_time_and_missing_source_are_rejected():
    catalog, candidate, ids = timed_report()
    catalog.observed_excerpts[ids[0]] = ["FAILED"]
    with pytest.raises(ValueError, match="TIMELINE_TIME_NOT_OBSERVED"):
        catalog.validate(AnalysisReport.model_validate(candidate))
    candidate["timeline"][0].pop("timestamp_evidence_id")
    with pytest.raises(ValueError, match="TIMELINE_TIME_REQUIRES_ORIGINAL_OWNER_FIELD"):
        AnalysisReport.model_validate(candidate)


def test_report_rejection_enters_existing_native_bounded_refinement(tmp_path):
    s, snap, model = service(tmp_path, reject_first=True)
    r = asyncio.run(s.analyze("human:owner", uuid4_from(snap), AnalysisTrigger(request_id=uuid4(), rationale="Investigate")))
    assert r["status"] == "COMPLETED"
    assert [v["verification"] for v in r["verification_receipts"]] == ["FAIL", "CITATIONS_AND_STRUCTURE_PASS"]
    assert r["refinement_feedback"][0]["status"] == "VERIFIED"
    assert any(f["fact_type"] == "RECENT_SELF_REFINE" for f in model.requests[1].context_facts)
    assert len(model.requests) == 3


def test_terminal_model_claim_cannot_replace_verified_submission(tmp_path):
    s, snap, _ = service(tmp_path, bad_terminal=True)
    r = asyncio.run(s.analyze("human:owner", uuid4_from(snap), AnalysisTrigger(request_id=uuid4(), rationale="Investigate")))
    assert r["status"] == "FAILED" and r["report"] is None


def test_idempotent_request_never_reissues_model_or_recaptures(tmp_path):
    s, snap, model = service(tmp_path)
    trigger = AnalysisTrigger(request_id=uuid4(), rationale="Investigate")
    first = asyncio.run(s.analyze("human:owner", uuid4_from(snap), trigger))
    second = asyncio.run(s.analyze("human:owner", uuid4_from(snap), trigger))
    assert first == second and len(model.requests) == 2 and s.exporter.calls == 1
    with pytest.raises(QualityError, match="ANALYSIS_REQUEST_ID_CONFLICT"):
        asyncio.run(s.analyze("human:owner", uuid4_from(snap), trigger.model_copy(update={"rationale": "changed"})))


def test_wrong_owner_and_active_work_rejected_before_capture_or_model(tmp_path):
    s, snap, model = service(tmp_path)
    trigger = AnalysisTrigger(request_id=uuid4(), rationale="Investigate")
    with pytest.raises(QualityError, match="TRACE_SOURCE_NOT_FOUND"):
        asyncio.run(s.analyze("human:foreign", uuid4_from(snap), trigger))
    s.registry.state = "RUNNING"
    with pytest.raises(QualityError, match="ANALYSIS_WORK_NOT_TERMINAL_OR_BLOCKED"):
        asyncio.run(s.analyze("human:owner", uuid4_from(snap), trigger))
    assert s.exporter.calls == 0 and not model.requests


def test_read_history_requires_current_owner(tmp_path):
    s, snap, _ = service(tmp_path)
    trigger = AnalysisTrigger(request_id=uuid4(), rationale="Investigate")
    asyncio.run(s.analyze("human:owner", uuid4_from(snap), trigger))
    with pytest.raises(QualityError, match="TRACE_SOURCE_NOT_FOUND"):
        s.read("human:foreign", uuid4_from(snap), trigger.request_id, detail=True)


def test_provider_failure_preserves_evidence_and_does_not_leak_exception_secrets(tmp_path):
    s, snap, _ = service(tmp_path)
    class Failed:
        async def infer(self, _):
            raise RuntimeError("api_key=must-never-be-persisted")
    s.inference_factory = Failed
    trigger = AnalysisTrigger(request_id=uuid4(), rationale="Investigate")
    r = asyncio.run(s.analyze("human:owner", uuid4_from(snap), trigger))
    assert r["status"] == "FAILED" and r["failure"]["error_type"] == "RuntimeError"
    assert "must-never" not in json.dumps(s.read("human:owner", uuid4_from(snap), trigger.request_id, detail=True))
    assert not (s.root / ".active-investigation").exists()


def test_crash_capacity_lock_is_not_silently_stolen(tmp_path):
    s, snap, model = service(tmp_path)
    (s.root / ".active-investigation").touch()
    with pytest.raises(QualityError, match="ANALYSIS_CAPACITY_BUSY"):
        asyncio.run(s.analyze("human:owner", uuid4_from(snap), AnalysisTrigger(request_id=uuid4(), rationale="Investigate")))
    assert not model.requests


@pytest.mark.parametrize("mutation, reason", [
    (lambda r: r.update(work_id=str(uuid4())), "REPORT_WORK_ID_MISMATCH"),
    (lambda r: r["current_state"]["citations"][0].update(evidence_id=str(uuid4())), "CITATION_NOT_OBSERVED"),
    (lambda r: r["current_state"]["citations"][0].update(quote="fake"), "CITATION_QUOTE_MISMATCH"),
])
def test_report_citations_are_exact_and_work_bound(mutation, reason):
    catalog = EvidenceCatalog(snapshot())
    r = report(catalog)
    mutation(r)
    with pytest.raises(ValueError, match=reason):
        catalog.validate(AnalysisReport.model_validate(r))


def test_root_cause_and_governance_classification_are_not_promoted_without_evidence():
    r = report(EvidenceCatalog(snapshot()))
    r["findings"][0]["epistemic_status"] = "ROOT_CAUSE_HYPOTHESIS"
    with pytest.raises(ValueError, match="repository evidence"):
        AnalysisReport.model_validate(r)
    r["findings"][0].update(epistemic_status="UNKNOWN", classification="GOVERNANCE_ISSUE")
    with pytest.raises(ValueError, match="classification boundary"):
        AnalysisReport.model_validate(r)


def test_exact_repository_read_ignores_dirty_worktree_and_denies_secrets(tmp_path):
    import subprocess
    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args], text=True).strip()
    git("init")
    (tmp_path / "src").mkdir()
    p = tmp_path / "src/runtime.py"
    p.write_text("original implementation\n")
    git("add", "src/runtime.py")
    git("-c", "user.name=fixture", "-c", "user.email=fixture@example.test", "commit", "-m", "fixture")
    revision = git("rev-parse", "HEAD")
    repo = RepositorySnapshot(key="runtime", path=tmp_path, revision=revision, roots=("src",))
    p.write_text("C3 temporary patch must not enter snapshot\n")
    assert "original implementation" in repo.read("src/runtime.py")["content"]
    assert "temporary patch" not in repo.read("src/runtime.py")["content"]
    assert "original implementation" in repo.search("original", "src")["matches"]
    for path in ("../private", "/etc/passwd", "src/.env", "src/holdout.json", "tests/outside.py"):
        with pytest.raises(ValueError, match="PATH_NOT_ADMITTED"):
            repo.read(path)


def test_snapshot_capacity_and_unknown_are_visible():
    snap = snapshot()
    snap["lifecycle"]["capture_truncation"] = {"execution_steps": {"observed_count": 100, "exported_count": 30}}
    catalog = EvidenceCatalog(snap)
    seed = catalog.seed()
    assert "100" in json.dumps(seed) and "raw failed response missing" in json.dumps(seed)
    assert catalog.index(group="execution_steps")["total"] == 1
    with pytest.raises(ValueError):
        catalog.index(limit=999)


def test_unread_fragment_cannot_be_used_as_a_valid_citation():
    catalog = EvidenceCatalog(snapshot())
    eid = catalog.add("fixture", "/fixture", "visible-head " + "x" * 100 + "unseen-tail")
    catalog.read(eid, limit=20)
    r = report(catalog)
    r["current_state"]["citations"] = [{"evidence_id": eid, "quote": "unseen-tail"}]
    with pytest.raises(ValueError, match="CITATION_QUOTE_MISMATCH"):
        catalog.validate(AnalysisReport.model_validate(r))


def test_cancelled_analysis_keeps_durable_partial_history(tmp_path):
    s, snap, _ = service(tmp_path)
    class Cancelled:
        async def infer(self, _):
            raise asyncio.CancelledError()
    s.inference_factory = Cancelled
    trigger = AnalysisTrigger(request_id=uuid4(), rationale="Investigate")
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(s.analyze("human:owner", uuid4_from(snap), trigger))
    r = s.read("human:owner", uuid4_from(snap), trigger.request_id, detail=True)
    assert r["status"] == "INTERRUPTED" and r["execution_history"]
    assert not (s.root / ".active-investigation").exists()


def test_investigation_tools_still_require_exact_grants(tmp_path):
    from spg.domain.native_execution import (
        NativeExecutionConflict, SourceVector, ToolExecutionRequest, WorkspaceManifest, WorkspaceMount,
    )
    from spg.infrastructure.trace_analysis_evidence import AnalysisTools
    tools = AnalysisTools(EvidenceCatalog(snapshot()), {}).registry()
    attempt, pwu, wid = uuid4(), uuid4(), uuid4()
    workspace = WorkspaceManifest(workspace_id=uuid4(), work_id=wid, pwu_id=pwu,
        attempt_id=attempt, source_vector_digest=SourceVector().digest,
        host_storage_id="fixture", environment_profile_digest="a" * 64,
        mounts=(WorkspaceMount(mount_id="artifacts", host_path=str(tmp_path),
                container_path="/artifacts", writable=True),), evidence_namespace="fixture", retention_policy="fixture")
    req = ToolExecutionRequest(delivery_id=uuid4(), attempt_id=attempt, worker_epoch=1,
        step_id=uuid4(), capability_grants=(), workspace=workspace,
        proposal=ToolCallProposal(proposal_index=0, tool_identity="evidence.index", arguments={}))
    with pytest.raises(NativeExecutionConflict, match="not granted"):
        asyncio.run(tools.execute(req))
    req = req.model_copy(update={"proposal": ToolCallProposal(proposal_index=0,
        tool_identity="file.write", arguments={"path": "src/x.py", "content": "bad"})})
    with pytest.raises(NativeExecutionConflict, match="not registered"):
        asyncio.run(tools.execute(req))


def test_native_refinement_patches_retained_report_and_rechecks_all_gates(tmp_path):
    s, snap, _ = service(tmp_path)
    class PatchingModel(NativeModel):
        async def infer(self, req):
            self.requests.append(req)
            if len(self.requests) == 1:
                candidate = report(self.catalog)
                candidate["deferred_items"][0]["finding_ids"] = ["abbreviated-invalid-id"]
                proposal = ToolCallProposal(proposal_index=0, tool_identity="analysis.submit", arguments={"report": candidate})
            elif len(self.requests) == 2:
                failure = req.previous_results[-1]["output"]
                assert failure["valid_finding_ids"] == ["missing-raw"]
                assert any(issue.get("location") == ["deferred_items", 0, "finding_ids"] for issue in failure["issues"])
                proposal = ToolCallProposal(proposal_index=0, tool_identity="analysis.revise", arguments={
                    "draft_id": failure["draft_id"], "edits": [{"op": "replace", "path": "/deferred_items/0/finding_ids", "value": ["missing-raw"]}]})
            else:
                return InferenceResponse(action=InferenceAction.RESULT_READY, summary="Verified retained report",
                    working_plan=req.working_plan, result_claim={"output_vector": {
                        "report_digest": req.previous_results[-1]["output"]["report_digest"]}})
            return InferenceResponse(action=InferenceAction.CONTINUE, summary="Bounded report refinement",
                                     working_plan=req.working_plan, tool_calls=(proposal,))
    model = PatchingModel(snap)
    s.inference_factory = lambda: model
    trigger = AnalysisTrigger(request_id=uuid4(), rationale="Investigate")
    r = asyncio.run(s.analyze("human:owner", uuid4_from(snap), trigger))
    assert r["status"] == "COMPLETED" and len(model.requests) == 3
    assert len(r["draft_digests"]) == 2
    detail = s.read("human:owner", uuid4_from(snap), trigger.request_id, detail=True)
    assert any(d["deferred_items"][0]["finding_ids"] == ["abbreviated-invalid-id"] for d in detail["report_drafts"].values())
    assert detail["report"]["deferred_items"][0]["finding_ids"] == ["missing-raw"]
    assert detail["report"]["findings"][0]["analysis"] == "Exact invalid text unavailable"


def test_public_tool_contract_exposes_report_schema_and_actual_bounds():
    from spg.infrastructure.trace_analysis_evidence import AnalysisTools
    contracts = {t["identity"]: t["input_schema"] for t in AnalysisTools(EvidenceCatalog(snapshot()), {}).registry().contracts()}
    assert contracts["evidence.index"]["properties"]["limit"]["maximum"] == 40
    assert contracts["repository.read"]["properties"]["lines"]["maximum"] == 200
    report_schema = contracts["analysis.submit"]
    assert "Finding" in report_schema["$defs"]
    assert report_schema["properties"]["report"]["additionalProperties"] is False


def test_wrong_snapshot_is_retained_as_failure_before_model(tmp_path):
    s, snap, model = service(tmp_path)
    s.exporter.snapshot = snapshot()
    r = asyncio.run(s.analyze("human:owner", uuid4_from(snap), AnalysisTrigger(request_id=uuid4(), rationale="Investigate")))
    assert r["status"] == "FAILED" and r["failure"]["reason_code"] == "ANALYSIS_SNAPSHOT_WORK_MISMATCH"
    assert not model.requests


def test_decoded_json_quote_requires_the_exact_observed_encoded_fragment():
    catalog = EvidenceCatalog(snapshot())
    quote = 'line one\n"line two"'
    eid = catalog.add("fixture", "/encoded", {"message": quote, "tail": "unseen\nvalue"})
    catalog.read(eid, limit=45)
    r = json.loads(json.dumps(report(catalog)))
    r["current_state"]["citations"] = [{"evidence_id": eid, "quote": quote}]
    catalog.validate(AnalysisReport.model_validate(r))
    r["current_state"]["citations"][0]["quote"] = "unseen\nvalue"
    with pytest.raises(ValueError, match="CITATION_QUOTE_MISMATCH"):
        catalog.validate(AnalysisReport.model_validate(r))


def test_all_bounded_citation_errors_are_returned_together():
    catalog = EvidenceCatalog(snapshot())
    r = report(catalog)
    # Independent copies: changing one shared fixture fact must not change all.
    r = json.loads(json.dumps(r))
    r["original_objective"]["citations"][0]["quote"] = "fabricated first"
    r["current_state"]["citations"][0]["quote"] = "fabricated second"
    with pytest.raises(ValueError) as caught:
        catalog.validate(AnalysisReport.model_validate(r))
    assert [i["location"][0] for i in caught.value.issues] == ["original_objective", "current_state"]


def test_original_incident_cannot_be_omitted_with_empty_findings():
    snap = snapshot()
    snap["lifecycle"]["advanced"]["owners"]["execution_steps"][0]["condition"] = "FAILED"
    catalog = EvidenceCatalog(snap)
    r = report(catalog)
    r.update(findings=[], deferred_items=[])
    with pytest.raises(ValueError, match="OBSERVED_INCIDENT_REQUIRES_FINDING"):
        catalog.validate(AnalysisReport.model_validate(r))
    r = report(catalog)
    eid = next(eid for eid, row in catalog.records.items() if row["group"] == "execution_steps")
    catalog.read(eid)
    r["findings"][0]["fact"] = {"statement": "Failed schema decision; raw invalid text unknown",
        "citations": [{"evidence_id": eid, "quote": "NATIVE_DECISION_SCHEMA_REJECTED"}]}
    r["findings"][0]["subject_evidence_id"] = eid
    inspection = catalog.inspect(eid)
    r["findings"][0].update(inspection_id=inspection["inspection_id"], uncertainty=inspection["bounded_conclusion"])
    catalog.validate(AnalysisReport.model_validate(r))


def test_no_incident_does_not_force_an_invented_finding():
    catalog = EvidenceCatalog(snapshot())
    r = report(catalog)
    r.update(findings=[], deferred_items=[])
    catalog.validate(AnalysisReport.model_validate(r))


def test_retained_draft_is_readable_but_cannot_be_cited_as_owner_truth():
    from types import SimpleNamespace
    from spg.infrastructure.trace_analysis_evidence import AnalysisTools
    catalog = EvidenceCatalog(snapshot())
    tools = AnalysisTools(catalog, {})
    r = report(catalog)
    r["deferred_items"][0]["finding_ids"] = ["invalid"]
    request = SimpleNamespace(delivery_id=uuid4(), proposal=SimpleNamespace(
        tool_identity="analysis.submit", arguments={"report": r}))
    receipt = asyncio.run(tools.execute(request))
    eid = receipt.output["draft_id"]
    draft = catalog.read(eid)
    assert draft["trust"] == "MODEL_PROPOSAL_NOT_OWNER_EVIDENCE"
    assert "invalid" in draft["content"]
    r = json.loads(json.dumps(report(catalog)))
    r["current_state"]["citations"] = [{"evidence_id": eid, "quote": "Work is completed"}]
    with pytest.raises(ValueError, match="MODEL_PROPOSAL_NOT_OWNER_EVIDENCE"):
        catalog.validate(AnalysisReport.model_validate(r))


def test_index_snippet_can_be_cited_but_unread_body_cannot():
    catalog = EvidenceCatalog(snapshot())
    eid = catalog.add("fixture", "/index-snippet", "returned-snippet " + "x" * 400 + "unread-tail")
    catalog.index(group="fixture")
    r = json.loads(json.dumps(report(catalog)))
    r["current_state"]["citations"] = [{"evidence_id": eid, "quote": "returned-snippet"}]
    catalog.validate(AnalysisReport.model_validate(r))
    r["current_state"]["citations"][0]["quote"] = "unread-tail"
    with pytest.raises(ValueError, match="CITATION_QUOTE_MISMATCH"):
        catalog.validate(AnalysisReport.model_validate(r))


def evidence_snapshot():
    snap = snapshot()
    pwu, session, attempt = (str(uuid4()) for _ in range(3))
    snap["capture_warnings"] = []
    snap["lifecycle"].update(guardian=[{"result_id": str(uuid4()), "gate": "PASS", "evidence": [
        {"status_code": 200, "response_sha256": "d" * 64, "runtime_ref": "candidate-preview:fixture",
         "obligation_ref": "an-arbitrary-route"}]}],
        served_delivery={"actions": [], "client_received": "UNAVAILABLE", "client_saved": "UNAVAILABLE",
                         "completion_basis": "server transfer only"})
    snap["lifecycle"]["advanced"]["owners"].update(execution_sessions=[{"id": session, "pwu_id": pwu}],
        execution_attempts=[{"id": attempt, "work_unit_id": pwu}])
    return snap


def test_preview_and_transfer_are_distinct_producer_scopes():
    catalog = EvidenceCatalog(evidence_snapshot())
    preview = catalog.check("PREVIEW_HTTP")
    transfer = catalog.check("DELIVERY_TRANSFER")
    assert preview["total_matches"] == 1 and preview["availability"] == "PRESENT"
    assert preview["examples"][0]["value"]["status_code"] == 200
    assert preview["examples"][0]["group"] == "guardian"
    assert transfer["examples"][0]["value"]["client_received"] == "UNAVAILABLE"
    with pytest.raises(ValueError, match="FIXED_BY_FAMILY"):
        catalog.check("PREVIEW_HTTP", group="served_delivery")


@pytest.mark.parametrize("actions", [[], [{"id": "arbitrary-action", "condition": "FAILED"}]])
def test_transfer_rule_is_not_a_completion_observation(actions):
    snap = evidence_snapshot()
    snap["lifecycle"]["served_delivery"].update(actions=actions,
        completion_basis="ASGI_SEND_COMPLETED proves server send only")
    catalog = EvidenceCatalog(snap)
    check = catalog.check("DELIVERY_TRANSFER")
    assert check["availability"] == "PRESENT"
    value = check["examples"][0]["value"]
    assert value["action_count"] == len(actions) and value["actions"] == actions
    assert value["completion_rule_description"] == "ASGI_SEND_COMPLETED proves server send only"
    assert "completion_basis" not in value and "not a completed transfer" in value["interpretation"]
    eid = check["examples"][0]["evidence_id"]
    assert "not an observed event" in catalog.read(eid)["semantics"]["boundary"]


@pytest.mark.parametrize("family,group,quote", [
    ("PREVIEW_HTTP", "served_delivery", "UNAVAILABLE"),
    ("DELIVERY_TRANSFER", "guardian", "200"),
])
def test_fact_cannot_cross_producer_surface(family, group, quote):
    catalog = EvidenceCatalog(evidence_snapshot())
    r = json.loads(json.dumps(report(catalog)))
    eid = next(eid for eid, row in catalog.records.items() if row["group"] == group)
    catalog.read(eid)
    r["current_state"].update(evidence_family=family, citations=[{"evidence_id": eid, "quote": quote}])
    with pytest.raises(ValueError, match="SOURCE_SURFACE_MISMATCH"):
        catalog.validate(AnalysisReport.model_validate(r))


def test_assurance_pass_without_http_receipt_is_not_http_observation():
    snap = evidence_snapshot()
    snap["lifecycle"]["guardian"][0].pop("evidence")
    catalog = EvidenceCatalog(snap)
    assert catalog.check("PREVIEW_HTTP")["availability"] == "NOT_OBSERVED_IN_CAPTURE"
    eid = next(eid for eid, row in catalog.records.items() if row["group"] == "guardian")
    assert "PREVIEW_HTTP" not in catalog.records[eid]["semantics"]["families"]


def test_lineage_exposes_owner_aliases_without_reading_every_row():
    catalog = EvidenceCatalog(evidence_snapshot())
    links = catalog.check("EXECUTION_RELATIONSHIP")
    pwu = catalog.snapshot["lifecycle"]["advanced"]["owners"]["execution_sessions"][0]["pwu_id"]
    same = [link for link in links["examples"] if link["value"] == pwu]
    assert {link["group"] for link in same} == {"execution_sessions", "execution_attempts"}
    assert all(link["identity_kind"] == "PWU" for link in same)
    specific = catalog.check("EXECUTION_RELATIONSHIP", group="execution_sessions", field="/pwu_id")
    assert specific["availability"] == "PRESENT"


@pytest.mark.parametrize("family,group,field", [
    ("PREVIEW_HTTP", None, None),
    ("EXECUTION_RELATIONSHIP", "execution_sessions", "/pwu_id"),
])
def test_available_evidence_cannot_be_claimed_missing(family, group, field):
    catalog = EvidenceCatalog(evidence_snapshot())
    r = report(catalog)
    receipt = catalog.check(family, group=group, field=field)
    r["missing_evidence"] = [{"statement": "Absent", "family": family,
        "check_id": receipt["check_id"], "availability": "NOT_OBSERVED_IN_CAPTURE"}]
    with pytest.raises(ValueError, match="MISSING_EVIDENCE_CONTRADICTS"):
        catalog.validate(AnalysisReport.model_validate(r))


def test_absence_is_snapshot_scoped_and_redaction_preserves_unknown():
    catalog = EvidenceCatalog(evidence_snapshot())
    check = catalog.check("OWNER_RECORD", group="execution_steps", field="/result_payload/raw_response")
    assert check["availability"] == "NOT_OBSERVED_IN_CAPTURE"
    assert check["scope"] == "FROZEN_EXPORTED_OWNER_RECORDS_ONLY"
    r = report(catalog)
    r["missing_evidence"] = [{"statement": check["bounded_conclusion"],
        "family": "OWNER_RECORD", "check_id": check["check_id"], "availability": check["availability"]}]
    r["evidence_assessments"].append({"statement": check["bounded_conclusion"], "family": "OWNER_RECORD",
        "check_id": check["check_id"], "availability": check["availability"]})
    r["findings"][0].update(scope_check_ids=[check["check_id"]], analysis=check["bounded_conclusion"])
    eid = next(eid for eid, row in catalog.records.items() if row["group"] == "execution_steps")
    inspection = catalog.inspect(eid)
    r["findings"][0].update(subject_evidence_id=eid, inspection_id=inspection["inspection_id"], uncertainty=inspection["bounded_conclusion"],
        fact={"statement": "Recorded inference rejection", "citations": [{"evidence_id": eid, "quote": "NATIVE_DECISION_SCHEMA_REJECTED"}]})
    catalog.validate(AnalysisReport.model_validate(r))
    snap = evidence_snapshot()
    snap["lifecycle"]["advanced"]["owners"]["execution_steps"][0]["result_payload"]["raw_response"] = "[REDACTED_FIELD]"
    assert EvidenceCatalog(snap).check("OWNER_RECORD", group="execution_steps",
        field="/result_payload/raw_response")["availability"] == "INCOMPLETE_CAPTURE"
    with pytest.raises(ValueError, match="GROUP_NOT_CAPTURED"):
        catalog.check("OWNER_RECORD", group="not-exported", field="/id")


def test_report_requires_full_family_reconciliation_and_checked_gaps():
    catalog = EvidenceCatalog(evidence_snapshot())
    r = report(catalog)
    r["evidence_assessments"] = []
    with pytest.raises(ValueError, match="RECONCILIATION_REQUIRED"):
        catalog.validate(AnalysisReport.model_validate(r))
    r = report(catalog)
    r["evidence_assessments"][0]["availability"] = "NOT_OBSERVED_IN_CAPTURE"
    with pytest.raises(ValueError, match="ASSESSMENT_MUST_MATCH"):
        catalog.validate(AnalysisReport.model_validate(r))
    r = report(catalog)
    r["missing_evidence"] = ["Unread records are absent"]
    with pytest.raises(ValueError):
        AnalysisReport.model_validate(r)


def test_wrong_selector_root_is_not_false_negative_evidence():
    catalog = EvidenceCatalog(evidence_snapshot())
    with pytest.raises(ValueError, match=r"use /\* to enumerate"):
        catalog.check("OWNER_RECORD", group="execution_sessions", field="*")
    assert catalog.check("OWNER_RECORD", group="execution_sessions", field="/*")["availability"] == "PRESENT"
    with pytest.raises(ValueError, match="CHECK_SELECTOR_ROOT_NOT_IN_RECORD_SCHEMA"):
        catalog.check("EXECUTION_RELATIONSHIP", group="execution_sessions", field="/0/pwu_id")
    with pytest.raises(ValueError, match="CHECK_SELECTOR_ROOT_NOT_IN_RECORD_SCHEMA"):
        catalog.check("OWNER_RECORD", group="execution_sessions", field="/misspelled_pwu_id")
    assert catalog.check("EXECUTION_RELATIONSHIP", group="execution_sessions", field="/pwu_id")["availability"] == "PRESENT"


def associated_incident_catalog():
    snap = snapshot()
    receipt_a, receipt_b, incident_a, incident_b, attempt = (str(uuid4()) for _ in range(5))
    owners = snap["lifecycle"]["advanced"]["owners"]
    owners["self_refine_events"] = [dict(id=incident, operation_id=attempt,
        affected_component="arbitrary-tool", failure_family="SAME_FAILURE",
        diagnostic_evidence={"receipt_ref": "native-receipt:" + receipt})
        for incident, receipt in [(incident_a, receipt_a), (incident_b, receipt_b)]]
    owners["effect_receipts"] = [dict(id=receipt, condition="FAILED", output={"message": "same failure"})
                                  for receipt in [receipt_a, receipt_b]]
    catalog = EvidenceCatalog(snap)
    events = [eid for eid, row in catalog.records.items() if row["group"] == "self_refine_events"]
    receipts = [eid for eid, row in catalog.records.items() if row["group"] == "effect_receipts"]
    return catalog, events, receipts


def test_same_attempt_same_error_cannot_join_distinct_incidents():
    catalog, events, receipts = associated_incident_catalog()
    r = json.loads(json.dumps(report(catalog)))
    for eid in events + receipts:
        catalog.read(eid)
    f = r["findings"][0]
    f["subject_evidence_id"] = events[0]
    inspection = catalog.inspect(events[0])
    f.update(inspection_id=inspection["inspection_id"], uncertainty=inspection["bounded_conclusion"])
    f["fact"] = {"statement": "Recorded failure", "citations": [
        {"evidence_id": events[0], "quote": "SAME_FAILURE"},
        {"evidence_id": receipts[0], "quote": "same failure"}]}
    catalog.validate(AnalysisReport.model_validate(r))
    assert catalog.association(events[0], receipts[0])["basis"] == "EXPLICIT_OWNER_REFERENCE"
    assert catalog.association(receipts[0], events[0])["status"] == "RELATED"
    f["fact"]["citations"][1]["evidence_id"] = events[1]
    f["fact"]["citations"][1]["quote"] = "SAME_FAILURE"
    with pytest.raises(ValueError, match="OWNER_ASSOCIATION_NOT_ESTABLISHED"):
        catalog.validate(AnalysisReport.model_validate(r))
    f["fact"]["citations"][1] = {"evidence_id": receipts[1], "quote": "same failure"}
    with pytest.raises(ValueError, match="OWNER_ASSOCIATION_NOT_ESTABLISHED"):
        catalog.validate(AnalysisReport.model_validate(r))


def test_related_record_metadata_does_not_observe_unread_body():
    catalog, events, receipts = associated_incident_catalog()
    detail = catalog.read(events[0])
    assert receipts[0] in {r["evidence_id"] for r in detail["related_records"]["items"]}
    assert receipts[0] not in catalog.observed
    r = json.loads(json.dumps(report(catalog)))
    f = r["findings"][0]
    f["subject_evidence_id"] = events[0]
    f["fact"]["citations"] = [{"evidence_id": events[0], "quote": "SAME_FAILURE"},
                              {"evidence_id": receipts[0], "quote": "same failure"}]
    # A plain read exposes only relationship hints; the mandatory inspect is
    # deliberately omitted here. It must not be bypassed by a snippet citation.
    with pytest.raises(ValueError, match="CITATION_NOT_OBSERVED|FINDING_REQUIRES_SUBJECT_OWNER_INSPECTION"):
        catalog.validate(AnalysisReport.model_validate(r))


def test_checked_field_cannot_be_promoted_to_missing_whole_response_or_history():
    catalog = EvidenceCatalog(evidence_snapshot())
    check = catalog.check("OWNER_RECORD", group="execution_steps", field="/result_payload/raw_response")
    r = json.loads(json.dumps(report(catalog)))
    f = r["findings"][0]
    eid = next(eid for eid, row in catalog.records.items() if row["group"] == "execution_steps")
    inspection = catalog.inspect(eid)
    f.update(subject_evidence_id=eid, inspection_id=inspection["inspection_id"], uncertainty=inspection["bounded_conclusion"],
             fact={"statement": "Recorded inference rejection", "citations": [{"evidence_id": eid, "quote": "NATIVE_DECISION_SCHEMA_REJECTED"}]})
    f.update(scope_check_ids=[check["check_id"]], analysis=check["bounded_conclusion"])
    r["missing_evidence"] = [{"statement": check["bounded_conclusion"], "family": "OWNER_RECORD",
        "check_id": check["check_id"], "availability": check["availability"]}]
    catalog.validate(AnalysisReport.model_validate(r))
    f["analysis"] = "Watt never stores raw responses anywhere"
    with pytest.raises(ValueError, match="CAPTURE_CONCLUSION_MUST_COPY_CHECKED_BOUNDARY"):
        catalog.validate(AnalysisReport.model_validate(r))
    f["analysis"] = check["bounded_conclusion"]
    r["missing_evidence"][0]["statement"] = "All historical provider response bodies are missing"
    with pytest.raises(ValueError, match="MISSING_EVIDENCE_MUST_COPY_BOUNDED_CONCLUSION"):
        catalog.validate(AnalysisReport.model_validate(r))


def test_random_failure_regression_qualifies_handling_not_zero_future_errors():
    r = report(EvidenceCatalog(snapshot()))
    f = r["findings"][0]
    f.update(classification="RUNTIME_MODEL_VARIANCE", handling="SELF_REFINE_RETRY_REGENERATE",
             regression_qualification="No model failure may ever recur")
    with pytest.raises(ValueError, match="REGRESSION_CRITERION_MUST_MATCH_GOVERNED_OUTCOME"):
        AnalysisReport.model_validate(r)
    f["regression_qualification"] = REGRESSION_CRITERIA[IssueClass.RUNTIME_MODEL_VARIANCE]
    AnalysisReport.model_validate(r)


def test_diagnostic_expected_behavior_does_not_become_execution_receipt():
    catalog, events, _ = associated_incident_catalog()
    semantics = catalog.read(events[0])["semantics"]
    assert semantics["surface"] == "OWNER_REFINEMENT_DIAGNOSIS"
    assert semantics["field_roles"]["diagnostic_evidence"] == "DIAGNOSIS_NOT_EXECUTION_RECEIPT"
    assert semantics["field_roles"]["expected_reality"] == "EXPECTED_NOT_OBSERVED"
    assert "do not establish executed file changes" in semantics["boundary"]
    r = report(catalog)
    f = r["findings"][0]
    f.update(epistemic_status="ROOT_CAUSE_HYPOTHESIS", repository_citations=[{
        "evidence_id": str(uuid4()), "quote": "comparison"}], analysis="A proposed constraint definitely executed")
    with pytest.raises(ValueError, match="CAUSAL_HYPOTHESIS_MUST_BE_EXPLICIT"):
        AnalysisReport.model_validate(r)
    f["analysis"] = "假设：可能与候选理解偏差相关；没有原始执行证据时保留 UNKNOWN。"
    AnalysisReport.model_validate(r)


@pytest.mark.parametrize("command", ["arbitrary-executable", "unlisted-reader", "自定义命令"])
def test_real_owner_effect_namespace_resolves_parameters_without_work_rules(command):
    snap = snapshot()
    effect, receipt, recovery, other_effect, other_receipt = [str(uuid4()) for _ in range(5)]
    owners = snap["lifecycle"]["advanced"]["owners"]
    owners["execution_effects"] = [
        {"id": effect, "semantic_input": {"argv": [command, "--generic-option"], "cwd": "."}},
        {"id": other_effect, "semantic_input": {"argv": ["unrelated-command"]}}]
    owners["effect_receipts"] = [
        {"id": receipt, "effect_id": effect, "condition": "FAILED", "output": {"error_type": "ValueError"}},
        {"id": other_receipt, "effect_id": other_effect, "condition": "FAILED", "output": {"error_type": "ValueError"}}]
    owners["self_refine_events"] = [{"id": recovery, "diagnostic_evidence": {"receipt_ref": "native-receipt:" + receipt}}]
    c = EvidenceCatalog(snap)
    rid = next(eid for eid, value in c.values.items() if isinstance(value, dict) and value.get("id") == receipt)
    effect_id = next(eid for eid, value in c.values.items() if isinstance(value, dict) and value.get("id") == effect)
    unrelated = next(eid for eid, value in c.values.items() if isinstance(value, dict) and value.get("id") == other_effect)
    assert c.association(rid, effect_id)["basis"] == "EXPLICIT_OWNER_REFERENCE"
    assert effect_id not in c.observed
    bundle = c.inspect(rid)
    assert effect_id in c.observed and unrelated not in c.observed
    row = next(r for r in bundle["records"] if r["evidence_id"] == effect_id)
    argv = next(f for f in row["fields"] if f["field"] == "/semantic_input")
    assert argv["read_status"] == "READ" and command in argv["original_excerpt"]
    assert c.association(rid, unrelated)["status"] == "NOT_ESTABLISHED"


def test_inspection_capacity_never_marks_unreturned_input_as_read():
    c = EvidenceCatalog(snapshot())
    effect = str(uuid4())
    eid = c.add("execution_effects", "/fixture/effect", {"id": effect, "semantic_input": {"argv": ["x" * 5000]}})
    rid = c.add("effect_receipts", "/fixture/receipt", {"id": str(uuid4()), "effect_id": effect, "output": {"error_type": "ValueError"}})
    first = c.inspect(rid)
    data = next(f for r in first["records"] if r["evidence_id"] == eid for f in r["fields"] if f["field"] == "/semantic_input")
    assert data["availability"] == "PRESENT" and data["read_status"] == "NOT_READ_CAPACITY"
    assert not any('x' * 5000 in s for s in c.observed_excerpts[eid])
    c.read(eid)
    second = c.inspect(rid)
    assert next(f for r in second["records"] if r["evidence_id"] == eid for f in r["fields"] if f["field"] == "/semantic_input")["read_status"] == "READ"


def test_redacted_empty_and_unexported_fields_remain_distinct():
    snap = snapshot()
    snap["lifecycle"]["advanced"]["owners"]["execution_steps"] = [
        {"id": str(uuid4()), "result_payload": {"raw_response": "[REDACTED_FIELD]"}},
        {"id": str(uuid4()), "result_payload": {"raw_response": ""}},
        {"id": str(uuid4()), "result_payload": {"reason_code": "INVALID"}}]
    c = EvidenceCatalog(snap)
    check = c.check("OWNER_RECORD", group="execution_steps", field="/result_payload/raw_response")
    assert check["field_states"] == {"AVAILABLE": 0, "REDACTED": 1, "EMPTY": 1, "NOT_EXPORTED": 1}
    assert check["availability"] == "INCOMPLETE_CAPTURE"


@pytest.mark.parametrize("field", ["analysis", "recommendation", "regression_scenario"])
def test_absence_cannot_escape_checked_boundaries_into_other_prose(field):
    c = EvidenceCatalog(snapshot())
    r = report(c)
    r["findings"][0][field] = "完整响应未保留，平台从未保存原始参数。"
    with pytest.raises(ValueError, match="EVIDENCE_ABSENCE_BELONGS_IN_CHECKED_UNCERTAINTY"):
        c.validate(AnalysisReport.model_validate(r))


def test_findings_cannot_claim_unbounded_uncertainty_or_borrow_inspection():
    c = EvidenceCatalog(snapshot())
    r = report(c)
    r["findings"][0]["uncertainty"] = "No raw response was ever retained"
    with pytest.raises(ValueError, match="UNCERTAINTY_MUST_COPY_INSPECTION"):
        c.validate(AnalysisReport.model_validate(r))
    r = report(c)
    r["findings"][0]["inspection_id"] = str(uuid4())
    with pytest.raises(ValueError, match="FINDING_REQUIRES_SUBJECT_OWNER_INSPECTION"):
        c.validate(AnalysisReport.model_validate(r))


def test_creation_time_requires_snapshot_state_boundary():
    c, r, _ = timed_report()
    r["timeline"][0]["time_interpretation"] = "Recovery definitely finished at creation time"
    with pytest.raises(ValueError, match="TIMELINE_REQUIRES_EXACT_TIME_BOUNDARY"):
        c.validate(AnalysisReport.model_validate(r))


@pytest.mark.parametrize("group", ["self_refine_events", "recovery"])
def test_refinement_created_at_does_not_timestamp_later_recovered_status(group):
    c = EvidenceCatalog(snapshot())
    r = report(c)
    eid = c.add(group, "/fixture/recovery", {"id": str(uuid4()),
        "created_at": "2026-10-05T10:00:00+00:00", "updated_at": "2026-10-05T10:01:00+00:00",
        "status": "VERIFIED", "final_result": "LOCAL_OBLIGATION_RECOVERED"})
    c.read(eid)
    r["timeline"] = [{"stage": "RECOVERY_REFINEMENT", "statement": "Recorded LOCAL_OBLIGATION_RECOVERED",
        "citations": [{"evidence_id": eid, "quote": "LOCAL_OBLIGATION_RECOVERED"}],
        "timestamp": c.values[eid]["created_at"], "timestamp_evidence_id": eid,
        "timestamp_field": "created_at", "time_interpretation": time_boundary("created_at")}]
    with pytest.raises(ValueError, match="TIMELINE_CREATION_CANNOT_TIMESTAMP_RECOVERY_STATE"):
        c.validate(AnalysisReport.model_validate(r))
    r["timeline"][0].update(timestamp=c.values[eid]["updated_at"], timestamp_field="updated_at",
                            time_interpretation=time_boundary("updated_at"))
    inspection = c.inspect(eid)
    r["findings"][0].update(subject_evidence_id=eid, inspection_id=inspection["inspection_id"],
        uncertainty=inspection["bounded_conclusion"], fact={"statement": "Recorded recovery",
        "citations": [{"evidence_id": eid, "quote": "VERIFIED"}]})
    c.validate(AnalysisReport.model_validate(r))


def test_unrelated_owner_gap_cannot_be_attached_to_another_subject():
    c = EvidenceCatalog(evidence_snapshot())
    r = report(c)
    check = c.check("OWNER_RECORD", group="execution_steps", field="/result_payload/raw_response")
    f = r["findings"][0]
    f.update(scope_check_ids=[check["check_id"]], analysis=check["bounded_conclusion"])
    with pytest.raises(ValueError, match="CHECK_OWNER_SCOPE_NOT_ASSOCIATED_WITH_FINDING"):
        c.validate(AnalysisReport.model_validate(r))


def test_seed_stays_in_context_budget_and_does_not_observe_omitted_bodies():
    from spg.infrastructure.trace_analysis_evidence import text
    snap = snapshot()
    owners = snap["lifecycle"]["advanced"]["owners"]
    owners["self_refine_events"] = [
        {"id": str(uuid4()), "diagnostic_evidence": {"payload": "x" * 12000},
         "condition": "FAILED", "marker": "only-original-" + str(uuid4())}
        for _ in range(20)]
    catalog = EvidenceCatalog(snap)
    seed = catalog.seed()
    assert len(text(seed)) <= 44000
    returned = {part["evidence_id"] for part in seed["initial_evidence"]}
    omitted = [eid for eid, row in catalog.records.items()
               if row["group"] == "self_refine_events" and eid not in returned]
    assert omitted
    assert not any(eid in catalog.observed for eid in omitted)
    assert catalog.index(group="self_refine_events")["total"] == 20


def test_recovery_projection_preserves_owner_identity_and_semantics():
    c = EvidenceCatalog(snapshot())
    value = {"id": str(uuid4()), "diagnostic_evidence": {"signal": "example"}}
    original = c.add("self_refine_events", "/fixture/original", value)
    projected = c.add("recovery", "/fixture/projected", value)
    unrelated = c.add("recovery", "/fixture/other", dict(value, id=str(uuid4())))
    assert c.association(original, projected)["basis"] == "SAME_OWNER_IDENTITY_PROJECTION"
    assert c.association(original, unrelated)["status"] == "NOT_ESTABLISHED"
    assert c.records[original]["semantics"] == c.records[projected]["semantics"]
    assert projected in {r["evidence_id"] for r in c.inspect(original)["records"]}
