"""Permanent semantic graph and conservative decomposition qualifications."""

from uuid import uuid4

import pytest

from spg.domain.planning import (
    OnePwuFitClassification, PlannedArtifactOperation, ProductionNodeKind,
    ProductionPlanArtifactTarget, ProductionPlanGraph, ProductionPlanNode,
    ProductionPlanningRequest,
)
from spg.providers.rule_based_planner import RuleBasedProductionPlanner


def _request(*paths: str, requirement: str = "independent capabilities"):
    return ProductionPlanningRequest(
        work_id=uuid4(), admitted_requirement=requirement,
        desired_outcome="all admitted surfaces changed", production_objective="Produce the admitted surfaces",
        artifact_targets=tuple(ProductionPlanArtifactTarget(
            path=path, operation=PlannedArtifactOperation.CREATE,
        ) for path in paths),
        verification_expectation="targeted tests", engineering_scope_summary="one repository",
        engineering_resource_id=uuid4(), repository_identity="test://multi-planning",
        source_baseline_id=uuid4(), source_revision="a" * 40,
    )


def test_distinct_capabilities_have_hierarchy_parallel_roots_and_join():
    plan = RuleBasedProductionPlanner().propose(_request(
        "src/auth.py", "tests/test_auth.py", "src/billing.py", "tests/test_billing.py",
    ))
    assert plan.fit_classification is OnePwuFitClassification.MULTI_PWU_FIT
    assert plan.graph is not None
    executable = [node for node in plan.graph.nodes if node.kind is not ProductionNodeKind.GROUP]
    assert len(executable) == 3
    assert executable[0].writable_paths == ("src/auth.py", "tests/test_auth.py")
    assert executable[1].writable_paths == ("src/billing.py", "tests/test_billing.py")
    assert executable[0].parent_id != executable[1].parent_id
    assert executable[2].kind is ProductionNodeKind.JOIN
    assert executable[2].dependency_ids == (executable[0].node_id, executable[1].node_id)


def test_one_web_feature_and_its_differently_named_test_remain_one_pwu():
    plan = RuleBasedProductionPlanner().propose(_request(
        "src/spg/web/app.js", "tests/js/test_web_state.cjs",
    ))
    assert plan.fit_classification is OnePwuFitClassification.ONE_PWU_FIT
    assert plan.graph is None


def test_historical_html_navigation_and_node_test_are_one_nonempty_obligation():
    plan = RuleBasedProductionPlanner().propose(_request("index.html", "tests/navigation.test.js"))
    assert plan.fit_classification is OnePwuFitClassification.ONE_PWU_FIT
    assert plan.graph is None
    assert tuple(item.path for item in plan.artifact_targets) == ("index.html", "tests/navigation.test.js")


def test_web_entrypoint_script_and_named_test_remain_one_coherent_pwu():
    plan = RuleBasedProductionPlanner().propose(_request(
        "index.html", "inventory.js", "tests/inventory.test.cjs",
    ))
    assert plan.fit_classification is OnePwuFitClassification.ONE_PWU_FIT
    assert plan.graph is None


def test_shared_interface_risk_forces_serial_baseline_evolution():
    plan = RuleBasedProductionPlanner().propose(_request(
        "src/auth.py", "src/billing.py", requirement="Independent capabilities: update shared interface across auth and billing",
    ))
    assert plan.graph is not None
    executable = [node for node in plan.graph.nodes if node.kind is not ProductionNodeKind.GROUP]
    assert [node.kind for node in executable] == [ProductionNodeKind.PWU, ProductionNodeKind.PWU]
    assert executable[1].dependency_ids == (executable[0].node_id,)


def test_steering_summary_cannot_discard_governed_predecessor_constraint():
    request = _request("team.html", "team-directory.html", requirement="Create two pages").model_copy(update={
        "constraints": ("team-directory 页面依赖前一步已验证的团队页，须在其之后产出。",),
    })
    plan = RuleBasedProductionPlanner().propose(request)
    units = [node for node in plan.graph.nodes if node.kind is not ProductionNodeKind.GROUP]
    assert [node.writable_paths for node in units] == [("team.html",), ("team-directory.html",)]
    assert units[0].dependency_ids == ()
    assert units[1].dependency_ids == (units[0].node_id,)


