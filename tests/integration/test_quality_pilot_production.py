"""Ten reviewed scenarios run through canonical owners on the existing isolated recipe DB.

Deterministic executors are explicit qualification adapters, not evidence of a live
coding model. C3 alone additionally calls real semantic/model and Aliyun providers.
"""
import asyncio
import json
import os
from pathlib import Path
from time import monotonic, sleep
from types import SimpleNamespace
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select

from test_work_delivery import clean_schema
import test_software_delivery as software
import test_product_managed_source_gitea as managed
import test_multi_pwu_runtime as multi
from spg.config import Settings
from spg.infrastructure.persistence.product_schema import product_works

pytestmark = pytest.mark.postgresql


def receipt(**facts):
    destination = os.environ.get('WATT_QUALITY_PRODUCT_EVIDENCE_FILE')
    if destination:
        Path(destination).write_text(json.dumps(facts, default=str))


def case_material():
    path = os.environ.get('WATT_QUALITY_CASE_FILE')
    if not path:
        pytest.skip('Run this sealed/live scenario through its reviewed Campaign recipe')
    return json.loads(Path(path).read_text())


def test_pilot_greenfield(postgres_database, tmp_path, live_gitea):
    from spg.application.product_assets import ProductAssetService
    product=ProductAssetService(postgres_database).create('human:test','Greenfield Web Pilot')
    service,wid,delivery,_=software.produce(postgres_database,tmp_path,user_repository=False,set_delivery_target=False,product_id=UUID(product['id']))
    assert service.get_work_result(wid).trusted_result
    manifest=delivery.publish(wid)
    assert manifest.software and set(software.SOURCE)<=set(a.path for a in manifest.artifacts)
    receipt(product_outcome='QUALIFIED_WEB_CANDIDATE', expected_outcome='QUALIFIED_WEB_CANDIDATE',
        executor='reviewed-deterministic', semantic_provider='qualification-fixture')


@pytest.fixture
def live_gitea(postgres_database, monkeypatch, tmp_path):
    yield from managed.managed_source_reality.__wrapped__(postgres_database, monkeypatch, tmp_path)


def test_pilot_brownfield(postgres_database, tmp_path, monkeypatch, live_gitea):
    managed.test_brownfield_import_acceptance_next_work_and_provider_fail_closed(postgres_database, tmp_path, monkeypatch)
    receipt(product_outcome='EXACT_BROWNFIELD_CANDIDATE', expected_outcome='EXACT_BROWNFIELD_CANDIDATE',
        source_provider='real-gitea', executor='reviewed-deterministic')


def test_pilot_repository_only(postgres_database, tmp_path, monkeypatch, live_gitea):
    material = case_material()['private_material']
    from spg.application.product_assets import ProductAssetService
    from spg.providers.external_search import AliyunOpenSearchWebProvider, GitHubPublicSearchProvider
    calls=[]
    def unexpected(*args, **kwargs):
        calls.append(True)
        raise AssertionError('Repository-only obligation must not call external Search')
    monkeypatch.setattr(AliyunOpenSearchWebProvider, 'search', unexpected)
    monkeypatch.setattr(GitHubPublicSearchProvider, 'search', unexpected)
    product=ProductAssetService(postgres_database).create('human:quality','Repository-only sealed Product')
    wid,basis,manifest,after=managed._run_and_accept(postgres_database,UUID(product['id']),
        '# '+material['replacement']+'\n',tmp_path)
    assert manifest.repository_revision != basis['source_revision']
    assert calls == [] and material['expected_search_calls']==0
    receipt(product_outcome='REPOSITORY_ONLY_QUALIFIED', expected_outcome='SEALED', search_calls=0,
        work_id=wid, product_id=product['id'], source_revision=basis['source_revision'], candidate_revision=manifest.repository_revision)


