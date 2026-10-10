import json,os
from pathlib import Path
from hashlib import sha256
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
P=Path('/retained');E=Path('/diagnostic')
inv=json.loads((P/'immutable-inventory.json').read_text());basis=json.loads(Path('/basis.json').read_text())
revision=WorkRealityRevision.model_validate(next(r for r in basis['datasets']['work_reality_revisions']['rows'] if r['id']==inv['work_reality_revision_id']))
assessment=next(r for r in basis['datasets']['interaction_assessments']['rows'] if r['id']==str(revision.source_assessment_id))
ir=GovernedSemanticIR.model_validate(assessment['semantic_ir']);items={i.item_id:i for i in ir.items}
entries=[s for s in inv['sources'] if s['kind'] in {'IR_CLAUSE','IR_CONSTRAINT'}]
rows=[]
for source,s in enumerate(inv['sources']):
 if s['kind']!='WORK_CONSTRAINT':continue
 quote=s['payload']['content'];direct=[];excluded=[]
 for e in entries:
  item=items[e['item_id']]
  if quote==item.statement or quote==e['payload']['clause']['source_text'] or (item.production is not None and quote in item.production.scope):direct.append(e['source_ref'])
  if item.production is not None:
   for value in item.production.exclusions:
    if quote=='Excluded from this Work: '+value:excluded.append(e['source_ref'])
 rows.append({'source':source,'source_ref':s['source_ref'],'constraint_index':s['index'],'content_sha256':sha256(quote.encode()).hexdigest(),
  'exact_original_source_matches':direct,'exact_existing_exclusion_derivation_matches':excluded,
  'can_existing_correspondence_function_enter_a_success_branch':bool(direct or excluded),
  'semantic_equivalence':'UNKNOWN_NOT_REVIEWED','owner_identity':'EXACT_PERSISTED_WORK_REALITY',
  'meaning':'This checks all success-branch prerequisites of current work_constraint_sources_correspond; no new route, binding, review or authority is created.'})
report={'application_source':os.environ['SPG_RUNTIME_REVISION'],'inventory_fingerprint':inv['inventory_fingerprint'],
 'source_revision':inv['source_revision'],'work_reality_revision_id':inv['work_reality_revision_id'],
 'model_calls':0,'owner_writes':0,'private_text_published':False,'contract_symbol':'spg.application.governed_obligations.work_constraint_sources_correspond',
 'all_original_clause_entries_checked':len(entries),'work_constraint_success_prerequisites':rows}
(E/'work-source-proof-boundary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'clauses_checked':len(entries),'work_constraints':len(rows),'no_existing_success_prerequisite':[r['source'] for r in rows if not r['can_existing_correspondence_function_enter_a_success_branch']], 'rows':rows}))
