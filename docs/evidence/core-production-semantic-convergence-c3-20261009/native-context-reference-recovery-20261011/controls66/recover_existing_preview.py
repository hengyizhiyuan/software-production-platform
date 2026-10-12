from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
from urllib.request import Request,urlopen
import json,os,subprocess,time,uuid
R=Path('/data/watt/c3-semantic-convergence-20261009/binding-g0-generation61-qualification-20261010');T=R/'native-context-recovery-generation66';E=T/'evidence';P=T/'private'
Q=Path('/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/g0-binding-generation66-qualified-20261010');BUILD=json.loads((Q/'final-image/evidence/build.json').read_text())
SOURCE='01446afc7cccb03f99e8e6febbe4cfe9ed8388e4';IMAGE=BUILD['image']['Id'];API='watt-c3-bindingg0g61-api-20261010'
WORK='6ba2cffa-0bf3-565a-81e0-7f3c6696f21e';ATTEMPT='de98f392-b8d1-40ac-a442-a283fa938060';CANDIDATE='4a4096c3-2846-5678-ab8c-37aed60a0c9c';FINGERPRINT='9446c018fcafc8512a56c00d46861feac90c440014e6dc72af373249825af823'
assert BUILD['sources']['watt']['revision']==SOURCE and not (E/'preview-owner-recovery.json').exists()
a=json.loads(subprocess.check_output(['docker','inspect',API]).decode())[0];assert a['Image']==IMAGE and a['Config']['Labels']['watt.production']=='false'
token=json.loads((R/'private/credentials.json').read_text())['operator_token']
def save_private(label,raw):
 f=P/(label+'-'+uuid.uuid4().hex+'.json')
 with f.open('xb') as stream:os.fchmod(stream.fileno(),0o600);stream.write(raw)
 return {'private_path':str(f),'sha256':sha256(raw).hexdigest(),'bytes':len(raw)}
def http(suffix,mutation=False):
 req=Request('http://127.0.0.1:18327/api/works/'+WORK+suffix,data=b'' if mutation else None,method='POST' if mutation else 'GET',headers={'Authorization':'Bearer '+token})
 try:
  with urlopen(req,timeout=120) as response:raw=response.read();status=response.status
 except Exception as error:
  (E/('preview-request-unknown-'+uuid.uuid4().hex+'.json')).write_text(json.dumps({'suffix':suffix,'mutation':mutation,'error_type':type(error).__name__,'outcome':'UNKNOWN','automatic_retry':False}))
  raise
 return json.loads(raw),{'http_status':status,**save_private('preview-http',raw)}