def test_pilot_live_search(postgres_database, tmp_path, monkeypatch):
    case_material()
    from spg.application.bootstrap import bootstrap
    from spg.domain.interaction import InteractionTurnStatus
    from spg.providers.external_search import AliyunOpenSearchWebProvider
    from spg.domain.engineering_semantics import SemanticReferenceRole
    s=Settings(database_url=os.environ['SPG_TEST_DATABASE_URL'],admin_enabled=False,owner_runtime_mode='OFF',managed_source_provider='disabled')
    assert s.web_search_provider == 'aliyun-opensearch' and s.aliyun_opensearch_api_key
    observed=[];original=AliyunOpenSearchWebProvider.search
    def real_search(self,*args,**kwargs):
        result=original(self,*args,**kwargs)
        observed.extend(result)
        return result
    monkeypatch.setattr(AliyunOpenSearchWebProvider,'search',real_search)
    interaction=bootstrap(s).interaction(postgres_database)
    human='制作一个展示 Python 当前稳定版本官方发布信息的静态页面。在生产前请真实 Web Search 搜索 Python 当前稳定版本的官方发布页面，提供检索来源和版本依据。https://www.python.org/downloads/ 只是外部参考资料，不是我的项目仓库。请直接 Fetch 此官方页面以确认当前版本。先完成调研，不开始开发。'
    try:
        item=interaction.create_interaction(human_identity='human:quality')
        turn=interaction.submit_turn(item.id,human,human_identity='human:quality')
        deadline=monotonic()+180
        while monotonic()<deadline:
            settled=interaction.get_turn(turn.id)
            if settled.status in {InteractionTurnStatus.COMPLETED,InteractionTurnStatus.FAILED}:break
            sleep(.3)
        assert settled.status is InteractionTurnStatus.COMPLETED, settled.failure_message
        assert observed and all(e.provider=='aliyun-opensearch' for e in observed)
        assert any(e.metadata.get('provider_request_id') for e in observed)
        facts=interaction.get_shared_understanding(item.id)
        ir=facts.latest_assessment.semantic_ir
        assert ir.repository_source is None
        # Canonical compiler arguments declare reference roles; never infer it from URL shape.
        refs=[arg for arg in ir.semantic_fact_candidates if arg.reference_role is not None]
        assert refs and all(arg.reference_role==SemanticReferenceRole.EXTERNAL_REFERENCE for arg in refs)
        events=interaction.response_events(turn.id)
        assert any(e.event_type.value=='SEARCH_EVIDENCE' for e in events)
        answer=facts.conversation_messages[-1].content
        assert any(e.url in answer for e in observed)
        official=next(e for e in observed if 'python.org' in e.url)
        # Production content derives from observed live evidence, not a fixture answer.
        import html
        from spg.providers.external_search import BoundedPublicHttp, inspect_web_resource
        fetched=inspect_web_resource(BoundedPublicHttp(),official)
        import re
        versions=re.findall(r'Python (3\.\d+\.\d+)\b',fetched.inspected_content)
        assert versions, 'Official fetched reference must provide actual version evidence'
        version=max(versions,key=lambda v:tuple(map(int,v.split('.'))))
        # Persist research provenance even when subsequent production fails.
        research_evidence=dict(interaction_id=item.id,turn_id=turn.id,semantic_ir_id=ir.id,
            reference_role='EXTERNAL_REFERENCE',provider='aliyun-opensearch',official_version=version,
            fetched_reference_fingerprint=__import__('hashlib').sha256(fetched.inspected_content.encode()).hexdigest(),
            sources=[{'url':e.url,'title':e.title,'provider_request_id':e.metadata.get('provider_request_id')} for e in observed],
            semantic_provider=s.wic_provider_adapter,executor='reviewed-deterministic')
        receipt(product_outcome='RESEARCH_QUALIFIED',expected_outcome='LIVE_REFERENCES_IN_QUALIFIED_WEB_CANDIDATE',**research_evidence)
        sources={'index.html':'<!doctype html><html><body><h1>Python 官方版本信息 '+version+'</h1><a href="'+html.escape(official.url,quote=True)+'">'+html.escape(official.title)+'</a><p>'+html.escape(official.snippet)+'</p></body></html>\n',
            'tests/reference.test.cjs':'const {test}=require("node:test");const assert=require("node:assert/strict");const fs=require("node:fs");test("observed official release reference",()=>{const page=fs.readFileSync("index.html","utf8");assert(page.includes('+json.dumps(html.escape(official.url,quote=True))+'));assert(page.includes('+json.dumps(version)+'));});\n'}
        monkeypatch.setattr(software,'SOURCE',sources)
        objective='Produce a tested Python official release reference page from observed live evidence'
        class ReferenceIntent(software.SoftwareIntent):
            def interpret(self,basis):
                return super().interpret(basis).model_copy(update={'desired_outcome':objective})
        class ReferenceDesign(software.SoftwareDesign):
            def execute(self,input):
                result=super().execute(input)
                if result.proposed_production and input.approved_artifact_references:
                    result=result.model_copy(update={'proposed_production':result.proposed_production.model_copy(update={
                        'objective':objective,'verification_expectation':'Node tests prove the produced page contains the exact observed official URL and release version'})})
                return result
        service,wid,delivery,_=software.produce(postgres_database,tmp_path,user_repository=False,set_delivery_target=False,
            human_requirement='依据已检索的官方 Python 发布信息生成 index.html，显示真实来源链接：'+official.url+'；只读外部参考，不获取为项目仓库。',
            intent_capability=ReferenceIntent(),design_capability=ReferenceDesign(),
            design_content='# Official release reference page\n\nUse exact observed URL '+official.url+' and version '+version+'. Verify page content with Node.\n')
        result=service.get_work_result(wid)
        receipt(product_outcome=result.status.value,trusted_result=result.trusted_result,work_id=wid,
            expected_outcome='LIVE_REFERENCES_IN_QUALIFIED_WEB_CANDIDATE',**research_evidence)
        assert service.get_work_result(wid).trusted_result
        manifest=delivery.publish(wid)
        assert manifest.repository_revision
        receipt(product_outcome='LIVE_REFERENCES_IN_QUALIFIED_WEB_CANDIDATE',expected_outcome='LIVE_REFERENCES_IN_QUALIFIED_WEB_CANDIDATE',
            interaction_id=item.id,turn_id=turn.id,work_id=wid, candidate_revision=manifest.repository_revision,
            reference_role='EXTERNAL_REFERENCE',provider='aliyun-opensearch',
            official_version=version, fetched_reference_fingerprint=__import__('hashlib').sha256(fetched.inspected_content.encode()).hexdigest(),
            sources=[{'url':e.url,'title':e.title,'provider_request_id':e.metadata.get('provider_request_id')} for e in observed],
            semantic_provider=s.wic_provider_adapter,executor='reviewed-deterministic')
    finally:
        interaction.shutdown()


