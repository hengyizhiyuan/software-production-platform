import json, sys
sys.dont_write_bytecode=True
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from collections import Counter
from spg.domain.governed_obligation import FulfillmentProjectionCandidate, fulfillment_candidate_fingerprint, fulfillment_components_fingerprint
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
from spg.application.governed_obligations import form_fulfillment_projection

root=Path('/historical-readonly')
output=Path('/c3-evidence')
results=[]
class NeverModel:
    def form(self,*args,**kwargs):raise AssertionError('READONLY_REPLAY_MUST_NOT_CALL_MODEL')
    def review(self,*args,**kwargs):raise AssertionError('READONLY_REPLAY_MUST_NOT_CALL_MODEL')
data=json.loads(Path('/basis.json').read_text())
rev=WorkRealityRevision.model_validate(next(r for r in data['datasets']['work_reality_revisions']['rows'] if r['id']=='332a3a38-8719-580c-a1a2-c331ae14a5ae'))
assessment=next(r for r in data['datasets']['interaction_assessments']['rows'] if r['id']==str(rev.source_assessment_id))
ir=GovernedSemanticIR.model_validate(assessment['semantic_ir'])
for name in ('semantic-convergence-live-1','semantic-domains-live-1','semantic-primary-live-1'):
    p=root/name/'private/model-observations'
    records=json.loads((p/'formation-owner-observations.json').read_text())
    old=deepcopy(records)
    provider=NeverModel();provider._fulfillment_receipts=records
    bindings=form_fulfillment_projection(rev,ir,provider=provider,database=None,
        source_revision='465038ded6cf4ba335a11577de76acb1dea55b76',exact_target_paths=('index.html',))
    assert records==old
    validated=[r for r in records if r['stage']=='CANDIDATE_VALIDATED']
    semantic_failed=[r for r in validated if r.get('semantic_feedback_contract')]
    row={'case':name,'records_unchanged':True,'model_calls':0,'receipt_sha256':sha256((p/'formation-owner-observations.json').read_bytes()).hexdigest(),
        'terminal_reason':bindings[0].formation_receipt['terminal_reason'],'binding_states':dict(Counter(b.state for b in bindings))}
    if semantic_failed:
        v=semantic_failed[-1];feedback=json.loads(v['validation_feedback'])
        row['semantic_feedback_binding']=feedback['semantic_review_feedback_binding']
        row['repair_feedback_binding']=feedback['repair_feedback_binding']
        row['violations']=[{k:val for k,val in x.items() if k!='review_reason'} for x in feedback['violations']]
        for x,y in zip(row['violations'],feedback['violations'],strict=True):
            if 'review_reason' in y:x['review_reason_sha256']=sha256(y['review_reason'].encode()).hexdigest()
    if name=='semantic-primary-live-1':
        candidate=FulfillmentProjectionCandidate.model_validate_json((p/'formation-1-located-candidate.json').read_text())
        inv=json.loads((p/'immutable-inventory.json').read_text());refs={s['source_ref']:i for i,s in enumerate(inv['sources'])}
        row.update(candidate_fingerprint=fulfillment_candidate_fingerprint(candidate),components_fingerprint=fulfillment_components_fingerprint(candidate),
            routes=[{'source':refs[r.source_ref],'capability':r.capability,'target_paths':list(r.target_paths),
                     'supporting_source_ordinals':[refs[s] for s in r.supporting_source_refs]} for r in candidate.routes])
        assert not any(r.capability=='DENY_PREVIEW' for r in candidate.routes)
    results.append(row)
neg=root/'preview-negative-final-1/private/model-observations'
review=json.loads((neg/'review-2-parsed-candidate.json').read_text())
bad=json.loads((root/'preview-negative-final-1/evidence/live-result.json').read_text())
bykey={(r['component_id'],r['capability']):r for r in bad['candidate']['routes']}
rejected=[{**{k:v for k,v in r.items() if k!='reason'},'route':bykey[(r['component_id'],r['capability'])]['route'],
    'source_ref':bykey[(r['component_id'],r['capability'])]['source_ref'],'reason_sha256':sha256(r['reason'].encode()).hexdigest()}
    for r in review['component_results'] if not(r['complete_and_equivalent'] and r['nonredundant'] and r['owner_phase_evidence_valid'])]
assert bad['result']=='REVIEW_REJECTED'
assert all(any(r['route']==i and r['capability']=='DENY_PREVIEW' for r in rejected) for i in (21,41))
report={'schema':'c3-primary-source-semantic-qualification-analysis-v1','model_calls':0,'private_originals_mutated':False,
    'replay_claim':'READONLY_CONTINUITY_NOT_NEW_MODEL_OR_WORK_QUALIFICATION','readonly_replays':results,
    'actual_final_negative':{'qualification':'PASS_EXPECTED_REJECTION','candidate_fingerprint':bad['candidate']['candidate_fingerprint'],
        'review_sha256':sha256((neg/'review-2-parsed-candidate.json').read_bytes()).hexdigest(),'rejected_components':rejected,
        'provider_usage':bad['observed_terminal_usage_sum'],'actual_gate_failure':bad['failed_predicate']}}
(output/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'readonly_replay_cases':len(results),'final_negative':'PASS_EXPECTED_REJECTION'}))
