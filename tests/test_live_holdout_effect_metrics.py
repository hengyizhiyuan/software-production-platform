from benchmarks.intent_realization.runtime.qualify_live_holdout import unexpected_branch_effect


def test_missing_requested_switch_is_missed_action_not_false_execution():
    case = {'expected_operations': ['CREATE_AND_SWITCH_BRANCH'], 'expected_branch': 'feat_next'}
    before = {'branches': ['main'], 'repository_ref': 'refs/heads/main', 'revision': 'a' * 40, 'tree': 'b' * 40}
    assert unexpected_branch_effect(case, before, dict(before)) is False
    after = {**before, 'branches': ['main', 'feat_next']}
    assert unexpected_branch_effect(case, before, after) is False


def test_wrong_target_partial_write_is_false_execution_even_if_head_stayed_main():
    case = {'expected_operations': ['CREATE_BRANCH'], 'expected_branch': 'feat_next'}
    before = {'branches': ['main'], 'repository_ref': 'refs/heads/main', 'revision': 'a' * 40, 'tree': 'b' * 40}
    assert unexpected_branch_effect(case, before, {**before, 'branches': ['main', 'refs/heads/main']}) is True
    assert unexpected_branch_effect(case, before, {**before, 'repository_ref': 'refs/heads/wrong'}) is True
    assert unexpected_branch_effect(case, before, {**before, 'revision': 'c' * 40}) is True


def test_unobserved_owner_storage_cannot_be_classified_as_zero_execution():
    case = {'expected_operations': [], 'expected_branch': None}
    assert unexpected_branch_effect(case, None, None) is None