def test_pilot_dependency(postgres_database, tmp_path):
    multi.test_three_serial_pwus_inherit_exact_verified_predecessor_baselines(postgres_database,tmp_path)
    receipt(product_outcome='QUALIFIED_SERIAL_LINEAGE',expected_outcome='QUALIFIED_SERIAL_LINEAGE')


def test_pilot_join(postgres_database, tmp_path, monkeypatch):
    multi.test_real_parallel_branch_outputs_join_only_after_verification(postgres_database,tmp_path,monkeypatch,'pwu:1')
    receipt(product_outcome='EXPLICIT_VERIFIED_JOIN',expected_outcome='EXPLICIT_VERIFIED_JOIN')


def test_pilot_negative_verification(postgres_database, tmp_path):
    software.test_failing_behavior_test_cannot_publish_software(postgres_database,tmp_path)
    receipt(product_outcome='VERIFICATION_FAILED',expected_outcome='VERIFICATION_FAILED',
        publication_blocked=True, oracle='Node boundary test: q < threshold, deliberately produced q <= threshold',
        quality_case_outcome='PASS_IF_FAILURE_OBSERVED')


def test_pilot_guardian(postgres_database, tmp_path, monkeypatch):
    software.test_required_guardian_static_review_precedes_explicit_acceptance(postgres_database,tmp_path)
    receipt(product_outcome='GUARDIAN_GATED_CANDIDATE',expected_outcome='GUARDIAN_GATED_CANDIDATE',
        independent_oracle='executable Web behavior and explicit authorization boundary')


