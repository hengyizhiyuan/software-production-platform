"""One WIC realization per exact owner Reality basis, shared by normal surfaces."""
from hashlib import sha256
import json
from uuid import UUID
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from spg.application.human_attention import canonical_ir_for_work
from spg.application.human_language import require_human_language, language_leaks
from spg.domain.human_visible import HumanVisibleProjection, HumanVisibleWording
from spg.infrastructure.persistence.human_visible_schema import wic_human_realizations


# These are WIC's bounded safe expression vocabulary, not prose from an owner.
PHASE = {'DESIGN':'整理实施方案','REFINE':'核对当前需求','PRODUCE':'准备与执行当前改动',
    'VERIFY_ACCEPT':'核对成果并准备审阅','HUMAN_DECISION':'等待明确的产品决定','COMPLETE':'确认本次目标已满足'}
STATUS = {'READY':'准备中','RUNNING':'正在生产','NEEDS_ATTENTION':'需要处理当前阻塞',
    'BLOCKED':'暂时受阻','COMPLETED':'已完成','DRAFT':'待准备','PRE_WORK':'正在理解',
    'NEEDS_REFINEMENT':'需要补齐生产条件','AWAITING_APPROVAL':'等待明确授权','CANCELLED':'已取消','DISCARDED':'已结束'}
EXECUTION = {'CREATED':'等待进入执行队列','QUEUED':'已排队，等待可用执行容量','ASSIGNED':'Worker 已领取',
    'RUNNING':'Worker 正在执行','VERIFYING':'正在验证执行成果','VERIFIED':'执行成果已通过验证',
    'COMPLETED':'执行已完成','FAILED':'执行失败，保留诊断与恢复记录','RECOVERY_REQUIRED':'执行中断，等待恢复',
    'CANCELLED':'执行已取消'}
UNIT = {**EXECUTION,'READY':'已就绪','WAITING_CAPACITY':'等待执行容量','DEPENDENCIES_PENDING':'等待前序成果验证',
    'WAITING_RESOURCE':'等待执行条件恢复','PREPARING':'正在准备执行','BLOCKED':'当前生产单元受阻'}
GUARDIAN = {'PASS':'质量检查通过','FAIL':'质量检查未通过','NOT_STARTED':'尚未开始质量检查',
    'FINDINGS_PRESENT':'质量检查发现问题','REPAIR_IN_PROGRESS':'正在修复质量问题',
    'REVERIFYING':'正在重新检查质量','UNAVAILABLE':'质量检查暂不可用','BLOCKED':'质量检查受阻'}


def _digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def projection_for_workspace(database, workspace):
    work = workspace['work']
    work_id = None if work is None else UUID(work['work_id'])
    with database.unit_of_work() as uow:
        ir = None if work_id is None else canonical_ir_for_work(uow.session, work_id)
        if ir is None and workspace.get('interaction_id'):
            from spg.infrastructure.persistence.interaction_store import InteractionStore
            assessment = InteractionStore(uow.session).latest_assessment(UUID(workspace['interaction_id']))
            ir = None if assessment is None else assessment.semantic_ir
    reality = workspace['reality']
    execution = reality.get('execution')
    # Heartbeat timing/capacity sampling does not create a new expression version.
    execution_fact = None if execution is None else {k:execution.get(k) for k in
        ('execution_id','id','status','state','worker_id','attempt_id','blocked_reason','failure_code','recovery_reason')}
    candidate = reality.get('candidate')
    facts = {'work': None if work is None else {k:work.get(k) for k in
        ('work_id','status','current_work_reality_revision_id','current_production_step',
         'most_recent_meaningful_event','what_happens_next','work_complete')},
        'execution':execution_fact,'scheduling':None if execution is None else {k:(execution.get('scheduling') or {}).get(k) for k in ('progression_state','compatible_slots','draining_worker_count')},'candidate':candidate,'guardian':reality.get('guardian'),
        'accepted_version':reality.get('accepted_version'),
        'accepted_revision':reality.get('accepted_revision'),
        'admission_context':reality.get('admission_context'),
        'deliveries':reality.get('deliveries',()),'cloud_deployment':reality.get('cloud_deployment')}
    agenda = tuple(workspace['agenda'])
    decisions = tuple({k:a.get(k) for k in ('id','kind','human_decision_need','actions','governed_subject_ref',
                                          'conversation_prompt','decision','reason')} for a in workspace['actions'])
    plan = reality.get('production_plan')
    units = () if plan is None else tuple({k:u.get(k) for k in
        ('pwu_id','objective','state','kind','blocked_reason','dependencies')} for u in plan['pwus'])
    motive = ('；'.join(goal.objective for goal in ir.current_production) if ir and ir.current_production else
              (work or {}).get('desired_outcome') or workspace['product']['name'])
    refs = tuple(filter(None, (f"product:{workspace['product']['id']}",
        None if work_id is None else f'work:{work_id}',
        None if ir is None else f'semantic-ir:{ir.id}',
        *((a.get('governed_subject_ref')) for a in workspace['actions']),
        *((reality.get('admission_context') or {}).get('source_references',())))))
    basis = {'motive':motive,'ir':None if ir is None else ir.model_dump(mode='json'),
             'facts':facts,'agenda':agenda,'decisions':decisions,'units':units,'refs':refs}
    return HumanVisibleProjection(basis_fingerprint=_digest(basis), governed_motive=motive,
        governed_semantic_ir=basis['ir'],owner_facts=facts,agenda=agenda,decision_needs=decisions,
        production_units=units,source_references=refs)


