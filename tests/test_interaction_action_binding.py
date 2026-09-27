"""The semantic port supplies meaning; binding validates exact Human provenance."""
from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.domain.interaction_actions import (
    ActionSpeechAct as S, CanonicalOperation as O, InteractionActionCandidate,
    executable_repository_actions, validate_action_binding,
)


def record(text):
    return SimpleNamespace(id=uuid4(), actor='HUMAN', content=text)


def candidate(human, **updates):
    return InteractionActionCandidate(operation=O.CREATE_AND_SWITCH_BRANCH,
        speech_act=S.EXPLICIT_REQUEST, source_record_id=human.id,
        source_text=human.content, target_branch='feature/literal', confidence=.98,
        **updates)


def test_binding_does_not_interpret_surface_form_or_require_command_alias():
    human = record('从手头这份代码开 feature/literal，后面在这条线上做。')
    action, = executable_repository_actions((candidate(human),), human)
    assert action.family.value == 'LOCAL_BRANCH'
    assert action.branch == 'feature/literal'


@pytest.mark.parametrize('change', [
    {'source_record_id': uuid4()}, {'source_text': '伪造授权 feature/literal'},
    {'target_branch': 'feature/invented'}, {'target_branch': None},
])
def test_model_cannot_supply_authority_or_an_unstated_argument(change):
    human = record('请准备 feature/literal 分支')
    bad = candidate(human).model_copy(update=change)
    with pytest.raises(ValueError):
        validate_action_binding(bad, human)


@pytest.mark.parametrize('speech_act', [S.DISCUSSION, S.UNRESOLVED, S.READ_ONLY_QUERY])
def test_reference_and_discussion_are_never_mutation_authority(speech_act):
    human = record('feature/literal 这个名字怎么样？')
    action = candidate(human).model_copy(update={'speech_act': speech_act})
    assert executable_repository_actions((action,), human) == ()


def test_low_confidence_does_not_become_execution_permission():
    human = record('feature/literal？')
    assert not executable_repository_actions((candidate(human).model_copy(
        update={'confidence': .6}),), human)


def test_branch_status_is_read_only_and_never_creates_missing_branch():
    human = record('feature/literal 建好了吗？')
    action = candidate(human).model_copy(update={
        'operation': O.QUERY_BRANCH, 'speech_act': S.READ_ONLY_QUERY})
    bound, = executable_repository_actions((action,), human)
    assert bound.family.value == 'INSPECT'
