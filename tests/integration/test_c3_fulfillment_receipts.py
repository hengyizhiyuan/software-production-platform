"""C3 Work-owner receipt persistence on exact controlled C1 admission fixtures."""
from uuid import UUID
from tests.test_c3_source_consumption_proof import fixture_review_proof
from tests.test_c3_fulfillment_capacity_representation import decode_review_input
from spg.providers.fulfillment_candidate import _restore_formation_inventory_view

import pytest

from spg.application.governed_obligations import form_fulfillment_projection, plan_with_formation_receipts
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from tests.integration.test_c1_contract_continuity import admitted_contract, c1_schema

pytestmark = pytest.mark.postgresql


def test_wire_feedback_capacity_stop_is_bounded_durable_and_never_reopens(postgres_database, tmp_path, monkeypatch):
    import json
    from copy import deepcopy
    from types import SimpleNamespace
    from spg.application import governed_obligations as app
    from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
    from spg.infrastructure.persistence.interaction_store import InteractionStore
    from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
    from tests.integration import test_c1_contract_continuity as c1
    from tests.test_c3_fulfillment_capacity_representation import controlled_wire
    declared=c1.DeclaredC1Fulfillment();calls=[];inventories=[]
    def generate(**request):
        payload=json.loads(request['input_text']);calls.append(payload)
        assert 'untrusted_fulfillment_candidate' not in payload
        inventory=_restore_formation_inventory_view(payload['immutable_inventory'],payload.get('existing_ir_item_table',{}))
        inventories.append(inventory)
        plan=declared.form(inventory,payload['existing_capability_contracts'])
        wire,_=controlled_wire(inventory,plan,owner_preconditions=payload.get('owner_source_preconditions'))
        route=deepcopy(wire['routes'][0])
        route.update(c=next(i for i,c in enumerate(app.fulfillment_capability_contracts()) if c['capability']=='UNRESOLVED'),f=[],t=[],u=[])
        wire['routes'].append(route)
        return StructuredModelResult(output_text=json.dumps(wire),provider=ModelProvider.DEEPSEEK,
            requested_model='controlled-pg-capacity',effective_model='controlled-pg-capacity',
            request_id='controlled-pg-capacity-1',usage=ModelUsage(),timing=ModelTiming(),retry_count=0)
    provider=ModelFulfillmentCandidateProvider(lambda:SimpleNamespace(generate=generate,close=lambda:None))
    monkeypatch.setattr(c1,'DeclaredC1Fulfillment',lambda:provider)
    bind=app._bind_repair_feedback
    def large_feedback(*args,**kwargs):
        value=json.loads(bind(*args,**kwargs));value['controlled_observation_padding']='x'*140000
        return json.dumps(value,separators=(',',':'))
    monkeypatch.setattr(app,'_bind_repair_feedback',large_feedback)
    class AfterDurableCapacity(BaseException):pass
    append=app.FulfillmentFormationReceipts.append
    def checkpoint(self,*args,**kwargs):
        try:return append(self,*args,**kwargs)
        except app.FulfillmentReceiptCapacityStop:raise AfterDurableCapacity()
    monkeypatch.setattr(app.FulfillmentFormationReceipts,'append',checkpoint)
    with pytest.raises(AfterDurableCapacity):c1._admit_c1(postgres_database,tmp_path,'work')
    monkeypatch.setattr(app.FulfillmentFormationReceipts,'append',append)
    inventory=inventories[-1];work_id=UUID(inventory['work_id']);fingerprint=inventory['inventory_fingerprint']
    with postgres_database.unit_of_work() as uow:
        revision=ProductStore(uow.session).current_work_reality_revision(work_id)
        ir=InteractionStore(uow.session).assessment(revision.source_assessment_id).semantic_ir
        rows=RuntimeStore(uow.session).governance_for_subject(fingerprint)
        original=[deepcopy(r.scope) for r in rows]
        terminal=next(r for r in original if r.get('terminal'))
        assert terminal['terminal_reason']=='OBLIGATION_FORMATION_RECEIPT_LIMIT'
        assert terminal['validation_passed'] is False and 'validation_feedback' not in terminal
        assert terminal['capacity_observation']['disposition'].startswith('PAYLOAD_NOT_RETAINED')
        assert all(len(json.dumps(r,ensure_ascii=False,default=str).encode())<=131072 for r in original)
    never=NeverCallAgain()
    replay=app.form_fulfillment_projection(revision,ir,provider=never,database=postgres_database,
        source_revision=inventory['source_revision'],exact_target_paths=inventory['exact_target_paths'])
    assert never.calls==0 and len(calls)==1
    assert all(b.state=='UNRESOLVED' for b in replay)
    assert replay[0].formation_receipt['terminal_reason']=='OBLIGATION_FORMATION_RECEIPT_LIMIT'
    with postgres_database.unit_of_work() as uow:
        runtime=RuntimeStore(uow.session);rows=runtime.governance_for_subject(fingerprint)
        assert [r.scope for r in rows]==original
        assert all(runtime.human_authorization(r.id) is None for r in rows)


