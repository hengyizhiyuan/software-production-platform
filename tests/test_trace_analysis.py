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
    inspection = next((item for item in catalog.inspections.values() if item["subject_evidence_id"] == row["evidence_id"]), None) or catalog.inspect(row["evidence_id"])
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
            "deferred_items": [{"statement": "Raw log investigation", "evidence_family": "OWNER_RECORD", "finding_ids": ["missing-raw"]}],
            "evidence_assessments": [{"family": c["family"], "check_id": c["check_id"],
                "availability": c["availability"], "statement": c["bounded_conclusion"]}
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
        self.catalog.seed()  # Mirror the original initial inspection returned by the service.
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
        output = req.previous_results[-1]["output"]
        if output.get("next_action") == "analysis.review":
            return InferenceResponse(action=InferenceAction.CONTINUE, summary="Review original evidence and conclusion boundaries",
                working_plan=req.working_plan, tool_calls=(ToolCallProposal(proposal_index=0,
                    tool_identity="analysis.review", arguments={"draft_id":output["draft_id"], "items":[
                        dict(target, judgment="QUALIFIED", rationale="Scoped fixture observation; no independent semantic assurance is claimed")
                        for target in output["review_targets"]]}),))
        return InferenceResponse(action=InferenceAction.RESULT_READY, summary="Advisory report and self-review recorded",
            working_plan=req.working_plan, result_claim={"evidence_ids": [], "output_vector": {
                "report_digest": "wrong" if self.bad_terminal else output["report_digest"]}})



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
    assert [v["verification"] for v in r["verification_receipts"]] == ["FAIL", "CITATIONS_AND_STRUCTURE_PASS", "CITATIONS_AND_STRUCTURE_PASS"]
    assert r["refinement_feedback"][0]["status"] == "VERIFIED"
    assert any(f["fact_type"] == "RECENT_SELF_REFINE" for f in model.requests[1].context_facts)
    assert len(model.requests) == 4


def test_terminal_model_claim_cannot_replace_verified_submission(tmp_path):
    s, snap, _ = service(tmp_path, bad_terminal=True)
    r = asyncio.run(s.analyze("human:owner", uuid4_from(snap), AnalysisTrigger(request_id=uuid4(), rationale="Investigate")))
    assert r["status"] == "FAILED" and r["report"] is None


def test_idempotent_request_never_reissues_model_or_recaptures(tmp_path):
    s, snap, model = service(tmp_path)
    trigger = AnalysisTrigger(request_id=uuid4(), rationale="Investigate")
    first = asyncio.run(s.analyze("human:owner", uuid4_from(snap), trigger))
    second = asyncio.run(s.analyze("human:owner", uuid4_from(snap), trigger))
    assert first == second and len(model.requests) == 3 and s.exporter.calls == 1
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


def test_repository_multiline_excerpt_is_exact_and_excludes_unread_source(tmp_path):
    import subprocess
    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args], text=True).strip()
    git("init")
    (tmp_path / "src").mkdir()
    source = "header\nif diagnostic_list:\n    record_diagnosis()\nunread_tail()\n"
    (tmp_path / "src/runtime.py").write_text(source)
    git("add", ".")
    git("-c", "user.name=fixture", "-c", "user.email=fixture@example.test", "commit", "-m", "fixture")
    repo = RepositorySnapshot(key="runtime", path=tmp_path, revision=git("rev-parse", "HEAD"), roots=("src",))
    value = repo.read("src/runtime.py", start_line=2, lines=2)
    assert value["content"] == "if diagnostic_list:\n    record_diagnosis()\n"
    assert (value["start_line"], value["end_line"], value["next_line"]) == (2, 3, 4)
    catalog = EvidenceCatalog(snapshot())
    eid = catalog.add("repository_read", "/fixture/source", value, repository=True)
    catalog.read(eid)
    r = report(catalog)
    r["findings"][0]["repository_citations"] = [{"evidence_id": eid, "quote": value["content"]}]
    catalog.validate(AnalysisReport.model_validate(r))
    r["findings"][0]["repository_citations"][0]["quote"] += "unread_tail()"
    with pytest.raises(ValueError, match="CITATION_QUOTE_MISMATCH"):
        catalog.validate(AnalysisReport.model_validate(r))




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
                assert next(i for i in failure["issues"] if i.get("location") == ["deferred_items", 0, "finding_ids"])["rejected_value"] == ["abbreviated-invalid-id"]
                assert any(issue.get("location") == ["deferred_items", 0, "finding_ids"] for issue in failure["issues"])
                proposal = ToolCallProposal(proposal_index=0, tool_identity="analysis.revise", arguments={
                    "draft_id": failure["draft_id"], "edits": [{"op": "replace", "path": "/deferred_items/0/finding_ids", "value": ["missing-raw"]}]})
            elif req.previous_results[-1]["output"].get("next_action") == "analysis.review":
                pending = req.previous_results[-1]["output"]
                proposal = ToolCallProposal(proposal_index=0, tool_identity="analysis.review", arguments={
                    "draft_id": pending["draft_id"], "items": [dict(t,judgment="QUALIFIED",rationale="Scoped fixture sources and qualified interpretation") for t in pending["review_targets"]]})
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
    assert r["status"] == "COMPLETED" and len(model.requests) == 4
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
    assert c.inspect(original)["identical_owner_projections"][projected] == original


