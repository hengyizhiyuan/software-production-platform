"""Status must report the current production binding, not newer stale history."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

import spg.application.interaction as interaction_module
from spg.application.interaction import WorkInteractionService
from spg.domain.interaction import WorkImpactDisposition
from spg.domain.native_execution import QueueCondition
from spg.domain.response_contract import InteractionMode


@pytest.fixture
def projection(monkeypatch):
    work_id, pwu_id, attempt_id = uuid4(), uuid4(), uuid4()
    state = SimpleNamespace(
        binding=SimpleNamespace(work_unit_id=pwu_id),
        summary=SimpleNamespace(
            attempt_id=attempt_id, runtime_commit_id=None,
            candidate_id=None, authorization_id=None,
        ),
        queue=[],
    )
    basis = SimpleNamespace(
        active_work_context=SimpleNamespace(
            work_revision=SimpleNamespace(
                work_id=work_id, motive="Account access",
                desired_outcome="A usable sign-in form",
                context_facts=(), constraints=(), requests=(),
            ),
            relevant_reality_references=(),
        ),
        records=[SimpleNamespace(content="现在做到哪了？")],
    )

    class ReadOnlyDatabase:
        @contextmanager
        def unit_of_work(self):
            # No commit or write operations are available on this seam.
            yield SimpleNamespace(session=object())

    class ProductReads:
        def runtime_binding(self, requested_work):
            assert requested_work == work_id
            return state.binding

        def runtime_summary(self, binding):
            assert binding is state.binding
            return state.summary

    class SteeringReads:
        def plan_for_work(self, requested_work):
            assert requested_work == work_id
            return None

    class QueueReads:
        def list_queue(self, *, work_id: object):
            assert work_id == basis.active_work_context.work_revision.work_id
            return state.queue

    monkeypatch.setattr(interaction_module, "ProductStore", lambda _: ProductReads())
    monkeypatch.setattr(interaction_module, "SteeringStore", lambda _: SteeringReads())
    monkeypatch.setattr(interaction_module, "NativeExecutionStore", lambda _: QueueReads())
    service = SimpleNamespace(database=ReadOnlyDatabase())
    now = datetime.now(UTC)

    def entry(*, old_pwu=False, old_attempt=False, condition=QueueCondition.EXECUTING,
              later_by=0, reason=None):
        return SimpleNamespace(
            pwu_id=uuid4() if old_pwu else pwu_id,
            attempt_id=uuid4() if old_attempt else attempt_id,
            condition=condition,
            wait_reason=reason,
            enqueued_at=now + timedelta(seconds=later_by),
        )

    def project(question="现在做到哪了？"):
        basis.records[0].content = question
        return WorkInteractionService._work_reality_status_candidate(service, basis)

    return state, entry, project


def test_newer_stale_pwu_and_attempt_cannot_replace_current_runtime_status(projection):
    state, entry, project = projection
    state.queue = [
        entry(condition=QueueCondition.EXECUTING),
        entry(old_pwu=True, condition=QueueCondition.COMPLETED, later_by=10),
        entry(old_attempt=True, condition=QueueCondition.WAITING_RESOURCE, later_by=20,
              reason="old-attempt-capacity-reason"),
    ]
    candidate = project()
    assert candidate.natural_response.startswith("当前执行状态是 EXECUTING。")
    assert "COMPLETED" not in candidate.natural_response
    assert "old-attempt-capacity-reason" not in candidate.natural_response
    assert candidate.response_intent.interaction_mode is InteractionMode.STATUS
    assert candidate.impact_disposition is WorkImpactDisposition.NO_GOVERNED_CHANGE


@pytest.mark.parametrize("condition", [QueueCondition.COMPLETED, QueueCondition.CANCELLED])
def test_terminal_queue_entry_is_labelled_as_last_attempt_not_current_execution(projection, condition):
    state, entry, project = projection
    state.queue = [entry(condition=condition)]
    assert project().natural_response.startswith(f"最近一次执行状态是 {condition.value}。")


def test_diagnosis_reports_missing_current_queue_instead_of_reusing_old_cause(projection):
    state, entry, project = projection
    state.queue = [entry(old_attempt=True, condition=QueueCondition.WAITING_RESOURCE,
                         reason="stale-capacity-shortage")]
    candidate = project("为什么一直卡在 QUEUED？")
    assert "当前生产周期没有对应的执行队列记录" in candidate.natural_response
    assert "证据不足" in candidate.natural_response
    assert "stale-capacity-shortage" not in candidate.natural_response
    assert candidate.response_intent.interaction_mode is InteractionMode.DIAGNOSE


def test_without_current_binding_historical_queue_does_not_imply_running(projection):
    state, entry, project = projection
    state.binding = None
    state.queue = [entry(condition=QueueCondition.EXECUTING)]
    candidate = project()
    assert "尚未创建生产周期" in candidate.natural_response
    assert "EXECUTING" not in candidate.natural_response