class NeverCallAgain:
    def __init__(self): self.calls = 0
    def form(self, inventory, capabilities, *, validation_feedback=None):
        self.calls += 1
        raise AssertionError("A sealed same-basis receipt must be replayed without another model call")


@pytest.mark.parametrize('first_failure', ('semantic', 'semantic-jsonb-order', 'semantic-framed', 'incomplete', 'critic-schema', 'critic-json', 'consumption-proof', 'critic-duplicate'))
def test_rejected_independent_review_feedback_persists_and_replays_in_postgresql(postgres_database, tmp_path, monkeypatch, first_failure):
    import json
    from types import SimpleNamespace
    from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
    from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
    from tests.integration import test_c1_contract_continuity as c1
    from tests.test_c3_fulfillment_capacity_representation import controlled_wire
    from tests.test_c3_semantic_contract_calibration import review
    declared = c1.DeclaredC1Fulfillment()
    calls, reviews = [], []
    def generate(**request):
        payload = json.loads(request['input_text']); calls.append(payload)
        inventory = _restore_formation_inventory_view(payload['immutable_inventory'], payload.get('existing_ir_item_table', {}))
        if 'untrusted_fulfillment_candidate' in payload:
            candidate = decode_review_input(payload)
            verdict = fixture_review_proof(inventory, candidate, review(inventory, candidate), payload)
            if not reviews and first_failure.startswith('semantic'):
                first, *rest = verdict.component_results
                verdict = verdict.model_copy(update={'component_results': (
                    first.model_copy(update={'complete_and_equivalent': False, 'reason': 'Controlled rejected interpretation.'}), *rest)})
            if not reviews and first_failure == 'critic-schema':
                first = verdict.component_results[0]
                verdict = verdict.model_copy(update={'component_results': (
                    first.model_copy(update={'component_id': first.component_id[:48]}),)})
            if not reviews and first_failure == 'consumption-proof':
                raw = verdict.model_dump(mode="json")
                raw["source_results"][0]["consumption_checks"][0]["route_indices"] = []
                verdict = type(verdict).model_validate(raw)
            if not reviews and first_failure == 'critic-duplicate':
                from copy import deepcopy
                raw = verdict.model_dump(mode='json')
                raw['source_results'][0]['consumption_checks'].append(
                    deepcopy(raw['source_results'][0]['consumption_checks'][0]))
                verdict = type(verdict).model_validate(raw)
            reviews.append(verdict)
            output = verdict.model_dump_json()
            if len(reviews) == 1 and first_failure == 'critic-json':
                output = '{'
        else:
            plan = declared.form(inventory, payload['existing_capability_contracts'],
                validation_feedback=payload.get('same_basis_validation_feedback'))
            if first_failure == 'incomplete' and payload.get('same_basis_validation_feedback') is None:
                plan = plan.model_copy(update={'routes': tuple(r.model_copy(update={
                    'capability': 'UNRESOLVED', 'target_paths': (), 'supporting_source_refs': ()})
                    if r.source_ref.startswith('semantic-fact:') else r for r in plan.routes)})
            wire, _ = controlled_wire(inventory, plan, feedback=payload.get('same_basis_validation_feedback'),
                owner_preconditions=payload.get('owner_source_preconditions'))
            output = json.dumps(wire)
            if first_failure == 'semantic-framed':
                output = '```json\n' + output + '\n```'
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model='controlled-pg-semantic-feedback', effective_model='controlled-pg-semantic-feedback',
            request_id=f'controlled-pg-feedback-{len(calls)}', usage=ModelUsage(), timing=ModelTiming(), retry_count=0)
    provider = ModelFulfillmentCandidateProvider(lambda: SimpleNamespace(generate=generate, close=lambda: None))
    monkeypatch.setattr(c1, 'DeclaredC1Fulfillment', lambda: provider)
    _, work_id, revision, ir, _, baseline, pwu = c1._admit_c1(postgres_database, tmp_path, 'work')
    assert len(calls) == 4 and len(reviews) == 2
    fingerprint = pwu.completion_contract.fulfillment_bindings[0].projection_inventory_fingerprint
    with postgres_database.unit_of_work() as uow:
        records = RuntimeStore(uow.session).governance_for_subject(fingerprint)
        failed = next(r.scope for r in records if r.scope['stage'] == 'CANDIDATE_VALIDATED' and r.scope['attempt'] == 1)
        feedback = json.loads(failed['validation_feedback'])
        observed = next(r.scope for r in records if r.scope['stage'] == 'SEMANTIC_REVIEW_OBSERVED' and r.scope['attempt'] == 1)
        if first_failure.startswith('semantic'):
            assert feedback['semantic_review_feedback_binding']['observed_receipt_id'] == observed['receipt_id']
            assert feedback['violations'][0]['review_reason'] == 'Controlled rejected interpretation.'
        elif first_failure in ('consumption-proof', 'critic-duplicate'):
            assert feedback['primary_error'] == ('OBLIGATION_SOURCE_CONSUMPTION_ROUTE_REQUIRED'
                if first_failure == 'consumption-proof' else 'OBLIGATION_SOURCE_CONSUMPTION_DUPLICATE')
            violations = [v for v in feedback['violations'] if 'source_consumption_comparison' in v]
            assert violations and violations[0]['source_consumption_comparison']['check'] == (
                0 if first_failure == 'consumption-proof' else 1)
            assert feedback['semantic_review_feedback_binding']['observed_receipt_id'] == observed['receipt_id']
            assert failed['terminal'] is False
        elif first_failure.startswith('critic-'):
            from hashlib import sha256
            assert feedback['primary_error'] == 'OBLIGATION_SEMANTIC_REVIEW_SCHEMA_INVALID'
            assert feedback['semantic_review_feedback_binding']['observed_receipt_id'] == observed['receipt_id']
            diagnostic = feedback['semantic_review_feedback_binding']['review_contract_failure']
            assert diagnostic['review_output_sha256'] == sha256(observed['review_output'].encode()).hexdigest()
            assert diagnostic['missing_component_route_indices']
            validated = next(r for r in records if r.scope['stage'] == 'SEMANTIC_REVIEW_VALIDATED' and r.scope['attempt'] == 1)
            assert validated.scope['validation_passed'] is False
            assert validated.scope['review_contract_failure'] == diagnostic
            assert 'INDEPENDENT_SEMANTIC_REVIEW' in feedback['not_evaluable']
        else:
            assert feedback['completion_observation_contract'] == 'existing-bounded-completion-feedback-v1'
            assert feedback['primary_error'] == 'OBLIGATION_PROJECTION_UNRESOLVED'
            assert all(v['code'] == 'OBLIGATION_PROJECTION_UNRESOLVED' for v in feedback['violations'])
            assert failed['terminal'] is False
            assert feedback['repair_feedback_binding']['completion_feedback_contract'] == 'existing-bounded-completion-feedback-v1'
        count = len(records)
        if first_failure in ('consumption-proof', 'critic-duplicate', 'critic-schema', 'critic-json'):
            from spg.domain.governed_obligation import canonical_fingerprint
            second = next(r.scope for r in records if r.scope['stage'] == 'SEMANTIC_REVIEW_PENDING' and r.scope['attempt'] == 2)
            bound = calls[3]['existing_bound_reviewer_feedback']
            assert second['review_repair_context'] == bound
            assert second['review_repair_context_fingerprint'] == canonical_fingerprint(bound)
            assert bound['previous_review_binding']['observed_receipt_id'] == observed['receipt_id']
        if first_failure == 'semantic-framed':
            from spg.providers.fulfillment_candidate import _fulfillment_wire_value
            formations = [r.scope for r in records if r.scope['stage'] == 'MODEL_RESPONSE_OBSERVED']
            assert len(formations) == 2
            for scope in formations:
                assert scope['candidate_output'].startswith('```json')
                assert scope['wire_presentation'] == _fulfillment_wire_value(scope['candidate_output'],
                    scope['owner_source_preconditions'])[1]
            assert feedback['repair_feedback_binding']['response_receipt_id'] == formations[0]['receipt_id']
            assert feedback['repair_feedback_binding']['wire_presentation'] == formations[0]['wire_presentation']
    never = NeverCallAgain()
    if first_failure == 'semantic-jsonb-order':
        # The actual PG JSONB representation may reorder nested objects used
        # during feedback recomputation. Never rewrite the historical strings
        # or next request: those remain bound to their original fingerprints.
        from sqlalchemy import text
        from spg.application import governed_obligations as app
        recompute=app._bind_repair_feedback
        changed_bytes=[]
        def jsonb_recompute(*args,**kwargs):
            original=recompute(*args,**kwargs)
            with postgres_database.unit_of_work() as uow:
                restored=uow.session.execute(text('SELECT CAST(CAST(:value AS jsonb) AS text)'),
                    {'value':original}).scalar_one()
            assert json.loads(restored)==json.loads(original)
            changed_bytes.append(restored!=original)
            return restored
        monkeypatch.setattr(app,'_bind_repair_feedback',jsonb_recompute)
    replay = form_fulfillment_projection(revision, ir, provider=never, database=postgres_database,
        source_revision=baseline.repository_revision, exact_target_paths=('index.html',))
    assert never.calls == 0 and all(b.state != 'UNRESOLVED' for b in replay)
    if first_failure == 'semantic-jsonb-order':
        assert changed_bytes and all(changed_bytes)
    with postgres_database.unit_of_work() as uow:
        restored=RuntimeStore(uow.session).governance_for_subject(fingerprint)
        assert len(restored)==count
        assert [r.scope for r in restored]==[r.scope for r in records]
    if first_failure in ('critic-schema', 'critic-json'):
        from copy import deepcopy
        from sqlalchemy import update
        from spg.infrastructure.persistence.runtime_store import governance_records
        with postgres_database.unit_of_work() as uow:
            record = next(r for r in RuntimeStore(uow.session).governance_for_subject(fingerprint)
                if r.scope['stage'] == 'SEMANTIC_REVIEW_VALIDATED' and r.scope['attempt'] == 1)
            changed = deepcopy(record.scope)
            changed['review_contract_failure']['observed_component_count'] = 999
            uow.session.execute(update(governance_records).where(governance_records.c.id == record.id).values(scope=changed))
            uow.commit()
        refused = form_fulfillment_projection(revision, ir, provider=never, database=postgres_database,
            source_revision=baseline.repository_revision, exact_target_paths=('index.html',))
        assert never.calls == 0 and all(b.state == 'UNRESOLVED' for b in refused)
        assert refused[0].formation_receipt['terminal_reason'] == 'OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'
        with postgres_database.unit_of_work() as uow:
            assert ProductStore(uow.session).current_work_reality_revision(work_id) == revision
            assert len(RuntimeStore(uow.session).governance_for_subject(fingerprint)) == count


