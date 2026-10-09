"""Prior-Runtime truthful stops; controlled Owner stores, no model or database."""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

import spg.application.steering_production as production_module
import spg.application.governed_obligations as obligations
import spg.infrastructure.persistence.interaction_store as interaction_module
from spg.application.planning import ProductionPlanningService
from spg.application.steering_driver import PlanSteeringDriver
from spg.application.steering_production import (
    FulfillmentProjectionNotReady, SteeringProductionService,
)
from spg.domain.change import ProductionTargetKind
from spg.domain.governed_obligation import (
    FulfillmentOwner, FulfillmentPhase, fulfillment_source_ref,
)
from spg.domain.planning import PlannedArtifactOperation, ProductionPlanArtifactTarget
from spg.domain.product import SteeringProductionRequest
from spg.providers.rule_based_planner import RuleBasedProductionPlanner
from tests.test_fulfillment_projection import Oracle, basis


class OwnerFixture:
    def __init__(self):
        self.governance = []
        self.commits = 0

    @contextmanager
    def unit_of_work(self):
        yield SimpleNamespace(session=self, commit=self.commit, rollback=lambda: None)

    def commit(self):
        self.commits += 1


def setup_service(monkeypatch, *, failed):
    revision, ir = basis()
    # Exercise real bounded formation only in the declared transport fixture.
    # Its memory carrier has the same terminal replay contract, no live Provider.
    if failed:
        ir.clauses = (ir.clauses[0].model_copy(update={"requested_effects": ()}),)
    assessment = SimpleNamespace(id=revision.source_assessment_id, semantic_ir=ir)
    resource = SimpleNamespace(id=uuid4(), repository_identity="test://c3-stop",
                               location_ref="/declared-source", context_references=())
    scope = SimpleNamespace(id=uuid4(), summary="one admitted artifact")
    baseline = SimpleNamespace(id=uuid4(), repository_revision=revision.source_revision)
    work = SimpleNamespace(id=revision.work_id, current_work_reality_revision_id=revision.id,
        desired_outcome="One exact artifact", raw_user_requirement="One exact artifact",
        production_objective="One exact artifact")
    database = OwnerFixture()

    class ProductFixture:
        def __init__(self, session):
            assert session is database
        def work(self, identity, *, for_update=False):
            assert identity == work.id
            return work
        def scope_for_work(self, _): return scope
        def resource(self, _): return resource
        def current_work_reality_revision(self, _): return revision
        def runtime_binding_for_step(self, _): return None
        def runtime_bindings(self, _): return []

    class RuntimeFixture:
        def __init__(self, session):
            assert session is database
        def governance_for_subject(self, identity):
            return [SimpleNamespace(**row) for row in database.governance
                    if row["subject_identity"] == identity]
        def insert_governance(self, values):
            database.governance.append(dict(values))

    monkeypatch.setattr(production_module, "ProductStore", ProductFixture)
    monkeypatch.setattr(production_module, "RuntimeStore", RuntimeFixture)
    monkeypatch.setattr(interaction_module, "InteractionStore",
        lambda _: SimpleNamespace(assessment=lambda _: assessment))
    monkeypatch.setattr(obligations, "plan_with_formation_receipts", lambda db, wid, plan, **kw: plan)
    oracle = Oracle([TimeoutError()]) if failed else Oracle([])
    actual_admitted = obligations.admitted_fulfillment_bindings
    monkeypatch.setattr(obligations, "admitted_fulfillment_bindings",
        lambda rev, assessed, **kw: actual_admitted(rev, assessed,
            provider=kw["provider"], source_revision=kw["source_revision"],
            exact_target_paths=kw["exact_target_paths"]))
    service = SteeringProductionService.__new__(SteeringProductionService)
    service.database = database
    service.fulfillment_provider = oracle
    service.runtime = SimpleNamespace(current_baseline=lambda **kw: baseline,
        create_initial_runtime_spine=lambda *_: pytest.fail("Unresolved must create no Runtime/PWU/Attempt/Dispatch"))
    service.planning = ProductionPlanningService(RuleBasedProductionPlanner())
    service._task_contract = lambda *args, **kw: None
    request = SteeringProductionRequest(work_id=work.id, work_reality_revision_id=revision.id,
        steering_step_id=uuid4(), production_objective="One exact artifact",
        target_kind=ProductionTargetKind.DOCUMENTATION_WORK, engineering_scope_id=scope.id,
        engineering_resource_id=resource.id, repository_identity=resource.repository_identity,
        source_baseline_id=baseline.id, source_revision=baseline.repository_revision,
        artifact_targets=(ProductionPlanArtifactTarget(path="index.html", operation=PlannedArtifactOperation.CREATE),),
        constraints=revision.constraints, verification_expectation="The exact artifact exists")
    service.materialize_request = lambda _: request
    return service, request, database, revision, ir, oracle


