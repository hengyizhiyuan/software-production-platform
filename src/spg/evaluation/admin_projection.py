"""Human projections of the existing Quality ledger; never a quality authority."""
from collections import Counter

OWNER_NAMES = {'WIC':'交流与表达','IRK':'意图理解','ECF':'生产上下文','SEARCH':'资料检索',
    'STEERING':'推进决策','PLANNING':'生产规划','PWU':'生产单元','EXECUTION':'执行',
    'VERIFICATION':'独立验证','GUARDIAN':'独立质量保证','CANDIDATE':'候选成果',
    'DEPLOYMENT':'部署','MODEL_ROUTING':'模型选择'}
FINDING_NAMES = {
    'MANAGED_GREENFIELD_CONTEXT_SOURCE_MISSING':'首次网站生产未取得合法产品上下文',
    'HUMAN_ATTENTION_AUTHORITY_INVALID':'没有实际人工决定却要求人工介入',
    'UNQUALIFIED_HUMAN_ATTENTION':'没有实际人工决定却要求人工介入',
    'CANONICAL_INVARIANT_BROKEN':'已治理的生产约束未得到满足',
    'ORACLE_ASSERTION_FAILED':'行为与已批准的场景预期不一致',
    'QUALIFICATION_FAILED':'场景验证未通过',
    'RECIPE_ORACLE_FAILED':'资格验证未满足已批准判据',
    'OWNER_LINEAGE_UNAVAILABLE':'缺少可追溯的生产 owner 证据',
    'OPTIONAL_DISCOVERY_REQUIRES_HUMAN':'可逆设计问题被误判为必需人工决定',
    'UNQUALIFIED_TEMPLATE_ATTENTION':'模板检查项产生了未经授权的人工关注',
    'UNATTRIBUTED_FAILURE':'发现问题，尚缺足够证据确定原因',
}


def issue_projection(cluster, later_results=(), cases=()):
    """A later PASS is requalification evidence, not permission to close a finding."""
    code = cluster.get('finding_code')
    owner = OWNER_NAMES.get(cluster.get('stage'), '尚未确定的环节')
    observed_titles=list(dict.fromkeys(r['title'] for r in later_results if str(r.get('case_id')) in cluster.get('affected_cases',[]) and r.get('title')))
    title = FINDING_NAMES.get(code, owner + '未符合场景预期')
    if observed_titles: title += '：'+'、'.join(observed_titles[:2])
    qualified = [r for r in later_results if str(r.get('case_id')) in cluster.get('affected_cases', [])
        and r.get('state') == 'PASS' and str(r.get('created_at')) > str(cluster.get('last_seen'))]
    catalog = {str(c['id']): c for c in cases}
    closures = []
    for occurrence in cluster.get('occurrences', ()):
        if occurrence['state'] == 'CLOSED':
            continue
        for row in later_results:
            case = catalog.get(str(row.get('case_id')), {})
            cohorts = case.get('cohorts', ())
            eligible = (occurrence.get('regression_case_id') == str(row.get('case_id')) and 'REGRESSION' in cohorts
                or occurrence.get('case_id') == str(row.get('case_id')) and 'FRESH_HOLDOUT' in cohorts)
            if eligible and row.get('state') == 'PASS' and str(row['created_at']) > str(occurrence['created_at']):
                closures.append({'finding_id': occurrence['id'], 'case_run_id': str(row['id']), 'title': row.get('title')})
                break
    divergence = next((r.get('divergence_stage') for r in later_results
        if str(r['id']) in cluster.get('findings_case_runs', ()) and r.get('divergence_stage')), None)
    return {**cluster, 'earliest_divergence_label': OWNER_NAMES.get(divergence, '尚无独立最早偏离证据'), 'case_titles': [catalog[c]['definition']['title'] for c in cluster.get('affected_cases', ()) if c in catalog],
        'eligible_closures': closures, 'title':title, 'owner_label':owner,
        'severity_label':'需要审查（尚未评定严重程度）',
        'repair_label': '已治理关闭' if cluster.get('closure_state') == 'CLOSED' else
            '后续验证通过，历史问题记录仍待治理关闭' if qualified else '尚无后续通过证据',
        'requalified_case_runs':[str(r['id']) for r in qualified],
        'observation_label':f"{cluster.get('occurrence_count', 0)} 次观测，影响 {len(cluster.get('affected_cases', []))} 个场景",
        'regression_label':'已纳入历史回归' if cluster.get('regression_status') == 'PERMANENT_CASE' else '尚未纳入历史回归'}


