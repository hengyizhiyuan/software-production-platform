"""Fan out PostgreSQL Work-change notifications to in-process subscribers.

One daemon thread per process holds a dedicated `LISTEN watt_work_changed`
connection. Subscribers (SSE clients) register an asyncio queue for one Work
and receive a bare "changed" signal; they then re-read the existing
projection. No Work truth flows through here.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from uuid import UUID

LOGGER = logging.getLogger(__name__)
CHANNEL = "watt_work_changed"


class WorkChangeHub:
    def __init__(self, database_url: str) -> None:
        # SQLAlchemy URLs carry a driver suffix that libpq does not accept.
        self.dsn = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self._lock = threading.Lock()
        self._subscribers: dict[UUID, set[tuple[asyncio.AbstractEventLoop, asyncio.Queue]]] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.connected = threading.Event()

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="watt-work-change-hub", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def subscribe(self, work_id: UUID) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        with self._lock:
            self._subscribers.setdefault(work_id, set()).add((asyncio.get_running_loop(), queue))
        return queue

    def unsubscribe(self, work_id: UUID, queue: asyncio.Queue) -> None:
        with self._lock:
            entries = self._subscribers.get(work_id, set())
            entries = {entry for entry in entries if entry[1] is not queue}
            if entries:
                self._subscribers[work_id] = entries
            else:
                self._subscribers.pop(work_id, None)

    def publish(self, work_id: UUID) -> None:
        with self._lock:
            targets = tuple(self._subscribers.get(work_id, ()))
        for loop, queue in targets:
            loop.call_soon_threadsafe(_signal, queue)

    def _run(self) -> None:
        import psycopg

        backoff = 1.0
        while not self._stop.is_set():
            try:
                with psycopg.connect(self.dsn, autocommit=True) as connection:
                    connection.execute(f"LISTEN {CHANNEL}")
                    self.connected.set()
                    backoff = 1.0
                    while not self._stop.is_set():
                        for notice in connection.notifies(timeout=5.0, stop_after=64):
                            try:
                                self.publish(UUID(notice.payload))
                            except ValueError:
                                continue
            except Exception:  # noqa: BLE001 - the hub must outlive database restarts
                self.connected.clear()
                LOGGER.warning("Work change listener disconnected; retrying", exc_info=True)
                self._stop.wait(backoff)
                backoff = min(backoff * 2, 30.0)


def _signal(queue: asyncio.Queue) -> None:
    # Changes coalesce: one pending signal is enough to trigger a re-read.
    if queue.empty():
        queue.put_nowait(True)
