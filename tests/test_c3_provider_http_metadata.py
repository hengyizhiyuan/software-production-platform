"""Actual HTTP metadata on normalized failure, no live Provider requests."""
import httpx2
import pytest
from spg.infrastructure.model_runtime import DeepSeekResponsesModelAdapter,ModelProviderError,ModelFailureKind
from spg.domain.model_runtime import ModelProfile,ModelPurpose,ModelProvider
from spg.providers.fulfillment_candidate import provider_failure_observation
PROFILE=ModelProfile(ModelPurpose.STEERING_SEMANTIC,ModelProvider.DEEPSEEK,'test-model','low',30,512)
@pytest.mark.parametrize('status,kind,retryable',[(401,ModelFailureKind.AUTHENTICATION,False),(402,ModelFailureKind.BALANCE_OR_QUOTA,False),(429,ModelFailureKind.CAPACITY_OR_RATE_LIMIT,True),(422,ModelFailureKind.INVALID_MODEL_OR_REQUEST,False),(503,ModelFailureKind.CAPACITY_OR_RATE_LIMIT,True)])
def test_actual_http_status_code_and_request_identity_survive_safe_failure_projection(status,kind,retryable):
 calls=[]
 def handler(request):
  calls.append(request)
  return httpx2.Response(status,headers={'x-request-id':'req-stable-1'},json={'error':{'code':'contract_rejected','message':'arbitrary provider prose test-key'}})
 adapter=DeepSeekResponsesModelAdapter(api_key=lambda:'test-key',base_url='https://diagnostic.invalid',client=httpx2.Client(base_url='https://diagnostic.invalid',transport=httpx2.MockTransport(handler)))
 with pytest.raises(ModelProviderError) as raised:
  adapter.generate(profile=PROFILE,instructions='synthetic',input_text='no Work data',output_schema={'type':'object'})
 failure=raised.value
 assert failure.kind is kind and failure.retryable is retryable
 assert failure.provider_status==str(status) and failure.termination_reason=='contract_rejected' and failure.request_id=='req-stable-1'
 observation=provider_failure_observation(failure)
 assert observation['provider_failure']['provider_status']==str(status)
 assert 'arbitrary provider prose' not in str(observation) and 'test-key' not in str(observation)
 assert observation['transport_retry_count'] is None and observation['usage']['total_tokens'] is None
 assert len(calls)==1
@pytest.mark.parametrize('code,request_id', [('line\nsecret','bad/request'),('x'*121,'x'*201),('test-key','test-key'),({'nested':'raw'},'bad query?secret')])
def test_rejection_metadata_does_not_admit_prose_secret_or_unbounded_fields(code,request_id):
 def handler(request):return httpx2.Response(400,headers={'x-request-id':request_id.replace('\n',' ')},json={'error':{'code':code}})
 adapter=DeepSeekResponsesModelAdapter(api_key=lambda:'test-key',base_url='https://diagnostic.invalid',client=httpx2.Client(base_url='https://diagnostic.invalid',transport=httpx2.MockTransport(handler)))
 with pytest.raises(ModelProviderError) as raised:adapter.generate(profile=PROFILE,instructions='x',input_text='y',output_schema={'type':'object'})
 assert raised.value.provider_status=='400'
 assert raised.value.termination_reason is None and raised.value.request_id is None

def terminal_failure(usage, *, replay=False):
 import json
 requests=[]
 def handler(request):
  requests.append(request)
  if replay and len(requests)==1:
   raise httpx2.RemoteProtocolError('controlled pre-response transport failure')
  terminal={'id':'request-terminal-failure','status':'incomplete','incomplete_details':{'reason':'max_output_tokens'},'usage':usage}
  body='data: '+json.dumps({'type':'response.incomplete','response':terminal})+'\n\n'
  return httpx2.Response(200,text=body)
 adapter=DeepSeekResponsesModelAdapter(api_key=lambda:'test-key',base_url='https://diagnostic.invalid',client=httpx2.Client(base_url='https://diagnostic.invalid',transport=httpx2.MockTransport(handler)))
 with pytest.raises(ModelProviderError) as raised:
  adapter.generate(profile=PROFILE,instructions='synthetic',input_text='no Work data',output_schema={'type':'object'})
 return raised.value,requests


def test_terminal_failure_retains_actual_numeric_usage_and_zero_transport_replay():
 error,requests=terminal_failure({'input_tokens':10,'output_tokens':4096,'total_tokens':4106,'output_tokens_details':{'reasoning_tokens':33}})
 observation=provider_failure_observation(error)
 assert error.kind is ModelFailureKind.INCOMPLETE_RESPONSE
 assert observation['usage']=={'input_tokens':10,'output_tokens':4096,'total_tokens':4106,'cached_tokens':None,'reasoning_tokens':33,'unknown':False}
 assert error.observed_usage.total_tokens==4106
 assert observation['transport_retry_count']==0 and len(requests)==1


def test_incomplete_after_existing_bounded_transport_replay_preserves_partial_unknown():
 error,requests=terminal_failure({'input_tokens':10},replay=True)
 observation=provider_failure_observation(error)
 assert len(requests)==2 and observation['transport_retry_count']==1
 assert observation['usage']['input_tokens']==10
 assert observation['usage']['output_tokens'] is None and observation['usage']['total_tokens'] is None
 assert observation['usage']['unknown'] is True


def test_legacy_and_invalid_numeric_failure_metadata_never_fabricate_usage():
 from spg.domain.model_runtime import ModelUsage
 error=ModelProviderError(ModelFailureKind.INCOMPLETE_RESPONSE,'raw test-key body',request_sent=True,usage_unknown=False,retryable=True)
 legacy=provider_failure_observation(error)
 assert legacy['usage']['unknown'] is True and legacy['transport_retry_count'] is None
 assert all(value is None for key,value in legacy['usage'].items() if key!='unknown')
 error.observed_usage=ModelUsage(input_tokens=True,output_tokens=-1,cached_tokens=0,total_tokens=0,unknown=False)
 error.transport_retry_count=True
 invalid=provider_failure_observation(error)
 assert invalid['usage']['input_tokens'] is None and invalid['usage']['output_tokens'] is None
 assert invalid['usage']['cached_tokens']==0 and invalid['usage']['total_tokens']==0 and invalid['usage']['unknown'] is True
 assert invalid['transport_retry_count'] is None and 'test-key' not in str(invalid)
