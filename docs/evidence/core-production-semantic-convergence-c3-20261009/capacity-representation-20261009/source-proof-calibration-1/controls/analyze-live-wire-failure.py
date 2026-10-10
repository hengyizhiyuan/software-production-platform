from pathlib import Path
from hashlib import sha256
import json
R=Path('/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/source-proof-live-2')
p=R/'private/model-observations';inv=json.loads((p/'immutable-inventory.json').read_text());caps=json.loads((p/'capability-contracts.json').read_text());rows=json.loads((p/'formation-owner-observations.json').read_text())
report={'schema':'c3-exact-wire-failure-readonly-v1','model_calls':0,'candidate_modified':False,'candidate_admitted':False,'attempts':[]}
for attempt in (1,2):
 raw=(p/('formation-'+str(attempt)+'-safe-wire.txt')).read_text()
 start=next(r for r in rows if r['stage']=='MODEL_REQUEST_PENDING' and r['attempt']==attempt)
 response=next(r for r in rows if r['stage']=='MODEL_RESPONSE_OBSERVED' and r['attempt']==attempt)
 assert sha256(raw.encode()).hexdigest()==response['candidate_output_sha256']
 r={'attempt':attempt,'wire_sha256':sha256(raw.encode()).hexdigest(),'request_receipt_id':start['receipt_id'],'response_receipt_id':response['receipt_id'],
  'owner_preconditions_fingerprint':sha256(json.dumps(start['owner_source_preconditions'],sort_keys=True,separators=(',',':')).encode()).hexdigest()}
 try:wire=json.loads(raw)
 except json.JSONDecodeError as error:
  r.update(json_status='INVALID',stable_parser_message=error.msg,line=error.lineno,column=error.colno,character_offset=error.pos,
    unexpected_code_point=ord(raw[error.pos]) if error.pos<len(raw) else 'END_OF_OUTPUT',syntax_context_sha256=sha256(raw[max(0,error.pos-25):error.pos+25].encode()).hexdigest(),
    output_ends_with_closing_brace=raw.rstrip().endswith('}'),complete_json_tree='NOT_EVALUABLE',semantic_checks='NOT_EVALUABLE')
 else:
  invalid=[]
  for i,route in enumerate(wire['routes']):
   for ref in route['f']:
    if 0<=ref<len(inv['sources']) and inv['sources'][ref]['kind']!='FACT':invalid.append({'route':i,'source':route['s'],'capability':route['c'],'invalid_fact_reference':ref,'actual_kind':inv['sources'][ref]['kind']})
  r.update(json_status='VALID',route_count=len(wire['routes']),invalid_fact_references=invalid,
    copied_primary_source_into_f=sum(route['f']==[route['s']] for route in wire['routes']),
    all_primary_sources_present=set(route['s'] for route in wire['routes'])==set(range(len(inv['sources']))),
    capability_frequencies={c['capability']:sum(route['c']==i for route in wire['routes']) for i,c in enumerate(caps)},
    full_plan_and_semantic_equivalence='NOT_EVALUABLE; canonical decode rejected')
 report['attempts'].append(r)
(R/'evidence/readonly-wire-failure.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([{k:r[k] for k in r if k in ('attempt','json_status','stable_parser_message','line','column','character_offset','unexpected_code_point','route_count','copied_primary_source_into_f','all_primary_sources_present')} for r in report['attempts']]))
