from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,re
R=Path('/data/watt/c3-semantic-convergence-20261009/final-g0-qualification-20261010');E=R/'evidence'
r=json.loads(sorted(E.glob('owner-export-*.json'))[-1].read_text());s=json.loads((Path(r['private_directory'])/r['raw_private_file']).read_text());D=s['datasets']
state=json.loads((E/'normal-entry-state.json').read_text())
rows=[x for x in D['governance_records']['rows'] if x.get('decision_type')=='WORK_FULFILLMENT_OBSERVATION']
allowed={'provider','model','request_id','response_id','request_fingerprint','request_payload_fingerprint','model_profile_id','model_profile_fingerprint','provider_status','termination_reason','transport_retry_count','usage','duration_seconds','elapsed_seconds','reasoning_effort','candidate_output_sha256','candidate_output_bytes','output_sha256','output_bytes','actual_request_output_schema_fingerprint','provider_wire_version','wire_request_fingerprint','wire_table_fingerprint','wire_schema_fingerprint','runtime_request_id','provider_response_id','provider_request_id','response_status','max_output_tokens','timeout_seconds'}
def safe_meta(v):
 if isinstance(v,dict):return {k:safe_meta(x) for k,x in v.items() if k in allowed or k in ('input_tokens','output_tokens','cached_tokens','reasoning_tokens','total_tokens','unknown')}
 if isinstance(v,(str,int,float,bool)) or v is None:return v
 return None
out={'schema':'c3-final-real-g0-terminal-review-v1','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'result':'FAIL_NOT_REAL_G0_QUALIFIED','source':'34e9ca9cc5cd5623a9463b42ba4c26ede061640f','tree':'00f053019cf3c1ba0cd43fa1b1fca023ef638a71','image':'sha256:697b80141e1a11a70111166a1bb66db674457f8461ce9bea5fa21affebdbcbec','guardian':'76c1e87a1b29d151f4ed949748e3298f2169c5b1','ecf':'5aa4f8833c359c15bd059eda5972aa3915bcc18c','database':'spg_c3_finalg0_qualification_20261010','migration':'20261007_72','work_id':s['work_id'],'product_id':state['product_id'],'interaction_id':state['interaction_id'],'turn_id':state['turn_id'],'input_sha256':state['input_sha256'],'actual_database_snapshot':s['database_snapshot'],'private_export_directory':r['private_directory'],'private_export_file':r['raw_private_file'],'private_export_sha256':r['raw_private_sha256'],'table_counts':{k:len(v.get('rows',[])) for k,v in D.items()},'formation':[],'self_refine':[],'human_integration_authorized':False,'human_acceptance_written':False,'human_delivery_authorized':False,'full_effect_audit_claim':False}
for x in rows:
 a=x['scope'];v={k:a[k] for k in ('stage','receipt_id','attempt','budget_limit','inventory_fingerprint','failed_predicate','validation_passed','terminal','terminal_reason','source_revision','exact_target_paths','candidate_fingerprint','components_fingerprint','repair_feedback_bound') if k in a};v.update(governance_row_id=x['id'],created_at=x.get('created_at'))
 if a.get('model'):
  v['model_metadata']=safe_meta(a['model']);v['model_observation_original_keys']=list(a['model'])
 if a.get('candidate'):
  from hashlib import sha256
  candidate=a['candidate'];v['candidate_route_count']=len(candidate['routes']);v['candidate_original_json_fingerprint']=sha256(json.dumps(candidate,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
 if a.get('validation_feedback'):
  text=a['validation_feedback'];f=json.loads(text);raw=f.pop('untrusted_previous_wire',None)
  if raw is not None:f['private_original_wire_sha256']=sha256(raw.encode()).hexdigest()
  for vv in f.get('violations',[]):
   if 'review_reason' in vv:vv['review_reason_sha256']=sha256(vv.pop('review_reason').encode()).hexdigest()
  v['validation_feedback']=f;v['validation_feedback_sha256']=sha256(text.encode()).hexdigest()
 out['formation'].append(v)
for x in D['self_refine_events']['rows']:
 out['self_refine'].append({k:x.get(k) for k in ('id','status','failure_family','final_result','work_resume_result','model_token_usage','created_at','updated_at')})
usage=[x['model_metadata']['usage'] for x in out['formation'] if x['stage']=='MODEL_RESPONSE_OBSERVED']
out['formation_actual_usage_sum']={k:sum(x[k] for x in usage) for k in ('input_tokens','output_tokens','reasoning_tokens','cached_tokens','total_tokens')}
out['formation_logical_calls']=len(usage);out['semantic_review_calls']=0;out['feedback_count']=sum(x['stage']=='CANDIDATE_VALIDATED' and x.get('repair_feedback_bound') and not x.get('terminal') for x in out['formation'])
out['cost_boundary']='Formation actual usage counted once from response receipts. Same usage in proposal and self-refine event is a duplicate representation, not extra tokens. WIC/base Design usage, complete HTTP call count and monetary cost UNKNOWN.'
out['final_projection']=state.get('latest_observation');out['driver_status']=state.get('driver_status')
out['stored_work_condition']=D['product_works']['rows'][0]['condition']
out['not_reached']=['Runtime','PWU','Task Workspace','Attempt','Native Binding/Permit','Queue','actual business Worker','Git production artifact','Verification','software Candidate Seal','applicable Work Guardian Assurance','Human Integration/Acceptance/Delivery']
out['automatic_retry_or_new_work']=False
target=E/'real-g0-terminal-review.json'
with target.open('x') as f:json.dump(out,f,indent=2)
print(json.dumps({'work_id':out['work_id'],'formation_calls':out['formation_logical_calls'],'review_calls':0,'actual_formation_usage':out['formation_actual_usage_sum'],'driver_status':out['driver_status'],'result':out['result']}))
