"""Real PostgreSQL + real Git; preparatory actions never fabricate admitted Work."""
from pathlib import Path
import re
from types import SimpleNamespace
from tests.irk_test_fixtures import governed_ir, semantic_candidate, question
from tests.integration.test_intent_realization_ledger import DeclaredCompiler
import subprocess
import time
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import select, func

from spg.application.assets import RepositoryAssetService
from spg.application.interaction import WorkInteractionService, DeterministicWorkInteractionCapability
from spg.domain.assets import RepositoryAcquisitionFailure, RepositoryAcquisitionFailureCategory as F, RepositoryIntakeRequest
from spg.domain.interaction import InteractionActor
from spg.domain.wic_response import WicRuntimeMode
from spg.infrastructure.persistence.interaction_store import InteractionStore
from spg.infrastructure.persistence.product_schema import work_reality_revisions
from spg.infrastructure.production_environment import GitRepositoryAcquirer

@pytest.fixture
def owner(postgres_database, tmp_path, monkeypatch):
    monkeypatch.setenv('SPG_DATABASE_URL', postgres_database.engine.url.render_as_string(hide_password=False))
    command.upgrade(Config('alembic.ini'), 'head')
    assets = RepositoryAssetService(postgres_database, tmp_path/'assets', tmp_path)
    interaction = WorkInteractionService(postgres_database, capability=DeclaredCompiler(), runtime_mode=WicRuntimeMode.WIC_VNEXT_CONTROLLED)
    interaction.configure_repository_actions(assets.execute_interaction_actions, assets.interaction_observation)
    source = tmp_path/'source'
    source.mkdir()
    def git(*args):
        return subprocess.run(['git','-C',str(source),*args],check=True,capture_output=True,text=True).stdout.strip()
    git('init','-b','main')
    (source/'README.md').write_text('# Example\nReal fixture repository\n')
    (source/'package.json').write_text('{"dependencies":{"react":"19.0.0"},"scripts":{"test":"node --test"}}')
    git('add','.')
    git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture')
    yield interaction, assets, source, git('rev-parse','HEAD'), git('rev-parse','HEAD^{tree}')
    interaction.shutdown()


def turn(service, identity, text, *, operation=None, branch=None, ambiguous=False):
    if isinstance(service.capability, DeclaredCompiler):
        service.capability.operation = operation
        service.capability.arguments = {"target_branch": branch} if branch else {"repository_source": re.search(r"https://[^，\s]+", text).group(0)} if operation == "ACQUIRE_REPOSITORY" and not ambiguous else {}
        service.capability.conditional = ambiguous
    receipt = service.submit_turn(identity, text, human_identity='human:owner')
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        current=service.get_turn(receipt.id)
        if current.status.value in {'COMPLETED','FAILED'}:
            assert current.status.value=='COMPLETED', current.failure_message
            return service.get_shared_understanding(identity)
        time.sleep(.05)
    pytest.fail('Turn did not settle')


@pytest.mark.parametrize('pre_work',[False,True])
def test_acquisition_branch_and_query_without_work(owner, monkeypatch, pre_work):
    service, assets, source, revision, tree=owner
    # Substitute the public remote boundary only: all Git acquisition/branch
    # operations and exact source observation remain real.
    real=assets.repository_acquirer
    class LocalRemote(GitRepositoryAcquirer):
        def acquire(self, root, remote, destination, **kwargs):
            return real.acquire(root,str(source),destination)
    assets.repository_acquirer=LocalRemote()
    interaction=service.create_interaction(human_identity='human:owner',start_work_context=pre_work)
    projection=turn(service,interaction.id,f'我有个GitHub仓库：https://github.com/acme/{uuid4().hex}.git，把它clone下来，我要改个需求', operation='ACQUIRE_REPOSITORY')
    assert projection.governed_work_id is None
    observation=projection.repository_observation
    assert (observation['condition'],observation['revision'],observation['tree'])==('READY',revision,tree)
    assert observation['repository_ref']=='refs/heads/main'
    projection=turn(service,interaction.id,'切一个 feat_test 分支', operation='CREATE_AND_SWITCH_BRANCH', branch='feat_test')
    assert projection.repository_observation['repository_ref']=='refs/heads/feat_test'
    assert projection.repository_observation['revision']==revision
    assert projection.repository_observation['tree']==tree
    projection=turn(service,interaction.id,'我现在在哪个分支？', operation='QUERY_CURRENT_BRANCH')
    assert 'feat_test' in projection.conversation_messages[-1].content
    assert projection.governed_work_id is None
    assert len(assets.attempts_for_interaction(interaction.id))==2

@pytest.mark.parametrize('text',[
    '这个仓库 https://github.com/acme/project.git 以后可能会用到。',
    '不要 clone https://github.com/acme/project.git',
    '帮我看看有没有类似的 GitHub 项目',
])
def test_implied_or_negated_intent_has_no_intake(owner,text):
    service,assets,*_=owner
    interaction=service.create_interaction(human_identity='human:owner')
    projection=turn(service,interaction.id,text)
    assert not assets.attempts_for_interaction(interaction.id)
    assert projection.governed_work_id is None

