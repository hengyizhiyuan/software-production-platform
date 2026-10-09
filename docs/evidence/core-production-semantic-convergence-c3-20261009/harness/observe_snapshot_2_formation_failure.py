from pathlib import Path
from datetime import datetime, timezone
import json, subprocess
root=Path("/data/watt/c3-semantic-convergence-20261009")
sql="SELECT COALESCE(json_agg(json_build_object('id',id,'decision_type',decision_type,'authority_identity',authority_identity,'subject_type',subject_type,'subject_identity',subject_identity,'scope',scope,'created_at',created_at) ORDER BY created_at),'[]'::json) FROM governance_records WHERE decision_type='WORK_FULFILLMENT_OBSERVATION' AND authority_identity='work-governance:derived-candidate-observation';"
result=subprocess.check_output(["docker","exec","watt-c3-postgres-20261009","psql","-U","c3_app","-d","c1_contract_continuity","-tA","-c",sql],universal_newlines=True)
rows=json.loads(result)
creds=json.loads((root/"private/credentials.json").read_text())
public=json.dumps({"schema":"c3-scoped-failure-owner-observation-v1","observed_at_utc":datetime.now(timezone.utc).isoformat(),"database":"c1_contract_continuity","context":"last carrier setup after C1 setup failure; controlled fixture only","query_scope":"WORK_FULFILLMENT_OBSERVATION exact authority","rows":rows},indent=2)
for value in creds.values():
    if isinstance(value,str) and value:public=public.replace(value,"[REDACTED]")
(root/"evidence/dev-regression-2/formation-failure-owner-records.json").write_text(public+"\n")
sql="SELECT json_build_object('work_reality_revision_id',r.id,'work_id',r.work_id,'constraints',r.constraints,'context_facts',r.context_facts,'engineering_semantic_facts',r.engineering_semantic_facts,'semantic_ir',a.semantic_ir) FROM work_reality_revisions r JOIN interaction_assessments a ON a.id=r.source_assessment_id WHERE r.id='a2489a8e-fa3d-51cd-91e3-244545558aef';"
result=subprocess.check_output(["docker","exec","watt-c3-postgres-20261009","psql","-U","c3_app","-d","c1_contract_continuity","-tA","-c",sql],universal_newlines=True)
source=json.loads(result)
public=json.dumps({"observed_at_utc":datetime.now(timezone.utc).isoformat(),"database":"c1_contract_continuity","source":source},indent=2)
for value in creds.values():
    if isinstance(value,str) and value:public=public.replace(value,"[REDACTED]")
(root/"evidence/dev-regression-2/formation-failure-source-records.json").write_text(public+"\n")
print(json.dumps({"constraints":source["constraints"],"context_facts":source["context_facts"]}))
print(json.dumps({"record_count":len(rows),"failed_predicates":[r["scope"].get("failed_predicate") for r in rows if r["scope"].get("failed_predicate")],"terminal_reasons":[r["scope"].get("terminal_reason") for r in rows if r["scope"].get("terminal")]}))
