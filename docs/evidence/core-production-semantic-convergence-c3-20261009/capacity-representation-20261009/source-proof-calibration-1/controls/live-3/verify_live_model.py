"""One approved diagnostic using frozen Formation; no database or Owner writes."""
import sys
sys.dont_write_bytecode=True
import argparse,json,os,re,time
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import asdict,replace
from hashlib import sha256
from collections import Counter

SOURCE='89b1fbeab99ecc1a474a81ab64a787928c6441e9'
GUARDIAN='76c1e87a1b29d151f4ed949748e3298f2169c5b1'
ECF='5aa4f8833c359c15bd059eda5972aa3915bcc18c'
BASIS_SHA='9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c'
ATTESTATION_SHA='c6bc10e81d2e67747b4f5b1d0e0835b7a6a05325433c92c7b55b6c2a31dc838a'
INVENTORY='7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf'
PRODUCT_SOURCE='465038ded6cf4ba335a11577de76acb1dea55b76'

def now():return datetime.now(timezone.utc).isoformat()
def machine(value):
    return value if isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,200}',value) else None

def main(execute):
    from spg.config import Settings
    from spg.domain.interaction import WorkRealityRevision
    from spg.domain.intent_realization import GovernedSemanticIR
    from spg.domain.model_runtime import ModelPurpose,PurposeProfileRouter
    from spg.domain.governed_obligation import (canonical_fingerprint,fulfillment_candidate_fingerprint,
        fulfillment_components_fingerprint,fulfillment_component_id)
    from spg.application.governed_obligations import (fulfillment_inventory,fulfillment_capability_contracts,
        form_fulfillment_projection,validate_projection_candidate,projection_validation_feedback,_owner_source_preconditions)
    from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider,provider_failure_observation
    from spg.providers.verification_receipts import _safe_value
    from spg.infrastructure.model_runtime import httpx2
    out=Path('/c3-evidence/live-result.json');private=Path('/c3-private')
    assert not execute or not out.exists(),'DIAGNOSTIC_ALREADY_EXECUTED'
    clock=time.monotonic();active=None;provider=None;bindings=()
    row={'schema':'c3-feedback-convergence-live-v1','started_at_utc':now(),'application_source':SOURCE,
        'application_tree':'178bb8b19a265d3c7c0ccee6e42e0732de4a75b7','guardian_source':GUARDIAN,'ecf_source':ECF,
        'authorization':'Human 2026-10-10 instruction to complete source/Owner repair and real bounded qualification; bounded feedback convergence first',
        'logical_calls':0,'calls':[],'formation_attempts':[],'owner_observations':[],
        'new_work_created':False,'business_database_access':False,'historical_owner_mutated':False,
        'holdout_opened':False,'production_configuration_mutated':False,'c3_status':'PARTIAL',
        'formation_candidate_limit':2,'feedback_limit':1,'logical_call_limit':4,
        'transport_policy':'Frozen Runtime: at most one fresh connection replay only before any response event/output; no extra retry',
        'qualification_boundary':'Derived fulfillment formation and independent semantic review only; no Work/Candidate seal, content Verification, Guardian Assurance or Human authority',
        'private_artifacts':[],'result':'NOT_EXECUTED'}
    def write(path,value):
        if _safe_value(value)!=value:raise RuntimeError('DIAGNOSTIC_SAFE_VALUE_REJECTED')
        with path.open('w',encoding='utf-8') as stream:
            os.fchmod(stream.fileno(),0o600);json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
    def checkpoint():
        if execute:write(out,row)
    def save_private(name,value):
        path=private/name;write(path,value)
        observation={'name':name,'sha256':sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'public_content':False}
        row['private_artifacts']=[r for r in row['private_artifacts'] if r['name']!=name]+[observation]
    def summary(candidate):
        return {'candidate_fingerprint':fulfillment_candidate_fingerprint(candidate),
            'components_fingerprint':fulfillment_components_fingerprint(candidate),
            'routes':[{'route':i,'source_ref':r.source_ref,'capability':r.capability,
                'component_id':fulfillment_component_id(r,INVENTORY),'target_paths':list(r.target_paths),
                'work_constraint_indices':list(r.work_constraint_indices),'supporting_source_refs':list(r.supporting_source_refs),
                'basis':None if r.component_basis is None else {'start':r.component_basis.source_span_start,
                    'end':r.component_basis.source_span_end,'quote_sha256':sha256(r.component_basis.source_component_quote.encode()).hexdigest(),
                    'linked_fact_refs':list(r.component_basis.linked_fact_refs)}} for i,r in enumerate(candidate.routes)]}
    def public_feedback(text):
        data=json.loads(text)
        raw=data.pop('untrusted_previous_wire',None)
        if raw is not None:
            data['untrusted_previous_wire_sha256']=sha256(raw.encode()).hexdigest()
            data['untrusted_previous_wire_bytes']=len(raw.encode())
            data['original_feedback_sha256']=sha256(text.encode()).hexdigest()
            data['private_content_omitted']=True
        return data
    def review_summary(review):
        data=review.model_dump(mode='json')
        for key in ('source_results','component_results'):
            for entry in data.get(key) or []:
                if 'reason' in entry:entry['reason_sha256']=sha256(entry.pop('reason').encode()).hexdigest()
                if 'source_ref' in entry and entry['source_ref'] not in {s['source_ref'] for s in inventory['sources']}:
                    entry['invalid_source_ref_sha256']=sha256(entry.pop('source_ref').encode()).hexdigest()
        return data
    class Receipts(list):
        def append(self,entry):
            super().append(entry)
            if execute:
                save_private('formation-owner-observations.json',list(self))
                public={k:v for k,v in entry.items() if k in {'stage','receipt_id','attempt','recorded_at_utc',
                    'budget_limit','inventory_fingerprint','work_id','work_reality_revision_id','source_revision',
                    'failed_predicate','validation_passed','terminal','terminal_reason','failure_stage',
                    'candidate_fingerprint','raw_candidate_fingerprint','capabilities_fingerprint','components_fingerprint'}}
                if entry.get('validation_feedback') is not None:public['validation_feedback']=public_feedback(entry['validation_feedback'])
                if entry.get('candidate') is not None:
                    from spg.domain.governed_obligation import FulfillmentProjectionCandidate
                    public['candidate']=summary(FulfillmentProjectionCandidate.model_validate(entry['candidate']))
                if entry.get('locator_adjustments') is not None:public['locator_adjustments']=entry['locator_adjustments']
                row['owner_observations'].append(public);checkpoint()
    def begin(operation,attempt):
        call={'operation':operation,'formation_attempt':attempt,'started_at_utc':now(),'stages':[],
            'http_requests':[],'http_responses':[],'terminal_events':[],'usage':'UNKNOWN','provider_status':'UNKNOWN'}
        row['calls'].append(call);checkpoint();return call
    def callback(kind,original,**values):
        output_key='candidate_output' if kind=='formation' else 'review_output'
        text=values.get(output_key)
        active['output_observation']={k:v for k,v in values.items() if k!=output_key}
        if text is not None:
            if _safe_value(text)!=text:raise RuntimeError('DIAGNOSTIC_UNSAFE_PRIVATE_RESPONSE')
            path=private/(kind+'-'+str(active['formation_attempt'])+'-safe-wire.txt')
            assert not path.exists()
            with path.open('x',encoding='utf-8') as stream:os.fchmod(stream.fileno(),0o600);stream.write(text)
            row['private_artifacts'].append({'name':path.name,'sha256':sha256(path.read_bytes()).hexdigest(),
                'bytes':path.stat().st_size,'public_content':False})
        checkpoint()
        if original is not None:original(**values)
    try:
        basis=Path('/basis.json').read_bytes();assert sha256(basis).hexdigest()==BASIS_SHA
        attestation=Path('/qualified-imports.json').read_bytes();assert sha256(attestation).hexdigest()==ATTESTATION_SHA
        imported=json.loads(attestation)['actual_imports'];checked={}
        for owner in ('spg','guardian','ecf'):
            item=imported[owner]
            for path,digest in item['file_sha256'].items():
                assert sha256((Path(item['package_root'])/path).read_bytes()).hexdigest()==digest,'INSTALLED_OWNER_DRIFT'
            checked[owner]=len(item['file_sha256'])
        data=json.loads(basis)
        revision=WorkRealityRevision.model_validate(next(r for r in data['datasets']['work_reality_revisions']['rows'] if r['id']=='332a3a38-8719-580c-a1a2-c331ae14a5ae'))
        assessment=next(r for r in data['datasets']['interaction_assessments']['rows'] if r['id']==str(revision.source_assessment_id))
        ir=GovernedSemanticIR.model_validate(assessment['semantic_ir'])
        original_revision=canonical_fingerprint(revision.model_dump(mode='json'));original_ir=canonical_fingerprint(ir.model_dump(mode='json'))
        inventory=fulfillment_inventory(revision,ir,source_revision=PRODUCT_SOURCE,exact_target_paths=('index.html',))
        capabilities=fulfillment_capability_contracts()
        assert inventory['inventory_fingerprint']==INVENTORY and len(inventory['sources'])==26 and len(capabilities)==12
        row.update(inventory_fingerprint=INVENTORY,source_count=26,capability_count=12,
            capabilities_fingerprint=canonical_fingerprint(capabilities),basis_sha256=BASIS_SHA,
            installed_owner_hashes={'status':'PASS','counts':checked,'attestation_sha256':ATTESTATION_SHA},
            work_id=str(revision.work_id),work_reality_revision_id=str(revision.id))
        provider=ModelFulfillmentCandidateProvider.from_settings(Settings());assert provider is not None
        provider._fulfillment_receipts=Receipts();base_factory=provider.runtime_factory
        preflight_operation='formation'
        def runtime_factory():
            runtime=base_factory();base=runtime.profile(ModelPurpose.STEERING_SEMANTIC)
            assert base.reasoning_effort=='low','BASE_PROFILE_DRIFT'
            operation=active['operation'] if active is not None else preflight_operation
            profile=replace(base,reasoning_effort='none' if operation=='formation' else 'low')
            runtime.router=PurposeProfileRouter({ModelPurpose.STEERING_SEMANTIC:profile})
            adapter=runtime.registry.adapter(profile.provider)
            actual={'provider':profile.provider.value,'model':profile.model,'reasoning_effort':profile.reasoning_effort,
                'timeout_seconds':profile.timeout_seconds,'max_output_tokens':profile.max_output_tokens,'base_url':adapter.base_url}
            assert actual=={'provider':'deepseek','model':'deepseek-flash','reasoning_effort':'none' if operation=='formation' else 'low',
                'timeout_seconds':120,'max_output_tokens':16384,'base_url':'https://api.deepseek.com'},'MODEL_PROFILE_DRIFT'
            row.setdefault('profiles',{})[operation]=actual
            def request_hook(request):
                assert execute and active is not None
                observed={'bytes':len(request.content),'sha256':sha256(request.content).hexdigest()}
                assert observed==active['request_entity'],'HTTP_REQUEST_BODY_DRIFT'
                active['http_requests'].append({'at_utc':now(),**observed})
                assert len(active['http_requests'])<=2,'EXTRA_TRANSMISSION_FORBIDDEN'
                if len(active['http_requests'])==2:
                    assert sum(s['stage']=='provider_transport_recovery' for s in active['stages'])==1,'UNAUTHORIZED_TRANSPORT_REPLAY'
                checkpoint()
            def response_hook(response):
                observed={'at_utc':now(),'status_code':response.status_code,
                    'request_id':machine(response.headers.get('x-request-id') or response.headers.get('request-id'))}
                if response.status_code>=400:
                    try:
                        payload=json.loads(response.read());error=payload.get('error') if isinstance(payload,dict) else None
                        if isinstance(error,dict):observed.update(error_code=machine(error.get('code')),error_type=machine(error.get('type')))
                    except Exception as error:observed['error_body_parse_type']=type(error).__name__
                active['http_responses'].append(observed)
                original_lines=response.iter_lines
                def lines():
                    for line in original_lines():
                        if line.startswith('data:'):
                            try:event=json.loads(line[5:].strip())
                            except Exception:event={}
                            if isinstance(event,dict) and event.get('type') in {'response.completed','response.incomplete','response.failed'}:
                                terminal=event.get('response');terminal=terminal if isinstance(terminal,dict) else {}
                                usage=terminal.get('usage');usage=usage if isinstance(usage,dict) else {}
                                details=terminal.get('incomplete_details');details=details if isinstance(details,dict) else {}
                                def numeric(value):
                                    if type(value) is int and value>=0:return value
                                    if isinstance(value,dict):return {k:numeric(v) for k,v in value.items() if machine(k) and (type(v) is int or isinstance(v,dict))}
                                    return None
                                active['terminal_events'].append({'at_utc':now(),'event':machine(event.get('type')),
                                    'status':machine(terminal.get('status')),'response_id':machine(terminal.get('id')),
                                    'actual_usage_numeric_fields':numeric(usage),
                                    'termination_reason':machine(details.get('reason'))})
                                checkpoint()
                        yield line
                response.iter_lines=lines;checkpoint()
            def attach(client):
                client.event_hooks['request'].append(request_hook);client.event_hooks['response'].append(response_hook);return client
            original_new=adapter._new_client;adapter._new_client=lambda:attach(original_new());attach(adapter._client)
            original_generate=runtime.generate
            def generate(**kwargs):
                assert execute and active is not None
                assert kwargs.get('on_stage') is None and kwargs.get('on_output_delta') is None
                payload=adapter._payload(profile=profile,instructions=kwargs['instructions'],input_text=kwargs['input_text'],output_schema=kwargs['output_schema'])
                entity=httpx2.Request('POST','https://api.deepseek.com/responses',json=payload).content
                active['request_entity']={'bytes':len(entity),'sha256':sha256(entity).hexdigest()}
                row['logical_calls']+=1;assert row['logical_calls']<=4;checkpoint()
                def stage(name):
                    active['stages'].append({'stage':machine(name),'at_utc':now()});checkpoint()
                try:
                    result=original_generate(**kwargs,on_stage=stage)
                    active.update(provider_status='completed',provider_status_source='Frozen Runtime validates actual completed terminal',
                        request_id=machine(result.request_id),usage=asdict(result.usage),timing=asdict(result.timing),
                        transport_retry_count=result.retry_count,effective_model=machine(result.effective_model),
                        output_bytes=len(result.output_text.encode()),output_sha256=sha256(result.output_text.encode()).hexdigest())
                    checkpoint();return result
                except Exception as error:
                    failure=provider_failure_observation(error)
                    active.update(exception_type=type(error).__name__,failure_observation=failure)
                    if failure is not None:
                        active.update(usage=failure['usage'],provider_status=failure['provider_failure']['provider_status'] or 'UNKNOWN',
                            transport_retry_count=failure['transport_retry_count'])
                    checkpoint();raise
            runtime.generate=generate;return runtime
        provider.runtime_factory=runtime_factory
        for preflight_operation in ('formation','semantic_review'):
            runtime=runtime_factory();runtime.close()
        preconditions=_owner_source_preconditions(revision,ir,inventory,capabilities)
        row['owner_source_preconditions_fingerprint']=canonical_fingerprint(preconditions)
        row['preflight']='PASS_LOCAL_NO_HTTP';row['initial_wire_metadata']=provider.form_wire_metadata(inventory,capabilities,owner_preconditions=preconditions)
        if not execute:
            print(json.dumps({'preflight':'PASS','source':SOURCE,'inventory':INVENTORY,'sources':26,'capabilities':12,
                'profiles':row['profiles'],'installed_owner_hashes':checked,'wire_metadata':row['initial_wire_metadata'],'logical_calls':0}));return
        save_private('immutable-inventory.json',inventory);save_private('capability-contracts.json',capabilities)
        original_form=provider.form;original_review=provider.review
        def form(inv,caps,*,validation_feedback=None,receipt_callback=None,owner_preconditions=None):
            nonlocal active
            assert canonical_fingerprint(inv)==canonical_fingerprint(inventory) and caps==capabilities
            assert owner_preconditions==preconditions
            attempt=1+sum(c['operation']=='formation' for c in row['calls']);assert attempt<=2
            if attempt==1:assert validation_feedback is None
            else:
                prior=[r for r in provider._fulfillment_receipts if r['stage']=='CANDIDATE_VALIDATED'][-1]
                assert validation_feedback==prior['validation_feedback']
            active=begin('formation',attempt);active['feedback']=None if validation_feedback is None else public_feedback(validation_feedback)
            start=time.monotonic()
            try:
                candidate=original_form(inv,caps,validation_feedback=validation_feedback,owner_preconditions=owner_preconditions,
                    receipt_callback=lambda **v:callback('formation',receipt_callback,**v))
                save_private('formation-'+str(attempt)+'-expanded-candidate.json',candidate.model_dump(mode='json'))
                active['raw_candidate']=summary(candidate);return candidate
            except Exception as error:
                active['provider_or_output_exception_type']=type(error).__name__
                if hasattr(error,'errors'):
                    active['schema_errors']=[{'type':machine(e.get('type')),'location':list(e.get('loc',()))}
                        for e in error.errors(include_input=False,include_url=False,include_context=False)]
                raise
            finally:active.update(ended_at_utc=now(),wall_seconds=time.monotonic()-start);checkpoint()
        def review(inv,candidate,*,capabilities,receipt_callback=None):
            nonlocal active
            attempt=sum(c['operation']=='formation' for c in row['calls'])
            preliminary=validate_projection_candidate(candidate,revision,ir,inventory,allow_review_pending=True)
            assert not any(c['operation']=='semantic_review' and c['formation_attempt']==attempt for c in row['calls'])
            active=begin('semantic_review',attempt)
            active.update(pre_review_deterministic_status='PASS',candidate=summary(candidate),
                pre_review_binding_states=dict(Counter(b.state for b in preliminary)))
            save_private('formation-'+str(attempt)+'-located-candidate.json',candidate.model_dump(mode='json'))
            start=time.monotonic()
            try:
                result=original_review(inv,candidate,capabilities=capabilities,
                    receipt_callback=lambda **v:callback('review',receipt_callback,**v))
                save_private('review-'+str(attempt)+'-parsed-candidate.json',result.model_dump(mode='json'))
                active['semantic_review']=review_summary(result);return result
            except Exception as error:
                active['provider_or_output_exception_type']=type(error).__name__
                if hasattr(error,'errors'):
                    active['schema_errors']=[{'type':machine(e.get('type')),'location':list(e.get('loc',()))}
                        for e in error.errors(include_input=False,include_url=False,include_context=False)]
                raise
            finally:active.update(ended_at_utc=now(),wall_seconds=time.monotonic()-start);checkpoint()
        provider.form=form;provider.review=review
        checkpoint()
        bindings=form_fulfillment_projection(revision,ir,provider=provider,database=None,
            source_revision=PRODUCT_SOURCE,exact_target_paths=('index.html',))
        receipt=bindings[0].formation_receipt
        save_private('final-derived-projection.json',[b.model_dump(mode='json') for b in bindings])
        row.update(terminal_reason=receipt['terminal_reason'],binding_states=dict(Counter(b.state for b in bindings)),
            provider_call_count=receipt['provider_call_count'],observed_model_call_count=receipt['observed_model_call_count'],
            formation_attempt_count=receipt['attempt_count'],feedback_count=sum(c['operation']=='formation' and c.get('feedback') is not None for c in row['calls']),
            result='ISOLATED_FULFILLMENT_PLAN_QUALIFIED' if receipt['terminal_reason']=='VALIDATED_PROJECTION' else 'STOPPED')
        row['immutable_basis_in_memory']=original_revision==canonical_fingerprint(revision.model_dump(mode='json')) and original_ir==canonical_fingerprint(ir.model_dump(mode='json'))
        assert row['immutable_basis_in_memory'] and row['provider_call_count']==row['logical_calls']
        assert row['formation_attempt_count']<=2 and row['feedback_count']<=1 and row['logical_calls']<=4
    except Exception as error:
        row.update(result='HARNESS_OR_PREFLIGHT_STOP',exception_type=type(error).__name__,
            failed_predicate=(re.findall(r'\bOBLIGATION_[A-Z0-9_]+\b',str(error)) or [machine(str(error))])[0])
        if not execute:
            print(json.dumps({'preflight':'FAILED','exception_type':type(error).__name__,'code':row['failed_predicate']}));raise SystemExit(2)
    finally:
        if execute:
            usage={}
            for key in ('input_tokens','output_tokens','cached_tokens','reasoning_tokens','total_tokens'):
                values=[c.get('usage',{}).get(key) if isinstance(c.get('usage'),dict) else None for c in row['calls']]
                usage[key]=sum(values) if values and all(type(v) is int for v in values) else 'UNKNOWN'
            row.update(ended_at_utc=now(),wall_seconds=time.monotonic()-clock,observed_terminal_usage_sum=usage,
                http_transmissions=sum(len(c['http_requests']) for c in row['calls']),
                transport_recovery_stages=sum(s['stage']=='provider_transport_recovery' for c in row['calls'] for s in c['stages']),
                visible_json_token_count='UNKNOWN',monetary_cost='UNKNOWN',runtime_or_assurance_pass=False)
            row['all_transmission_usage']=usage if row['transport_recovery_stages']==0 else 'UNKNOWN: unobserved replayed transmission usage'
            checkpoint()
    print(json.dumps({k:row.get(k) for k in ('result','terminal_reason','logical_calls','formation_attempt_count','feedback_count','observed_terminal_usage_sum','wall_seconds')}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute-authorized-live',action='store_true')
    main(parser.parse_args().execute_authorized_live)
