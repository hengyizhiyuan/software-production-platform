"""Product scope oracle accepts an inline addition but rejects unrelated edits."""
from benchmarks.golden.runtime.oracle import only_link_added


def test_navigation_scope_oracle_accepts_equivalent_minimal_insertions():
    anchor = '<a href="/help">使用帮助</a>'
    assert only_link_added([anchor], [], label='使用帮助', href='/help')
    assert only_link_added(['<nav>Existing '+anchor+'</nav>'], ['<nav>Existing</nav>'],
        label='使用帮助', href='/help')


def test_navigation_scope_oracle_rejects_unrequested_behavior_or_source_changes():
    for added in [
        '<nav>Changed <a href="/help">使用帮助</a></nav>',
        '<nav>Existing <a href="/other">使用帮助</a></nav>',
        '<nav>Existing <a href="/help" onclick="run()">使用帮助</a></nav>',
    ]:
        assert not only_link_added([added], ['<nav>Existing</nav>'], label='使用帮助', href='/help')
