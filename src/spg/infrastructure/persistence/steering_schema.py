"""Normalized persistence for long-lived Steering Plan truth."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from spg.infrastructure.persistence.metadata import metadata


steering_plans = Table(
    "steering_plans",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "work_id",
        Uuid(as_uuid=True),
        ForeignKey("product_works.id", name="fk_steering_plans_work"),
        nullable=False,
        unique=True,
    ),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


steering_plan_revisions = Table(
    "steering_plan_revisions",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "steering_plan_id",
        Uuid(as_uuid=True),
        ForeignKey("steering_plans.id", name="fk_steering_plan_revisions_plan"),
        nullable=False,
    ),
    Column(
        "work_id",
        Uuid(as_uuid=True),
        ForeignKey("product_works.id", name="fk_steering_plan_revisions_work"),
        nullable=False,
    ),
    Column("revision_number", Integer, nullable=False),
    Column("condition", String(32), nullable=False),
    Column(
        "supersedes_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "steering_plan_revisions.id",
            name="fk_steering_plan_revisions_supersedes",
        ),
        nullable=True,
        unique=True,
    ),
    Column("rationale", Text, nullable=False),
    Column("reality_refs", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint(
        "steering_plan_id",
        "revision_number",
        name="uq_steering_plan_revisions_plan_revision",
    ),
    CheckConstraint(
        "revision_number >= 1",
        name="ck_steering_plan_revisions_revision_number_positive",
    ),
    CheckConstraint(
        "condition IN ('ACTIVE', 'SUPERSEDED')",
        name="ck_steering_plan_revisions_revision_condition_known",
    ),
)

Index(
    "uq_steering_plan_revisions_one_active",
    steering_plan_revisions.c.steering_plan_id,
    unique=True,
    postgresql_where=text("condition = 'ACTIVE'"),
)


steering_steps = Table(
    "steering_steps",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "steering_plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "steering_plan_revisions.id",
            name="fk_steering_steps_revision",
        ),
        nullable=False,
    ),
    Column("type", String(32), nullable=False),
    Column("objective", Text, nullable=False),
    Column("completion_condition", Text, nullable=False),
    Column("position", Integer, nullable=False),
    Column("state", String(32), nullable=False),
    Column(
        "elaborates_step_id",
        Uuid(as_uuid=True),
        ForeignKey("steering_steps.id", name="fk_steering_steps_elaborates"),
        nullable=True,
    ),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "position >= 1",
        name="ck_steering_steps_step_position_positive",
    ),
    CheckConstraint(
        "type IN ('REFINE', 'HUMAN_DECISION', 'DESIGN', 'PRODUCE', "
        "'VERIFY_ACCEPT', 'COMPLETE')",
        name="ck_steering_steps_step_type_known",
    ),
    CheckConstraint(
        "state IN ('KNOWN', 'CURRENT', 'CLOSED', 'SUPERSEDED')",
        name="ck_steering_steps_step_state_known",
    ),
)

Index(
    "uq_steering_steps_one_current_per_revision",
    steering_steps.c.steering_plan_revision_id,
    unique=True,
    postgresql_where=text("state = 'CURRENT'"),
)
Index(
    "uq_steering_steps_active_position",
    steering_steps.c.steering_plan_revision_id,
    steering_steps.c.position,
    unique=True,
    postgresql_where=text("state <> 'SUPERSEDED'"),
)


steering_decisions = Table(
    "steering_decisions",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "steering_plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "steering_plan_revisions.id",
            name="fk_steering_decisions_revision",
        ),
        nullable=False,
    ),
    Column(
        "current_step_id",
        Uuid(as_uuid=True),
        ForeignKey("steering_steps.id", name="fk_steering_decisions_current_step"),
        nullable=False,
    ),
    Column("next_step_type", String(32), nullable=False),
    Column("objective", Text, nullable=False),
    Column("reason", Text, nullable=False),
    Column("reality_refs", JSONB, nullable=False),
    Column("human_required", Boolean, nullable=False),
    Column("completion_condition", Text, nullable=False),
    Column("steering_outcome", String(32), nullable=False),
    Column("basis_fingerprint", String(64), nullable=False, unique=True),
    Column("reasoning_provider_identity", String(255), nullable=True),
    Column("attention_reason", String(64), nullable=True),
    Column("recommendation", Text, nullable=True),
    Column("alternatives", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("trade_offs", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("expected_impact", Text, nullable=True),
    Column("authority_assessment", String(32), nullable=True),
    Column("proposed_engineering_scope_fingerprint", String(64), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "next_step_type IN ('REFINE', 'HUMAN_DECISION', 'DESIGN', 'PRODUCE', "
        "'VERIFY_ACCEPT', 'COMPLETE')",
        name="ck_steering_decisions_decision_step_type_known",
    ),
    CheckConstraint(
        "steering_outcome IN ('AUTO_CONTINUE', 'HUMAN_ATTENTION', 'COMPLETE')",
        name="ck_steering_decisions_decision_outcome_known",
    ),
    CheckConstraint(
        "(steering_outcome = 'HUMAN_ATTENTION' AND human_required) OR "
        "(steering_outcome <> 'HUMAN_ATTENTION' AND NOT human_required)",
        name="ck_steering_decisions_human_outcome_consistent",
    ),
    CheckConstraint(
        "(steering_outcome = 'COMPLETE' AND next_step_type = 'COMPLETE') OR "
        "(steering_outcome <> 'COMPLETE' AND next_step_type <> 'COMPLETE')",
        name="ck_steering_decisions_complete_outcome_consistent",
    ),
    CheckConstraint(
        "attention_reason IS NULL OR attention_reason IN "
        "('MOTIVE_OR_OUTCOME_AMBIGUITY', "
        "'MAJOR_PRODUCT_OR_ARCHITECTURE_DECISION', "
        "'SCOPE_OR_AUTHORITY_EXPANSION', "
        "'MATERIAL_RISK_OR_COST_DECISION', "
        "'PRODUCT_ACCEPTANCE_REQUIRED')",
        name="ck_steering_decisions_attention_reason_known",
    ),
    CheckConstraint(
        "authority_assessment IS NULL OR authority_assessment IN "
        "('WITHIN_AUTHORITY', 'UNCERTAIN', 'EXPANDS_AUTHORITY')",
        name="ck_steering_decisions_authority_assessment_known",
    ),
)


steering_history_events = Table(
    "steering_history_events",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "steering_plan_id",
        Uuid(as_uuid=True),
        ForeignKey("steering_plans.id", name="fk_steering_history_plan"),
        nullable=False,
    ),
    Column(
        "steering_plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "steering_plan_revisions.id",
            name="fk_steering_history_revision",
        ),
        nullable=False,
    ),
    Column("event_type", String(32), nullable=False),
    Column(
        "from_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "steering_plan_revisions.id",
            name="fk_steering_history_from_revision",
        ),
        nullable=True,
    ),
    Column(
        "to_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "steering_plan_revisions.id",
            name="fk_steering_history_to_revision",
        ),
        nullable=True,
    ),
    Column(
        "from_step_id",
        Uuid(as_uuid=True),
        ForeignKey("steering_steps.id", name="fk_steering_history_from_step"),
        nullable=True,
    ),
    Column(
        "to_step_id",
        Uuid(as_uuid=True),
        ForeignKey("steering_steps.id", name="fk_steering_history_to_step"),
        nullable=True,
    ),
    Column(
        "steering_decision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "steering_decisions.id",
            name="fk_steering_history_decision",
        ),
        nullable=True,
    ),
    Column("related_step_ids", JSONB, nullable=False),
    Column("rationale", Text, nullable=False),
    Column("reality_refs", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "event_type IN ('STEP_TRANSITION', 'STEP_ELABORATION', 'PLAN_REVISION')",
        name="ck_steering_history_events_event_type_known",
    ),
)


steering_tables = (
    steering_plans,
    steering_plan_revisions,
    steering_steps,
    steering_decisions,
    steering_history_events,
)
