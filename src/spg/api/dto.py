"""Explicit product HTTP DTOs; no persistence or Runtime rows cross this boundary."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from spg.domain.product import (
    AttentionAction,
    AttentionItem,
    AttentionKind,
    EngineeringScopeRecord,
    GoalProjection,
    GoalRecord,
    WorkProjection,
    WorkResultProjection,
    WorkStatus,
)


class ApiDto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GoalCreateRequest(ApiDto):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None


class GoalResponse(ApiDto):
    goal_id: UUID
    title: str
    description: str | None
    condition: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, goal: GoalRecord) -> Self:
        return cls(
            goal_id=goal.id,
            title=goal.title,
            description=goal.description,
            condition=goal.condition.value,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        )


class ResourceBindingResponse(ApiDto):
    resource_id: UUID
    condition: str


class EngineeringScopeResponse(ApiDto):
    engineering_scope_id: UUID
    summary: str
    condition: str
    resources: tuple[ResourceBindingResponse, ...]

    @classmethod
    def from_record(cls, scope: EngineeringScopeRecord) -> Self:
        return cls(
            engineering_scope_id=scope.id,
            summary=scope.summary,
            condition=scope.condition.value,
            resources=tuple(
                ResourceBindingResponse(
                    resource_id=binding.resource_id,
                    condition=binding.condition.value,
                )
                for binding in scope.bindings
            ),
        )


class WorkResponse(ApiDto):
    work_id: UUID
    goal_id: UUID | None
    raw_user_requirement: str
    title: str | None
    desired_outcome: str | None
    constraints: tuple[str, ...]
    tags: tuple[str, ...]
    engineering_scope: EngineeringScopeResponse | None
    status: WorkStatus
    current_production_step: str
    most_recent_meaningful_event: str
    what_happens_next: str
    human_attention_required: bool
    result_summary: str | None

    @classmethod
    def from_projection(cls, work: WorkProjection) -> Self:
        return cls(
            work_id=work.work_id,
            goal_id=work.goal_id,
            raw_user_requirement=work.raw_user_requirement,
            title=work.title,
            desired_outcome=work.desired_outcome,
            constraints=work.constraints,
            tags=work.tags,
            engineering_scope=(
                None
                if work.engineering_scope is None
                else EngineeringScopeResponse.from_record(work.engineering_scope)
            ),
            status=work.status,
            current_production_step=work.current_production_step,
            most_recent_meaningful_event=work.most_recent_meaningful_event,
            what_happens_next=work.what_happens_next,
            human_attention_required=work.human_attention_required,
            result_summary=work.result_summary,
        )


class GoalSummaryResponse(ApiDto):
    goal: GoalResponse
    work_count: int
    works_by_status: dict[str, int]
    recent_works: tuple[WorkResponse, ...]
    needs_attention_count: int

    @classmethod
    def from_projection(cls, projection: GoalProjection) -> Self:
        return cls(
            goal=GoalResponse.from_record(projection.goal),
            work_count=projection.work_count,
            works_by_status={
                status.value: count
                for status, count in projection.works_by_status.items()
            },
            recent_works=tuple(
                WorkResponse.from_projection(work)
                for work in projection.recent_works
            ),
            needs_attention_count=projection.needs_attention_count,
        )


class WorkSubmitRequest(ApiDto):
    requirement: str = Field(min_length=1)
    goal_id: UUID | None = None
    tags: tuple[str, ...] = ()


class WorkRefineRequest(ApiDto):
    title: str | None = None
    desired_outcome: str | None = None
    constraints: tuple[str, ...] = ()
    scope_summary: str | None = None
    production_objective: str | None = None
    expected_artifact_path: str | None = None
    verification_expectation: str | None = None


class HumanDecisionRequest(ApiDto):
    authority_identity: str = Field(min_length=1)
    rationale: str | None = None


class AttentionResolveRequest(ApiDto):
    action: AttentionAction
    authority_identity: str = Field(min_length=1)
    rationale: str | None = None


class AttentionResponse(ApiDto):
    attention_id: UUID
    work_id: UUID
    kind: AttentionKind
    decision: str
    reason: str
    available_actions: tuple[AttentionAction, ...]
    recommended_action: AttentionAction | None
    governed_subject_ref: str

    @classmethod
    def from_projection(cls, attention: AttentionItem) -> Self:
        return cls(
            attention_id=attention.id,
            work_id=attention.work_id,
            kind=attention.kind,
            decision=attention.decision,
            reason=attention.reason,
            available_actions=attention.available_actions,
            recommended_action=attention.recommended_action,
            governed_subject_ref=attention.governed_subject_ref,
        )


class WorkResultResponse(ApiDto):
    work_id: UUID
    status: WorkStatus
    desired_outcome: str | None
    produced_artifacts: tuple[str, ...]
    verification_summary: tuple[str, ...]
    repository_state: str | None
    trusted_result: bool
    remaining_blocker_or_risk: str | None
    human_attention_required: bool

    @classmethod
    def from_projection(cls, result: WorkResultProjection) -> Self:
        return cls(**result.model_dump())


class HealthResponse(ApiDto):
    service: str
    database: str
    application_initialized: bool


class ErrorResponse(ApiDto):
    code: str
    message: str
