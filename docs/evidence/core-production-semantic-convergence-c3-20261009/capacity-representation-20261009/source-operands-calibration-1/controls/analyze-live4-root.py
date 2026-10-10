import json
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from types import SimpleNamespace
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
from spg.domain.governed_obligation import FulfillmentProjectionCandidate
from spg.application.governed_obligations import (_owner_source_preconditions, form_fulfillment_projection,
    projection_validation_feedback, validate_projection_candidate)
p=Path('/retained'); inv=json.loads((p/'immutable-inventory.json').read_text()); caps=json.loads((p/'capability-contracts.json').read_text())
rows=json.loads((p/'formation-owner-observations.json').read_text()); basis=json.loads(Path('/basis.json').read_text())
revision=WorkRealityRevision.model_validate(next(r for r in basis['datasets']['work_reality_revisions']['rows'] if r['id']==inv['work_reality_revision_id']))
ir=GovernedSemanticIR.model_validate(next(r for r in basis['datasets']['interaction_assessments']['rows'] if r['id']==str(revision.source_assessment_id))['semantic_ir'])
candidate=FulfillmentProjectionCandidate.model_validate(json.loads((p/'formation-2-expanded-candidate.json').read_text()))
wire=(p/'formation-2-safe-wire.txt').read_text()
start=next(r for r in rows if r['stage']=='MODEL_REQUEST_PENDING' and r['attempt']==2)
response=next(r for r in rows if r['stage']=='MODEL_RESPONSE_OBSERVED' and r['attempt']==2)
refs={s['source_ref']:i for i,s in enumerate(inv['sources'])}
new=_owner_source_preconditions(revision,ir,inv,caps)
report={'schema':'c3-existing-owner-operands-root-cause-v1','attempt':2,'request_receipt_id':start['receipt_id'],
 'response_receipt_id':response['receipt_id'],'wire_output_fingerprint':sha256(wire.encode()).hexdigest(),
 'inventory_fingerprint':inv['inventory_fingerprint'],'model_calls':0,'owner_writes':0,'historical_candidate_modified':False,
 'observations':[]}
for ordinal in (4,29,30,31,32):
 r=candidate.routes[ordinal];s=refs[r.source_ref];cap=next(i for i,c in enumerate(caps) if c['capability']==r.capability)
 proof=next((p for p in new['sources'][s].get('necessary_source_proofs',[]) if p['capability']==cap),None)
 report['observations'].append({'route':ordinal,'source':s,'capability':r.capability,
  'observed_target_paths':r.target_paths,'required_target_paths':inv['exact_target_paths'] if r.capability=='GIT_DIFF_SCOPE' else None,
  'observed_support_ordinals':[refs[x] for x in r.supporting_source_refs],
  'necessary_source_proof_alternatives':None if proof is None else proof['minimal_support_sets'],
  'quote_sha256':sha256(r.component_basis.source_component_quote.encode()).hexdigest(),
  'predicate': 'OBLIGATION_DIFF_SCOPE_INCOMPLETE' if ordinal in (4,31,32) else 'OBLIGATION_SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN'})
before=deepcopy(rows)
def forbidden(*a,**kw):raise AssertionError('Read-only replay cannot make model calls')
provider=SimpleNamespace(_fulfillment_receipts=rows,form=forbidden,review=forbidden)
replayed=form_fulfillment_projection(revision,ir,provider=provider,source_revision=inv['source_revision'],exact_target_paths=inv['exact_target_paths'])
assert rows==before
report['historical_replay']={'terminal_reason':replayed[0].formation_receipt['terminal_reason'],'unchanged_receipts':True,'new_calls':0}
altered=[]
for ordinal,r in enumerate(candidate.routes):
 if ordinal in (4,31,32):r=r.model_copy(update={'target_paths':tuple(inv['exact_target_paths'])})
 if ordinal in (29,30):r=r.model_copy(update={'supporting_source_refs':(inv['sources'][7]['source_ref'],inv['sources'][13]['source_ref'])})
 altered.append(r)
diagnostic=candidate.model_copy(update={'routes':tuple(altered)})
try:
 validate_projection_candidate(diagnostic,revision,ir,inv,allow_review_pending=True)
 report['counterfactual']={'structural_predicate_result':'PASS','semantic_review':'NOT_EXECUTED','admission':'NOT_PERFORMED'}
except ValueError as error:
 report['counterfactual']={'structural_predicate_result':str(error),
  'feedback':json.loads(projection_validation_feedback(diagnostic,revision,ir,inv,error)),'admission':'NOT_PERFORMED'}
Path('/diagnostic/readonly-root-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'observations':len(report['observations']),'historical_replay':report['historical_replay'],'counterfactual':report['counterfactual']}))
