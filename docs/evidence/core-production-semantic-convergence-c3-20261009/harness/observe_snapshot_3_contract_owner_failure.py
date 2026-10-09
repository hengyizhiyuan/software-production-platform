from pathlib import Path
from datetime import datetime, timezone
import json, os, subprocess
ROOT=Path('/data/watt/c3-semantic-convergence-20261009');P=ROOT/'private';E=ROOT/'evidence/dev-regression-3-guardian-contract'
WORK='05ba84df-6881-56b6-a23a-f0e6c7120d41';REV='35571d11-9ce6-5e45-812f-21a86b8b31fb';PWU='4770e7c7-d15c-4f4e-b9a3-cce598818908'
VERIFICATIONS=('2ad7d287-fa64-5624-a923-41b4f01a1b3a','e9d817a6-d340-54c6-a14b-b71c8ae5e173')
def query(sql):
    data=subprocess.check_output(['docker','exec','watt-c3-postgres-20261009','psql','-U','c3_app','-d','c1_contract_continuity','-tA','-c',sql],universal_newlines=True)
    return json.loads(data)
source=query("SELECT json_build_object('work',(SELECT json_build_object('id',id,'work_mode',work_mode,'condition',condition,'current_work_reality_revision_id',current_work_reality_revision_id,'production_plan_proposal',production_plan_proposal) FROM product_works WHERE id='"+WORK+"'),'reality',(SELECT row_to_json(r) FROM work_reality_revisions r WHERE id='"+REV+"'),'semantic_ir',(SELECT a.semantic_ir FROM interaction_assessments a JOIN work_reality_revisions r ON r.source_assessment_id=a.id WHERE r.id='"+REV+"'),'pwu',(SELECT row_to_json(u) FROM production_work_units u WHERE id='"+PWU+"'),'plan_revision',(SELECT row_to_json(p) FROM plan_revisions p JOIN production_work_units u ON u.plan_revision_id=p.id WHERE u.id='"+PWU+"'),'native_bindings',(SELECT COALESCE(json_agg(b),'[]'::json) FROM native_attempt_bindings b WHERE b.pwu_id='"+PWU+"'),'pwu_contract_versions',(SELECT COALESCE(json_agg(c),'[]'::json) FROM pwu_contract_versions c WHERE c.pwu_id='"+PWU+"'));" )
assert source['work'] and source['reality'] and source['pwu'],'exact last fixture Owner record no longer exists'
verifications=query("SELECT COALESCE(json_agg(v ORDER BY v.created_at),'[]'::json) FROM verification_records v WHERE v.id IN ('"+"','".join(VERIFICATIONS)+"') AND v.work_unit_id='"+PWU+"';")
assert len(verifications)==2,'exact two Verification Owner records are missing'
observations=query("SELECT COALESCE(json_agg(g ORDER BY g.created_at),'[]'::json) FROM governance_records g WHERE g.decision_type='WORK_FULFILLMENT_OBSERVATION' AND g.authority_identity='work-governance:derived-candidate-observation' AND g.scope->>'work_reality_revision_id'='"+REV+"';")
payload={'schema':'c3-scoped-actual-fixture-owner-preservation-v1','observed_at_utc':datetime.now(timezone.utc).isoformat(),'database':'c1_contract_continuity','fixture_only':True,'guardian_request_id':'f7d2f0a6-088f-5492-8bbc-a988b444e7dc','work_id':WORK,'work_reality_revision_id':REV,'pwu_id':PWU,'source':source,'verifications':verifications,'formation_observations':observations,'scope':'exact last steering fixture Owner records read before independent carrier fixture reset; no reconstruction'}
private=P/'dev-regression-3-contract-last-c1-owner.raw.json'
with private.open('x') as output:
    os.fchmod(output.fileno(),0o600);output.write(json.dumps(payload,indent=2)+'\n')
public=json.dumps(payload,indent=2)
for value in json.loads((P/'credentials.json').read_text()).values():
    if isinstance(value,str) and value:public=public.replace(value,'[REDACTED]')
(E/'last-c1-full-owner-records.json').write_text(public+'\n')
summary=[]
for row in verifications:
    m=row['evidence'].get('metadata',{});dc=m.get('decision_context',{})
    summary.append({'id':row['id'],'obligation':row['obligation'],'result':row['result'],'protected_context_checks_count':len(m.get('protected_context_checks',[])),'decision_context':dc})
(E/'last-c1-verification-compact.json').write_text(json.dumps({'observed_at_utc':payload['observed_at_utc'],'work_id':WORK,'work_reality_revision_id':REV,'pwu_id':PWU,'verifications':summary,'formation_observation_count':len(observations)},indent=2)+'\n')
print(json.dumps({'owner_preserved':True,'work_id':WORK,'reality_revision':REV,'pwu_id':PWU,'verification_count':len(verifications),'formation_observation_count':len(observations),'verification_summaries':[{k:v for k,v in r.items() if k!='decision_context'} for r in summary]}))