def validate_wording(projection, wording):
    expected = lambda rows: {r['id'] for r in rows}
    if len(wording.agenda) != len(projection.agenda) or {r.id for r in wording.agenda} != expected(projection.agenda):
        raise ValueError('HUMAN_REALIZATION_AGENDA_BINDING')
    if len(wording.decisions) != len(projection.decision_needs) or {r.id for r in wording.decisions} != expected(projection.decision_needs):
        raise ValueError('HUMAN_REALIZATION_DECISION_BINDING')
    if len(wording.production_units) != len(projection.production_units) or {r.id for r in wording.production_units} != {r['pwu_id'] for r in projection.production_units}:
        raise ValueError('HUMAN_REALIZATION_PWU_BINDING')
    for field in ('headline','summary','current_activity','next_step'):
        require_human_language(getattr(wording,field))
    for row in (*wording.agenda,*wording.production_units):
        require_human_language(row.text)
    for row in wording.decisions:
        for field in ('title','question','why_now'):require_human_language(getattr(row,field))
    # A Realizer never manufactures a request or a success absent from owner truth.
    prose = ' '.join((wording.summary,wording.current_activity,wording.next_step))
    if not projection.decision_needs and any(t in prose for t in ('请你决定','等待你的决定','请选择','请先确认','？','?')):
        raise ValueError('HUMAN_REALIZATION_INVENTED_DECISION')
    guardian = projection.owner_facts.get('guardian') or {}
    candidate = projection.owner_facts.get('candidate')
    work = projection.owner_facts.get('work') or {}
    if (projection.owner_facts.get('admission_context') or {}).get('status') == 'NOT_READY':
        if not any(t in wording.summary for t in ('受阻','暂停','停止','尚未','无法','未满足','缺少','缺失','未齐','不足','未就绪','未准备')):
            raise ValueError('HUMAN_REALIZATION_HIDDEN_ADMISSION_BLOCKER')
        if any(t in prose for t in ('正在生产','正在执行改动','会自动继续','将自动继续','按当前目标继续形成并验证改动')):
            raise ValueError('HUMAN_REALIZATION_FALSE_AUTONOMOUS_PROGRESS')
    for claim, allowed in [('质量检查通过',guardian.get('gate')=='PASS'),
                           ('验证已通过',bool(candidate and candidate.get('verification') and all(v.endswith(': PASS') for v in candidate['verification']))),('已完成本次',work.get('work_complete') is True),
                           ('已经部署',projection.owner_facts.get('cloud_deployment',{}) and
                            projection.owner_facts['cloud_deployment'].get('state')=='SUCCEEDED')]:
        if claim in prose and not allowed:raise ValueError('HUMAN_REALIZATION_UNSUPPORTED_SUCCESS')
    return wording


