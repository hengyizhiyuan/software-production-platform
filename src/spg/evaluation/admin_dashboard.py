"""Read-only cockpit counts over canonical records; no new Quality authority."""
from datetime import datetime, timedelta, timezone
import json
from sqlalchemy import text
from spg.evaluation.contracts import QualityError
from spg.infrastructure.performance import span

LOCAL = timezone(timedelta(hours=8))


def period_start(period, observed_at):
    days = {'TODAY': 1, '7D': 7, '30D': 30}.get(period)
    if days is None:
        raise QualityError('DASHBOARD_PERIOD_NOT_SUPPORTED')
    return (observed_at.astimezone(LOCAL).replace(hour=0, minute=0, second=0, microsecond=0)
            - timedelta(days=days - 1)).astimezone(timezone.utc)


def metric(label, value, note):
    return {'label': label, 'value': value, 'note': note}


def dashboard(database, settings, period='TODAY'):
    observed_at = datetime.now(timezone.utc)
    start = period_start(period, observed_at)
    # One statement with bounded scalar aggregates. No full Work reconstruction,
    # Docker census, mutations, inferred completion, or metrics schema.
    sql = '''SELECT
      (SELECT count(*) FROM product_works WHERE created_at >= :since AND created_at <= :until) AS works,
      (SELECT count(*) FROM execution_events WHERE event_type='NativeExecutionStarted' AND created_at BETWEEN :since AND :until) AS executions,
      (SELECT count(*) FROM baseline_candidates WHERE sealed_at BETWEEN :since AND :until) AS candidates,
      (SELECT count(*) FROM work_delivery_acceptances WHERE payload->>'decision'='ACCEPT' AND created_at BETWEEN :since AND :until) AS accepted,
      (SELECT count(*) FROM work_delivery_manifests WHERE created_at BETWEEN :since AND :until) AS deliveries,
      (SELECT count(*) FROM cloud_deployments WHERE created_at BETWEEN :since AND :until) AS deployments,
      (SELECT count(*) FROM cloud_deployments WHERE state='SUCCEEDED' AND created_at BETWEEN :since AND :until) AS deployed,
      (SELECT count(*) FROM software_products WHERE lifecycle='ACTIVE') AS active_products,
      (SELECT count(*) FROM self_refine_events WHERE final_result='LOCAL_OBLIGATION_RECOVERED' AND created_at BETWEEN :since AND :until) AS recovered,
      (SELECT count(*) FROM human_authorizations WHERE authorized_at BETWEEN :since AND :until) AS interventions,
      (SELECT count(*) FROM quality_findings WHERE state<>'CLOSED' AND created_at BETWEEN :since AND :until) AS findings,
      (SELECT count(*) FROM quality_cases WHERE cohorts @> '["REGRESSION"]'::jsonb) AS regressions,
      (SELECT count(*) FROM verification_records WHERE result='FAIL' AND created_at BETWEEN :since AND :until) AS verification_failed,
      (SELECT percentile_cont(.95) WITHIN GROUP (ORDER BY extract(epoch FROM completed_at-created_at))
         FROM interaction_turns WHERE status='COMPLETED' AND created_at BETWEEN :since AND :until) AS turn_p95,
      (SELECT percentile_cont(.95) WITHIN GROUP (ORDER BY extract(epoch FROM started.created_at-queued.created_at))
         FROM execution_events started JOIN execution_events queued ON queued.attempt_id=started.attempt_id
         AND queued.event_type='NativeExecutionQueued' WHERE started.event_type='NativeExecutionStarted'
         AND started.created_at BETWEEN :since AND :until) AS queue_p95'''
    with database.unit_of_work() as u:
        values = dict(u.session.execute(text(sql), {'since': start, 'until': observed_at}).mappings().one())
    return {'period': period, 'from': start, 'to': observed_at, 'timezone': 'Asia/Shanghai',
        'production': [metric('新建 Work', values['works'], '按 Work 创建时间'),
            metric('本期创建 Work 当前完成', None, '未保存独立完成时间口径；不能用 Execution 或 Candidate 替代'),
            metric('PWU 执行', values['executions'], '实际 NativeExecutionStarted 事件'),
            metric('候选成果', values['candidates'], '按 Candidate 封存时间'),
            metric('Human 验收记录', values['accepted'], '明确 ACCEPT 验收记录数，非自动授权'),
            metric('交付成果', values['deliveries'], '持久化交付清单'),
            metric('部署尝试', values['deployments'], '包含失败历史'),
            metric('当前活跃 Product', values['active_products'], '当前 ACTIVE 存量，不代表期间使用人数')],
        'users': [metric('活跃 / 新增 / 回访用户', None, '未建立用户活动遥测；不以单一拥有者或 Work 数冒充'),
            metric('登录与活动', None, '目前认证不能提供完整登录与回访统计')],
        'quality': [metric('完成 Work 成功率', None, '缺少独立 Work 完成事件分母'),
            metric('永久回归场景', values['regressions'], '当前资产存量'),
            metric('期间发现且未关闭问题', values['findings'], 'Finding 观测数，不代表已评定严重等级'),
            metric('Self-Refine 恢复', values['recovered'], '明确局部义务恢复记录'),
            metric('Verification 失败', values['verification_failed'], '验证记录数，不冒充 Candidate 拦截数量'),
            metric('Human 授权', values['interventions'], '明确候选授权记录，非所有人工干预'),
            metric('部署成功 / 尝试', f"{values['deployed']} / {values['deployments']}", '期间创建尝试的当前状态，API success 不等于部署 PASS')],
        'experience': [metric('WIC 完整处理 P95', None if values['turn_p95'] is None else round(values['turn_p95'], 3), '秒；包含模型完成，非请求确认'),
            metric('PWU 入队至开始 P95', None if values['queue_p95'] is None else round(values['queue_p95'], 3), '秒；同一 Attempt 的真实事件')],
        'performance_qualification': performance_qualification(settings, start, observed_at)}


def performance_qualification(settings, start, end):
    path = settings.owner_runtime_store_root / 'qualifications/watt-core-performance-p0-v1/qualification-report-summary.json'
    try:
        with span('filesystem'):
            if not path.exists() or path.stat().st_size > 250000:
                return None
            report = json.loads(path.read_text())
        at = datetime.fromisoformat(report['observed_at'])
        if not start <= at <= end:
            return None
        http = report['ECS_loopback_http_after']
        human = report['human_perceived']['after_async_wording']
        return {'observed_at': at, 'revision': report['commit'],
            'scope': 'Performance P0 资格小样本；非线上全量，不能代表当前版本实时 SLA',
            'api': [{'path': r['path'], 'p95_seconds': r['p95'], 'samples': r['n'], 'errors': r['errors']} for r in http['read_api']],
            'pages': [{'route': p['route'], 'first_useful_ms': p['first_useful_page_ms']} for p in report['browser']['rows']],
            'ack_ms': human['public_ack_ms'], 'semantic_seconds': human['semantic_assessment_seconds'],
            'error_rate': sum(r['errors'] for r in http['read_api']) / sum(r['n'] for r in http['read_api'])}
    except (OSError, ValueError, KeyError, ZeroDivisionError, TypeError):
        return None
