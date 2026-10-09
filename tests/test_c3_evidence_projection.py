"""Exact lifecycle disposition projection; these tests grant no Human authority."""
from types import SimpleNamespace
from uuid import uuid4
from hashlib import sha256

import pytest

from spg.application.verification import _project_decision_context_evidence
from spg.application.guardian_assurance import (
    GuardianAssuranceClient, _protected_context_for_guardian,
)
from spg.domain.production_intelligence import ProtectedContextObligation
from spg.domain.verification import VerificationResultValue


class Evidence:
    def __init__(self, metadata):
        self.metadata = metadata
    def model_dump(self, **_):
        return {"metadata": self.metadata}


def basis():
    content = "A source-owned requirement"
    item = ProtectedContextObligation(
        context_class="APPROVED_CONSTRAINT", semantic_key="boundary",
        source_ref=f"semantic-fact:{uuid4()}", source_revision="a" * 40,
        authority="HUMAN_EXPLICIT", content=content,
        content_digest=sha256(content.encode()).hexdigest(),
        package_fingerprint="b" * 64,
    )
    request = SimpleNamespace(decision_context_fingerprint="b" * 64,
        protected_context_obligations=(item,))
    task = SimpleNamespace(decision_context=SimpleNamespace(
        package_fingerprint="b" * 64, protected_obligations=(item,)))
    return item, request, task


def result(checks, passed=True):
    return SimpleNamespace(result=VerificationResultValue.PASS if passed else
        VerificationResultValue.FAIL,
        evidence=Evidence({"protected_context_checks": checks}))


def projection(request, checks, passed=True):
    return _project_decision_context_evidence(request, result(checks, passed))[
        "metadata"]["decision_context"]


@pytest.mark.parametrize("coverage", ["COVERED", "PENDING_CANDIDATE_GATE",
    "PENDING_HUMAN_GATE", "CONTEXT_RETAINED"])
def test_exact_disposition_is_preserved_without_becoming_approval(coverage):
    item, request, task = basis()
    context = projection(request, [{**item.model_dump(mode="json"),
        "coverage": coverage}])
    assert context["protected_obligations"][0]["coverage"] == coverage
    record = SimpleNamespace(id=uuid4(), result=VerificationResultValue.PASS,
        evidence=Evidence({"decision_context": context}))
    checked = _protected_context_for_guardian(task, (record,))[0]
    assert checked.coverage == coverage
    assert checked.verification_refs == (f"verification:{record.id}",)
    assert "authorization" not in checked.model_dump()


@pytest.mark.parametrize("key,value", [("source_revision", "c" * 40),
    ("authority", "MODEL_CANDIDATE"), ("content_digest", "0" * 64),
    ("package_fingerprint", "d" * 64)])
def test_wrong_owner_identity_does_not_project_coverage(key, value):
    item, request, task = basis()
    check = {**item.model_dump(mode="json"), "coverage": "COVERED", key: value}
    context = projection(request, [check])
    assert context["protected_obligations"][0]["coverage"] == "UNVERIFIED"
    record = SimpleNamespace(id=uuid4(), result=VerificationResultValue.PASS,
        evidence=Evidence({"decision_context": {
            "package_fingerprint": "b" * 64, "protected_obligations": [check]}}))
    assert _protected_context_for_guardian(task, (record,))[0].coverage == "GUARDIAN_REQUIRED"


@pytest.mark.parametrize("passed,duplicate", [(False, False), (True, True)])
def test_failed_or_ambiguous_check_remains_unverified(passed, duplicate):
    item, request, _ = basis()
    check = {**item.model_dump(mode="json"), "coverage": "COVERED"}
    context = projection(request, [check, check] if duplicate else [check], passed)
    assert context["protected_obligations"][0]["coverage"] == "UNVERIFIED"


def test_conflicting_persisted_dispositions_do_not_prefer_coverage():
    item, request, task = basis()
    records = []
    for coverage in ("COVERED", "PENDING_HUMAN_GATE"):
        context = projection(request, [{**item.model_dump(mode="json"),
                                       "coverage": coverage}])
        records.append(SimpleNamespace(id=uuid4(), result=VerificationResultValue.PASS,
            evidence=Evidence({"decision_context": context})))
    checked = _protected_context_for_guardian(task, records)[0]
    assert checked.coverage == "GUARDIAN_REQUIRED"
    assert not checked.verification_refs


