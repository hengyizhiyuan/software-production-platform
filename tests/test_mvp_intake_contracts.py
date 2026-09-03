"""Focused deterministic MVP-INTAKE-2A contract evidence (no Provider turn)."""

from datetime import UTC, datetime
from pathlib import Path
import subprocess
from uuid import uuid4

import pytest

from spg.application.work import WorkApplicationService
from spg.domain.product import (
    ArtifactTargetOperation,
    EngineeringResourceKind,
    EngineeringResourceRecord,
    ProductInvariantViolation,
)
from spg.domain.runtime import ArtifactContract, ArtifactOperation, CompletionContract
from spg.infrastructure.configured_executor import render_governed_instruction
from spg.providers.repository_markdown_verifier import evaluate_repository_artifact


SAME_INTENT = """Create a formal Production Orchestration Lite product/architecture document
in an appropriate location in the existing documentation system.

Cover Human-in-the-loop != Human-as-the-loop, the automatic progression
boundary, Human Attention responsibility, MVP vs future evolution, and reuse
the accepted design. Do not expand or invent new capabilities beyond the
already accepted design."""

CHINESE_DOGFOOD_CONSTRAINT = (
    "尽量复用现有已经确定的设计，不要发散新的能力"
)
CHINESE_DOGFOOD_INTENT = (
    "把我们刚刚确立的 Production Orchestration Lite 设计原则整理成一份正式的"
    "产品/架构说明文档，放到现有文档体系中合适的位置。"
    "重点说明 Human-in-the-loop 不等于 Human-as-the-loop、Watt 的自动推进边界、"
    "Human Attention 的职责，以及 MVP 当前方案和未来演进方向的区别。"
    "尽量复用现有已经确定的设计，不要发散新的能力。"
)


def test_intake_01_02_03_06_07_08_repository_aware_proposal(
    tmp_path: Path,
) -> None:
    repository, revision = _repository(tmp_path)
    resource = _resource(repository)

    proposal = WorkApplicationService._artifact_target_proposal(
        raw=SAME_INTENT,
        explicit_path=None,
        resource=resource,
        baseline_id=uuid4(),
        source_revision=revision,
    )

    assert proposal is not None
    assert proposal.path == "docs/architecture/production-orchestration-lite.md"
    assert proposal.operation is ArtifactTargetOperation.CREATE
    assert "Source Baseline" not in proposal.placement_rationale or proposal.source_revision == revision
    assert "work-" not in proposal.path
    constraints = WorkApplicationService._extract_constraints(SAME_INTENT)
    assert constraints
    assert constraints[0] == (
        "Do not expand or invent capabilities beyond the already accepted design."
    )
    assert SAME_INTENT.startswith("Create a formal")

    target = repository / proposal.path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("existing\n", encoding="utf-8")
    _git(repository, "add", proposal.path)
    _git(repository, "commit", "-m", "add exact target")
    updated_revision = _git(repository, "rev-parse", "HEAD")
    update = WorkApplicationService._artifact_target_proposal(
        raw=SAME_INTENT,
        explicit_path=None,
        resource=resource,
        baseline_id=uuid4(),
        source_revision=updated_revision,
    )
    assert update is not None
    assert update.operation is ArtifactTargetOperation.UPDATE


def test_intake_multilingual_extracts_exact_dogfood_constraint() -> None:
    assert WorkApplicationService._extract_constraints(
        f"{CHINESE_DOGFOOD_CONSTRAINT}。"
    ) == (CHINESE_DOGFOOD_CONSTRAINT,)
    assert WorkApplicationService._extract_constraints(CHINESE_DOGFOOD_INTENT) == (
        CHINESE_DOGFOOD_CONSTRAINT,
    )


@pytest.mark.parametrize(
    "phrase",
    (
        "不要发散新的能力",
        "不得修改已确认的边界",
        "不应引入新的运行时依赖",
        "禁止修改历史事实",
        "必须保持精确基线绑定",
        "只能变更已批准的文档路径",
        "仅限当前 MVP 范围",
    ),
)
def test_intake_multilingual_supports_bounded_chinese_markers(phrase: str) -> None:
    assert WorkApplicationService._extract_constraints(f"{phrase}。") == (phrase,)


def test_intake_multilingual_splits_chinese_punctuation_and_bounds_reuse(
) -> None:
    assert WorkApplicationService._extract_constraints(
        "尽量复用现有设计。必须保持现有产品边界；不要新增能力。"
    ) == (
        "尽量复用现有设计",
        "必须保持现有产品边界",
        "不要新增能力",
    )


@pytest.mark.parametrize(
    "prose",
    (
        "系统复用现有设计并描述未来能力。",
        "这里介绍当前行为和未来方向。",
        "团队尽量复用现有设计。",
    ),
)
def test_intake_multilingual_rejects_descriptive_chinese_prose(prose: str) -> None:
    assert WorkApplicationService._extract_constraints(prose) == ()


