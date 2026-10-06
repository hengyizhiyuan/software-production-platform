"""Permanent identities for the observed Human-visible owner-boundary incident."""
from spg.evaluation.contracts import CaseDefinition,Cohort,Stage
from spg.evaluation.catalog import Recipe

CASES=(
 ('REG-HI-001','我要开发一个工律的官网','test_persisted_routine_advances_without_schema_attention[REG-HI-001]'),
 ('REG-HI-002','给官网增加一个关于我们页面','test_persisted_routine_advances_without_schema_attention[REG-HI-002]'),
 ('REG-HI-003','在导航栏增加联系我们','test_persisted_routine_advances_without_schema_attention[REG-HI-003]'),
 ('REG-HI-004','做一个简单的公司介绍页','test_persisted_routine_advances_without_schema_attention[REG-HI-004]'),
 ('REG-HI-005','把首页的公司简介改成新的介绍文字','test_persisted_routine_advances_without_schema_attention[REG-HI-005]'),
 ('REG-HI-P01','官网第一版是只做品牌展示，还是同时加入登录和客户后台？请先分析差异，再让我决定。','test_persisted_reserved_choice_has_exact_useful_action[REG-HI-P01]'),
 ('REG-HI-P02','数据应只保存在公司的私有环境，还是允许交给外部云服务？请分析权限与数据边界，再由我决定。','test_persisted_reserved_choice_has_exact_useful_action[REG-HI-P02]'))

def recipes():
    return tuple(Recipe(identity,text,Stage.STEERING,
        'tests/integration/test_human_interaction_authority.py::'+selector,
        'IRK meaning remains exact; only concrete Human-owned material choices block; WIC alone realizes ordinary owner facts',
        True,'qualification:human-interaction-authority-repair-v1') for identity,text,selector in CASES)

def definitions():
    return tuple(CaseDefinition(key=r.key,title=r.title,motive=r.title,runner_key=r.key,
        stage=r.stage,source='HISTORICAL_INCIDENT' if not r.key.startswith('REG-HI-P') else 'POSITIVE_GOVERNANCE',
        invariants=(r.invariant,),cohorts=(Cohort.REGRESSION,),
        provenance=(r.provenance,r.selector),context={'execution_environment':'ISOLATED_QUALIFICATION',
            'earliest_divergence':'IRK optional inferred QUESTION obligation improperly required Human; downstream schema activation compounded it',
            'owners':['IRK_OBLIGATIONS','GUIDED_DESIGN','STEERING','ATTENTION','WIC_REALIZATION']},aliases=(r.key,)) for r in recipes())
