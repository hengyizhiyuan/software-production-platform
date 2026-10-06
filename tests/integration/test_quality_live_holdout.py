"""Private generated material is visible only inside the evaluation recipe process."""
import json
import os
from pathlib import Path

import pytest
from spg.application.bootstrap import bootstrap
from spg.config import Settings


pytestmark = pytest.mark.postgresql


def test_sealed_unseen_intent_uses_real_compiler_and_irk(postgres_database):
    path = os.environ.get("WATT_QUALITY_CASE_FILE")
    if not path:
        pytest.skip("A sealed Campaign Case is required; never invent a holdout result")
    definition = json.loads(Path(path).read_text())
    assert definition["runner_key"] == "sealed-live-intent"
    private = definition["private_material"]
    s = Settings(database_url=os.environ["SPG_TEST_DATABASE_URL"], admin_enabled=False,
        managed_source_provider="disabled", owner_runtime_mode="OFF")
    assert s.wic_provider_adapter == "deepseek" and s.deepseek_api_key
    interaction = bootstrap(s).interaction(postgres_database)
    try:
        turn = interaction.create_interaction(human_identity="human:quality")
        result = interaction.append_and_assess(turn.id, private["human_text"], human_identity="human:quality")
        assessment = result.latest_assessment
        assert assessment is not None and assessment.semantic_ir is not None
        ir = assessment.semantic_ir
        production = ir.current_production
        assert production and all(p.current and not p.repository_required
            and p.repository_reference is None for p in production)
        assert ir.repository_source is None
    finally:
        interaction.shutdown()
