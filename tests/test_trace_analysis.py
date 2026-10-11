"""Native investigation gates, evidence fidelity, replay and failure receipts."""
import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest

from spg.application.trace_analysis import TraceAnalysisService
from spg.config import Settings
from spg.domain.native_execution import InferenceAction, InferenceResponse, ToolCallProposal, canonical_digest
from spg.domain.trace_analysis import AnalysisReport, AnalysisTrigger
from spg.evaluation.contracts import QualityError
from spg.infrastructure.trace_analysis_evidence import EvidenceCatalog, RepositorySnapshot


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
    fact = {"statement": "Work is completed", "citations": [
        {"evidence_id": row["evidence_id"], "quote": "COMPLETED"}]}
    return {"work_id": catalog.snapshot["work_id"], "original_objective": fact,
            "expected_outcome": fact, "actual_execution_path": fact, "current_state": fact,
            "timeline": [dict(fact, stage="FINAL_STATE", timestamp=None)],
            "findings": [{"finding_id": "missing-raw", "classification": "UNKNOWN",
                "epistemic_status": "UNKNOWN", "fact": fact, "analysis": "Exact invalid text unavailable",
                "repository_citations": [], "uncertainty": "No raw provider output",
                "recommendation": "Inspect existing owner evidence", "handling": "INVESTIGATE",
                "regression_qualification": "Preserve UNKNOWN when raw evidence is absent"}],
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
    r = report(catalog)
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
    r["missing_evidence"] = [{"statement": "Raw response not observed in this captured group",
        "family": "OWNER_RECORD", "check_id": check["check_id"], "availability": check["availability"]}]
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
