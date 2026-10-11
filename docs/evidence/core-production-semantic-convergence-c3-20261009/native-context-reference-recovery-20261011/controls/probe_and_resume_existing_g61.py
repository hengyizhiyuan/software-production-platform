from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,subprocess,os
from urllib.request import Request,urlopen
R=Path('/data/watt/c3-semantic-convergence-20261009/binding-g0-generation61-qualification-20261010');T=R/'native-context-recovery-generation62';E=T/'evidence';P=T/'private'
upgrade=json.loads((E/'isolated-role-upgrade.json').read_text());WORK=upgrade['work_id'];ATTEMPT=upgrade['attempt_id'];IMAGE=upgrade['image_id']
assert not (E/'lawful-resume.json').exists()
probe=r"""import json,sys
from copy import deepcopy
from spg.config import Settings
from spg.infrastructure.persistence import Database
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.domain.native_execution import WorkingPlan,canonical_digest
from spg.executor.context import NativeContextAssembler
from spg.executor.context_evidence import NativeContractExecutionView
from spg.executor.tools import PUBLIC_NATIVE_TOOL_CONTRACTS
settings=Settings();db=Database.from_settings(settings)
from uuid import UUID
with db.unit_of_work() as uow:
 store=NativeExecutionStore(uow.session);binding=store.attempt_binding(UUID(ATTEMPT)).binding;contract=store.contract(binding.pwu_contract_version_id)
 assert binding.work_id==UUID(WORK)
 assert store.steps_for_attempt(binding.attempt_id)==() and store.effects_for_attempt(binding.attempt_id)==()
view=NativeContractExecutionView(binding,contract);payload=deepcopy(view.payload)
for ref in view.references:
 for pointer in ref['original_locations']:
  parts=pointer.strip('/').split('/');parent=payload
  for part in parts[:-1]:parent=parent[int(part)] if isinstance(parent,list) else parent[part]
  parent[int(parts[-1])]=view.resolve(ref['reference'])
assert payload==contract.contract_payload and canonical_digest(payload)==contract.contract_digest
assembler=NativeContextAssembler();request=assembler.assemble(binding=binding,contract=contract,working_plan=WorkingPlan(version=1,objective_reference=str(contract.id),chosen_approach='Inspect governed Reality and execute the bounded PWU contract.',approach_rationale='No prior checkpoint exists for this execution session.',obligation_ids=tuple(binding.obligation_references)),step_sequence=1,available_tools=tuple(x for x in PUBLIC_NATIVE_TOOL_CONTRACTS if x['identity'] in {g.identity for g in binding.capability_grants}))
print(json.dumps({'work_id':str(binding.work_id),'attempt_id':str(binding.attempt_id),'contract_version_id':str(contract.id),'contract_digest':contract.contract_digest,'original_payload_bytes':len(json.dumps(contract.contract_payload,ensure_ascii=False,separators=(',',':')).encode()),'execution_view_bytes':len(json.dumps(view.payload,ensure_ascii=False,separators=(',',':')).encode()),'actual_request_bytes':assembler._size(request),'max_request_bytes':assembler.max_request_bytes,'reference_count':len(view.references),'total_reference_locations':sum(len(r['original_locations']) for r in view.references),'exact_roundtrip':True,'references':view.references,'source_vector_digest':binding.source_vector.digest,'original_resource_envelope':binding.resource_envelope.model_dump(mode='json'),'grants_digest':canonical_digest([g.model_dump(mode='json') for g in binding.capability_grants]),'model_calls':0,'tool_effects':0,'application_revision':settings.runtime_revision}))
""".replace('ATTEMPT',repr(ATTEMPT)).replace('WORK',repr(WORK))
p=subprocess.run(['docker','exec','-i','watt-c3-bindingg0g61-worker-20261010','python','-'],input=probe.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
assert p.returncode==0,'CURRENT_CONTRACT_READONLY_PROBE_FAILED'
result=json.loads(p.stdout);assert result['exact_roundtrip'] and result['actual_request_bytes']<result['max_request_bytes'] and result['contract_digest']=='bfca72d790e278192dd1238b34d04ae2493ec832013ae7c7ba7437db2f144100'
def write(path,obj,private=False):
 with path.open('x') as f:os.fchmod(f.fileno(),0o600 if private else 0o644);json.dump(obj,f,indent=2)
write(E/'native-context-projection-probe.json',result)
token=json.loads((R/'private/credentials.json').read_text())['operator_token']
def http(method,path,payload=None):
 data=None if payload is None else json.dumps(payload).encode()
 request=Request('http://127.0.0.1:18327'+path,data=data,method=method,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
 with urlopen(request,timeout=30) as f:return json.load(f)
reads=[]
for ref in result['references']:
 response=http('GET','/api/works/'+WORK+'/native-context/'+ATTEMPT+'/evidence/'+ref['content_digest'])
 assert response['reference']==ref['reference'] and response['contract_digest']==result['contract_digest']
 content=json.dumps(response['record'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
 assert sha256(content).hexdigest()==ref['content_digest']
 reads.append({'reference':ref['reference'],'content_digest':ref['content_digest'],'owner':ref['owner'],'http_status':200,'record_digest_verified':True})
write(E/'actual-owner-evidence-readback.json',{'captured_at_utc':datetime.now(timezone.utc).isoformat(),'reads':reads,'model_calls':0,'tool_effects':0,'work_created':0})
state=http('GET','/api/native-execution/attempts/'+ATTEMPT)
assert state['state']['runtime_mode']=='WAITING_RESOURCE' and not state['state']['effect_uncertainty']
assert state['steps']==[] and state['effects']==[] and state['state']['terminal_outcome'] is None
write(P/'before-resume-attempt.json',state,True)
from uuid import uuid5,NAMESPACE_URL
receipts=[]
for action in ('PAUSE','RESUME'):
 version=state['state']['control_version']
 response=http('POST','/api/native-execution/attempts/'+ATTEMPT+'/control',{'command_id':str(uuid5(NAMESPACE_URL,'c3-native-context62:'+ATTEMPT+':'+action)), 'action':action,'expected_control_version':version,'actor_identity':'human:owner','reason':'Qualified lossless Native Context assembly now fits unchanged admitted capacity; resume exact Attempt without resetting budget or effects.'})
 assert response['accepted'] and response['condition']=='APPLIED'
 receipts.append(response);state=http('GET','/api/native-execution/attempts/'+ATTEMPT)
write(E/'lawful-resume.json',{'captured_at_utc':datetime.now(timezone.utc).isoformat(),'work_id':WORK,'attempt_id':ATTEMPT,'image_id':IMAGE,'source':upgrade['source'],'control_receipts':receipts,'new_work':0,'original_contract_modified':False,'budget_increased':False,'permission_increased':False,'prior_effects':0,'controller_sha256':sha256(Path(__file__).read_bytes()).hexdigest()})
print(json.dumps({'probe':'PASS','exact_roundtrip':True,'request_bytes':result['actual_request_bytes'],'budget_bytes':result['max_request_bytes'],'history_readbacks':len(reads),'resume':'APPLIED','work_id':WORK,'attempt_id':ATTEMPT}))
