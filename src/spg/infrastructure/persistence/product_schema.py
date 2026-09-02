"""SQLAlchemy Core schema for MVP goal-centric product-owned facts."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
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
    Column("raw_user_requirement", Text, nullable=False),
    Column("refined_title", String(255), nullable=True),
    Column("desired_outcome", Text, nullable=True),
    Column("constraints", JSONB, nullable=False),
    Column("tags", JSONB, nullable=False),
    Column("condition", String(32), nullable=False),
    Column("scope_summary", Text, nullable=True),
    Column("production_objective", Text, nullable=True),
    Column("expected_artifact_path", Text, nullable=True),
    Column("verification_expectation", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
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
        unique=True,
    ),
    Column("summary", Text, nullable=False),
    Column("fingerprint", String(64), nullable=False, unique=True),
    Column("condition", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
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

work_runtime_bindings = Table(
    "work_runtime_bindings",
    metadata,
    Column(
        "work_id",
        Uuid(as_uuid=True),
        ForeignKey("product_works.id", name="fk_work_runtime_bindings_work"),
        primary_key=True,
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
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


product_tables = (
    product_goals,
    engineering_resources,
    product_works,
    engineering_scopes,
    engineering_resource_bindings,
    work_runtime_bindings,
)