@pytest.mark.parametrize("family", ["DELIVERY_TRANSFER", "PREVIEW_HTTP", "EXECUTION_RELATIONSHIP"])
def test_recommendation_surface_cannot_borrow_unrelated_finding(family):
    c = EvidenceCatalog(snapshot())
    r = report(c)
    eid = c.add("guardian", "/fixture/guardian", {"id": str(uuid4()), "gate": "PASS"})
    inspection = c.inspect(eid)
    r["findings"][0].update(subject_evidence_id=eid, inspection_id=inspection["inspection_id"],
        uncertainty=inspection["bounded_conclusion"], fact={"statement":"Guardian gate",
            "citations":[{"evidence_id":eid, "quote":"PASS"}]})
    r["deferred_items"][0]["evidence_family"] = family
    with pytest.raises(ValueError, match="RECOMMENDATION_FAMILY_REQUIRES_FINDING_SUBJECT_SURFACE"):
        c.validate(AnalysisReport.model_validate(r))




def test_transfer_recommendation_accepts_its_own_audit_subject():
    c = EvidenceCatalog(snapshot())
    r = report(c)
    eid = c.add("served_delivery", "/fixture/transfer", {"actions":[], "client_saved":"UNAVAILABLE"})
    inspection = c.inspect(eid)
    r["findings"][0].update(subject_evidence_id=eid, inspection_id=inspection["inspection_id"],
        uncertainty=inspection["bounded_conclusion"], fact={"statement":"Audit client state",
            "citations":[{"evidence_id":eid, "quote":"UNAVAILABLE"}]})
    r["deferred_items"][0].update(evidence_family="DELIVERY_TRANSFER", statement="Evaluate client receipt observations")
    c.validate(AnalysisReport.model_validate(r))


def test_checked_boundary_markers_materialize_only_verified_receipts():
    c = EvidenceCatalog(snapshot())
    r = report(c)
    r["findings"][0]["uncertainty"] = "INSPECTED_OWNER_BOUNDARY"
    for a in r["evidence_assessments"]:a["statement"] = "CHECKED_FIELD_SCOPE"
    original = json.loads(json.dumps(r))
    materialized = c.materialize_boundaries(AnalysisReport.model_validate(r)).model_dump(mode="json")
    assert r == original
    assert materialized["findings"][0]["fact"] == original["findings"][0]["fact"] | {"evidence_family":"OWNER_RECORD"}
    assert materialized["findings"][0]["analysis"] == original["findings"][0]["analysis"]
    assert materialized["deferred_items"] == original["deferred_items"]
    assert "本次关联读取仅限冻结导出" in materialized["findings"][0]["checked_boundaries"][0]
    for a in materialized["evidence_assessments"]:
        assert a["checked_boundary"] == c.checks[a["check_id"]]["bounded_conclusion"]
        assert a["statement"] == "CHECKED_FIELD_SCOPE"
    r["findings"][0]["inspection_id"] = str(uuid4())
    with pytest.raises(ValueError, match="FINDING_REQUIRES_SUBJECT_OWNER_INSPECTION"):
        c.materialize_boundaries(AnalysisReport.model_validate(r))


