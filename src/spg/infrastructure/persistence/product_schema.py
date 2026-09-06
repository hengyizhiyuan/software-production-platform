"""SQLAlchemy Core schema for MVP goal-centric product-owned facts."""

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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from spg.infrastructure.persistence.metadata import metadata
from spg.infrastructure.persistence.steering_schema import steering_tables


product_goals = Table(
    "product_goals",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("title", String(255), nullable=False),
    Column("description", Text, nullable=True),
    Column("condition", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

engineering_resources = Table(
    "engineering_resources",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("kind", String(32), nullable=False),
    Column("repository_identity", String(255), nullable=False, unique=True),
    Column("location_ref", Text, nullable=False),
    Column("authoritative_ref", String(512), nullable=False),
    Column("context_references", JSONB, nullable=False),
    Column("is_default", Boolean, nullable=False, server_default=text("false")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

Index(
    "uq_engineering_resources_one_default",
    engineering_resources.c.is_default,
    unique=True,
    postgresql_where=text("is_default = true"),
)

product_works = Table(
    "product_works",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "goal_id",
        Uuid(as_uuid=True),
        ForeignKey("product_goals.id", name="fk_product_works_goal"),
        nullable=True,
    ),
    Column("work_mode", String(32), nullable=False),
    Column("raw_user_requirement", Text, nullable=False),
    Column("refined_title", String(255), nullable=True),
    Column("desired_outcome", Text, nullable=True),
    Column("constraints", JSONB, nullable=False),
    Column("tags", JSONB, nullable=False),
    Column("condition", String(32), nullable=False),
    Column("scope_summary", Text, nullable=True),
    Column("production_objective", Text, nullable=True),
    Column("expected_artifact_path", Text, nullable=True),
    Column("artifact_operation", String(16), nullable=True),
    Column("artifact_placement_rationale", Text, nullable=True),
    Column("artifact_target_confidence", String(16), nullable=True),
    Column("artifact_source_baseline_id", Uuid(as_uuid=True), nullable=True),
    Column("artifact_source_revision", String(64), nullable=True),
    Column("verification_expectation", Text, nullable=True),
    Column("code_change_proposal", JSONB, nullable=True),
    Column("production_plan_proposal", JSONB, nullable=True),
    Column(
        "current_work_reality_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "work_reality_revisions.id",
            name="fk_product_works_current_reality_revision",
            use_alter=True,
        ),
        nullable=True,
    ),
    Column(
        "current_engineering_scope_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "engineering_scopes.id",
            name="fk_product_works_current_engineering_scope",
            use_alter=True,
        ),
        nullable=True,
    ),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "work_mode IN ('IMMEDIATE_PRODUCTION', 'LONG_LIVED_STEERING')",
        name="ck_product_works_work_mode_known",
    ),
)

engineering_scopes = Table(
    "engineering_scopes",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "work_id",
        Uuid(as_uuid=True),
        ForeignKey("product_works.id", name="fk_engineering_scopes_work"),
        nullable=False,
    ),
    Column("summary", Text, nullable=False),
    Column("fingerprint", String(64), nullable=False, unique=True),
    Column("condition", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

Index(
    "ix_engineering_scopes_work_created",
    engineering_scopes.c.work_id,
    engineering_scopes.c.created_at,
)

engineering_resource_bindings = Table(
    "engineering_resource_bindings",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "engineering_scope_id",
        Uuid(as_uuid=True),
        ForeignKey("engineering_scopes.id", name="fk_resource_bindings_scope"),
        nullable=False,
    ),
    Column(
        "resource_id",
        Uuid(as_uuid=True),
        ForeignKey("engineering_resources.id", name="fk_resource_bindings_resource"),
        nullable=False,
    ),
    Column("condition", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint(
        "engineering_scope_id",
        "resource_id",
        name="uq_resource_bindings_scope_resource",
    ),
)

product_interactions = Table(
    "product_interactions",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("condition", String(32), nullable=False),
    Column(
        "current_work_id",
        Uuid(as_uuid=True),
        ForeignKey("product_works.id", name="fk_product_interactions_current_work"),
        nullable=True,
    ),
    Column("created_by", String(255), nullable=False),
    Column("updated_by", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "condition IN ('OPEN', 'ARCHIVED')",
        name="ck_product_interactions_condition_known",
    ),
)

interaction_records = Table(
    "interaction_records",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "interaction_id",
        Uuid(as_uuid=True),
        ForeignKey("product_interactions.id", name="fk_interaction_records_interaction"),
        nullable=False,
    ),
    Column("sequence", Integer, nullable=False),
    Column("actor", String(32), nullable=False),
    Column("source", String(255), nullable=False),
    Column("content", Text, nullable=False),
    Column("content_fingerprint", String(64), nullable=False),
    Column(
        "work_focus_id",
        Uuid(as_uuid=True),
        ForeignKey("product_works.id", name="fk_interaction_records_work_focus"),
        nullable=True,
    ),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint(
        "interaction_id",
        "sequence",
        name="uq_interaction_records_interaction_sequence",
    ),
    CheckConstraint(
        "actor IN ('HUMAN', 'WATT')",
        name="ck_interaction_records_actor_known",
    ),
)