def test_pilot_continuous_work(postgres_database, tmp_path, live_gitea):
    from spg.application.interaction import WorkInteractionService
    from test_workspace_independent_work import TypedIntent
    from spg.domain.interaction import WorkTransitionChoice
    from spg.application.product_assets import ProductAssetService
    p=ProductAssetService(postgres_database).create('human:test','Continuous Product Pilot')
    service,a,delivery,_=software.produce(postgres_database,tmp_path,authorize_candidate=False,set_delivery_target=False,user_repository=False,product_id=UUID(p['id']))
    context=delivery.candidate_context(a)
    assert context and context['authorization_pending']
    with postgres_database.unit_of_work() as u:
        before=dict(u.session.execute(select(product_works).where(product_works.c.id==a)).mappings().one())
        product_id=before['product_id'];assert product_id
        # Current Work owns its canonical originating Interaction.
        from spg.infrastructure.persistence.product_schema import product_interactions
        iid=u.session.scalar(select(product_interactions.c.id).where(product_interactions.c.current_work_id==a));assert iid
    class GovernedProductIntent(TypedIntent):
        def interpret(self,basis):
            from spg.domain.intent_realization import SemanticProvenance, SemanticOrigin
            candidate=super().interpret(basis)
            provenance=SemanticProvenance(origin=SemanticOrigin.REPOSITORY_OBSERVED,evidence_reference=source_ref)
            items=tuple(x.model_copy(update={'provenance':(provenance,), 'observed_facts':{k:v.model_copy(update={'provenance':provenance}) for k,v in x.observed_facts.items()}}) if x.item_id=='product-fact' else x for x in candidate.semantic_intent.items)
            return candidate.model_copy(update={'semantic_intent':candidate.semantic_intent.model_copy(update={'items':items})})
    interaction=WorkInteractionService(postgres_database,capability=GovernedProductIntent(True,True,str(product_id)))
    source_ref=next(o.evidence_references[0] for o in interaction._semantic_owner_observations(iid) if o.owner=='product-managed-source')
    received=interaction.append_and_assess(iid,'独立新 Work：为同一个 Product 创建 contact.html 联系页面。保留现有 Candidate 的人工决定，不接受或拒绝它。',human_identity='human:test')
    assert received.latest_work_transition.choice is WorkTransitionChoice.START_NEW_WORK
    b=service.admit_interaction_work(iid,assessment_id=received.latest_assessment.id,
        basis_fingerprint=received.latest_assessment.basis_fingerprint,authority_identity='human:test')
    assert b.work_id!=a and b.desired_outcome=='Create contact.html'
    with postgres_database.unit_of_work() as u:
        after=dict(u.session.execute(select(product_works).where(product_works.c.id==a)).mappings().one())
        brow=dict(u.session.execute(select(product_works).where(product_works.c.id==b.work_id)).mappings().one())
    assert after==before and brow['product_id']==product_id
    assert delivery.candidate_context(a)['candidate_fingerprint']==context['candidate_fingerprint']
    receipt(product_outcome='INDEPENDENT_WORK_ADMITTED',expected_outcome='INDEPENDENT_WORK_ADMITTED',
        product_id=product_id,work_a=a,work_b=b.work_id,pending_candidate_fingerprint=context['candidate_fingerprint'],prior_work_unchanged=True)