def safe_wording(projection):
    """WIC safe expression if a replaceable model fails. No owner prose passthrough."""
    motive = projection.governed_motive
    if language_leaks(motive):motive='当前产品目标'
    work = projection.owner_facts.get('work') or {}
    execution = projection.owner_facts.get('execution')
    state = None if execution is None else execution.get('status') or execution.get('state')
    phase = PHASE.get(work.get('current_production_step'),'核对当前生产条件')
    activity = EXECUTION.get(state,phase)
    summary = f'{motive}。{STATUS.get(work.get("status"),"正在保留并理解这次请求")}；{activity}。'
    next_step = '按当前目标继续形成并验证改动；成果需要你明确审阅和接受。'
    context_blocker = admission_context_wording(projection.owner_facts.get('admission_context'))
    if context_blocker:
        activity='生产准备受阻，尚未进入执行'
        summary=f'{motive}。{context_blocker}'
        next_step='先核对并补齐已有授权的生产依据，再重新检查准入；不会代替你批准缺失的决定。'
    if work.get('status') in {'BLOCKED','NEEDS_REFINEMENT','NEEDS_ATTENTION'} and not projection.decision_needs:
        next_step='当前生产条件未满足，需先由负责的模块核对阻塞证据；尚未完成。'
    if projection.decision_needs:next_step='先处理下方的具体决定，再依据你的选择推进。'
    decisions=[]
    for item in projection.decision_needs:
        need=item.get('human_decision_need')
        if need:
            question=need['question'];why=need['why_now']+'；'+'；'.join(o['label']+'：'+o['consequence'] for o in need['supported_options']);title=need['decision_subject']
            if any(language_leaks(v) for v in (question,why,title)):
                question='当前决定的说明暂时无法安全展示，请稍后重新读取。';why='授权边界仍保留，系统不会代替你做决定。';title='待处理的明确决定'
        else:
            title={'CANDIDATE_AUTHORIZATION':'审阅当前候选成果','WORK_APPROVAL':'确认本次生产范围',
                   'WORK_REVISION_APPROVAL':'确认新要求对当前事项的影响'}.get(item['kind'],'审阅当前授权事项')
            question='请查看当前成果和范围，再明确授权或要求修改。';why='这一授权由你决定；系统不会自动接受或扩大范围。'
        decisions.append({'id':item['id'],'title':title,'question':question,'why_now':why})
    return HumanVisibleWording(headline=motive,summary=summary,current_activity=activity,next_step=next_step,
        agenda=tuple({'id':a['id'],'text':PHASE.get(a['type'],'继续当前生产目标')} for a in projection.agenda),
        decisions=tuple(decisions),production_units=tuple({'id':u['pwu_id'], 'text':
            f'第 {index+1} 个生产单元：'+UNIT.get(u['state'],'等待推进')}
            for index,u in enumerate(projection.production_units)))


def admission_context_wording(context):
    """WIC vocabulary for a source-owned admission observation."""
    if not context or context.get('status') != 'NOT_READY':
        return ''
    labels={'PRODUCT_INTENT':'产品意图依据','PRODUCT_INVARIANT':'产品不变量依据',
            'APPROVED_DECISION':'已批准决定的依据','APPROVED_CONSTRAINT':'已批准约束的依据'}
    missing=context.get('missing_classes') or ()
    if missing:
        detail='、'.join(labels.get(c,'必要的生产依据') for c in missing)
        return f'生产准备受阻：当前缺少{detail}，尚未进入执行。'
    if context.get('conflict_references'):
        return '生产准备受阻：当前生产依据存在冲突，尚未进入执行。'
    if context.get('stale_risks'):
        return '生产准备受阻：当前生产依据需要重新核对，尚未进入执行。'
    return '生产准入条件尚未满足；已停止推进，尚未进入执行。'


