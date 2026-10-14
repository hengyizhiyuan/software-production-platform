"""Immutable ordinary34 snapshot; full existing bounded Formation, no Work writes."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import time
from types import SimpleNamespace

from spg.application import governed_obligations as owner
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
from spg.domain.model_runtime import (ModelProfile, ModelProvider, ModelPurpose,
    ModelProviderRegistry, PurposeProfileRouter, WattModelRuntime,
    StructuredModelResult, ModelUsage, ModelTiming)
from spg.infrastructure.model_runtime import DeepSeekResponsesModelAdapter
from spg.providers import fulfillment_candidate as wire

parser=argparse.ArgumentParser()
parser.add_argument('--live',action='store_true')
parser.add_argument('--retained-first',action='store_true')
args=parser.parse_args()
private=Path('/private')
evidence=Path('/evidence')
mode='retained-first' if args.retained_first else 'live' if args.live else 'preflight'
out=private/mode
out.mkdir(exist_ok=False)
def digest(path):return sha256(path.read_bytes()).hexdigest()
inputs={p.name:digest(p) for p in Path('/inventory').glob('*.json')}
inputs['historical-owner-receipts']=digest(Path('/historical-owner-receipts.json'))
inventory=json.loads(Path('/inventory/immutable-inventory.json').read_text())
assert inventory['inventory_fingerprint']=='b023bae819f456da05abe983f48da4f2157da60df412de909f9f834991bcef29'
data=json.loads(Path('/inventory/basis.json').read_text())['datasets']
revision=WorkRealityRevision.model_validate(next(row for row in data['work_reality_revisions']['rows']
    if row['id']==inventory['work_reality_revision_id']))
ir=GovernedSemanticIR.model_validate(next(row for row in data['interaction_assessments']['rows']
    if row['id']==str(revision.source_assessment_id))['semantic_ir'])
kwargs={'source_revision':inventory['source_revision'],'exact_target_paths':inventory['exact_target_paths']}
assert owner.fulfillment_inventory(revision,ir,**kwargs)==inventory
immutable=(revision.model_dump_json(),ir.model_dump_json())
historical=json.loads(Path('/historical-owner-receipts.json').read_text())
if isinstance(historical,dict):
    raise ValueError('EXPECTED_HISTORICAL_RECEIPT_ARRAY')
historical=owner.FulfillmentFormationReceipts(revision,inventory,memory=historical).records()
first_raw=next(r['candidate_output'] for r in historical if r['stage']=='MODEL_RESPONSE_OBSERVED' and r['attempt']==1)
assert sha256(first_raw.encode()).hexdigest()=='893f167cab558759ab2eb2a2a3664e2d57650e71a0077b2fcf6e5553928ebc4e'
calls=[]
class PreflightComplete(BaseException):pass
def save(name,value):
    target=out/name
    temporary=target.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str))
    temporary.replace(target)
def runtime():
    registry=ModelProviderRegistry()
    registry.register(DeepSeekResponsesModelAdapter(api_key=lambda:os.environ['SPG_DEEPSEEK_API_KEY'],
        base_url=os.environ.get('SPG_DEEPSEEK_BASE_URL','https://api.deepseek.com')))
    profile=ModelProfile(purpose=ModelPurpose.STEERING_SEMANTIC,provider=ModelProvider.DEEPSEEK,
        model='deepseek-flash',reasoning_effort='none',max_output_tokens=16384,timeout_seconds=120)
    actual=WattModelRuntime(registry,PurposeProfileRouter({ModelPurpose.STEERING_SEMANTIC:profile})) if args.live else None
    def generate(**request):
        payload=json.loads(request['input_text'])
        role='review' if 'untrusted_fulfillment_candidate' in payload else 'formation'
        if len(calls)>=4 or (role=='formation' and sum(c['role']==role for c in calls)>=2):
            raise RuntimeError('QUALIFICATION_LOGICAL_CALL_LIMIT')
        index=len(calls)+1
        save('request-'+str(index)+'.json',request)
        if not args.live and calls:
            feedback=json.loads(payload['same_basis_validation_feedback'])
            decisions=feedback['owner_repair_context']['decision_revision_requests']
            assert decisions['contract']==wire._DECISION_REVISION_CONTRACT and decisions['requests']
            assert payload['owner_source_preconditions']['candidate_construction_state']['repair_targets']
            raise PreflightComplete()
        controlled=not args.live or (args.retained_first and not calls)
        entry={'role':role,'logical_call':index,'retained_response_control':controlled,
            'started_at_utc':datetime.now(timezone.utc).isoformat()}
        calls.append(entry)
        save('calls.json',calls)
        started=time.monotonic()
        try:
            if actual and not controlled:
                result=actual.generate(**request)
            else:
                result=StructuredModelResult(output_text=first_raw,provider=ModelProvider.DEEPSEEK,
                    requested_model='retained-response-no-network',effective_model='retained-response-no-network',
                    request_id='controlled-preflight',usage=ModelUsage(unknown=True),timing=ModelTiming())
            entry.update(completed=True,elapsed_seconds=time.monotonic()-started,
                request_id=result.request_id,usage=asdict(result.usage),timing=asdict(result.timing),
                transport_retry_count=result.retry_count,output_evidence=result.output_evidence,
                response_sha256=sha256(result.output_text.encode()).hexdigest())
            return result
        except Exception as error:
            entry.update(completed=False,error_type=type(error).__name__,elapsed_seconds=time.monotonic()-started)
            raise
        finally:save('calls.json',calls)
    return SimpleNamespace(generate=generate,close=actual.close if actual else lambda:None)

p=wire.ModelFulfillmentCandidateProvider(runtime,candidate_construction=True,
    candidate_construction_contract='owner-local-interpretation-role-construction-v4',
    raw_role_repair=True,construction_consumer_instructions=True,unparsed_claim_repair=True,role_convergence=True)
original_append=owner.FulfillmentFormationReceipts.append
def checkpoint(self,*a,**kw):
    try:return original_append(self,*a,**kw)
    finally:save('owner-receipts.json',self.memory)
owner.FulfillmentFormationReceipts.append=checkpoint
started=time.monotonic()
terminal=None
error_type=None
replay_no_calls=None
try:
    result=owner.form_fulfillment_projection(revision,ir,provider=p,**kwargs)
    save('bindings.json',[b.model_dump(mode='json') for b in result])
    terminal=result[0].formation_receipt['terminal_reason']
    if args.live:
        before=(len(calls),json.dumps(p._fulfillment_receipts,sort_keys=True))
        owner.form_fulfillment_projection(revision,ir,provider=p,**kwargs)
        replay_no_calls=before==(len(calls),json.dumps(p._fulfillment_receipts,sort_keys=True))
        assert replay_no_calls
except PreflightComplete:
    terminal='SECOND_REQUEST_READY_NO_NETWORK'
except Exception as error:
    error_type=type(error).__name__
    codes=re.findall(r'OBLIGATION_[A-Z_]+',str(error))
    terminal=codes[0] if codes else 'UNKNOWN_EXCEPTION'
assert immutable==(revision.model_dump_json(),ir.model_dump_json())
assert inputs=={**{p.name:digest(p) for p in Path('/inventory').glob('*.json')},
    'historical-owner-receipts':digest(Path('/historical-owner-receipts.json'))}
rows=owner.FulfillmentFormationReceipts(revision,inventory,memory=p._fulfillment_receipts).records()
save('materialized-owner-receipts.json',rows)
summary={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'mode':mode,
    'revision':os.environ['SPG_RUNTIME_REVISION'],'inventory_fingerprint':inventory['inventory_fingerprint'],
    'source_count':len(inventory['sources']),'input_sha256':inputs,'terminal_reason':terminal,
    'error_type':error_type,'calls':calls if args.live else [],'elapsed_seconds':time.monotonic()-started,
    'actual_calls':sum(not c['retained_response_control'] for c in calls),'new_work_created':False,'historical_writes':False,
    'terminal_replay_without_calls':replay_no_calls,
    'stages':[{'stage':r['stage'],'attempt':r['attempt'],'receipt_id':r['receipt_id'],
        **{k:r[k] for k in ('validation_passed','failure_code','terminal_reason','terminal') if k in r}} for r in rows],
    'physical_receipt_max_bytes':max([len(json.dumps(r,ensure_ascii=False).encode()) for r in p._fulfillment_receipts],default=0),
    'owner_state_only':True,'no_assurance_or_human_authority_granted':True,
    'currency_cost':'UNKNOWN'}
(evidence/(mode+'-result.json')).write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k not in ('input_sha256','calls','stages')},indent=2))
if not args.live:assert terminal=='SECOND_REQUEST_READY_NO_NETWORK',terminal
