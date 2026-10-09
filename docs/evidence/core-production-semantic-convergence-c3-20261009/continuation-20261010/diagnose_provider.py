"""One exact historical formation request, observation only; no Work/Owner write."""
import sys
sys.dont_write_bytecode = True
from datetime import datetime, timezone
from hashlib import sha256
import json, re, time
from pathlib import Path
from dataclasses import asdict

OUT=Path('/c3-evidence/provider-diagnostic.json')
BASIS=Path('/basis.json')
assert not OUT.exists()
started=datetime.now(timezone.utc).isoformat(); clock=time.monotonic()
row={'schema':'c3-continuation-provider-diagnostic-v1','started_at_utc':started,
 'scope':'One historical formation request reproduced outside Work, no admission, Owner write, model authority or Candidate',
 'historical_failure_cause':'UNKNOWN','new_work_created':False,'historical_work_mutated':False,
 'logical_model_entries':0,'stages':[],'http_observations':[],'numeric_usage':'UNKNOWN','output_contract':'NOT_REACHED'}
def machine(v,limit=200):
 if not isinstance(v,str) or re.fullmatch(r'[A-Za-z0-9_.:-]{1,'+str(limit)+'}',v) is None:return None
 from spg.providers.verification_receipts import _safe_value
 return v if _safe_value(v)==v else None
def stage(v):
 row['stages'].append({'stage':machine(v),'at_utc':datetime.now(timezone.utc).isoformat()})
try:
 from spg.config import Settings
 from spg.domain.interaction import WorkRealityRevision
 from spg.domain.intent_realization import GovernedSemanticIR
 from spg.application.governed_obligations import fulfillment_inventory, fulfillment_capability_contracts
 from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider, provider_failure_observation
 from spg.domain.model_runtime import ModelPurpose
 from spg.infrastructure.model_runtime import ModelProviderError
 data=json.loads(BASIS.read_text())
 rows=data['datasets']
 revision=WorkRealityRevision.model_validate(next(r for r in rows['work_reality_revisions']['rows'] if r['id']=='332a3a38-8719-580c-a1a2-c331ae14a5ae'))
 assessment=next(r for r in rows['interaction_assessments']['rows'] if r['id']==str(revision.source_assessment_id))
 ir=GovernedSemanticIR.model_validate(assessment['semantic_ir'])
 binding=data['actual_task_projections'][0]['fulfillment_bindings'][0]
 inventory=fulfillment_inventory(revision,ir,source_revision=binding['source_revision'],exact_target_paths=('index.html',))
 assert inventory['inventory_fingerprint']=='7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf'
 capabilities=fulfillment_capability_contracts()
 row.update(basis_sha256=sha256(BASIS.read_bytes()).hexdigest(),work_id=str(revision.work_id),
   work_reality_revision_id=str(revision.id),inventory_fingerprint=inventory['inventory_fingerprint'],
   capabilities_sha256=sha256(json.dumps(capabilities,sort_keys=True).encode()).hexdigest(),
   source_revision=inventory['source_revision'],source_refs=[s['source_ref'] for s in inventory['sources']])
 settings=Settings()
 provider=ModelFulfillmentCandidateProvider.from_settings(settings)
 assert provider is not None
 factory=provider.runtime_factory
 def runtime_factory():
  runtime=factory();profile=runtime.profile(ModelPurpose.STEERING_SEMANTIC)
  adapter=runtime.registry.adapter(profile.provider)
  row['profile']={'provider':profile.provider.value,'model':profile.model,'reasoning_effort':profile.reasoning_effort,
   'timeout_seconds':profile.timeout_seconds,'max_output_tokens':profile.max_output_tokens,'base_url':adapter.base_url}
  def response_hook(response):
   observed={'status_code':response.status_code,'at_utc':datetime.now(timezone.utc).isoformat(),
    'request_id':machine(response.headers.get('x-request-id') or response.headers.get('request-id'))}
   if response.status_code>=400:
    try:
     payload=json.loads(response.read());error=payload.get('error',{}) if isinstance(payload,dict) else {}
     if isinstance(error,dict):
      observed.update(error_code=machine(error.get('code'),120),error_type=machine(error.get('type'),120))
    except Exception as exc:observed['error_body_parse_type']=type(exc).__name__
   row['http_observations'].append(observed)
  original_new=adapter._new_client
  def observed_new():
   client=original_new();client.event_hooks['response'].append(response_hook);return client
  adapter._client.event_hooks['response'].append(response_hook)
  adapter._new_client=observed_new
  original_generate=runtime.generate
  def generate(**kwargs):
   assert kwargs.get('on_stage') is None
   row['logical_model_entries']+=1
   return original_generate(**kwargs,on_stage=stage)
  runtime.generate=generate
  return runtime
 provider.runtime_factory=runtime_factory
 def callback(**values):
  row['model_observation']=values.get('model')
  row['candidate_output_sha256']=values.get('candidate_output_sha256')
  row['candidate_output_bytes']=values.get('candidate_output_bytes')
 candidate=provider.form(inventory,capabilities,receipt_callback=callback)
 row.update(result='PROVIDER_RESPONSE_AND_OUTPUT_CONTRACT_OBSERVED',output_contract='PARSED_CANDIDATE_NOT_AUTHORITY',
  candidate_fingerprint=sha256(candidate.model_dump_json().encode()).hexdigest(),validation_or_assurance_pass=False)
 row['numeric_usage']=provider.last_observation.get('usage')
except Exception as error:
 from spg.providers.fulfillment_candidate import provider_failure_observation
 row.update(result='FAILED',exception_type=type(error).__name__,provider_failure=provider_failure_observation(error))
 if row['http_observations'] and row['http_observations'][-1]['status_code']>=400:row['failure_boundary']='PROVIDER_HTTP_REJECTION'
 elif row['provider_failure']:row['failure_boundary']='TYPED_PROVIDER_FAILURE'
 elif any(x['stage']=='provider_response_accepted' for x in row['stages']):row['failure_boundary']='OUTPUT_OR_RESPONSE_CONTRACT'
 else:row['failure_boundary']='LOCAL_PRE_REQUEST_OR_UNKNOWN'
 row['stable_local_code']=machine(str(error),120) if not row['provider_failure'] else None
row.update(ended_at_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-clock,
 transport_recovery_stages=sum(s['stage']=='provider_transport_recovery' for s in row['stages']),
 credential_or_raw_provider_body_output=False,qualification_claim='PROVIDER_DIAGNOSTIC_ONLY_NOT_REAL_G0_PASS')
OUT.write_text(json.dumps(row,indent=2)+'\n')
print(json.dumps({k:row.get(k) for k in ('result','failure_boundary','exception_type','wall_seconds','logical_model_entries')}))