def test_terminal_formation_blocks_before_planning_and_runtime_and_replays_once(monkeypatch):
    service, request, database, revision, ir, oracle = setup_service(monkeypatch, failed=True)
    original_facts = [fact.model_dump(mode="json") for fact in revision.engineering_semantic_facts]
    service.planning = SimpleNamespace(propose=lambda *_: pytest.fail("Unresolved must stop before Planning"))
    errors = []
    for _ in range(2):
        with pytest.raises(FulfillmentProjectionNotReady) as stopped:
            service.admit_cycle(request)
        errors.append(stopped.value)
    assert len(oracle.calls) == 1
    assert len(database.governance) == database.commits == 1
    assert errors[0].observation_id == errors[1].observation_id
    record = database.governance[0]
    assert record["decision_type"] == "WORK_FULFILLMENT_STOP_OBSERVATION"
    assert record["subject_type"] == "WORK_FULFILLMENT_STOP_BASIS"
    assert record["authority_identity"] == "work-governance:derived-candidate-observation"
    evidence = record["scope"]
    inventory = obligations.fulfillment_inventory(revision, ir,
        source_revision=request.source_revision, exact_target_paths=("index.html",))
    assert set(evidence["source_refs"]) == {source["source_ref"] for source in inventory["sources"]}
    assert evidence["unresolved_source_refs"] == evidence["source_refs"]
    assert evidence["inventory_fingerprint"] == inventory["inventory_fingerprint"]
    assert evidence["terminal_reason"] == "OBLIGATION_FORMATION_TRANSPORT_TimeoutError"
    assert evidence["formation_receipt_refs"] == [f"work-plan-receipt:{row['receipt_id']}" for row in oracle._fulfillment_receipts]
    assert evidence["candidate_is_authority"] is False and evidence["runtime_admitted"] is False
    assert "LOCAL_OBLIGATION_RECOVERED" not in str(record)
    assert [fact.model_dump(mode="json") for fact in revision.engineering_semantic_facts] == original_facts
    assert oracle._fulfillment_receipts[-1]["terminal"] is True
    assert oracle._fulfillment_receipts[-1]["validation_passed"] is False


def test_partial_unresolved_is_not_silently_admitted_without_terminal_receipt(monkeypatch):
    service, request, database, revision, ir, oracle = setup_service(monkeypatch, failed=False)
    inventory = obligations.fulfillment_inventory(revision, ir,
        source_revision=request.source_revision, exact_target_paths=("index.html",))
    bindings = obligations.deterministic_fulfillment_projection(revision, ir, inventory)
    pending = bindings[-1].model_copy(update={"state": "UNRESOLVED",
        "owner": FulfillmentOwner.UNRESOLVED, "phase": FulfillmentPhase.UNRESOLVED,
        "evidence_method": "UNRESOLVED", "gate_ref": "UNRESOLVED"})
    monkeypatch.setattr(obligations, "admitted_fulfillment_bindings", lambda *a, **kw: (*bindings[:-1], pending))
    service.planning = SimpleNamespace(propose=lambda *_: pytest.fail("Partial inventory cannot proceed"))
    with pytest.raises(FulfillmentProjectionNotReady):
        service.admit_cycle(request)
    evidence = database.governance[0]["scope"]
    assert evidence["unresolved_source_refs"] == [fulfillment_source_ref(pending)]
    assert evidence["formation_receipt_refs"] == [] and evidence["terminal_reason"] is None
    assert evidence["candidate_is_authority"] is False and oracle.calls == []


def test_lawful_pending_evidence_routes_still_form_original_completion_contract(monkeypatch):
    service, request, database, revision, ir, oracle = setup_service(monkeypatch, failed=False)
    plan, completion, horizon, objective = service._production_contract(request)
    assert completion.fulfillment_bindings
    assert all(binding.state != "UNRESOLVED" for binding in completion.fulfillment_bindings)
    assert any(binding.phase is FulfillmentPhase.CONTINUOUS_FROM_ADMISSION
               for binding in completion.fulfillment_bindings)
    assert completion.required_outputs == ("index.html",)
    assert completion.artifact_contract.source_revision == request.source_revision
    assert plan.fit_classification.value == "ONE_PWU_FIT"
    assert horizon.value == "DOCUMENTATION" and objective
    assert database.governance == [] and database.commits == 0 and oracle.calls == []


def test_driver_truthful_blocked_does_not_create_refine_human_or_provider_retry(monkeypatch):
    service, request, database, revision, ir, oracle = setup_service(monkeypatch, failed=True)
    def iterate(_):
        service.admit_cycle(request)
        pytest.fail("Unresolved cannot reach a scheduled production action")
    def forbidden(*args, **kw):
        pytest.fail("Terminal observation must not refine/escalate/retry/reset")
    driver = SimpleNamespace(_work_convergence_halted=lambda _: False,
        _provider_failure_escalated=lambda _: False,
        _stopping=SimpleNamespace(is_set=lambda: False), max_automatic_transitions=1,
        iterate=iterate, _observe_convergence=forbidden, _record_provider_failure=forbidden,
        _clear_provider_failure=forbidden)
    for _ in range(2):
        result = PlanSteeringDriver.activate(driver, request.work_id)
        assert result.stop_reason.value == "BLOCKED"
        assert result.iterations_executed == 0 and result.last_action is None
    assert len(database.governance) == 1 and len(oracle.calls) == 1
