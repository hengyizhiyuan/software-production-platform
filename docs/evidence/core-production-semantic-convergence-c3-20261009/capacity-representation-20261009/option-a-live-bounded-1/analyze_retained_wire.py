"""Read-only raw wire diagnostics; no repair, decoding bypass or model request."""
import json,os
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
from collections import Counter
from spg.providers.fulfillment_candidate import _FulfillmentCompactCandidate,_fulfillment_wire_context,_wire_json_object
from spg.domain.governed_obligation import canonical_fingerprint

P=Path('/retained');E=Path('/diagnostic')
inventory=json.loads((P/'immutable-inventory.json').read_text())
caps=json.loads((P/'capability-contracts.json').read_text())
observations=json.loads((P/'formation-owner-observations.json').read_text())
inputs=[P/'immutable-inventory.json',P/'capability-contracts.json',P/'formation-owner-observations.json',
        P/'formation-1-safe-wire.txt',P/'formation-2-safe-wire.txt']
before={p.name:sha256(p.read_bytes()).hexdigest() for p in inputs}
sources=inventory['sources']
report={'schema':'c3-option-a-readonly-wire-diagnostics-v1','recorded_at_utc':datetime.now(timezone.utc).isoformat(),
    'source':os.environ['SPG_RUNTIME_REVISION'],'inventory_fingerprint':inventory['inventory_fingerprint'],
    'capabilities_fingerprint':canonical_fingerprint(caps),'inputs_before':before,'attempts':[],
    'private_text_published':False,'candidate_repaired':False,'model_calls':0,'diagnostic_is_admission':False}
for attempt in (1,2):
    pending=next(r for r in observations if r['stage']=='MODEL_REQUEST_PENDING' and r['attempt']==attempt)
    context=_fulfillment_wire_context(inventory,caps,validation_feedback=pending.get('feedback'))
    text=(P/('formation-'+str(attempt)+'-safe-wire.txt')).read_text()
    parsed=json.loads(text,object_pairs_hook=_wire_json_object)
    wire=_FulfillmentCompactCandidate.model_validate(parsed)
    detail={'attempt':attempt,'raw_response_sha256':before['formation-'+str(attempt)+'-safe-wire.txt'],
        'wire_schema':'PASS','request_fingerprint_match':wire.h==context['wire_request_fingerprint'],
        'table_fingerprint_match':wire.d==context['wire_table_fingerprint'],'route_count':len(wire.routes),
        'routes':[],'independently_evaluable_wire_errors':[],
        'not_evaluable':['CANONICAL_CANDIDATE','COMPONENT_SEMANTIC_EQUIVALENCE','SOURCE_OWNER_CORRESPONDENCE',
            'INDEPENDENT_SEMANTIC_REVIEW','ACTUAL_PERMISSION_AND_EVIDENCE','ASSURANCE'],
        'actual_feedback':None if pending.get('feedback') is None else json.loads(pending['feedback'])}
    coverage={i:set() for i in range(len(sources))}
    def error(code,route,**values):detail['independently_evaluable_wire_errors'].append({'code':code,'route':route,**values})
    for i,r in enumerate(wire.routes):
        item={'route':i,'source_ordinal':r.s,'capability_ordinal':r.c,'raw_wire_route_fingerprint':canonical_fingerprint(r.model_dump(mode='json')),
            'span':[r.a,r.z],'fact_ordinals':list(r.f),'target_ordinals':list(r.t),'support_ordinals':list(r.u)}
        if r.s>=len(sources) or r.c>=len(caps):
            error('OBLIGATION_FORMATION_WIRE_SOURCE_OR_CAPABILITY_INDEX_INVALID',i);detail['routes'].append(item);continue
        item.update(source_ref=sources[r.s]['source_ref'],source_kind=sources[r.s]['kind'],capability=caps[r.c]['capability'])
        source_text=context['source_texts'][r.s]
        quote=source_text[r.a:r.z] if r.q is None and 0<=r.a<r.z<=len(source_text) else r.q
        for name,values,size in [('FACT',r.f,len(sources)),('TARGET',r.t,len(context['tables']['target_paths'])),('SUPPORT',r.u,len(sources))]:
            if len(set(values))!=len(values) or any(v<0 or v>=size for v in values):error('OBLIGATION_FORMATION_WIRE_'+name+'_INDEX_INVALID',i)
        for index in r.f:
            if 0<=index<len(sources) and sources[index]['kind']!='FACT':
                error('OBLIGATION_FORMATION_WIRE_FACT_KIND_INVALID',i,source_ordinal=r.s,capability=item['capability'],
                    invalid_fact_ordinal=index,actual_source_kind=sources[index]['kind'],actual_source_ref=sources[index]['source_ref'])
        if r.q is None and not 0<=r.a<r.z<=len(source_text):error('OBLIGATION_FORMATION_WIRE_SPAN_INVALID',i,source_ordinal=r.s)
        if quote is not None:
            item['quote_sha256']=sha256(quote.encode()).hexdigest()
            item['slice_currently_exact']=0<=r.a<r.z<=len(source_text) and source_text[r.a:r.z]==quote
            if item['slice_currently_exact']:coverage[r.s].update(range(r.a,r.z))
            if all(0<=f<len(sources) for f in r.f):
                item['diagnostic_proposed_component_fingerprint']=canonical_fingerprint({
                    'inventory_fingerprint':inventory['inventory_fingerprint'],'source_ref':sources[r.s]['source_ref'],
                    'component_basis':{'source_span_start':r.a,'source_span_end':r.z,'source_component_quote':quote,
                        'linked_fact_refs':[sources[f]['source_ref'] for f in r.f]}})
                item['component_identity_status']='RAW_PROPOSAL_ONLY_NOT_CONSTRUCTED_OR_VALIDATED'
        detail['routes'].append(item)
    detail['wire_error_counts']=dict(Counter(e['code'] for e in detail['independently_evaluable_wire_errors']))
    detail['raw_span_source_observations']=[{'source_ordinal':i,'source_ref':s['source_ref'],'source_kind':s['kind'],
        'text_length':len(context['source_texts'][i]),'covered_nonwhitespace':all(j in coverage[i] for j,c in enumerate(context['source_texts'][i]) if not c.isspace()),
        'meaning':'raw slice observation only, not semantic coverage'} for i,s in enumerate(sources)]
    report['attempts'].append(detail)
report['inputs_after']={p.name:sha256(p.read_bytes()).hexdigest() for p in inputs}
report['immutable_inputs']=before==report['inputs_after'];assert report['immutable_inputs']
(E/'retained-wire-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'source':report['source'],'immutable_inputs':True,'candidate_repaired':False,
    'attempts':[{'attempt':r['attempt'],'routes':r['route_count'],'wire_errors':r['wire_error_counts'],
        'feedback_predicate':None if r['actual_feedback'] is None else r['actual_feedback']['primary_error']} for r in report['attempts']]}))