def test_calibrated_component_review_persists_replays_and_reaches_independent_guardian(
    postgres_database, tmp_path, monkeypatch, record_property,
):
    from tests.integration import test_c1_contract_continuity as c1
    from tests.test_c3_semantic_contract_calibration import review as component_review
    original_review = c1.DeclaredC1SemanticReview.review
    def calibrated(self, inventory, candidate):
        original = original_review(self, inventory, candidate)
        components = component_review(inventory, candidate).component_results
        return original.model_copy(update={"component_results": components})
    monkeypatch.setattr(c1.DeclaredC1SemanticReview, "review", calibrated)
    admitted = c1._admit_c1(postgres_database, tmp_path, "work")
    _,work_id,revision,ir,_,baseline,pwu=admitted
    provider=NeverCallAgain()
    replay=form_fulfillment_projection(revision,ir,provider=provider,database=postgres_database,
        source_revision=baseline.repository_revision,exact_target_paths=("index.html",))
    assert provider.calls==0
    assert replay[0].formation_receipt["semantic_review"]["component_results"]
    original=pwu.completion_contract.fulfillment_bindings
    assert [b.model_dump(exclude={"formation_receipt"}) for b in replay]==[b.model_dump(exclude={"formation_receipt"}) for b in original]
    assert replay[0].formation_receipt["semantic_review"]==original[0].formation_receipt["semantic_review"]
    assert set(replay[0].formation_receipt["receipt_refs"])==set(original[0].formation_receipt["receipt_refs"])
    assert {k:v for k,v in replay[0].formation_receipt.items() if k!="elapsed_seconds"}=={
        k:v for k,v in original[0].formation_receipt.items() if k!="elapsed_seconds"}
    chain=c1._produce_chain(postgres_database,tmp_path,admitted)
    projection=c1._assess(chain)
    assert projection["gate"]=="PASS",projection
    with postgres_database.unit_of_work() as uow:
        runtime=RuntimeStore(uow.session)
        assert runtime.human_authorizations_for_candidate(chain.candidate.id)==()
        records=runtime.governance_for_subject(replay[0].projection_inventory_fingerprint)
        assert len(records)==6
        validated=next(r for r in records if r.scope["stage"]=="SEMANTIC_REVIEW_VALIDATED")
        assert validated.scope["semantic_review"]["component_results"]==replay[0].formation_receipt["semantic_review"]["component_results"]
    record_property("qualification_kind","controlled PostgreSQL/Git/Guardian, not real model/G0")
    record_property("work",str(work_id));record_property("candidate",str(chain.candidate.id))


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
        inventory = _restore_formation_inventory_view(payload["immutable_inventory"], payload.get('existing_ir_item_table', {}))
        if "untrusted_fulfillment_candidate" in payload:
            from spg.domain.governed_obligation import FulfillmentProjectionCandidate
            plan = decode_review_input(payload)
            output = fixture_review_proof(inventory, plan, declared.review(inventory, plan), payload).model_dump_json()
        else:
            plan = declared.form(inventory, payload["existing_capability_contracts"],
                validation_feedback=payload.get("same_basis_validation_feedback"))
            wire, _ = controlled_wire(inventory, plan, feedback=payload.get("same_basis_validation_feedback"), owner_preconditions=payload.get("owner_source_preconditions"))
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


