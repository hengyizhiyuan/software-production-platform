"""Provider-neutral contracts for single-PWU production planning."""

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from spg.domain.change import CodeChangeContract, ProductionTargetKind


class OnePwuFitClassification(StrEnum):
    ONE_PWU_FIT = "ONE_PWU_FIT"
    NEEDS_REFINEMENT = "NEEDS_REFINEMENT"
    MULTI_PWU_REQUIRED = "MULTI_PWU_REQUIRED"


class PlannedArtifactOperation(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"


class ProductionPlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    position: int = Field(ge=1)
    instruction: str = Field(min_length=1)


class ProductionPlanArtifactTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1)
    operation: PlannedArtifactOperation

    @field_validator("path")
    @classmethod
    def require_safe_repository_path(cls, value: str) -> str:
        if "\\" in value:
            raise ValueError("artifact path must use POSIX separators")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or value in {"", "."}:
            raise ValueError("artifact path must be repository-relative")
        if ".git" in path.parts:
            raise ValueError("artifact path cannot address Git internals")
        return str(path)


class ProductionPlanProposal(BaseModel):
    """Durable plan proposal; its ordered steps remain inside one MVP PWU."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: UUID
    target_kind: ProductionTargetKind = ProductionTargetKind.DOCUMENTATION_WORK
    objective: str = Field(min_length=1)
    desired_outcome: str = Field(min_length=1)
    ordered_steps: tuple[ProductionPlanStep, ...] = Field(min_length=1)
    artifact_targets: tuple[ProductionPlanArtifactTarget, ...] = ()
    change_contract: CodeChangeContract | None = None
    inherited_constraints: tuple[str, ...] = ()
    verification_approach: str = Field(min_length=1)
    assumptions: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    fit_classification: OnePwuFitClassification
    engineering_resource_id: UUID
    repository_identity: str = Field(min_length=1)
    source_baseline_id: UUID
    source_revision: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_ordered_single_pwu_plan(self) -> "ProductionPlanProposal":
        positions = tuple(step.position for step in self.ordered_steps)
        if positions != tuple(range(1, len(positions) + 1)):
            raise ValueError("Production Plan steps must be contiguous and ordered from 1")
        paths = tuple(target.path for target in self.artifact_targets)
        if len(paths) != len(set(paths)):
            raise ValueError("Production Plan artifact targets must be unique")
        if self.artifact_targets and self.change_contract is not None:
            raise ValueError("a Production Plan cannot mix documentation and code contracts")
        if self.target_kind is ProductionTargetKind.CODE_WORK and self.artifact_targets:
            raise ValueError("CODE_WORK cannot use documentation artifact targets")
        if (
            self.target_kind is ProductionTargetKind.DOCUMENTATION_WORK
            and self.change_contract is not None
        ):
            raise ValueError("DOCUMENTATION_WORK cannot use a Code Change Contract")
        if self.fit_classification is OnePwuFitClassification.ONE_PWU_FIT and not (
            self.artifact_targets or self.change_contract is not None
        ):
            raise ValueError("ONE_PWU_FIT requires an admitted production target")
        return self


class ProductionPlanningRequest(BaseModel):
    """Governed facts available to planning; no conversation history is admitted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    work_id: UUID
    target_kind: ProductionTargetKind = ProductionTargetKind.DOCUMENTATION_WORK
    admitted_requirement: str = Field(min_length=1)
    desired_outcome: str = Field(min_length=1)
    production_objective: str = Field(min_length=1)
    artifact_targets: tuple[ProductionPlanArtifactTarget, ...] = ()
    change_contract: CodeChangeContract | None = None
    constraints: tuple[str, ...] = ()
    verification_expectation: str = Field(min_length=1)
    engineering_scope_summary: str = Field(min_length=1)
    engineering_resource_id: UUID
    repository_identity: str = Field(min_length=1)
    source_baseline_id: UUID
    source_revision: str = Field(min_length=1)
    context_references: tuple[str, ...] = ()
    refinement_reasons: tuple[str, ...] = ()


class ProductionPlanner(Protocol):
    """Replaceable planning intelligence behind a stable production contract."""

    def propose(self, request: ProductionPlanningRequest) -> ProductionPlanProposal:
        ...