@pytest.mark.parametrize("matching", [True, False])
def test_work_reality_resolver_reads_only_its_exact_source_assessment(monkeypatch, matching):
    revision_id, interaction_id, assessment_id = uuid4(), uuid4(), uuid4()
    revision = SimpleNamespace(source_kind="INTERACTION_ASSESSMENT",
        source_interaction_id=interaction_id, source_assessment_id=assessment_id,
        model_dump=lambda **_: {"id": str(revision_id)})
    ir = {"id": str(uuid4()), "items": []}
    assessment = SimpleNamespace(interaction_id=interaction_id if matching else uuid4(),
        semantic_ir=SimpleNamespace(model_dump=lambda **_: ir))
    reads = []
    class Product:
        def __init__(self, _): pass
        def work_reality_revision(self, identity):
            reads.append(("revision", identity)); return revision
    class Interaction:
        def __init__(self, _): pass
        def assessment(self, identity):
            reads.append(("assessment", identity)); return assessment
    monkeypatch.setattr("spg.application.guardian_assurance.ProductStore", Product)
    monkeypatch.setattr("spg.infrastructure.persistence.interaction_store.InteractionStore", Interaction)
    monkeypatch.setattr("spg.application.guardian_assurance.RuntimeStore", lambda _: None)
    class Unit:
        session = object()
        def __enter__(self): return self
        def __exit__(self, *_): return False
    client = object.__new__(GuardianAssuranceClient)
    client.delivery = SimpleNamespace(database=SimpleNamespace(unit_of_work=lambda: Unit()))
    observed = client._resolve_owner_evidence(f"work-reality:{revision_id}")
    assert reads == [("revision", revision_id), ("assessment", assessment_id)]
    assert observed["semantic_ir"] == (ir if matching else None)


def test_planning_replacement_preserves_pending_observations_and_replay_budget():
    from spg.infrastructure.persistence.product_store import _merge_fulfillment_formation_receipts
    row = {"receipt_id": str(uuid4()), "inventory_fingerprint": "a" * 64,
           "stage": "MODEL_REQUEST_PENDING", "attempt": 1}
    prior = {"proposal_id": "old", "fulfillment_formation_receipts": [row]}
    incoming = {"proposal_id": "new", "objective": "new legal planning representation"}
    merged = _merge_fulfillment_formation_receipts(prior, incoming)
    assert merged["proposal_id"] == "new"
    assert merged["fulfillment_formation_receipts"] == [row]
    assert _merge_fulfillment_formation_receipts(merged, merged) == merged
    with pytest.raises(ValueError, match="FULFILLMENT_RECEIPT_IDENTITY_DRIFT"):
        _merge_fulfillment_formation_receipts(prior, {
            "fulfillment_formation_receipts": [{**row, "attempt": 0}]})


@pytest.mark.parametrize("defect", [None, "duplicate", "missing", "authority", "subject", "schema", "owner", "receipt", "candidate-authority"])
def test_fulfillment_receipt_resolver_reads_exact_derived_owner_record(monkeypatch, defect):
    from spg.domain.runtime import GovernanceRecord
    from datetime import datetime, UTC
    receipt_id = uuid4()
    values = dict(id=uuid4(), decision_type="WORK_FULFILLMENT_OBSERVATION",
        authority_identity="work-governance:derived-candidate-observation",
        subject_type="WORK_FULFILLMENT_BASIS", subject_identity="a"*64,
        scope={"schema":"work-fulfillment-formation-receipt-v1", "owner":"WORK_FULFILLMENT_PROJECTION",
            "receipt_id":str(receipt_id), "inventory_fingerprint":"a"*64, "candidate_is_authority":False},
        rationale=None, created_at=datetime.now(UTC))
    if defect == "authority": values["authority_identity"]="human:owner"
    if defect == "subject": values["subject_identity"]="b"*64
    if defect in {"schema", "owner"}: values["scope"][defect]="wrong"
    if defect == "receipt": values["scope"]["receipt_id"]=str(uuid4())
    if defect == "candidate-authority": values["scope"]["candidate_is_authority"]=True
    record=GovernanceRecord.model_validate(values)
    reads=[]
    class Store:
        def __init__(self, _): pass
        def fulfillment_observations_for_receipt(self, identity):
            reads.append(identity)
            return [] if defect=="missing" else [record, record] if defect=="duplicate" else [record]
    class Unit:
        session=object()
        def __enter__(self): return self
        def __exit__(self,*_): return False
    monkeypatch.setattr("spg.application.guardian_assurance.RuntimeStore",Store)
    client=object.__new__(GuardianAssuranceClient)
    client.delivery=SimpleNamespace(database=SimpleNamespace(unit_of_work=lambda:Unit()))
    observed=client._resolve_owner_evidence(f"work-plan-receipt:{receipt_id}")
    assert reads==[receipt_id]
    assert (observed is not None)==(defect is None)
    if observed is not None:
        assert observed["id"]==str(record.id) and observed["scope"]["receipt_id"]==str(receipt_id)


