import json
from pathlib import Path
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
from spg.application.governed_obligations import _owner_source_preconditions, form_fulfillment_projection
p=Path('/retained');inv=json.loads((p/'immutable-inventory.json').read_text());caps=json.loads((p/'capability-contracts.json').read_text())
rows=json.loads((p/'formation-owner-observations.json').read_text());basis=json.loads(Path('/basis.json').read_text())
revision=WorkRealityRevision.model_validate(next(r for r in basis['datasets']['work_reality_revisions']['rows'] if r['id']==inv['work_reality_revision_id']))
ir=GovernedSemanticIR.model_validate(next(r for r in basis['datasets']['interaction_assessments']['rows'] if r['id']==str(revision.source_assessment_id))['semantic_ir'])
preconditions=_owner_source_preconditions(revision,ir,inv,caps)
index={s['source_ref']:i for i,s in enumerate(inv['sources'])}
report={'schema':'c3-source-proof-readonly-review-v1','model_calls':0,'original_candidate_modified':False,'owner_writes':0,
    'inventory_fingerprint':inv['inventory_fingerprint'],'original_owner_preconditions':preconditions,'attempts':[]}
for attempt in (1,2):
 candidate=json.loads((p/('formation-'+str(attempt)+'-expanded-candidate.json')).read_text())
 raw=(p/('formation-'+str(attempt)+'-safe-wire.txt')).read_text()
 issues=[]
 for ordinal,route in enumerate(candidate['routes']):
  row=preconditions['sources'][index[route['source_ref']]]
  capability=next(i for i,c in enumerate(caps) if c['capability']==route['capability'])
  proof=next((r for r in row.get('necessary_source_proofs',[]) if r['capability']==capability),None)
  if proof:
   selected=sorted(index[s] for s in route['supporting_source_refs'])
   issues.append({'route':ordinal,'source':row['source'],'capability':route['capability'],'selected_supports':selected,
    'is_minimal_eligible_source_proof':selected in proof['minimal_support_sets'],'eligible_minimal_proofs':proof['minimal_support_sets'],
    'semantic_equivalence':'NOT_EVALUATED; structural eligibility is not semantic proof'})
 report['attempts'].append({'attempt':attempt,'wire_sha256':sha256(raw.encode()).hexdigest(),'source_proof_observations':issues})
original=deepcopy(rows)
def forbidden(*args,**kwargs):raise AssertionError('Historical replay may not call a model')
provider=SimpleNamespace(_fulfillment_receipts=rows,form=forbidden,review=forbidden)
result=form_fulfillment_projection(revision,ir,provider=provider,source_revision=inv['source_revision'],exact_target_paths=inv['exact_target_paths'])
assert original==rows
report['legacy_terminal_replay']={'unchanged':True,'reason':result[0].formation_receipt['terminal_reason'],'new_calls':0}
Path('/diagnostic/analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'sources':len(preconditions['sources']),'precondition_bytes':len(json.dumps(preconditions).encode()),'legacy_replay':report['legacy_terminal_replay']}))
