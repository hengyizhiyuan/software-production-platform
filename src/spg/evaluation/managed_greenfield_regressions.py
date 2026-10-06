"""Frozen regression recipes for the observed first-production context gap."""
from spg.evaluation.catalog import Recipe
from spg.evaluation.contracts import CaseDefinition,Cohort,Stage

CASES=(
 ('REG-ECF-GF-001','首次 greenfield 无伪造不变量或批准决定','tests/integration/test_managed_greenfield_context.py::test_persisted_greenfield_owner_context_binds_task_and_freshness[minimal]'),
 ('REG-ECF-GF-002','真实 Product Invariant 精确传播','tests/integration/test_managed_greenfield_context.py::test_persisted_greenfield_owner_context_binds_task_and_freshness[explicit-invariant]'),
 ('REG-ECF-GF-003','真实 Human Approved Decision 精确传播','tests/integration/test_managed_greenfield_context.py::test_persisted_greenfield_owner_context_binds_task_and_freshness[explicit-approved-decision]'),
 ('REG-ECF-GF-004','缺少当前必需决定仍阻止生产','tests/test_managed_greenfield_context.py::test_reg_ecf_gf_004_required_decision_missing_fail_closed'),
 ('REG-ECF-GF-005','Brownfield 继续使用 repository canonical provenance','tests/test_decision_context_integration.py::test_managed_web_change_requires_project_intent_invariant_and_decision'),
 ('REG-ECF-GF-006','来源改变后旧 Task Contract 不可执行','tests/test_managed_greenfield_context.py::test_reg_ecf_gf_006_freshness_changes_before_executor_effect'))


def recipes():
    return tuple(Recipe(key,title,Stage.ECF,selector,
        'Canonical owner sources and ECF applicability remain exact; no invented invariant/approval; freshness fails closed',
        True,'qualification:ecf-managed-greenfield-context-closure-v1') for key,title,selector in CASES)


def definitions():
    return tuple(CaseDefinition(key='watt.'+r.key,title=r.title,motive=r.title,runner_key=r.key,
        stage=r.stage,source='HISTORICAL_INCIDENT',invariants=(r.invariant,),cohorts=(Cohort.REGRESSION,),
        provenance=(r.provenance,r.selector),aliases=(r.key,),context={'execution_environment':'ISOLATED_QUALIFICATION',
        'earliest_divergence':'Managed Web consumer projected README only and selected universally mandatory brownfield classes',
        'owners':['WATT_ECF_CONTEXT_CONSUMER','IRK','WORK','GOVERNANCE','ECF']}) for r in recipes())
