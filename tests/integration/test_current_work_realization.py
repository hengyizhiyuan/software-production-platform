from types import SimpleNamespace
from tests.conftest import _legacy_test_auth_mode
from tests.integration.conftest import postgres_database
from tests.integration.test_wic_governed_work_admission import clean_schema,services,_ready,_admit
from spg.application.production_admission import ProductionAdmissionTrigger
from spg.application.interaction import WorkInteractionService
from spg.domain.interaction import InteractionAssessmentCandidate,WorkFocusClassification,WorkImpactDisposition
from spg.domain.product import AttentionAction
from spg.domain.intent_realization import ProductionIntent,SemanticItem,SemanticKind,SemanticProvenance,SemanticOrigin,SemanticClause,TurnSemanticCandidate
from spg.infrastructure.persistence.interaction_store import InteractionStore


def test_current_work_port_does_not_repeat_an_assessment_already_realized_by_owner(postgres_database,services):
 work,interactions=services;ready=_ready(interactions);admitted=_admit(work,ready,authority_identity='human:test')
 class CurrentGoal:
  def interpret(self,basis):
   r=basis.records[-1];p=SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,source_record_id=r.id,source_text=r.content)
   item=SemanticItem(item_id='current-goal',kind=SemanticKind.PRODUCTION_INTENT,statement=r.content,provenance=(p,),confidence=1,production=ProductionIntent(objective='Make the current interface clearer',primary_change='Improve the current interface labels',current=True,bounded_change=True))
   return InteractionAssessmentCandidate(provider_identity='declared:current-goal',natural_response='Current request',semantic_intent=TurnSemanticCandidate(items=(item,),clauses=(SemanticClause(clause_id='current',source_record_id=r.id,source_text=r.content,semantic_item_ids=(item.item_id,)),)),focus_classification=WorkFocusClassification.ON_TOPIC,impact_disposition=WorkImpactDisposition.CURRENT_RESULT_MAY_BE_INSUFFICIENT)
 active=WorkInteractionService(postgres_database,capability=CurrentGoal())
 active.append_human_input(ready.interaction.id,'Improve the labels in the current interface.',human_identity='human:test')
 assessment=active.assess_current(ready.interaction.id)
 work.decide_interaction_work_revision(ready.interaction.id,assessment_id=assessment.id,basis_fingerprint=assessment.basis_fingerprint,expected_previous_revision_id=assessment.basis_work_revision_id,action=AttentionAction.APPROVE,authority_identity='human:test',rationale='Exact current typed owner fixture decision')
 realized=work.get_work(admitted.work_id).current_work_reality_revision_id
 scheduled=[]
 post=SimpleNamespace(steering_driver=SimpleNamespace(schedule=scheduled.append),steering_bootstrap=SimpleNamespace(bootstrap=scheduled.append))
 trigger=ProductionAdmissionTrigger(active,work,None,post)
 with postgres_database.unit_of_work()as uow:record=InteractionStore(uow.session).records(ready.interaction.id)[-1]
 try:
  assert trigger.execute_governed_work_turn(ready.interaction.id,assessment,record)is None
  assert work.get_work(admitted.work_id).current_work_reality_revision_id==realized
  assert scheduled==[]
 finally:active.shutdown()
