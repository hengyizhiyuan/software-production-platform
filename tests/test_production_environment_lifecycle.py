from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from spg.application.production_environment import (
    DeliveryAuthorizationService,
    ProductionEnvironmentLifecycle,
)
from spg.domain.production_environment import (
    DeliveryAuthorizationRejected,
    DeliveryIntentKind,
    DeliveryIntentV1,
    EnvironmentLifecycleState,
    EnvironmentRuntimeState,
    HumanDeliveryAction,
    HumanDeliveryDecision,
    LifecycleDecisionContext,
    LifecycleTransitionRejected,
    ProductionDeliveryState,
    ProductionEnvironmentV1,
)


def environment():
    now = datetime.now(UTC)
    return ProductionEnvironmentV1(
        id=uuid4(),
        work_id=uuid4(),
        workspace_id=uuid4(),
        lifecycle_state=EnvironmentLifecycleState.CREATED,
        runtime_state=EnvironmentRuntimeState.NOT_PROVISIONED,
        created_at=now,
        updated_at=now,
    )


def context(**updates):
    payload = {
        "work_state": "RUNNING",
        "human_review_pending": False,
        "reachable_reference_count": 0,
        "cleanup_authorized": False,
    }
    payload.update(updates)
    return LifecycleDecisionContext(**payload)


def transition(lifecycle, current, target, at, **kwargs):
    return lifecycle.transition(
        current,
        target=target,
        context=context(**kwargs),
        actor_reference="system:production-environment",
        reason=f"move to {target.value}",
        decided_at=at,
        provider_reference="container-v1:1",
    )[0]


def test_lifecycle_supports_activation_suspend_resume_archive_and_safe_destroy():
    lifecycle = ProductionEnvironmentLifecycle()
    value = environment()
    at = value.created_at
    value = transition(lifecycle, value, EnvironmentLifecycleState.INITIALIZING, at)
    value = transition(lifecycle, value, EnvironmentLifecycleState.ACTIVE, at)
    value = transition(lifecycle, value, EnvironmentLifecycleState.SUSPENDED, at)
    value = transition(lifecycle, value, EnvironmentLifecycleState.ACTIVE, at)
    value = transition(lifecycle, value, EnvironmentLifecycleState.ARCHIVED, at)
    value = transition(
        lifecycle,
        value,
        EnvironmentLifecycleState.DESTROYED,
        at,
        cleanup_authorized=True,
    )

    assert value.lifecycle_state is EnvironmentLifecycleState.DESTROYED
    assert value.version == 7


def test_lifecycle_rejects_skips_and_referenced_cleanup():
    lifecycle = ProductionEnvironmentLifecycle()
    value = environment()
    with pytest.raises(LifecycleTransitionRejected, match="not structural"):
        transition(lifecycle, value, EnvironmentLifecycleState.ACTIVE, value.created_at)
    value = transition(
        lifecycle,
        value,
        EnvironmentLifecycleState.INITIALIZING,
        value.created_at,
    )
    value = transition(
        lifecycle,
        value,
        EnvironmentLifecycleState.ARCHIVED,
        value.created_at,
    )
    with pytest.raises(LifecycleTransitionRejected, match="referenced"):
        transition(
            lifecycle,
            value,
            EnvironmentLifecycleState.DESTROYED,
            value.created_at,
            cleanup_authorized=True,
            reachable_reference_count=1,
        )


def test_delivery_requires_separate_human_acceptance_and_authorization():
    now = datetime.now(UTC)
    intent = DeliveryIntentV1(
        id=uuid4(),
        work_id=uuid4(),
        environment_id=uuid4(),
        repository_identity="repo:frontend",
        kinds=(
            DeliveryIntentKind.BRANCH_CREATION,
            DeliveryIntentKind.COMMIT,
            DeliveryIntentKind.PULL_REQUEST_PREPARATION,
        ),
        target_branch="feature/environment",
        commit="a" * 40,
        created_at=now,
        updated_at=now,
    )
    service = DeliveryAuthorizationService()
    with pytest.raises(DeliveryAuthorizationRejected, match="requires Human action ACCEPT"):
        service.apply(
            intent,
            HumanDeliveryDecision(
                id=uuid4(),
                delivery_intent_id=intent.id,
                action=HumanDeliveryAction.AUTHORIZE_DELIVERY,
                authority_identity="human:operator",
                rationale="ship it",
                decided_at=now,
            ),
        )
    accepted = service.apply(
        intent,
        HumanDeliveryDecision(
            id=uuid4(),
            delivery_intent_id=intent.id,
            action=HumanDeliveryAction.ACCEPT,
            authority_identity="human:operator",
            rationale="preview accepted",
            decided_at=now + timedelta(seconds=1),
        ),
    )
    authorized = service.apply(
        accepted,
        HumanDeliveryDecision(
            id=uuid4(),
            delivery_intent_id=intent.id,
            action=HumanDeliveryAction.AUTHORIZE_DELIVERY,
            authority_identity="human:operator",
            rationale="delivery authorized",
            decided_at=now + timedelta(seconds=2),
        ),
    )

    assert accepted.state is ProductionDeliveryState.ACCEPTED
    assert authorized.state is ProductionDeliveryState.AUTHORIZED_FOR_DELIVERY
