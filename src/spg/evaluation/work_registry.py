"""Bounded Work discovery from canonical owner rows; never hydrates Work/Trace."""
from __future__ import annotations

import json
from sqlalchemy import text
from spg.evaluation.contracts import QualityError
from spg.evaluation.production_trace import safe

STATE_LABELS = {'COMMUNICATING':'尚在沟通','PREPARING':'准备生产','QUEUED':'等待执行',
    'RUNNING':'执行中','REPAIRING':'自修复中','VERIFYING':'验证中','REVIEWING':'候选待审查',
    'WAITING_HUMAN':'等待 Human 决定','WAITING_ACCEPTANCE':'等待 Human 验收',
    'COMPLETED':'已完成','BLOCKED':'受阻','FAILED':'失败','STOPPED':'已停止'}
BUCKETS = {'WAITING_HUMAN':'WAITING','WAITING_ACCEPTANCE':'WAITING','COMPLETED':'COMPLETED',
    'BLOCKED':'PROBLEM','FAILED':'PROBLEM','STOPPED':'PROBLEM'}

# Set aggregates are shared by pagination/count. No per-row application query,
# repository inspection, qualification filesystem scan, or full Work projection.
FACTS_SQL = '''
WITH bindings AS (
 SELECT DISTINCT work_id,production_run_id FROM work_runtime_bindings
), current_binding AS (SELECT DISTINCT ON(work_id) * FROM work_runtime_bindings ORDER BY work_id,cycle_number DESC), units AS (
 SELECT b.work_id,p.id,p.production_run_id FROM bindings b
 JOIN production_work_units p ON p.production_run_id=b.production_run_id
), activity AS (
 SELECT id work_id,updated_at at,'Work 记录更新' event FROM product_works
 UNION ALL SELECT work_id,created_at,'Work 意图修订' FROM work_reality_revisions
 UNION ALL SELECT work_id,created_at,'进入受治理生产' FROM work_runtime_bindings
 UNION ALL SELECT work_focus_id,created_at,'Human / Watt 交流' FROM interaction_records WHERE work_focus_id IS NOT NULL
 UNION ALL SELECT work_id,enqueued_at,'进入执行队列' FROM executor_queue
 UNION ALL SELECT u.work_id,e.created_at,e.event_type FROM units u JOIN execution_events e ON e.pwu_id=u.id
 UNION ALL SELECT work_id,updated_at,'Self-Refine 状态更新' FROM self_refine_events
 UNION ALL SELECT p.work_id,e.created_at,'Steering 推进记录' FROM steering_plans p JOIN steering_history_events e ON e.steering_plan_id=p.id
 UNION ALL SELECT b.work_id,c.sealed_at,'Candidate 已封存' FROM bindings b JOIN baseline_candidates c ON c.production_run_id=b.production_run_id
 UNION ALL SELECT b.work_id,a.authorized_at,'Human 精确候选授权' FROM bindings b JOIN baseline_candidates c ON c.production_run_id=b.production_run_id JOIN human_authorizations a ON a.candidate_id=c.id AND a.candidate_fingerprint=c.fingerprint
 UNION ALL SELECT work_id,created_at,'交付 Manifest 已保存' FROM work_delivery_manifests
 UNION ALL SELECT m.work_id,a.created_at,'Human 交付验收' FROM work_delivery_manifests m JOIN work_delivery_acceptances a ON a.manifest_id=m.id
 UNION ALL SELECT m.work_id,d.updated_at,'部署状态更新' FROM work_delivery_manifests m JOIN cloud_deployments d ON d.manifest_id=m.id
), latest_activity AS (SELECT DISTINCT ON(work_id) work_id,at,event FROM activity ORDER BY work_id,at DESC,event),
counts AS (SELECT work_id,count(*) pwu_count FROM units GROUP BY work_id),
repairs AS (SELECT work_id,count(*) self_refine_count,max(updated_at) repair_at FROM self_refine_events GROUP BY work_id),
last_repair AS (SELECT DISTINCT ON(work_id) work_id,status,final_result,diagnosis_summary,failure_family FROM self_refine_events ORDER BY work_id,created_at DESC,id DESC),
queue AS (SELECT DISTINCT ON(work_id) work_id,condition,attempt_id,wait_reason FROM executor_queue ORDER BY work_id,CASE WHEN condition IN ('EXECUTING','ALLOCATED') THEN 0 WHEN condition IN ('QUEUED','REQUEUED') THEN 1 ELSE 2 END,enqueued_at DESC,id DESC),
candidates AS (SELECT DISTINCT ON(b.work_id) b.work_id,c.id,c.condition,c.fingerprint,c.sealed_at,
 EXISTS(SELECT 1 FROM human_authorizations a WHERE a.candidate_id=c.id AND a.candidate_fingerprint=c.fingerprint) authorized
 FROM bindings b JOIN baseline_candidates c ON c.production_run_id=b.production_run_id ORDER BY b.work_id,c.sealed_at DESC,c.id DESC),
manifests AS (SELECT DISTINCT ON(work_id) work_id,id FROM work_delivery_manifests ORDER BY work_id,created_at DESC,id DESC),
acceptance AS (SELECT DISTINCT ON(manifest_id) manifest_id,id,payload->>'decision' decision FROM work_delivery_acceptances ORDER BY manifest_id,created_at DESC,id DESC),
deployment AS (SELECT DISTINCT ON(m.work_id) m.work_id,d.id,d.state FROM work_delivery_manifests m JOIN cloud_deployments d ON d.manifest_id=m.id ORDER BY m.work_id,d.created_at DESC,d.id DESC),
steps AS (SELECT DISTINCT ON(r.work_id) r.work_id,s.type,s.objective,r.id revision_id FROM steering_plan_revisions r JOIN steering_steps s ON s.steering_plan_revision_id=r.id WHERE r.condition='ACTIVE' AND s.state='CURRENT' ORDER BY r.work_id,r.revision_number DESC,s.position),
decisions AS (SELECT DISTINCT ON(r.work_id) r.work_id,d.steering_outcome,d.reason,d.reality_refs,d.steering_plan_revision_id FROM steering_plan_revisions r JOIN steering_decisions d ON d.steering_plan_revision_id=r.id WHERE r.condition='ACTIVE' ORDER BY r.work_id,d.created_at DESC,d.id DESC),
trusted AS (SELECT DISTINCT ON(b.work_id) b.work_id,c.id,b.work_reality_revision_id,c.id::text commit_ref,
 p.completion_contract->'task_contract'->>'task_mode' task_mode,
 EXISTS(SELECT 1 FROM completion_evaluations e WHERE e.work_unit_id=b.work_unit_id AND e.outcome='PRODUCED') produced,
 EXISTS(SELECT 1 FROM verification_records v WHERE v.proposed_snapshot_id=cand.proposed_snapshot_id) has_verification,
 NOT EXISTS(SELECT 1 FROM verification_records v WHERE v.proposed_snapshot_id=cand.proposed_snapshot_id AND v.result<>'PASS') verification_pass,
 effect.state integration_state
 FROM current_binding b LEFT JOIN runtime_commits c ON c.production_run_id=b.production_run_id
 LEFT JOIN production_work_units p ON p.id=b.work_unit_id
 LEFT JOIN baseline_candidates cand ON cand.id=c.candidate_id
 LEFT JOIN repository_integration_effects effect ON effect.id=c.repository_integration_effect_id ORDER BY b.work_id,c.committed_at DESC,c.id DESC),
runtime_progress AS (
 SELECT b.work_id,e.outcome completion_outcome,ad.outcome admissibility_outcome,report.outcome provider_outcome
 FROM current_binding b JOIN product_works w ON w.id=b.work_id
 LEFT JOIN LATERAL (SELECT * FROM execution_attempts a WHERE a.work_unit_id=b.work_unit_id ORDER BY generation DESC LIMIT 1) a ON true
 LEFT JOIN LATERAL (SELECT * FROM completion_evaluations e WHERE e.attempt_id=a.id ORDER BY created_at DESC,id DESC LIMIT 1) e ON true
 LEFT JOIN proposed_repository_snapshots prop ON prop.completion_evaluation_id=e.id
 LEFT JOIN production_admissibility_records ad ON ad.proposed_snapshot_id=prop.id
 LEFT JOIN execution_dispatches disp ON disp.attempt_id=a.id
 LEFT JOIN provider_execution_reports report ON report.dispatch_id=disp.id
 WHERE w.current_work_reality_revision_id IS NULL OR b.work_reality_revision_id=w.current_work_reality_revision_id
), findings AS (SELECT q.lineage->>'work_id' work_ref,count(f.id) FILTER(WHERE f.state<>'CLOSED') open_finding_count FROM quality_case_runs q LEFT JOIN quality_findings f ON f.case_run_id=q.id WHERE q.lineage ? 'work_id' GROUP BY q.lineage->>'work_id'),
pulses AS (SELECT key::uuid work_id,value facts FROM jsonb_each(CAST(:pulses AS jsonb))),
facts AS (
 SELECT w.id work_id,w.product_id,p.name product_name,w.refined_title,w.raw_user_requirement,w.desired_outcome,w.condition,w.work_mode,w.created_at,w.updated_at,a.at latest_activity_at,a.event latest_event_label,f.open_finding_count,
 w.current_work_reality_revision_id,coalesce(n.pwu_count,0) pwu_count,coalesce(r.self_refine_count,0) self_refine_count,
 q.condition queue_condition,q.attempt_id,q.wait_reason,c.id candidate_id,c.condition candidate_state,c.authorized,c.fingerprint candidate_fingerprint,
 m.id manifest_id,ac.id acceptance_id,ac.decision acceptance_decision,d.id deployment_id,d.state deployment_state,
 s.type stage,s.objective stage_objective,ds.steering_outcome,ds.reason steering_reason,
 (ds.reality_refs @> jsonb_build_array(jsonb_build_object('kind','WORK_REALITY_REVISION','identity',w.current_work_reality_revision_id::text))) decision_matches_revision,
 progress.completion_outcome,progress.admissibility_outcome,progress.provider_outcome,
 lr.status repair_status,lr.final_result repair_result,lr.diagnosis_summary repair_summary,lr.failure_family,
 pulse.facts->>'stop_reason' stop_reason,pulse.facts->>'active' active,
 (t.id IS NOT NULL AND ((w.work_mode='IMMEDIATE_PRODUCTION') OR
 (ds.steering_outcome='COMPLETE' AND coalesce(t.task_mode,'')<>'DESIGN_ARTIFACT' AND t.produced AND t.has_verification AND t.verification_pass AND t.integration_state='CONVERGED' AND t.work_reality_revision_id=w.current_work_reality_revision_id
 AND ds.reality_refs @> jsonb_build_array(jsonb_build_object('kind','RUNTIME_COMMIT','identity',t.commit_ref))))) complete
 FROM product_works w LEFT JOIN software_products p ON p.id=w.product_id
 LEFT JOIN latest_activity a ON a.work_id=w.id LEFT JOIN counts n ON n.work_id=w.id
 LEFT JOIN repairs r ON r.work_id=w.id LEFT JOIN last_repair lr ON lr.work_id=w.id
 LEFT JOIN queue q ON q.work_id=w.id LEFT JOIN candidates c ON c.work_id=w.id
 LEFT JOIN manifests m ON m.work_id=w.id LEFT JOIN acceptance ac ON ac.manifest_id=m.id
 LEFT JOIN deployment d ON d.work_id=w.id LEFT JOIN steps s ON s.work_id=w.id
 LEFT JOIN decisions ds ON ds.work_id=w.id LEFT JOIN trusted t ON t.work_id=w.id
 LEFT JOIN runtime_progress progress ON progress.work_id=w.id LEFT JOIN findings f ON f.work_ref=w.id::text LEFT JOIN pulses pulse ON pulse.work_id=w.id
 WHERE (p.owner_id=:owner OR w.product_id IS NULL) AND (CAST(:product AS uuid) IS NULL OR w.product_id=CAST(:product AS uuid))
), classified AS (
 SELECT *,CASE
 WHEN condition='DISCARDED' THEN 'STOPPED'
 WHEN condition='REJECTED' THEN 'BLOCKED'
 WHEN complete THEN 'COMPLETED'
 WHEN stop_reason='HUMAN_ATTENTION' OR (steering_outcome='HUMAN_ATTENTION' AND (current_work_reality_revision_id IS NULL OR decision_matches_revision)) OR condition='AWAITING_APPROVAL' THEN 'WAITING_HUMAN'
 WHEN queue_condition IN ('EXECUTING','ALLOCATED') AND repair_status='OPEN' AND repair_result IS NULL THEN 'REPAIRING'
 WHEN queue_condition IN ('EXECUTING','ALLOCATED') THEN 'RUNNING'
 WHEN queue_condition IN ('QUEUED','REQUEUED') THEN 'QUEUED'
 WHEN stop_reason IN ('BLOCKED','CAPABILITY_UNAVAILABLE','NO_PROGRESS','TRANSITION_BOUND') THEN 'BLOCKED'
 WHEN queue_condition='FAILED' OR provider_outcome='FAILURE' THEN 'FAILED'
 WHEN completion_outcome='NOT_PRODUCED' OR (admissibility_outcome IS NOT NULL AND admissibility_outcome<>'ADMISSIBLE') THEN 'BLOCKED'
 WHEN queue_condition IN ('CANCELLED','STOPPED','INTERRUPTED') THEN 'STOPPED'
 WHEN manifest_id IS NOT NULL AND acceptance_id IS NULL THEN 'WAITING_ACCEPTANCE'
 WHEN candidate_id IS NOT NULL AND NOT authorized THEN 'REVIEWING'
 WHEN queue_condition='COMPLETED' THEN 'VERIFYING'
 WHEN condition IN ('PRE_WORK','DRAFT','NEEDS_REFINEMENT') THEN 'COMMUNICATING'
 ELSE 'PREPARING' END state FROM facts
), scoped AS (
 SELECT * FROM classified WHERE :filter='ALL'
 OR (:filter='ACTIVE' AND state IN ('COMMUNICATING','PREPARING','QUEUED','RUNNING','REPAIRING','VERIFYING','REVIEWING'))
 OR (:filter='WAITING' AND state IN ('WAITING_HUMAN','WAITING_ACCEPTANCE'))
 OR (:filter='PROBLEM' AND state IN ('BLOCKED','FAILED','STOPPED'))
 OR (:filter='COMPLETED' AND state='COMPLETED')
)
'''


