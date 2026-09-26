"""Provider-neutral contracts for governed production planning."""

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from spg.domain.change import CodeChangeContract, ProductionTargetKind
from spg.domain.engineering_semantics import SemanticFactReference
from spg.domain.refinement import RepositoryChangeProposal


class OnePwuFitClassification(StrEnum):
    ONE_PWU_FIT = "ONE_PWU_FIT"
    MULTI_PWU_FIT = "MULTI_PWU_FIT"
    NEEDS_REFINEMENT = "NEEDS_REFINEMENT"
    MULTI_PWU_REQUIRED = "MULTI_PWU_REQUIRED"


class PlannedArtifactOperation(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"


class ProductionPlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    position: int = Field(ge=1)
    instruction: str = Field(min_length=1)


class ProductionNodeKind(StrEnum):
    GROUP = "GROUP"
    PWU = "PWU"
    JOIN = "JOIN"


class ProductionPlanNode(BaseModel):
    """One semantic group or executable leaf in a versioned production DAG."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(min_length=1)
    kind: ProductionNodeKind
    objective: str = Field(min_length=1)
    parent_id: str | None = None
    dependency_ids: tuple[str, ...] = ()
    writable_paths: tuple[str, ...] = ()
    context_references: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    authority_scope: tuple[str, ...] = ()
    responsibility_boundary: str | None = None
    acceptance_criteria: tuple[str, ...] = ()
    verification_requirements: tuple[str, ...] = ()
    estimated_duration_seconds: int = Field(default=900, ge=1)
    model_token_budget: int = Field(default=20_000, ge=1)
    compute_budget_seconds: int = Field(default=1_800, ge=1)
    atomicity_rationale: str | None = None

    @field_validator("writable_paths")
    @classmethod
    def require_safe_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(ProductionPlanArtifactTarget.require_safe_repository_path(path) for path in value)

    @model_validator(mode="after")
    def require_executable_boundary(self) -> "ProductionPlanNode":
        if self.kind is ProductionNodeKind.GROUP:
            if self.dependency_ids or self.writable_paths:
                raise ValueError("semantic group cannot execute or depend on PWUs")
        elif not self.responsibility_boundary or not self.acceptance_criteria:
            raise ValueError("executable PWU needs responsibility and acceptance boundaries")
        if self.kind is ProductionNodeKind.JOIN and len(self.dependency_ids) < 2:
            raise ValueError("Join PWU requires at least two parent PWUs")
        if self.kind is not ProductionNodeKind.JOIN and len(self.dependency_ids) > 1:
            raise ValueError("multi-parent dependency requires an explicit Join PWU")
        if len(self.dependency_ids) != len(set(self.dependency_ids)):
            raise ValueError("PWU dependencies must be unique")
        return self


class ProductionPlanGraph(BaseModel):
    """Semantic hierarchy and executable dependency graph, kept separate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    nodes: tuple[ProductionPlanNode, ...] = Field(min_length=1)
    planning_rationale: str = Field(min_length=1)
    starting_baseline_id: UUID | None = None
    parallel_overlap_policy: Literal["FORBID", "EXPLICIT_JOIN_RECONCILIATION"] = "FORBID"

    @model_validator(mode="after")
    def validate_graph(self) -> "ProductionPlanGraph":
        nodes = {node.node_id: node for node in self.nodes}
        if len(nodes) != len(self.nodes):
            raise ValueError("Production Plan node identities must be unique")
        executable = {key: node for key, node in nodes.items() if node.kind is not ProductionNodeKind.GROUP}
        if not executable:
            raise ValueError("Production Plan needs an executable PWU")
        for node in self.nodes:
            if node.parent_id is not None:
                parent = nodes.get(node.parent_id)
                if parent is None or parent.kind is not ProductionNodeKind.GROUP:
                    raise ValueError("semantic parent must be an existing group")
            if node.node_id in node.dependency_ids or any(dep not in executable for dep in node.dependency_ids):
                raise ValueError("PWU dependency is missing or self-referential")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("Production Plan dependency cycle")
            if node_id in visited:
                return
            visiting.add(node_id)
            for dependency in executable[node_id].dependency_ids:
                visit(dependency)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in executable:
            visit(node_id)
        def ancestors(node_id: str) -> set[str]:
            result: set[str] = set()
            for dependency in executable[node_id].dependency_ids:
                result.add(dependency)
                result.update(ancestors(dependency))
            return result

        leaves_to_check = tuple(node for node in executable.values() if node.kind is not ProductionNodeKind.JOIN)
        for index, first in enumerate(leaves_to_check):
            for second in leaves_to_check[index + 1:]:
                overlap = set(first.writable_paths).intersection(second.writable_paths)
                concurrent = (
                    first.node_id not in ancestors(second.node_id)
                    and second.node_id not in ancestors(first.node_id)
                )
                if overlap and concurrent:
                    protected = self.parallel_overlap_policy == "EXPLICIT_JOIN_RECONCILIATION" and any(
                        join.kind is ProductionNodeKind.JOIN
                        and first.node_id in ancestors(join.node_id)
                        and second.node_id in ancestors(join.node_id)
                        for join in executable.values()
                    )
                    if not protected:
                        raise ValueError("parallel PWUs cannot write the same path")
        for node in nodes.values():
            parents: set[str] = set()
            cursor = node.parent_id
            while cursor is not None:
                if cursor in parents or cursor == node.node_id:
                    raise ValueError("Production Plan hierarchy cycle")
                parents.add(cursor)
                cursor = nodes[cursor].parent_id
        leaves = set(executable) - {dep for node in executable.values() for dep in node.dependency_ids}
        if len(leaves) > 1:
            raise ValueError("parallel branches require an explicit integration path")
        return self


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
    """Durable proposal; old ordered steps remain truthful legacy history."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: UUID
    target_kind: ProductionTargetKind = ProductionTargetKind.DOCUMENTATION_WORK
    objective: str = Field(min_length=1)
    desired_outcome: str = Field(min_length=1)
    ordered_steps: tuple[ProductionPlanStep, ...] = Field(min_length=1)
    graph: ProductionPlanGraph | None = None
    artifact_targets: tuple[ProductionPlanArtifactTarget, ...] = ()
    change_proposal: RepositoryChangeProposal | None = None
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
        target_forms = sum(
            (
                bool(self.artifact_targets),
                self.change_proposal is not None,
                self.change_contract is not None,
            )
        )
        if target_forms > 1:
            raise ValueError("a Production Plan cannot mix target proposal/contract forms")
        if self.target_kind is ProductionTargetKind.CODE_WORK and self.artifact_targets:
            raise ValueError("CODE_WORK cannot use documentation artifact targets")
        if (
            self.target_kind is ProductionTargetKind.DOCUMENTATION_WORK
            and (self.change_proposal is not None or self.change_contract is not None)
        ):
            raise ValueError("DOCUMENTATION_WORK cannot use a Code Change Proposal or Contract")
        if self.fit_classification in {
            OnePwuFitClassification.ONE_PWU_FIT,
            OnePwuFitClassification.MULTI_PWU_FIT,
        } and not (
            self.artifact_targets
            or self.change_proposal is not None
            or self.change_contract is not None
        ):
            raise ValueError("ONE_PWU_FIT requires an admitted production target")
        if self.fit_classification is OnePwuFitClassification.MULTI_PWU_FIT:
            if self.graph is None or len(tuple(node for node in self.graph.nodes if node.kind is not ProductionNodeKind.GROUP)) < 2:
                raise ValueError("MULTI_PWU_FIT requires a valid multi-PWU graph")
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
    change_proposal: RepositoryChangeProposal | None = None
    change_contract: CodeChangeContract | None = None
    constraints: tuple[str, ...] = ()
    engineering_semantic_facts: tuple[SemanticFactReference, ...] = ()
    verification_expectation: str = Field(min_length=1)
    engineering_scope_summary: str = Field(min_length=1)
    engineering_resource_id: UUID
    repository_identity: str = Field(min_length=1)
    source_baseline_id: UUID
    source_revision: str = Field(min_length=1)
    context_references: tuple[str, ...] = ()
    target_effort_seconds: dict[str, int] = Field(default_factory=dict)
    max_pwu_duration_seconds: int = Field(default=1_800, ge=1)
    refinement_reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_sizing_evidence(self) -> "ProductionPlanningRequest":
        targets = {item.path for item in self.artifact_targets}
        if self.change_contract is not None:
            targets.update(item.path for item in self.change_contract.exact_targets)
        if self.change_proposal is not None:
            targets.update(item.path for item in self.change_proposal.required_targets)
        if any(path not in targets or seconds < 1 for path, seconds in self.target_effort_seconds.items()):
            raise ValueError("target effort must name an exact admitted path and positive seconds")
        return self


class ProductionPlanner(Protocol):
    """Replaceable planning intelligence behind a stable production contract."""

    def propose(self, request: ProductionPlanningRequest) -> ProductionPlanProposal:
        ...
