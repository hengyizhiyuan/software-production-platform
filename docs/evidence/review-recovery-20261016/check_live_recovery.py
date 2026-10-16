from pathlib import Path
import json,sys
from types import SimpleNamespace
from dataclasses import asdict
from spg.config import Settings
from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
from tests.test_c3_reviewer_contract_feedback import run_case
out=Path('/tmp/watt-review-live-20261016');out.mkdir(exist_ok=True)
rev,ir,inv,provider,calls,execute=run_case(same_candidate=True,empty_operands=True)
controlled=provider.runtime_factory
settings=Settings(_env_file='.env',wic_provider_adapter='deepseek',wic_provider_model='deepseek-flash',
 wic_provider_reasoning_effort='none',collaboration_provider_timeout_seconds=120,collaboration_provider_max_output_tokens=16384)
real=ModelFulfillmentCandidateProvider.from_settings(settings)
real_calls=[]
def factory():
 if len(calls)<2:return controlled()
 runtime=real.runtime_factory()
 def generate(**request):
  assert len(real_calls)==0,'extra real call forbidden'
  real_calls.append({'status':'REQUESTED'})
  response=runtime.generate(**request)
  real_calls[0]={'request_id':response.request_id,'provider':response.provider.value,'model':response.effective_model,'usage':asdict(response.usage),'output_sha256':__import__('hashlib').sha256(response.output_text.encode()).hexdigest()}
  return response
 return SimpleNamespace(generate=generate,close=runtime.close)
provider.runtime_factory=factory
try:
 bindings=execute();receipt=bindings[0].formation_receipt
 rows=provider._fulfillment_receipts
 result={'scenario':'Declared non-game admitted fixture, controlled Formation and initial malformed Review; ONE real independent recovery Review',
  'source_files':{p:__import__('hashlib').sha256(Path(p).read_bytes()).hexdigest() for p in ['src/spg/application/governed_obligations.py','src/spg/providers/fulfillment_candidate.py']},'production_mutations':False,'real_calls':real_calls,'formation_calls':sum(r['stage']=='MODEL_REQUEST_PENDING' for r in rows),
  'review_calls':sum(r['stage'] in {'SEMANTIC_REVIEW_PENDING','SEMANTIC_REVIEW_REPAIR_PENDING'} for r in rows),
  'terminal_reason':receipt.get('terminal_reason'),'admitted_derived_plan':all(b.state!='UNRESOLVED' for b in bindings),
  'repair':[{k:v for k,v in r.items() if k in ['stage','validation_passed','failed_predicate','receipt_id']} for r in rows if r['stage'].startswith('SEMANTIC_REVIEW_REPAIR_')]}
 (out/'receipts.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps(result,ensure_ascii=False))
except Exception as e:
 (out/'failure.json').write_text(json.dumps({'type':type(e).__name__,'real_calls':real_calls}));print(type(e).__name__);raise