@pytest.mark.parametrize('tamper', (None, 'feedback', 'response-receipt', 'scope-inventory', 'owner-precondition', 'initial-prerequisite', 'raw-owner-observation', 'selection-input-contract'))
@pytest.mark.parametrize('failure_kind', ('predecode', 'canonical', 'complete-prefix'))
def test_predecode_feedback_recovers_from_postgresql_and_rejects_identity_drift(
    postgres_database, tmp_path, monkeypatch, record_property, tamper, failure_kind,
):
    """New isolated fixture records only; no historical or live model writes."""
    from copy import deepcopy
    import json
    from types import SimpleNamespace
    from sqlalchemy import update
    from spg.application.governed_obligations import FulfillmentFormationReceipts
    from spg.domain.governed_obligation import FulfillmentProjectionCandidate
    from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
    from spg.infrastructure.persistence.interaction_store import InteractionStore
    from spg.infrastructure.persistence.runtime_store import governance_records
    from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
    from tests.integration import test_c1_contract_continuity as c1
    from tests.test_c3_fulfillment_capacity_representation import controlled_wire
    from tests.test_c3_semantic_contract_calibration import review as component_review

    declared = c1.DeclaredC1Fulfillment()
    calls, inventories = [], []
    def generate(**request):
        payload = json.loads(request['input_text'])
        calls.append(payload)
        inventory = _restore_formation_inventory_view(payload['immutable_inventory'], payload.get('existing_ir_item_table', {}))
        inventories.append(inventory)
        if 'untrusted_fulfillment_candidate' in payload:
            plan = decode_review_input(payload)
            result = declared.review(inventory, plan).model_copy(update={
                'component_results': component_review(inventory, plan).component_results})
            output = fixture_review_proof(inventory, plan, result, payload).model_dump_json()
        else:
            plan = declared.form(inventory, payload['existing_capability_contracts'])
            wire, _ = controlled_wire(inventory, plan, feedback=payload.get('same_basis_validation_feedback'), owner_preconditions=payload.get('owner_source_preconditions'))
            if len(calls) == 1:
                if failure_kind == 'canonical':
                    wire['routes'].append(deepcopy(wire['routes'][0]))
                else:
                    wire['routes'][0]['f'] = [i for i,s in enumerate(inventory['sources'])
                                             if s['kind'] in {'IR_CLAUSE','IR_CONSTRAINT'}][:2]
                    assert len(wire['routes'][0]['f']) == 2
                    wire['routes'][0]['t'] = []
            elif payload.get('same_basis_validation_feedback') is not None:
                feedback = json.loads(payload['same_basis_validation_feedback'])
                assert feedback['untrusted_previous_wire']
                assert feedback['repair_feedback_binding']['attempt'] == 1
            output = json.dumps(wire, ensure_ascii=False)
            if failure_kind == 'complete-prefix' and len(calls) == 1:
                output += '}'  # Complete original value remains unadmitted.
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model='controlled-pg-feedback', effective_model='controlled-pg-feedback',
            request_id=f'controlled-pg-feedback-{len(calls)}', usage=ModelUsage(), timing=ModelTiming(), retry_count=0)
    provider = ModelFulfillmentCandidateProvider(lambda: SimpleNamespace(generate=generate, close=lambda: None))
    original_append = FulfillmentFormationReceipts.append
    class AfterDurableFeedback(BaseException):
        pass
    interrupted = False
    def append(self, stage, attempt, **values):
        nonlocal interrupted
        row = original_append(self, stage, attempt, **values)
        if stage == 'CANDIDATE_VALIDATED' and attempt == 1 and not interrupted:
            interrupted = True
            raise AfterDurableFeedback()
        return row
    monkeypatch.setattr(FulfillmentFormationReceipts, 'append', append)
    monkeypatch.setattr(c1, 'DeclaredC1Fulfillment', lambda: provider)
    with pytest.raises(AfterDurableFeedback): c1._admit_c1(postgres_database, tmp_path, 'work')
    inventory = inventories[-1]
    fingerprint = inventory['inventory_fingerprint']
    work_id = UUID(inventory['work_id'])
    with postgres_database.unit_of_work() as uow:
        product = ProductStore(uow.session)
        revision = product.current_work_reality_revision(work_id)
        ir = InteractionStore(uow.session).assessment(revision.source_assessment_id).semantic_ir
        records = RuntimeStore(uow.session).governance_for_subject(fingerprint)
        assert [r.scope['stage'] for r in records] == ['MODEL_REQUEST_PENDING','MODEL_RESPONSE_OBSERVED','CANDIDATE_VALIDATED']
        failed = records[-1]
        original_scope = deepcopy(failed.scope)
        feedback = json.loads(original_scope['validation_feedback'])
        binding = feedback['repair_feedback_binding']
        assert original_scope['owner_repair_context_bound']
        assert feedback['owner_repair_context']['inventory_fingerprint'] == fingerprint
        assert binding['response_receipt_id'] == records[1].scope['receipt_id']
        assert binding['request_receipt_id'] == records[0].scope['receipt_id']
        raw_operands = feedback['owner_repair_context']['original_wire_owner_operands']
        if failure_kind == 'predecode':
            assert any('OBLIGATION_CONTENT_TARGET_UNRESOLVED' in f['failed_predicates']
                for f in raw_operands['violations'])
        if failure_kind == 'complete-prefix':
            assert any('OBLIGATION_CONTENT_TARGET_UNRESOLVED' in f['failed_predicates']
                for f in raw_operands['violations'])
            assert raw_operands['complete_value_observation']['original_wire_sha256'] == binding['wire_output_fingerprint']
            assert 'COMPLETE_WIRE_SYNTAX' in raw_operands['not_evaluable']
        else:
            assert 'ASSURANCE' in raw_operands['not_evaluable']
        assert 'ASSURANCE' in feedback['owner_repair_context']['not_evaluable']
        if tamper:
            scope = deepcopy(original_scope)
            if tamper == 'feedback': scope['validation_feedback'] += ' '
            elif tamper == 'scope-inventory': scope['inventory_fingerprint'] = '0'*64
            elif tamper == 'owner-precondition':
                changed = json.loads(scope['validation_feedback'])
                changed['owner_repair_context']['source_preconditions'][0]['primary_component_required'] = False
                scope['validation_feedback'] = json.dumps(changed)
            elif tamper == 'raw-owner-observation':
                changed = json.loads(scope['validation_feedback'])
                changed['owner_repair_context']['original_wire_owner_operands']['not_evaluable'].append('INVENTED')
                scope['validation_feedback'] = json.dumps(changed)
            elif tamper == 'initial-prerequisite':
                for original in records[:2]:
                    changed=deepcopy(original.scope)
                    changed['owner_source_preconditions']['sources'][0]['source']=999
                    uow.session.execute(update(governance_records).where(governance_records.c.id == original.id).values(scope=changed))
            elif tamper == 'selection-input-contract':
                for original in records[:2]:
                    changed=deepcopy(original.scope)
                    changed['owner_source_preconditions'].pop('semantic_selection_input_contract')
                    uow.session.execute(update(governance_records).where(governance_records.c.id == original.id).values(scope=changed))
            else:
                changed = json.loads(scope['validation_feedback'])
                changed['repair_feedback_binding']['response_receipt_id'] = str(work_id)
                scope['validation_feedback'] = json.dumps(changed)
            # Deliberate corruption of this freshly created isolated fixture.
            uow.session.execute(update(governance_records).where(governance_records.c.id == failed.id).values(scope=scope))
            uow.commit()
    assert len(calls) == 1
    result = form_fulfillment_projection(revision, ir, provider=provider, database=postgres_database,
        source_revision=inventory['source_revision'], exact_target_paths=inventory['exact_target_paths'])
    receipt = result[0].formation_receipt
    if tamper:
        assert len(calls) == 1 and all(b.state == 'UNRESOLVED' for b in result)
        assert receipt['terminal_reason'] == 'OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT'
    else:
        assert len(calls) == 3 and all(b.state != 'UNRESOLVED' for b in result)
        assert calls[1]['same_basis_validation_feedback'] == original_scope['validation_feedback']
        start = next(r for r in receipt['candidate_attempts'] if r['stage']=='MODEL_REQUEST_PENDING' and r['attempt']==2)
        assert start['feedback_receipt_id'] == original_scope['receipt_id']
    before_count = len(calls)
    form_fulfillment_projection(revision, ir, provider=provider, database=postgres_database,
        source_revision=inventory['source_revision'], exact_target_paths=inventory['exact_target_paths'])
    assert len(calls) == before_count
    with postgres_database.unit_of_work() as uow:
        runtime = RuntimeStore(uow.session)
        assert ProductStore(uow.session).current_work_reality_revision(work_id) == revision
        rows = runtime.governance_for_subject(fingerprint)
        assert all(runtime.human_authorization(row.id) is None for row in rows)
    record_property('qualification_kind','isolated PostgreSQL predecode feedback recovery, not live model/G0')
    record_property('tamper',str(tamper))
    record_property('work',str(work_id))
    record_property('inventory_fingerprint',fingerprint)
    record_property('feedback_receipt_id',original_scope['receipt_id'])
    record_property('logical_stub_calls',len(calls))


