import json
from pathlib import Path
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
from spg.application.governed_obligations import form_fulfillment_projection
from spg.providers.fulfillment_candidate import _fulfillment_wire_context,_FulfillmentCompactCandidate,_fulfillment_wire_diagnostics
p=Path('/retained');inventory=json.loads((p/'immutable-inventory.json').read_text());caps=json.loads((p/'capability-contracts.json').read_text())
rows=json.loads((p/'formation-owner-observations.json').read_text());data=json.loads(Path('/basis.json').read_text())
revision=WorkRealityRevision.model_validate(next(r for r in data['datasets']['work_reality_revisions']['rows'] if r['id']==inventory['work_reality_revision_id']))
ir=GovernedSemanticIR.model_validate(next(r for r in data['datasets']['interaction_assessments']['rows'] if r['id']==str(revision.source_assessment_id))['semantic_ir'])
raw=(p/'formation-1-safe-wire.txt').read_text();first=next(r for r in rows if r['stage']=='MODEL_REQUEST_PENDING' and r['attempt']==1)
prefix,end=json.JSONDecoder().raw_decode(raw)
context=_fulfillment_wire_context(inventory,caps,validation_feedback=first.get('feedback'),owner_preconditions=first['owner_source_preconditions'])
wire=_FulfillmentCompactCandidate.model_validate(prefix)
assert wire.h==context['wire_request_fingerprint'] and wire.d==context['wire_table_fingerprint']
diagnostics=_fulfillment_wire_diagnostics(wire,inventory,context)
before=deepcopy(rows)
def forbidden(*args,**kwargs):raise AssertionError('Historical terminal must not call a model')
provider=SimpleNamespace(_fulfillment_receipts=rows,form=forbidden,review=forbidden)
result=form_fulfillment_projection(revision,ir,provider=provider,source_revision=inventory['source_revision'],exact_target_paths=inventory['exact_target_paths'])
assert before==rows
report={'schema':'c3-legacy-syntax-observation-review-v1','model_calls':0,'original_candidate_modified':False,'prefix_admitted':False,
 'wire_sha256':sha256(raw.encode()).hexdigest(),'prefix_span':[0,end],'prefix_sha256':sha256(raw[:end].encode()).hexdigest(),
 'trailing_bytes':len(raw[end:].encode()),'independent_raw_field_observations':diagnostics,
 'historical_terminal_replay':{'unchanged':True,'reason':result[0].formation_receipt['terminal_reason'],'new_calls':0},
 'claim':'Read-only original complete-value field observations; not repaired Candidate or historical success'}
Path('/diagnostic/analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'retained_terminal_unchanged':True,'observed_prefix_errors':len(diagnostics['violations']),
 'additional':diagnostics['additional_violation_count'],'codes':sorted({r['code'] for r in diagnostics['violations']})}))
