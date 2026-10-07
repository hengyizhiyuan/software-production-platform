"""Durable guidance and continuation use the existing admission owners."""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from spg.application.interaction import WorkInteractionService
from spg.application.product_assets import ProductAssetService
from spg.application.production_admission import ProductionAdmissionTrigger
from spg.application.steering_bootstrap import SteeringBootstrapService
from spg.domain.intent_realization import ProductionSufficiency, SemanticArgument, SemanticOrigin, SemanticProvenance
from spg.domain.interaction import InteractionAssessmentCandidate, InteractionInvariantViolation
from spg.infrastructure.persistence.runtime_schema import production_work_units
from tests.integration.test_wic_governed_work_admission import clean_schema, _services_for_resource, _admit
from tests.test_guided_interaction_calibration import guidance, meaning, PROPOSAL, QUESTION

pytestmark = pytest.mark.postgresql


class Compiler:
    def __init__(self, profile='broad'): self.profile=profile; self.seen=[]
    def interpret(self, basis):
        self.seen.append(basis)
        record = basis.records[-1]
        refs = tuple(ref for o in basis.observed_reality if o.owner == 'product-context' for ref in o.evidence_references)
        scope=()
        if self.profile == 'broad': sufficient=guidance(context_references=refs)
        elif self.profile == 'accept':
            prior=basis.governed_semantic_history[-1]
            scope=(prior.production_sufficiency.proposal,)
            sufficient=ProductionSufficiency(status='READY',reason='当前 Human 选择了上一轮具体且有限的成果方案',
                recommendation_acceptance=SemanticArgument(value=str(prior.id), provenance=SemanticProvenance(
                    origin=SemanticOrigin.HUMAN_EXPLICIT, source_record_id=record.id, source_text=record.content)))
        else: sufficient=ProductionSufficiency(status='READY',reason='当前请求明确指定唯一导航改动、目标及不得扩大范围的约束')
        raw=meaning(record,sufficient,scope=scope,bounded=self.profile=='specific')
        return InteractionAssessmentCandidate(semantic_intent=raw,natural_response='提供当前目标的有限建议。',provider_identity='fixture:qualified-compiler')


def test_guidance_is_durable_and_cannot_create_pwu_before_answer(postgres_database,tmp_path):
    work,_=_services_for_resource(postgres_database,tmp_path,'test://guided-closure')
    compiler=Compiler(); service=WorkInteractionService(postgres_database,capability=compiler)
    origin=service.create_interaction(human_identity='human:test')
    first=service.append_and_assess(origin.id,'我要开发一个工律的官网',human_identity='human:test')
    assert first.readiness.status.value=='NOT_READY' and first.governed_work_id is None
    with pytest.raises(InteractionInvariantViolation, match='not READY'):_admit(work,first)
    effects=[]
    trigger=ProductionAdmissionTrigger(service,work,SimpleNamespace(),SimpleNamespace(activate=effects.append))
    trigger.prepare(origin.id,first.latest_assessment,first.records[-1])
    assert effects==[]
    rebuilt=WorkInteractionService(postgres_database,capability=compiler).get_shared_understanding(origin.id)
    assert rebuilt.latest_assessment.semantic_ir.production_sufficiency.question==QUESTION
    assert rebuilt.latest_assessment.semantic_ir.current_production[0].objective=='开发工律官网'
    with postgres_database.unit_of_work() as u: assert u.session.execute(select(production_work_units.c.id)).all()==[]
    compiler.profile='accept'
    answer=service.append_and_assess(origin.id,'按你的建议来',human_identity='human:test')
    assert answer.readiness.status.value=='READY'
    admitted=_admit(work,answer)
    current=service.get_shared_understanding(origin.id)
    assert current.governed_work_id==admitted.work_id
    assert PROPOSAL in current.latest_assessment.candidate_constraints
    steering=SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)
    assert steering.current_step is not None
    assert len(compiler.seen[-1].governed_semantic_history)==1


def test_known_product_context_informs_guidance_without_authorizing_new_scope(postgres_database,tmp_path):
    _services_for_resource(postgres_database,tmp_path,'test://guided-context')
    product=ProductAssetService(postgres_database).create('human:test','工律',
        '工律服务软件生产中的 Human 治理，当前用户为软件产品团队。',provision_source=False)
    compiler=Compiler();service=WorkInteractionService(postgres_database,capability=compiler)
    from uuid import UUID
    origin=service.create_interaction(human_identity='human:test',product_id=UUID(product['id']))
    projection=service.append_and_assess(origin.id,'我要开发一个工律的官网',human_identity='human:test')
    observation=next(o for o in compiler.seen[0].observed_reality if o.owner=='product-context')
    assert observation.facts['name']=='工律' and '软件产品团队' in observation.facts['description']
    assert observation.facts['authority']=='EXISTING_PRODUCT_CONTEXT_NOT_NEW_SCOPE_APPROVAL'
    assert projection.latest_assessment.semantic_ir.production_sufficiency.context_references==observation.evidence_references
    assert projection.readiness.status.value=='NOT_READY'


def test_specific_request_does_not_reopen_definition(postgres_database,tmp_path):
    work,_=_services_for_resource(postgres_database,tmp_path,'test://guided-specific')
    service=WorkInteractionService(postgres_database,capability=Compiler('specific'))
    origin=service.create_interaction(human_identity='human:test')
    projection=service.append_and_assess(origin.id,'给现有官网导航栏增加“联系我们”，链接到已有 contact 页面，其他内容不要改。',human_identity='human:test')
    assert projection.readiness.status.value=='READY'
    assert projection.latest_assessment.progressive_semantics.selected_question is None
    assert _admit(work,projection).work_id
