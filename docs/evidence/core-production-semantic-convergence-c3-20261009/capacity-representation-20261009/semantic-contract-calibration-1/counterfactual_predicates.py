"""Counterfactual copies only. Never eligible for admission or qualification."""
import sys
sys.dont_write_bytecode = True
import json, os
from collections import Counter
from hashlib import sha256
from pathlib import Path
from datetime import datetime, timezone
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
from spg.domain.governed_obligation import FulfillmentProjectionCandidate, fulfillment_source_semantic_text, fulfillment_candidate_fingerprint
from spg.application.governed_obligations import fulfillment_inventory, validate_projection_candidate, validate_projection_components

b=Path('/basis.json').read_bytes(); c=Path('/candidate.json').read_bytes()
assert sha256(b).hexdigest()=='9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c'
assert sha256(c).hexdigest()=='e9020a908ba354c2e12ab4db297b32b7d17041fd12e4180a740f39d9fb42c9b5'
d=json.loads(b)
rev=WorkRealityRevision.model_validate(next(r for r in d['datasets']['work_reality_revisions']['rows'] if r['id']=='332a3a38-8719-580c-a1a2-c331ae14a5ae'))
ir=GovernedSemanticIR.model_validate(next(r for r in d['datasets']['interaction_assessments']['rows'] if r['id']==str(rev.source_assessment_id))['semantic_ir'])
inv=fulfillment_inventory(rev,ir,source_revision='465038ded6cf4ba335a11577de76acb1dea55b76',exact_target_paths=('index.html',))
original=FulfillmentProjectionCandidate.model_validate_json(c)
refs={s['source_ref']:i for i,s in enumerate(inv['sources'])}
texts=[fulfillment_source_semantic_text(s) for s in inv['sources']]
def check(candidate, function=validate_projection_candidate):
    try:
        function(candidate,rev,ir,inv,allow_review_pending=True) if function==validate_projection_candidate else function(candidate,inv,allow_review_pending=True)
        return {'predicate':'RETURNED_WITH_REVIEW_PENDING_NOT_ADMISSION'}
    except ValueError as e: return {'predicate':str(e).split('\n')[0]}
seen=set(); keep=[]
for i,r in enumerate(original.routes):
    key=(r.source_ref,r.capability)
    if key in seen: continue
    seen.add(key)
    caps={r2.capability for r2 in original.routes if r2.source_ref==r.source_ref}
    if r.capability in {'UNRESOLVED','RETAIN_CONTEXT'}:
        if caps-{'UNRESOLVED','RETAIN_CONTEXT'}: continue
        if r.capability=='UNRESOLVED' and 'RETAIN_CONTEXT' in caps: continue
    keep.append(i)
rows=[]
def record(name,candidate,description):
    rows.append({'name':name,'counterfactual_only':True,'invalid_as_production_result':True,'recipe':description,'candidate_fingerprint':fulfillment_candidate_fingerprint(candidate),'source_count':len({r.source_ref for r in candidate.routes}),'route_count':len(candidate.routes),'result':check(candidate),'independent_review':'NOT_EXECUTED','admission':False})
plan=original.model_copy(update={'routes':tuple(original.routes[i] for i in keep)})
record('CF_SINGLE_DISPOSITION',plan,'Discard duplicate and secondary dispositions; retains context for descriptive sources; destructive diagnostic selection only')
full=[]
for r in plan.routes:
    text=texts[refs[r.source_ref]]
    full.append(r.model_copy(update={'component_basis':r.component_basis.model_copy(update={'source_span_start':0,'source_span_end':len(text),'source_component_quote':text})}))
plan=plan.model_copy(update={'routes':tuple(full)})
record('CF_FULL_SOURCE_SPANS',plan,'Extend every selected span to the full original source. This changes candidate meaning/identity and is not a valid repaired Candidate')
plan=plan.model_copy(update={'routes':tuple(r for r in plan.routes if not(refs[r.source_ref]==3 and r.capability=='GIT_DIFF_SCOPE'))})
record('CF_SUPPRESS_UNSUPPORTED_FACT_SCOPE_ROUTE',plan,'Remove Fact Scope Git route, leaving content proposal; conceals real obligation and cannot qualify')
routes=[]
for r in plan.routes:
    if refs[r.source_ref]==4:
        if any(refs[x.source_ref]==4 for x in routes): continue
        r=r.model_copy(update={'capability':'UNRESOLVED','target_paths':()})
    routes.append(r)
plan=plan.model_copy(update={'routes':tuple(routes)})
record('CF_UNRESOLVED_PROHIBITION_FACT',plan,'Replace three permission Fact routes by one UNRESOLVED; truthful unresolved still cannot permit runtime')
result={'schema':'c3-isolated-counterfactual-predicates-v1','observed_at_utc':datetime.now(timezone.utc).isoformat(),'original_candidate_sha256':sha256(c).hexdigest(),'counterfactuals':rows,'uncovered_sources':[{'source_ordinal':i,'last_character_codepoint':ord(t[-1]),'missing_nonwhitespace_positions':[len(t)-1]} for i,t in enumerate(texts)],'original_span_end_is_length_minus_one':all(r.component_basis.source_span_start==0 and r.component_basis.source_span_end==len(texts[refs[r.source_ref]])-1 for r in original.routes),'model_calls':0,'semantic_review':False,'source_or_owner_writes':False}
with Path('/evidence/counterfactual-predicates.json').open('x',encoding='utf-8') as stream:
    os.fchmod(stream.fileno(),0o600); json.dump(result,stream,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=False))
