from pathlib import Path
import json,re
R=Path('/data/watt/c3-semantic-convergence-20261009/final-g0-qualification-20261010');E=R/'evidence'
r=json.loads(sorted(E.glob('owner-export-*.json'))[-1].read_text());s=json.loads((Path(r['private_directory'])/r['raw_private_file']).read_text())
def safe(v):
 if isinstance(v,dict):
  return {k:safe(x) for k,x in v.items() if not any(p in k.lower() for p in ('text','prompt','quote','rationale','secret','password','key','content','instructions')) and safe(x) is not None}
 if isinstance(v,list):return [safe(x) for x in v if safe(x) is not None][:50]
 if isinstance(v,(int,float,bool)) or v is None:return v
 if isinstance(v,str) and (re.fullmatch(r'[A-Z][A-Z0-9_:.\-]{0,150}',v) or re.fullmatch(r'[0-9a-f\-]{32,64}',v)):return v
 return None
out={'work_id':s['work_id'],'tables':{k:len(v.get('rows',[])) for k,v in s['datasets'].items()}}
for n in ('product_works','steering_steps','steering_decisions','semantic_step_results','work_convergence_observations','self_refine_events','production_work_units','execution_attempts','baseline_candidates','verification_records'):
 out[n]=[safe(v) for v in s['datasets'].get(n,{}).get('rows',[])]
out['governance']=[safe(v) for v in s['datasets'].get('governance_records',{}).get('rows',[])]
keys=('id','receipt_id','stage','attempt','budget_limit','failed_predicate','terminal','terminal_reason','validation_passed','inventory_fingerprint','candidate_fingerprint','components_fingerprint','usage','provider_failure','model_request_id','model_response_id','repair_feedback_bound')
def collect_codes(v):
 result=[]
 if isinstance(v,dict):
  for k,x in v.items():
   if k in ('failed_predicate','code','error_code','error_type','failure_code','terminal_reason') and isinstance(x,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:\-]{0,160}',x):result.append(x)
   if k not in ('owner_source_preconditions','inventory','candidate','request_context','prompt','messages','source_records'):result+=collect_codes(x)
 elif isinstance(v,list):
  for x in v:result+=collect_codes(x)
 return result
compact={'work_id':s['work_id'],'counts':out['tables'],'governance':[]}
for row in s['datasets'].get('governance_records',{}).get('rows',[]):
 scope=row.get('scope',{});v={k:scope[k] for k in keys if k in scope};v['governance_row_id']=row['id'];v['codes']=sorted(set(collect_codes(scope)))
 compact['governance'].append(v)
def find_usage(v,path=''):
 rows=[]
 if isinstance(v,dict):
  numeric={k:x for k,x in v.items() if k in ('input_tokens','output_tokens','reasoning_tokens','cached_tokens','cached_input_tokens','total_tokens','unknown') and (x is None or isinstance(x,(int,bool)))}
  if any(k in numeric for k in ('input_tokens','output_tokens','total_tokens')):rows.append({'path':path,'usage':numeric})
  for k,x in v.items():
   if k not in ('candidate','inventory','owner_source_preconditions','request_context','model_response','source_records'):rows+=find_usage(x,path+'/'+k)
 elif isinstance(v,list):
  for i,x in enumerate(v):rows+=find_usage(x,path+'/'+str(i))
 return rows
compact['usage_observations']=find_usage(s['datasets'])
for n in ('semantic_step_results','work_convergence_observations','self_refine_events'):
 compact[n]=[{'id':x.get('id'),'keys':list(x),'codes':sorted(set(collect_codes(x))),'status':x.get('status'),'result':x.get('result'),'state':x.get('state'), 'result_kind':x.get('result_kind'),'step_type':x.get('step_type'),'completion_satisfied':x.get('completion_satisfied'),'failure_family':x.get('failure_family'),'final_result':x.get('final_result'),'work_resume_result':x.get('work_resume_result')} for x in s['datasets'].get(n,{}).get('rows',[])]
print(json.dumps(compact))
