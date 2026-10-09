"""Reusable, read-only production history assembled from owner records.

Quality observations use saved qualification facts, never today's Product state.
Live entity lookup is separately labelled. Missing observation is not a zero or PASS.
"""
from __future__ import annotations

from datetime import datetime, UTC
from hashlib import sha256
import json
from pathlib import Path
import re
from uuid import UUID

from sqlalchemy import select, or_
from spg.infrastructure.performance import timed
from fastapi.encoders import jsonable_encoder

from spg.infrastructure.persistence import metadata
from spg.evaluation.contracts import QualityError
from spg.evaluation.admin_projection import OWNER_NAMES, outcome_projection

PRIVATE_KEYS = {'reasoning', 'reasoning_content', 'chain_of_thought', 'thinking', 'analysis',
    'access_token', 'refresh_token', 'api_key', 'secret', 'password', 'authorization',
    'security_token', 'credential', 'credentials', 'operator_token', 'lease_token'}
TABLE_OWNERS = {
    'product_works':'WORK', 'execution_dispatches':'EXECUTION', 'provider_execution_reports':'EXECUTION',
    'completion_evaluations':'VERIFICATION', 'production_admissibility_records':'VERIFICATION',
    'proposed_repository_snapshots':'CANDIDATE', 'repository_integration_effects':'GOVERNANCE', 'interaction_assessments':'WIC', 'semantic_step_results':'STEERING',
    'interaction_messages':'WIC', 'interaction_records':'WIC', 'interaction_turns':'WIC',
    'interaction_response_events':'WIC', 'interaction_turn_realizations':'IRK',
    'interaction_turn_obligations':'IRK', 'work_reality_revisions':'WORK',
    'production_snapshots':'SOURCE', 'work_source_bases':'SOURCE', 'steering_steps':'STEERING', 'steering_decisions':'STEERING',
    'steering_history_events':'STEERING', 'plan_revisions':'PLANNING',
    'production_work_units':'PWU', 'context_packages':'ECF', 'pwu_contract_versions':'ECF',
    'executor_queue':'EXECUTION', 'execution_allocations':'EXECUTION', 'execution_attempts':'EXECUTION',
    'execution_steps':'EXECUTION', 'execution_events':'EXECUTION', 'execution_evidence':'EXECUTION',
    'transition_history':'EXECUTION', 'self_refine_events':'EXECUTION', 'checkpoint_bundles':'EXECUTION',
    'execution_effects':'EXECUTION', 'effect_receipts':'EXECUTION',
    'verification_records':'VERIFICATION', 'baseline_candidates':'CANDIDATE',
    'work_product_references':'CANDIDATE', 'repository_observations':'CANDIDATE',
    'human_authorizations':'GOVERNANCE', 'governance_records':'GOVERNANCE',
    'work_delivery_manifests':'GOVERNANCE', 'work_delivery_acceptances':'GOVERNANCE',
    'product_source_versions':'GOVERNANCE', 'cloud_deployments':'DEPLOYMENT',
    'cloud_operation_receipts':'DEPLOYMENT'}
EVENT_LABELS = {'INFERENCE':'调用模型','TOOL':'执行工具','ADMITTED':'准入',
    'QUEUED':'进入队列','ALLOCATED':'获得执行容量','EXECUTING':'进入执行','COMPLETED':'执行完成',
    'FAILED':'执行失败','CANCELLED':'取消','STARTED':'开始执行','PAUSED':'暂停',
    'INTERRUPTED':'中断','RESUMED':'恢复执行','STOPPED':'停止','REQUEUED':'重新排队',
    'RUNNING':'运行中','VERIFYING':'开始验证','VERIFIED':'验证完成',
    'RESULT_READY':'产物准备就绪','SESSION_OPENED':'建立执行会话',
    'CHECKPOINT_SAVED':'保存恢复点','RECOVERY_REQUIRED':'需要恢复',
    'SELF_REFINE':'自修复','SATISFIED':'生产义务已满足','SEALED':'封存候选成果'}
EVENT_LABELS.update({'ExecutionRequestCreated':'形成执行请求','NativeExecutionQueued':'进入队列',
    'ExecutionCapacityAllocated':'获得执行容量','NativeExecutionStarted':'开始执行',
    'ExecutionWorkspacePrepared':'准备独立工作区','ExecutionResultObserved':'观测执行产物',
    'ExecutionCapacityReleased':'释放执行容量','NativeExecutionWorkerReturned':'Worker 返回结果',
    'ExecutionFailed':'执行失败','ExecutionWorkerCompleted':'执行完成','NativeExecutionPaused':'暂停执行',
    'NativeExecutionResumed':'恢复执行','NativeExecutionCancelled':'取消执行',
    'ExecutionRecoveryRequired':'需要恢复','ExecutionRequeued':'恢复后重新排队'})


def safe(value, _memo=None):
    """Do not expose credentials or hidden model reasoning, even in diagnostic mode."""
    if _memo is None:
        _memo = {}
    if isinstance(value, (dict, list, tuple)) and id(value) in _memo:
        return _memo[id(value)]
    if isinstance(value, dict):
        result = {k:safe(v, _memo) for k,v in value.items() if str(k).lower() not in PRIVATE_KEYS
            and not any(s in str(k).lower() for s in ('chain_of_thought', 'secret_key', 'accesskeysecret'))}
        _memo[id(value)] = result
        return result
    if isinstance(value, (list, tuple)):
        result = [safe(v, _memo) for v in value]
        _memo[id(value)] = result
        return result
    if isinstance(value, str):
        value = re.sub(r'(?i)(Bearer\s+)[A-Za-z0-9._\-]+', r'\1[已脱敏]', value)
        value = re.sub(r'(?i)((?:password|api[_-]?key|access[_-]?token|secret|credential)\s*[=:]\s*)[^\s,;]+', r'\1[已脱敏]', value)
        return re.sub(r'([a-z]+(?:\+[a-z]+)?://)[^\s/@]+:[^\s/@]+@', r'\1[已脱敏]@', value)
    return jsonable_encoder(value)