def test_checked_markers_do_not_allow_present_evidence_to_be_called_missing():
    c = EvidenceCatalog(evidence_snapshot())
    r = report(c)
    eid = next(eid for eid,row in c.records.items() if row["group"] == "served_delivery")
    inspection = c.inspect(eid);check = c.check("DELIVERY_TRANSFER")
    r["findings"][0].update(subject_evidence_id=eid, inspection_id=inspection["inspection_id"],
        uncertainty="INSPECTED_OWNER_BOUNDARY", scope_check_ids=[check["check_id"]],
        analysis="CHECKED_FIELD_SCOPE", fact={"statement":"Existing audit", "citations":[{"evidence_id":eid,"quote":"UNAVAILABLE"}]})
    with pytest.raises(ValueError, match="PRESENT_CHECK_CANNOT_SUPPORT_MISSING_FIELD_FINDING"):
        c.materialize_boundaries(AnalysisReport.model_validate(r))




def test_time_marker_does_not_change_an_event_or_hide_recovery_creation_error():
    c,r,_=timed_report()
    for t in r["timeline"]:t["time_interpretation"]="ORIGINAL_OWNER_TIME_BOUNDARY"
    output=c.materialize_boundaries(AnalysisReport.model_validate(r)).model_dump(mode="json")
    for old,new in zip(r["timeline"],output["timeline"]):
        assert old["timestamp"]==new["timestamp"] and old["statement"]==new["statement"]
        assert new["time_interpretation"]==old["time_interpretation"]
        assert new["owner_time_boundary"]==time_boundary(old["timestamp_field"])


def test_unknown_gap_markers_keep_the_exact_performed_field_scope():
    c=EvidenceCatalog(evidence_snapshot());r=report(c)
    eid=next(eid for eid,row in c.records.items() if row["group"]=="execution_steps")
    inspection=c.inspect(eid);check=c.check("OWNER_RECORD",group="execution_steps",field="/result_payload/raw_response")
    r["findings"][0].update(subject_evidence_id=eid,inspection_id=inspection["inspection_id"],
        uncertainty="INSPECTED_OWNER_BOUNDARY",scope_check_ids=[check["check_id"]],analysis="CHECKED_FIELD_SCOPE",
        fact={"statement":"Owner payload inspected", "citations":[{"evidence_id":eid,"quote":"result_payload"}]})
    r["missing_evidence"]=[{"statement":"CHECKED_FIELD_SCOPE","family":"OWNER_RECORD", "check_id":check["check_id"],"availability":check["availability"]}]
    r["evidence_assessments"].append({"statement":"CHECKED_FIELD_SCOPE","family":"OWNER_RECORD","check_id":check["check_id"],"availability":check["availability"]})
    output=c.materialize_boundaries(AnalysisReport.model_validate(r)).model_dump(mode="json")
    assert output["findings"][0]["analysis"]==r["findings"][0]["analysis"]
    assert output["findings"][0]["checked_boundaries"][-1]==check["bounded_conclusion"]
    assert output["missing_evidence"][0]["statement"]==r["missing_evidence"][0]["statement"]
    assert output["missing_evidence"][0]["checked_boundary"]==check["bounded_conclusion"]
    r["evidence_assessments"][0]["availability"]="INCOMPLETE_CAPTURE"
    with pytest.raises(ValueError,match="EVIDENCE_ASSESSMENT_MUST_MATCH_SEEDED_FAMILY_LOOKUP"):
        c.materialize_boundaries(AnalysisReport.model_validate(r))


def test_native_audit_counts_are_current_investigation_planning_only(tmp_path):
    from spg.application.trace_analysis import AnalysisJournal
    from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
    journal=AnalysisJournal(ContentAddressedStorage(tmp_path),"test-investigation",None)
    journal.append("INFERENCE_STARTED",{})
    journal.append("TOOL_STARTED",{})
    journal.append("TOOL_FINISHED",{})
    assert journal.event_counts=={"INFERENCE_STARTED":1,"TOOL_STARTED":1,"TOOL_FINISHED":1}
    snap=evidence_snapshot()
    snap["lifecycle"]["advanced"]["owners"]["execution_steps"][0]["condition"]="FAILED"
    c=EvidenceCatalog(snap);seed=c.seed()
    assert seed["incident_targets"]
    for target in seed["incident_targets"]:
        assert c.records[target["evidence_id"]]["group"]==target["group"]
        assert target["group"] in {"self_refine_events","execution_steps","effect_receipts"}


