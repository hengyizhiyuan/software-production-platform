"""SQLAlchemy Core schema for the currently admitted durable Runtime slices."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
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


production_snapshots = Table(
    "production_snapshots",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("condition", String(32), nullable=False),
    Column("repository_identity", String(255), nullable=False),
    Column("repository_ref", String(512), nullable=False),
    Column("repository_revision", String(64), nullable=False),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_snapshots_source_baseline"),
        nullable=True,
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

current_trusted_baseline_pointer = Table(
    "current_trusted_baseline_pointer",
    metadata,
    Column("singleton_id", SmallInteger, primary_key=True),
    Column(
        "snapshot_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_baseline_pointer_snapshot"),
        nullable=False,
    ),
    Column("version", Integer, nullable=False),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    CheckConstraint("singleton_id = 1", name="singleton_id_is_one"),
)

production_runs = Table(
    "production_runs",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("intent_ref", String(255), nullable=False),
    Column("goal", Text, nullable=False),
    Column("production_horizon", String(64), nullable=False),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_runs_source_baseline"),
        nullable=False,
    ),
    Column(
        "current_plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "plan_revisions.id",
            name="fk_runs_current_plan_revision",
            use_alter=True,
        ),
        nullable=True,
    ),
    Column("condition", String(32), nullable=False),
    Column("version", Integer, nullable=False),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

plan_revisions = Table(
    "plan_revisions",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "production_run_id",
        Uuid(as_uuid=True),
        ForeignKey("production_runs.id", name="fk_plan_revisions_run"),
        nullable=False,
    ),
    Column("revision_number", Integer, nullable=False),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_plan_revisions_baseline"),
        nullable=False,
    ),
    Column("condition", String(32), nullable=False),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    UniqueConstraint(
        "production_run_id",
        "revision_number",
        name="uq_plan_revisions_run_revision",
    ),
)

Index(
    "uq_plan_revisions_one_active_per_run",
    plan_revisions.c.production_run_id,
    unique=True,
    postgresql_where=text("condition = 'ACTIVE'"),
)

production_work_units = Table(
    "production_work_units",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "production_run_id",
        Uuid(as_uuid=True),
        ForeignKey("production_runs.id", name="fk_work_units_run"),
        nullable=False,
    ),
    Column(
        "plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey("plan_revisions.id", name="fk_work_units_plan_revision"),
        nullable=False,
    ),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_work_units_baseline"),
        nullable=False,
    ),
    Column("objective", Text, nullable=False),
    Column("completion_contract", JSONB, nullable=False),
    Column("condition", String(32), nullable=False),
    Column("version", Integer, nullable=False),
    Column("current_execution_generation", Integer, nullable=False),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

execution_attempts = Table(
    "execution_attempts",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "work_unit_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", name="fk_attempts_work_unit"),
        nullable=False,
    ),
    Column("generation", Integer, nullable=False),
    Column(
        "plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey("plan_revisions.id", name="fk_attempts_plan_revision"),
        nullable=False,
    ),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_attempts_baseline"),
        nullable=False,
    ),
    Column("context_ref", String(255), nullable=True),
    Column("provider_ref", String(255), nullable=True),
    Column("workspace_ref", String(1024), nullable=True),
    Column("condition", String(32), nullable=False),
    Column(
        "retry_of",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", name="fk_attempts_retry_of"),
        nullable=True,
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    UniqueConstraint(
        "work_unit_id",
        "generation",
        name="uq_execution_attempts_work_unit_generation",
    ),
)

governance_records = Table(
    "governance_records",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("decision_type", String(64), nullable=False),
    Column("authority_identity", String(255), nullable=False),
    Column("subject_type", String(64), nullable=False),
    Column("subject_identity", String(255), nullable=False),
    Column("scope", JSONB, nullable=False),
    Column("rationale", Text, nullable=True),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

transition_history = Table(
    "transition_history",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("entity_type", String(64), nullable=False),
    Column("entity_identity", String(255), nullable=False),
    Column("from_condition", String(64), nullable=True),
    Column("to_condition", String(64), nullable=False),
    Column("reason", String(128), nullable=False),
    Column("actor_identity", String(255), nullable=False),
    Column("correlation_identity", String(255), nullable=True),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

context_packages = Table(
    "context_packages",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("version", Integer, nullable=False),
    Column(
        "production_run_id",
        Uuid(as_uuid=True),
        ForeignKey("production_runs.id", name="fk_context_packages_run"),
        nullable=False,
    ),
    Column(
        "work_unit_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", name="fk_context_packages_work_unit"),
        nullable=False,
    ),
    Column(
        "plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey("plan_revisions.id", name="fk_context_packages_plan_revision"),
        nullable=False,
    ),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_context_packages_baseline"),
        nullable=False,
    ),
    Column("manifest", JSONB, nullable=False),
    Column("content_fingerprint", String(64), nullable=False),
    Column("completion_contract_fingerprint", String(64), nullable=False),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    UniqueConstraint(
        "work_unit_id",
        "version",
        name="uq_context_packages_work_unit_version",
    ),
)

attempt_preparations = Table(
    "attempt_preparations",
    metadata,
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", name="fk_attempt_preparations_attempt"),
        primary_key=True,
    ),
    Column(
        "context_package_id",
        Uuid(as_uuid=True),
        ForeignKey("context_packages.id", name="fk_attempt_preparations_context"),
        nullable=False,
    ),
    Column("executor_binding", JSONB, nullable=False),
    Column("workspace_identity", String(255), nullable=False, unique=True),
    Column("workspace_path", String(2048), nullable=False, unique=True),
    Column("repository_identity", String(255), nullable=False),
    Column("repository_path", String(2048), nullable=False),
    Column("source_revision", String(64), nullable=False),
    Column(
        "prepared_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

execution_dispatches = Table(
    "execution_dispatches",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", name="fk_execution_dispatches_attempt"),
        nullable=False,
    ),
    Column("generation", Integer, nullable=False),
    Column(
        "context_package_id",
        Uuid(as_uuid=True),
        ForeignKey("context_packages.id", name="fk_execution_dispatches_context"),
        nullable=False,
    ),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_execution_dispatches_baseline"),
        nullable=False,
    ),
    Column("executor_binding", JSONB, nullable=False),
    Column("workspace_identity", String(255), nullable=False),
    Column("workspace_path", String(2048), nullable=False),
    Column("repository_identity", String(255), nullable=False),
    Column("repository_path", String(2048), nullable=False),
    Column("source_revision", String(64), nullable=False),
    Column("authoritative_ref_revision", String(64), nullable=False),
    Column(
        "dispatched_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    UniqueConstraint("attempt_id", name="uq_execution_dispatches_attempt"),
)

provider_execution_reports = Table(
    "provider_execution_reports",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "dispatch_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_dispatches.id", name="fk_provider_reports_dispatch"),
        nullable=False,
        unique=True,
    ),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", name="fk_provider_reports_attempt"),
        nullable=False,
    ),
    Column("generation", Integer, nullable=False),
    Column("executor_binding", JSONB, nullable=False),
    Column("provider_reference", String(1024), nullable=False),
    Column("outcome", String(32), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=False),
    Column("metadata", JSONB, nullable=False),
    Column("summary", Text, nullable=True),
    Column(
        "recorded_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

repository_observations = Table(
    "repository_observations",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "dispatch_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_dispatches.id", name="fk_repository_observations_dispatch"),
        nullable=False,
        unique=True,
    ),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", name="fk_repository_observations_attempt"),
        nullable=False,
    ),
    Column("generation", Integer, nullable=False),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_repository_observations_baseline"),
        nullable=False,
    ),
    Column("repository_identity", String(255), nullable=False),
    Column("source_revision", String(64), nullable=False),
    Column("workspace_identity", String(255), nullable=False),
    Column("workspace_path", String(2048), nullable=False),
    Column("authoritative_ref_revision", String(64), nullable=False),
    Column("change_manifest", JSONB, nullable=False),
    Column("observation_fingerprint", String(64), nullable=False),
    Column(
        "observed_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

work_product_references = Table(
    "work_product_references",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "production_run_id",
        Uuid(as_uuid=True),
        ForeignKey("production_runs.id", name="fk_work_product_refs_run"),
        nullable=False,
    ),
    Column(
        "work_unit_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", name="fk_work_product_refs_work_unit"),
        nullable=False,
    ),
    Column(
        "plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey("plan_revisions.id", name="fk_work_product_refs_plan"),
        nullable=False,
    ),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", name="fk_work_product_refs_attempt"),
        nullable=False,
    ),
    Column("generation", Integer, nullable=False),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_work_product_refs_baseline"),
        nullable=False,
    ),
    Column(
        "repository_observation_id",
        Uuid(as_uuid=True),
        ForeignKey("repository_observations.id", name="fk_work_product_refs_observation"),
        nullable=False,
    ),
    Column("artifact_path", String(2048), nullable=False),
    Column("change_type", String(32), nullable=False),
    Column("source_fingerprint", String(128), nullable=True),
    Column("observed_fingerprint", String(128), nullable=True),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    UniqueConstraint(
        "repository_observation_id",
        "artifact_path",
        name="uq_work_product_refs_observation_path",
    ),
)


runtime_tables = (
    production_snapshots,
    current_trusted_baseline_pointer,
    production_runs,
    plan_revisions,
    production_work_units,
    execution_attempts,
    governance_records,
    transition_history,
    context_packages,
    attempt_preparations,
    execution_dispatches,
    provider_execution_reports,
    repository_observations,
    work_product_references,
)