def _time(row):
    return row.get('occurred_at') or row.get('created_at') or row.get('observed_at') or row.get('issued_at') or row.get('started_at') or row.get('assigned_at') or row.get('sealed_at') or row.get('assessed_at')


def _walk(value, key):
    if isinstance(value, dict):
        if key in value:
            yield value[key]
        for v in value.values():
            yield from _walk(v, key)
    elif isinstance(value, list):
        for v in value:
            yield from _walk(v, key)


@timed("filesystem")
def qualification_artifact(settings, reference):
    """Only checksum-bound qualification JSON beneath the configured owner root."""
    match = re.fullmatch(r'evidence:(.+):sha256:([a-f0-9]{64})', reference)
    if not match:
        return None
    root = (settings.owner_runtime_store_root / 'qualifications').resolve()
    path = Path(match[1]).resolve()
    if not path.is_relative_to(root) or path.suffix != '.json':
        return None
    try:
        if path.stat().st_size > 10_000_000:
            return None
        data = path.read_bytes()
        if sha256(data).hexdigest() != match[2]:
            return None
        return path, json.loads(data)
    except (OSError, ValueError):
        return None


def compact_trace_tables(tables):
    """Summary keeps identities, chronology and owner outcomes, omits raw bodies.

    Full governed evidence remains available via explicit retrieval. This never
    changes the stored snapshot or fills missing historical facts.
    """
    result = {}
    bulky = {'request_payload','result_payload','provider_response','payload','evidence',
        'context_facts','diagnostic_evidence','request','response','output','files', 'content'}
    for name, rows in tables.items():
        result[name] = []
        for row in rows:
            if name in {'interaction_turn_realizations','interaction_records','interaction_messages','production_work_units','pwu_contract_versions','plan_revisions'}:
                compact = dict(row)
            else:
                compact = {k:v for k,v in row.items() if k not in bulky}
            if name == 'execution_steps':
                request = row.get('request_payload') or {}
                compact['request_payload'] = {'objective':request.get('objective')}
                contexts = list(_walk(request, 'decision_context'))
                if contexts:
                    compact['request_payload']['decision_context'] = {'protected_obligations':[
                        {'context_class':o.get('context_class')} for c in contexts if isinstance(c,dict)
                        for o in c.get('protected_obligations',[])]}
                response = row.get('provider_response') or row.get('result_payload') or {}
                compact['result_payload'] = {k:v for k,v in response.items() if k in
                    {'provider_observation','usage','action','summary','status'}}
            result[name].append(compact)
    return result


