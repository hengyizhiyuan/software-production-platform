from types import SimpleNamespace
import pytest
from uuid import UUID
from sqlalchemy import select
from tests.conftest import _legacy_test_auth_mode
from tests.integration.conftest import postgres_database
from tests.integration.test_intent_realization_ledger import runtime, acquired, settled
from spg.application.production_admission import ProductionAdmissionTrigger
from spg.application.intent_owner_adapters import IntentOwnerAdapters
from spg.application.work import WorkApplicationService
from spg.infrastructure.persistence.product_schema import repository_intakes
from spg.domain.intent_realization import ProductionIntent, SemanticArgument, SemanticItem, SemanticKind


def test_provisional_ui_focus_does_not_bind_or_activate_work_or_corrupt_shared_acquisition(runtime):
    service,assets,compiler,original=acquired(runtime)
    prior=assets.interaction_observation(original.id)
    interaction=service.create_interaction(human_identity='human:owner',start_work_context=True)
    work=WorkApplicationService(service.database)
    activated=[]
    trigger=ProductionAdmissionTrigger(service,work,assets,SimpleNamespace(activate=activated.append))
    options={'work_handler':trigger.execute_governed_work_turn}if hasattr(trigger,'execute_governed_work_turn')else{}
    service.configure_governed_branch_handler(trigger.execute_governed_turn,**options)
    service.configure_production_admission(trigger.execute,prepare_handler=trigger.prepare,reality_provider=trigger.projection)
    IntentOwnerAdapters(service,work,SimpleNamespace(),SimpleNamespace(),SimpleNamespace()).install()
    class MixedCompiler:
        def interpret(self,basis):
            candidate=compiler.interpret(basis)
            if compiler.operation!='ACQUIRE_REPOSITORY':return candidate
            semantic=candidate.semantic_intent
            missing=SemanticItem(item_id='missing-goal',kind=SemanticKind.PRODUCTION_INTENT,statement='The current change lacks its concrete objective.',provenance=semantic.items[0].provenance,confidence=1,production=ProductionIntent(objective='Unspecified change',primary_change='Unspecified change',current=True,bounded_change=True,repository_reference=SemanticArgument(value=prior['source'],provenance=semantic.items[0].provenance[0]),unresolved_arguments=('objective',)))
            clauses=tuple(c.model_copy(update={'semantic_item_ids':(*c.semantic_item_ids,missing.item_id)})for c in semantic.clauses)
            return candidate.model_copy(update={'semantic_intent':semantic.model_copy(update={'items':(*semantic.items,missing),'clauses':clauses})})
    service.capability=MixedCompiler()
    compiler.operation='ACQUIRE_REPOSITORY';compiler.arguments={'repository_source':prior['source']}
    turn,projection=settled(service,interaction,'获取 '+prior['source']+'。我要改个需求，具体需求稍后再说。')
    observed=assets.interaction_observation(interaction.id)
    assert observed['condition']=='READY',observed
    assert observed['work_id'] is None
    assert service.get_shared_understanding(interaction.id).governed_work_id is None
    assert work.get_work(interaction.current_work_id).current_work_reality_revision_id is None
    assert activated==[]
    assert compiler.calls==2
    assert len(assets.attempts_for_interaction(interaction.id))==1
    assert observed['interaction_id']==str(interaction.id)
    assert assets.interaction_observation(original.id)['condition']=='READY'
    assert projection['obligations'][0]['state']=='SATISFIED'
    with service.database.unit_of_work()as uow:
        intake=uow.session.execute(select(repository_intakes).where(repository_intakes.c.id==UUID(observed['intake_request_id']))).mappings().one()
        assert intake['request']['interaction_id']==str(interaction.id)
        assert intake['observation']['resource_id']==observed['resource_id']
    compiler.operation='CREATE_AND_SWITCH_BRANCH';compiler.arguments={'target_branch':'feat_feedback'}
    branch_turn,branch=settled(service,interaction,'创建并切换到 feat_feedback。')
    assert branch['obligations'][0]['state']=='SATISFIED',branch
    assert assets.interaction_observation(interaction.id)['repository_ref']=='refs/heads/feat_feedback'
    assert service.get_shared_understanding(interaction.id).governed_work_id is None
    assert work.get_work(interaction.current_work_id).current_work_reality_revision_id is None
    assert activated==[]


