"""A stopped convergence episode offers retry or pause, and only an explicit retry restarts it."""
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

import spg.application.work as work_module
from spg.application.work import WorkApplicationService, _is_convergence_incident
from spg.domain.product import AttentionAction, AttentionKind, ProductInvariantViolation
from spg.domain.steering import SteeringAttentionReason, SteeringOutcome


def incident(**overrides):
    values = dict(steering_outcome=SteeringOutcome.HUMAN_ATTENTION,
        attention_reason=SteeringAttentionReason.MATERIAL_RISK_OR_COST_DECISION,
        reason="Work convergence stopped: NON_CONVERGING; 3 failed no-progress outcomes")
    values.update(overrides)
    return SimpleNamespace(**values)


def test_only_the_convergence_stop_decision_is_an_incident():
    assert _is_convergence_incident(incident())
    assert not _is_convergence_incident(incident(reason="Choose between two product directions"))
    assert not _is_convergence_incident(incident(attention_reason=SteeringAttentionReason.PRODUCTION_PROPOSAL_REVIEW_REQUIRED))
    assert not _is_convergence_incident(incident(steering_outcome=SteeringOutcome.COMPLETE))


class Runtime:
    def __init__(self):
        self.records = []
    def governance_for_subject(self, subject):
        return [SimpleNamespace(**r) for r in self.records if r["subject_identity"] == subject]
    def insert_governance(self, values):
        self.records.append(values)


def resolve(monkeypatch, action, decision):
    runtime = Runtime()
    work_id, decision_id = uuid4(), uuid4()

    class UoW:
        session = None
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def commit(self): pass

    monkeypatch.setattr(work_module, "SteeringStore", lambda _: SimpleNamespace(decision=lambda _id: decision))
    monkeypatch.setattr(work_module, "RuntimeStore", lambda _: runtime)
    service = WorkApplicationService.__new__(WorkApplicationService)
    service.database = SimpleNamespace(unit_of_work=UoW)
    service.get_work = lambda wid: wid
    attention = SimpleNamespace(work_id=work_id, kind=AttentionKind.STEERING_DECISION_REQUIRED,
                                governed_subject_ref=f"steering-decision:{decision_id}")
    request = SimpleNamespace(action=action, authority_identity="human:owner", rationale=None)
    service._resolve_convergence_incident(attention, request)
    service._resolve_convergence_incident(attention, request)  # idempotent
    return runtime.records


def test_retry_records_one_restart_and_pause_records_one_pause(monkeypatch):
    restart = resolve(monkeypatch, AttentionAction.APPROVE, incident())
    assert [r["decision_type"] for r in restart] == ["RESTART_CONVERGENCE_EPISODE"]
    assert restart[0]["authority_identity"] == "human:owner"
    pause = resolve(monkeypatch, AttentionAction.REJECT, incident())
    assert [r["decision_type"] for r in pause] == ["PAUSE_AFTER_CONVERGENCE_INCIDENT"]


def test_a_non_incident_decision_cannot_be_restarted(monkeypatch):
    with pytest.raises(ProductInvariantViolation):
        resolve(monkeypatch, AttentionAction.APPROVE, incident(reason="A material product choice"))


def test_only_a_restart_record_changes_the_convergence_episode():
    from spg.domain.native_execution import canonical_digest
    base = {"raw_requirement": "r", "desired_outcome": "o", "constraints": []}
    restart_id = uuid4()
    assert canonical_digest(base) != canonical_digest({**base, "episode": str(restart_id)})
    assert canonical_digest({**base, "episode": str(restart_id)}) == canonical_digest({**base, "episode": str(restart_id)})
