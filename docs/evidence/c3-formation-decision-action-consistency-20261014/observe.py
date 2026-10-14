"""Read retained qualification evidence; no admission or natural-language parsing."""
from hashlib import sha256
import json
from pathlib import Path
from spg.providers import fulfillment_candidate as wire
from spg.application import governed_obligations as owner

rows=json.loads(Path('/private/retained-first/materialized-owner-receipts.json').read_text())
inventory=json.loads(Path('/inventory/immutable-inventory.json').read_text())
caps=owner.fulfillment_capability_contracts()
observed=next(r for r in rows if r['stage']=='MODEL_RESPONSE_OBSERVED' and r['attempt']==2)
start=next(r for r in rows if r['stage']=='MODEL_REQUEST_PENDING' and r['attempt']==2)
first=next(r for r in rows if r['stage']=='MODEL_RESPONSE_OBSERVED' and r['attempt']==1)
feedback=json.loads(start['feedback'])
decisions=feedback['owner_repair_context']['decision_revision_requests']
targets=[r['original_route'] for r in decisions['requests']]
raw,_=wire._fulfillment_wire_value(observed['candidate_output'],start['owner_source_preconditions'],construct=False)
value=json.loads(raw)
original=json.loads(first['candidate_output'])['routes']
construction=observed['wire_presentation']['candidate_construction']
action=construction.get('decision_revision_action_observation') or construction.get('diagnostics',{}).get('decision_revision_action_observation')
summary={'original_wire_sha256':first['candidate_output_sha256'],
    'inventory_fingerprint':inventory['inventory_fingerprint'],
    'response_receipt_id':observed['receipt_id'],'response_sha256':observed['candidate_output_sha256'],
    'request_receipt_id':start['receipt_id'],'feedback_sha256':sha256(start['feedback'].encode()).hexdigest(),
    'declared_dispositions':[{k:r[k] for k in ('original_route','disposition','revised_fields') if k in r}
        for r in value.get('decision_revisions',[])],
    'constructor_action_evidence':action,'construction_rejected':construction.get('rejected',False),
    'decisions':[],'actual_independent_review_calls':sum(r['stage']=='SEMANTIC_REVIEW_PENDING' for r in rows),
    'candidate_validation':[],'semantics_not_inferred_from_rationale':True}
for index in targets:
    replacement=next((r['route'] for r in value.get('replace',[]) if r['index']==index),None)
    removed=any((r.get('index') if isinstance(r,dict) else r)==index for r in value.get('remove',[]))
    after=None if removed else replacement or original[index]
    summary['decisions'].append({'original_route':index,'operation':'remove' if removed else 'replace' if replacement else 'unchanged',
        'consumer_before':original[index]['capability'],'consumer_after':after['capability'] if after else None,
        'changed_fields':[k for k,v in (replacement or {}).items() if original[index].get(k)!=v]})
for r in rows:
    if r['stage']!='CANDIDATE_VALIDATED':continue
    data=json.loads(r['validation_feedback']) if r.get('validation_feedback') else {}
    safe=lambda vs:[{k:v[k] for k in ('code','condition','source','route','original_route','component_id') if k in v} for v in vs]
    summary['candidate_validation'].append({'attempt':r['attempt'],'validation_passed':r['validation_passed'],
        'failed_predicate':r.get('failed_predicate'),'failures':safe(data.get('violations',[])),
        'owner_prerequisite_failures':safe(data.get('owner_repair_context',{}).get('violations',[]))})
if not construction.get('rejected'):
    context=wire._fulfillment_wire_context(inventory,caps,validation_feedback=start['feedback'],owner_preconditions=start['owner_source_preconditions'])
    body,_=wire._fulfillment_wire_value(observed['candidate_output'],start['owner_source_preconditions'],inventory=inventory,wire_identity=context)
    compact=wire._FulfillmentCompactCandidate.model_validate_json(body)
    summary['source_consumer_sets']={str(i):sorted({caps[r.c]['capability'] for r in compact.routes if r.s==i}) for i in range(len(inventory['sources']))}
    summary['geometry_failures']=wire._fulfillment_wire_diagnostics(compact,inventory,context,detailed=True)['violations']
else:
    summary['source_consumer_sets']='NOT_EVALUABLE; NO_CONSISTENT_CONSTRUCTED_CANDIDATE'
Path('/evidence/action-observations.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k not in ('geometry_failures','source_consumer_sets')},indent=2))