@pytest.mark.parametrize('failure,attempts',[(F.NETWORK_FAILURE,2),(F.AUTH_REQUIRED,1),(F.REPOSITORY_NOT_FOUND,1)])
def test_retryable_failure_has_bounded_lineage_and_terminal_does_not_retry(owner,failure,attempts):
    service,assets,source,*_=owner
    real=assets.repository_acquirer
    class Unstable(GitRepositoryAcquirer):
        calls=0
        def acquire(self,root,remote,destination,**kwargs):
            self.calls+=1
            if self.calls==1:
                raise RepositoryAcquisitionFailure(failure,'Observed boundary failure',technical_evidence={'signal':failure.value},retryable=failure is F.NETWORK_FAILURE)
            return real.acquire(root,str(source),destination)
    adapter=Unstable()
    assets.repository_acquirer=adapter
    interaction=service.create_interaction(human_identity='human:owner')
    projection=turn(service,interaction.id,f'clone https://github.com/acme/{uuid4().hex}.git', operation='ACQUIRE_REPOSITORY')
    assert adapter.calls==attempts
    assert len(assets.attempts_for_interaction(interaction.id))==attempts
    assert projection.governed_work_id is None
    if attempts==2:
        assert projection.repository_observation['condition']=='READY'
        with service.database.unit_of_work() as uow:
            events=InteractionStore(uow.session).response_events(projection.turns[-1].id)
        assert any(e.metadata.get('recovery_scope')=='INTERACTION_ACTION_ONLY' and not e.metadata['work_converged'] for e in events)


def test_valid_credential_and_capability_do_not_replace_current_resource_authority(owner):
    service, assets, *_ = owner
    assets.github_delivery.settings = assets.github_delivery.settings.model_copy(update={
        'auth_mode': 'required', 'github_read_token': 'available-test-provider-token',
    })
    interaction = service.create_interaction(human_identity='human:owner')
    from sqlalchemy import delete
    from spg.infrastructure.persistence.auth_schema import authority_resource_access
    with service.database.unit_of_work() as uow:
        uow.session.execute(delete(authority_resource_access).where(
            authority_resource_access.c.resource_kind == 'interaction',
            authority_resource_access.c.resource_id == str(interaction.id),
        ))
        uow.commit()
    projection = turn(service, interaction.id, f'clone https://github.com/acme/{uuid4().hex}.git', operation='ACQUIRE_REPOSITORY')
    assert not assets.attempts_for_interaction(interaction.id)
    assert projection.governed_work_id is None
    assert '尚未完成' in projection.conversation_messages[-1].content
    assert service.realization_projection(projection.turns[-1].id)['obligations'][0]['state'] == 'BLOCKED_WITH_EVIDENCE'


def test_exhausted_network_retries_preserve_non_convergence_and_do_not_restart_blindly(owner):
    service, assets, *_ = owner
    class Unavailable(GitRepositoryAcquirer):
        calls = 0
        def acquire(self, *args, **kwargs):
            self.calls += 1
            raise RepositoryAcquisitionFailure(F.NETWORK_FAILURE, 'Network unavailable',
                technical_evidence={'boundary': 'remote'}, retryable=True)
    adapter = Unavailable()
    assets.repository_acquirer = adapter
    interaction = service.create_interaction(human_identity='human:owner')
    projection = turn(service, interaction.id, f'clone https://github.com/acme/{uuid4().hex}.git', operation='ACQUIRE_REPOSITORY')
    assert adapter.calls == 3
    assert projection.repository_observation['condition'] == 'FAILED_RETRYABLE'
    assert projection.governed_work_id is None
    assets.restore_interaction_actions()
    assert adapter.calls == 3
    with service.database.unit_of_work() as uow:
        events = InteractionStore(uow.session).response_events(projection.turns[-1].id)
    repairs = [e for e in events if e.metadata.get('recovery_scope') == 'INTERACTION_ACTION_ONLY']
    assert len(repairs) == 1
    assert repairs[0].metadata['attempt_count'] == 3
    assert not repairs[0].metadata['work_converged']


def test_ambiguous_target_asks_once_without_acquisition(owner):
    service, assets, *_ = owner
    interaction = service.create_interaction(human_identity='human:owner')
    projection = turn(service, interaction.id,
        'clone https://github.com/acme/one.git https://github.com/acme/two.git', operation='ACQUIRE_REPOSITORY', ambiguous=True)
    assert not assets.attempts_for_interaction(interaction.id)
    assert service.realization_projection(projection.turns[-1].id)['obligations'][0]['state'] == 'REQUIRES_HUMAN'
    assert projection.governed_work_id is None


