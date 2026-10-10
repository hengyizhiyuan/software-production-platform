import json,os
from pathlib import Path
from hashlib import sha256
from spg.providers.fulfillment_candidate import _FulfillmentCompactCandidate,_fulfillment_wire_context
P=Path('/retained');E=Path('/diagnostic')
inventory=json.loads((P/'immutable-inventory.json').read_text());caps=json.loads((P/'capability-contracts.json').read_text())
context=_fulfillment_wire_context(inventory,caps)
rows=[]
for attempt in (1,2):
 raw=(P/('formation-'+str(attempt)+'-safe-wire.txt')).read_bytes()
 wire=_FulfillmentCompactCandidate.model_validate_json(raw)
 missing=set(range(len(inventory['sources'])))-{r.s for r in wire.routes}
 detail=[]
 for idx in sorted(missing):
  source=inventory['sources'][idx];text=context['source_texts'][idx]
  same=[i for i,t in enumerate(context['source_texts']) if i!=idx and t==text]
  clause=source.get('clause_id')
  item=source.get('payload',{}).get('item',{})
  detail.append({'source':idx,'source_ref':source['source_ref'],'kind':source['kind'],'clause_id':clause,
   'semantic_item_kind':item.get('kind'),'own_route_count':0,
   'same_text_source_records':[{'source':i,'kind':inventory['sources'][i]['kind'],'own_route_capabilities':[caps[r.c]['capability'] for r in wire.routes if r.s==i],
    'same_clause_id':clause is not None and inventory['sources'][i].get('clause_id')==clause} for i in same],
   'support_reference_routes':[{'route':i,'primary_source':r.s,'capability':caps[r.c]['capability']} for i,r in enumerate(wire.routes) if idx in r.u],
   'semantic_equivalence_or_complete_business_coverage':'NOT_EVALUATED_NO_INDEPENDENT_REVIEW'})
 rows.append({'attempt':attempt,'wire_sha256':sha256(raw).hexdigest(),'primary_source_count':len({r.s for r in wire.routes}),'missing_source_records':detail})
report={'application_source':os.environ['SPG_RUNTIME_REVISION'],'inventory_fingerprint':inventory['inventory_fingerprint'],'attempts':rows,
 'model_calls':0,'candidate_modified':False,'private_text_published':False,'meaning':'Identical source text does not prove identical Fact/Clause/Constraint authority or disposition; supporting references are not own source-component routes under the current contract.'}
(E/'source-correspondence-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
