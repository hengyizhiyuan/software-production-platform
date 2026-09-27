from dataclasses import replace

import pytest

from spg.domain.action_admission import ActionFacts, ActionFamily as A, ActionEligibility as E, admit_action
from spg.domain.connectors import SideEffectLevel
from spg.domain.repository_actions import repository_actions

BASE = ActionFacts(explicit=True, authority=True, capability=True)

@pytest.mark.parametrize('action,facts,expected,execute', [
    (A.ACQUIRE_REPOSITORY, BASE, E.ALLOWED_IF_EXPLICIT, True),
    (A.INSPECT, BASE, E.ALLOWED_IF_EXPLICIT, True),
    (A.LOCAL_BRANCH, replace(BASE, repository_ready=True), E.ALLOWED_IF_EXPLICIT, True),
    (A.LOCAL_BRANCH, BASE, E.SELF_REFINE_FIRST, False),
    (A.PRODUCE, BASE, E.REQUIRES_WORK_ADMISSION, False),
    (A.PRODUCE, replace(BASE, work_admitted=True), E.REQUIRES_WORK_ADMISSION, False),
    (A.PRODUCE, replace(BASE, work_admitted=True, production_intent_sufficient=True), E.ALLOWED_IF_EXPLICIT, True),
    (A.PRODUCE, replace(BASE, work_admitted=True, production_intent_sufficient=True, candidate_sealed=True), E.SELF_REFINE_FIRST, False),
    (A.PREVIEW, replace(BASE, explicit=False, candidate=True, system_obligation=True), E.AUTO_ALLOWED, True),
    (A.PREVIEW, BASE, E.REQUIRES_CANDIDATE, False),
    (A.HUMAN_ACCEPTANCE, replace(BASE, candidate=True, preview_required=True), E.SELF_REFINE_FIRST, False),
    (A.DELIVERY, replace(BASE, candidate=True, work_admitted=True), E.REQUIRES_ACCEPTANCE, False),
    (A.DELIVERY, replace(BASE, candidate=True, human_accepted=True), E.REQUIRES_DELIVERY_AUTHORIZATION, False),
    (A.DELIVERY, replace(BASE, candidate=True, human_accepted=True, delivery_authorized=True), E.ALLOWED_IF_AUTHORIZED, True),
    (A.NEW_WORK, BASE, E.ALLOWED_IF_EXPLICIT, True),
    (A.INSPECT, replace(BASE, authority=False, credential=True), E.BLOCKED, False),
    (A.DELIVERY, replace(BASE, authority=False, capability=True), E.BLOCKED, False),
    (A.ACQUIRE_REPOSITORY, replace(BASE, credential=False), E.REQUIRES_HUMAN, False),
    (A.ACQUIRE_REPOSITORY, replace(BASE, explicit=False), E.ALLOWED_IF_EXPLICIT, False),
    (A.ACQUIRE_REPOSITORY, replace(BASE, retryable=True, attempts=2), E.ALLOWED_IF_EXPLICIT, True),
    (A.ACQUIRE_REPOSITORY, replace(BASE, retryable=True, attempts=3), E.BLOCKED, False),
    (A.ACQUIRE_REPOSITORY, replace(BASE, terminal=True), E.BLOCKED, False),
    (A.ACQUIRE_REPOSITORY, replace(BASE, already_completed=True), E.AUTO_ALLOWED, False),
    (A.INSPECT, replace(BASE, side_effect=SideEffectLevel.EXTERNAL_WRITE), E.BLOCKED, False),
])
def test_independent_action_obligations(action, facts, expected, execute):
    decision = admit_action(action, facts)
    assert (decision.eligibility, decision.execute) == (expected, execute)

@pytest.mark.parametrize('text,families', [
    ('我有个GitHub仓库：https://github.com/acme/project.git，把它clone下来，我要改个需求', [A.ACQUIRE_REPOSITORY]),
    ('clone 这个仓库，然后切 feat_test。', [A.ACQUIRE_REPOSITORY, A.LOCAL_BRANCH]),
    ('切一个 feat_test 分支', [A.LOCAL_BRANCH]),
    ('先帮我看看这个仓库使用什么框架，我再决定改什么。', [A.INSPECT]),
    ('我现在在哪个分支？', [A.INSPECT]),
    ('这个 repo 以后可能会改。', []),
    ('帮我看看有没有类似的 GitHub 项目', []),
    ('不要 clone https://github.com/acme/project.git', []),
    ('如何 clone 这个 repo？', []),
    ('以后可能切一个 feat_test 分支', []),
    ('切一个 feat_test 分支了吗？', []),
    ('create a file named hello', []),
    ('please explain git clone', []),
    ('他建议切 feat_test 分支', []),
    ('先看看这个项目是什么技术栈，我之后再决定改什么。', [A.INSPECT]),
    ('create branch feature/example', [A.LOCAL_BRANCH]),
    ('切一个本地 feat_test 分支', [A.LOCAL_BRANCH]),
    ('switch to branch feat_test', [A.LOCAL_BRANCH]),
    ('switch to dark mode', []),
    ('切换到 dark 主题', []),
    ('checkout index.html', []),
    ('pull this repository https://github.com/acme/project.git', [A.ACQUIRE_REPOSITORY]),
    ('请拉取这个项目 https://github.com/acme/project.git', [A.ACQUIRE_REPOSITORY]),
])
def test_human_command_witnesses(text, families):
    assert [item.family for item in repository_actions(text)] == families


def test_multiple_targets_preserve_ambiguity_instead_of_using_previous_repository():
    action, = repository_actions('clone https://github.com/a/one.git https://github.com/b/two.git')
    assert action.source is None and action.target_ambiguous


def test_source_url_does_not_include_sentence_punctuation():
    action, = repository_actions('clone https://github.com/acme/project.git, then discuss future changes')
    assert action.source == 'https://github.com/acme/project.git'


def test_versioned_matrix_matches_policy_and_never_grants_actor_authority():
    import json
    from pathlib import Path
    from spg.domain.action_admission import POLICY_VERSION
    matrix = json.loads(Path('benchmarks/golden/lifecycle-action-matrix-v1.json').read_text())
    assert matrix['policy_version'] == POLICY_VERSION
    assert len(matrix['rows']) >= 16
    for row in matrix['rows']:
        for action in A:
            facts = replace(BASE, **row['facts'])
            if action in {A.INSPECT, A.RESEARCH, A.NEW_WORK}:
                facts = replace(facts, terminal=False, retryable=False, attempts=0)
            decision = admit_action(action, facts)
            assert row['actions'][action.value] == {
                'eligibility': decision.eligibility.value,
                'execute': decision.execute, 'signal': decision.signal,
            }, (row['observed_state'], action)
            assert not admit_action(action, replace(facts, authority=False)).execute
