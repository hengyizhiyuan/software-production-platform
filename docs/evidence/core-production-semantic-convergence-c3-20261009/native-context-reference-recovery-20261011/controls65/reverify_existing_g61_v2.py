"""Append corrected Verification on existing exact G61 Git subject; no execution replay."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,subprocess,uuid,time
R=Path('/data/watt/c3-semantic-convergence-20261009/binding-g0-generation61-qualification-20261010')
T=R/'native-context-recovery-generation65';E=T/'evidence';P=T/'private'
Q=Path('/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/g0-binding-generation65-qualified-20261010')
API='watt-c3-bindingg0g61-api-20261010';WORK='6ba2cffa-0bf3-565a-81e0-7f3c6696f21e';ATTEMPT='de98f392-b8d1-40ac-a442-a283fa938060';SNAPSHOT='5e7cd6d9-6899-5921-9e77-c8f030f319d6'
assert not (E/'corrected-verification.json').exists()
upgrade=json.loads((E/'isolated-role-upgrade.json').read_text());build=json.loads((Q/'final-image/evidence/build.json').read_text())
x=json.loads(subprocess.check_output(['docker','inspect',API],universal_newlines=True))[0];assert x['Image']==build['image']['Id'] and x['State']['Running']
script=r"""
from uuid import UUID
import json,os
from spg.config import Settings
from spg.infrastructure.persistence import Database
from spg.application.verification import VerificationService
from spg.providers.contract_verifier import ContractDrivenRepositoryVerifier
from spg.providers.protected_context_verifier import StaticProtectedContextVerifier
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
s=Settings();assert s.runtime_revision=='518fcf9f07c7ddfc9672dde431419af0412d58ed';db=Database.from_settings(s)
assert db.engine.url.database=='spg_c3_bindingg0g61_qualification_20261010'
service=VerificationService(db);provider=ContractDrivenRepositoryVerifier(db,context_verifier=StaticProtectedContextVerifier.from_settings(s))
assert provider.binding.provider_version=='v4-reviewed-responsibility-plan'
with db.unit_of_work() as uow:
 store=RuntimeStore(uow.session);native=NativeExecutionStore(uow.session)
 snapshot=store.proposed_snapshot(UUID('SNAPSHOT'));assert snapshot.attempt_id==UUID('ATTEMPT')
 assert snapshot.proposed_commit_identity=='43fa0621e0d0e06fd1b84c9b76e06b831a578d97' and snapshot.tree_identity=='c9942900fd4ad60eff68f4133bbf57181390da1a'
 unit=store.work_unit(snapshot.work_unit_id);assert unit.condition.value=='PRODUCED'
 binding=native.attempt_binding(UUID('ATTEMPT')).binding;assert binding.work_id==UUID('WORK')
 original_contract=native.contract(binding.pwu_contract_version_id)
 before={'contract_digest':original_contract.contract_digest,'steps':[str(r.id) for r in native.steps_for_attempt(UUID('ATTEMPT'))],'effects':[str(r.id) for r in native.effects_for_attempt(UUID('ATTEMPT'))],'old_verification':[r.model_dump(mode='json') for r in store.verification_records_for_snapshot(snapshot.id)]}
 assert len(before['steps'])==7 and len(before['effects'])==9
 assert not any(r['provider']['provider_version']=='v4-reviewed-responsibility-plan' for r in before['old_verification'])
record=service.verify_obligation(snapshot.id,'PATH_SCOPE',provider)
result={'source_revision':s.runtime_revision,'provider_binding':provider.binding.model_dump(mode='json'),'verification_record':record.model_dump(mode='json'),'prior_state':before,'admissibility':None}
if record.result.value=='PASS':
 diff=service.verify_obligation(snapshot.id,'GIT_DIFF_CHECK',provider);result['additional_verification_record']=diff.model_dump(mode='json')
 admitted=service.evaluate_admissibility(snapshot.id);result['admissibility']=admitted.model_dump(mode='json')
with db.unit_of_work() as uow:
 store=RuntimeStore(uow.session);native=NativeExecutionStore(uow.session)
 after={'contract_digest':native.contract(binding.pwu_contract_version_id).contract_digest,'steps':[str(r.id) for r in native.steps_for_attempt(UUID('ATTEMPT'))],'effects':[str(r.id) for r in native.effects_for_attempt(UUID('ATTEMPT'))]}
 assert all(after[k]==before[k] for k in after)
 assert all(store.verification_record(UUID(r['id'])).model_dump(mode='json')==r for r in before['old_verification'])
 result['unchanged_execution']=after
 from spg.infrastructure.persistence.product_store import ProductStore
 product=ProductStore(uow.session);work_binding=product.runtime_binding(UUID('WORK'));result['current_runtime_summary']=product.runtime_summary(work_binding).model_dump(mode='json')