def fact_wording(facts):
    """Deterministic WIC expression of typed owner facts, shared by normal views.

    State fields stay in owner_facts; these labels convey no new authority.
    Raw error strings, recommendations and findings are never rendered.
    """
    work=facts.get('work') or {}
    execution=facts.get('execution') or {}
    scheduling=facts.get('scheduling') or {}
    candidate=facts.get('candidate') or {}
    guardian=facts.get('guardian') or {}
    deliveries=facts.get('deliveries') or ()
    acceptance=deliveries[0].get('acceptance') if deliveries else None
    promotion=deliveries[0].get('source_promotion') if deliveries else None
    state=execution.get('status') or execution.get('state')
    running=EXECUTION.get(state,'尚未进入执行队列')
    if state=='QUEUED':
        progression=scheduling.get('progression_state')
        if progression=='INFRASTRUCTURE_UNAVAILABLE':running='执行资源暂不可用，恢复后自动继续'
        elif progression=='CAPACITY_WAIT':running=('执行资源正在维护，任务在等待' if scheduling.get('draining_worker_count') and not scheduling.get('compatible_slots') else '等待执行容量')
        elif progression=='SCHEDULING':running='已可执行，等待分配'
    verification=candidate.get('verification') or ()
    verified=bool(verification) and all(v.endswith(': PASS') for v in verification)
    verification_text=(f'独立验证已通过（{len(verification)} 项）' if verified else
        '独立验证未通过' if any(v.endswith(': FAIL') for v in verification) or execution.get('recovery_reason')=='VERIFICATION_FAILED' else
        '正在独立验证' if state=='VERIFYING' else '独立验证已通过' if state in {'VERIFIED','COMPLETED'} else '尚无验证结果')
    guardian_text=GUARDIAN.get(guardian.get('status'),'质量检查状态待确认')
    if guardian.get('status')=='RUNNING':guardian_text='质量检查正在重新验证'
    acceptance_text=('本次成果未被接受' if acceptance and acceptance.get('decision')!='ACCEPT' else
        '验收已记录；正式版本更新受阻，可重试同一决定' if acceptance and promotion and promotion.get('state')=='BLOCKED' else
        '验收已记录；正在更新正式版本' if acceptance and promotion and promotion.get('state')!='COMPLETED' else
        '已验收' if acceptance else '尚待你明确决定')
    ready=not guardian.get('required') or guardian.get('gate')=='PASS'
    review=('尚未形成候选成果，不能授权或验收。' if not candidate else
        '候选成果尚未通过独立验证，不能授权或验收。' if not verified else
        '机器验证已通过，质量检查尚未通过；当前版本还不能授权或验收。' if verified and not ready else
        '质量检查尚未通过；当前版本还不能授权或验收。' if not ready else
        '质量条件已满足；请查看预览与改动，再明确决定是否授权当前候选。')
    cloud=facts.get('cloud_deployment') or {}
    cloud_text={'SUCCEEDED':'部署成功','FAILED':'部署失败','ROLLED_BACK':'已回滚','NEEDS_HUMAN_ATTENTION':'部署受阻',
        'PRECHECK':'检查环境','STAGING':'传送成果','PREPARING':'正在部署','VERIFYING':'正在验证'}.get(cloud.get('state'),'未部署')
    blocker=cloud.get('blocker')
    blockers={'DEPLOYMENT_USER_NOT_FOUND':'历史尝试：目标 ECS 当时缺少部署用户 wattdeploy，部署尚未开始。Watt 现在会在新授权的部署尝试中自动评估并准备受支持的主机。',
        'PUBLIC_BUSINESS_VERIFICATION_REQUIRED':'目标机本地服务已启动，公网业务验证尚未通过。',
        'UNSUPPORTED_HOST_PROFILE':'目标系统不在当前自动部署支持范围内。',
        'HOST_PROFILE_CONFLICT':'这台 ECS 的现有主机状态与受控部署环境冲突，Watt 已安全停止。',
        'BLOCKED_APPROVED_PACKAGE_SOURCE':'主机无法从受控软件源准备所需组件，已停止且没有部署交付物。',
        'BLOCKED_APPROVED_PACKAGE_INSTALL':'主机所需组件未能安全安装，已停止且没有部署交付物。',
        'BLOCKED_ROOTLESS_SETUP':'非 root 容器运行时未能安全完成准备，已停止且没有部署交付物。',
        'BLOCKED_ROOTLESS_VERIFICATION':'非 root 容器运行时未能通过验证，已停止且没有部署交付物。'}
    return {'work':STATUS.get(work.get('status'),'尚无具体事项'),'execution':running,
        'verification':verification_text,'guardian':guardian_text,
        'candidate':acceptance_text if acceptance else '已形成，等待你授权' if candidate.get('authorization_pending') else '已形成，可查看' if candidate else '尚未形成',
        'acceptance':acceptance_text,'review':review,'cloud':cloud_text,
        'blocker':admission_context_wording(facts.get('admission_context')) or (blockers.get(blocker,'部署条件未满足，尚未通过验证。') if blocker else ''),
        'production_result':acceptance_text if acceptance else '机器验证通过；质量检查尚未通过，暂不能接受。' if verified and not ready else '候选成果已满足质量条件，等待你的明确决定。' if verified and ready else '当前成果仍需独立验证，尚未完成。'}