@pytest.mark.parametrize('preview_status,expected',[
    ('PREPARING','PREVIEW_PREPARING'),('BUILDING','PREVIEW_PREPARING'),
    ('READY','WAITING_FOR_HUMAN'),('FAILED','PREVIEW_UNHEALTHY'),
])
def test_preview_preparation_is_owned_before_human_attention(owner, preview_status, expected):
    from types import SimpleNamespace
    from sqlalchemy import insert
    from spg.application.control_room import ControlRoomService
    from spg.infrastructure.persistence.product_schema import product_works
    service, *_ = owner
    work_id = uuid4()
    with service.database.unit_of_work() as uow:
        uow.session.execute(insert(product_works).values(id=work_id,
            work_mode='IMMEDIATE_PRODUCTION', raw_user_requirement='Preview obligation',
            constraints=[], tags=[], condition='READY'))
        uow.commit()
    work = SimpleNamespace(status=SimpleNamespace(value='RUNNING'),
        human_attention_required=True, what_happens_next='Preview owner continues')
    preview_id = uuid4()
    preview = SimpleNamespace(id=preview_id, status=SimpleNamespace(value=preview_status),
        repository_revision='a'*40, repository_tree='b'*40, mode='FUNCTIONAL')
    previews = SimpleNamespace(store=SimpleNamespace(current_candidate_preview=lambda _:preview),
        provider=SimpleNamespace(probe=lambda *args, **kwargs:True))
    room = ControlRoomService(service.database, SimpleNamespace(get_work=lambda _:work))
    room.candidate_preview_service = previews
    diagnosis = room.diagnosis(work_id)
    assert diagnosis['state'] == expected
    assert diagnosis['preview'] == [{'preview_id':str(preview_id),'status':preview_status}]


def test_provider_semantic_action_survives_nonmatching_surface_and_persists_authority(owner):
    from spg.domain.interaction_actions import InteractionActionCandidate
    service, assets, source, revision, tree = owner
    real = assets.repository_acquirer
    class LocalRemote(GitRepositoryAcquirer):
        def acquire(self, root, remote, destination, **kwargs):
            return real.acquire(root, str(source), destination)
    assets.repository_acquirer = LocalRemote()
    interaction = service.create_interaction(human_identity='human:owner')
    turn(service, interaction.id, f'clone https://github.com/acme/{uuid4().hex}.git', operation='ACQUIRE_REPOSITORY')
    original = service.capability
    class SemanticPort:
        provider_identity = 'deepseek-responses:test'
        def interpret(self, basis):
            human = basis.records[-1]
            value = original.interpret(basis)
            return value.model_copy(update={
                'provider_identity': self.provider_identity,
                'semantic_intent': semantic_candidate(human, operation='CREATE_AND_SWITCH_BRANCH', arguments={'target_branch': 'feat_semantic_binding'}),
                'action_candidates': (InteractionActionCandidate(
                    operation='CREATE_AND_SWITCH_BRANCH', speech_act='EXPLICIT_REQUEST',
                    source_record_id=human.id, source_text=human.content,
                    target_branch='feat_semantic_binding', confidence=.99),)})
    service.capability = SemanticPort()
    result = turn(service, interaction.id, '从当前代码切个 feat_semantic_binding 出来')
    assert result.repository_observation['repository_ref'] == 'refs/heads/feat_semantic_binding'
    assert (result.repository_observation['revision'], result.repository_observation['tree']) == (revision, tree)
    assert 'feat_semantic_binding' in result.conversation_messages[-1].content
    assert result.latest_assessment.action_candidates[0].target_branch == 'feat_semantic_binding'
    # Execute authorization is rechecked from persisted semantics, not caller flags.
    request = assets.attempts_for_interaction(interaction.id)[-1]['request']
    from spg.domain.assets import RepositoryIntakeRequest
    assets._require_interaction_authority(RepositoryIntakeRequest.model_validate(request))
    assert result.governed_work_id is None


def test_provider_discussion_cannot_fall_back_to_legacy_phrase_mutation(owner):
    from spg.domain.interaction_actions import InteractionActionCandidate
    service, assets, *_ = owner
    original = service.capability
    class DiscussionPort:
        provider_identity = 'deepseek-responses:test'
        def interpret(self, basis):
            human = basis.records[-1]
            return original.interpret(basis).model_copy(update={
                'provider_identity': self.provider_identity,
                'semantic_intent': semantic_candidate(human),
                'action_candidates': (InteractionActionCandidate(
                    operation='CREATE_AND_SWITCH_BRANCH', speech_act='DISCUSSION',
                    source_record_id=human.id, source_text=human.content,
                    target_branch='feat_discussion', confidence=.99),)})
    service.capability = DiscussionPort()
    interaction = service.create_interaction(human_identity='human:owner')
    turn(service, interaction.id, '切一个 feat_discussion 分支')
    assert not assets.attempts_for_interaction(interaction.id)
