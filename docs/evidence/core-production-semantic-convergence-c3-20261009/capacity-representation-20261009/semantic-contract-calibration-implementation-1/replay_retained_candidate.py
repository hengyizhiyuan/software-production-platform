"""Read-only negative regression. Never repairs or admits the retained candidate."""
from datetime import datetime,timezone
from hashlib import sha256
import json,os
from pathlib import Path
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
from spg.domain.governed_obligation import FulfillmentProjectionCandidate,fulfillment_candidate_fingerprint
from spg.application.governed_obligations import fulfillment_inventory,validate_projection_candidate,projection_validation_feedback

basis=Path('/basis.json').read_bytes();raw=Path('/candidate.json').read_bytes()
assert sha256(basis).hexdigest()=='9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c'
assert sha256(raw).hexdigest()=='e9020a908ba354c2e12ab4db297b32b7d17041fd12e4180a740f39d9fb42c9b5'
data=json.loads(basis)
rev=WorkRealityRevision.model_validate(next(r for r in data['datasets']['work_reality_revisions']['rows'] if r['id']=='332a3a38-8719-580c-a1a2-c331ae14a5ae'))
assessment=next(r for r in data['datasets']['interaction_assessments']['rows'] if r['id']==str(rev.source_assessment_id))
ir=GovernedSemanticIR.model_validate(assessment['semantic_ir'])
inventory=fulfillment_inventory(rev,ir,source_revision='465038ded6cf4ba335a11577de76acb1dea55b76',exact_target_paths=('index.html',))
assert inventory['inventory_fingerprint']=='7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf'
candidate=FulfillmentProjectionCandidate.model_validate_json(raw)
assert len(candidate.routes)==57 and len(inventory['sources'])==26
assert fulfillment_candidate_fingerprint(candidate)=='98e38e96d66751327a6eb44519cf980db471aae99664b324c3e36a043a049444'
try:validate_projection_candidate(candidate,rev,ir,inventory,allow_review_pending=True)
except ValueError as error:
    assert str(error)=='OBLIGATION_PROJECTION_DUPLICATE_ROUTE'
    feedback=json.loads(projection_validation_feedback(candidate,rev,ir,inventory,error))
else:raise AssertionError('Retained failed candidate must not pass after calibration')
codes={r['code'] for r in feedback['violations']}
assert {'OBLIGATION_PROJECTION_DUPLICATE_ROUTE','OBLIGATION_PROJECTION_CONFLICTING_DISPOSITION','OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST'}<=codes
receipt={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'kind':'UNMODIFIED_HISTORICAL_NEGATIVE_REPLAY',
    'watt_source':os.environ['SPG_RUNTIME_REVISION'],'guardian_source':os.environ['C3_GUARDIAN_REVISION'],
    'basis_sha256':sha256(basis).hexdigest(),'candidate_sha256':sha256(raw).hexdigest(),
    'inventory_sources':26,'candidate_routes':57,'candidate_modified':False,'predicate':'OBLIGATION_PROJECTION_DUPLICATE_ROUTE',
    'feedback':feedback,'semantic_review':'NOT_EVALUABLE','owner_effect_evidence':'NOT_EVALUABLE',
    'formation_calls':0,'review_calls':0,'self_refine_calls':0,'work_or_owner_mutation':False,
    'claim':'Rejection/feedback regression only; not repaired Candidate or real model success'}
Path('/evidence/historical-replay.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'result':'REJECTED_AS_REQUIRED','primary_predicate':receipt['predicate'],
    'reported_violation_count':len(feedback['violations']),'additional_count':feedback['additional_violation_count']}))
