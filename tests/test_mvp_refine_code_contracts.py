from pathlib import Path
import subprocess
from uuid import uuid4

from pydantic import ValidationError
import pytest

from spg.application.planning import ProductionPlanningService
from spg.application.refinement import RepositoryChangeProposalService
from spg.application.work import WorkApplicationService
from spg.domain.change import CodeVerificationKind, ProductionTargetKind
from spg.domain.planning import (
    OnePwuFitClassification,
    ProductionPlanProposal,
    ProductionPlanningRequest,
)
from spg.domain.product import ProductInvariantViolation
from spg.domain.product import WorkRefinementRequest
from spg.domain.refinement import (
    ProposalConfidence,
    ProposalTargetDisposition,
    RepositoryChangeProposalRequest,
)
from spg.providers.repository_change_proposal import (
    RepositoryAwareChangeProposalProvider,
)
from spg.providers.rule_based_planner import RuleBasedProductionPlanner


DOGFOOD_INTENT = (
    "让底部 Work Composer 的展开/收缩状态在页面刷新后保持用户上一次选择。"
    "只修改实现这个行为所需的前端文件和相关测试，"
    "不要改动其他功能，也不要进行 UI 重构。"
)


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


@pytest.fixture
def proposal_repository(tmp_path: Path) -> tuple[Path, str]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Proposal Test")
    _git(repository, "config", "user.email", "proposal@example.invalid")
    (repository / "src" / "spg" / "web").mkdir(parents=True)
    (repository / "src" / "spg" / "domain").mkdir(parents=True)
    (repository / "tests" / "js").mkdir(parents=True)
    (repository / "tests" / "integration").mkdir(parents=True)
    (repository / "src" / "spg" / "web" / "app.js").write_text(
        """const composer = document.querySelector("#composer");
const expanded = composer.getAttribute("aria-expanded") === "true";
composer.classList.toggle("expanded", !expanded);
const state = globalThis.localStorage;
""",
        encoding="utf-8",
    )
    (repository / "src" / "spg" / "web" / "index.html").write_text(
        """<button id="composer" aria-expanded="true">Collapse composer</button>
""",
        encoding="utf-8",
    )
    (repository / "src" / "spg" / "domain" / "backend.py").write_text(
        """COMPOSER_STATE = "backend must remain unrelated"
""",
        encoding="utf-8",
    )
    (repository / "tests" / "js" / "test_web_state.cjs").write_text(
        """const appPath = "src/spg/web/app.js";
test("composer expand state", () => appPath);
""",
        encoding="utf-8",
    )
    (repository / "tests" / "integration" / "test_api.py").write_text(
        'ASSET_NAMES = ("app.js",)\n',
        encoding="utf-8",
    )
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "proposal baseline")
    return repository, _git(repository, "rev-parse", "HEAD")


def _request(
    repository: Path,
    revision: str,
    *,
    intent: str = DOGFOOD_INTENT,
    explicit_targets: tuple[str, ...] = (),
) -> RepositoryChangeProposalRequest:
    return RepositoryChangeProposalRequest(
        work_id=uuid4(),
        refined_code_intent=intent,
        constraints=(
            "只修改实现这个行为所需的前端文件和相关测试，不要改动其他功能，也不要进行 UI 重构",
        ),
        engineering_resource_id=uuid4(),
        repository_identity="test://proposal-repository",
        repository_location=str(repository),
        source_baseline_id=uuid4(),
        source_ref="refs/heads/main",
        source_revision=revision,
        explicit_targets=explicit_targets,
    )


