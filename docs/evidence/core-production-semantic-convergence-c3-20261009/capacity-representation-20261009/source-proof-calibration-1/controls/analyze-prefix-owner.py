import json
from pathlib import Path
from hashlib import sha256
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
from spg.application.governed_obligations import _owner_repair_context
p=Path('/retained');inv=json.loads((p/'immutable-inventory.json').read_text());caps=json.loads((p/'capability-contracts.json').read_text());rows=json.loads((p/'formation-owner-observations.json').read_text())
data=json.loads(Path('/basis.json').read_text())
revision=WorkRealityRevision.model_validate(next(r for r in data['datasets']['work_reality_revisions']['rows'] if r['id']==inv['work_reality_revision_id']))
ir=GovernedSemanticIR.model_validate(next(r for r in data['datasets']['interaction_assessments']['rows'] if r['id']==str(revision.source_assessment_id))['semantic_ir'])
raw=(p/'formation-1-safe-wire.txt').read_text();start=next(r for r in rows if r['stage']=='MODEL_REQUEST_PENDING' and r['attempt']==1)
_,end=json.JSONDecoder().raw_decode(raw)
view=_owner_repair_context(raw[:end],revision,ir,inv,caps,validation_feedback=start.get('feedback'),owner_preconditions=start['owner_source_preconditions'])
report={'schema':'c3-counterfactual-prefix-owner-observations-v1','original_wire_sha256':sha256(raw.encode()).hexdigest(),
 'original_prefix_sha256':sha256(raw[:end].encode()).hexdigest(),'inventory_fingerprint':inv['inventory_fingerprint'],
 'request_receipt_id':start['receipt_id'],'attempt':1,'model_calls':0,'original_candidate_modified':False,
 'prefix_admitted':False,'not_historical_feedback_or_qualification':True,'observations':view}
Path('/diagnostic/owner-prefix-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'owner_predicate_failures':len(view['violations']),'codes':sorted({r['code'] for r in view['violations']})}))