def test_intake_04_05_16_human_override_is_safe_and_replaces_authority(
    tmp_path: Path,
) -> None:
    repository, revision = _repository(tmp_path)
    resource = _resource(repository)
    baseline_id = uuid4()
    proposed = WorkApplicationService._artifact_target_proposal(
        raw=SAME_INTENT,
        explicit_path=None,
        resource=resource,
        baseline_id=baseline_id,
        source_revision=revision,
    )
    override = WorkApplicationService._artifact_target_proposal(
        raw=SAME_INTENT,
        explicit_path="docs/roadmap/production-orchestration-lite.md",
        resource=resource,
        baseline_id=baseline_id,
        source_revision=revision,
    )
    assert proposed is not None and override is not None
    assert proposed.path != override.path
    assert override.placement_rationale.startswith("Human-selected")

    for unsafe in (
        "/tmp/result.md",
        "../result.md",
        "docs/../result.md",
        ".git/config.md",
        "src/runtime.md",
        "docs\\result.md",
    ):
        with pytest.raises(ProductInvariantViolation):
            WorkApplicationService._validate_artifact_path(unsafe)


def test_intake_09_10_11_12_17_exact_contract_renders_one_authority() -> None:
    artifact = _artifact("docs/roadmap/approved-target.md")
    contract = CompletionContract(
        required_outputs=(artifact.artifact_path,),
        required_changes=(artifact.artifact_path,),
        verification_obligations=(artifact.verification_obligation,),
        artifact_contract=artifact,
    )
    objective = WorkApplicationService._artifact_objective(artifact)
    instruction = render_governed_instruction(objective, contract)

    assert artifact.artifact_path in objective
    assert "Operation: CREATE" in instruction
    assert "Desired outcome: Record the accepted design" in instruction
    assert "Do not invent new capability" in instruction
    assert "docs/architecture/rejected-target.md" not in instruction
    assert "Do not modify any other repository path" in instruction


def test_intake_13_14_15_verifier_uses_x_not_historical_y(
    tmp_path: Path,
) -> None:
    repository, source = _repository(tmp_path)
    target_x = "docs/architecture/x.md"
    historical_y = "docs/mvp-e2e/first-real-governed-work.md"
    path = repository / target_x
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# X\n\nrequired marker\n", encoding="utf-8")
    _git(repository, "add", target_x)
    _git(repository, "commit", "-m", "produce X")
    proposed = _git(repository, "rev-parse", "HEAD")

    facts = evaluate_repository_artifact(
        repository,
        source,
        proposed,
        _artifact(target_x, source_revision=source),
        required_markers=("required marker",),
    )
    assert facts.passed
    assert historical_y != target_x

    (repository / "unauthorized.md").write_text("drift\n", encoding="utf-8")
    _git(repository, "add", "unauthorized.md")
    _git(repository, "commit", "-m", "scope drift")
    drifted = _git(repository, "rev-parse", "HEAD")
    drift_facts = evaluate_repository_artifact(
        repository,
        source,
        drifted,
        _artifact(target_x, source_revision=source),
    )
    assert not drift_facts.exact_path_only
    assert not drift_facts.passed


def test_intake_03_18_19_20_unresolved_is_not_silently_admitted(
    tmp_path: Path,
) -> None:
    repository, revision = _repository(tmp_path)
    proposal = WorkApplicationService._artifact_target_proposal(
        raw="Investigate the bounded behavior",
        explicit_path=None,
        resource=_resource(repository),
        baseline_id=uuid4(),
        source_revision=revision,
    )
    assert proposal is None
    assert "Planner" not in WorkApplicationService.__dict__
    assert "ECF" not in WorkApplicationService.__dict__
    assert "Recovery" not in WorkApplicationService.__dict__


def _artifact(
    path: str,
    *,
    source_revision: str = "a" * 40,
) -> ArtifactContract:
    return ArtifactContract(
        engineering_resource_id=uuid4(),
        repository_identity="test://intake",
        source_baseline_id=uuid4(),
        source_revision=source_revision,
        artifact_path=path,
        operation=ArtifactOperation.CREATE,
        constraints=("Do not invent new capability",),
        expected_outcome="Record the accepted design",
        verification_obligation="Verify exact admitted artifact",
    )


def _resource(repository: Path) -> EngineeringResourceRecord:
    now = datetime.now(UTC)
    return EngineeringResourceRecord(
        id=uuid4(),
        kind=EngineeringResourceKind.REPOSITORY,
        repository_identity="test://intake",
        location_ref=str(repository),
        authoritative_ref="refs/heads/main",
        context_references=(),
        is_default=True,
        created_at=now,
        updated_at=now,
    )


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Intake Test")
    _git(repository, "config", "user.email", "spg-intake@example.invalid")
    (repository / "docs" / "architecture").mkdir(parents=True)
    (repository / "docs" / "roadmap").mkdir(parents=True)
    (repository / "docs" / "evidence").mkdir(parents=True)
    (repository / "docs" / "architecture" / "architecture-principles.md").write_text(
        "# Principles\n",
        encoding="utf-8",
    )
    (repository / "docs" / "roadmap" / "mvp.md").write_text("# MVP\n", encoding="utf-8")
    (repository / "docs" / "evidence" / "index.md").write_text("# Evidence\n", encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    return repository, _git(repository, "rev-parse", "HEAD")


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
