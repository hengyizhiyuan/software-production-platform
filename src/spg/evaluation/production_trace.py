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
from fastapi.encoders import jsonable_encoder

from spg.infrastructure.persistence import metadata
from spg.evaluation.contracts import QualityError
from spg.evaluation.admin_projection import OWNER_NAMES, outcome_projection

PRIVATE_KEYS = {'reasoning', 'reasoning_content', 'chain_of_thought', 'thinking', 'analysis',
    'access_token', 'refresh_token', 'api_key', 'secret', 'password', 'authorization',
    'security_token', 'credential', 'credentials', 'operator_token', 'lease_token'}
TABLE_OWNERS = {
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
    'ExecutionWorkerCompleted':'执行完成','NativeExecutionPaused':'暂停执行',
    'NativeExecutionResumed':'恢复执行','NativeExecutionCancelled':'取消执行',
    'ExecutionRecoveryRequired':'需要恢复','ExecutionRequeued':'恢复后重新排队'})


def safe(value):
    """Do not expose credentials or hidden model reasoning, even in diagnostic mode."""
    if isinstance(value, dict):
        return {k:safe(v) for k,v in value.items() if str(k).lower() not in PRIVATE_KEYS
            and not any(s in str(k).lower() for s in ('chain_of_thought', 'secret_key', 'accesskeysecret'))}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
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


def project_trace(tables, *, scene, purpose, first_input=None, case=None, basis=None,
                  owner_refs=(), guardian=(), browser=None):
    """Both story and diagnostic modes consume this same historical fact set."""
    tables = safe(tables)
    events = []
    for name, rows in tables.items():
        if name not in TABLE_OWNERS:
            continue
        for row in rows:
            kind = row.get('event_type') or row.get('to_condition') or row.get('kind') or name
            record_labels={'executor_queue':'进入队列','execution_allocations':'获得执行容量',
                'production_work_units':'建立生产单元','baseline_candidates':'封存候选成果',
                'execution_attempts':'建立执行尝试','self_refine_events':'自修复记录',
                'steering_steps':'登记推进步骤','interaction_messages':'Human 可见交流',
                'interaction_records':'保存交流记录','work_source_bases':'绑定精确来源'}
            events.append({'timestamp':_time(row), 'owner':TABLE_OWNERS[name],
                'title':record_labels.get(name, EVENT_LABELS.get(kind, {'verification_records':'独立验证记录',
                    'self_refine_events':'自修复记录','steering_decisions':'推进决定',
                    'plan_revisions':'形成生产计划','interaction_turn_realizations':'意图已治理',
                    'execution_allocations':'分配执行容量','human_authorizations':'Human 授权',
                    'work_delivery_acceptances':'Human 验收'}.get(name, OWNER_NAMES.get(TABLE_OWNERS[name], '生产')+'记录'))),
                'state':row.get('result') if name=='verification_records' else row.get('to_condition'),
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
        if not exact_revision and not row.get('parent_baseline_ids'):
            exact_revision = next((b.get('source_revision') for b in tables.get('work_source_bases',[]) if str(b.get('source_baseline_id'))==str(row.get('source_baseline_id'))),None)
        name=node.get('objective') or row.get('objective') or '历史记录未保存生产目标'
        for context in contexts:
            for obligation in ([] if node else context.get('protected_obligations',[])):
                if obligation.get('context_class')=='PRODUCT_INTENT':
                    try:name=json.loads(obligation['content']).get('desired_outcome') or name
                    except (ValueError,TypeError):pass
        units.append({'id':row['id'], 'name':name,
            'objective':row.get('objective'), 'baseline':row.get('source_baseline_id'),
            'source_revision':exact_revision,
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
        model_calls.append({'sequence':s.get('sequence'), 'timestamp':_time(s), 'purpose':'推进当前已治理的生产单元', 'governed_objective':req.get('objective'),
            'provider':observation.get('provider_identity'),
            'model':observation.get('effective_model'), 'state':s.get('condition'),
            'duration_ms':observation.get('transport',{}).get('elapsed_ms'),'usage':observation.get('usage'),
            'context_classes':sorted({x.get('context_class') for c in contexts for x in c.get('protected_obligations', []) if x.get('context_class')}),
            'input_categories':['Task Contract','工程来源与恢复点'] if req else [],
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
    return safe({'schema_version':'production-trace-v1','scene':scene,'purpose':purpose,
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
        'advanced':{'case':case,'owners':tables},
        'missing_note':'历史测试未采集的对话、时间或资源显示为未采集；不会用当前状态填补历史。'})


class ProductionTraceService:
    def __init__(self, database, settings, quality):
        self.database, self.settings, self.quality = database, settings, quality

    def case_trace(self, case_run_id):
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
        return project_trace(tables,scene=member['title'],purpose=member['definition'].get('motive', member['title']),
            first_input=lineage.get('input'),case=case,browser=browser,guardian=guardian,owner_refs=refs,
            basis={'mode':'HISTORICAL_QUALIFICATION','at':a['finished_at'],'watt_revision':run['watt_revision'],
                'case_version':member['version'],'case_fingerprint':member['fingerprint'],
                'complete_execution_observation':bool(tables.get('execution_steps'))})

    def entity_trace(self, kind, entity_id):
        roots={'work':'product_works','product':'software_products','interaction':'product_interactions',
            'pwu':'production_work_units','candidate':'baseline_candidates','deployment':'cloud_deployments'}
        if kind not in roots:raise QualityError('TRACE_IDENTIFIER_NOT_SUPPORTED')
        root=roots[kind];ids={entity_id};tables={}
        allowed=set(TABLE_OWNERS)|{'product_works','software_products','work_runtime_bindings','production_runs',
            'product_interactions','product_workspace_interactions','execution_sessions','execution_workspaces'}
        with self.database.unit_of_work() as u:
            found=u.session.execute(select(metadata.tables[root]).where(metadata.tables[root].c.id==entity_id)).mappings().first()
            if found is None:raise QualityError('TRACE_SOURCE_NOT_FOUND')
            tables[root]=[dict(found)]
            # Exact engineering identity relations, never arbitrary SQL or a global ledger walk.
            for _ in range(10):
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
            if baselines:
                t=metadata.tables['production_snapshots']
                tables['production_snapshots']=[dict(r) for r in u.session.execute(select(t).where(t.c.id.in_(baselines))).mappings()]
        guardian=[]
        for r in tables.get('baseline_candidates', []):
            folder=self.settings.owner_runtime_store_root/'guardian/results'
            for p in folder.glob('*.json'):
                if p.stat().st_size>1_000_000:continue
                try:
                    g=json.loads(p.read_text())
                    if g.get('candidate_id')==str(r['id']) and g.get('candidate_fingerprint')==r['fingerprint']:guardian.append(g)
                except (ValueError,OSError):continue
        return project_trace(tables,scene=next((w.get('refined_title') or w.get('desired_outcome') for w in tables.get('product_works',[])), '生产历程'),
            purpose='查看指定生产对象的 owner 记录。当前查询与历史资格快照明确区分。',guardian=guardian,
            owner_refs=[f'{kind}:{entity_id}'],basis={'mode':'LIVE_ENTITY_LOOKUP','at':datetime.now(UTC).isoformat(),
                'complete_execution_observation':bool(tables.get('execution_steps'))})