@timed("projection")
def project_trace(tables, *, scene, purpose, first_input=None, case=None, basis=None,
                  owner_refs=(), guardian=(), browser=None, detail=True):
    """Both story and diagnostic modes consume this same historical fact set."""
    tables = safe(tables if detail else compact_trace_tables(tables))
    events = []
    for name, rows in tables.items():
        if name not in TABLE_OWNERS:
            continue
        for row in rows:
            kind = row.get('event_type') or row.get('to_condition') or row.get('kind') or name
            record_labels={'executor_queue':'进入队列','execution_allocations':'获得执行容量',
                'production_work_units':'建立生产单元','baseline_candidates':'封存候选成果',
                'execution_attempts':'建立执行尝试','self_refine_events':'自修复记录',
                'provider_execution_reports':'执行器报告生产结果','completion_evaluations':'核对生产义务',
                'steering_steps':'登记推进步骤','interaction_messages':'Human 可见交流',
                'interaction_records':'保存交流记录','work_source_bases':'绑定精确来源'}
            events.append({'timestamp':_time(row), 'owner':TABLE_OWNERS[name],
                'title':record_labels.get(name, EVENT_LABELS.get(kind, {'verification_records':'独立验证记录',
                    'self_refine_events':'自修复记录','steering_decisions':'推进决定',
                    'plan_revisions':'形成生产计划','interaction_turn_realizations':'意图已治理',
                    'execution_allocations':'分配执行容量','human_authorizations':'Human 授权',
                    'work_delivery_acceptances':'Human 验收'}.get(name, OWNER_NAMES.get(TABLE_OWNERS[name], '生产')+'记录'))),
                'state':('FAIL' if kind=='ExecutionFailed' else
                    {'SUCCESS':'PASS','FAILURE':'FAIL','NOT_PRODUCED':'BLOCKED'}.get(row.get('outcome'),row.get('outcome'))
                    if name in {'provider_execution_reports','completion_evaluations'} else
                    row.get('result') if name=='verification_records' else row.get('to_condition')),
                'pwu_id':row.get('pwu_id') or row.get('work_unit_id') or (row.get('id') if name=='production_work_units' else None),
                'source_ref':f"{name}:{row.get('id') or row.get('work_id')}", 'detail':row})
            if row.get('tool_identity'):
                tool=row['tool_identity']
                events[-1]['title']={'file.read':'读取仓库文件','file.write':'保存受控文件修改','file.list':'检查仓库文件','git.status':'检查 Git 状态','git.diff':'读取代码差异','git.commit':'记录精确代码修订','test.run':'运行测试','build.run':'构建产物','process.run':'执行受控命令','preview.inspect':'检查预览','web.search':'检索外部资料','search.query':'检索外部资料','web.fetch':'读取外部参考'}.get(tool,'执行已登记的工具')
                events[-1]['tool']=tool
            if name=='execution_steps' and row.get('finished_at'):
                events.append({'timestamp':row['finished_at'],'owner':'EXECUTION','title':'模型或工具返回结果',
                    'state':row.get('condition'),'pwu_id':row.get('pwu_id'),
                    'source_ref':f"execution-step:{row['id']}:result",'detail':row})
            if name=='execution_allocations' and row.get('released_at'):
                events.append({'timestamp':row['released_at'],'owner':'EXECUTION','title':'释放执行容量',
                    'state':None,'pwu_id':row.get('pwu_id'),'source_ref':f"allocation:{row['id']}:released",'detail':row})
    events.sort(key=lambda r:(str(r['timestamp'] or ''),r['source_ref']))
    messages = tables.get('interaction_messages', []) or tables.get('interaction_records', [])
    conversation = [{'actor':r['actor'], 'text':r.get('content'), 'timestamp':_time(r),
        'state':r.get('processing_status'), 'source_ref':f"interaction-message:{r['id']}"}
        for r in sorted(messages, key=lambda r:(r.get('sequence',0),str(_time(r)))) if r.get('actor') in ('HUMAN','WATT')]
    if not conversation and browser:
        original = browser.get('input')
        if original:
            conversation = [{'actor':'HUMAN','text':original,'timestamp':browser.get('turn',{}).get('created_at'),
                'source_ref':f"turn:{browser.get('receipt',{}).get('turn_id')}"}]
        # The visible response is not reconstructed from UI boilerplate.
    first_input = first_input or next((m['text'] for m in conversation if m['actor']=='HUMAN'), None)
    irs = list(_walk(tables.get('interaction_turn_realizations', []), 'semantic_ir'))
    if not irs:
        irs=[r['payload'] for r in tables.get('interaction_turn_realizations',[]) if isinstance(r.get('payload'),dict) and 'items' in r['payload']]
    if not irs and browser:
        irs = [browser.get('realization', {}).get('semantic_ir', {})]
    semantic = [ir for ir in irs if ir]
    contexts = list(_walk(tables.get('production_work_units', []), 'decision_context'))
    contexts += list(_walk(tables.get('pwu_contract_versions', []), 'decision_context'))
    if not contexts:
        contexts = list(_walk(tables.get('execution_steps', []), 'decision_context'))
    contexts = list({c.get('package_fingerprint'):c for c in contexts if isinstance(c,dict)}.values())
    if not contexts and browser:
        admission=browser.get('workspace',{}).get('reality',{}).get('admission_context')
        if admission:contexts=[admission]
    units = []
    for row in tables.get('production_work_units', []):
        contract = row.get('completion_contract', {})
        task = contract.get('task_contract', {})
        steps = [s for s in tables.get('execution_steps', []) if str(s.get('attempt_id')) in
            {str(a['id']) for a in tables.get('execution_attempts', []) if str(a.get('work_unit_id'))==str(row['id'])}]
        metrics = {'model_call_count':sum(s.get('kind')=='INFERENCE' for s in steps) if steps else None, 'input_tokens':None,
            'output_tokens':None, 'cpu':None, 'memory':None, 'disk_delta':None, 'network':None,
            'queue_seconds':None, 'elapsed_seconds':None, 'model_seconds':None,
            'tool_seconds':None, 'verification_seconds':None}
        usage = [u for s in steps if s.get('kind')=='INFERENCE' for u in _walk(s.get('provider_response', s.get('result_payload', {})), 'usage') if isinstance(u,dict)]
        if usage:
            for key in ('input_tokens','output_tokens'):
                values = [u.get(key) for u in usage]
                if all(isinstance(v,(float,int)) for v in values): metrics[key]=sum(values)
        durations=[(s.get('result_payload') or {}).get('provider_observation',{}).get('transport',{}).get('elapsed_ms') for s in steps if s.get('kind')=='INFERENCE']
        if durations and all(isinstance(v,(int,float)) for v in durations):metrics['model_seconds']=sum(durations)/1000
        attempt_ids={str(a['id']) for a in tables.get('execution_attempts',[]) if str(a.get('work_unit_id'))==str(row['id'])}
        unit_events=[e for e in tables.get('execution_events',[]) if str(e.get('pwu_id'))==str(row['id'])]
        def elapsed(start,end):
            first=next((_time(e) for e in unit_events if e['event_type']==start),None)
            last=next((_time(e) for e in unit_events if e['event_type']==end),None)
            if first and last:return (datetime.fromisoformat(last)-datetime.fromisoformat(first)).total_seconds()
            return None
        metrics['queue_seconds']=elapsed('NativeExecutionQueued','NativeExecutionStarted')
        metrics['elapsed_seconds']=elapsed('NativeExecutionStarted','ExecutionWorkerCompleted')
        graph = next((p.get('graph') or {} for p in tables.get('plan_revisions',[]) if str(p['id'])==str(row.get('plan_revision_id'))),{})
        node = next((n for n in graph.get('nodes',[]) if n['node_id']==row.get('node_id')),{})
        snapshot = next((b for b in tables.get('production_snapshots',[]) if str(b['id'])==str(row.get('source_baseline_id'))),{})
        exact_revision = snapshot.get('repository_revision')
        exact_tree = snapshot.get('repository_tree') or snapshot.get('source_tree')
        if not exact_revision and not row.get('parent_baseline_ids'):
            exact_revision = next((b.get('source_revision') for b in tables.get('work_source_bases',[]) if str(b.get('source_baseline_id'))==str(row.get('source_baseline_id'))),None)
        if not exact_tree and not row.get('parent_baseline_ids'):
            exact_tree = next((b.get('source_tree') for b in tables.get('work_source_bases',[]) if str(b.get('source_baseline_id'))==str(row.get('source_baseline_id'))),None)
        name=node.get('objective') or row.get('objective') or '历史记录未保存生产目标'
        for context in contexts:
            for obligation in ([] if node else context.get('protected_obligations',[])):
                if obligation.get('context_class')=='PRODUCT_INTENT':
                    try:name=json.loads(obligation['content']).get('desired_outcome') or name
                    except (ValueError,TypeError):pass
        units.append({'id':row['id'], 'name':name,
            'objective':row.get('objective'), 'baseline':row.get('source_baseline_id'),
            'source_revision':exact_revision,
            'source_tree':exact_tree,
            'dependencies':node.get('dependency_ids',[]), 'parent_baselines':row.get('parent_baseline_ids') or [],
            'scope':task.get('scope', []), 'allowed_paths':node.get('writable_paths',task.get('writable_paths',[]) or [v.split(':',1)[1] for v in task.get('scope',[]) if isinstance(v,str) and v.startswith(('CREATE:','MODIFY:','DELETE:'))]),
            'dependency_names':[n['objective'] for n in graph.get('nodes',[]) if n['node_id'] in node.get('dependency_ids',[])],
            'verification':contract.get('verification_obligations', task.get('verification_requirements', [])),
            'state':row.get('condition'), 'events':[e for e in events if str(e['pwu_id'])==str(row['id'])
                or str(e['detail'].get('attempt_id')) in {str(s.get('attempt_id')) for s in steps}
                or (e['owner']=='EXECUTION' and e['detail'].get('session_id') in {s.get('session_id') for s in steps})],
            'metrics':metrics, 'source_ref':f"production-work-unit:{row['id']}"})
    for g in guardian:
        c=next((c for c in tables.get('baseline_candidates',[]) if str(c['id'])==g.get('candidate_id') and c.get('fingerprint')==g.get('candidate_fingerprint')),None)
        if c:
            for uid in c.get('satisfied_work_unit_ids',[]):
                e={'timestamp':g.get('assessed_at'),'owner':'GUARDIAN','title':'独立保证已评估精确候选','state':g.get('gate'),'pwu_id':uid,'source_ref':'guardian:'+str(g.get('request_id')),'detail':g}
                events.append(e)
                for unit in units:
                    if str(unit['id'])==str(uid):unit['events'].append(e)
    events.sort(key=lambda e:(str(e['timestamp'] or ''),e['source_ref']))
    # Recovery belongs to the owning Work; attach it to units only where a saved
    # exact baseline proves the relation, rather than every unit of that Work.
    for unit in units:
        unit['events'] += [e for e in events if e['source_ref'].startswith('self_refine_events:') and 'source-baseline:'+str(unit['baseline']) in e['detail'].get('evidence_references',[])]
        unit['events'].sort(key=lambda e:(str(e['timestamp'] or ''),e['source_ref']))
    model_calls = []
    for s in sorted(tables.get('execution_steps', []),key=lambda s:(str(_time(s) or ''),s.get('sequence',0))):
        if s.get('kind') != 'INFERENCE':continue
        req = s.get('request_payload', {})
        result = s.get('provider_response') or s.get('result_payload') or {}
        observation=result.get('provider_observation',{})
        call_contexts=[c for c in _walk(req,'decision_context') if isinstance(c,dict)]
        model_calls.append({'sequence':s.get('sequence'), 'timestamp':_time(s), 'purpose':'推进当前已治理的生产单元', 'governed_objective':req.get('objective'),
            'provider':observation.get('provider_identity'),
            'model':observation.get('effective_model'), 'state':s.get('condition'),
            'duration_ms':observation.get('transport',{}).get('elapsed_ms'),'usage':observation.get('usage'),
            'context_classes':sorted({x.get('context_class') for c in call_contexts for x in c.get('protected_obligations', []) if x.get('context_class')}),
            'input_categories':(['Task Contract'] if list(_walk(req,'task_contract')) else [])+(['已绑定的执行上下文与恢复事实'] if req.get('context_facts') else []),
            'observable_result':{k:result[k] for k in ('action','summary','tool_calls','result_claim','actions','usage','output','status','content','final') if k in result},
            'source_ref':f"execution-step:{s['id']}"})
    tool_calls = [e for e in events if e['detail'].get('kind') == 'TOOL' or e['detail'].get('tool_identity') or e['detail'].get('payload',{}).get('type') == 'PRODUCTION_ENVIRONMENT_COMMAND']
    searches = [e for e in tool_calls if any(w in str(e['detail'].get('tool_identity') or e['detail'].get('payload',{}).get('tool_identity','')).lower() for w in ('search.query','web.search','repository.search'))]
    for event in searches:
        effect=event['detail'];args=effect.get('semantic_input',{})
        event['query']=args.get('query') or args.get('intent')
        receipt=next((r for r in tables.get('effect_receipts',[]) if str(r.get('effect_id'))==str(effect.get('id'))),{})
        output=receipt.get('output',{})
        event['provider']=output.get('provider') or output.get('provider_identity')
        event['results_count']=len(output['results']) if isinstance(output.get('results'),list) else None
        event['selected_references']=output.get('selected_references')
        event['influence']='是否成为生产输入需查看精确上下文引用；不能凭搜索成功推断。'
    verifications = [{'obligation':v.get('obligation') or v.get('kind'), 'result':v.get('result'),
        'timestamp':_time(v), 'source_ref':f"verification:{v['id']}", 'evidence':v.get('evidence')}
        for v in tables.get('verification_records', [])]
    candidate = tables.get('baseline_candidates', [])
    artifacts = [{'path':a.get('artifact_path'), 'change':a.get('change_type'), 'source_ref':f"work-product:{a['id']}"}
        for a in tables.get('work_product_references', [])]
    repairs = tables.get('self_refine_events', [])
    deployment = tables.get('cloud_deployments', [])
    diagnosis = outcome_projection(case or {'state':'UNKNOWN'})
    diagnosis.update(production_result='候选已封存，尚需 Human 授权或验收' if candidate else '未形成候选，详见已观测生产记录',
        stability='经过自修复后推进' if repairs else '没有已保存的自修复记录，不能据此断言没有重试',
        repair_count=len(repairs), recovered=any(r.get('final_result')=='LOCAL_OBLIGATION_RECOVERED' for r in repairs),
        regression=case.get('lineage',{}).get('regression',None) if case else None,
        safety='存在独立验证或 Guardian 证据' if verifications or guardian else '未采集到完整保护证据')
    if repairs and diagnosis['divergence_label']=='尚未观测到可归因偏离':
        diagnosis['divergence_label']='受治理生产范围：自修复 owner 记录首次候选与准入义务不一致' if any(r.get('diagnostic_evidence',{}).get('signal')=='SCOPE_INFLATION' for r in repairs) else '恢复 owner 观测到局部义务未满足；更早的归因未采集'
    if not detail:
        # Event cards need chronology and owner outcome; task/context bodies are
        # already represented once above and remain retrievable as full evidence.
        for event in events:
            event['detail'] = {key:value for key,value in event['detail'].items() if key in {
                'id','attempt_id','session_id','condition','status','kind','event_type','reason',
                'work_id','pwu_id','tool_identity','semantic_input','output_summary','result',
                'candidate_id','candidate_fingerprint','source_revision','source_tree','outcome'}}
    return safe({'schema_version':'production-trace-v1','scene':scene,'purpose':purpose,
        'elapsed_seconds':case.get('elapsed_seconds') if case else None,
        'first_human_input':first_input,'basis':basis,'source_references':list(owner_refs),
        'conversation':conversation,'semantic':semantic,'contexts':contexts,
        'steering':tables.get('steering_steps', []),'plan_history':tables.get('steering_history_events', [])+tables.get('plan_revisions', []),
        'units':units,'timeline':events,'model_calls':model_calls,'tool_calls':tool_calls,
        'queue':tables.get('executor_queue', []),'search':searches,
        'search_note': '已记录外部搜索，来源与查询见下方。' if searches else '本 Case 未使用外部搜索。' if basis and basis.get('complete_execution_observation') else '现有记录未发现外部搜索；未记录的阶段不能判断。',
        'verification':verifications,'guardian':list(guardian),'candidate':candidate,
        'governance':[e for e in events if e['owner']=='GOVERNANCE'],'artifacts':artifacts,
        'recovery':repairs,'deployment':deployment,
        'deployment_note':'本 Case 未执行部署；资格范围止于 Candidate。' if candidate and not deployment else
            '未保存部署记录，不能宣称已上线。' if not deployment else '部署事实见精确目标与操作记录。',
        'diagnosis':diagnosis,'diagnostic_owners':[{'owner':o,'label':OWNER_NAMES.get(o,o),
            'events':[e for e in events if e['owner']==o]} for o in
            ('WIC','IRK','ECF','SEARCH','STEERING','PLANNING','PWU','EXECUTION','VERIFICATION','GUARDIAN','CANDIDATE','GOVERNANCE','DEPLOYMENT')],
        'advanced':{'case':case,'owners':tables} if detail else {},
        'detail_level':'full' if detail else 'summary',
        'missing_note':'历史测试未采集的对话、时间或资源显示为未采集；不会用当前状态填补历史。'})


