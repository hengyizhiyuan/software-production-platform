from datetime import timedelta

from spg.application.executor_runtime import FairCapacityScheduler
from tests.test_native_executor_contracts import _queue, _offer, NOW


def test_aged_backlog_rotates_between_works_and_preserves_priority():
    scheduler = FairCapacityScheduler(aging_threshold=timedelta(seconds=30))
    a = [_queue("work:a", index) for index in range(5)]
    b = _queue("work:b", 6).model_copy(update={"priority": -100})
    entries = [*a, b]
    selected = scheduler.choose(entries, _offer(), now=NOW + timedelta(minutes=20),
                                last_fairness_group="work:a")
    assert selected.selected_queue_entry_id == b.id
    assert "aging" in selected.reason
    assert b.priority == -100
    next_turn = scheduler.choose(entries, _offer(), now=NOW + timedelta(minutes=20),
                                 last_fairness_group="work:b")
    assert next_turn.selected_queue_entry_id == a[0].id


def test_cursor_survives_a_group_departing_and_priority_is_within_work():
    low = _queue("work:a", 0).model_copy(update={"priority": -5})
    high = _queue("work:a", 1).model_copy(update={"priority": 10})
    b = _queue("work:c", 2)
    scheduler = FairCapacityScheduler()
    decision = scheduler.choose([low, high, b], _offer(), now=NOW + timedelta(minutes=3),
                                last_fairness_group="work:b")
    assert decision.selected_queue_entry_id == b.id
    priority = scheduler.choose([low, high, b], _offer(), now=NOW + timedelta(minutes=3),
                                last_fairness_group="work:c")
    assert priority.selected_queue_entry_id == high.id


def test_incompatible_old_entry_never_bypasses_capability_authority():
    old = _queue("work:a", 0, capability="ungranted.capability")
    runnable = _queue("work:b", 1)
    decision = FairCapacityScheduler().choose([old, runnable], _offer(),
        now=NOW + timedelta(hours=1), last_fairness_group=None)
    assert decision.selected_queue_entry_id == runnable.id