interaction_assessments = Table(
    "interaction_assessments",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "interaction_id",
        Uuid(as_uuid=True),
        ForeignKey("product_interactions.id", name="fk_interaction_assessments_interaction"),
        nullable=False,
    ),
    Column("basis_fingerprint", String(64), nullable=False),
    Column("basis_last_sequence", Integer, nullable=False),
    Column("interpreted_motive", Text, nullable=True),
    Column("desired_outcome", Text, nullable=True),
    Column("candidate_context", JSONB, nullable=False),
    Column("candidate_constraints", JSONB, nullable=False),
    Column("current_requests", JSONB, nullable=False),
    Column("unresolved_material_questions", JSONB, nullable=False),
    Column("meanings", JSONB, nullable=False),
    Column("natural_response", Text, nullable=False),
    Column("readiness", JSONB, nullable=False),
    Column("provider_identity", String(255), nullable=False),
    Column("model_identity", String(255), nullable=True),
    Column("schema_version", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint(
        "interaction_id",
        "basis_fingerprint",
        name="uq_interaction_assessments_interaction_basis",
    ),
)

work_reality_revisions = Table(
    "work_reality_revisions",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "work_id",
        Uuid(as_uuid=True),
        ForeignKey("product_works.id", name="fk_work_reality_revisions_work"),
        nullable=False,
    ),
    Column("revision_number", Integer, nullable=False),
    Column(
        "previous_revision_id",
        Uuid(as_uuid=True),
        ForeignKey("work_reality_revisions.id", name="fk_work_reality_revisions_previous"),
        nullable=True,
    ),
    Column("basis_fingerprint", String(64), nullable=False),
    Column("motive", Text, nullable=False),
    Column("desired_outcome", Text, nullable=False),
    Column("context_facts", JSONB, nullable=False),
    Column("constraints", JSONB, nullable=False),
    Column("requests", JSONB, nullable=False),
    Column(
        "engineering_scope_id",
        Uuid(as_uuid=True),
        ForeignKey("engineering_scopes.id", name="fk_work_reality_revisions_scope"),
        nullable=True,
    ),
    Column("supporting_references", JSONB, nullable=False),
    Column("change_set", JSONB, nullable=False),
    Column("rationale", Text, nullable=False),
    Column("admitted_by", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint(
        "work_id",
        "revision_number",
        name="uq_work_reality_revisions_work_number",
    ),
    UniqueConstraint(
        "work_id",
        "basis_fingerprint",
        name="uq_work_reality_revisions_work_basis",
    ),
)

work_runtime_bindings = Table(
    "work_runtime_bindings",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "work_id",
        Uuid(as_uuid=True),
        ForeignKey("product_works.id", name="fk_work_runtime_bindings_work"),
        nullable=False,
    ),
    Column("cycle_number", Integer, nullable=False),
    Column(
        "steering_step_id",
        Uuid(as_uuid=True),
        ForeignKey("steering_steps.id", name="fk_work_runtime_bindings_steering_step"),
        nullable=True,
        unique=True,
    ),
    Column(
        "steering_decision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "steering_decisions.id",
            name="fk_work_runtime_bindings_steering_decision",
        ),
        nullable=True,
    ),
    Column(
        "work_reality_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "work_reality_revisions.id",
            name="fk_work_runtime_bindings_reality_revision",
        ),
        nullable=True,
    ),
    Column(
        "engineering_scope_id",
        Uuid(as_uuid=True),
        ForeignKey("engineering_scopes.id", name="fk_work_runtime_bindings_scope"),
        nullable=False,
    ),
    Column(
        "resource_id",
        Uuid(as_uuid=True),
        ForeignKey("engineering_resources.id", name="fk_work_runtime_bindings_resource"),
        nullable=False,
    ),
    Column(
        "production_run_id",
        Uuid(as_uuid=True),
        ForeignKey("production_runs.id", name="fk_work_runtime_bindings_run"),
        nullable=False,
        unique=True,
    ),
    Column(
        "plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey("plan_revisions.id", name="fk_work_runtime_bindings_plan"),
        nullable=False,
        unique=True,
    ),
    Column(
        "work_unit_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", name="fk_work_runtime_bindings_pwu"),
        nullable=False,
        unique=True,
    ),
    Column(
        "governance_record_id",
        Uuid(as_uuid=True),
        ForeignKey("governance_records.id", name="fk_work_runtime_bindings_governance"),
        nullable=False,
        unique=True,
    ),
    Column("admitted_by", String(255), nullable=False),
    Column("condition", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint(
        "work_id",
        "cycle_number",
        name="uq_work_runtime_bindings_work_cycle",
    ),
    CheckConstraint(
        "condition IN ('ADMITTED', 'TRUSTED')",
        name="ck_work_runtime_bindings_condition_known",
    ),
)

product_tables = (
    product_goals,
    engineering_resources,
    product_works,
    engineering_scopes,
    engineering_resource_bindings,
    product_interactions,
    interaction_records,
    interaction_assessments,
    work_reality_revisions,
    work_runtime_bindings,
    *steering_tables,
)
