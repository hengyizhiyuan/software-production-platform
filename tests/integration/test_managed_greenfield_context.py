"""Persisted owner seam; Product/Gitea attachment is an explicit isolated fixture.
IRK and Work admission are canonical services, not JSON context substitutes.
"""
from uuid import uuid4
from pathlib import Path
from sqlalchemy import insert,update,select
import pytest
from types import SimpleNamespace
from tests.integration.test_wic_governed_work_admission import clean_schema,_services_for_resource,_admit
from tests.integration.test_human_interaction_authority import DeclaredCompiler
from spg.application.interaction import WorkInteractionService
from spg.domain.intent_realization import SemanticItem,SemanticKind,SemanticClause
from spg.domain.semantic_provenance import SemanticProvenance,SemanticOrigin
from spg.infrastructure.persistence.product_schema import software_products,product_works,product_managed_sources,work_source_bases,engineering_resources
from spg.infrastructure.persistence.product_store import ProductStore
from spg.application.decision_context import lineage_for_work_task,assert_task_context_fresh,DecisionContextChanged,WattDecisionContextGateway,MilestoneClosureContextService
from spg.application.production_intelligence import default_task_contract_builder,TaskContractRequest
from tests.test_decision_context_integration import git

pytestmark=pytest.mark.postgresql


class Compiler(DeclaredCompiler):
    def __init__(self,role=None,text=None):super().__init__();self.role=role;self.text=text
    def interpret(self,basis):
        c=super().interpret(basis)
        if self.role is None:return c
        r=basis.records[-1];p=SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,source_record_id=r.id,source_text=self.text)
        item=SemanticItem(item_id='explicit',kind=SemanticKind.CONSTRAINT if self.role=='product_invariant' else SemanticKind.FACT,subject=self.role,statement=self.text,provenance=(p,),confidence=1)
        clause=SemanticClause(clause_id='explicit',source_record_id=r.id,source_text=self.text,semantic_item_ids=('explicit',),polarity='AFFIRMATIVE',modality='ASSERTION',temporal_scope='CURRENT')
        raw=c.semantic_intent.model_copy(update={'items':(*c.semantic_intent.items,item),'clauses':(*c.semantic_intent.clauses,clause)})
        return c.model_copy(update={'semantic_intent':raw})


@pytest.mark.parametrize('role,text,expected',[
    (None,None,{'PRODUCT_INTENT','APPROVED_CONSTRAINT'}),
    ('product_invariant','产品不变量：官网所有页面必须使用中文。',{'PRODUCT_INTENT','PRODUCT_INVARIANT'}),
    ('approved_product_decision','我决定第一版只做品牌展示，不加入登录和客户后台。',{'PRODUCT_INTENT','APPROVED_DECISION'})],ids=['minimal','explicit-invariant','explicit-approved-decision'])
def test_persisted_greenfield_owner_context_binds_task_and_freshness(postgres_database,tmp_path,role,text,expected):
    identity='watt://qualification/'+str(uuid4());work,_=_services_for_resource(postgres_database,tmp_path,identity)
    interaction=WorkInteractionService(postgres_database,capability=Compiler(role,text));origin=interaction.create_interaction(human_identity='human:test')
    content='我要开发一个工律的官网'+('；'+text if text else '')
    ready=interaction.append_and_assess(origin.id,content,human_identity='human:test')
    if ready.readiness.status.value=='NOT_READY' and ready.latest_assessment.semantic_ir.production_sufficiency:
        ready=interaction.append_and_assess(origin.id,'按你的建议来',human_identity='human:test')
    admitted=_admit(work,ready)
    pid=uuid4()
    with postgres_database.unit_of_work() as u:
        store=ProductStore(u.session);resource=store.resource_for_work(admitted.work_id);record=store.work(admitted.work_id);revision=store.current_work_reality_revision(admitted.work_id)
        repo=Path(resource.location_ref);git(repo,'remote','add','origin','http://gitea.invalid/qualification.git');sha=git(repo,'rev-parse','HEAD');tree=git(repo,'rev-parse','HEAD^{tree}')
        u.session.execute(insert(software_products).values(id=pid,owner_id='human:test',name='Greenfield seam',lifecycle='ACTIVE',description='explicit isolated source attachment'))
        u.session.execute(update(product_works).where(product_works.c.id==record.id).values(product_id=pid))
        # Managed Product source and the per-Work branch are distinct identities.
        u.session.execute(insert(product_managed_sources).values(product_id=pid,repository_identity=identity+'-product',provider_kind='gitea',provider_reference='qualification',accepted_ref='refs/heads/main',accepted_revision=sha,accepted_tree=tree,origin={},version=0))
        u.session.execute(insert(work_source_bases).values(work_id=record.id,product_id=pid,resource_id=resource.id,source_version=0,source_revision=sha,source_tree=tree,work_ref='refs/heads/main'))
        u.commit()
    lineage=lineage_for_work_task(postgres_database,work_id=record.id,repository_identity=identity,repository_path=repo,repository_revision=sha,target_paths=('index.html',))
    assert lineage.contract_id=='MANAGED_GREENFIELD_PRODUCTION'
    # The Product source and Work branch have separate identities at milestone
    # evaluation too; only their exact admitted source version/tree may join.
    closure=MilestoneClosureContextService(postgres_database).assess_work_milestone(record.id)
    assert closure.context_status in {'READY','INCOMPLETE'}
    assert {o.context_class for o in lineage.protected_obligations}==expected
    if role is None:
        from tests.test_guided_interaction_calibration import PROPOSAL
        assert next(o for o in lineage.protected_obligations if o.context_class=='APPROVED_CONSTRAINT').content==PROPOSAL
    assert any(str(revision.id) in t.provenance for t in lineage.generated_from)
    if text:assert next(o for o in lineage.protected_obligations if o.context_class!='PRODUCT_INTENT').content==text
    task=default_task_contract_builder().build(TaskContractRequest(objective=content,scope=('CREATE:index.html',),acceptance_meaning=('Verify homepage',),out_of_scope=('Unrelated files',),authority_lineage=(f'work:{record.id}',),work_reality_references=(f'work:{record.id}',),ecf_references=(f'repository:{identity}',),decision_reference=f'work:{record.id}',governed_surface=lineage.surface,decision_context=lineage))
    assert_task_context_fresh(postgres_database,task)
    # A mutable source projection cannot evade the current Work freshness check.
    with postgres_database.unit_of_work() as u:
        u.session.execute(update(product_works).where(product_works.c.id==record.id).values(desired_outcome='Later source-owned Work changed'));u.commit()
    with pytest.raises(DecisionContextChanged):assert_task_context_fresh(postgres_database,task)
    assert (repo/'AI_context.md').read_text()=='governed context\n' and not (repo/'README.md').exists()