def test_field_lookup_bounds_whole_nested_values_without_denoting_absence():
    snap=snapshot();payload={"items":[{"description":"x"*1000,"index":i} for i in range(200)]}
    snap["lifecycle"]["advanced"]["owners"]["execution_steps"][0]["request_payload"]=payload
    c=EvidenceCatalog(snap);result=c.check("OWNER_RECORD",group="execution_steps",field="/request_payload")
    assert result["availability"]=="PRESENT" and result["field_states"]["AVAILABLE"]==1
    value=result["examples"][0]["value"]
    assert value["visibility"]=="NOT_RETURNED_CAPACITY" and value["serialized_bytes"]>1500
    assert len(json.dumps(result).encode())<10000
    assert value["read_required"]["evidence_id"] not in c.observed


@pytest.mark.parametrize("hole",[False,True])
def test_large_original_field_paging_tracks_real_coverage_without_unread_holes(hole):
    c=EvidenceCatalog(snapshot())
    eid=c.add("execution_effects","/fixture/large-parameters",{"id":str(uuid4()),
        "semantic_input":{"argv":["arbitrary-command","x"*30000]}})
    first=c.inspect(eid)
    field=lambda value:next(f for r in value["records"] if r["evidence_id"]==eid for f in r["fields"] if f["field"]=="/semantic_input")
    assert field(first)["read_status"]=="NOT_READ_CAPACITY"
    c.read(eid,offset=0,limit=16000)
    c.read(eid,offset=16001 if hole else 16000,limit=24000)
    final=field(c.inspect(eid))
    assert final["read_status"]==("NOT_READ_CAPACITY" if hole else "READ")
    if not hole:assert final["previous_original_read"] is True


def test_runtime_commit_time_uses_only_observed_original_owner_field():
    c,r,_=timed_report()
    eid=c.add("runtime_commit","/fixture/runtime-commit",{"id":str(uuid4()),"committed_at":"2026-10-05T12:00:00+00:00"})
    c.read(eid)
    r["timeline"]=[{"stage":"FINAL_STATE","statement":"Recorded runtime commit", "citations":[{"evidence_id":eid,"quote":"committed_at"}],"timestamp":c.values[eid]["committed_at"],"timestamp_evidence_id":eid,"timestamp_field":"committed_at","time_interpretation":"ORIGINAL_OWNER_TIME_BOUNDARY"}]
    output=c.materialize_boundaries(AnalysisReport.model_validate(r))
    assert "运行时提交" in output.timeline[0].owner_time_boundary
    r["timeline"][0]["timestamp"]="2026-10-05T13:00:00+00:00"
    with pytest.raises(ValueError,match="TIMELINE_TIME_DOES_NOT_MATCH_OWNER_FIELD"):
        c.materialize_boundaries(AnalysisReport.model_validate(r))


def test_inspection_reuses_only_actually_read_original_fields():
    c=EvidenceCatalog(snapshot());eid=c.add("execution_effects","/fixture/commands",{"id":str(uuid4()),"semantic_input":{"argv":["generic-command","--flag"],"cwd":"."}})
    first=c.inspect(eid);before=list(c.observed_excerpts[eid]);second=c.inspect(eid)
    field=lambda result:next(f for r in result["records"] if r["evidence_id"]==eid for f in r["fields"] if f["field"]=="/semantic_input")
    assert "generic-command" in field(first)["original_excerpt"]
    assert field(second)["read_status"]=="READ" and field(second)["previous_original_read"] is True
    assert "original_excerpt" not in field(second) and c.observed_excerpts[eid]==before
    other=c.add("execution_effects","/fixture/unread",{"id":str(uuid4()),"semantic_input":{"argv":["different-command"]}})
    assert "different-command" in next(f for r in c.inspect(other)["records"] if r["evidence_id"]==other for f in r["fields"] if f["field"]=="/semantic_input")["original_excerpt"]


def test_identical_owner_projection_deduplication_never_grants_unread_alias_authority():
    c=EvidenceCatalog(snapshot());value={"id":str(uuid4()),"signal":"arbitrary-signal","status":"VERIFIED"}
    original=c.add("self_refine_events","/fixture/original",value);alias=c.add("recovery","/fixture/alias",value)
    inspected=c.inspect(original)
    assert [r["evidence_id"] for r in inspected["records"]]==[original]
    assert inspected["identical_owner_projections"]=={alias:original}
    assert alias not in c.observed and c.association(original,alias)["basis"]=="SAME_OWNER_IDENTITY_PROJECTION"
    conflicting=c.add("recovery","/fixture/conflict",dict(value,status="FAILED"))
    inspected=c.inspect(original)
    assert conflicting in [r["evidence_id"] for r in inspected["records"]]


