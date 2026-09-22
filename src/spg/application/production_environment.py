"""Policy-driven Production Environment lifecycle and Human delivery authority."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

from spg.domain.production_environment import (
    DeliveryAuthorizationRejected,
    DeliveryIntentV1,
    EnvironmentLifecycleState,
    EnvironmentRuntimeState,
    HumanDeliveryAction,
    HumanDeliveryDecision,
    LifecycleDecisionContext,
    LifecycleTransitionRecord,
    LifecycleTransitionRejected,
    ProductionDeliveryState,
    ProductionEnvironmentV1,
    PreviewRuntimeStatus,
    PreviewRuntimeV1,
    ReferenceRelationship,
    ResourceKind,
    ResourceReferenceV1,
)


class LifecyclePolicy(Protocol):
    """Extension point for idle, cost, organization, and reference policies."""

    @property
    def reference(self) -> str: ...

    def authorize(
        self,
        current: EnvironmentLifecycleState,
        target: EnvironmentLifecycleState,
        context: LifecycleDecisionContext,
    ) -> tuple[bool, str]: ...


class StructuralLifecyclePolicy:
    """The lifecycle graph only; operational retention policy remains external."""

    reference = "watt:production-environment:structural-lifecycle:v1"

    _allowed = {
        EnvironmentLifecycleState.CREATED: {EnvironmentLifecycleState.INITIALIZING},
        EnvironmentLifecycleState.INITIALIZING: {
            EnvironmentLifecycleState.ACTIVE,
            EnvironmentLifecycleState.SUSPENDED,
            EnvironmentLifecycleState.ARCHIVED,
        },
        EnvironmentLifecycleState.ACTIVE: {
            EnvironmentLifecycleState.SUSPENDED,
            EnvironmentLifecycleState.ARCHIVED,
        },
        EnvironmentLifecycleState.SUSPENDED: {
            EnvironmentLifecycleState.INITIALIZING,
            EnvironmentLifecycleState.ACTIVE,
            EnvironmentLifecycleState.ARCHIVED,
        },
        EnvironmentLifecycleState.ARCHIVED: {EnvironmentLifecycleState.DESTROYED},
        EnvironmentLifecycleState.DESTROYED: set(),
    }

    def authorize(
        self,
        current: EnvironmentLifecycleState,
        target: EnvironmentLifecycleState,
        context: LifecycleDecisionContext,
    ) -> tuple[bool, str]:
        if target not in self._allowed[current]:
            return False, f"transition {current.value} -> {target.value} is not structural"
        if target is EnvironmentLifecycleState.DESTROYED:
            if not context.cleanup_authorized:
                return False, "destruction requires an explicit cleanup authorization"
            if context.reachable_reference_count:
                return False, "referenced environment resources cannot be destroyed"
            if context.human_review_pending:
                return False, "Human review dependency prevents environment destruction"
        return True, "structural transition admitted"


class ProductionEnvironmentLifecycle:
    def __init__(self, policy: LifecyclePolicy | None = None) -> None:
        self.policy = policy or StructuralLifecyclePolicy()

    def transition(
        self,
        environment: ProductionEnvironmentV1,
        *,
        target: EnvironmentLifecycleState,
        context: LifecycleDecisionContext,
        actor_reference: str,
        reason: str,
        decided_at: datetime,
        provider_reference: str | None = None,
        artifact_references: tuple[str, ...] | None = None,
        evidence_references: tuple[str, ...] | None = None,
    ) -> tuple[ProductionEnvironmentV1, LifecycleTransitionRecord]:
        allowed, policy_reason = self.policy.authorize(
            environment.lifecycle_state,
            target,
            context,
        )
        if not allowed:
            raise LifecycleTransitionRejected(policy_reason)
        runtime_state = {
            EnvironmentLifecycleState.CREATED: EnvironmentRuntimeState.NOT_PROVISIONED,
            EnvironmentLifecycleState.INITIALIZING: EnvironmentRuntimeState.PREPARING,
            EnvironmentLifecycleState.ACTIVE: EnvironmentRuntimeState.READY,
            EnvironmentLifecycleState.SUSPENDED: EnvironmentRuntimeState.STOPPED,
            EnvironmentLifecycleState.ARCHIVED: EnvironmentRuntimeState.STOPPED,
            EnvironmentLifecycleState.DESTROYED: EnvironmentRuntimeState.STOPPED,
        }[target]
        provider = provider_reference or environment.provider_reference
        updated = environment.model_copy(
            update={
                "lifecycle_state": target,
                "runtime_state": runtime_state,
                "provider_reference": provider,
                "artifact_references": (
                    environment.artifact_references
                    if artifact_references is None
                    else artifact_references
                ),
                "evidence_references": (
                    environment.evidence_references
                    if evidence_references is None
                    else evidence_references
                ),
                "updated_at": decided_at,
                "version": environment.version + 1,
            }
        )
        # model_copy does not revalidate; reconstruct the immutable contract.
        updated = ProductionEnvironmentV1.model_validate(updated.model_dump())
        transition = LifecycleTransitionRecord(
            id=uuid4(),
            environment_id=environment.id,
            from_state=environment.lifecycle_state,
            to_state=target,
            actor_reference=actor_reference,
            reason=reason,
            policy_reference=self.policy.reference,
            decided_at=decided_at,
        )
        return updated, transition


class DeliveryAuthorizationService:
    """Advance only through explicit, attributable Human decisions."""

    def apply(
        self,
        intent: DeliveryIntentV1,
        decision: HumanDeliveryDecision,
    ) -> DeliveryIntentV1:
        if decision.delivery_intent_id != intent.id:
            raise DeliveryAuthorizationRejected("decision addresses another delivery intent")
        expected = {
            ProductionDeliveryState.READY_FOR_HUMAN_ACCEPTANCE: (
                HumanDeliveryAction.ACCEPT,
                ProductionDeliveryState.ACCEPTED,
            ),
            ProductionDeliveryState.ACCEPTED: (
                HumanDeliveryAction.AUTHORIZE_DELIVERY,
                ProductionDeliveryState.AUTHORIZED_FOR_DELIVERY,
            ),
        }.get(intent.state)
        if expected is None:
            raise DeliveryAuthorizationRejected("delivery intent is already terminal")
        expected_action, target = expected
        if decision.action is not expected_action:
            raise DeliveryAuthorizationRejected(
                f"{intent.state.value} requires Human action {expected_action.value}"
            )
        updated = intent.model_copy(
            update={
                "state": target,
                "updated_at": decision.decided_at,
                "version": intent.version + 1,
            }
        )
        return DeliveryIntentV1.model_validate(updated.model_dump())


def environment_reference(environment_id: UUID) -> str:
    return f"production-environment:{environment_id}"


def preview_runtime_from_observation(
    environment: ProductionEnvironmentV1,
    *,
    preview_id: UUID,
    preview_reference: str,
    artifact_references: tuple[str, ...],
    observation: dict,
    created_at: datetime,
    observed_at: datetime,
) -> PreviewRuntimeV1:
    """Bind the existing runtime observation to the new preview boundary."""

    raw_status = str(observation.get("status", "NOT_READY"))
    try:
        status = PreviewRuntimeStatus(raw_status)
    except ValueError:
        status = PreviewRuntimeStatus.FAILED
    endpoint = observation.get("url")
    return PreviewRuntimeV1(
        id=preview_id,
        environment_id=environment.id,
        workspace_id=environment.workspace_id,
        environment_lifecycle_state=environment.lifecycle_state,
        status=status,
        preview_reference=preview_reference,
        endpoint=endpoint if isinstance(endpoint, str) and endpoint else None,
        artifact_references=artifact_references,
        created_at=created_at,
        updated_at=observed_at,
    )


def production_resource_references(
    environment: ProductionEnvironmentV1,
    *,
    delivery_reference: str | None,
    created_at: datetime,
) -> tuple[ResourceReferenceV1, ...]:
    """Create reference edges only; cleanup eligibility remains future policy."""

    environment_ref = environment_reference(environment.id)
    workspace_ref = f"workspace:{environment.workspace_id}"
    edges = [
        ResourceReferenceV1(
            id=uuid4(),
            source_kind=ResourceKind.WORK,
            source_reference=f"work:{environment.work_id}",
            target_kind=ResourceKind.ENVIRONMENT,
            target_reference=environment_ref,
            relationship=ReferenceRelationship.BINDS,
            created_at=created_at,
        ),
        ResourceReferenceV1(
            id=uuid4(),
            source_kind=ResourceKind.ENVIRONMENT,
            source_reference=environment_ref,
            target_kind=ResourceKind.WORKSPACE,
            target_reference=workspace_ref,
            relationship=ReferenceRelationship.BINDS,
            created_at=created_at,
        ),
    ]
    edges.extend(
        ResourceReferenceV1(
            id=uuid4(),
            source_kind=ResourceKind.WORKSPACE,
            source_reference=workspace_ref,
            target_kind=ResourceKind.ARTIFACT,
            target_reference=reference,
            relationship=ReferenceRelationship.PRODUCES,
            created_at=created_at,
        )
        for reference in environment.artifact_references
    )
    edges.extend(
        ResourceReferenceV1(
            id=uuid4(),
            source_kind=ResourceKind.ENVIRONMENT,
            source_reference=environment_ref,
            target_kind=ResourceKind.EVIDENCE,
            target_reference=reference,
            relationship=ReferenceRelationship.SUPPORTS,
            created_at=created_at,
        )
        for reference in environment.evidence_references
    )
    if delivery_reference is not None:
        edges.append(
            ResourceReferenceV1(
                id=uuid4(),
                source_kind=ResourceKind.ENVIRONMENT,
                source_reference=environment_ref,
                target_kind=ResourceKind.DELIVERY,
                target_reference=delivery_reference,
                relationship=ReferenceRelationship.DELIVERS,
                created_at=created_at,
            )
        )
    return tuple(edges)
