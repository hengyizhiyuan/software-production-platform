"""Turn execution: ordered within one interaction, parallel across interactions.

A single global worker made every conversation wait behind every other one.
This executor keeps the per-interaction ordering the conversation relies on
(turns of one interaction never overlap) while different interactions run
concurrently on a bounded pool.
"""
from __future__ import annotations

from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock
from typing import Callable, Hashable


class KeyedSerialExecutor:
    def __init__(self, max_workers: int, thread_name_prefix: str) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=thread_name_prefix)
        self._lock = Lock()
        self._queues: dict[Hashable, deque[tuple[Callable, tuple, Future]]] = {}

    def submit(self, key: Hashable, fn: Callable, *args) -> Future:
        """Run `fn(*args)` after every task already submitted for `key`."""
        future: Future = Future()
        with self._lock:
            queue = self._queues.get(key)
            if queue is not None:
                queue.append((fn, args, future))
                return future
            self._queues[key] = deque()
        try:
            self._pool.submit(self._drain, key, fn, args, future)
        except BaseException:
            # The pool refused (e.g. shut down): never leave the key wedged.
            with self._lock:
                self._queues.pop(key, None)
            raise
        return future

    def _drain(self, key: Hashable, fn: Callable, args: tuple, future: Future) -> None:
        while True:
            if future.set_running_or_notify_cancel():
                try:
                    future.set_result(fn(*args))
                except BaseException as error:  # noqa: BLE001 - delivered through the Future
                    future.set_exception(error)
            with self._lock:
                queue = self._queues[key]
                if not queue:
                    del self._queues[key]
                    return
                fn, args, future = queue.popleft()

    def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
        if cancel_futures:
            with self._lock:
                for queue in self._queues.values():
                    while queue:
                        queue.popleft()[2].cancel()
        self._pool.shutdown(wait=wait, cancel_futures=cancel_futures)