@pytest.mark.parametrize("operation",["read","search","diff"])
def test_root_cause_requires_implementation_excerpt_not_only_final_net_changes(operation):
    c=EvidenceCatalog(snapshot());r=report(c)
    base={"repository":"arbitrary-repository","revision":"a"*40}
    value=base|({"path":"src/example.py","blob":"b"*40,"content":"10: record_signal(condition)"} if operation=="read" else {"matches":"a:src/example.py:10: record_signal(condition)"} if operation=="search" else {"changed_paths":["src/example.py"],"patch":"+record_signal(condition)"})
    eid=c.add("repository","/fixture/source",value,repository=True);c.read(eid)
    r["findings"][0].update(epistemic_status="ROOT_CAUSE_HYPOTHESIS",analysis="假设：若该条件成立，则该实现可能产生诊断；历史实现身份保持 UNKNOWN。",repository_citations=[{"evidence_id":eid,"quote":"record_signal(condition)"}])
    if operation!="read":
        with pytest.raises(ValueError,match="ROOT_CAUSE_REQUIRES_IMPLEMENTATION_EXCERPT"):
            c.materialize_boundaries(AnalysisReport.model_validate(r))
    else:
        c.materialize_boundaries(AnalysisReport.model_validate(r))


def test_removing_a_citation_cannot_keep_an_uncited_original_owner_claim():
    c=EvidenceCatalog(snapshot());r=report(c);other_id=str(uuid4());eid=c.add("execution_evidence","/fixture/other",{"id":other_id,"evidence_type":"arbitrary-evidence"})
    c.read(eid);r["findings"][0]["fact"]["statement"]="Other original Owner "+other_id+" proves an unrelated result"
    with pytest.raises(ValueError,match="FACT_NAMES_UNCITED_OWNER_RECORD"):
        c.materialize_boundaries(AnalysisReport.model_validate(r))


def test_positive_execution_receipts_require_an_execution_timeline_entry():
    c=EvidenceCatalog(snapshot());r=report(c);eid=c.add("effect_receipts","/fixture/settled",{"id":str(uuid4()),"condition":"SETTLED","output":{"path":"arbitrary.txt"}})
    assert eid in c.seed()["execution_stage_targets"]
    with pytest.raises(ValueError,match="OBSERVED_EXECUTION_STAGE_MUST_BE_RECONSTRUCTED"):
        c.materialize_boundaries(AnalysisReport.model_validate(r))
    c.read(eid);r["timeline"].insert(0,{"stage":"EXECUTION","statement":"Recorded settled effect", "citations":[{"evidence_id":eid,"quote":"SETTLED"}]})
    c.materialize_boundaries(AnalysisReport.model_validate(r))




@pytest.mark.parametrize("group",["plan_history","production_work_units"])
def test_original_planning_records_cannot_be_omitted_from_timeline(group):
    c=EvidenceCatalog(snapshot());r=report(c);eid=c.add(group,"/fixture/planning",{"id":str(uuid4()),"objective":"arbitrary objective"})
    assert eid in c.seed()["planning_stage_targets"]
    with pytest.raises(ValueError,match="OBSERVED_PLANNING_STAGE_MUST_BE_RECONSTRUCTED"):
        c.materialize_boundaries(AnalysisReport.model_validate(r))
    c.read(eid);r["timeline"].insert(0,{"stage":"PLANNING","statement":"Recorded planning objective", "citations":[{"evidence_id":eid,"quote":"arbitrary objective"}]})
    c.materialize_boundaries(AnalysisReport.model_validate(r))








