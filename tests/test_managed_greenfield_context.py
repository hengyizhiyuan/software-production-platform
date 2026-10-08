"""Permanent REG-ECF-GF-001..006 over admitted owner facts and canonical ECF."""
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4
from pathlib import Path
import pytest
from spg.application.managed_greenfield_context import project_greenfield_context
from spg.application.decision_context import WattDecisionContextGateway,DecisionContextRequirement,MANAGED_WEB_SURFACE,DecisionContextNotReady,DecisionContextChanged,DecisionContextAuthorityMissing
from spg.domain.intent_realization import SemanticItem,SemanticKind,SemanticClause
from spg.domain.semantic_provenance import SemanticProvenance,SemanticOrigin
from tests.test_human_interaction_authority import declared_ir,ROUTINE,POSITIVE
from tests.test_decision_context_integration import git


def owner_basis(extra=None,pending=False):
    ir,_=declared_ir(ROUTINE[0][1]);work=SimpleNamespace(id=uuid4());pid=uuid4();rev=SimpleNamespace(id=uuid4(),work_id=work.id,revision_fingerprint='a'*64,desired_outcome='制作工律官网',constraints=(),governance_record_id=uuid4())
    gov={'id':rev.governance_record_id,'decision_type':'ADMIT_LONG_LIVED_WORK',
         'subject_type':'PRODUCT_WORK','subject_identity':str(work.id),
         'authority_identity':'human:qualification','scope':{'work_reality_revision_id':str(rev.id)}}
    if extra:
        subject,kind,text=extra;p=SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,source_record_id=ir.source_record_id,source_text=text)
        item=SemanticItem(item_id='explicit',kind=kind,subject=subject,statement=text,provenance=(p,),confidence=1)
        clause=SemanticClause(clause_id='explicit',source_record_id=ir.source_record_id,source_text=text,semantic_item_ids=('explicit',),polarity='AFFIRMATIVE',modality='ASSERTION',temporal_scope='CURRENT')
        ir=ir.model_copy(update={'items':(*ir.items,item),'clauses':(*ir.clauses,clause),'basis_fingerprint':'b'*64})
        if kind is SemanticKind.CONSTRAINT:rev.constraints=(text,)
    if pending:
        positive,_=declared_ir(POSITIVE[0][1],positive=POSITIVE[0][2:]);ir=ir.model_copy(update={'human_decisions':positive.human_decisions})
    return dict(product_id=pid,work=work,revision=rev,ir=ir,governance=gov)


def package(tmp_path,basis):
    repo=tmp_path/'repo';repo.mkdir();git(repo,'init','-b','main');git(repo,'config','user.name','Qualification');git(repo,'config','user.email','ecf@example.invalid');(repo/'README.md').write_text('# Empty managed genesis\n');git(repo,'add','.');git(repo,'commit','-m','genesis')
    req=DecisionContextRequirement(MANAGED_WEB_SURFACE,basis['product_id'],basis['work'].id,'index.html',repo,git(repo,'rev-parse','HEAD'),'watt://qualified')
    source=project_greenfield_context(**basis);gateway=WattDecisionContextGateway()
    return gateway,req,source


def test_reg_ecf_gf_001_minimal_context_no_fabricated_invariant_or_decision(tmp_path):
    basis=owner_basis();g,r,s=package(tmp_path,basis);p=g.require_ready(r,managed_context=s,work_statement='制作工律官网',work_revision=str(basis['revision'].id));lineage=g.lineage(p,r)
    assert p.context_status.value=='READY'
    assert {o.context_class for o in lineage.protected_obligations}=={'PRODUCT_INTENT'}
    intent=lineage.protected_obligations[0];assert intent.source_revision==s.source_revision
    assert str(basis['ir'].id) in lineage.generated_from[0].provenance or any(str(basis['ir'].id) in t.provenance for t in lineage.generated_from)
    assert g.applicability(p)['APPROVED_DECISION']=='NOT_YET_ESTABLISHED_BUT_NON_BLOCKING'
    assert (r.repository_path/'README.md').read_text()=='# Empty managed genesis\n'


@pytest.mark.parametrize('subject,kind,cls,text',[
    ('product_invariant',SemanticKind.CONSTRAINT,'PRODUCT_INVARIANT','产品不变量：所有对外页面必须使用中文。'),
    ('approved_product_decision',SemanticKind.FACT,'APPROVED_DECISION','我决定第一版只做品牌展示，不加入登录和客户后台。')])
def test_reg_ecf_gf_002_003_exact_invariant_and_decision(tmp_path,subject,kind,cls,text):
    b=owner_basis((subject,kind,text));g,r,s=package(tmp_path,b);p=g.require_ready(r,managed_context=s,work_statement='生产官网',work_revision='r1');lineage=g.lineage(p,r)
    o=next(o for o in lineage.protected_obligations if o.context_class==cls);assert o.content==text and o.source_revision==s.source_revision
    assert cls in s.required_classes and g.applicability(p)[cls]=='REQUIRED_AND_PRESENT'
    assert str(b['revision'].governance_record_id) in next(t.provenance for t in lineage.generated_from if t.source_ref==o.source_ref)


def test_reg_ecf_gf_004_required_decision_missing_fail_closed(tmp_path):
    b=owner_basis(pending=True);g,r,s=package(tmp_path,b)
    assert not s.decisions and s.applicability['APPROVED_DECISION']=='REQUIRED_AND_MISSING'
    with pytest.raises(DecisionContextNotReady) as e:g.require_ready(r,managed_context=s,work_statement='生产官网',work_revision='r1')
    assert e.value.missing_classes==('APPROVED_DECISION',)
    from spg.application.human_attention import attention_from_semantic_decisions
    assert len(attention_from_semantic_decisions(b['ir'],product_id=b['product_id'],product_name='官网'))==1


