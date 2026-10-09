"""C3 Work-owner receipt persistence on exact controlled C1 admission fixtures."""
from uuid import UUID

import pytest

from spg.application.governed_obligations import form_fulfillment_projection, plan_with_formation_receipts
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from tests.integration.test_c1_contract_continuity import admitted_contract, c1_schema

pytestmark = pytest.mark.postgresql


class NeverCallAgain:
    def __init__(self): self.calls = 0
    def form(self, inventory, capabilities, *, validation_feedback=None):
        self.calls += 1
        raise AssertionError("A sealed same-basis receipt must be replayed without another model call")


def test_owner_observation_survives_legal_plan_clear_and_preserves_budget(postgres_database, admitted_contract):
    works, work_id, revision, ir, repository, baseline, pwu = admitted_contract
    original = pwu.completion_contract.fulfillment_bindings
    fingerprint = original[0].projection_inventory_fingerprint
    assert fingerprint
    with postgres_database.unit_of_work() as uow:
        product = ProductStore(uow.session)
        previous_plan = product.work(work_id).production_plan
        assert previous_plan is not None
        records = RuntimeStore(uow.session).governance_for_subject(fingerprint)
        assert [r.scope["stage"] for r in records] == ["MODEL_REQUEST_PENDING", "MODEL_RESPONSE_OBSERVED", "SEMANTIC_REVIEW_PENDING",
            "SEMANTIC_REVIEW_OBSERVED", "SEMANTIC_REVIEW_VALIDATED", "CANDIDATE_VALIDATED"]
        # Real PG JSONB lookup uses receipt identity, even when legacy carrier
        # record.id is a separately allocated UUID. No inference from rev-parse.
        for record in records:
            assert record.id != UUID(record.scope["receipt_id"])
            exact=RuntimeStore(uow.session).fulfillment_observations_for_receipt(UUID(record.scope["receipt_id"]))
            assert exact == [record]
        assert all(r.decision_type == "WORK_FULFILLMENT_OBSERVATION" and r.authority_identity == "work-governance:derived-candidate-observation" for r in records)
        product.update_work(work_id, {"production_plan_proposal": None})
        uow.commit()
    provider = NeverCallAgain()
    replayed = form_fulfillment_projection(revision, ir, provider=provider, database=postgres_database,
        source_revision=baseline.repository_revision, exact_target_paths=("index.html",))
    assert provider.calls == 0
    assert [b.model_dump(exclude={"formation_receipt"}) for b in replayed] == [b.model_dump(exclude={"formation_receipt"}) for b in original]
    recovered_plan = plan_with_formation_receipts(postgres_database, work_id, previous_plan, inventory_fingerprint=fingerprint)
    assert len(recovered_plan.fulfillment_formation_receipts) == 6
    with postgres_database.unit_of_work() as uow:
        product = ProductStore(uow.session)
        assert product.work(work_id).production_plan is None
        assert product.current_work_reality_revision(work_id) == revision
        runtime = RuntimeStore(uow.session)
        assert len(runtime.governance_for_subject(fingerprint)) == len(records)
        # The actual observation governance IDs cannot be looked up as Human
        # Authorization records; this does not invent a Candidate or approval.
        assert all(runtime.human_authorization(r.id) is None for r in records)
