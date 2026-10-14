"""Read-only structural observations; never admit, repair or re-review output."""
from hashlib import sha256
import json
from pathlib import Path
from spg.application import governed_obligations as owner
from spg.providers import fulfillment_candidate as wire

inventory=json.loads(Path('/inventory/immutable-inventory.json').read_text())
caps=owner.fulfillment_capability_contracts()
def failure_rows(feedback):
    return [{k:r[k] for k in ('code','source','route','component_id','missing_same_capability_source_ordinals') if k in r}
        for r in feedback if isinstance(r,dict)]
report={}
for mode in ('live','retained-first'):
    rows=json.loads((Path('/private')/mode/'materialized-owner-receipts.json').read_text())
    results=[]
    for observed in [r for r in rows if r['stage']=='MODEL_RESPONSE_OBSERVED']:
        attempt=observed['attempt']
        start=next(r for r in rows if r['stage']=='MODEL_REQUEST_PENDING' and r['attempt']==attempt)
        pre=start['owner_source_preconditions']
        context=wire._fulfillment_wire_context(inventory,caps,validation_feedback=start.get('feedback'),owner_preconditions=pre)
        body,presentation=wire._fulfillment_wire_value(observed['candidate_output'],pre,inventory=inventory,wire_identity=context)
        compact=wire._FulfillmentCompactCandidate.model_validate_json(body)
        geometry=wire._fulfillment_wire_diagnostics(compact,inventory,context,detailed=True)
        routes=[{'ordinal':i,'source':r.s,'capability':caps[r.c]['capability'],
            'source_span':[r.a,r.z],'facts':list(r.f),'support_sources':list(r.u),
            'targets':list(r.t),'raw_route_fingerprint':wire.canonical_fingerprint(r.model_dump(mode='json'))}
            for i,r in enumerate(compact.routes)]
        validation=next(r for r in rows if r['stage']=='CANDIDATE_VALIDATED' and r['attempt']==attempt)
        feedback=json.loads(validation['validation_feedback']) if validation.get('validation_feedback') else {}
        repair=feedback.get('owner_repair_context',{})
        decision=repair.get('decision_revision_requests')
        raw=json.loads(observed['candidate_output'])
        edits={'replace_count':len(raw.get('replace',[])),'remove':raw.get('remove',[]),'append_count':len(raw.get('append',[]))}
        prior_feedback=json.loads(start['feedback']) if start.get('feedback') else {}
        prior_decisions=prior_feedback.get('owner_repair_context',{}).get('decision_revision_requests')
        revision_observations=[]
        if prior_decisions:
            basis=start['owner_source_preconditions']['candidate_construction_state']['repair_basis']['original_wire']
            for requested in prior_decisions['requests']:
                index=requested['original_route']
                replacement=next((edit['route'] for edit in raw.get('replace',[]) if edit['index']==index),None)
                old=basis['routes'][index]
                revision_observations.append({'original_route':index,
                    'replaced':replacement is not None,
                    'removed':any((r.get('index') if isinstance(r,dict) else r)==index for r in raw.get('remove',[])),
                    'replacement_consumer':(replacement or {}).get('capability'),
                    'changed_fields':[k for k,v in (replacement or {}).items() if old.get(k)!=v]})
        results.append({'attempt':attempt,'response_receipt_id':observed['receipt_id'],
            'response_sha256':observed['candidate_output_sha256'],'route_count':len(routes),
            'routes':routes,'source_consumer_sets':{str(i):sorted({r['capability'] for r in routes if r['source']==i}) for i in range(len(inventory['sources']))},
            'raw_geometry_failures':failure_rows(geometry['violations']),
            'validation_passed':validation['validation_passed'],'failed_predicate':validation.get('failed_predicate'),
            'validation_feedback_sha256':validation.get('validation_feedback_sha256'),
            'wire_failures':failure_rows(feedback.get('violations',[])),
            'owner_prerequisite_failures':failure_rows(repair.get('violations',[])),
            'decision_revision_requests':decision,'edits':edits,
            'consumed_decision_revision_requests':prior_decisions,
            'decision_revision_observations':revision_observations,
            'candidate_fingerprint':(validation.get('candidate') or {}).get('candidate_fingerprint')})
    review_count=sum(r['stage']=='SEMANTIC_REVIEW_PENDING' for r in rows)
    report[mode]={'attempts':results,'independent_review_calls':review_count,
        'consumer_correction_is_not_semantic_acceptance':True}
Path('/evidence/candidate-observations.json').write_text(json.dumps(report,indent=2))
print(json.dumps({m:{'review_calls':d['independent_review_calls'],'attempts':[
    {'attempt':r['attempt'],'consumers_0_1_2':{k:v for k,v in r['source_consumer_sets'].items() if k in ('0','1','2')},
     'geometry_failure_count':len(r['raw_geometry_failures']),'owner_failures':r['owner_prerequisite_failures'],
     'decision_request_count':len((r['decision_revision_requests'] or {}).get('requests',[])),'edits':r['edits']}
    for r in d['attempts']]} for m,d in report.items()},indent=2))
