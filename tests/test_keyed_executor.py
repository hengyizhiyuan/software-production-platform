"""Keyed serial executor: ordered per key, concurrent across keys."""
from threading import Barrier, Event, Lock
import time

import pytest

from spg.application.keyed_executor import KeyedSerialExecutor


def test_tasks_of_one_key_run_in_order_and_never_overlap():
    executor = KeyedSerialExecutor(4, "t")
    order, active, peak, lock = [], [0], [0], Lock()

    def task(i):
        with lock:
            active[0] += 1
            peak[0] = max(peak[0], active[0])
        time.sleep(0.01)
        order.append(i)
        with lock:
            active[0] -= 1

    futures = [executor.submit("interaction-a", task, i) for i in range(10)]
    for future in futures:
        future.result(5)
    executor.shutdown()
    assert order == list(range(10))
    assert peak[0] == 1


def test_different_keys_run_concurrently():
    executor = KeyedSerialExecutor(2, "t")
    barrier = Barrier(2, timeout=5)
    a = executor.submit("a", barrier.wait)
    b = executor.submit("b", barrier.wait)
    a.result(5)
    b.result(5)  # would raise BrokenBarrierError if the keys were serialized
    executor.shutdown()


def test_a_failing_task_does_not_stop_later_tasks_of_its_key():
    executor = KeyedSerialExecutor(1, "t")

    def boom():
        raise ValueError("turn failed")

    failed = executor.submit("a", boom)
    later = executor.submit("a", lambda: "ok")
    with pytest.raises(ValueError):
        failed.result(5)
    assert later.result(5) == "ok"
    executor.shutdown()


def test_a_slow_interaction_does_not_delay_another():
    executor = KeyedSerialExecutor(2, "t")
    release = Event()
    slow = executor.submit("slow", release.wait, 5)
    started = time.monotonic()
    assert executor.submit("fast", lambda: "done").result(2) == "done"
    assert time.monotonic() - started < 1
    release.set()
    slow.result(5)
    executor.shutdown()