@pytest.mark.parametrize("tamper", [False, True])
def test_expanded_candidate_capacity_is_durable_without_repair_authority(postgres_database, tmp_path, monkeypatch, tamper):
    """Real isolated persistence of a rejected expanded controlled proposal."""
    from copy import deepcopy
    import json
    from types import SimpleNamespace
    from sqlalchemy import update
    from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
    from spg.infrastructure.persistence.interaction_store import InteractionStore
    from spg.infrastructure.persistence.runtime_store import governance_records
    from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
    from spg.providers.verification_receipts import MAX_CANDIDATE_BYTES
    from tests.integration import test_c1_contract_continuity as c1
    from tests.test_c3_fulfillment_capacity_representation import controlled_wire
    declared=c1.DeclaredC1Fulfillment();calls=[];inventories=[]
    def generate(**request):
        payload=json.loads(request["input_text"]);calls.append(payload)
        assert "untrusted_fulfillment_candidate" not in payload
        inventory=_restore_formation_inventory_view(payload["immutable_inventory"],payload.get("existing_ir_item_table",{}));inventories.append(inventory)
        plan=declared.form(inventory,payload["existing_capability_contracts"])
        wire,_=controlled_wire(inventory,plan,owner_preconditions=payload.get("owner_source_preconditions"))
        count=64
        base=plan.model_copy(update={"routes":tuple(plan.routes[i%len(plan.routes)].model_copy(update={"rationale":""}) for i in range(count))})
        size=(MAX_CANDIDATE_BYTES+128-len(base.model_dump_json().encode()))//count+1
        assert 0<size<=1000
        wire["routes"]=[{**deepcopy(wire["routes"][i%len(wire["routes"])]),"r":"x"*size} for i in range(count)]
        output=json.dumps(wire,ensure_ascii=False)
        assert len(output.encode())<=MAX_CANDIDATE_BYTES
        return StructuredModelResult(output_text=output,provider=ModelProvider.DEEPSEEK,
            requested_model="controlled-pg-expanded-capacity",effective_model="controlled-pg-expanded-capacity",
            request_id="controlled-pg-expanded-capacity-1",usage=ModelUsage(),timing=ModelTiming(),retry_count=0)
    provider=ModelFulfillmentCandidateProvider(lambda:SimpleNamespace(generate=generate,close=lambda:None))
    monkeypatch.setattr(c1,"DeclaredC1Fulfillment",lambda:provider)
    with pytest.raises(ValueError,match="OBLIGATION_COMPONENT_INVENTORY_INCOMPLETE"):
        c1._admit_c1(postgres_database,tmp_path,"work")
    inventory=inventories[-1];fingerprint=inventory["inventory_fingerprint"];work_id=UUID(inventory["work_id"])
    with postgres_database.unit_of_work() as uow:
        revision=ProductStore(uow.session).current_work_reality_revision(work_id)
        ir=InteractionStore(uow.session).assessment(revision.source_assessment_id).semantic_ir
        records=RuntimeStore(uow.session).governance_for_subject(fingerprint)
        assert [r.scope["stage"] for r in records]==["MODEL_REQUEST_PENDING","MODEL_RESPONSE_OBSERVED","CANDIDATE_VALIDATED"]
        failed=records[-1];scope=deepcopy(failed.scope)
        assert scope["failed_predicate"]=="OBLIGATION_FORMATION_EXPANDED_RECEIPT_LIMIT"
        assert scope["terminal_reason"]=="OBLIGATION_FORMATION_RECEIPT_LIMIT"
        assert scope.get("candidate") is None and not scope["validation_passed"]
        assert scope["capacity_observation"]["original_row_bytes"]>131072
        assert records[1].scope["candidate_output"] and "validation_feedback" not in scope
        if tamper:
            scope["capacity_observation"]["original_row_sha256"]="invalid"
            uow.session.execute(update(governance_records).where(governance_records.c.id==failed.id).values(scope=scope));uow.commit()
    before=deepcopy(scope)
    for _ in range(2):
        result=form_fulfillment_projection(revision,ir,provider=provider,database=postgres_database,
            source_revision=inventory["source_revision"],exact_target_paths=inventory["exact_target_paths"])
        assert all(b.state=="UNRESOLVED" for b in result) and len(calls)==1
        assert result[0].formation_receipt["terminal_reason"]==("OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT" if tamper else "OBLIGATION_FORMATION_RECEIPT_LIMIT")
    with postgres_database.unit_of_work() as uow:
        rows=RuntimeStore(uow.session).governance_for_subject(fingerprint)
        assert len(rows)==3 and rows[-1].scope==before
        assert ProductStore(uow.session).current_work_reality_revision(work_id)==revision
        assert all(RuntimeStore(uow.session).human_authorization(r.id) is None for r in rows)


