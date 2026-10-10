"""Read-only diagnostics of old private wires; no model, repair or admission."""
import json, os
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
from spg.domain.governed_obligation import canonical_fingerprint
from spg.application.governed_obligations import (
    fulfillment_inventory, fulfillment_capability_contracts, _bind_wire_diagnostics, projection_validation_feedback)
from spg.providers.fulfillment_candidate import _decode_fulfillment_candidate_wire, _FulfillmentWireValidationError
from spg.providers.verification_receipts import _safe_value

P=Path('/retained');E=Path('/evidence')
inputs=[Path('/basis.json')]+[P/n for n in ('immutable-inventory.json','capability-contracts.json',
    'formation-owner-observations.json','formation-1-safe-wire.txt','formation-2-safe-wire.txt')]
before={p.name:sha256(p.read_bytes()).hexdigest() for p in inputs}
assert before['basis.json']=='9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c'
data=json.loads(inputs[0].read_text())
revision=WorkRealityRevision.model_validate(next(r for r in data['datasets']['work_reality_revisions']['rows']
    if r['id']=='332a3a38-8719-580c-a1a2-c331ae14a5ae'))
assessment=next(r for r in data['datasets']['interaction_assessments']['rows'] if r['id']==str(revision.source_assessment_id))
ir=GovernedSemanticIR.model_validate(assessment['semantic_ir'])
inventory=fulfillment_inventory(revision,ir,source_revision='465038ded6cf4ba335a11577de76acb1dea55b76',exact_target_paths=('index.html',))
caps=fulfillment_capability_contracts()
assert inventory==json.loads((P/'immutable-inventory.json').read_text())
assert caps==json.loads((P/'capability-contracts.json').read_text())
assert inventory['inventory_fingerprint']=='7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf'
rows=json.loads((P/'formation-owner-observations.json').read_text())
report={'schema':'c3-predecode-retained-diagnostic-recheck-v1','recorded_at_utc':datetime.now(timezone.utc).isoformat(),
    'application_source':os.environ['SPG_RUNTIME_REVISION'],'inventory_fingerprint':inventory['inventory_fingerprint'],
    'source_count':26,'capability_count':12,'capabilities_fingerprint':canonical_fingerprint(caps),
    'inputs_before':before,'attempts':[],'model_calls':0,'database_access':False,'history_mutated':False,
    'candidate_repaired':False,'canonical_candidate_admitted':False,'claim':'NEW_READONLY_DIAGNOSTICS_OF_OLD_OUTPUTS_NOT_NEW_LIVE_CONVERGENCE'}
for attempt in (1,2):
    start=next(r for r in rows if r['stage']=='MODEL_REQUEST_PENDING' and r['attempt']==attempt)
    response=next(r for r in rows if r['stage']=='MODEL_RESPONSE_OBSERVED' and r['attempt']==attempt)
    raw=(P/('formation-'+str(attempt)+'-safe-wire.txt')).read_text()
    try:
        _decode_fulfillment_candidate_wire(raw,inventory,caps,validation_feedback=start.get('feedback'),wire_metadata=response)
    except _FulfillmentWireValidationError as error:
        bound=_bind_wire_diagnostics(error,rows,attempt,revision,inventory,caps)
        feedback=json.loads(projection_validation_feedback(None,revision,ir,inventory,error,wire_diagnostics=bound))
        report['attempts'].append({'attempt':attempt,'canonical_candidate':'NOT_CONSTRUCTED','primary_error':str(error),
            'new_derived_diagnostics':bound,'new_derived_feedback':feedback,
            'feedback_sent_to_provider':False,'historical_feedback_replaced':False})
    else:
        raise AssertionError('Historical invalid output unexpectedly accepted')
report['inputs_after']={p.name:sha256(p.read_bytes()).hexdigest() for p in inputs}
assert report['inputs_before']==report['inputs_after']
assert _safe_value(report)==report
assert [len(a['new_derived_diagnostics']['violations']) for a in report['attempts']]==[2,6]
(E/'retained-diagnostic-recheck.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'result':'REJECTED_WITH_BOUND_DIAGNOSTICS','attempt_error_counts':[2,6],'model_calls':0,'history_mutated':False}))
