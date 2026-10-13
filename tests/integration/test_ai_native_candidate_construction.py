"""Durable local candidate edits, resumed through the existing Work Owner."""
from copy import deepcopy
import json
from types import SimpleNamespace
from uuid import UUID

import pytest

from spg.application import governed_obligations as app
from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
from spg.infrastructure.persistence.interaction_store import InteractionStore
from spg.infrastructure.persistence.product_store import ProductStore
from spg.providers.fulfillment_candidate import (
    ModelFulfillmentCandidateProvider, _restore_formation_inventory_view,
)
from tests.integration import test_c1_contract_continuity as c1
from tests.integration.test_c1_contract_continuity import c1_schema
from tests.test_c3_fulfillment_capacity_representation import controlled_wire, decode_review_input
from tests.test_c3_semantic_contract_calibration import review
from tests.test_c3_source_consumption_proof import fixture_review_proof

pytestmark = pytest.mark.postgresql


@pytest.mark.parametrize('construction_contract,raw_role_repair,consumer_instructions,unparsed_claim,role_convergence',(
    ('owner-local-wire-candidate-edits-v1',False,False,False,False),('owner-local-semantic-candidate-edits-v2',False,False,False,False),
    ('owner-local-role-reference-candidates-v3',False,False,False,False),('owner-local-role-reference-candidates-v3',True,False,False,False),
    ('owner-local-interpretation-role-construction-v4',False,False,False,False),('owner-local-interpretation-role-construction-v4',True,False,False,False),
    ('owner-local-role-reference-candidates-v3',True,True,False,False),('owner-local-interpretation-role-construction-v4',True,True,False,False),
    ('owner-local-interpretation-role-construction-v4',True,True,True,False),('owner-local-interpretation-role-construction-v4',True,True,False,True)))