def outcome_projection(case):
    evaluations = case.get('evaluations', [])
    protected = any(e.get('details', {}).get('production_failed_correctly') or
        e.get('details', {}).get('expected_safety_block') for e in evaluations)
    # Only explicit oracle evidence establishes an intentionally blocked production.
    return {'quality_state':case.get('state', 'UNKNOWN'),
        'quality_label':{'PASS':'场景符合预期','FAIL':'场景未符合预期','BLOCKED':'资格验证受阻',
            'UNKNOWN':'资格不足','RUNNING':'场景验证中'}.get(case.get('state'), '尚无完成证据'),
        'production_label':'错误生产被正确阻止；场景符合预期' if protected and case.get('state') == 'PASS'
            else '生产结果需查看实际 owner 证据；场景通过不等于产物已交付',
        'divergence_label':OWNER_NAMES.get(case.get('lineage', {}).get('divergence', {}).get('stage'), '尚未观测到可归因偏离'),
        'safety_block_proven':bool(protected)}


def version_comparison(current, previous):
    """Compare the same exact case version and policy, not unrelated campaign totals."""
    changes = []
    old = {(str(c['case_version_id']), c.get('policy_fingerprint')):c for c in previous}
    for c in current:
        before = old.get((str(c['case_version_id']), c.get('policy_fingerprint')))
        if before is None:
            changes.append({'case_id':str(c['case_id']), 'title':c['title'], 'kind':'NO_COMPARABLE_BASIS',
                'label':'没有相同场景版本和配置的比较依据'})
        elif c['state'] != before['state']:
            regression = before['state'] == 'PASS' and c['state'] != 'PASS'
            changes.append({'case_id':str(c['case_id']), 'title':c['title'],
                'kind':'REGRESSION' if regression else 'IMPROVED' if c['state'] == 'PASS' else 'CHANGED',
                'before':before['state'], 'after':c['state'],
                'label':'历史问题重新出现' if regression else '本次符合预期，过去未通过' if c['state'] == 'PASS' else '结果发生变化'})
    return changes


def cockpit_projection(overview, ledger):
    revision = overview['watt_revision']
    revisions = list(dict.fromkeys(r['watt_revision'] for r in ledger))
    basis = revision if revision in revisions else (revisions[0] if revisions else None)
    def latest(rev):
        out = {}
        for r in ledger:
            if r['watt_revision'] == rev and not r.get('experiment_id'):
                out.setdefault(str(r['case_version_id']), r)
        return list(out.values())
    current = latest(basis)
    previous_revision = next((v for v in revisions if v != basis), None)
    changes = version_comparison(current, latest(previous_revision))
    issues = [issue_projection(c, ledger, overview['quality'].get('cases', ())) for c in overview['quality']['clusters']]
    opened = [i for i in issues if i['closure_state'] != 'CLOSED']
    regressions = [c for c in changes if c['kind'] == 'REGRESSION']
    qualified = sum(r['state'] == 'PASS' for r in current)
    counts = Counter(c for r in current for c in r.get('cohorts', []))
    condition = '数据不足' if not current else '发现回退' if regressions else '资格不足' if basis != revision or qualified < len(current) else '有待处理问题' if opened else '正常'
    briefing = f"当前结论：{condition}。"
    if current:
        briefing += f"最近可读取的验证基线有 {qualified}/{len(current)} 个场景符合预期。"
    if basis != revision:
        briefing += '当前运行版本尚无此账本中的完整资格记录，不能沿用旧版本宣称合格。'
    briefing += f"当前有 {len(opened)} 个不同问题记录待审查。"
    comparable = previous_revision and any((str(r['case_version_id']),r.get('policy_fingerprint')) in {(str(p['case_version_id']),p.get('policy_fingerprint')) for p in latest(previous_revision)} for r in current)
    briefing += f"观察到 {len(regressions)} 个可比场景回退。" if comparable else '尚无相同场景版本和策略的历史依据，无法判断质量变化。'
    active = [r for r in overview['quality']['runs'] if r['state'] in ('QUEUED','RUNNING','PAUSE_REQUESTED','PAUSED','STOPPING')]
    return {'condition':condition, 'briefing':briefing, 'issues':issues, 'attention_count':len(opened),
        'current_revision':revision, 'evidence_revision':basis, 'previous_revision':previous_revision,
        'qualified':qualified, 'observed':len(current), 'cohort_counts':dict(counts), 'version_changes':changes,
        'active_runs':active, 'coverage_note':'按精确场景版本和策略比较；缺少记录不代表通过。账本展示最近 500 次非实验场景观测。',
        'regression_count':len(regressions)}


