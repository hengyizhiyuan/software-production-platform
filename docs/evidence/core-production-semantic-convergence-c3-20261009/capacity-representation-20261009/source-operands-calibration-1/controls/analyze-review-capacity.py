from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
import json,httpx2
from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
from spg.domain.governed_obligation import FulfillmentProjectionCandidate
from spg.domain.model_runtime import ModelProfile,ModelProvider,ModelPurpose
from spg.infrastructure.model_runtime import ResponsesModelAdapter
p=Path('/retained'); inv=json.loads((p/'immutable-inventory.json').read_text()); caps=json.loads((p/'capability-contracts.json').read_text())
candidate=FulfillmentProjectionCandidate.model_validate(json.loads((p/'formation-1-located-candidate.json').read_text()))
live=json.loads(Path('/live-result.json').read_text()); call=next(c for c in live['calls'] if c['operation']=='semantic_review')
captured={}
class Captured(BaseException):pass
def generate(**kwargs):captured.update(kwargs);raise Captured()
provider=ModelFulfillmentCandidateProvider(lambda:SimpleNamespace(generate=generate,close=lambda:None))
try:provider.review(inv,candidate,capabilities=caps)
except Captured:pass
profile=ModelProfile(purpose=ModelPurpose.STEERING_SEMANTIC,provider=ModelProvider.DEEPSEEK,model='deepseek-flash',reasoning_effort='low',timeout_seconds=120,max_output_tokens=16384)
adapter=object.__new__(ResponsesModelAdapter)
payload=adapter._payload(profile=profile,instructions=captured['instructions'],input_text=captured['input_text'],output_schema=captured['output_schema'])
entity=httpx2.Request('POST','https://api.deepseek.com/responses',json=payload).content
identity={'bytes':len(entity),'sha256':sha256(entity).hexdigest()};assert identity==call['request_entity']
data=json.loads(captured['input_text'])
def size(v):return len(json.dumps(v,ensure_ascii=False,separators=(',',':')).encode())
report={'schema':'c3-independent-review-capacity-readonly-v1','model_calls':0,'owner_writes':0,'candidate_modified':False,
 'request_identity_verified':True,'request_entity':identity,'request_id':call['failure_observation']['provider_failure']['request_id'],
 'inventory_fingerprint':inv['inventory_fingerprint'],'candidate_fingerprint':data['candidate_fingerprint'],
 'components_fingerprint':data['components_fingerprint'],'sources':len(inv['sources']),'routes':len(candidate.routes),
 'instructions_utf8_bytes':len(captured['instructions'].encode()),'input_text_utf8_bytes':len(captured['input_text'].encode()),
 'schema_utf8_bytes':size(payload['text']['format']['schema']),
 'standalone_compact_input_section_bytes':{k:size(v) for k,v in data.items()},
 'section_bytes_not_additive_to_encoded_http_entity':True,'actual_provider_usage':call['usage'],
 'provider_failure':call['failure_observation']['provider_failure'],'actual_delta_count':call['provider_output_identity']['delta_event_count'],
 'terminal_output_availability':call['provider_output_identity']['terminal_output'].get('availability'),
 'full_review_results':'NOT_GENERATED','json_output_overflow_cause':'NOT_SUPPORTED; no visible output',
 'reasoning_process_or_hidden_tokens_content':'NOT_RECORDED',
 'root_cause':'Provider low reasoning consumed entire existing output budget before an independent review result',
 'reasoning_complexity_explanation':'UNKNOWN','would_input_deduplication_converge':'UNKNOWN',
 'automatic_retry':'NOT_AUTHORIZED_BY_FAILURE_CONTRACT; nonconverged budget stop','semantic_criteria_changed':False}
Path('/diagnostic/review-capacity-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'request_identity_verified':True,'input_section_bytes':report['standalone_compact_input_section_bytes'],'actual_provider_usage':call['usage'],'sources':len(inv['sources']),'routes':len(candidate.routes)}))