def test_estimated_oversize_is_split_at_safe_capability_boundary():
    request = _request("src/auth.py", "src/billing.py").model_copy(update={
        "target_effort_seconds": {"src/auth.py": 1_500, "src/billing.py": 1_500},
        "max_pwu_duration_seconds": 1_800,
    })
    plan = RuleBasedProductionPlanner().propose(request)
    assert plan.fit_classification is OnePwuFitClassification.MULTI_PWU_FIT
    assert plan.graph is not None
    independent = [node for node in plan.graph.nodes if node.kind is ProductionNodeKind.PWU]
    assert len(independent) == 2
    assert [node.estimated_duration_seconds for node in independent] == [1_500, 1_500]


def test_estimated_oversize_does_not_fragment_one_coherent_capability():
    request = _request("src/auth.py", "tests/test_auth.py").model_copy(update={
        "target_effort_seconds": {"src/auth.py": 1_500, "tests/test_auth.py": 1_500},
        "max_pwu_duration_seconds": 1_800,
    })
    plan = RuleBasedProductionPlanner().propose(request)
    assert plan.fit_classification is OnePwuFitClassification.NEEDS_REFINEMENT
    assert plan.graph is None
    assert "safe semantic split" in plan.unresolved_questions[0]


def test_graph_rejects_parallel_write_overlap_even_if_caller_bypasses_planner():
    def leaf(node_id: str):
        return ProductionPlanNode(
            node_id=node_id, kind=ProductionNodeKind.PWU,
            objective=node_id, writable_paths=("src/shared.py",),
            responsibility_boundary=node_id, acceptance_criteria=("verified",),
        )
    join = ProductionPlanNode(
        node_id="join", kind=ProductionNodeKind.JOIN,
        objective="integrate", dependency_ids=("a", "b"),
        responsibility_boundary="integration", acceptance_criteria=("verified",),
    )
    with pytest.raises(ValueError, match="parallel PWUs cannot write"):
        ProductionPlanGraph(nodes=(leaf("a"), leaf("b"), join), planning_rationale="unsafe")
    guarded = ProductionPlanGraph(
        nodes=(leaf("a"), leaf("b"), join),
        planning_rationale="overlap is explicitly reconciled and reverified",
        parallel_overlap_policy="EXPLICIT_JOIN_RECONCILIATION",
    )
    assert guarded.nodes[-1].kind is ProductionNodeKind.JOIN


def test_graph_rejects_hierarchy_cycle():
    a = ProductionPlanNode(node_id="a", kind=ProductionNodeKind.GROUP, objective="a", parent_id="b")
    b = ProductionPlanNode(node_id="b", kind=ProductionNodeKind.GROUP, objective="b", parent_id="a")
    work = ProductionPlanNode(
        node_id="work", kind=ProductionNodeKind.PWU, objective="work", parent_id="a",
        responsibility_boundary="bounded", acceptance_criteria=("verified",),
    )
    with pytest.raises(ValueError, match="hierarchy cycle"):
        ProductionPlanGraph(nodes=(a, b, work), planning_rationale="invalid")


@pytest.mark.parametrize('root',['','web/','nested/site/'])
def test_one_page_styles_and_script_form_one_verifiable_implementation(root):
    request=_request(*(root+p for p in ['index.html','styles.css','app.js']))
    plan=RuleBasedProductionPlanner().propose(request)
    assert plan.graph is None
    assert plan.fit_classification is OnePwuFitClassification.ONE_PWU_FIT
    assert {t.path for t in plan.artifact_targets}=={root+p for p in ['index.html','styles.css','app.js']}


def test_distinct_pages_keep_separate_implementation_units():
    plan=RuleBasedProductionPlanner().propose(_request('index.html','contact.html','app.js','styles.css'))
    assert plan.graph is not None
    assert plan.fit_classification is OnePwuFitClassification.MULTI_PWU_FIT


def test_ordinary_multifile_application_is_one_actual_verification_subject():
    paths = ('index.html', 'src/main.js', 'src/game/state.js', 'src/game/units.js',
             'src/render/renderer.js', 'src/assets/manifest.js')
    plan = RuleBasedProductionPlanner().propose(_request(*paths,
        requirement='Create one playable browser application using these modules'))
    assert plan.graph is None
    assert plan.fit_classification is OnePwuFitClassification.ONE_PWU_FIT
    assert tuple(t.path for t in plan.artifact_targets) == paths


def test_filenames_do_not_establish_independent_capabilities():
    plan = RuleBasedProductionPlanner().propose(_request('src/users.py', 'src/storage.py',
        requirement='Implement the admitted feature across these files'))
    assert plan.graph is None
    assert plan.fit_classification is OnePwuFitClassification.ONE_PWU_FIT