class HumanVisibleRealizationService:
    """WIC owns expression; owner records are copied read-only and never updated."""
    def __init__(self,database,realizer=None):
        self.database=database;self.realizer=realizer

    def realize(self,projection):
        table=wic_human_realizations
        with self.database.unit_of_work() as uow:
            # Cross-process fencing avoids one model call per simultaneous quadrant/read.
            lock=int(projection.basis_fingerprint[:15],16)
            uow.session.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':lock})
            old=uow.session.scalar(select(table.c.realization).where(table.c.basis_fingerprint==projection.basis_fingerprint))
            if old is not None:
                try:
                    validate_wording(projection, HumanVisibleWording.model_validate(old['wording']))
                    return old
                except ValueError:
                    pass  # Disposable expression cache must satisfy the current gate.
            wording=None;finding=None
            generate=getattr(self.realizer,'realize_human_projection',None)
            if callable(generate):
                for attempt in range(2):
                    try:
                        wording=validate_wording(projection,generate(projection,feedback=finding));break
                    except (ValueError,RuntimeError) as error:
                        finding=str(error)[:160];wording=None
            if wording is None:wording=validate_wording(projection,safe_wording(projection))
            result={'basis_fingerprint':projection.basis_fingerprint,'source_references':list(projection.source_references),
                'wording':wording.model_dump(mode='json'),'expression_finding':finding,
                'owner_facts':projection.owner_facts,'facts':fact_wording(projection.owner_facts)}
            uow.session.execute(insert(table).values(basis_fingerprint=projection.basis_fingerprint,
                work_id=(projection.owner_facts.get('work') or {}).get('work_id'),
                projection=projection.model_dump(mode='json'),realization=result).on_conflict_do_update(
                    index_elements=[table.c.basis_fingerprint],set_={
                        "projection":projection.model_dump(mode="json"),"realization":result}))
            uow.commit()
        return result


def cloud_presentation(deployment):
    """Derived WIC wording for the same Cloud owner facts, including detail views."""
    result=dict(deployment)
    labels=fact_wording({'cloud_deployment':deployment})
    result['human_visible']={'status':labels['cloud'],'blocker':labels['blocker']}
    return result


def cloud_error_wording(code):
    return {
        'CONNECTION_EXECUTION_GRANT_REQUIRED':'当前云连接缺少受控执行能力，请完成一次连接策略更新。',
        'SECURITY_GROUP_DISCOVERY_FAILED':'无法读取目标安全组，云连接的受控网络能力尚未验证。',
        'SECURITY_GROUP_RULE_READ_FAILED':'无法读取当前入站规则，尚未确认网络条件。',
        'PUBLIC_INGRESS_CREATE_FAILED':'精确入站规则未能建立，公网业务尚未通过验证。',
        'UNSUPPORTED_HOST_PROFILE':'目标系统不在当前自动部署支持范围内，请选择受支持的主机。',
        'HOST_PROFILE_CONFLICT':'主机现有状态无法安全自动准备，请选择另一台主机。',
    }.get(code,'本次云操作未能完成，请查看保留的证据；系统不会把它视为成功。')