class ProductionTraceService:
    def __init__(self, database, settings, quality):
        self.database, self.settings, self.quality = database, settings, quality

    def case_trace(self, case_run_id, *, detail=True):
        from spg.infrastructure.persistence.quality_schema import quality_case_runs, quality_case_versions
        with self.database.unit_of_work() as u:
            a = self.quality._one(u.session, quality_case_runs, case_run_id)
            v = self.quality._one(u.session, quality_case_versions, a['case_version_id'])
        run = self.quality.run_detail(a['campaign_run_id'])
        member = next(m for m in run['members'] if m['case_version_id']==a['case_version_id'])
        if member['definition'].get('sealed'):
            return project_trace({},scene=member['title'],purpose='未见场景材料已封存，不向优化或诊断页面披露答案。',
                case={'state':a['state'],'lineage':{'sealed':True}},basis={'mode':'SEALED','at':a['finished_at']})
        case = next(c for c in run['cases'] if c['id']==case_run_id)
        lineage = case['lineage'];tables = {};refs = [];browser=None;guardian=[]
        for observation in lineage.get('owner_observations', []):
            for name, rows in observation.get('owners', {}).items():
                if isinstance(rows,list):tables.setdefault(name,[]).extend(rows)
            guardian.extend(observation.get('guardian_results', []))
        refs = [r for e in case['evaluations'] for r in e.get('evidence_refs', [])]
        for ref in refs:
            artifact = qualification_artifact(self.settings, ref)
            if artifact is None:continue
            path,bundle = artifact
            files = bundle.get('files', {})
            for key,item in files.items():
                raw = item.get('content', {})
                if ('final' in key or browser is None) and raw.get('receipt', {}).get('turn_id') == lineage.get('turn_id'):
                    browser=raw
            # Complete saved owner observations are immutable qualification snapshots.
            cutoff = (a['finished_at'] or datetime.now(UTC)).timestamp()
            snapshots=[]
            for p in path.parent.glob('owner-trace-observation-*.json'):
                if (p.resolve().parent==path.parent.resolve() and p.stat().st_size<=10_000_000
                        and p.stat().st_mtime<=cutoff): snapshots.append(p)
            if snapshots and browser:
                saved=json.loads(max(snapshots,key=lambda p:p.stat().st_mtime).read_text())
                expected_work=lineage.get('work_id') or browser.get('workspace',{}).get('work',{}).get('work_id')
                saved_work_ids={str(w['id']) for w in saved.get('tables',{}).get('product_works',[])}
                if saved.get('revision') == run['watt_revision'] and expected_work and str(expected_work) in saved_work_ids:
                    tables = saved.get('tables', tables)
                    refs.append('qualification-owner-snapshot:sha256:'+sha256(max(snapshots,key=lambda p:p.stat().st_mtime).read_bytes()).hexdigest())
            for item in files.values():
                raw=item.get('content', {})
                expected_work=lineage.get('work_id') or (browser or {}).get('workspace',{}).get('work',{}).get('work_id')
                if expected_work and raw.get('status')=='PASS' and raw.get('work_id')==expected_work and raw.get('guardian'):
                    guardian.append(raw['guardian'])
            break
        if browser:
            # Completed published dialogue is attributable to exact Interaction and time.
            # Never read current Product/Work state to fill an old qualification gap.
            from spg.infrastructure.persistence.product_schema import interaction_messages
            iid=UUID(browser['receipt']['interaction_id'])
            with self.database.unit_of_work() as u:
                messages=[dict(r) for r in u.session.execute(select(interaction_messages).where(
                    interaction_messages.c.interaction_id==iid,
                    interaction_messages.c.created_at <= (a['finished_at'] or datetime.now(UTC)),
                    interaction_messages.c.processing_status=='COMPLETED').order_by(interaction_messages.c.sequence)).mappings()]
            target_turn=browser['receipt']['turn_id']
            sequences=[m['sequence'] for m in messages if str(m.get('turn_id'))==target_turn]
            if sequences:messages=[m for m in messages if m['sequence']<=max(sequences)]
            if messages:tables['interaction_messages']=messages
            # Immutable exact source and effect receipts enrich the saved snapshot.
            # IDs and observation cut-off fence future executions and current Product state.
            with self.database.unit_of_work() as u:
                baseline_ids={UUID(str(p['source_baseline_id'])) for p in tables.get('production_work_units',[]) if p.get('source_baseline_id')}
                step_ids={UUID(str(p['id'])) for p in tables.get('execution_steps',[])}
                for name,col,values in [('production_snapshots','id',baseline_ids),('execution_effects','step_id',step_ids)]:
                    t=metadata.tables[name]
                    if values:
                        tables[name]=[dict(r) for r in u.session.execute(select(t).where(t.c[col].in_(values),t.c.created_at<=a['finished_at'])).mappings()]
                effect_ids={p['id'] for p in tables.get('execution_effects',[])}
                if effect_ids:
                    t=metadata.tables['effect_receipts']
                    tables['effect_receipts']=[dict(r) for r in u.session.execute(select(t).where(t.c.effect_id.in_(effect_ids),t.c.created_at<=a['finished_at'])).mappings()]
            workspace=browser.get('workspace', {})
            if not tables.get('steering_steps'):
                tables['steering_steps']=workspace.get('agenda', [])
            context=workspace.get('reality', {}).get('admission_context')
            if context: tables.setdefault('production_work_units', [])
        purpose='验证已治理的意图保持精确，只有实际由 Human 保留的决定才能阻止推进，普通生产事实由 Watt 负责表达。' if member['definition'].get('runner_key','').startswith('REG-HI-') else '验证本场景满足已批准义务：'+'；'.join(member['definition'].get('invariants',[]))
        return project_trace(tables,scene=member['title'],purpose=purpose,detail=detail,
            first_input=lineage.get('input'),case=case,browser=browser,guardian=guardian,owner_refs=refs,
            basis={'mode':'HISTORICAL_QUALIFICATION','at':a['finished_at'],'watt_revision':run['watt_revision'],
                'case_version':member['version'],'case_fingerprint':member['fingerprint'],
                'complete_execution_observation':bool(tables.get('execution_steps'))})

    def entity_trace(self, kind, entity_id, *, detail=True, work=None,
                     max_rows_per_table=None):
        roots={'work':'product_works','product':'software_products','interaction':'product_interactions',
            'pwu':'production_work_units','candidate':'baseline_candidates','deployment':'cloud_deployments'}
        if kind not in roots:raise QualityError('TRACE_IDENTIFIER_NOT_SUPPORTED')
        root=roots[kind];ids={entity_id};tables={}
        allowed=set(TABLE_OWNERS)|{'product_works','software_products','work_runtime_bindings','production_runs',
            'product_interactions','product_workspace_interactions','execution_sessions','execution_workspaces'}
        truncated_tables = {}
        with self.database.unit_of_work() as u:
            found=u.session.execute(select(metadata.tables[root]).where(metadata.tables[root].c.id==entity_id)).mappings().first()
            if found is None:raise QualityError('TRACE_SOURCE_NOT_FOUND')
            tables[root]=[dict(found)]
            if kind == 'work':
                tables = self._work_tables(u.session, entity_id,
                    max_rows_per_table=max_rows_per_table, truncated=truncated_tables)
            # Other entity entrypoints retain their existing lookup semantics.
            for _ in range(0 if kind == 'work' else 10):
                before=len(ids)
                for name in allowed:
                    t=metadata.tables.get(name)
                    if t is None:continue
                    cols=[c for c in t.c if c.name in ('id','work_id','work_focus_id','interaction_id',
                        'turn_id','production_run_id','plan_revision_id','work_unit_id','pwu_id','attempt_id','session_id',
                        'steering_plan_id','steering_plan_revision_id','step_id','effect_id', *(['product_id'] if kind=='product' else [])) and isinstance(c.type,__import__('sqlalchemy').Uuid)]
                    if not cols:continue
                    rows=[dict(r) for r in u.session.execute(select(t).where(or_(*(c.in_(ids) for c in cols)))).mappings()]
                    if not rows:continue
                    tables[name]=rows
                    for r in rows:
                        for c in cols:
                            if isinstance(r[c.name], UUID):ids.add(r[c.name])
                if len(ids)==before:break
            baselines={r['source_baseline_id'] for r in tables.get('production_work_units',[]) if r.get('source_baseline_id')}
            if baselines and kind != 'work':
                t=metadata.tables['production_snapshots']
                tables['production_snapshots']=[dict(r) for r in u.session.execute(select(t).where(t.c.id.in_(baselines))).mappings()]
        guardian=[]
        candidate_keys={(str(r['id']),r['fingerprint']) for r in tables.get('baseline_candidates', [])}
        if candidate_keys:
            folder=self.settings.owner_runtime_store_root/'guardian/results'
            scanned=0
            for p in folder.glob('*.json'):
                if max_rows_per_table is not None and scanned>=2000:
                    truncated_tables['guardian_result_files']={'scanned_count':scanned,
                        'remaining_count':'UNKNOWN','selection':'first 2000 filesystem entries; later results not observed'}
                    break
                scanned+=1
                try:
                    if p.stat().st_size>1_000_000:continue
                    g=json.loads(p.read_text())
                    if (g.get('candidate_id'),g.get('candidate_fingerprint')) in candidate_keys:guardian.append(g)
                except (ValueError,OSError):continue
        result = project_trace(tables,scene=next((w.get('refined_title') or w.get('desired_outcome') for w in tables.get('product_works',[])), '生产历程'),
            purpose=(work or {}).get('desired_outcome') or (work or {}).get('raw_user_requirement') or '查看指定生产对象的 owner 记录。当前查询与历史资格快照明确区分。',guardian=guardian,detail=detail,
            owner_refs=[f'{kind}:{entity_id}'],basis={'mode':'LIVE_ENTITY_LOOKUP','at':datetime.now(UTC).isoformat(),
                'complete_execution_observation':bool(tables.get('execution_steps'))})
        if kind == 'work':
            if work is None:
                from spg.evaluation.work_registry import WorkRegistryService
                owner=next((p['owner_id'] for p in tables.get('software_products',[])), 'human:owner')
                work=WorkRegistryService(self.database).get(owner,entity_id)
            result['work']=work
            # Selected Trace reuses the owner reader without creating state.
            from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore
            store=JsonProductionEnvironmentStore(self.settings.native_executor_production_environment_store_root,create_root=False)
            preview=None;preview_error=None
            try:
                current=store.current_candidate_preview(entity_id)
                if current is not None and current.work_id==entity_id:
                    preview=current.model_dump(mode='json')
                    projection=store.guardian_projection(current.id)
                    if projection and projection.get('candidate_id')==str(current.candidate_id) and projection.get('candidate_fingerprint',current.candidate_fingerprint)==current.candidate_fingerprint:
                        guardian.append(projection)
            except (ValueError,OSError,KeyError) as error:
                preview_error=type(error).__name__
            result['preview']=preview
            result['preview_observation_error']=preview_error
            result['guardian']=guardian
            result['manifests']=tables.get('work_delivery_manifests',[])
            result['acceptance']=tables.get('work_delivery_acceptances',[])
            end=('已保存交付 Manifest；验收及部署见 owner 记录' if tables.get('work_delivery_manifests') else
                '已形成 Candidate，尚无交付 Manifest；不能宣称已完整交付' if result['candidate'] else
                '已进入执行，尚未形成 Candidate' if tables.get('execution_attempts') else
                '尚未进入执行；已保存的交流、意图和推进记录如下')
            if guardian and any(g.get('gate') in {'BLOCKED','FAIL','FAIL_REPAIRABLE'} and g.get('candidate_id')==str(work.get('candidate_id')) and g.get('candidate_fingerprint')==work.get('candidate_fingerprint') for g in guardian):
                work={**work,'state':'BLOCKED','state_label':'受阻','bucket':'PROBLEM'};result['work']=work
            result['diagnosis'].update(quality_label=work['state_label'],production_result=end)
            result['story']={'current_state':work['state_label'],'flow_ended':end,'latest_event':work['latest_event'],
                'latest_activity_at':work['latest_activity_at'],'product_name':work['product_name'],
                'original_input':result['first_human_input'],'candidate_ids':[str(c['id']) for c in tables.get('baseline_candidates',[])],
                'manifest_ids':[str(m['id']) for m in tables.get('work_delivery_manifests',[])]}
            result['search_note']='已记录外部搜索，来源与查询见下方。' if result['search'] else '已保存的 Work 记录未发现外部搜索；未记录阶段不能判定。'
            result['missing_note']='未发生或未记录的后续阶段保持缺失；普通 Work 不依赖 Quality Case 或 Candidate。'
            result['deployment_note']='部署事实见精确目标与操作记录。' if result['deployment'] else '尚无部署记录；不代表已上线。'
            if result['candidate'] and not tables.get('work_delivery_manifests'):result['deployment_note']='已生成候选源码；尚无 Delivery Manifest，不能将源码下载等同于完整交付。'
        if truncated_tables:
            result['capture_truncation'] = truncated_tables
        return safe(result)

    def _work_tables(self,session,work_id,*,max_rows_per_table=None,truncated=None):
        """Directional exact lineage. Shared Interaction never pulls sibling Works."""
        tables={}
        def read(name,condition):
            t=metadata.tables[name]
            query=select(t).where(condition)
            if max_rows_per_table is None:
                rows=[dict(r) for r in session.execute(query).mappings()]
            else:
                # Exports cannot hydrate an unbounded owner table. Keep the
                # earliest record, recent records and failure-bearing rows.
                primary=list(t.primary_key.columns)
                order=t.c.created_at if 'created_at' in t.c else primary[0]
                # Multiple conversation records can share a transaction
                # timestamp. Their durable sequence precedes random UUIDs.
                tie_break=([t.c.sequence] if 'sequence' in t.c and order.name!='sequence' else []) + (
                    primary if 'created_at' in t.c else primary[1:])
                first=[dict(r) for r in session.execute(query.order_by(order,*tie_break).limit(max_rows_per_table+1)).mappings()]
                if len(first)<=max_rows_per_table:
                    rows=first
                else:
                    from sqlalchemy import cast, String, func
                    count=session.scalar(select(func.count()).select_from(t).where(condition))
                    third=max(1,max_rows_per_table//3)
                    latest=[dict(r) for r in session.execute(query.order_by(order.desc(),*(c.desc() for c in tie_break)).limit(third)).mappings()]
                    failure_columns=[c for key in ('condition','state','status','outcome','result','event_type',
                                      'steering_outcome','failure_family','stop_reason','error_code')
                                     if (c:=t.c.get(key)) is not None]
                    failure=or_(*(cast(c,String).ilike(pattern) for c in failure_columns
                        for pattern in ('%FAIL%','%BLOCK%','%NON_CONVERG%','%ERROR%','%INTERRUPT%',
                                        '%HUMAN_ATTENTION%'))) if failure_columns else None
                    failures=[dict(r) for r in session.execute(query.where(failure).order_by(order,*tie_break).limit(third)).mappings()] if failure is not None else []
                    picked={tuple(str(r[c.name]) for c in primary):r for r in [*first[:third],*failures,*latest]}
                    rows=sorted(picked.values(),key=lambda r:(str(r.get(order.name) or ''),
                        tuple(str(r[c.name]) for c in primary)))[:max_rows_per_table]
                    truncated[name]={'observed_count':count,'exported_count':len(rows),
                        'selection':'earliest, failure-bearing, latest; remaining records omitted'}
            tables[name]=rows;return rows
        def ids(name):return {r['id'] for r in tables.get(name,[]) if r.get('id')}
        w=metadata.tables['product_works'];work=read('product_works',w.c.id==work_id)[0]
        if work['product_id']:
            t=metadata.tables['software_products'];read('software_products',t.c.id==work['product_id'])
        t=metadata.tables['work_reality_revisions'];revisions=read('work_reality_revisions',t.c.work_id==work_id)
        iids={r['source_interaction_id'] for r in revisions if r.get('source_interaction_id')}
        t=metadata.tables['product_interactions'];iids|={r['id'] for r in read('product_interactions',t.c.current_work_id==work_id)}
        if iids:read('product_interactions',t.c.id.in_(iids))
        record_ids={UUID(str(v)) for r in revisions for v in r.get('source_record_ids',[])}
        first=min((r['created_at'] for r in revisions),default=work['created_at'])
        t=metadata.tables['interaction_records'];read('interaction_records',or_(t.c.work_focus_id==work_id,t.c.id.in_(record_ids),
            (t.c.interaction_id.in_(iids)) & (t.c.work_focus_id.is_(None)) & (t.c.created_at<=first)))
        t=metadata.tables['interaction_turns'];read('interaction_turns',t.c.request_record_id.in_(ids('interaction_records')))
        tids=ids('interaction_turns');aids={r['assessment_id'] for r in tables['interaction_turns'] if r.get('assessment_id')}
        for name,col,values in [('interaction_messages','turn_id',tids),('interaction_response_events','turn_id',tids),
            ('interaction_turn_realizations','turn_id',tids),('interaction_turn_obligations','turn_id',tids),('interaction_assessments','id',aids)]:
            t=metadata.tables[name];read(name,t.c[col].in_(values))
        for name in ('work_source_bases','work_runtime_bindings','steering_plans','steering_plan_revisions','semantic_step_results','self_refine_events','work_delivery_manifests'):
            t=metadata.tables[name];read(name,t.c.work_id==work_id)
        run_ids={r['production_run_id'] for r in tables['work_runtime_bindings']}
        t=metadata.tables['production_runs'];read('production_runs',t.c.id.in_(run_ids))
        t=metadata.tables['production_work_units'];read('production_work_units',t.c.production_run_id.in_(run_ids))
        t=metadata.tables['execution_attempts'];read('execution_attempts',t.c.work_unit_id.in_(ids('production_work_units')))
        t=metadata.tables['execution_sessions'];read('execution_sessions',t.c.pwu_id.in_(ids('production_work_units')))
        t=metadata.tables['execution_steps'];read('execution_steps',t.c.attempt_id.in_(ids('execution_attempts')))
        t=metadata.tables['execution_effects'];read('execution_effects',t.c.step_id.in_(ids('execution_steps')))
        t=metadata.tables['baseline_candidates'];read('baseline_candidates',t.c.production_run_id.in_(run_ids))
        t=metadata.tables['execution_dispatches'];read('execution_dispatches',t.c.attempt_id.in_(ids('execution_attempts')))
        t=metadata.tables['completion_evaluations'];read('completion_evaluations',t.c.attempt_id.in_(ids('execution_attempts')))
        t=metadata.tables['proposed_repository_snapshots'];read('proposed_repository_snapshots',or_(t.c.completion_evaluation_id.in_(ids('completion_evaluations')),t.c.id.in_({r['proposed_snapshot_id'] for r in tables['baseline_candidates']})))
        t=metadata.tables['cloud_deployments'];read('cloud_deployments',t.c.manifest_id.in_(ids('work_delivery_manifests')))
        domains={'work_id':{work_id},'production_run_id':run_ids,'plan_revision_id':{r['plan_revision_id'] for r in tables['work_runtime_bindings']},
            'steering_plan_id':ids('steering_plans'),'steering_plan_revision_id':ids('steering_plan_revisions'),
            'pwu_id':ids('production_work_units'),'work_unit_id':ids('production_work_units'),'attempt_id':ids('execution_attempts'),
            'dispatch_id':ids('execution_dispatches'),'completion_evaluation_id':ids('completion_evaluations'),'proposed_snapshot_id':ids('proposed_repository_snapshots'),
            'session_id':ids('execution_sessions'),'step_id':ids('execution_steps'),'effect_id':ids('execution_effects'),
            'candidate_id':ids('baseline_candidates'),'manifest_id':ids('work_delivery_manifests'),'deployment_id':ids('cloud_deployments')}
        for name in set(TABLE_OWNERS)|{'runtime_commits','execution_workspaces'}:
            if name in tables or name not in metadata.tables:continue
            t=metadata.tables[name];cols=[(c,values) for c,values in domains.items() if c in t.c and values]
            if cols:read(name,or_(*(t.c[c].in_(values) for c,values in cols)))
        t=metadata.tables['governance_records'];read('governance_records',t.c.subject_identity.in_([str(work_id),*[str(c) for c in ids('baseline_candidates')]]))
        snapshots={r['source_baseline_id'] for r in tables['production_work_units'] if r.get('source_baseline_id')}
        snapshots|={r['verified_output_baseline_id'] for r in tables['production_work_units'] if r.get('verified_output_baseline_id')}
        t=metadata.tables['production_snapshots'];read('production_snapshots',t.c.id.in_(snapshots))
        return tables
