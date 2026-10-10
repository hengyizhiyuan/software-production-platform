import json
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from types import SimpleNamespace
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
from spg.application.governed_obligations import _owner_source_preconditions,form_fulfillment_projection
inv=json.loads(Path('/retained/immutable-inventory.json').read_text());caps=json.loads(Path('/retained/capability-contracts.json').read_text())
basis=json.loads(Path('/basis.json').read_text())
revision=WorkRealityRevision.model_validate(next(r for r in basis['datasets']['work_reality_revisions']['rows'] if r['id']==inv['work_reality_revision_id']))
ir=GovernedSemanticIR.model_validate(next(r for r in basis['datasets']['interaction_assessments']['rows'] if r['id']==str(revision.source_assessment_id))['semantic_ir'])
preconditions=_owner_source_preconditions(revision,ir,inv,caps)
report={'schema':'c3-existing-typed-owner-root-v1','model_calls':0,'owner_writes':0,'inventory_fingerprint':inv['inventory_fingerprint'],
 'typed_observations':[preconditions['sources'][i] for i in (2,21,22)],'historical_replays':[],'counterfactual_admission':'NOT_PERFORMED'}
for folder in ('source-proof-live-4','source-operands-live-1','source-operands2-live-1','source-review-fixed-live-1'):
 rows=json.loads((Path('/history')/folder/'private/model-observations/formation-owner-observations.json').read_text());before=deepcopy(rows)
 def forbidden(*a,**kw):raise AssertionError('No model call allowed in historical replay')
 provider=SimpleNamespace(_fulfillment_receipts=rows,form=forbidden,review=forbidden)
 result=form_fulfillment_projection(revision,ir,provider=provider,source_revision=inv['source_revision'],exact_target_paths=inv['exact_target_paths'])
 assert rows==before
 report['historical_replays'].append({'folder':folder,'terminal_reason':result[0].formation_receipt['terminal_reason'],
  'receipt_bytes_sha256':sha256((Path('/history')/folder/'private/model-observations/formation-owner-observations.json').read_bytes()).hexdigest(),
  'unchanged_receipts':True,'new_calls':0})
Path('/evidence/typed-owner-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'historical_replays':report['historical_replays'],'typed_prerequisite_contract':preconditions['typed_prerequisite_contract']}))
