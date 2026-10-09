"""Controlled Owner-record regressions; no live Work, model or business database.

The projection is rebuilt for every read.  Test records are synthetic and do not
claim an actual historical Work was repaired or accepted.
"""
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest

import spg.application.work as work_module
from spg.application.work import WorkApplicationService
from spg.domain.governed_obligation import canonical_fingerprint
from spg.domain.product import WorkCondition, WorkMode, WorkRecord, WorkStatus
from spg.domain.runtime import (
    BaselinePointerRecord, GovernanceRecord, SnapshotCondition, SnapshotRecord,
)
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
        return ReadOnlyRows([record.model_dump() for record in self.records])


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
    def record(values=scope, **changes):
        basis = canonical_fingerprint(values)
        fields = dict(id=uuid5(NAMESPACE_URL, f"spg:work-fulfillment-stop:{basis}"),
            decision_type="WORK_FULFILLMENT_STOP_OBSERVATION",
            authority_identity="work-governance:derived-candidate-observation",
            subject_type="WORK_FULFILLMENT_STOP_BASIS", subject_identity=basis,
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
    return WorkApplicationService.__new__(WorkApplicationService)._projection(basis.product, basis.work)


def test_fresh_projection_consumes_current_durable_fulfillment_stop(monkeypatch):
    basis = fixture_basis(monkeypatch)
    for _ in range(2):
        projection = read_fresh(basis)
        assert projection.status is WorkStatus.BLOCKED
        assert projection.most_recent_meaningful_event == "OBLIGATION_PROJECTION_UNRESOLVED"
        assert not projection.human_attention_required and not projection.work_complete
        assert projection.current_production_run_id is None
        assert projection.current_steering_step_id == basis.step.id
    assert basis.work.condition is WorkCondition.READY
    assert len(basis.session.records) == 1