def test_time_rejection_returns_bounded_exact_draft_entry_without_changing_it():
    from types import SimpleNamespace
    from spg.infrastructure.trace_analysis_evidence import AnalysisTools
    c=EvidenceCatalog(snapshot());r=report(c)
    eid=c.add("self_refine_events","/fixture/diagnosis",{"id":str(uuid4()),"created_at":"2026-10-05T12:00:00+00:00","status":"VERIFIED"});c.read(eid)
    entry={"stage":"RECOVERY_REFINEMENT","statement":"Owner recorded VERIFIED", "citations":[{"evidence_id":eid,"quote":"VERIFIED"}],
        "timestamp":"2026-10-05T13:00:00+00:00","timestamp_evidence_id":eid,"timestamp_field":"created_at","time_interpretation":"ORIGINAL_OWNER_TIME_BOUNDARY"}
    r["timeline"]=[entry]
    tools=AnalysisTools(c,{})
    req=SimpleNamespace(delivery_id=uuid4(),proposal=SimpleNamespace(tool_identity="analysis.submit",arguments={"report":r}))
    result=asyncio.run(tools.execute(req))
    issue=next(i for i in result.output["issues"] if i.get("reason","").startswith("TIMELINE_TIME_DOES_NOT_MATCH_OWNER_FIELD"))
    assert issue["rejected_context"]=={"path":"/timeline/0","value":entry}
    assert tools.drafts[result.output["draft_id"]]["timeline"][0]==entry
    assert tools.accepted_report is None
    assert sum(len(json.dumps(i.get(k),ensure_ascii=False).encode()) for i in result.output["issues"] for k in ["rejected_value","rejected_context"] if k in i)<8500


@pytest.mark.parametrize("pointer,expected", [
    ("/input/argv/1", "--random-option"), ("/input/cwd", "nested"),
    ("/a~1b/~0key/0", "escaped-field")])
def test_nested_original_field_read_preserves_exact_bytes_and_does_not_read_parent(pointer, expected):
    c=EvidenceCatalog(snapshot())
    value={"huge": "x"*40000, "input":{"argv":["arbitrary-command","--random-option"],"cwd":"nested"}, "a/b":{"~key":["escaped-field"]}}
    eid=c.add("execution_effects","/fixture/nested",value)
    read=c.read(eid,field=pointer)
    left,right=read["original_body_range"]
    assert json.loads(read["content"])==expected
    assert read["content"]==c.records[eid]["body"][left:right]
    assert not c._range_read(eid,0,len(c.records[eid]["body"]))
    with pytest.raises(ValueError,match="READ_FIELD_NOT_FOUND"):
        c.read(eid,field="/missing/field")
    with pytest.raises(ValueError,match="READ_FIELD_INVALID_ESCAPE"):
        c.read(eid,field="/a~2b")


def test_nested_original_paging_requires_contiguous_observed_range():
    c=EvidenceCatalog(snapshot());eid=c.add("execution_steps","/fixture/paging",{"payload":{"value":"abcdefghij"},"unrelated":"x"*40000})
    a=c.read(eid,field="/payload/value",limit=5)
    b=c.read(eid,field="/payload/value",offset=6,limit=10)
    assert not c._range_read(eid,a["original_body_range"][0],b["original_body_range"][1])
    c.read(eid,field="/payload/value",offset=5,limit=1)
    assert c._range_read(eid,a["original_body_range"][0],b["original_body_range"][1])


def test_original_tool_identities_read_within_large_request_without_marking_it_read():
    c=EvidenceCatalog(snapshot());eid=c.add("execution_steps","/fixture/request",{"request_payload":{"available_tools":[{"identity":"original.inspect","schema":{"description":"x"*70000}}]}})
    result=c.inspect(eid)
    fields=next(r["fields"] for r in result["records"] if r["evidence_id"]==eid)
    parent=next(f for f in fields if f["field"]=="/request_payload")
    nested=next(f for f in fields if f["field"]=="/request_payload/available_tools/0/identity")
    assert parent["read_status"]=="NOT_READ_CAPACITY"
    assert json.loads(nested["original_excerpt"])=="original.inspect"
    assert "not an executed effect" in nested["authority_boundary"]
    assert not c._range_read(eid,0,len(c.records[eid]["body"]))












def test_explicit_original_disposal_observation_is_distinct_from_capture_gap():
    c=EvidenceCatalog(snapshot());r=report(c)
    eid=c.add("retention_receipts","/fixture/disposal",{"id":str(uuid4()),"observation":"原始记录已删除"})
    f=r["findings"][0];f.update(subject_evidence_id=eid,inspection_id=c.inspect(eid)["inspection_id"],uncertainty="INSPECTED_OWNER_BOUNDARY",fact={"statement":"Owner observation: 原始记录已删除","citations":[{"evidence_id":eid,"quote":"原始记录已删除"}]},recommendation="核对原始记录已删除的处置收据")
    c.materialize_boundaries(AnalysisReport.model_validate(r))


