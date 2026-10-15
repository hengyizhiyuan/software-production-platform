"""Idle Native workers back off instead of re-polling in a tight loop."""
import asyncio
from types import SimpleNamespace

from spg.executor_worker import _run_poll_loop


class CountingWorker:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    async def run_once(self, offer):
        self.calls += 1
        await asyncio.sleep(0)
        return self.results.pop(0) if self.results else False


def run(worker, seconds, poll):
    async def scenario():
        heartbeat = asyncio.create_task(asyncio.sleep(3600))
        loop = asyncio.create_task(_run_poll_loop(worker, SimpleNamespace(max_concurrency=1), poll, heartbeat))
        await asyncio.sleep(seconds)
        loop.cancel()
        await asyncio.gather(loop, return_exceptions=True)
    asyncio.run(scenario())


def test_idle_worker_waits_poll_interval_between_attempts():
    worker = CountingWorker([])
    run(worker, 0.35, poll=0.1)
    assert 2 <= worker.calls <= 6


def test_productive_worker_polls_again_immediately():
    worker = CountingWorker([True] * 50)
    run(worker, 0.1, poll=10)
    assert worker.calls >= 20
