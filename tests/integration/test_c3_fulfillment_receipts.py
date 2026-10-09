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


@pytest.mark.parametrize("route", ("work", "steering"))
def test_actual_compact_observation_replays_from_postgresql_without_repeating_formation(
    postgres_database, tmp_path, monkeypatch, route, record_property,
):
    """Controlled interruption after the actual raw observation Owner commit.

    Only the runtime adapter is a no-network oracle. Actual admission, receipt
    ownership, raw compact decoding and bounded independent review remain real.
    This is not live semantic intelligence, production Work or Human acceptance.
    """
    import json
    from types import SimpleNamespace
    from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
    from spg.infrastructure.persistence.interaction_store import InteractionStore
    from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
    from tests.integration import test_c1_contract_continuity as c1
    from tests.test_c3_fulfillment_capacity_representation import controlled_wire

    declared = c1.DeclaredC1Fulfillment()
    calls, inventories = [], []

    class ControlledFormationInterruption(BaseException):
        pass

    def generate(**request):
        payload = json.loads(request["input_text"])
        calls.append(payload)
        inventory = payload["immutable_inventory"]
        if "untrusted_fulfillment_candidate" in payload:
            from spg.domain.governed_obligation import FulfillmentProjectionCandidate
            plan = FulfillmentProjectionCandidate.model_validate(payload["untrusted_fulfillment_candidate"])
            output = declared.review(inventory, plan).model_dump_json()
        else:
            plan = declared.form(inventory, payload["existing_capability_contracts"],
                validation_feedback=payload.get("same_basis_validation_feedback"))
            wire, _ = controlled_wire(inventory, plan, feedback=payload.get("same_basis_validation_feedback"))
            output = json.dumps(wire, ensure_ascii=False)
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model="controlled-pg-no-network", effective_model="controlled-pg-no-network",
            request_id=f"controlled-pg-compact-{len(calls)}", usage=ModelUsage(), timing=ModelTiming(), retry_count=0)

    class InterruptedCompactProvider(ModelFulfillmentCandidateProvider):
        def __init__(self):
            super().__init__(lambda: SimpleNamespace(generate=generate, close=lambda: None))
            self.interrupt_once = True

        def form(self, inventory, capabilities, *, validation_feedback=None, receipt_callback=None):
            inventories.append(inventory)
            def observed(**row):
                assert receipt_callback is not None
                receipt_callback(**row)  # Actual PG commit occurs before the interruption.
                if self.interrupt_once:
                    self.interrupt_once = False
                    raise ControlledFormationInterruption()
            return super().form(inventory, capabilities, validation_feedback=validation_feedback,
                receipt_callback=observed)

    provider = InterruptedCompactProvider()
    monkeypatch.setattr(c1, "DeclaredC1Fulfillment", lambda: provider)
    with pytest.raises(ControlledFormationInterruption):
        c1._admit_c1(postgres_database, tmp_path, route)
    inventory = inventories[-1]
    work_id = UUID(inventory["work_id"])
    fingerprint = inventory["inventory_fingerprint"]
    with postgres_database.unit_of_work() as uow:
        product = ProductStore(uow.session)
        revision = product.current_work_reality_revision(work_id)
        assessment = InteractionStore(uow.session).assessment(revision.source_assessment_id)
        ir = assessment.semantic_ir
        rows = RuntimeStore(uow.session).governance_for_subject(fingerprint)
        assert [row.scope["stage"] for row in rows] == ["MODEL_REQUEST_PENDING", "MODEL_RESPONSE_OBSERVED"]
        raw = rows[-1].scope
        assert raw["provider_wire_version"] == "fulfillment-compact-v1"
        assert "candidate" not in raw
        assert json.loads(raw["candidate_output"])["v"] == 1
        original_facts = tuple(fact.model_dump(mode="json") for fact in revision.engineering_semantic_facts)
    assert len(calls) == 1
    result = form_fulfillment_projection(revision, ir, provider=provider, database=postgres_database,
        source_revision=inventory["source_revision"], exact_target_paths=inventory["exact_target_paths"])
    assert len(calls) == 2 and "untrusted_fulfillment_candidate" in calls[-1]
    assert all(binding.state != "UNRESOLVED" for binding in result)
    assert {binding.component for binding in result} >= {
        "artifact-content", "git-diff-scope", "deploy", "publish", "reviewable-candidate"}
    again = form_fulfillment_projection(revision, ir, provider=provider, database=postgres_database,
        source_revision=inventory["source_revision"], exact_target_paths=inventory["exact_target_paths"])
    assert len(calls) == 2
    assert [binding.model_dump(exclude={"formation_receipt"}) for binding in again] == [
        binding.model_dump(exclude={"formation_receipt"}) for binding in result]
    with postgres_database.unit_of_work() as uow:
        runtime = RuntimeStore(uow.session)
        rows = runtime.governance_for_subject(fingerprint)
        assert len(rows) == 6
        assert ProductStore(uow.session).current_work_reality_revision(work_id) == revision
        assert tuple(fact.model_dump(mode="json") for fact in revision.engineering_semantic_facts) == original_facts
        assert all(runtime.human_authorization(row.id) is None for row in rows)
        assert all(row.authority_identity == "work-governance:derived-candidate-observation" for row in rows)
    record_property("controlled_fixture_admission_route", route)
    record_property("work_id", str(work_id))
    record_property("work_reality_revision_id", str(revision.id))
    record_property("inventory_fingerprint", fingerprint)
    record_property("logical_stub_calls", len(calls))
    record_property("receipt_ids", json.dumps([row.scope["receipt_id"] for row in rows]))