def work_summary(row):
    r=dict(row)
    r['title']=r.get('refined_title') or r.get('desired_outcome') or r['raw_user_requirement']
    r['state_label']=STATE_LABELS[r['state']]
    r['bucket']=BUCKETS.get(r['state'],'ACTIVE')
    r['stage_label']={'DESIGN':'设计','REFINE':'完善方向','PRODUCE':'生产','VERIFY_ACCEPT':'验证与验收','COMPLETE':'收尾'}.get(r.get('stage'),'阶段未记录')
    r['result_label']=('Work 已完成' if r['complete'] else '已保存交付 Manifest' if r.get('manifest_id') else 'Candidate 已封存' if r.get('candidate_id') else '尚未形成 Candidate')
    r['issue_hint']=(f"部署 {r['deployment_state']}；打开 Trace 核对" if r.get('deployment_state') in {'FAILED','BLOCKED'} else None) or ((r.get('repair_summary') or r.get('failure_family') or r.get('stop_reason') or r.get('wait_reason')) if r['bucket']=='PROBLEM' else None)
    if r.get('open_finding_count'):r['issue_hint']=f"{r['open_finding_count']} 项未关闭问题"
    r['acceptance_label']=r.get('acceptance_decision') or ('等待验收记录' if r.get('manifest_id') else '尚无验收记录')
    from spg.evaluation.production_trace import EVENT_LABELS
    r['latest_event']=EVENT_LABELS.get(r.get('latest_event_label'),r.get('latest_event_label')) or '最新记录时间见时间列'
    r['trace_url']=f"/admin/trace?kind=work&entity={r['work_id']}"
    return safe(r)


