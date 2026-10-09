"""Controlled Owner-record regressions; no live Work, model or business database.

Every projection is fresh. Synthetic Owner records do not claim that any
historical Work was repaired, accepted, or authorized.
"""
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from sqlalchemy.dialects import postgresql

import spg.application.work as work_module
from spg.application.work import WorkApplicationService
from spg.domain.governed_obligation import canonical_fingerprint
from spg.domain.product import RuntimeFactSummary, WorkCondition, WorkMode, WorkRecord, WorkStatus
from spg.domain.runtime import BaselinePointerRecord, GovernanceRecord, SnapshotCondition, SnapshotRecord
from spg.domain.steering import RealityReference, RealityReferenceKind, SteeringAttentionReason, SteeringOutcome
from spg.infrastructure.persistence.runtime_store import RuntimeStore


NOW = datetime(2026, 10, 9, 14, 0, tzinfo=UTC)


class ReadOnlyRows:
    def __init__(self, values):
        self.values = values
    def mappings(self):
        return self
    def __iter__(self):
        return iter(self.values)
    def all(self):
        return self.values


class ReadOnlySession:
    def __init__(self, records):
        self.records = records
        self.info = {}
        self.queries = []
    def execute(self, statement):
        self.queries.append(statement)
        return ReadOnlyRows([record.model_dump() if isinstance(record, GovernanceRecord)
                             else record for record in self.records])


def fixture_basis(monkeypatch):
    work_id, revision_id, step_id, baseline_id = (uuid4() for _ in range(4))
    source = SnapshotRecord(id=baseline_id, condition=SnapshotCondition.TRUSTED,
        repository_identity="qualification:synthetic-owner-source", repository_ref="refs/heads/main",
        repository_revision="a" * 40, repository_tree_identity="b" * 40,
        source_baseline_id=None, created_at=NOW)
    scope = {"schema": "work-fulfillment-stop-observation-v1",
        "owner": "WORK_FULFILLMENT_PROJECTION", "work_id": str(work_id),
        "work_reality_revision_id": str(revision_id), "steering_step_id": str(step_id),
        "source_baseline_id": str(baseline_id), "source_revision": source.repository_revision,
        "inventory_fingerprint": "c" * 64,
        "source_refs": ["ir-clause:synthetic-current-clause"],
        "unresolved_source_refs": ["ir-clause:synthetic-current-clause"],
        "formation_receipt_refs": ["governance:synthetic-formation-receipt"],
        "terminal_reason": "MODEL_FORMATION_UNRESOLVED",
        "condition": "OBLIGATION_PROJECTION_UNRESOLVED",
        "candidate_is_authority": False, "runtime_admitted": False}
    def record(values=None, **changes):
        values = scope if values is None else values
        fingerprint = canonical_fingerprint(values)
        fields = dict(id=uuid5(NAMESPACE_URL, f"spg:work-fulfillment-stop:{fingerprint}"),
            decision_type="WORK_FULFILLMENT_STOP_OBSERVATION",
            authority_identity="work-governance:derived-candidate-observation",
            subject_type="WORK_FULFILLMENT_STOP_BASIS", subject_identity=fingerprint,
            scope=dict(values), rationale="Controlled synthetic stop observation", created_at=NOW)
        fields.update(changes)
        return GovernanceRecord(**fields)
    session = ReadOnlySession([record()])
    step = SimpleNamespace(id=step_id, type=SimpleNamespace(value="PRODUCE"),
        state=SimpleNamespace(value="CURRENT"))
    steering = SimpleNamespace(plan_for_work=lambda _: SimpleNamespace(id=uuid4()),
        active_revision=lambda _: SimpleNamespace(id=uuid4()), steps=lambda _: (step,),
        latest_decision=lambda _: None)
    monkeypatch.setattr(work_module, "SteeringStore", lambda _: steering)
    monkeypatch.setattr(RuntimeStore, "snapshot", lambda _, identity: source if identity == source.id else None)
    monkeypatch.setattr(RuntimeStore, "current_pointer", lambda _, **kw:
        BaselinePointerRecord(snapshot_id=source.id, version=1, updated_at=NOW))
    product = SimpleNamespace(session=session, scope_for_work=lambda _: None,
        runtime_binding=lambda _: None, runtime_binding_for_step=lambda _: None,
        runtime_bindings=lambda _: (),
        resource_for_work=lambda _: SimpleNamespace(repository_identity=source.repository_identity,
            authoritative_ref=source.repository_ref))
    work = WorkRecord(id=work_id, goal_id=None, mode=WorkMode.LONG_LIVED_STEERING,
        raw_user_requirement="Controlled current production requirement",
        refined_title="Synthetic qualification basis", desired_outcome="Qualified result",
        constraints=("Retain the exact original requirement",), tags=(), condition=WorkCondition.READY,
        engineering_scope_id=None, scope_summary=None, production_objective=None,
        expected_artifact_path=None, verification_expectation=None,
        current_work_reality_revision_id=revision_id, created_at=NOW, updated_at=NOW)
    return SimpleNamespace(work=work, source=source, step=step, product=product,
        session=session, record=record, scope=scope, steering=steering)


