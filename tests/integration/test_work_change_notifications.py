"""Work-change notifications reach subscribers only after commit, per Work."""
import asyncio
import os
from uuid import uuid4

from sqlalchemy import text

from spg.infrastructure.work_changes import CHANNEL, WorkChangeHub


def _hub():
    hub = WorkChangeHub(os.environ["SPG_TEST_DATABASE_URL"])
    hub.start()
    assert hub.connected.wait(10)
    return hub


def test_committed_notification_signals_only_the_subscribed_work(postgres_database):
    hub = _hub()
    watched, other = uuid4(), uuid4()

    async def scenario():
        queue = hub.subscribe(watched)
        with postgres_database.engine.begin() as connection:
            connection.execute(text("SELECT pg_notify(:c, :w)"), {"c": CHANNEL, "w": str(other)})
        await asyncio.sleep(0.5)
        assert queue.empty()
        with postgres_database.engine.begin() as connection:
            connection.execute(text("SELECT pg_notify(:c, :w)"), {"c": CHANNEL, "w": str(watched)})
        assert await asyncio.wait_for(queue.get(), 5) is True
        hub.unsubscribe(watched, queue)

    try:
        asyncio.run(scenario())
    finally:
        hub.stop()


def test_rolled_back_write_is_never_signalled_and_bursts_coalesce(postgres_database):
    hub = _hub()
    watched = uuid4()

    async def scenario():
        queue = hub.subscribe(watched)
        connection = postgres_database.engine.connect()
        transaction = connection.begin()
        connection.execute(text("SELECT pg_notify(:c, :w)"), {"c": CHANNEL, "w": str(watched)})
        transaction.rollback()
        connection.close()
        await asyncio.sleep(0.5)
        assert queue.empty()
        with postgres_database.engine.begin() as connection:
            for _ in range(5):
                connection.execute(text("SELECT pg_notify(:c, :w)"), {"c": CHANNEL, "w": str(watched) + ""})
        await asyncio.wait_for(queue.get(), 5)
        await asyncio.sleep(0.3)
        assert queue.empty()  # PostgreSQL folds identical payloads; the hub keeps one pending signal

    try:
        asyncio.run(scenario())
    finally:
        hub.stop()
