"""SQLAlchemy Core schema for the currently admitted durable Runtime slices."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
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
    Column("repository_tree_identity", String(64), nullable=True),
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

production_snapshots.append_constraint(UniqueConstraint("id", "repository_identity", "repository_ref", name="uq_snapshot_repository"))
production_snapshots.append_constraint(ForeignKeyConstraint(
    ["source_baseline_id", "repository_identity", "repository_ref"],
    ["production_snapshots.id", "production_snapshots.repository_identity", "production_snapshots.repository_ref"],
    name="fk_snapshot_same_repository_source"))

current_trusted_baseline_pointer = Table(
    "current_trusted_baseline_pointer",
    metadata,
    Column("repository_identity", String(255), primary_key=True),
    Column("repository_ref", String(512), primary_key=True),
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
    ForeignKeyConstraint(["snapshot_id", "repository_identity", "repository_ref"],
        ["production_snapshots.id", "production_snapshots.repository_identity", "production_snapshots.repository_ref"],
        name="fk_pointer_repository_baseline"),
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
    Column("integrated_baseline_id", Uuid(as_uuid=True),
           ForeignKey("production_snapshots.id", name="fk_runs_integrated_baseline"), nullable=True),
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
    Column("graph", JSONB, nullable=True),
    Column("supersedes_plan_revision_id", Uuid(as_uuid=True),
           ForeignKey("plan_revisions.id", name="fk_plan_revision_supersedes"), nullable=True),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_plan_revisions_baseline"),
        nullable=False,
    ),
    Column("condition", String(32), nullable=False),
    Column("version", Integer, nullable=False),
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
        nullable=True,
    ),
    Column("node_id", String(128), nullable=True),
    Column("parent_baseline_ids", JSONB, nullable=True),
    Column("verified_output_baseline_id", Uuid(as_uuid=True),
           ForeignKey("production_snapshots.id", name="fk_work_units_verified_output"), nullable=True),
    Column("reconciliation_evidence", JSONB, nullable=True),
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
    UniqueConstraint("plan_revision_id", "node_id", name="uq_work_units_plan_node"),
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

materialized_execution_inputs = Table(
    "materialized_execution_inputs",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", name="fk_materialized_inputs_attempt"),
        nullable=False,
        unique=True,
    ),
    Column("generation", Integer, nullable=False),
    Column(
        "production_run_id",
        Uuid(as_uuid=True),
        ForeignKey("production_runs.id", name="fk_materialized_inputs_run"),
        nullable=False,
    ),
    Column(
        "work_unit_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", name="fk_materialized_inputs_work_unit"),
        nullable=False,
    ),
    Column(
        "plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey("plan_revisions.id", name="fk_materialized_inputs_plan"),
        nullable=False,
    ),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_materialized_inputs_baseline"),
        nullable=False,
    ),
    Column(
        "context_package_id",
        Uuid(as_uuid=True),
        ForeignKey("context_packages.id", name="fk_materialized_inputs_context"),
        nullable=False,
    ),
    Column("context_package_version", Integer, nullable=False),
    Column("context_package_content_fingerprint", String(64), nullable=False),
    Column("completion_contract_fingerprint", String(64), nullable=False),
    Column("prepared_execution_request", JSONB, nullable=False),
    Column("instruction_content", Text, nullable=False),
    Column("context_projection", JSONB, nullable=False),
    Column("input_fingerprint", String(64), nullable=False, unique=True),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    CheckConstraint("generation > 0", name="materialized_input_generation_positive"),
    CheckConstraint(
        "context_package_version > 0",
        name="materialized_input_context_version_positive",
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

completion_evaluations = Table(
    "completion_evaluations",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "production_run_id",
        Uuid(as_uuid=True),
        ForeignKey("production_runs.id", name="fk_completion_evaluations_run"),
        nullable=False,
    ),
    Column(
        "work_unit_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "production_work_units.id",
            name="fk_completion_evaluations_work_unit",
        ),
        nullable=False,
    ),
    Column(
        "plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "plan_revisions.id",
            name="fk_completion_evaluations_plan",
        ),
        nullable=False,
    ),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "production_snapshots.id",
            name="fk_completion_evaluations_baseline",
        ),
        nullable=False,
    ),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "execution_attempts.id",
            name="fk_completion_evaluations_attempt",
        ),
        nullable=False,
    ),
    Column("generation", Integer, nullable=False),
    Column("completion_contract_fingerprint", String(64), nullable=False),
    Column(
        "repository_observation_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "repository_observations.id",
            name="fk_completion_evaluations_observation",
        ),
        nullable=False,
    ),
    Column("repository_observation_fingerprint", String(64), nullable=False),
    Column("work_product_lineage", JSONB, nullable=False),
    Column("work_product_set_fingerprint", String(64), nullable=False),
    Column("basis_fingerprint", String(64), nullable=False, unique=True),
    Column("outcome", String(32), nullable=False),
    Column("obligation_results", JSONB, nullable=False),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

proposed_repository_snapshots = Table(
    "proposed_repository_snapshots",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "production_run_id",
        Uuid(as_uuid=True),
        ForeignKey("production_runs.id", name="fk_proposed_snapshots_run"),
        nullable=False,
    ),
    Column(
        "work_unit_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", name="fk_proposed_snapshots_work_unit"),
        nullable=False,
    ),
    Column(
        "plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey("plan_revisions.id", name="fk_proposed_snapshots_plan"),
        nullable=False,
    ),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_proposed_snapshots_baseline"),
        nullable=False,
    ),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", name="fk_proposed_snapshots_attempt"),
        nullable=False,
    ),
    Column("generation", Integer, nullable=False),
    Column(
        "completion_evaluation_id",
        Uuid(as_uuid=True),
        ForeignKey("completion_evaluations.id", name="fk_proposed_snapshots_completion"),
        nullable=False,
        unique=True,
    ),
    Column(
        "repository_observation_id",
        Uuid(as_uuid=True),
        ForeignKey("repository_observations.id", name="fk_proposed_snapshots_observation"),
        nullable=False,
    ),
    Column("repository_identity", String(255), nullable=False),
    Column("repository_ref", String(255), nullable=False),
    Column("authoritative_ref_revision", String(128), nullable=False),
    Column("proposed_commit_identity", String(128), nullable=False),
    Column("tree_identity", String(128), nullable=False),
    Column("basis_fingerprint", String(64), nullable=False, unique=True),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

verification_records = Table(
    "verification_records",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "production_run_id",
        Uuid(as_uuid=True),
        ForeignKey("production_runs.id", name="fk_verification_records_run"),
        nullable=False,
    ),
    Column(
        "work_unit_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", name="fk_verification_records_work_unit"),
        nullable=False,
    ),
    Column(
        "plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey("plan_revisions.id", name="fk_verification_records_plan"),
        nullable=False,
    ),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_verification_records_baseline"),
        nullable=False,
    ),
    Column(
        "completion_evaluation_id",
        Uuid(as_uuid=True),
        ForeignKey("completion_evaluations.id", name="fk_verification_records_completion"),
        nullable=False,
    ),
    Column(
        "proposed_snapshot_id",
        Uuid(as_uuid=True),
        ForeignKey("proposed_repository_snapshots.id", name="fk_verification_records_snapshot"),
        nullable=False,
    ),
    Column("proposed_commit_identity", String(128), nullable=False),
    Column("tree_identity", String(128), nullable=False),
    Column("obligation", Text, nullable=False),
    Column("obligation_fingerprint", String(64), nullable=False),
    Column("provider_binding", JSONB, nullable=False),
    Column("result", String(32), nullable=False),
    Column("evidence", JSONB, nullable=False),
    Column("basis_fingerprint", String(64), nullable=False, unique=True),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

production_admissibility_records = Table(
    "production_admissibility_records",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "production_run_id",
        Uuid(as_uuid=True),
        ForeignKey("production_runs.id", name="fk_admissibility_records_run"),
        nullable=False,
    ),
    Column(
        "work_unit_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", name="fk_admissibility_records_work_unit"),
        nullable=False,
    ),
    Column(
        "plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey("plan_revisions.id", name="fk_admissibility_records_plan"),
        nullable=False,
    ),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_admissibility_records_baseline"),
        nullable=False,
    ),
    Column(
        "completion_evaluation_id",
        Uuid(as_uuid=True),
        ForeignKey("completion_evaluations.id", name="fk_admissibility_records_completion"),
        nullable=False,
    ),
    Column(
        "proposed_snapshot_id",
        Uuid(as_uuid=True),
        ForeignKey("proposed_repository_snapshots.id", name="fk_admissibility_records_snapshot"),
        nullable=False,
    ),
    Column("required_obligations_fingerprint", String(64), nullable=False),
    Column("verification_record_ids", JSONB, nullable=False),
    Column("obligation_results", JSONB, nullable=False),
    Column("basis_fingerprint", String(64), nullable=False, unique=True),
    Column("outcome", String(32), nullable=False),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

baseline_candidates = Table(
    "baseline_candidates",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("condition", String(32), nullable=False),
    Column(
        "production_run_id",
        Uuid(as_uuid=True),
        ForeignKey("production_runs.id", name="fk_baseline_candidates_run"),
        nullable=False,
    ),
    Column(
        "plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey("plan_revisions.id", name="fk_baseline_candidates_plan"),
        nullable=False,
    ),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_baseline_candidates_baseline"),
        nullable=False,
    ),
    Column("repository_identity", String(255), nullable=False),
    Column("target_authoritative_ref", String(512), nullable=False),
    Column("expected_source_repository_revision", String(128), nullable=False),
    Column(
        "proposed_snapshot_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "proposed_repository_snapshots.id",
            name="fk_baseline_candidates_proposed_snapshot",
        ),
        nullable=False,
    ),
    Column("proposed_commit_identity", String(128), nullable=False),
    Column("proposed_tree_identity", String(128), nullable=False),
    Column("satisfied_work_unit_ids", JSONB, nullable=False),
    Column("completion_evaluation_ids", JSONB, nullable=False),
    Column("work_product_reference_ids", JSONB, nullable=False),
    Column("verification_record_ids", JSONB, nullable=False),
    Column(
        "production_admissibility_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "production_admissibility_records.id",
            name="fk_baseline_candidates_admissibility",
        ),
        nullable=False,
    ),
    Column(
        "production_admissibility_basis_fingerprint",
        String(64),
        nullable=False,
    ),
    Column("fingerprint", String(64), nullable=False, unique=True),
    Column(
        "sealed_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    CheckConstraint("condition = 'SEALED'", name="baseline_candidate_is_sealed"),
)

human_authorizations = Table(
    "human_authorizations",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("authority_identity", String(255), nullable=False),
    Column(
        "candidate_id",
        Uuid(as_uuid=True),
        ForeignKey("baseline_candidates.id", name="fk_human_authorizations_candidate"),
        nullable=False,
    ),
    Column("candidate_fingerprint", String(64), nullable=False),
    Column("authorization_scope", JSONB, nullable=False),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey("production_snapshots.id", name="fk_human_authorizations_baseline"),
        nullable=False,
    ),
    Column("repository_identity", String(255), nullable=False),
    Column("target_authoritative_ref", String(512), nullable=False),
    Column("expected_source_repository_revision", String(128), nullable=False),
    Column("proposed_repository_revision", String(128), nullable=False),
    Column("rationale", Text, nullable=True),
    Column(
        "governance_record_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "governance_records.id",
            name="fk_human_authorizations_governance",
        ),
        nullable=False,
        unique=True,
    ),
    Column("basis_fingerprint", String(64), nullable=False, unique=True),
    Column(
        "authorized_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

repository_integration_effects = Table(
    "repository_integration_effects",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("version", Integer, nullable=False),
    Column("effect_type", String(64), nullable=False),
    Column("state", String(32), nullable=False),
    Column(
        "candidate_id",
        Uuid(as_uuid=True),
        ForeignKey("baseline_candidates.id", name="fk_repository_effects_candidate"),
        nullable=False,
    ),
    Column("candidate_fingerprint", String(64), nullable=False),
    Column(
        "human_authorization_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "human_authorizations.id",
            name="fk_repository_effects_authorization",
        ),
        nullable=False,
    ),
    Column("repository_identity", String(255), nullable=False),
    Column("target_authoritative_ref", String(512), nullable=False),
    Column("expected_source_repository_revision", String(128), nullable=False),
    Column("proposed_repository_revision", String(128), nullable=False),
    Column("proposed_tree_identity", String(128), nullable=False),
    Column("operation_fingerprint", String(64), nullable=False, unique=True),
    Column(
        "prepared_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Column("observed_repository_revision", String(128), nullable=True),
    Column("observed_at", DateTime(timezone=True), nullable=True),
    Column("converged_at", DateTime(timezone=True), nullable=True),
    CheckConstraint(
        "effect_type = 'REPOSITORY_REF_ADVANCE'",
        name="repository_effect_is_ref_advance",
    ),
    CheckConstraint(
        "state IN ('PREPARED', 'CONVERGED')",
        name="repository_effect_state_is_narrow",
    ),
    CheckConstraint(
        "(state = 'PREPARED' AND converged_at IS NULL) OR "
        "(state = 'CONVERGED' AND converged_at IS NOT NULL "
        "AND observed_repository_revision = proposed_repository_revision)",
        name="repository_effect_convergence_is_observed",
    ),
)

runtime_commits = Table(
    "runtime_commits",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "candidate_id",
        Uuid(as_uuid=True),
        ForeignKey("baseline_candidates.id", name="fk_runtime_commits_candidate"),
        nullable=False,
        unique=True,
    ),
    Column("candidate_fingerprint", String(64), nullable=False),
    Column(
        "human_authorization_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "human_authorizations.id",
            name="fk_runtime_commits_authorization",
        ),
        nullable=False,
    ),
    Column(
        "repository_integration_effect_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "repository_integration_effects.id",
            name="fk_runtime_commits_integration_effect",
        ),
        nullable=False,
        unique=True,
    ),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "production_snapshots.id",
            name="fk_runtime_commits_source_baseline",
        ),
        nullable=False,
    ),
    Column(
        "new_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "production_snapshots.id",
            name="fk_runtime_commits_new_baseline",
        ),
        nullable=False,
        unique=True,
    ),
    Column(
        "production_run_id",
        Uuid(as_uuid=True),
        ForeignKey("production_runs.id", name="fk_runtime_commits_run"),
        nullable=False,
    ),
    Column(
        "plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey("plan_revisions.id", name="fk_runtime_commits_plan"),
        nullable=False,
    ),
    Column("repository_identity", String(255), nullable=False),
    Column("target_authoritative_ref", String(512), nullable=False),
    Column("expected_source_repository_revision", String(128), nullable=False),
    Column("repository_revision", String(128), nullable=False),
    Column("repository_tree_identity", String(128), nullable=False),
    Column("satisfied_work_unit_ids", JSONB, nullable=False),
    Column("completion_evaluation_ids", JSONB, nullable=False),
    Column("verification_record_ids", JSONB, nullable=False),
    Column(
        "production_admissibility_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "production_admissibility_records.id",
            name="fk_runtime_commits_admissibility",
        ),
        nullable=False,
    ),
    Column(
        "production_admissibility_basis_fingerprint",
        String(64),
        nullable=False,
    ),
    Column("commit_fingerprint", String(64), nullable=False, unique=True),
    Column(
        "committed_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

recovery_assessments = Table(
    "recovery_assessments",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("subject_type", String(64), nullable=False),
    Column("subject_identity", String(255), nullable=False),
    Column("governed_basis", JSONB, nullable=False),
    Column("observed_facts", JSONB, nullable=False),
    Column("differences", JSONB, nullable=False),
    Column("classification", String(32), nullable=False),
    Column("guidance", String(64), nullable=False),
    Column("subject_is_current", SmallInteger, nullable=False),
    Column("safely_recoverable", SmallInteger, nullable=False),
    Column("requires_human_attention", SmallInteger, nullable=False),
    Column("recovery_barrier", SmallInteger, nullable=False),
    Column("basis_fingerprint", String(64), nullable=False, unique=True),
    Column(
        "assessed_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    CheckConstraint(
        "subject_type IN ('ATTEMPT', 'REPOSITORY_INTEGRATION')",
        name="recovery_assessment_subject_is_narrow",
    ),
    CheckConstraint(
        "classification IN "
        "('COHERENT', 'RECOVERABLE', 'UNKNOWN', 'DIVERGED', 'STALE', 'BLOCKED')",
        name="recovery_assessment_classification_is_known",
    ),
    CheckConstraint(
        "subject_is_current IN (0, 1) AND safely_recoverable IN (0, 1) "
        "AND requires_human_attention IN (0, 1) "
        "AND recovery_barrier IN (0, 1)",
        name="recovery_assessment_flags_are_boolean",
    ),
)

recovery_action_records = Table(
    "recovery_action_records",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "recovery_assessment_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "recovery_assessments.id",
            name="fk_recovery_actions_assessment",
        ),
        nullable=False,
    ),
    Column("assessment_basis_fingerprint", String(64), nullable=False),
    Column("action_type", String(64), nullable=False),
    Column("subject_type", String(64), nullable=False),
    Column("subject_identity", String(255), nullable=False),
    Column(
        "integration_effect_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "repository_integration_effects.id",
            name="fk_recovery_actions_effect",
        ),
        nullable=True,
    ),
    Column(
        "candidate_id",
        Uuid(as_uuid=True),
        ForeignKey("baseline_candidates.id", name="fk_recovery_actions_candidate"),
        nullable=True,
    ),
    Column(
        "runtime_commit_id",
        Uuid(as_uuid=True),
        ForeignKey("runtime_commits.id", name="fk_recovery_actions_runtime_commit"),
        nullable=True,
    ),
    Column(
        "old_attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", name="fk_recovery_actions_old_attempt"),
        nullable=True,
    ),
    Column(
        "new_attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", name="fk_recovery_actions_new_attempt"),
        nullable=True,
    ),
    Column("old_generation", Integer, nullable=True),
    Column("new_generation", Integer, nullable=True),
    Column("workspace_identity", String(255), nullable=True),
    Column(
        "repository_observation_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "repository_observations.id",
            name="fk_recovery_actions_observation",
        ),
        nullable=True,
    ),
    Column(
        "completion_evaluation_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "completion_evaluations.id",
            name="fk_recovery_actions_completion",
        ),
        nullable=True,
    ),
    Column("action_basis_fingerprint", String(64), nullable=False, unique=True),
    Column("outcome", String(32), nullable=False),
    Column("observed_repository_revision", String(128), nullable=True),
    Column("observed_tree_identity", String(128), nullable=True),
    Column(
        "resolved_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    CheckConstraint(
        "action_type IN ('RECORD_EXTERNAL_CONVERGENCE', 'RETRY_RUNTIME_COMMIT', "
        "'REOBSERVE_ATTEMPT_WORK', 'RETRY_WITH_NEW_ATTEMPT', "
        "'RESUME_EXISTING_ATTEMPT')",
        name="recovery_action_type_is_narrow",
    ),
    CheckConstraint(
        "subject_type IN ('REPOSITORY_INTEGRATION', 'ATTEMPT')",
        name="recovery_action_subject_is_narrow",
    ),
    CheckConstraint(
        "outcome IN ('APPLIED', 'NO_ACTION', 'SALVAGED', 'INCOMPLETE', "
        "'RETRY_CREATED', 'UNSUPPORTED_DEFERRED')",
        name="recovery_action_outcome_is_known",
    ),
    CheckConstraint(
        "(subject_type = 'REPOSITORY_INTEGRATION' "
        "AND integration_effect_id IS NOT NULL AND candidate_id IS NOT NULL "
        "AND old_attempt_id IS NULL) OR "
        "(subject_type = 'ATTEMPT' AND old_attempt_id IS NOT NULL "
        "AND integration_effect_id IS NULL AND candidate_id IS NULL)",
        name="recovery_action_subject_binding_is_exact",
    ),
    UniqueConstraint(
        "recovery_assessment_id",
        "action_type",
        name="uq_recovery_action_assessment_type",
    ),
)


maintenance_recovery_admissions = Table(
    "maintenance_recovery_admissions",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("operation_fingerprint", String(64), nullable=False, unique=True),
    Column(
        "old_trusted_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "production_snapshots.id",
            name="fk_maintenance_recovery_old_baseline",
        ),
        nullable=False,
    ),
    Column(
        "new_trusted_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "production_snapshots.id",
            name="fk_maintenance_recovery_new_baseline",
        ),
        nullable=False,
        unique=True,
    ),
    Column("expected_pointer_version", Integer, nullable=False),
    Column("repository_identity", String(255), nullable=False),
    Column("authoritative_ref", String(512), nullable=False),
    Column("target_commit", String(128), nullable=False),
    Column("target_tree", String(128), nullable=False),
    Column("maintenance_purpose", Text, nullable=False),
    Column("approved_changed_paths", JSONB, nullable=False),
    Column("verification_evidence", JSONB, nullable=False),
    Column("maintenance_evidence_fingerprint", String(64), nullable=False),
    Column("authority", JSONB, nullable=False),
    Column("maintenance_authority_fingerprint", String(64), nullable=False),
    Column(
        "governance_record_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "governance_records.id",
            name="fk_maintenance_recovery_governance",
        ),
        nullable=False,
        unique=True,
    ),
    Column(
        "recovery_assessment_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "recovery_assessments.id",
            name="fk_maintenance_recovery_assessment",
        ),
        nullable=False,
        unique=True,
    ),
    Column("recovery_assessment_fingerprint", String(64), nullable=False),
    Column(
        "old_run_id",
        Uuid(as_uuid=True),
        ForeignKey("production_runs.id", name="fk_maintenance_recovery_old_run"),
        nullable=False,
        unique=True,
    ),
    Column(
        "old_plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "plan_revisions.id",
            name="fk_maintenance_recovery_old_plan",
        ),
        nullable=False,
        unique=True,
    ),
    Column(
        "old_work_unit_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "production_work_units.id",
            name="fk_maintenance_recovery_old_work_unit",
        ),
        nullable=False,
        unique=True,
    ),
    Column(
        "old_attempt_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "execution_attempts.id",
            name="fk_maintenance_recovery_old_attempt",
        ),
        nullable=False,
        unique=True,
    ),
    Column(
        "new_run_id",
        Uuid(as_uuid=True),
        ForeignKey("production_runs.id", name="fk_maintenance_recovery_new_run"),
        nullable=False,
        unique=True,
    ),
    Column(
        "new_plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "plan_revisions.id",
            name="fk_maintenance_recovery_new_plan",
        ),
        nullable=False,
        unique=True,
    ),
    Column(
        "new_work_unit_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "production_work_units.id",
            name="fk_maintenance_recovery_new_work_unit",
        ),
        nullable=False,
        unique=True,
    ),
    Column("governance_contract_snapshot_identity", String(255), nullable=False),
    Column("governance_contract_snapshot_fingerprint", String(64), nullable=False),
    Column("external_intent_ref", String(255), nullable=False),
    Column("outcome", String(32), nullable=False),
    Column(
        "admitted_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    CheckConstraint(
        "expected_pointer_version >= 0",
        name="maintenance_recovery_pointer_version_nonnegative",
    ),
    CheckConstraint(
        "outcome = 'APPLIED'",
        name="maintenance_recovery_outcome_is_applied",
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
    materialized_execution_inputs,
    attempt_preparations,
    execution_dispatches,
    provider_execution_reports,
    repository_observations,
    work_product_references,
    completion_evaluations,
    proposed_repository_snapshots,
    verification_records,
    production_admissibility_records,
    baseline_candidates,
    human_authorizations,
    repository_integration_effects,
    runtime_commits,
    recovery_assessments,
    recovery_action_records,
    maintenance_recovery_admissions,
)