def test_reg_ecf_gf_005_brownfield_repository_owner_preserved(tmp_path):
    b=owner_basis();g,r,s=package(tmp_path,b);p=g.assemble(r,work_statement='更新官网',work_revision='r1')
    assert p.contract.contract_id=='PRODUCT_UI_CHANGE' and p.context_status.value=='INCOMPLETE'
    assert {c.value for c in p.missing_required_classes}=={'PRODUCT_INTENT','PRODUCT_INVARIANT','APPROVED_DECISION'}


def test_reg_ecf_gf_006_freshness_changes_before_executor_effect(tmp_path):
    b=owner_basis(('product_invariant',SemanticKind.CONSTRAINT,'产品不变量：页面必须中文。'));g,r,s=package(tmp_path,b);p=g.require_ready(r,managed_context=s,work_statement='生产官网',work_revision='r1');lineage=g.lineage(p,r)
    g.assert_fresh(lineage,managed_context=s,work_statement='生产官网',work_revision='r1')
    changed=replace(s,invariants=(('explicit','产品不变量：页面必须双语。'),),source_revision='c'*64)
    with pytest.raises(DecisionContextChanged):g.assert_fresh(lineage,managed_context=changed,work_statement='生产官网',work_revision='r2')
    with pytest.raises(DecisionContextAuthorityMissing):g.assemble(r,managed_context=replace(s,product_id=uuid4()))


def test_inferred_or_unadmitted_context_role_cannot_become_protected_truth():
    b=owner_basis(('product_invariant',SemanticKind.CONSTRAINT,'页面必须中文。'))
    b['revision'].constraints=();s=project_greenfield_context(**b);assert not s.invariants and 'PRODUCT_INVARIANT' in s.required_classes
    b['governance']['scope']={}
    with pytest.raises(DecisionContextAuthorityMissing):project_greenfield_context(**b)


def test_admitted_history_retains_invariant_when_followup_turn_has_no_new_production():
    b=owner_basis(('product_invariant',SemanticKind.CONSTRAINT,'产品不变量：页面必须中文。'));older=b['ir']
    current,_=declared_ir(POSITIVE[0][1],positive=POSITIVE[0][2:])
    current=current.model_copy(update={'human_decisions':()})
    b['ir']=current
    s=project_greenfield_context(**b,semantic_history=(older,))
    assert s.intent and s.invariants[0][1]=='产品不变量：页面必须中文。'
    assert str(older.id) in s.provenance and str(current.id) in s.provenance


def test_explicit_supersession_preserves_old_fact_and_changes_current_context():
    old=owner_basis(('product_invariant',SemanticKind.CONSTRAINT,'产品不变量：页面必须中文。'))
    old_source=project_greenfield_context(**old)
    new=owner_basis(('product_invariant',SemanticKind.CONSTRAINT,'产品不变量：页面必须双语。'))
    item=new['ir'].items[-1].model_copy(update={'kind':SemanticKind.CORRECTION,'supersedes':(str(old['ir'].id)+':explicit',)})
    new['ir']=new['ir'].model_copy(update={'items':(*new['ir'].items[:-1],item)})
    source=project_greenfield_context(**new,semantic_history=(old['ir'],))
    assert [v for _,v in source.invariants]==['产品不变量：页面必须双语。']
    assert source.source_revision!=old_source.source_revision
    assert old['revision'].constraints==('产品不变量：页面必须中文。',)


def test_ordinary_work_restriction_does_not_become_product_invariant():
    b=owner_basis();b['revision'].constraints=('不要引入登录和客户后台。',)
    source=project_greenfield_context(**b)
    assert source.constraints==b['revision'].constraints and not source.invariants and not source.decisions
    assert source.required_classes==('APPROVED_CONSTRAINT','PRODUCT_INTENT')


def test_admitted_revision_uses_its_own_governance_basis():
    basis=owner_basis();revision=basis['revision'];previous=revision.id
    revision.id=uuid4();revision.previous_revision_id=previous
    revision.source_assessment_id=uuid4();revision.governance_record_id=uuid4()
    basis['governance']={
        'id':revision.governance_record_id,'decision_type':'ADMIT_WORK_REALITY_REVISION',
        'subject_type':'WORK_REALITY_REVISION_CANDIDATE',
        'subject_identity':f'interaction-assessment:{revision.source_assessment_id}',
        'authority_identity':'human:qualification',
        'scope':{'work_id':str(basis['work'].id),
                 'assessment_id':str(revision.source_assessment_id),
                 'previous_revision_id':str(previous)},
    }
    assert project_greenfield_context(**basis).work_id==basis['work'].id
    basis['governance']['scope']['previous_revision_id']=str(uuid4())
    with pytest.raises(DecisionContextAuthorityMissing):
        project_greenfield_context(**basis)


def test_existing_product_first_bounded_work_can_use_managed_genesis():
    basis=owner_basis();ir=basis['ir']
    items=tuple(item.model_copy(update={'production':item.production.model_copy(update={'new_work':False})})
                if item.production is not None else item for item in ir.items)
    basis['ir']=ir.model_copy(update={'items':items})
    source=project_greenfield_context(**basis)
    assert source is not None and source.intent
    assert source.work_id==basis['work'].id
