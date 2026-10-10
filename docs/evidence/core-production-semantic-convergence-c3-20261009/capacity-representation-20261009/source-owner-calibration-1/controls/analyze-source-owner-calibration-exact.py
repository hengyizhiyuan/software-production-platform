import json, os
from copy import deepcopy
from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
from spg.application.governed_obligations import (
    _owner_repair_context, _work_constraint_direct_source,
    work_constraint_sources_correspond, form_fulfillment_projection, _capability_tuple,
)
from spg.providers.fulfillment_candidate import (
    _fulfillment_wire_route_observations, _decode_fulfillment_candidate_wire,
    _FulfillmentWireValidationError,
)
P=Path('/retained'); E=Path('/diagnostic')
inv=json.loads((P/'immutable-inventory.json').read_text())
caps=json.loads((P/'capability-contracts.json').read_text())
rows=json.loads((P/'formation-owner-observations.json').read_text())
basis=json.loads(Path('/basis.json').read_text())
revision=WorkRealityRevision.model_validate(next(r for r in basis['datasets']['work_reality_revisions']['rows'] if r['id']==inv['work_reality_revision_id']))
ir=GovernedSemanticIR.model_validate(next(r for r in basis['datasets']['interaction_assessments']['rows'] if r['id']==str(revision.source_assessment_id))['semantic_ir'])
report={'schema':'c3-source-owner-calibration-readonly-analysis-v1', 'inventory_fingerprint':inv['inventory_fingerprint'],
 'watt_source':os.environ['SPG_RUNTIME_REVISION'], 'model_calls':0,'owner_writes':0,
 'candidate_modified':False,'candidate_admitted':False,'private_text_published':False,'attempts':[]}
for attempt in (1,2):
 raw=(P/('formation-'+str(attempt)+'-safe-wire.txt')).read_text()
 start=next(r for r in rows if r['attempt']==attempt and r['stage']=='MODEL_REQUEST_PENDING')
 response=next(r for r in rows if r['attempt']==attempt and r['stage']=='MODEL_RESPONSE_OBSERVED')
 assert sha256(raw.encode()).hexdigest()==response['candidate_output_sha256']
 ctx=_owner_repair_context(raw,revision,ir,inv,caps,validation_feedback=start.get('feedback'))
 observed,_=_fulfillment_wire_route_observations(raw,inv,caps,validation_feedback=start.get('feedback'))
 detail=[]
 for index,wire,route in observed:
  source=inv['sources'][wire['s']]
  if source['kind']!='WORK_CONSTRAINT':continue
  entries=[inv['sources'][s] for s in wire['u']]
  component,_,phase,_,_=_capability_tuple(route.capability)
  quote=source['payload']['content']
  detail.append({'route':index,'source':wire['s'],'capability':route.capability,
   'selected_supports':wire['u'],
   'each_selected_support_directly_corresponds':[_work_constraint_direct_source(ir,quote,e) for e in entries],
   'existing_complete_correspondence_result':work_constraint_sources_correspond(ir,quote,entries,component=component,phase=phase,semantic_component_declared=True,calibrated=True),
   'exact_content_sha256':sha256(quote.encode()).hexdigest()})
 try:_decode_fulfillment_candidate_wire(raw,inv,caps,validation_feedback=start.get('feedback'))
 except _FulfillmentWireValidationError as error:decoder=str(error)
 else:raise AssertionError('Historical failed Candidate unexpectedly decoded')
 report['attempts'].append({'attempt':attempt,'wire_sha256':sha256(raw.encode()).hexdigest(),
   'request_receipt_id':start['receipt_id'],'response_receipt_id':response['receipt_id'],
   'strict_decoder_result':decoder,'new_bound_owner_context':ctx,'work_constraint_support_predicates':detail})
original=deepcopy(rows)
def forbidden(*args,**kwargs):raise AssertionError('Read-only replay may not call model')
provider=SimpleNamespace(_fulfillment_receipts=rows,form=forbidden,review=forbidden)
result=form_fulfillment_projection(revision,ir,provider=provider,source_revision=inv['source_revision'],exact_target_paths=inv['exact_target_paths'])
assert rows==original
report['historical_terminal_replay']={'receipt_bytes_unchanged':rows==original,'terminal_reason':result[0].formation_receipt['terminal_reason'],
 'all_bindings_unresolved':all(b.state=='UNRESOLVED' for b in result),'new_model_calls':0}
(E/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'attempts':[{'attempt':r['attempt'],'decoder':r['strict_decoder_result'],
 'codes':sorted({e['code'] for e in r['new_bound_owner_context']['violations']}),
 'wrong_direct_support_sets':[e['route'] for e in r['work_constraint_support_predicates'] if False in e['each_selected_support_directly_corresponds']]} for r in report['attempts']],
 'historical_terminal_replay':report['historical_terminal_replay']}))