@pytest.mark.parametrize("analysis", [
    "如果接纳记录满足该条件，代码会写入完成状态；历史加载版本仍待查。",
    "A possible explanation is this accepted-input branch; the historical implementation remains unknown.",
    "这是一项源码比较假设：满足条件时返回完成状态，尚不能认定历史调用过该实现。",
    "若预算内的重新推理采用该已读实现，接纳输入会进入完成分支；此处不声称实际重试过。"])
def test_semantically_qualified_source_comparisons_do_not_require_a_sentence_template(analysis):
    c=EvidenceCatalog(snapshot());r=report(c)
    code=c.add("repository","/fixture/actual-source",{"repository":"source","revision":"a"*40,"path":"src/state.py","blob":"b"*40,"content":"if acceptance == 'ACCEPT': work.state = 'COMPLETED'"},repository=True);c.read(code)
    f=r["findings"][0];f.update(epistemic_status="ROOT_CAUSE_HYPOTHESIS",analysis=analysis,
        repository_citations=[{"evidence_id":code,"quote":"if acceptance == 'ACCEPT': work.state = 'COMPLETED'"}],
        regression_qualification="在原权限和预算里核验可恢复结果；否则如实停止。")
    result=c.materialize_boundaries(AnalysisReport.model_validate(r))
    assert result.findings[0].analysis==analysis and result.findings[0].regression_qualification==f["regression_qualification"]
    f["repository_citations"][0]["evidence_id"]=str(uuid4())
    with pytest.raises(ValueError):c.materialize_boundaries(AnalysisReport.model_validate(r))


def invoke_analysis(tools, identity, args):
    from types import SimpleNamespace
    return asyncio.run(tools.execute(SimpleNamespace(delivery_id=uuid4(),proposal=SimpleNamespace(tool_identity=identity,arguments=args))))


def review_items(pending, *, revise=False):
    return [dict(t,judgment="REVISE" if revise and t["target_path"]=="/findings/0" else "QUALIFIED",
        rationale="原始快照没有提供处置事件；应限于实际可读字段，不能将取证范围扩为历史丢失。" if revise and t["target_path"]=="/findings/0" else "按原始字段和已检查范围限定解释；仍需独立审查。") for t in pending["review_targets"]]


def test_structural_pass_is_pending_until_native_self_review_and_changed_report_is_reviewed_again():
    from spg.infrastructure.trace_analysis_evidence import AnalysisTools
    c=EvidenceCatalog(snapshot());tools=AnalysisTools(c,{});r=report(c)
    submitted=invoke_analysis(tools,"analysis.submit",{"report":r})
    assert submitted.condition.value=="SETTLED" and tools.accepted_report is None
    assert "report_digest" not in submitted.output and submitted.output["next_action"]=="analysis.review"
    pending=submitted.output
    feedback=invoke_analysis(tools,"analysis.review",{"draft_id":pending["draft_id"],"items":review_items(pending,revise=True)})
    assert feedback.condition.value=="FAILED" and tools.accepted_report is None
    assert feedback.output["failure_class"]=="RUNTIME_MODEL_VARIANCE"
    revised=invoke_analysis(tools,"analysis.revise",{"draft_id":pending["draft_id"],"edits":[{"op":"replace","path":"/findings/0/recommendation","value":"仅核对已导出的原始信息，处置状态保持 UNKNOWN。"}]})
    assert tools.accepted_report is None and revised.output["draft_id"]!=pending["draft_id"]
    reviewed=invoke_analysis(tools,"analysis.review",{"draft_id":revised.output["draft_id"],"items":review_items(revised.output)})
    assert reviewed.condition.value=="SETTLED" and tools.accepted_digest==reviewed.output["report_digest"]
    assert tools.accepted_report["findings"][0]["recommendation"]=="仅核对已导出的原始信息，处置状态保持 UNKNOWN。"
    assert tools.accepted_review["authority"]=="MODEL_SELF_REVIEW_PROPOSAL_NOT_INDEPENDENT_ASSURANCE"
    assert tools.drafts[pending["draft_id"]]==r


