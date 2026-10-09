"""Synthetic Provider transport probe, no Human/Work or historical content."""
import sys
sys.dont_write_bytecode=True
import json,time,re
from datetime import datetime,timezone
from pathlib import Path
from dataclasses import asdict
from spg.config import Settings
from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider,provider_failure_observation
from spg.domain.model_runtime import ModelPurpose
out=Path('/c3-evidence/provider-probe.json');assert not out.exists()
row={'schema':'c3-synthetic-provider-probe-v1','started_at_utc':datetime.now(timezone.utc).isoformat(),'historical_data_in_request':False,'work_created':False,'diagnostic_only':True,'stages':[],'http_observations':[],'numeric_usage':'UNKNOWN','logical_model_entries':0}
started=time.monotonic()
def stage(value):row['stages'].append({'stage':value,'at_utc':datetime.now(timezone.utc).isoformat()})
def machine(value):
 from spg.providers.verification_receipts import _safe_value
 return value if isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,120}',value) and _safe_value(value)==value else None
runtime=None
try:
 provider=ModelFulfillmentCandidateProvider.from_settings(Settings());assert provider is not None
 runtime=provider.runtime_factory();profile=runtime.profile(ModelPurpose.STEERING_SEMANTIC);adapter=runtime.registry.adapter(profile.provider)
 row['profile']={'provider':profile.provider.value,'model':profile.model,'reasoning_effort':profile.reasoning_effort,'timeout_seconds':profile.timeout_seconds,'max_output_tokens':profile.max_output_tokens,'base_url':adapter.base_url}
 def response_hook(response):
  observed={'status_code':response.status_code,'request_id':machine(response.headers.get('x-request-id') or response.headers.get('request-id'))}
  if response.status_code>=400:
   try:
    data=json.loads(response.read());error=data.get('error',{})
    if isinstance(error,dict):observed.update(error_code=machine(error.get('code')),error_type=machine(error.get('type')))
   except Exception as exc:observed['error_body_parse_type']=type(exc).__name__
  row['http_observations'].append(observed)
 adapter._client.event_hooks['response'].append(response_hook)
 original_new=adapter._new_client
 def new_client():
  client=original_new();client.event_hooks['response'].append(response_hook);return client
 adapter._new_client=new_client
 row['logical_model_entries']=1
 result=runtime.generate(purpose=ModelPurpose.STEERING_SEMANTIC,instructions='This is a transport diagnostic, not software production. Return JSON only with diagnostic equal to ready.',input_text='Synthetic transport probe. No Human or Work data is supplied.',output_schema={'type':'object','properties':{'diagnostic':{'type':'string','enum':['ready']}},'required':['diagnostic'],'additionalProperties':False},on_stage=stage)
 parsed=json.loads(result.output_text);assert parsed=={'diagnostic':'ready'}
 row.update(result='SYNTHETIC_RESPONSE_CONTRACT_OBSERVED',request_id=machine(result.request_id),numeric_usage=asdict(result.usage),timing=asdict(result.timing),transport_retry_count=result.retry_count)
except Exception as error:
 row.update(result='FAILED',exception_type=type(error).__name__,provider_failure=provider_failure_observation(error))
 row['failure_boundary']='PROVIDER_HTTP_REJECTION' if row['http_observations'] and row['http_observations'][-1]['status_code']>=400 else 'TYPED_PROVIDER_OR_LOCAL_FAILURE'
 if not row['provider_failure']:row['stable_local_code']=machine(str(error))
finally:
 if runtime is not None:runtime.close()
row.update(ended_at_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-started,qualification_claim='NOT_HISTORICAL_FORMATION_OR_REAL_G0_OR_HOLDOUT')
out.write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({'result':row['result'],'logical_model_entries':row['logical_model_entries']}))