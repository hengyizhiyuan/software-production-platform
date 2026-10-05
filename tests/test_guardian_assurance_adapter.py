"""Owner boundary tests for exact Candidate assurance admission and projection."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.application.guardian_assurance import GuardianAssuranceClient
from spg.application.candidate_preview import CandidatePreviewApplicationService
from spg.domain.product import ProductInvariantViolation
from spg.domain.production_environment import CandidatePreviewMode, PreviewRuntimeStatus
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore


class _Session:
    def execute(self, *_):
        return SimpleNamespace(scalar_one_or_none=lambda: None)


class _Uow:
    session = _Session()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


class _Database:
    def unit_of_work(self):
        return _Uow()


def _basis(tmp_path, monkeypatch):
    work_id, revision_id, candidate_id, preview_id = (uuid4() for _ in range(4))
    work = SimpleNamespace(current_work_reality_revision_id=revision_id,
        desired_outcome="Details are reachable", constraints=("same Work scope",),
        engineering_scope_id=uuid4())
    product = SimpleNamespace(work=lambda _: work,
        scope_for_work=lambda _: SimpleNamespace(id=work.engineering_scope_id),
        runtime_binding=lambda _: SimpleNamespace(governance_record_id=uuid4()),
        runtime_summary=lambda _: SimpleNamespace(candidate_id=None))
    monkeypatch.setattr("spg.application.guardian_assurance.ProductStore", lambda _: product)
    context = {"candidate_id": str(candidate_id), "candidate_fingerprint": "a" * 64,
        "repository_revision": "b" * 40, "tree": "c" * 40,
        "artifacts": ["index.html"], "verification_references": ["verification:one"]}
    delivery = SimpleNamespace(database=_Database(), candidate_context=lambda _: context)
    store = JsonProductionEnvironmentStore(tmp_path / "watt")
    guardian = SimpleNamespace(requests=[], results={})

    def assess(request):
        from guardian.contracts.software_assurance import AssuranceResult, Gate
        guardian.requests.append(request)
        result = AssuranceResult(result_id=uuid4(), request_id=request.request_id,
            candidate_id=request.candidate_id,
            candidate_fingerprint=request.candidate_fingerprint,
            source_revision=request.source_revision, source_tree=request.source_tree,
            runtime_ref=request.runtime_ref, gate=Gate.PASS,
            coverage_obligation_refs=tuple(item.obligation_ref for item in request.required_effects),
            evidence=(), findings=(), assessed_at=datetime.now(UTC))
        guardian.results[request.request_id] = result
        return result

    guardian.assess = assess
    guardian.get_result = guardian.results.get
    client = GuardianAssuranceClient(delivery, store, guardian)
    preview = SimpleNamespace(id=preview_id, work_id=work_id, candidate_id=candidate_id,
        candidate_fingerprint=context["candidate_fingerprint"],
        repository_revision=context["repository_revision"],
        repository_tree=context["tree"], status=PreviewRuntimeStatus.READY,
        endpoint="http://127.0.0.1:8080", created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC))
    monkeypatch.setattr(store, "candidate_preview_history", lambda _: ())
    monkeypatch.setattr(store, "current_candidate_preview", lambda _: preview)
    return client, guardian, preview, work, context


def test_watt_binds_governed_effect_and_consumes_exact_guardian_pass(tmp_path, monkeypatch):
    client, guardian, preview, work, _ = _basis(tmp_path, monkeypatch)
    effect = {"obligation_ref": "details-route", "kind": "HTTP_ROUTE",
        "expected_behavior": "Details route is reachable", "path": "/details"}
    client.bind_requirements(preview.work_id, [effect], authority_identity="human:governor")
    projection = client.assess_ready_preview(preview)
    assert projection["gate"] == "PASS"
    assert projection["finding_count"] == 0
    assert guardian.requests[0].governed_intent_ref == (
        f"work-reality-revision:{work.current_work_reality_revision_id}")
    assert guardian.requests[0].candidate_id == preview.candidate_id
    assert guardian.requests[0].source_tree == preview.repository_tree
    assert client.passed(preview.work_id, preview.candidate_id)
    assert client.assess_ready_preview(preview) == projection
    assert len(guardian.requests) == 1
    error = client.preview_store.save_guardian_feedback_error(preview.id,
        "Watt repair feedback failed")
    assert not client.passed(preview.work_id, preview.candidate_id)
    assert client.projection(preview.work_id)["status"] == "BLOCKED"
    assert client.projection(preview.work_id)["platform_error_ref"] == error["reference"]


def test_missing_scope_and_candidate_change_fail_closed(tmp_path, monkeypatch):
    client, guardian, preview, _, context = _basis(tmp_path, monkeypatch)
    assert client.assess_ready_preview(preview)["gate"] == "BLOCKED"
    assert not client.passed(preview.work_id, preview.candidate_id)
    assert not guardian.requests
    context["tree"] = "d" * 40
    with pytest.raises(ProductInvariantViolation, match="sealed Candidate"):
        client.assess_ready_preview(preview)


def test_preview_readiness_requires_guardian_pass(tmp_path, monkeypatch):
    client, _, preview, _, context = _basis(tmp_path, monkeypatch)
    preview.evidence = ({"kind": "SERVED_VERIFICATION", "result": "PASS"},)
    provider = SimpleNamespace()
    service = CandidatePreviewApplicationService(client.delivery, client.preview_store, provider)
    service.assurance_client = client
    monkeypatch.setattr(service, "mode_for", lambda _: CandidatePreviewMode.FULL_APPLICATION_RUNTIME)
    assert not service.review_ready(preview.work_id, preview.candidate_id)