@pytest.mark.parametrize("invalid",["coverage","source","empty_rationale"])
def test_native_self_review_cannot_forge_coverage_or_source_identity(invalid):
    from spg.infrastructure.trace_analysis_evidence import AnalysisTools
    c=EvidenceCatalog(snapshot());tools=AnalysisTools(c,{});pending=invoke_analysis(tools,"analysis.submit",{"report":report(c)}).output
    items=review_items(pending)
    if invalid=="coverage":items.pop()
    if invalid=="source":items[0]["evidence_ids"]=[str(uuid4())]
    if invalid=="empty_rationale":items[0]["rationale"]=""
    result=invoke_analysis(tools,"analysis.review",{"draft_id":pending["draft_id"],"items":items})
    assert result.condition.value=="FAILED" and tools.accepted_report is None


class SemanticRefinementModel(NativeModel):
    """Scripted semantic feedback for recovery control qualification, not live-model evidence."""
    async def infer(self, req):
        self.requests.append(req);n=len(self.requests)
        if n==1:
            candidate=report(self.catalog);candidate["findings"][0]["recommendation"]="历史响应已丢弃，请重建原始字节。"
            identity,args="analysis.submit",{"report":candidate}
        elif n==2:
            pending=req.previous_results[-1]["output"]
            identity,args="analysis.review",{"draft_id":pending["draft_id"],"items":review_items(pending,revise=True)}
        elif n==3:
            feedback=req.previous_results[-1]["output"]
            identity,args="analysis.revise",{"draft_id":feedback["draft_id"],"edits":[{"op":"replace","path":"/findings/0/recommendation","value":"先检查已有原始记录；未查明保留状态时保持 UNKNOWN。"}]}
        elif n==4:
            pending=req.previous_results[-1]["output"]
            identity,args="analysis.review",{"draft_id":pending["draft_id"],"items":review_items(pending)}
        else:
            return InferenceResponse(action=InferenceAction.RESULT_READY,summary="Scoped report reviewed",working_plan=req.working_plan,
                result_claim={"output_vector":{"report_digest":req.previous_results[-1]["output"]["report_digest"]}})
        return InferenceResponse(action=InferenceAction.CONTINUE,summary="Same-owner bounded candidate feedback and repair",working_plan=req.working_plan,
            tool_calls=(ToolCallProposal(proposal_index=0,tool_identity=identity,arguments=args),))


@pytest.mark.parametrize("limit,expected",[(12,"COMPLETED"),(3,"FAILED")])
def test_native_semantic_feedback_uses_existing_bounded_refinement_and_exhausts_honestly(tmp_path, limit, expected):
    s,snap,_=service(tmp_path);original=json.loads(json.dumps(snap));model=SemanticRefinementModel(snap)
    s.inference_factory=lambda:model;s.settings=s.settings.model_copy(update={"trace_analysis_max_inferences":limit})
    trigger=AnalysisTrigger(request_id=uuid4(),rationale="Recover a candidate's unsupported presupposition")
    result=asyncio.run(s.analyze("human:owner",uuid4_from(snap),trigger))
    assert result["status"]==expected and len(model.requests)<=limit and snap==original
    assert any(v["verification"]=="NATIVE_SELF_REVIEW_REQUIRES_REVISION" for v in result["verification_receipts"])
    assert result["refinement_feedback"]
    if expected=="COMPLETED":
        assert result["report"]["findings"][0]["recommendation"]=="先检查已有原始记录；未查明保留状态时保持 UNKNOWN。"
        assert result["native_self_review"]["report_digest"]==result["kernel_result"]["result_claim"]["output_vector"]["report_digest"]
    else:assert result["report"] is None


def test_unreviewed_structurally_valid_report_cannot_finish_as_completed(tmp_path):
    s,snap,_=service(tmp_path)
    class SkipReview(NativeModel):
        async def infer(self, req):
            if req.previous_results:
                self.requests.append(req)
                return InferenceResponse(action=InferenceAction.RESULT_READY,summary="Premature terminal",working_plan=req.working_plan,
                    result_claim={"output_vector":{"report_digest":req.previous_results[-1]["output"]["candidate_digest"]}})
            return await super().infer(req)
    model=SkipReview(snap);s.inference_factory=lambda:model
    result=asyncio.run(s.analyze("human:owner",uuid4_from(snap),AnalysisTrigger(request_id=uuid4(),rationale="Require self-review")))
    assert result["status"]=="FAILED" and result["report"] is None
