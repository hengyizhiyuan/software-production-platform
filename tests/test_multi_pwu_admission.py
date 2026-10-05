"""Reject empty/uncovered production before queue admission; preserve history."""
import pytest
from spg.application.planning import ProductionPlanningService
from spg.application.runtime import RuntimeService
from spg.domain.planning import ProductionPlanGraph, ProductionNodeKind
from spg.domain.runtime import CompletionContract, RuntimeInvariantViolation
from spg.providers.rule_based_planner import RuleBasedProductionPlanner
from tests.test_multi_pwu_planning import _request


def plan():
    return RuleBasedProductionPlanner().propose(_request('index.html', 'tests/navigation.test.js'))


@pytest.mark.parametrize('field,value,reason', [
    ('writable_paths', (), 'EMPTY_PWU'),
    ('objective', ' ', 'EMPTY_PWU'),
    ('verification_requirements', (), 'VERIFICATION_MISSING'),
    ('writable_paths', ('unapproved.html',), 'SCOPE_NOT_ADMITTED'),
])
def test_invalid_dual_target_node_cannot_materialize_pwu(field, value, reason):
    proposal = plan()
    nodes = tuple(node.model_copy(update={field:value}) if node.node_id == 'pwu:2' else node
                  for node in proposal.graph.nodes)
    invalid = proposal.model_copy(update={'graph':proposal.graph.model_copy(update={'nodes':nodes})})
    # Historical serialization is still readable; new admission rejects it.
    contract = CompletionContract(required_outputs=('index.html', 'tests/navigation.test.js'),
        required_changes=('index.html', 'tests/navigation.test.js'),
        verification_obligations=('PATH_SCOPE',), production_plan=invalid)
    with pytest.raises(RuntimeInvariantViolation, match=reason):
        RuntimeService._validate_plan_admission(contract)


def test_dual_target_source_and_navigation_test_never_have_empty_scoped_units():
    proposal = plan()
    contract = CompletionContract(required_outputs=('index.html', 'tests/navigation.test.js'),
        required_changes=('index.html', 'tests/navigation.test.js'),
        verification_obligations=('PATH_SCOPE',), production_plan=proposal)
    RuntimeService._validate_plan_admission(contract)
    for node in proposal.graph.nodes:
        if node.kind is ProductionNodeKind.GROUP:
            continue
        scoped = RuntimeService._scoped_contract(contract, node, proposal.source_baseline_id, proposal.source_revision)
        assert scoped.required_outputs and scoped.required_changes and scoped.verification_obligations


@pytest.mark.parametrize('dependencies,reason', [
    (('missing',), 'missing'), (('pwu:2',), 'cycle'),
])
def test_cycle_or_missing_predecessor_is_rejected(dependencies, reason):
    graph = plan().graph
    nodes = tuple(node.model_copy(update={'dependency_ids':dependencies}) if node.node_id == 'pwu:1'
        else node.model_copy(update={'dependency_ids':('pwu:1',)}) if node.node_id == 'pwu:2'
        else node for node in graph.nodes)
    with pytest.raises(ValueError, match=reason):
        ProductionPlanGraph.model_validate(graph.model_copy(update={'nodes':nodes}).model_dump(mode='json'))


def test_authority_boundary_refines_bad_provider_without_accepting_empty_node():
    request = _request('index.html', 'tests/navigation.test.js')
    valid = RuleBasedProductionPlanner().propose(request)
    nodes = tuple(node.model_copy(update={'writable_paths':()}) if node.node_id == 'pwu:2' else node
                  for node in valid.graph.nodes)
    class BadPlanner:
        def propose(self, request):
            return valid.model_copy(update={'graph':valid.graph.model_copy(update={'nodes':nodes})})
    corrected = ProductionPlanningService(BadPlanner()).propose(request)
    corrected.graph.validate_admission({'index.html', 'tests/navigation.test.js'})
    assert all(node.writable_paths for node in corrected.graph.nodes if node.kind is ProductionNodeKind.PWU)


def test_material_graph_change_changes_proposal_identity():
    request = _request('src/alpha.py', 'src/beta.py')
    first = RuleBasedProductionPlanner().propose(request)
    second = RuleBasedProductionPlanner().propose(request.model_copy(update={'target_effort_seconds':{'src/alpha.py':100}}))
    assert first.proposal_id != second.proposal_id
