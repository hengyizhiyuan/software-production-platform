from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
from spg.domain.governed_obligation import FulfillmentProjectionCandidate,fulfillment_candidate_fingerprint,fulfillment_components_fingerprint,fulfillment_component_id,fulfillment_source_semantic_text,canonical_fingerprint
from spg.application.governed_obligations import fulfillment_inventory,projection_validation_feedback,validate_projection_candidate,is_context_only_clause
s=json.loads(Path('/basis.json').read_text());datasets=s['datasets'];work=s['work_id']
revision=WorkRealityRevision.model_validate(datasets['work_reality_revisions']['rows'][0])
assessment=next(r for r in datasets['interaction_assessments']['rows'] if r['id']==str(revision.source_assessment_id))
ir=GovernedSemanticIR.model_validate(assessment['semantic_ir'])
rows=[r for r in datasets['governance_records']['rows'] if r['decision_type']=='WORK_FULFILLMENT_OBSERVATION']
scope=rows[0]['scope']
inventory=fulfillment_inventory(revision,ir,source_revision=scope['source_revision'],exact_target_paths=tuple(scope['exact_target_paths']))
assert inventory['inventory_fingerprint']==scope['inventory_fingerprint']
result={'schema':'c3-final-g0-original-candidate-readonly-review-v1','observed_at_utc':datetime.now(timezone.utc).isoformat(),'work_id':work,'reality_id':str(revision.id),'inventory_fingerprint':scope['inventory_fingerprint'],'source_count':len(inventory['sources']),'exact_target_paths':inventory['exact_target_paths'],'model_calls':0,'candidate_mutations':0,'original_basis_sha256':sha256(Path('/basis.json').read_bytes()).hexdigest(),'attempts':[]}
for row in rows:
 a=row['scope']
 if a['stage']!='CANDIDATE_VALIDATED' or not a.get('candidate'):continue
 c=FulfillmentProjectionCandidate.model_validate(a['candidate'])
 try:validate_projection_candidate(c,revision,ir,inventory,allow_review_pending=True);code='DETERMINISTIC_PASS'
 except ValueError as error:code=str(error)
 assert code==a['failed_predicate'],'ORIGINAL_PREDICATE_REPLAY_DRIFT'
 fb=json.loads(projection_validation_feedback(c,revision,ir,inventory,code))
 v={'attempt':a['attempt'],'candidate_fingerprint':fulfillment_candidate_fingerprint(c),'components_fingerprint':fulfillment_components_fingerprint(c),'route_count':len(c.routes),'original_row_id':row['id'],'original_receipt_id':a['receipt_id'],'failed_predicate':code,'terminal':a['terminal'],'full_original_candidate_replayed_without_change':True,'violations':fb['violations'],'affected_components':[]}
 for violation in fb['violations']:
  if 'route' not in violation:continue
  n=violation['route'];route=c.routes[n];source=next(x for x in inventory['sources'] if x['source_ref']==route.source_ref)
  item=next((x for x in ir.items if x.item_id==source.get('item_id')),None)
  clause=next((x for x in ir.clauses if x.clause_id==source.get('clause_id')),None)
  b=route.component_basis
  v['affected_components'].append({'code':violation['code'],'route':n,'source_ref':route.source_ref,'source_kind':source['kind'],'capability':route.capability,'component_id':fulfillment_component_id(route,inventory['inventory_fingerprint']),'original_text_sha256':sha256(fulfillment_source_semantic_text(source).encode()).hexdigest(),'start':b.source_span_start if b else None,'end':b.source_span_end if b else None,'component_quote_sha256':sha256(b.source_component_quote.encode()).hexdigest() if b else None,'original_item_kind':item.kind if item else None,'clause_temporal_scope':clause.temporal_scope if clause else None,'clause_polarity':clause.polarity if clause else None,'existing_context_only_contract':is_context_only_clause(revision,ir,item.item_id,clause.clause_id) if clause and item else None})
 result['attempts'].append(v)
assert len(result['attempts'])==2
with Path('/out/original-candidate-readonly-review.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({'work_id':work,'source_count':result['source_count'],'attempts':[{'attempt':x['attempt'],'failed_predicate':x['failed_predicate'],'violations':x['violations'],'affected_components':x['affected_components']} for x in result['attempts']]}))