script=r"""
import json
from hashlib import sha256
from uuid import UUID
from pathlib import Path
from spg.config import Settings
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore
s=Settings();assert s.runtime_revision=='SOURCE';db=Database.from_settings(s);assert db.engine.url.database=='spg_c3_bindingg0g61_qualification_20261010'
def digest(x):return sha256(json.dumps(x.model_dump(mode='json'),sort_keys=True,separators=(',',':')).encode()).hexdigest()
with db.unit_of_work() as u:
 product=ProductStore(u.session);runtime=RuntimeStore(u.session);native=NativeExecutionStore(u.session)
 binding=product.runtime_binding(UUID('WORK'));summary=product.runtime_summary(binding);candidate=runtime.baseline_candidate(UUID('CANDIDATE'));assert candidate is not None and candidate.fingerprint=='FINGERPRINT'
 assert candidate.id==summary.candidate_id and summary.admissibility_outcome=='ADMISSIBLE'
 assert summary.authorization_id is None and summary.runtime_commit_id is None and summary.integration_effect_id is None
 assert tuple(str(x) for x in candidate.verification_record_ids)==('5d603bcf-4245-5c64-8333-179d1fc797d6','a0c9307e-f5fe-516a-95e8-fe17b27e985b')
 proposed=runtime.proposed_snapshot(candidate.proposed_snapshot_id);admission=runtime.production_admissibility(candidate.production_admissibility_id)
 records=runtime.verification_records_for_snapshot(candidate.proposed_snapshot_id)
 steps=native.steps_for_attempt(UUID('ATTEMPT'));effects=native.effects_for_attempt(UUID('ATTEMPT'))
 assert len(steps)==7 and len(effects)==9
 pe=JsonProductionEnvironmentStore(s.native_executor_production_environment_store_root)
 original=pe.guardian_projection(UUID('OLD_PREVIEW'))
 assert original is not None and original['gate']=='BLOCKED' and original.get('result_ref') is None
 original_bytes=(pe.root/'guardian-projections'/'OLD_PREVIEW.json').read_bytes()
 print(json.dumps({'candidate_id':str(candidate.id),'candidate_fingerprint':candidate.fingerprint,'candidate_owner_sha256':digest(candidate),'proposal_sha256':digest(proposed),'admissibility_sha256':digest(admission),'historical_verification_sha256':{str(r.id):digest(r) for r in records},'native_step_sha256':{str(x.id):digest(x) for x in steps},'settled_effect_sha256':{str(x.id):digest(x) for x in effects},'original_guardian_projection_sha256':sha256(original_bytes).hexdigest(),'integration_authorization_id':summary.authorization_id,'runtime_commit_id':summary.runtime_commit_id,'integration_effect_id':summary.integration_effect_id},default=str))
""".replace('SOURCE',SOURCE).replace('WORK',WORK).replace('ATTEMPT',ATTEMPT).replace('CANDIDATE',CANDIDATE).replace('FINGERPRINT',FINGERPRINT)
def inspect(old_id):
 r=subprocess.run(['docker','exec','-i',API,'python','-'],input=script.replace('OLD_PREVIEW',old_id).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if r.returncode:
  save_private('preview-owner-inspection-failure',json.dumps({'stdout':r.stdout.decode(errors='replace'),'stderr':r.stderr.decode(errors='replace')}).encode());raise RuntimeError('PREVIEW_OWNER_CONTINUITY_REJECTED')
 return json.loads(r.stdout.decode())
before,record=http('/functional-preview');assert before['status']=='READY' and before['candidate_fingerprint']==FINGERPRINT
old_id=before['session']['id'];initial=inspect(old_id)
(E/'preview-recovery-before.json').write_text(json.dumps({'old_preview_id':old_id,'owner_identity':initial,'http_receipt':record},indent=2))
stopped,stop_receipt=http('/functional-preview/stop',True);assert stopped['id']==old_id and stopped['status']=='STOPPED'
requested,request_receipt=http('/functional-preview',True);assert requested['id']!=old_id and requested['candidate_fingerprint']==FINGERPRINT
latest={};guardian={};observations=[]
for _ in range(45):
 latest,lr=http('/functional-preview');guardian,gr=http('/guardian-assurance')
 observations.append({'captured_at_utc':datetime.now(timezone.utc).isoformat(),'preview_status':latest['status'],'preview_id':(latest.get('session') or {}).get('id'),'guardian_status':guardian.get('status'),'guardian_gate':guardian.get('gate'),'preview_http':lr,'guardian_http':gr})
 if guardian.get('gate') in ('PASS','BLOCKED','FAIL_REPAIRABLE') and latest['status'] in ('READY','FAILED'):break
 time.sleep(2)
final=inspect(old_id);assert final==initial,'IMMUTABLE_OWNER_RECORD_CHANGED_DURING_PREVIEW_RECOVERY'
obj={'schema':'c3-exact-candidate-preview-recovery-v1','captured_at_utc':datetime.now(timezone.utc).isoformat(),'source_revision':SOURCE,'actual_api_image':IMAGE,'work_id':WORK,'attempt_id':ATTEMPT,'candidate_id':CANDIDATE,'candidate_fingerprint':FINGERPRINT,'old_preview_id':old_id,'new_preview_id':requested['id'],'stop_http_receipt':stop_receipt,'request_http_receipt':request_receipt,'observations':observations,'latest_preview':{k:latest.get(k) for k in ('status','candidate_revision','candidate_fingerprint')},'guardian_projection':guardian,'immutable_owner_records_before':initial,'immutable_owner_records_after':final,'work_created':0,'formation_replayed':False,'native_execution_replayed':False,'verification_model_replayed':False,'human_authorization_created':False,'original_guardian_projection_retained':True,'model_calls_by_controller':0,'controller_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
(E/'preview-owner-recovery.json').write_text(json.dumps(obj,indent=2));print(json.dumps({'guardian':guardian,'preview_status':latest['status'],'candidate_id':CANDIDATE,'immutable_owner_records_unchanged':True}))