def test_reused_resource_persists_current_acquisition_identity(runtime):
    service,assets,compiler,original=acquired(runtime)
    prior=assets.interaction_observation(original.id)
    interaction=service.create_interaction(human_identity='human:owner')
    compiler.operation='ACQUIRE_REPOSITORY';compiler.arguments={'repository_source':prior['source']}
    settled(service,interaction,'获取 '+prior['source'])
    latest=assets.interaction_observation(interaction.id)
    current=assets.attempts_for_interaction(interaction.id)[-1]
    assert latest['intake_request_id']==current['intake_request_id']
    assert latest['interaction_id']==str(interaction.id)
    with service.database.unit_of_work()as uow:
        identity=uow.session.execute(select(repository_intakes.c.observation).where(repository_intakes.c.id==UUID(current['intake_request_id']))).scalar_one()
        assert identity['resource_id']==latest['resource_id']


def test_work_binding_failure_refreshes_actual_trusted_repository_without_rewriting_history(runtime):
    from spg.domain.assets import RepositoryAcquisitionFailureCategory
    service,assets,compiler,original=acquired(runtime)
    prior=assets.interaction_observation(original.id)
    failed=assets.mark_attempt_failure(UUID(prior['intake_request_id']),category=RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE,human_message='This Work could not bind the exact repository.',technical_evidence={'phase':'WORK_REALITY_BINDING','error_type':'ValidationError'},retryable=True)
    refreshed=assets.observation(UUID(prior['resource_id']))
    assert refreshed['condition']=='READY',refreshed
    assert refreshed['revision']==prior['revision'] and refreshed['tree']==prior['tree']
    assert refreshed['current_trusted_snapshot_id']
    assert assets.attempts_for_interaction(original.id)[-1]['condition']=='FAILED_RETRYABLE'
    actual=service.create_interaction(human_identity='human:owner')
    compiler.operation='ACQUIRE_REPOSITORY';compiler.arguments={'repository_source':prior['source']}
    settled(service,actual,'获取 '+prior['source'])
    assert assets.interaction_observation(actual.id)['condition']=='READY'
    assert assets.attempts_for_interaction(original.id)[-1]['condition']=='FAILED_RETRYABLE'


@pytest.mark.parametrize('unavailable_authority',[True,False])
def test_binding_refresh_does_not_promote_missing_authority_or_untrusted_git(runtime,unavailable_authority):
    from spg.domain.assets import RepositoryAcquisitionFailureCategory
    service,assets,compiler,original=acquired(runtime)
    prior=assets.interaction_observation(original.id)
    if unavailable_authority:
        category=RepositoryAcquisitionFailureCategory.AUTH_REQUIRED;phase='REPOSITORY_ACQUISITION'
    else:
        from pathlib import Path
        import subprocess
        from spg.infrastructure.persistence.product_store import ProductStore
        with service.database.unit_of_work()as uow:resource=ProductStore(uow.session).resource(UUID(prior['resource_id']))
        path=Path(resource.location_ref);(path/'drift.txt').write_text('untrusted drift')
        for args in [('add','drift.txt'),('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','untrusted drift')]:subprocess.run(['git','-C',str(path),*args],check=True,capture_output=True)
        category=RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE;phase='WORK_REALITY_BINDING'
    assets.mark_attempt_failure(UUID(prior['intake_request_id']),category=category,human_message='Retained failure.',technical_evidence={'phase':phase},retryable=True)
    assert assets.observation(UUID(prior['resource_id']))['condition']!='READY'