def _typed_nonconsumer(request, *, defect=None):
    request.obligation = "GIT_DIFF_CHECK"
    metadata = {"mode": "contract-driven-code-verification", "kind": "GIT_DIFF_CHECK", "target": None}
    evidence = Evidence(metadata); evidence.obligation = request.obligation
    outcome = SimpleNamespace(result=VerificationResultValue.PASS, evidence=evidence)
    projected = _project_decision_context_evidence(request, outcome)["metadata"]
    if defect == "related-check":
        projected["protected_context_checks"] = [{**request.protected_context_obligations[0].model_dump(mode="json"), "coverage": "UNVERIFIED"}]
    if defect == "wrong-revision":
        projected["decision_context"]["protected_obligations"][0]["source_revision"] = "f"*40
    if defect == "wrong-kind": projected["kind"] = "PATH_SCOPE"
    if defect == "wrong-obligation": request.obligation = "PYTHON_COMPILE"
    if defect == "duplicate":
        projected["decision_context"]["protected_obligations"] *= 2
    if defect == "no-disposition":
        projected["decision_context"]["protected_obligations"][0].pop("projection_disposition")
    evidence = Evidence(projected); evidence.obligation = "GIT_DIFF_CHECK"
    return SimpleNamespace(id=uuid4(), result=VerificationResultValue.PASS,
        obligation=request.obligation, evidence=evidence)


def test_real_coverage_and_explicit_nonconsumer_are_not_conflicting():
    item, request, task = basis()
    context = projection(request, [{**item.model_dump(mode="json"), "coverage": "COVERED"}])
    covered = SimpleNamespace(id=uuid4(), result=VerificationResultValue.PASS,
        evidence=Evidence({"decision_context": context}))
    unconsumed = _typed_nonconsumer(request)
    checked = _protected_context_for_guardian(task, (covered, unconsumed))[0]
    assert checked.coverage == "COVERED"
    assert checked.verification_refs == (f"verification:{covered.id}",)
    assert unconsumed.evidence.metadata["decision_context"]["protected_obligations"][0]["coverage"] == "UNVERIFIED"


def test_nonconsumer_alone_cannot_supply_missing_protected_evidence():
    _, request, task = basis()
    checked = _protected_context_for_guardian(task, (_typed_nonconsumer(request),))[0]
    assert checked.coverage == "GUARDIAN_REQUIRED" and not checked.verification_refs


@pytest.mark.parametrize("defect", ["related-check", "wrong-revision", "wrong-kind", "wrong-obligation", "duplicate", "no-disposition"])
def test_nonconsumer_label_does_not_hide_rejected_owner_checks(defect):
    item, request, task = basis()
    context = projection(request, [{**item.model_dump(mode="json"), "coverage": "COVERED"}])
    covered = SimpleNamespace(id=uuid4(), result=VerificationResultValue.PASS,
        evidence=Evidence({"decision_context": context}))
    checked = _protected_context_for_guardian(task, (covered, _typed_nonconsumer(request, defect=defect)))[0]
    assert checked.coverage == "GUARDIAN_REQUIRED" and not checked.verification_refs