def test_pilot_independent_roots(postgres_database, tmp_path):
    """Real DAG/queue/lease/worker over two bounded independent repository outputs."""
    from spg.application.executor_runtime import NativeExecutorRuntimeService
    from spg.infrastructure.executor_runtime.worker import NativeExecutionWorker
    from spg.infrastructure.executor_runtime.runtime_ports import DurableCheckpointPort
    from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
    from spg.domain.native_execution import KernelRunResult, KernelCheckpoint, WorkingPlan, ExecutionMode, AttemptTerminalOutcome
    from test_native_executor_runtime import _admission, _offer
    repository=tmp_path/'independent';repository.mkdir()
    for args in [('init','-b','main'),('config','user.name','Quality Pilot'),('config','user.email','pilot@example.invalid')]:multi._git(repository,*args)
    (repository/'README.md').write_text('Two independent documentation obligations\n')
    multi._git(repository,'add','.');multi._git(repository,'commit','-m','Exact accepted baseline')
    runtime=multi.RuntimeService(postgres_database)
    baseline=runtime.bootstrap_trusted_baseline(multi.BootstrapRequest(repository_path=repository,repository_identity=str(repository),repository_ref='refs/heads/main',authority_identity='human:quality')).snapshot
    paths=('docs/auth.md','docs/billing.md')
    planning_work_id=uuid4()
    plan=multi.RuleBasedProductionPlanner().propose(multi.ProductionPlanningRequest(work_id=planning_work_id,admitted_requirement='Produce independent auth and billing guides',desired_outcome='Both guides qualified',production_objective='Two independent guides',artifact_targets=tuple(multi.ProductionPlanArtifactTarget(path=p,operation=multi.PlannedArtifactOperation.CREATE) for p in paths),verification_expectation='Both files exist',engineering_scope_summary='one exact repository',engineering_resource_id=uuid4(),repository_identity=str(repository),source_baseline_id=baseline.id,source_revision=baseline.repository_revision))
    spine=runtime.create_initial_runtime_spine(multi.InitialRunRequest(intent_ref='quality:pilot:independent',goal='Both guides qualified',production_horizon=multi.ProductionHorizon.DOCUMENTATION,initial_work_unit_objective='Two independent guides',completion_contract=multi.CompletionContract(required_outputs=paths,required_changes=paths,verification_obligations=('Both files exist',),production_plan=plan)))
    preparation=multi.PreparationService(postgres_database)
    execution=multi.ExecutionService(postgres_database,preparation=preparation)
    completion=multi.CompletionService(postgres_database,observer=execution.observer)
    verification=multi.VerificationService(postgres_database,observer=execution.observer)
    scheduler=NativeExecutorRuntimeService(postgres_database)
    offer=_offer().model_copy(update={'worker_id':'quality-independent-'+str(uuid4()),'max_concurrency':1})
    scheduler.register_worker(offer);scheduler.heartbeat_worker(offer)
    units=[]
    for index,path in enumerate(paths,1):
        with postgres_database.unit_of_work() as u:unit=multi.RuntimeStore(u.session).work_unit_for_node(spine.plan_revision.id,'pwu:'+str(index))
        assert unit.source_baseline_id==baseline.id
        attempt=runtime.create_initial_attempt(unit.id)
        package=preparation.assemble_context_package(unit.id,repository,multi.ContextPackageRequest(artifacts=(multi.ContextArtifactSelection(semantic_role=multi.ContextSemanticRole.PROJECT_CONTEXT,repository_relative_path='README.md'),)))
        prepared=preparation.prepare_attempt(attempt.id,package.id,multi.ExecutorBinding(binding_ref='quality:independent',capability_identity='capability:executor',profile_identity='profile:local-fvs'),repository,tmp_path/'workspaces')
        admission=_admission(postgres_database,repository,spine_attempt=(SimpleNamespace(work_unit=unit),attempt),work_id=planning_work_id,contract_payload={'objective':unit.objective,'verification':['Both files exist']})
        member=admission.binding.source_vector.members[0].model_copy(update={'write_scope':(path,)})
        from spg.domain.native_execution import SourceVector
        vector=SourceVector(members=(member,))
        workspace=admission.binding.workspace.model_copy(update={'source_vector_digest':vector.digest or '', 'mounts':tuple(m.model_copy(update={'write_scope':(path,), 'host_path':str(prepared.execution_request.workspace.workspace_path)}) for m in admission.binding.workspace.mounts)})
        binding=admission.binding.model_copy(update={'source_vector':vector,'workspace':workspace,'context_package_ref':str(package.id), 'materialized_input_digest':__import__('spg.domain.native_execution',fromlist=['canonical_digest']).canonical_digest(prepared.execution_request), 'capability_grants':tuple(g.model_copy(update={'scope':{'paths':[path]}}) for g in admission.binding.capability_grants)})
        admission=admission.model_copy(update={'binding':binding,'materialization_path':str(prepared.execution_request.workspace.workspace_path)})
        scheduler.admit(admission)
        units.append((unit,attempt,admission,path))
    assert all(scheduler.execution_request(x[1].id).status.value=='QUEUED' for x in units)
    outcomes=[]
    class Kernel:
        def __init__(self,grant):self.grant=grant
        async def run(self,**kwargs):
            grant=self.grant
            unit,attempt,admission,path=next(x for x in units if x[1].id==grant.allocation.attempt_id)
            assert scheduler.allocate(offer) is None # second root stays capacity-waiting
            dispatched=execution.dispatch_and_observe(attempt.id,multi.DeterministicTestExecutor(multi.DeterministicExecutionSpecification(operations=(multi.DeterministicFileOperation(operation=multi.DeterministicFileOperationType.CREATE,repository_relative_path=path,content=path+'\n'),),reported_outcome=multi.ProviderReportedOutcome.SUCCESS)))
            evaluated=completion.evaluate_observation(dispatched.observation.id)
            candidate=verification.create_proposed_snapshot(evaluated.evaluation.id)
            verification.verify_obligation(candidate.id,'Both files exist',multi.DeterministicVerificationProvider({'Both files exist':multi.VerificationResultValue.PASS}))
            assert verification.evaluate_admissibility(candidate.id).admissibility.outcome.value=='ADMISSIBLE'
            output=runtime.publish_verified_pwu_output(unit.id,candidate.id);outcomes.append(output)
            checkpoint=await DurableCheckpointPort(postgres_database,ContentAddressedStorage(tmp_path/'checkpoints'),attempt_id=attempt.id,session_id=admission.binding.session_id,worker_epoch=grant.allocation.lease_epoch).commit(KernelCheckpoint(step_sequence=1,working_plan=WorkingPlan(version=1,objective_reference=str(admission.contract.id),chosen_approach='reviewed deterministic bounded change',approach_rationale='exact qualification obligation'),tool_results=(),source_vector_digest=admission.binding.source_vector.digest or '',result_claim={'output_vector':{'files':[path]},'evidence_ids':[]}))
            return KernelRunResult(runtime_mode=ExecutionMode.FINISHED,terminal_outcome=AttemptTerminalOutcome.RESULT_READY,final_checkpoint_id=checkpoint.id,step_count=1,inference_submissions=0,tool_effects=1,summary='Verified exact independent output',result_claim={'output_vector':{'files':[path]},'evidence_ids':[]})
    worker=NativeExecutionWorker(scheduler,lambda grant:Kernel(grant))
    assert asyncio.run(worker.run_once(offer))
    assert asyncio.run(worker.run_once(offer))
    assert len(outcomes)==2
    assert all(x.source_baseline_id==baseline.id for x in outcomes)
    receipt(product_outcome='TWO_INDEPENDENT_QUALIFIED_OUTPUTS',expected_outcome='TWO_INDEPENDENT_QUALIFIED_OUTPUTS',
        plan_revision_id=spine.plan_revision.id,pwu_ids=[x[0].id for x in units],executions=[x[1].id for x in units],
        worker_id=offer.worker_id,max_concurrency=1,parallel_ready=True,actual_concurrency=1,executor='reviewed-deterministic-qualification-kernel')