def test_observed_edit_resumes_after_postgresql_checkpoint_without_regeneration(postgres_database, tmp_path, monkeypatch,construction_contract,raw_role_repair,consumer_instructions,unparsed_claim,role_convergence):
    declared = c1.DeclaredC1Fulfillment()
    calls = []
    inventories = []

    def generate(**request):
        payload = json.loads(request["input_text"])
        calls.append(payload)
        if "untrusted_fulfillment_candidate" in payload:
            candidate = decode_review_input(payload)
            inventory = inventories[-1]
            output = fixture_review_proof(inventory, candidate, review(inventory,candidate), payload).model_dump_json()
        else:
            inventory = _restore_formation_inventory_view(payload["immutable_inventory"],payload.get("existing_ir_item_table",{}))
            inventories.append(inventory)
            plan = declared.form(inventory,payload["existing_capability_contracts"])
            wire,_ = controlled_wire(inventory,plan,feedback=payload["same_basis_validation_feedback"],
                owner_preconditions=payload["owner_source_preconditions"])
            def role(r):
                return {'source_ref':inventory['sources'][r['s']]['source_ref'],
                    'capability':payload['existing_capability_contracts'][r['c']]['capability'],
                    'component_quote':r['q'],
                    'current_fact_dependencies':[inventory['sources'][i]['source_ref'] for i in r['f']],
                    'target_paths':[inventory['exact_target_paths'][i] for i in r['t']],
                    'provenance_support_refs':[inventory['sources'][i]['source_ref'] for i in r['u']],
                    'rationale':r['r']}
            if payload["same_basis_validation_feedback"] is None:
                assert inventory["sources"][wire["routes"][0]["s"]]["kind"] == "FACT"
                original_dependencies=wire['routes'][0]['f']
                wire["routes"][0]["f"] = [len(inventory["sources"])]
                output = json.dumps({"routes":[{k:v for k,v in row.items() if k not in {"a","z"}}
                    for row in wire["routes"]]})
                if construction_contract=='owner-local-role-reference-candidates-v3':
                    wire['routes'][0]['f']=[]
                    proposal={'routes':[role(r) for r in wire['routes']]}
                    proposal['routes'][0]['current_fact_dependencies']=[next(
                        s['source_ref'] for s in inventory['sources'] if s['kind']!='FACT')]
                    if raw_role_repair:proposal['routes'][0]['current_fact_dependencies']=[0,1]
                    output=json.dumps(proposal)
                if construction_contract=='owner-local-interpretation-role-construction-v4':
                    output=json.dumps({'components':[{'source_ref':s['source_ref'],'component_quote':None,
                        'interpretation':'Unreviewed complete contribution','unknowns':['Need role binding'],
                        'alternatives':[]} for s in inventory['sources']]})
                    if unparsed_claim:output=output[:-1]
                    if role_convergence:
                        wire['routes'][0]['f']=original_dependencies
                        duplicate=deepcopy(wire['routes'][0])
                        duplicate.update(c=next(i for i,c in enumerate(payload['existing_capability_contracts']) if c['capability']=='UNRESOLVED'),f=[],t=[],u=[])
                        wire['routes'].append(duplicate)
                        output=json.dumps({'routes':[role(r) for r in wire['routes']]})
            else:
                basis = payload["owner_source_preconditions"]["candidate_construction_state"]["repair_basis"]
                replacement=wire['routes'][0]
                if basis.get('representation')=='UNLOCATED_SEMANTIC_PROPOSAL':
                    replacement={k:v for k,v in replacement.items() if k not in {'a','z'}}
                output = json.dumps({"v":1,"h":wire["h"],"d":wire["d"],"basis":basis["raw_sha256"],
                    "replace":[{"index":0,"route":replacement}],"remove":[],"append":[]})
                if construction_contract=='owner-local-role-reference-candidates-v3':
                    output=json.dumps({'basis':basis['raw_sha256'],'replace':[{'index':0,'route':role(wire['routes'][0])}],
                        'remove':[],'append':[]})
                if construction_contract=='owner-local-interpretation-role-construction-v4':
                    output=(json.dumps({'basis':basis['raw_sha256'],'replace':[],
                        'remove':[{'index':len(basis['original_wire']['routes'])-1}],'append':[]}) if role_convergence else json.dumps({'routes':[role(r) for r in wire['routes']]}))
        return StructuredModelResult(output_text=output,provider=ModelProvider.DEEPSEEK,
            requested_model="controlled-pg-edit",effective_model="controlled-pg-edit",
            request_id=f"pg-edit-{len(calls)}",usage=ModelUsage(unknown=True),timing=ModelTiming(),retry_count=0)

    provider = ModelFulfillmentCandidateProvider(lambda:SimpleNamespace(generate=generate,close=lambda:None),
        candidate_construction=True,candidate_construction_contract=construction_contract,raw_role_repair=raw_role_repair,
        construction_consumer_instructions=consumer_instructions,unparsed_claim_repair=unparsed_claim,role_convergence=role_convergence)
    monkeypatch.setattr(c1,"DeclaredC1Fulfillment",lambda:provider)
    class DurableEditObserved(BaseException):
        pass
    original_append = app.FulfillmentFormationReceipts.append
    def checkpoint(self, stage, attempt, **values):
        row = original_append(self,stage,attempt,**values)
        if stage == "MODEL_RESPONSE_OBSERVED" and attempt == 2:
            raise DurableEditObserved()
        return row
    monkeypatch.setattr(app.FulfillmentFormationReceipts,"append",checkpoint)
    with pytest.raises(DurableEditObserved):
        c1._admit_c1(postgres_database,tmp_path,"work")
    assert len(calls) == 2
    monkeypatch.setattr(app.FulfillmentFormationReceipts,"append",original_append)
    inventory = inventories[-1]
    provider.supports_raw_role_repair=False
    provider.supports_construction_consumer_instructions=False
    provider.supports_unparsed_claim_repair=False
    provider.supports_role_convergence=False
    with postgres_database.unit_of_work() as uow:
        revision = ProductStore(uow.session).current_work_reality_revision(UUID(inventory["work_id"]))
        ir = InteractionStore(uow.session).assessment(revision.source_assessment_id).semantic_ir
    resumed = app.form_fulfillment_projection(revision,ir,provider=provider,database=postgres_database,
        source_revision=inventory["source_revision"],exact_target_paths=inventory["exact_target_paths"])
    assert all(b.state != "UNRESOLVED" for b in resumed), resumed[0].formation_receipt["terminal_reason"]
    assert len(calls) == 3  # only the remaining independent Review
    original = deepcopy(resumed[0].formation_receipt["candidate_attempts"])
    replayed = app.form_fulfillment_projection(revision,ir,provider=provider,database=postgres_database,
        source_revision=inventory["source_revision"],exact_target_paths=inventory["exact_target_paths"])
    assert all(b.state != "UNRESOLVED" for b in replayed)
    assert replayed[0].formation_receipt["candidate_attempts"] == original
    assert len(calls) == 3