def read_fresh(basis):
    service = WorkApplicationService.__new__(WorkApplicationService)
    service.candidate_review_readiness = None
    service.candidate_review_state = None
    service.executor = SimpleNamespace()
    service.verifier = SimpleNamespace()
    service._multi_pwu_projection = lambda *args: None
    return service._projection(basis.product, basis.work)


def test_fresh_projection_consumes_current_durable_fulfillment_stop(monkeypatch):
    basis = fixture_basis(monkeypatch)
    original = basis.work.model_dump(mode="json")
    for _ in range(2):
        projection = read_fresh(basis)
        assert projection.status is WorkStatus.BLOCKED
        assert projection.most_recent_meaningful_event == "OBLIGATION_PROJECTION_UNRESOLVED"
        assert not projection.human_attention_required and not projection.work_complete
        assert projection.current_production_run_id is None
        assert projection.current_steering_step_id == basis.step.id
        assert str(basis.session.records[0].id) in projection.what_happens_next
    assert basis.work.model_dump(mode="json") == original
    assert len(basis.session.records) == 1
    statement = basis.session.queries[0].compile(dialect=postgresql.dialect())
    assert {str(basis.work.id), str(basis.work.current_work_reality_revision_id), str(basis.step.id),
        "WORK_FULFILLMENT_STOP_OBSERVATION", "work-governance:derived-candidate-observation",
        "WORK_FULFILLMENT_STOP_BASIS"}.issubset(set(statement.params.values()))


@pytest.mark.parametrize("field,value", [
    ("decision_type", "WORK_FULFILLMENT_OBSERVATION"),
    ("authority_identity", "untrusted:provider-candidate"),
    ("subject_type", "WORK_FULFILLMENT_BASIS"),
    ("subject_identity", "d" * 64),
    ("id", uuid4()),
])
def test_wrong_carrier_identity_never_blocks(monkeypatch, field, value):
    basis = fixture_basis(monkeypatch)
    basis.session.records = [basis.record(**{field: value})]
    projection = read_fresh(basis)
    assert projection.status is WorkStatus.READY and not projection.human_attention_required


@pytest.mark.parametrize("field,value", [
    ("schema", "different-stop-schema"), ("owner", "MODEL"),
    ("work_id", str(uuid4())), ("work_reality_revision_id", str(uuid4())),
    ("steering_step_id", str(uuid4())), ("source_baseline_id", str(uuid4())),
    ("source_revision", "d" * 40), ("condition", "SATISFIED"),
    ("candidate_is_authority", True), ("runtime_admitted", True),
    ("unresolved_source_refs", []), ("unresolved_source_refs", ["ir-clause:unlisted"]),
    ("source_refs", "not-a-list"), ("extra_scope_key", "unsupported-contract"),
])
def test_wrong_or_stale_stop_scope_never_blocks_even_with_recomputed_identity(monkeypatch, field, value):
    basis = fixture_basis(monkeypatch)
    values = {**basis.scope, field: value}
    basis.session.records = [basis.record(values)]
    projection = read_fresh(basis)
    assert projection.status is WorkStatus.READY and not projection.human_attention_required


@pytest.mark.parametrize("missing", ["pointer", "snapshot", "resource"])
def test_missing_source_owner_evidence_does_not_promote_stop_claim(monkeypatch, missing):
    basis = fixture_basis(monkeypatch)
    if missing == "pointer":
        monkeypatch.setattr(RuntimeStore, "current_pointer", lambda _, **kw: None)
    elif missing == "snapshot":
        monkeypatch.setattr(RuntimeStore, "snapshot", lambda *args: None)
    else:
        basis.product.resource_for_work = lambda _: None
    assert read_fresh(basis).status is WorkStatus.READY


@pytest.mark.parametrize("changed", ["repository_identity", "repository_ref", "source_advanced"])
def test_source_namespace_or_current_baseline_change_keeps_old_stop_historical(monkeypatch, changed):
    basis = fixture_basis(monkeypatch)
    if changed == "source_advanced":
        newer = basis.source.model_copy(update={"id": uuid4(), "repository_revision": "e" * 40})
        monkeypatch.setattr(RuntimeStore, "current_pointer", lambda _, **kw:
            BaselinePointerRecord(snapshot_id=newer.id, version=2, updated_at=NOW))
        monkeypatch.setattr(RuntimeStore, "snapshot", lambda _, identity: newer if identity == newer.id else None)
    else:
        replacement = basis.source.model_copy(update={changed: "qualification:wrong-namespace"})
        monkeypatch.setattr(RuntimeStore, "snapshot", lambda _, identity: replacement)
    assert read_fresh(basis).status is WorkStatus.READY


