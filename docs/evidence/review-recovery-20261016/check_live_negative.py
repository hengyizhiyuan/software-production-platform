import json
from pathlib import Path
from spg.config import Settings
from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
from spg.application import governed_obligations as a
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case
rev,ir,inv,plan=controlled_capacity_case()
route=plan.routes[0].model_copy(update={'capability':'RETAIN_CONTEXT','target_paths':()})
wrong=plan.model_copy(update={'routes':(route,*plan.routes[1:])})
caps=a.fulfillment_capability_contracts()
owner=a._owner_source_preconditions(rev,ir,inv,caps,review_input_contract='existing-admission-source-comparison-input-v5',
 review_source_consumption_contract='existing-source-consumption-proof-v2')
s=Settings(_env_file='.env',wic_provider_adapter='deepseek',wic_provider_model='deepseek-flash',
 wic_provider_reasoning_effort='none',collaboration_provider_timeout_seconds=120,collaboration_provider_max_output_tokens=16384)
p=ModelFulfillmentCandidateProvider.from_settings(s)
rows=[]
try:
 review=p.review(inv,wrong,capabilities=caps,owner_preconditions=owner,receipt_callback=lambda **v:rows.append(v))
 reason=None
 try: a.validate_projection_components(wrong,inv,semantic_review=review,review_source_consumption_contract='existing-source-consumption-proof-v2')
 except ValueError as e: reason=str(e)
 assert reason is not None,'a content requirement must not pass as background retention'
 result={'scenario':'Real Review of a deliberately wrong content-as-retention route; declared isolated fixture',
   'source_files':{p:__import__('hashlib').sha256(Path(p).read_bytes()).hexdigest() for p in ['src/spg/application/governed_obligations.py','src/spg/providers/fulfillment_candidate.py']},'production_mutations':False,'real_call_count':1,'rejection':reason,'source_verdict':review.source_results[0].complete_and_equivalent,
   'model':p.last_observation}
 Path('/tmp/watt-review-live-20261016/negative-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 Path('/tmp/watt-review-live-20261016/negative-response.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 print(json.dumps(result,ensure_ascii=False))
except Exception as e:
 print(type(e).__name__); raise
