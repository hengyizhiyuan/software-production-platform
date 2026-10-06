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


def issue_projection(cluster, later_results=()):
    """A later PASS is requalification evidence, not permission to close a finding."""
    code = cluster.get('finding_code')
    owner = OWNER_NAMES.get(cluster.get('stage'), '尚未确定的环节')
    observed_titles=list(dict.fromkeys(r['title'] for r in later_results if str(r.get('case_id')) in cluster.get('affected_cases',[]) and r.get('title')))
    title = FINDING_NAMES.get(code, owner + '未符合场景预期')
    if observed_titles: title += '：'+'、'.join(observed_titles[:2])
    qualified = [r for r in later_results if str(r.get('case_id')) in cluster.get('affected_cases', [])
        and r.get('state') == 'PASS' and str(r.get('created_at')) > str(cluster.get('last_seen'))]
    return {**cluster, 'title':title, 'owner_label':owner,
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
    issues = [issue_projection(c, ledger) for c in overview['quality']['clusters']]
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