def test_refcode_01_02_08_repository_inspection_is_read_only_and_baseline_bound(
    proposal_repository: tuple[Path, str],
) -> None:
    repository, revision = proposal_repository
    before = (
        _git(repository, "rev-parse", "HEAD"),
        _git(repository, "status", "--porcelain"),
        _git(repository, "show-ref"),
    )

    proposal = RepositoryAwareChangeProposalProvider().propose(
        _request(repository, revision)
    )

    after = (
        _git(repository, "rev-parse", "HEAD"),
        _git(repository, "status", "--porcelain"),
        _git(repository, "show-ref"),
    )
    assert after == before
    assert proposal.source_revision == revision
    assert proposal.source_ref == "refs/heads/main"
    assert all(revision[:12] in target.evidence or "exact Source Baseline" in target.evidence
               for target in proposal.proposed_targets)


def test_refcode_05_07_09_12_24_dogfood_intent_gets_grounded_bounded_proposal(
    proposal_repository: tuple[Path, str],
) -> None:
    repository, revision = proposal_repository

    proposal = RepositoryAwareChangeProposalProvider().propose(
        _request(repository, revision)
    )

    required = tuple(target.path for target in proposal.required_targets)
    assert required == (
        "src/spg/web/app.js",
        "tests/js/test_web_state.cjs",
    )
    assert "src/spg/domain/backend.py" not in {
        target.path for target in proposal.proposed_targets
    }
    assert "src/spg/domain/**" in proposal.forbidden_areas
    assert proposal.confidence is ProposalConfidence.MEDIUM
    assert all(target.rationale and target.evidence for target in proposal.proposed_targets)
    assert proposal.provenance.inspection_method.startswith("git-object-read-only")
    assert WorkApplicationService._is_code_work(DOGFOOD_INTENT, WorkRefinementRequest())
    assert DOGFOOD_INTENT not in Path(
        "src/spg/providers/repository_change_proposal.py"
    ).read_text(encoding="utf-8")


def test_refcode_06_07_conditional_target_remains_non_authoritative(
    proposal_repository: tuple[Path, str],
) -> None:
    repository, revision = proposal_repository
    proposal = RepositoryAwareChangeProposalProvider().propose(
        _request(repository, revision)
    )

    conditional = proposal.conditional_targets
    assert conditional
    assert all(
        target.disposition is ProposalTargetDisposition.CONDITIONAL
        for target in conditional
    )
    assert not set(target.path for target in conditional) & set(
        target.path for target in proposal.required_targets
    )


def test_refcode_05_explicit_path_is_preserved(
    proposal_repository: tuple[Path, str],
) -> None:
    repository, revision = proposal_repository
    proposal = RepositoryAwareChangeProposalProvider().propose(
        _request(
            repository,
            revision,
            intent="Modify src/spg/web/app.js",
            explicit_targets=("src/spg/web/app.js",),
        )
    )

    assert tuple(target.path for target in proposal.required_targets) == (
        "src/spg/web/app.js",
    )
    assert proposal.confidence is ProposalConfidence.HIGH


def test_refcode_06_bounded_area_is_supported_without_root_fallback(
    proposal_repository: tuple[Path, str],
) -> None:
    repository, revision = proposal_repository
    request = _request(repository, revision, intent="Modify the bounded web area").model_copy(
        update={"explicit_allowed_areas": ("src/spg/web/**",)}
    )

    proposal = RepositoryAwareChangeProposalProvider().propose(request)

    assert proposal.allowed_areas == ("src/spg/web/**",)
    assert not proposal.required_targets
    assert not proposal.unresolved_scope_questions


def test_refcode_10_11_ambiguous_work_has_no_repository_wide_fallback(
    proposal_repository: tuple[Path, str],
) -> None:
    repository, revision = proposal_repository
    proposal = RepositoryAwareChangeProposalProvider().propose(
        _request(repository, revision, intent="Improve code somehow")
    )

    assert not proposal.required_targets
    assert not proposal.allowed_areas
    assert proposal.unresolved_scope_questions
    assert not {"src/**", "tests/**", "**/*"} & set(proposal.allowed_areas)


