"""A bounded reviewed pilot over canonical owners, not a second Case corpus."""
from spg.evaluation.catalog import Recipe
from spg.evaluation.contracts import CaseDefinition, Cohort, Stage, QualityError

PILOT = (
    Recipe('pilot-greenfield', '新建有验证的静态 Web Product', Stage.EXECUTION,
        'tests/integration/test_quality_pilot_production.py::test_pilot_greenfield',
        'Human intent admits Work and managed source; executable Web verification precedes Candidate'),
    Recipe('pilot-brownfield', '已有项目的精确单目标修改', Stage.ACCEPTANCE_PROMOTION,
        'tests/integration/test_quality_pilot_production.py::test_pilot_brownfield',
        'A bounded README change consumes the exact imported accepted revision and produces a qualified Candidate'),
    Recipe('pilot-live-search', '用实时官方版本信息生成页面', Stage.SEARCH,
        'tests/integration/test_quality_pilot_production.py::test_pilot_live_search',
        'Aliyun live Search and fetched official reference drive the produced page; references do not acquire project source'),
    Recipe('pilot-repository-only', '只依据仓库修改的封存场景', Stage.EXECUTION,
        'tests/integration/test_quality_pilot_production.py::test_pilot_repository_only',
        'A fresh exact repository-only modification executes without any external Search'),
    Recipe('pilot-independent-roots', '独立 PWU 与有限容量', Stage.PWU,
        'tests/integration/test_quality_pilot_production.py::test_pilot_independent_roots',
        'Two independent PWUs are parallel-ready but exact leases enforce one executing slot'),
    Recipe('pilot-dependency', '精确前序结果的依赖链', Stage.PWU,
        'tests/integration/test_quality_pilot_production.py::test_pilot_dependency',
        'Each successor consumes the qualified predecessor source and no dependent unit executes early'),
    Recipe('pilot-join', '两路结果显式汇合并验证', Stage.PWU,
        'tests/integration/test_quality_pilot_production.py::test_pilot_join',
        'Independent roots qualify before explicit source reconciliation and final Candidate retains lineage'),
    Recipe('pilot-negative-verification', '预期失败的行为验证', Stage.VERIFICATION,
        'tests/integration/test_quality_pilot_production.py::test_pilot_negative_verification',
        'The deliberately incorrect boundary fails executable verification and cannot publish software'),
    Recipe('pilot-guardian', '独立判据核对 Guardian 门禁', Stage.GUARDIAN,
        'tests/integration/test_quality_pilot_production.py::test_pilot_guardian',
        'Default Guardian gates exact Candidate before Human acceptance; independent executable oracles evaluate it'),
    Recipe('pilot-continuous-work', '待决 Candidate 不阻止独立新 Work', Stage.WIC,
        'tests/integration/test_quality_pilot_production.py::test_pilot_continuous_work',
        'A pending exact Candidate and its Work remain unchanged when an independent Work is admitted for the same Product'),
)
PILOT_KEYS = tuple(r.key for r in PILOT)


def register_pilot(service):
    if not service.settings.runtime_revision:
        raise QualityError('WATT_VERSION_NOT_BOUND')
    # Reopening the control page does not generate a new Holdout or case identity.
    existing = next((c for c in service.campaigns() if c['key'] == 'quality-evolution-pilot-v1'), None)
    if existing:
        return existing
    import secrets
    salt = secrets.token_hex(8)
    selected = []
    for i, r in enumerate(PILOT, start=1):
        fresh = r.key == 'pilot-repository-only'
        definition = CaseDefinition(key='watt.' + r.key, title=r.title,
            source='FRESH_HOLDOUT' if fresh else 'QUALIFICATION_MUTATION' if i == 8 else 'CORE_PILOT',
            motive=r.title, invariants=(r.invariant,), stage=r.stage, runner_key=r.key,
            context={'execution_environment':'ISOLATED_QUALIFICATION', 'pilot_ordinal':i,
                'expected_product_outcome':'VERIFICATION_FAILED' if i == 8 else 'QUALIFIED_OBLIGATION',
                'executor':'reviewed deterministic qualification executor; live compiler/provider explicitly declared per receipt'},
            provenance=(r.selector, 'quality:pilot:generated-at-revision:' + service.settings.runtime_revision),
            cohorts=(Cohort.FRESH_HOLDOUT,) if fresh else (Cohort.GOLDEN, Cohort.REGRESSION) if i in {6,10} else (Cohort.GOLDEN,),
            private_material={'replacement':'Repository-only pilot ' + salt,
                'expected_search_calls':0} if fresh else {})
        selected.append(service.register_case(definition)['id'])
    return service.register_campaign('quality-evolution-pilot-v1', 'Quality Evolution Pilot v1 — 10 Cases', selected)


def register_control_regression(service):
    from spg.evaluation.catalog import recipes
    r=recipes()['quality-control-regression']
    v=service.register_case(CaseDefinition(key='watt.'+r.key,title=r.title,source='HISTORICAL_INCIDENT',
        motive=r.title,invariants=(r.invariant,),runner_key=r.key,stage=r.stage,
        context={'execution_environment':'ISOLATED_QUALIFICATION','owner':'QUALITY_CONTROL'},
        cohorts=(Cohort.REGRESSION,),provenance=(r.selector,r.provenance)))
    return service.register_campaign('quality-control-regression-v1','Quality control permanent regression',[v['id']])
