import json,os,unicodedata
from pathlib import Path
from hashlib import sha256
from spg.providers.fulfillment_candidate import _FulfillmentCompactCandidate,_fulfillment_wire_context
from spg.domain.governed_obligation import canonical_fingerprint
P=Path('/retained');E=Path('/diagnostic')
inventory=json.loads((P/'immutable-inventory.json').read_text())
caps=json.loads((P/'capability-contracts.json').read_text())
rows=json.loads((P/'formation-owner-observations.json').read_text())
inputs=[P/n for n in ('immutable-inventory.json','capability-contracts.json','formation-owner-observations.json','formation-1-safe-wire.txt','formation-2-safe-wire.txt')]
before={p.name:sha256(p.read_bytes()).hexdigest() for p in inputs}
report={'application_source':os.environ['SPG_RUNTIME_REVISION'],'inventory_fingerprint':inventory['inventory_fingerprint'],
 'candidate_modified':False,'model_calls':0,'private_source_text_published':False,'attempts':[],'inputs_before':before}
for attempt in (1,2):
 pending=next(r for r in rows if r['stage']=='MODEL_REQUEST_PENDING' and r['attempt']==attempt)
 context=_fulfillment_wire_context(inventory,caps,validation_feedback=pending.get('feedback'))
 wire=_FulfillmentCompactCandidate.model_validate_json((P/('formation-'+str(attempt)+'-safe-wire.txt')).read_text())
 obs={'attempt':attempt,'wire_sha256':before['formation-'+str(attempt)+'-safe-wire.txt'],'route_count':len(wire.routes),'coverage_gaps':[]}
 for source,text in enumerate(context['source_texts']):
  routes=[(i,r) for i,r in enumerate(wire.routes) if r.s==source]
  covered=set()
  for i,r in routes:
   if 0<=r.a<r.z<=len(text) and (r.q is None or r.q==text[r.a:r.z]):covered.update(range(r.a,r.z))
  missing=[i for i,c in enumerate(text) if not c.isspace() and i not in covered]
  if not missing:continue
  ranges=[]
  for i in missing:
   if ranges and ranges[-1][1]==i:ranges[-1][1]=i+1
   else:ranges.append([i,i+1])
  obs['coverage_gaps'].append({'source':source,'kind':inventory['sources'][source]['kind'],'source_ref':inventory['sources'][source]['source_ref'],
   'source_text_sha256':sha256(text.encode()).hexdigest(),'source_length':len(text),'proposed_spans':[{'route':i,'capability':caps[r.c]['capability'],'span':[r.a,r.z],'explicit_quote':r.q is not None} for i,r in routes],
   'missing_ranges':ranges,'missing_nonwhitespace_count':len(missing),'missing_unicode_categories':sorted(set(unicodedata.category(text[i]) for i in missing)),
   'all_missing_are_punctuation':all(unicodedata.category(text[i]).startswith('P') for i in missing),
   'missing_text_sha256':sha256(''.join(text[i] for i in missing).encode()).hexdigest()})
 report['attempts'].append(obs)
report['inputs_after']={p.name:sha256(p.read_bytes()).hexdigest() for p in inputs};assert before==report['inputs_after']
(E/'source-contribution-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'immutable_inputs':True,'attempts':report['attempts']}))