@pytest.mark.parametrize("step_type", ["DESIGN", "VERIFY_ACCEPT", "COMPLETE"])
def test_wrong_lifecycle_phase_does_not_consume_production_stop(monkeypatch, step_type):
    basis = fixture_basis(monkeypatch)
    basis.step.type.value = step_type
    assert read_fresh(basis).status is WorkStatus.READY
    assert basis.session.queries == []


def test_new_revision_or_step_does_not_inherit_old_stop(monkeypatch):
    basis = fixture_basis(monkeypatch)
    original_revision_id = basis.work.current_work_reality_revision_id
    basis.work = basis.work.model_copy(update={"current_work_reality_revision_id": uuid4()})
    assert read_fresh(basis).status is WorkStatus.READY
    basis.work = basis.work.model_copy(update={"current_work_reality_revision_id":
        original_revision_id})
    basis.step.id = uuid4()
    assert read_fresh(basis).status is WorkStatus.READY


def test_existing_human_decision_has_priority_over_stop(monkeypatch):
    basis = fixture_basis(monkeypatch)
    decision = SimpleNamespace(steering_outcome=SteeringOutcome.HUMAN_ATTENTION,
        attention_reason=SteeringAttentionReason.MATERIAL_RISK_OR_COST_DECISION,
        reality_refs=(RealityReference(kind=RealityReferenceKind.WORK_REALITY_REVISION,
            identity=basis.work.current_work_reality_revision_id),))
    basis.steering.latest_decision = lambda _: decision
    projection = read_fresh(basis)
    assert projection.status is WorkStatus.NEEDS_ATTENTION and projection.human_attention_required
    assert projection.most_recent_meaningful_event == "STEERING_HUMAN_ATTENTION"
    assert basis.session.queries == []


@pytest.mark.parametrize("candidate_gate", [False, True])
def test_lawful_runtime_binding_and_candidate_gate_take_priority(monkeypatch, candidate_gate):
    basis = fixture_basis(monkeypatch)
    binding = SimpleNamespace(work_reality_revision_id=basis.work.current_work_reality_revision_id,
        production_run_id=uuid4(), plan_revision_id=uuid4(), cycle_number=1)
    facts = RuntimeFactSummary(attempt_id=uuid4(),
        candidate_id=uuid4() if candidate_gate else None)
    basis.product.runtime_binding = lambda _: binding
    basis.product.runtime_binding_for_step = lambda _: binding
    basis.product.runtime_bindings = lambda _: (binding,)
    basis.product.runtime_summary = lambda _: facts
    monkeypatch.setattr(RuntimeStore, "run", lambda *args: SimpleNamespace(
        current_plan_revision_id=binding.plan_revision_id))
    projection = read_fresh(basis)
    assert projection.current_production_run_id == binding.production_run_id
    assert projection.status is (WorkStatus.NEEDS_ATTENTION if candidate_gate else WorkStatus.RUNNING)
    assert projection.human_attention_required is candidate_gate
    assert projection.most_recent_meaningful_event != "OBLIGATION_PROJECTION_UNRESOLVED"
    assert basis.session.queries == []


def test_partial_formation_stop_with_no_inventory_receipt_stays_truthful(monkeypatch):
    basis = fixture_basis(monkeypatch)
    basis.session.records = [basis.record({**basis.scope, "inventory_fingerprint": None,
        "formation_receipt_refs": [], "terminal_reason": None})]
    assert read_fresh(basis).status is WorkStatus.BLOCKED


def test_no_stop_record_retains_existing_ready_projection(monkeypatch):
    basis = fixture_basis(monkeypatch)
    basis.session.records = []
    assert read_fresh(basis).status is WorkStatus.READY


@pytest.mark.parametrize("malformed", ["id", "scope", "scope_modified_after_identity"])
def test_malformed_or_modified_record_cannot_project_blocked(monkeypatch, malformed):
    basis = fixture_basis(monkeypatch)
    row = basis.record().model_dump()
    if malformed == "id":
        row["id"] = "not-a-uuid"
    elif malformed == "scope":
        row["scope"] = "not-an-owner-scope"
    else:
        row["scope"] = {**row["scope"], "terminal_reason": "different-unsealed-reason"}
    basis.session.records = [row]
    assert read_fresh(basis).status is WorkStatus.READY