def run_summaries(database, runs, campaigns, ledger):
    """Read-only human summaries; exact case version/policy comparison is retained."""
    from sqlalchemy import text
    if not runs:
        return []
    catalog = {str(c['id']): c for c in campaigns}
    with database.unit_of_work() as u:
        rows = u.session.execute(text("""
          SELECT m.run_id, v.definition->>'title' AS title, m.cohorts, m.disposition,
            a.state FROM quality_run_members m JOIN quality_case_versions v ON v.id=m.case_version_id
          LEFT JOIN LATERAL (SELECT state FROM quality_case_runs WHERE campaign_run_id=m.run_id
            AND case_version_id=m.case_version_id ORDER BY attempt DESC LIMIT 1) a ON true
          WHERE m.run_id=ANY(CAST(:ids AS uuid[])) ORDER BY m.run_id,m.ordinal
        """), {'ids': [str(r['id']) for r in runs]}).mappings().all()
    out = []
    for run in runs:
        members = [m for m in rows if m['run_id'] == run['id']]
        def latest(observations):
            unique = {}
            for row in sorted(observations, key=lambda r: str(r['created_at']), reverse=True):
                unique.setdefault((str(row['case_version_id']), row.get('policy_fingerprint')), row)
            return list(unique.values())
        current = latest(r for r in ledger if str(r.get('campaign_run_id')) == str(run['id']))
        previous = latest(r for r in ledger if not r.get('experiment_id')
            and str(r['created_at']) < str(run['created_at']))
        changes = version_comparison(current, previous)
        comparable = not run.get('experiment_id') and any(
            (str(r['case_version_id']), r.get('policy_fingerprint')) ==
            (str(p['case_version_id']), p.get('policy_fingerprint')) for r in current for p in previous)
        if run.get('experiment_id'):
            changes = []
        campaign = catalog.get(str(run.get('campaign_id')), {})
        definition = campaign.get('definition') or {}
        out.append({**run, 'human_summary': {
            'title': campaign.get('name') or definition.get('name') or '已保存的资格验证',
            'why': '重跑既有验证的选定范围' if run.get('parent_run_id') else '比较候选策略' if run.get('experiment_id') else definition.get('rationale') or '受治理的质量资格验证',
            'coverage_count': len(members), 'coverage': [m['title'] for m in members],
            'cohorts': sorted({c for m in members for c in m['cohorts']}),
            'passed': sum(m['state'] == 'PASS' for m in members),
            'attention': sum(m['state'] in ('FAIL','BLOCKED','UNKNOWN') for m in members),
            'changes': changes, 'comparison_available': comparable, 'comparison_scope': '最近 500 份账本、相同 Case 版本与策略；没有依据不判断改善'}})
    return out


def assurance_summary(database, assurance):
    """Summarize exact stored candidates; acceptance remains in the Product flow."""
    from sqlalchemy import text
    with database.unit_of_work() as u:
        rows = u.session.execute(text('''SELECT c.id,c.fingerprint,c.sealed_at,
          EXISTS(SELECT 1 FROM human_authorizations a WHERE a.candidate_id=c.id
            AND a.candidate_fingerprint=c.fingerprint) AS authorized,
          jsonb_array_length(c.verification_record_ids) AS required_verifications,
          (SELECT count(*) FROM jsonb_array_elements_text(c.verification_record_ids) ref(id)
            JOIN verification_records v ON v.id::text=ref.id WHERE v.result='PASS') AS passed_verifications,
          (SELECT count(*) FROM jsonb_array_elements_text(c.verification_record_ids) ref(id)
            JOIN verification_records v ON v.id::text=ref.id WHERE v.result='FAIL') AS failed_verifications
          FROM baseline_candidates c WHERE c.condition='SEALED' ORDER BY c.sealed_at DESC LIMIT 100''')).mappings().all()
    latest = {}
    for record in sorted(assurance['results'], key=lambda r: str(r.get('assessed_at') or ''), reverse=True):
        latest.setdefault((str(record['candidate_id']), record.get('candidate_fingerprint')), record)
    pending = []
    for row in rows:
        result = latest.get((str(row['id']), row['fingerprint']))
        if (result and result.get('gate') == 'PASS' and not row['authorized']
                and row['required_verifications'] > 0 and row['required_verifications'] == row['passed_verifications']):
            pending.append({'candidate_id': str(row['id']), 'sealed_at': row['sealed_at'], 'guardian': result,
                'verification_count': row['passed_verifications'], 'state_label': '待你审阅与授权；交付后再正式验收'})
    return {'verification_blocked_candidates': sum(row['failed_verifications'] > 0 for row in rows),
        'pending_review': pending, 'blocked_candidates': sum(r.get('gate') in ('FAIL', 'FAIL_REPAIRABLE', 'BLOCKED') for r in latest.values()),
        'unknown_candidates': sum(r.get('gate') not in ('PASS', 'FAIL', 'FAIL_REPAIRABLE', 'BLOCKED') for r in latest.values()),
        'observation_count': len(latest), 'scope': '最近可读取的 20 份 Guardian 结果及 100 个封存候选；不冒充全量拦截统计',
        'false_positive': None, 'health_note': '结果存储可读取不等于 owner 实时健康；独立质量评价另列。'}