def test_refcode_20_frontend_verification_gap_is_truthful(
    proposal_repository: tuple[Path, str],
) -> None:
    repository, revision = proposal_repository
    proposal = RepositoryAwareChangeProposalProvider().propose(
        _request(repository, revision)
    )

    assert tuple(item.kind for item in proposal.verification_obligations) == (
        CodeVerificationKind.PATH_SCOPE,
        CodeVerificationKind.GIT_DIFF_CHECK,
    )
    assert any(
        "FRONTEND_VERIFICATION_CONTRACT_GAP" in question
        for question in proposal.unresolved_scope_questions
    )
    assert "NODE_TEST" not in CodeVerificationKind.__members__


class _WrongBaselineProvider:
    def propose(self, request: RepositoryChangeProposalRequest):
        proposal = RepositoryAwareChangeProposalProvider().propose(request)
        return proposal.model_copy(update={"source_revision": "f" * 40})


def test_refcode_02_13_provider_cannot_change_baseline_or_resource(
    proposal_repository: tuple[Path, str],
) -> None:
    repository, revision = proposal_repository
    with pytest.raises(ProductInvariantViolation, match="Source Baseline"):
        RepositoryChangeProposalService(_WrongBaselineProvider()).propose(
            _request(
                repository,
                revision,
                explicit_targets=("src/spg/web/app.js",),
            )
        )


def test_refcode_10_proposal_rejects_broad_source_root_fallback(
    proposal_repository: tuple[Path, str],
) -> None:
    repository, revision = proposal_repository
    request = _request(repository, revision).model_copy(
        update={"explicit_allowed_areas": ("src/**",)}
    )
    with pytest.raises(ValidationError, match="broad source/test-root fallback"):
        RepositoryAwareChangeProposalProvider().propose(request)


def test_refcode_03_22_23_contract_is_provider_neutral_and_has_no_execution() -> None:
    domain_source = Path("src/spg/domain/refinement.py").read_text(encoding="utf-8")
    provider_source = Path(
        "src/spg/providers/repository_change_proposal.py"
    ).read_text(encoding="utf-8")

    assert "Codex" not in domain_source
    assert "subprocess" not in domain_source
    assert "Thread" not in provider_source
    assert "Executor" not in provider_source
    assert "embedding" not in provider_source.casefold()


class _ProposalExpandingPlanner:
    def propose(self, request: ProductionPlanningRequest) -> ProductionPlanProposal:
        plan = RuleBasedProductionPlanner().propose(request)
        assert request.change_proposal is not None
        expanded = request.change_proposal.model_copy(
            update={"allowed_areas": ("src/spg/web/**",)}
        )
        return plan.model_copy(update={"change_proposal": expanded})


def test_refcode_18_planner_cannot_widen_change_proposal(
    proposal_repository: tuple[Path, str],
) -> None:
    repository, revision = proposal_repository
    proposal = RepositoryAwareChangeProposalProvider().propose(
        _request(
            repository,
            revision,
            intent="Modify src/spg/web/app.js",
            explicit_targets=("src/spg/web/app.js",),
        )
    )
    request = ProductionPlanningRequest(
        work_id=uuid4(),
        target_kind=ProductionTargetKind.CODE_WORK,
        admitted_requirement="Modify one exact frontend file",
        desired_outcome="Update the admitted frontend behavior",
        production_objective="Update the admitted frontend behavior",
        change_proposal=proposal,
        constraints=("Do not widen scope.",),
        verification_expectation="Run the proposed typed checks.",
        engineering_scope_summary="One governed repository",
        engineering_resource_id=proposal.engineering_resource_id,
        repository_identity=proposal.repository_identity,
        source_baseline_id=proposal.source_baseline_id,
        source_revision=proposal.source_revision,
    )

    plan = ProductionPlanningService(_ProposalExpandingPlanner()).propose(request)

    assert plan.fit_classification is OnePwuFitClassification.NEEDS_REFINEMENT
    assert plan.change_proposal == proposal
    assert "unauthorized Change Proposal" in plan.unresolved_questions[0]