@pytest.mark.parametrize("roles", [
    ("COUNT_PLAN_PROPOSAL", "INDEPENDENT_COUNT_PLAN_REVIEW"),
    ("SCOPED_PLAN_PROPOSAL", "INDEPENDENT_SCOPED_PLAN_REVIEW"),
])
def test_count_plan_review_role_is_durable_in_existing_native_receipts(postgres_database, tmp_path, roles):
    """Receipt persistence only; does not claim a counted Fact or Work is accepted."""
    from types import SimpleNamespace
    from uuid import uuid4
    from spg.application.runtime import RuntimeService
    from spg.providers.verification_receipts import VerificationCandidateReceipts
    from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
    from tests.integration import test_c1_contract_continuity as c1
    from tests.test_c3_verification_receipts import response
    _,work_id,revision,ir,repository,baseline,pwu=c1._admit_c1(postgres_database,tmp_path,'work')
    attempt=RuntimeService(postgres_database).create_initial_attempt(pwu.id)
    request=SimpleNamespace(verification_identity=uuid4(),snapshot_id=uuid4(),source_baseline_id=baseline.id,
        proposed_commit_identity=baseline.repository_revision,tree_identity='b'*40,
        decision_context_fingerprint='a'*64,semantic_fact_obligations=pwu.completion_contract.semantic_fact_obligations,
        protected_context_obligations=())
    args=dict(database=postgres_database,work_id=work_id,work_revision_id=revision.id,pwu_id=pwu.id,attempt_id=attempt.id)
    recorder=VerificationCandidateReceipts(request,**args)
    for role in roles:
        number=recorder.begin('controlled-count-role')
        recorder.observed('controlled-count-role',number,response('{"controlled_receipt_only":true}'))
        recorder.validated('controlled-count-role',number,checks=[{'controlled_receipt_only':True}],
            terminal=number==2,plan_review_role=role)
    with postgres_database.unit_of_work() as uow:
        before=NativeExecutionStore(uow.session).evidence_for_attempt(attempt.id)
    restored=VerificationCandidateReceipts(request,**args)
    terminal=restored.completed('controlled-count-role')
    assert terminal['plan_review_role']==roles[1]
    assert terminal['attempt']==2 and terminal['budget_limit']==2 and terminal['candidate_is_authority'] is False
    assert terminal['work_id']==str(work_id) and terminal['attempt_id']==str(attempt.id)
    with pytest.raises(ValueError,match='ALREADY_TERMINAL'):
        restored.begin('controlled-count-role')
    with postgres_database.unit_of_work() as uow:
        after=NativeExecutionStore(uow.session).evidence_for_attempt(attempt.id)
    assert before==after and len(before)==6