print(json.dumps(result))
""".replace('SNAPSHOT',SNAPSHOT).replace('ATTEMPT',ATTEMPT).replace('WORK',WORK)
started=datetime.now(timezone.utc).isoformat();clock=time.monotonic()
r=subprocess.run(['docker','exec','-i',API,'python','-'],input=script.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
raw=P/('corrected-verification-private-'+uuid.uuid4().hex+'.json')
with raw.open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(json.dumps({'exit_code':r.returncode,'stdout':r.stdout.decode(errors='replace'),'stderr':r.stderr.decode(errors='replace')}).encode())
if r.returncode:print(json.dumps({'exit':r.returncode,'private_failure':str(raw),'model_outcome':'UNKNOWN'}));raise SystemExit(r.returncode)
x=json.loads(r.stdout.decode());record=x['verification_record'];meta=record['evidence'].get('metadata') or {};receipts=meta.get('verification_candidate_receipts') or {}
obj={'schema':'c3-corrected-owner-verification-continuation-v1','started_at_utc':started,'ended_at_utc':datetime.now(timezone.utc).isoformat(),'source_revision':build['sources']['watt']['revision'],'tree':build['sources']['watt']['tree'],'actual_api_image':build['image']['Id'],'work_id':WORK,'attempt_id':ATTEMPT,'snapshot_id':SNAPSHOT,'provider_binding':x['provider_binding'],'verification_record_id':record['id'],'verification_result':record['result'],'additional_verification_record_id':(x.get('additional_verification_record') or {}).get('id'),'additional_verification_result':(x.get('additional_verification_record') or {}).get('result'),'candidate_revision':record['proposed_commit_identity'],'candidate_tree':record['tree_identity'],'admissibility_id':None if x['admissibility'] is None else x['admissibility']['admissibility']['id'],'admissibility_outcome':None if x['admissibility'] is None else x['admissibility']['admissibility']['outcome'],'private_raw_path':str(raw),'private_raw_sha256':sha256(raw.read_bytes()).hexdigest(),'prior_verification_ids':[v['id'] for v in x['prior_state']['old_verification']],'original_contract_digest':x['prior_state']['contract_digest'],'execution_steps_unchanged':True,'settled_effects_unchanged':True,'historical_verification_unchanged':True,'current_runtime_summary':x['current_runtime_summary'],'formation_replayed':False,'native_execution_replayed':False,'work_created':0,'human_authorization_created':False,'failure_code':meta.get('protected_context_failure') or meta.get('failure_code'),'semantic_checks':[{'fact_id':c.get('fact_id'),'passed':c.get('passed'),'reason':c.get('reason'),'disposition':c.get('disposition')} for c in meta.get('static_html_semantic_checks',())],'receipt_refs':receipts.get('receipt_refs',[])}
rows=[v for v in receipts.get('records',()) if v.get('stage')=='CANDIDATE_OBSERVED']
requests=[];seen={}
for row in rows:
 rid=row['request_id']; safe={k:row.get(k) for k in ('request_id','usage','timing','effective_model','requested_model','provider','attempt','component','receipt_ref','candidate_output_sha256','candidate_bytes','transport_retry_count')}
 if rid in seen:assert seen[rid]==safe
 else:seen[rid]=safe;requests.append(safe)
keys=('input_tokens','output_tokens','total_tokens','cached_tokens','reasoning_tokens')
total={k:sum((v.get('usage') or {})[k] for v in requests) if requests and all(type((v.get('usage') or {}).get(k)) is int for v in requests) else 'UNKNOWN' for k in keys}
usage={'schema':'c3-actual-verification-provider-usage-v1','source_revision':obj['source_revision'],'verification_record_id':record['id'],'logical_calls':len(requests),'requests':requests,'deduplicated_actual_usage':total,'wall_seconds':time.monotonic()-clock,'monetary_cost':'UNKNOWN','provider_http_status':'UNKNOWN_NOT_RECORDED','private_raw_sha256':obj['private_raw_sha256']}
with (E/'actual-verification-provider-usage.json').open('x') as f:json.dump(usage,f,indent=2)
with (E/'corrected-verification.json').open('x') as f:json.dump(obj,f,indent=2)
print(json.dumps(obj))