class WorkRegistryService:
    def __init__(self,database):self.database=database

    def list(self,owner,*,filter='ALL',product=None,limit=50,offset=0,pulses=None):
        if filter not in {'ALL','ACTIVE','WAITING','PROBLEM','COMPLETED'} or not 1<=limit<=100 or offset<0:
            raise QualityError('WORK_REGISTRY_QUERY_NOT_SUPPORTED')
        args={'owner':owner,'filter':filter,'product':None if product is None else str(product),
              'limit':limit,'offset':offset,'pulses':json.dumps(pulses or {})}
        with self.database.unit_of_work() as u:
            total=u.session.scalar(text(FACTS_SQL+'SELECT count(*) FROM scoped'),args)
            rows=u.session.execute(text(FACTS_SQL+'SELECT * FROM scoped ORDER BY latest_activity_at DESC,work_id DESC LIMIT :limit OFFSET :offset'),args).mappings().all()
        return {'items':[work_summary(r) for r in rows],'total':total,'limit':limit,'offset':offset,
                'filter':filter,'next_offset':offset+limit if offset+limit<total else None,
                'scope':'当前 Admin owner 的全部 Product Work；未绑定 Product 的历史 Work 属于现有单 owner 管理环境。',
                'note':'只投影已保存的 owner 事实与当前 Steering 观测；未知保证状态不视为通过。'}

    def get(self,owner,work_id,*,pulses=None):
        args={'owner':owner,'product':None,'filter':'ALL','pulses':json.dumps(pulses or {}),'wid':work_id}
        with self.database.unit_of_work() as u:
            row=u.session.execute(text(FACTS_SQL+'SELECT * FROM classified WHERE work_id=:wid'),args).mappings().first()
        if row is None:raise QualityError('TRACE_SOURCE_NOT_FOUND')
        return work_summary(row)
