from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
import json,httpx2
from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider,_decode_fulfillment_candidate_wire
from spg.domain.governed_obligation import FulfillmentProjectionCandidate,fulfillment_candidate_fingerprint,fulfillment_components_fingerprint
from spg.domain.model_runtime import ModelProfile,ModelProvider,ModelPurpose
from spg.infrastructure.model_runtime import ResponsesModelAdapter
p=Path('/retained');inv=json.loads((p/'immutable-inventory.json').read_text());caps=json.loads((p/'capability-contracts.json').read_text())
candidate=FulfillmentProjectionCandidate.model_validate(json.loads((p/'formation-1-located-candidate.json').read_text()))
captured={}
class Captured(BaseException):pass
def generate(**kwargs):captured.update(kwargs);raise Captured()
provider=ModelFulfillmentCandidateProvider(lambda:SimpleNamespace(generate=generate,close=lambda:None))
try:provider.review(inv,candidate,capabilities=caps)
except Captured:pass
data=json.loads(captured['input_text']);restored=_decode_fulfillment_candidate_wire(json.dumps(data['untrusted_fulfillment_candidate']),inv,caps)
assert restored==candidate
profile=ModelProfile(purpose=ModelPurpose.STEERING_SEMANTIC,provider=ModelProvider.DEEPSEEK,model='deepseek-flash',reasoning_effort='low',timeout_seconds=120,max_output_tokens=16384)
payload=object.__new__(ResponsesModelAdapter)._payload(profile=profile,instructions=captured['instructions'],input_text=captured['input_text'],output_schema=captured['output_schema'])
entity=httpx2.Request('POST','https://api.deepseek.com/responses',json=payload).content
def size(value):return len(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode())
old=json.loads(Path('/original-analysis.json').read_text())
report={'schema':'c3-independent-review-wire-economy-v1','model_calls':0,'candidate_modified':False,'owner_writes':0,
 'inventory_fingerprint':inv['inventory_fingerprint'],'candidate_fingerprint':fulfillment_candidate_fingerprint(candidate),'components_fingerprint':fulfillment_components_fingerprint(candidate),
 'sources':len(inv['sources']),'routes':len(candidate.routes),'exact_roundtrip':True,'wire_version':data['candidate_representation'],
 'original_request_entity':old['request_entity'],'counterfactual_request_entity':{'bytes':len(entity),'sha256':sha256(entity).hexdigest()},
 'original_standalone_section_bytes':old['standalone_compact_input_section_bytes'],
 'compact_standalone_section_bytes':{k:size(v) for k,v in data.items()},
 'schema_utf8_bytes':size(payload['text']['format']['schema']),'output_schema_unchanged':size(payload['text']['format']['schema'])==old['schema_utf8_bytes'],
 'current_input_text_utf8_bytes':len(captured['input_text'].encode()),'original_input_text_utf8_bytes':old['input_text_utf8_bytes'],
 'actual_compact_provider_usage':'UNKNOWN; read-only comparison, not a model call',
 'reasoning_profile':'low','max_output_tokens':16384,'convergence':'UNPROVEN_BY_BYTE_REDUCTION','not_actual_provider_or_qualification_request':True}
Path('/diagnostic/review-wire-economy.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'sources':report['sources'],'routes':report['routes'],'roundtrip':True,'original_request_bytes':old['request_entity']['bytes'],'compact_counterfactual_request_bytes':len(entity),'compact_candidate_bytes':size(data['untrusted_fulfillment_candidate'])}))
