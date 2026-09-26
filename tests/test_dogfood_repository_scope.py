"""A Human nav-link request admits only repository-proven necessary paths."""

from pathlib import Path
import subprocess
from uuid import uuid4

from spg.application.planning import ProductionPlanningService
from spg.application.refinement import RepositoryChangeProposalService
from spg.application.semantic_steps import SemanticStepApplicationService
from spg.domain.change import CodeVerificationKind, ProductionTargetKind
from spg.domain.planning import OnePwuFitClassification
from spg.domain.refinement import RepositoryChangeProposalRequest
from spg.domain.steering import (
    SemanticProductionProposal, SemanticStepInput, SemanticStepResultCandidate,
)
from spg.providers.repository_change_proposal import RepositoryAwareChangeProposalProvider
from spg.providers.rule_based_planner import RuleBasedProductionPlanner


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def test_nav_link_discovers_markup_without_promoting_adjacent_files(tmp_path: Path) -> None:
    repository = tmp_path / "source"
    (repository / "src/spg/web").mkdir(parents=True)
    (repository / "tests/js").mkdir(parents=True)
    _git(repository, "init", "-b", "main")
    (repository / "src/spg/web/index.html").write_text(
        '<header class="topbar"><nav><a href="/delivery">Deliveries</a></nav></header>',
        encoding="utf-8",
    )
    (repository / "src/spg/web/app.js").write_text(
        "const app = document.querySelector('main');\n", encoding="utf-8",
    )
    (repository / "src/spg/web/styles.css").write_text(
        ".topbar { display: flex; }\n", encoding="utf-8",
    )
    (repository / "tests/js/test_ui.cjs").write_text(
        "const entry = 'index.html';\n", encoding="utf-8",
    )
    _git(repository, "add", ".")
    _git(repository, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "commit", "-m", "baseline")
    revision = _git(repository, "rev-parse", "HEAD")

    proposal = RepositoryAwareChangeProposalProvider().propose(
        RepositoryChangeProposalRequest(
            work_id=uuid4(),
            refined_code_intent=(
                "在现有网站顶部导航栏增加一个“关于我们”的文字链接，链接到 /about。"
            ),
            constraints=("改动限于在现有网站顶部导航栏新增一个文字链接",),
            engineering_resource_id=uuid4(),
            repository_identity="https://example.invalid/source.git",
            repository_location=str(repository),
            source_baseline_id=uuid4(), source_ref="refs/heads/main",
            source_revision=revision,
        )
    )

    assert [target.path for target in proposal.required_targets] == [
        "src/spg/web/index.html"
    ]
    assert not any(target.path.startswith("tests/") for target in proposal.required_targets)
    assert any(target.path == "tests/js/test_ui.cjs" for target in proposal.conditional_targets)
    assert all(obligation.kind is not CodeVerificationKind.NODE_TEST_TARGET
               for obligation in proposal.verification_obligations)

    fallback = RepositoryAwareChangeProposalProvider().propose(
        RepositoryChangeProposalRequest(
            work_id=uuid4(), refined_code_intent="Improve bounded behavior",
            engineering_resource_id=uuid4(),
            repository_identity="https://example.invalid/source.git",
            repository_location=str(repository), source_baseline_id=uuid4(),
            source_ref="refs/heads/main", source_revision=revision,
            candidate_targets=("src/spg/web/app.js",),
        )
    )
    assert [target.path for target in fallback.required_targets] == [
        "src/spg/web/app.js"
    ]
    assert "Human did not name" in fallback.required_targets[0].rationale


def test_provider_cannot_add_about_route_to_admitted_nav_link_work(tmp_path: Path) -> None:
    repository = tmp_path / "source"
    (repository / "src/spg/web").mkdir(parents=True)
    (repository / "src/spg/web/index.html").write_text(
        '<header><nav><a href="/delivery">Deliveries</a></nav></header>',
        encoding="utf-8",
    )
    _git(repository, "init", "-b", "main")
    _git(repository, "add", ".")
    _git(repository, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "commit", "-m", "baseline")
    revision = _git(repository, "rev-parse", "HEAD")
    desired = "在现有网站顶部导航栏增加一个“关于我们”的文字链接，链接到 /about。"
    semantic_input = SemanticStepInput.model_construct(
        work_id=uuid4(), desired_outcome=desired,
        constraints=("只在现有网站顶部导航栏新增一个文字链接，不改变其他功能",),
        work_requests=(desired,), repository_tree_paths=("src/spg/web/index.html",),
        engineering_resource_id=uuid4(), source_baseline_id=uuid4(),
        repository_identity="https://example.invalid/source.git",
        repository_location=str(repository), repository_ref="refs/heads/main",
        source_revision=revision, engineering_scope_summary="one repository",
        context_materials=(),
    )
    candidate = SemanticStepResultCandidate.model_construct(
        proposed_production=SemanticProductionProposal(
            target_kind=ProductionTargetKind.CODE_WORK,
            objective="Add a /about route in src/spg/api/http.py and the nav link",
            code_targets=("src/spg/web/index.html",),
            verification_expectation="Assert GET /about returns a new page",
        )
    )
    service = object.__new__(SemanticStepApplicationService)
    service.change_proposals = RepositoryChangeProposalService(
        RepositoryAwareChangeProposalProvider()
    )
    service.planning = ProductionPlanningService(RuleBasedProductionPlanner())

    plan, change = service._materialize_production_plan(semantic_input, candidate)

    assert plan.objective == desired
    assert "route" not in plan.objective
    assert "GET /about" not in plan.verification_approach
    assert plan.fit_classification is OnePwuFitClassification.ONE_PWU_FIT
    assert change is not None
    assert [target.path for target in change.required_targets] == [
        "src/spg/web/index.html"
    ]
