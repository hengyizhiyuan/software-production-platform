"""Unadmitted raw-route diagnostic view; no admission, review or gate bypass."""
import json,os
from pathlib import Path
from hashlib import sha256
from spg.providers.fulfillment_candidate import _FulfillmentCompactCandidate
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
from spg.domain.governed_obligation import FulfillmentProjectionCandidate
from spg.application.governed_obligations import projection_validation_feedback
P=Path('/retained');E=Path('/diagnostic')
inv=json.loads((P/'immutable-inventory.json').read_text());caps=json.loads((P/'capability-contracts.json').read_text())
basis=json.loads(Path('/basis.json').read_text())
revision=WorkRealityRevision.model_validate(next(r for r in basis['datasets']['work_reality_revisions']['rows'] if r['id']==inv['work_reality_revision_id']))
assessment=next(r for r in basis['datasets']['interaction_assessments']['rows'] if r['id']==str(revision.source_assessment_id))
ir=GovernedSemanticIR.model_validate(assessment['semantic_ir'])
report={'application_source':os.environ['SPG_RUNTIME_REVISION'],'inventory_fingerprint':inv['inventory_fingerprint'],
 'view_status':'UNADMITTED_COUNTERFACTUAL_DIAGNOSTIC_ONLY','excluded_frontier':'RAW_SOURCE_CONTRIBUTION_COVERAGE',
 'real_decoder_result':'FAIL_UNCHANGED','model_calls':0,'owner_writes':0,'candidate_admitted':False,'attempts':[]}
for attempt in (1,2):
 raw=(P/('formation-'+str(attempt)+'-safe-wire.txt')).read_bytes();wire=_FulfillmentCompactCandidate.model_validate_json(raw)
 routes=[]
 for route in wire.routes:
  source=inv['sources'][route.s]
  if source['kind']=='FACT':text=source['provenance']['source_text']
  elif source['kind'] in {'IR_CLAUSE','IR_CONSTRAINT'}:text=source['payload']['clause']['source_text']
  elif source['kind']=='IR_ITEM':text=source['payload']['item']['statement']
  else:text=source['payload']['content']
  assert 0<=route.a<route.z<=len(text) and all(inv['sources'][i]['kind']=='FACT' for i in route.f)
  routes.append({'source_ref':source['source_ref'],'capability':caps[route.c]['capability'],
   'work_constraint_indices':(source['index'],) if source['kind']=='WORK_CONSTRAINT' else (),
   'target_paths':[inv['exact_target_paths'][i] for i in route.t],
   'supporting_source_refs':[inv['sources'][i]['source_ref'] for i in route.u],'rationale':route.r,
   'component_basis':{'source_span_start':route.a,'source_span_end':route.z,'source_component_quote':text[route.a:route.z] if route.q is None else route.q,
    'linked_fact_refs':[inv['sources'][i]['source_ref'] for i in route.f]}})
 # A typed diagnostic value is not an admitted or valid complete Candidate.
 diagnostic=FulfillmentProjectionCandidate(inventory_fingerprint=inv['inventory_fingerprint'],routes=tuple(routes))
 feedback=json.loads(projection_validation_feedback(diagnostic,revision,ir,inv,'OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST'))
 report['attempts'].append({'attempt':attempt,'wire_sha256':sha256(raw).hexdigest(),'evaluated_raw_route_count':len(routes),
  'independently_evaluable_predicates':feedback['violations'],'additional_count':feedback['additional_violation_count'],
  'not_evaluable':['VALID_COMPLETE_CANDIDATE','INDEPENDENT_SEMANTIC_REVIEW','ACTUAL_OWNER_EVIDENCE','ASSURANCE'],
  'raw_routes_preserved':True,'missing_routes_added':False})
(E/'owner-predicate-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'view_status':report['view_status'],'attempts':[{'attempt':r['attempt'],'codes':sorted(set(e['code'] for e in r['independently_evaluable_predicates']))} for r in report['attempts']]}))
