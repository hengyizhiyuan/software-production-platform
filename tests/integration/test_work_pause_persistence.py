"""Pause is durable Work governance, not a rewritten execution result."""
from uuid import uuid4
from sqlalchemy import text
from spg.application.work import WorkApplicationService
from tests.integration.test_product_experience_attention import clean_product_reality, experience_reality


def test_explicit_pause_survives_new_service_and_schedules_no_attempt(experience_reality):
    projection, _, _, wid, _ = experience_reality
    service = projection.work
    with service.database.engine.connect() as c:
        before = c.execute(text('SELECT count(*) FROM execution_attempts')).scalar_one()
    assert not service.is_paused(wid)
    service.pause_work(wid, command_id=uuid4(), authority_identity='human:owner', reason='Pause this Work')
    restarted = WorkApplicationService(service.database)
    assert restarted.is_paused(wid)
    assert restarted.advance_work(wid).most_recent_meaningful_event == 'WORK_PAUSED_BY_HUMAN'
    with service.database.engine.connect() as c:
        assert c.execute(text('SELECT count(*) FROM execution_attempts')).scalar_one() == before
