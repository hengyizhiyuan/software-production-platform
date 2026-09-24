"""Additive PostgreSQL schema for Watt-native Executor v2 facts."""

from sqlalchemy import (
    BigInteger,
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


pwu_contract_versions = Table(
    "pwu_contract_versions",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "pwu_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("revision", Integer, nullable=False),
    Column("objective", Text, nullable=False),
    Column("contract_payload", JSONB, nullable=False),
    Column("contract_digest", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("pwu_id", "revision", name="uq_pwu_contract_versions_revision"),
    UniqueConstraint("pwu_id", "contract_digest", name="uq_pwu_contract_versions_digest"),
)

execution_source_vectors = Table(
    "execution_source_vectors",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("schema_version", Integer, nullable=False),
    Column("digest", String(64), nullable=False, unique=True),
    Column("non_repository_assets", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

execution_source_members = Table(
    "execution_source_members",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "source_vector_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_source_vectors.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("mount_id", String(255), nullable=False),
    Column("asset_id", Uuid(as_uuid=True), nullable=True),
    Column("repository_identity", String(1024), nullable=False),
    Column("source_baseline_ref", String(255), nullable=False),
    Column("source_commit_oid", String(128), nullable=False),
    Column("source_tree_oid", String(128), nullable=False),
    Column("git_object_format", String(16), nullable=False),
    Column("container_path", String(1024), nullable=False),
    Column("read_scope", JSONB, nullable=False),
    Column("write_scope", JSONB, nullable=False),
    Column("forbidden_paths", JSONB, nullable=False),
    Column("integration_target", String(1024), nullable=True),
    UniqueConstraint("source_vector_id", "mount_id", name="uq_source_members_mount"),
    UniqueConstraint(
        "source_vector_id",
        "container_path",
        name="uq_source_members_destination",
    ),
)

execution_resource_envelopes = Table(
    "execution_resource_envelopes",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "pwu_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("schema_version", Integer, nullable=False),
    Column("policy_version", String(128), nullable=False),
    Column("provider_profile", String(255), nullable=False),
    Column(
        "permitted_provider_profiles",
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    ),
    Column("max_inference_submissions", Integer, nullable=False),
    Column("max_tool_effects", Integer, nullable=False),
    Column("max_active_seconds", Integer, nullable=False),
    Column("max_successor_recoveries", Integer, nullable=False),
    Column("max_parallel_workers", Integer, nullable=False),
    Column("max_cost_units", BigInteger, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "max_inference_submissions > 0",
        name="ck_execution_resource_envelopes_inference_budget_positive",
    ),
    CheckConstraint(
        "max_tool_effects > 0",
        name="ck_execution_resource_envelopes_tool_budget_positive",
    ),
    CheckConstraint(
        "max_active_seconds > 0",
        name="ck_execution_resource_envelopes_active_time_positive",
    ),
    CheckConstraint(
        "max_successor_recoveries >= 0",
        name="ck_execution_resource_envelopes_recovery_budget_nonnegative",
    ),
    CheckConstraint(
        "max_parallel_workers > 0",
        name="ck_execution_resource_envelopes_worker_budget_positive",
    ),
)

execution_sessions = Table(
    "execution_sessions",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "pwu_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("condition", String(32), nullable=False),
    Column("parent_checkpoint_id", Uuid(as_uuid=True), nullable=True),
    Column("current_checkpoint_id", Uuid(as_uuid=True), nullable=True),
    Column("current_working_state_version", Integer, nullable=False, server_default="0"),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("closed_at", DateTime(timezone=True), nullable=True),
)

execution_workspaces = Table(
    "execution_workspaces",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "pwu_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    ),
    Column(
        "source_vector_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_source_vectors.id"),
        nullable=False,
    ),
    Column("condition", String(32), nullable=False),
    Column("host_storage_id", String(255), nullable=False),
    Column("materialization_path", String(2048), nullable=False),
    Column("manifest", JSONB, nullable=False),
    Column("manifest_digest", String(64), nullable=False),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

native_attempt_bindings = Table(
    "native_attempt_bindings",
    metadata,
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "pwu_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "session_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_sessions.id"),
        nullable=False,
    ),
    Column(
        "pwu_contract_version_id",
        Uuid(as_uuid=True),
        ForeignKey("pwu_contract_versions.id"),
        nullable=False,
    ),
    Column(
        "source_vector_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_source_vectors.id"),
        nullable=False,
    ),
    Column(
        "workspace_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_workspaces.id"),
        nullable=False,
    ),
    Column(
        "resource_envelope_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_resource_envelopes.id"),
        nullable=False,
    ),
    Column("binding_payload", JSONB, nullable=False),
    Column("binding_digest", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

native_attempt_states = Table(
    "native_attempt_states",
    metadata,
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("generation", Integer, nullable=False),
    Column("grant_state", String(32), nullable=False),
    Column("runtime_mode", String(32), nullable=False),
    Column("terminal_outcome", String(64), nullable=True),
    Column("control_version", Integer, nullable=False, server_default="0"),
    Column("worker_epoch", Integer, nullable=False, server_default="0"),
    Column("current_step_sequence", Integer, nullable=False, server_default="0"),
    Column("current_checkpoint_id", Uuid(as_uuid=True), nullable=True),
    Column("blocker_reasons", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("effect_uncertainty", Boolean, nullable=False, server_default=text("false")),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

executor_queue = Table(
    "executor_queue",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("command_id", Uuid(as_uuid=True), nullable=False, unique=True),
    Column("request_digest", String(64), nullable=False),
    Column("actor_identity", String(255), nullable=False),
    Column("work_id", Uuid(as_uuid=True), nullable=False),
    Column(
        "pwu_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("grant_revision", Integer, nullable=False),
    Column("fairness_group", String(255), nullable=False),
    Column("condition", String(32), nullable=False),
    Column("required_capabilities", JSONB, nullable=False),
    Column("required_provider_profile", String(255), nullable=False),
    Column("required_resource_profile", String(255), nullable=False),
    Column("wait_reason", Text, nullable=True),
    Column("enqueued_at", DateTime(timezone=True), nullable=False),
    Column("available_at", DateTime(timezone=True), nullable=False),
    Column("resume_count", Integer, nullable=False, server_default="0"),
    Column("version", Integer, nullable=False, server_default="1"),
)

Index(
    "uq_executor_queue_active_grant",
    executor_queue.c.attempt_id,
    executor_queue.c.grant_revision,
    unique=True,
    postgresql_where=text(
        "condition IN ('QUEUED','WAITING_RESOURCE','WAITING_HUMAN',"
        "'ALLOCATED','EXECUTING','CHECKPOINTED','RETURNED_TO_QUEUE')"
    ),
)
Index(
    "ix_executor_queue_runnable",
    executor_queue.c.condition,
    executor_queue.c.available_at,
    executor_queue.c.enqueued_at,
)

execution_allocations = Table(
    "execution_allocations",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "queue_entry_id",
        Uuid(as_uuid=True),
        ForeignKey("executor_queue.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "pwu_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("grant_revision", Integer, nullable=False),
    Column("worker_id", String(255), nullable=False),
    Column("worker_profile", String(255), nullable=False),
    Column("provider_profile", String(255), nullable=False),
    Column("lease_epoch", Integer, nullable=False),
    Column("lease_token_digest", String(64), nullable=False),
    Column("condition", String(32), nullable=False),
    Column("policy_version", String(128), nullable=False),
    Column("decision_reason", Text, nullable=False),
    Column("issued_at", DateTime(timezone=True), nullable=False),
    Column("start_deadline", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("released_at", DateTime(timezone=True), nullable=True),
)

Index(
    "uq_execution_allocations_active_attempt",
    execution_allocations.c.attempt_id,
    unique=True,
    postgresql_where=text("condition IN ('ISSUED','ACTIVE')"),
)

executor_leases = Table(
    "executor_leases",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "allocation_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_allocations.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("worker_id", String(255), nullable=False),
    Column("epoch", Integer, nullable=False),
    Column("token_digest", String(64), nullable=False),
    Column("deadline", DateTime(timezone=True), nullable=False),
    Column("heartbeat_at", DateTime(timezone=True), nullable=False),
    Column("released_at", DateTime(timezone=True), nullable=True),
    UniqueConstraint("attempt_id", "epoch", name="uq_executor_leases_attempt_epoch"),
)

Index(
    "uq_executor_leases_live_attempt",
    executor_leases.c.attempt_id,
    unique=True,
    postgresql_where=text("released_at IS NULL"),
)

execution_steps = Table(
    "execution_steps",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "session_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_sessions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("sequence", Integer, nullable=False),
    Column("kind", String(32), nullable=False),
    Column("condition", String(32), nullable=False),
    Column("request_payload", JSONB, nullable=False),
    Column("request_digest", String(64), nullable=False),
    Column("result_payload", JSONB, nullable=True),
    Column("result_digest", String(64), nullable=True),
    Column("context_revision", Integer, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    UniqueConstraint("session_id", "sequence", name="uq_execution_steps_sequence"),
)

execution_effects = Table(
    "execution_effects",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "step_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_steps.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("proposal_index", Integer, nullable=False),
    Column("tool_identity", String(255), nullable=False),
    Column("tool_version", String(64), nullable=False),
    Column("semantic_input", JSONB, nullable=False),
    Column("semantic_input_digest", String(64), nullable=False),
    Column("classification", String(64), nullable=False),
    Column("conflict_domains", JSONB, nullable=False),
    Column("condition", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("step_id", "proposal_index", name="uq_execution_effects_proposal"),
)

effect_receipts = Table(
    "effect_receipts",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "effect_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_effects.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("delivery_id", Uuid(as_uuid=True), nullable=False),
    Column("host_identity", String(255), nullable=False),
    Column("host_nonce", String(255), nullable=False),
    Column("condition", String(32), nullable=False),
    Column("output", JSONB, nullable=False),
    Column("output_digest", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("effect_id", "delivery_id", name="uq_effect_receipts_delivery"),
)

checkpoint_bundles = Table(
    "checkpoint_bundles",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("schema_version", Integer, nullable=False),
    Column(
        "session_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_sessions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("step_sequence", Integer, nullable=False),
    Column("worker_epoch", Integer, nullable=False),
    Column("condition", String(32), nullable=False),
    Column("source_vector_digest", String(64), nullable=False),
    Column("repository_manifest", JSONB, nullable=False),
    Column("execution_manifest", JSONB, nullable=False),
    Column("semantic_manifest", JSONB, nullable=False),
    Column("content_digest", String(64), nullable=False),
    Column("consistency_class", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("committed_at", DateTime(timezone=True), nullable=True),
)

execution_evidence = Table(
    "execution_evidence",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "pwu_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("step_id", Uuid(as_uuid=True), nullable=True),
    Column("effect_id", Uuid(as_uuid=True), nullable=True),
    Column("evidence_type", String(64), nullable=False),
    Column("producer_identity", String(255), nullable=False),
    Column("subject_digest", String(64), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("content_digest", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

result_ready_claims = Table(
    "result_ready_claims",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "pwu_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "checkpoint_bundle_id",
        Uuid(as_uuid=True),
        ForeignKey("checkpoint_bundles.id"),
        nullable=False,
    ),
    Column("contract_digest", String(64), nullable=False),
    Column("output_vector", JSONB, nullable=False),
    Column("evidence_ids", JSONB, nullable=False),
    Column("residual_obligations", JSONB, nullable=False),
    Column("claimant_identity", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

execution_resource_usage = Table(
    "execution_resource_usage",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "envelope_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_resource_envelopes.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("reservation_key", String(255), nullable=False),
    Column("resource_type", String(64), nullable=False),
    Column("amount", BigInteger, nullable=False),
    Column("certainty", String(32), nullable=False),
    Column("condition", String(32), nullable=False),
    Column("evidence", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "envelope_id",
        "reservation_key",
        "resource_type",
        name="uq_execution_resource_usage_reservation",
    ),
)

execution_control_requests = Table(
    "execution_control_requests",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("command_id", Uuid(as_uuid=True), nullable=False, unique=True),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("actor_identity", String(255), nullable=False),
    Column("action", String(32), nullable=False),
    Column("expected_control_version", Integer, nullable=False),
    Column("request_digest", String(64), nullable=False),
    Column("condition", String(32), nullable=False),
    Column("reason", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("applied_at", DateTime(timezone=True), nullable=True),
)

execution_recovery_cases = Table(
    "execution_recovery_cases",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "pwu_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "attempt_id",
        Uuid(as_uuid=True),
        ForeignKey("execution_attempts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("classification", String(64), nullable=False),
    Column("basis_checkpoint_id", Uuid(as_uuid=True), nullable=True),
    Column("observed_reality", JSONB, nullable=False),
    Column("residual_obligations", JSONB, nullable=False),
    Column("effect_uncertainty", Boolean, nullable=False),
    Column("resolution", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("resolved_at", DateTime(timezone=True), nullable=True),
)

self_refine_events = Table(
    "self_refine_events",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("work_id", Uuid(as_uuid=True), nullable=False),
    Column("operation_id", Uuid(as_uuid=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("failure_family", String(64), nullable=False),
    Column("failure_signature", String(64), nullable=False),
    Column("affected_component", String(255), nullable=False),
    Column("expected_reality", JSONB, nullable=False),
    Column("observed_reality", JSONB, nullable=False),
    Column("diagnosis_summary", Text, nullable=False),
    Column("root_cause_classification", String(64), nullable=False),
    Column("repair_hypothesis", Text, nullable=False),
    Column("evidence_references", JSONB, nullable=False),
    Column("repairability", String(64), nullable=False, server_default="REPAIRABLE_WITH_SUFFICIENT_EVIDENCE"),
    Column("observation_confidence", String(64), nullable=False, server_default="CONFIRMED_FAILURE"),
    Column("budget_decision", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("diagnostic_evidence", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("final_result", String(32), nullable=True),
    Column("work_resume_result", String(64), nullable=True),
    Column("extra_elapsed_seconds", Integer, nullable=True),
    Column("model_token_usage", JSONB, nullable=False),
    Column("compute_overhead", JSONB, nullable=False),
    Column("known_failure_match", Boolean, nullable=False),
    Column("platform_improvement_candidate_ref", String(255), nullable=True),
    Column("status", String(32), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
Index("ix_self_refine_events_work_created", self_refine_events.c.work_id, self_refine_events.c.created_at)
Index("ix_self_refine_events_signature", self_refine_events.c.failure_signature)
Index("ix_self_refine_events_status", self_refine_events.c.status)

self_refine_actions = Table(
    "self_refine_actions",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("event_id", Uuid(as_uuid=True), ForeignKey("self_refine_events.id"), nullable=False),
    Column("sequence", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("repair_action", Text, nullable=False),
    Column("observed_reality", JSONB, nullable=False),
    Column("evidence_references", JSONB, nullable=False),
    Column("outcome", String(32), nullable=False),
    UniqueConstraint("event_id", "sequence", name="uq_self_refine_actions_sequence"),
)

execution_events = Table(
    "execution_events",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "pwu_id",
        Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("attempt_id", Uuid(as_uuid=True), nullable=True),
    Column("sequence", BigInteger, nullable=False),
    Column("event_type", String(128), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("causation_id", Uuid(as_uuid=True), nullable=True),
    Column("correlation_id", Uuid(as_uuid=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("pwu_id", "sequence", name="uq_execution_events_sequence"),
)

event_outbox = Table(
    "event_outbox",
    metadata,
    Column("event_id", Uuid(as_uuid=True), ForeignKey("execution_events.id"), primary_key=True),
    Column("condition", String(32), nullable=False, server_default="PENDING"),
    Column("attempt_count", Integer, nullable=False, server_default="0"),
    Column("available_at", DateTime(timezone=True), nullable=False),
    Column("published_at", DateTime(timezone=True), nullable=True),
)

executor_scheduler_state = Table(
    "executor_scheduler_state",
    metadata,
    Column("scheduler_identity", String(128), primary_key=True),
    Column("policy_version", String(128), nullable=False),
    Column("last_fairness_group", String(255), nullable=True),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

executor_worker_registrations = Table(
    "executor_worker_registrations",
    metadata,
    Column("worker_id", String(255), primary_key=True),
    Column("worker_profile", String(255), nullable=False),
    Column("provider_profiles", JSONB, nullable=False),
    Column("resource_profiles", JSONB, nullable=False),
    Column("capability_identities", JSONB, nullable=False),
    Column("heartbeat_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("version", Integer, nullable=False, server_default="1"),
)

Index("ix_executor_worker_registrations_expires", executor_worker_registrations.c.expires_at)

native_candidate_vectors = Table(
    "native_candidate_vectors",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "pwu_id", Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", ondelete="CASCADE"), nullable=False,
    ),
    Column("source_vector_digest", String(64), nullable=False),
    Column(
        "checkpoint_id", Uuid(as_uuid=True),
        ForeignKey("checkpoint_bundles.id"), nullable=False,
    ),
    Column("manifest", JSONB, nullable=False),
    Column("manifest_digest", String(64), nullable=False, unique=True),
    Column("condition", String(32), nullable=False),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

native_vector_verifications = Table(
    "native_vector_verifications",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "pwu_id", Uuid(as_uuid=True),
        ForeignKey("production_work_units.id", ondelete="CASCADE"), nullable=False,
    ),
    Column("mount_id", String(255), nullable=False),
    Column("proposed_revision", String(128), nullable=False),
    Column("proposed_tree_identity", String(128), nullable=False),
    Column("obligation", Text, nullable=False),
    Column("provider_identity", String(255), nullable=False),
    Column("result", String(32), nullable=False),
    Column("evidence", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "pwu_id", "mount_id", "proposed_revision", "obligation", "provider_identity",
        name="uq_native_vector_verification_basis",
    ),
)

native_candidate_vector_targets = Table(
    "native_candidate_vector_targets",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "vector_id", Uuid(as_uuid=True),
        ForeignKey("native_candidate_vectors.id", ondelete="CASCADE"), nullable=False,
    ),
    Column("mount_id", String(255), nullable=False),
    Column("target", JSONB, nullable=False),
    Column("condition", String(32), nullable=False),
    Column("observed_revision", String(128), nullable=True),
    Column("operation_key", String(64), nullable=False, unique=True),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("prepared_at", DateTime(timezone=True), nullable=False),
    Column("settled_at", DateTime(timezone=True), nullable=True),
    UniqueConstraint("vector_id", "mount_id", name="uq_native_candidate_vector_mount"),
)

native_candidate_vector_authorizations = Table(
    "native_candidate_vector_authorizations",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "vector_id", Uuid(as_uuid=True),
        ForeignKey("native_candidate_vectors.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    ),
    Column("manifest_digest", String(64), nullable=False),
    Column("authority_identity", String(255), nullable=False),
    Column("rationale", Text, nullable=False),
    Column("authorized_at", DateTime(timezone=True), nullable=False),
)

native_trusted_source_pointers = Table(
    "native_trusted_source_pointers",
    metadata,
    Column("repository_identity", String(1024), primary_key=True),
    Column("target_authoritative_ref", String(1024), primary_key=True),
    Column("repository_revision", String(128), nullable=False),
    Column("tree_identity", String(128), nullable=False),
    Column("trusted_vector_digest", String(64), nullable=False),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

native_aggregate_runtime_commits = Table(
    "native_aggregate_runtime_commits",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "vector_id", Uuid(as_uuid=True),
        ForeignKey("native_candidate_vectors.id"), nullable=False, unique=True,
    ),
    Column("manifest_digest", String(64), nullable=False),
    Column(
        "authorization_id", Uuid(as_uuid=True),
        ForeignKey("native_candidate_vector_authorizations.id"), nullable=False,
    ),
    Column("trusted_vector_digest", String(64), nullable=False, unique=True),
    Column("committed_at", DateTime(timezone=True), nullable=False),
)

native_resource_pins = Table(
    "native_resource_pins",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("resource_kind", String(64), nullable=False),
    Column("resource_id", String(1024), nullable=False),
    Column("owner_kind", String(64), nullable=False),
    Column("owner_id", String(1024), nullable=False),
    Column("reason", Text, nullable=False),
    Column("active", Boolean, nullable=False, server_default=text("true")),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("released_at", DateTime(timezone=True), nullable=True),
    UniqueConstraint(
        "resource_kind", "resource_id", "owner_kind", "owner_id",
        name="uq_native_resource_pin_owner",
    ),
)

native_retention_actions = Table(
    "native_retention_actions",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "workspace_id", Uuid(as_uuid=True),
        ForeignKey("execution_workspaces.id", ondelete="CASCADE"), nullable=False,
    ),
    Column("action_key", String(64), nullable=False, unique=True),
    Column("action_kind", String(32), nullable=False),
    Column("condition", String(32), nullable=False),
    Column("bundle_digest", String(64), nullable=True),
    Column("bundle_path", String(2048), nullable=True),
    Column("physical_receipt", JSONB, nullable=True),
    Column("failure", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=True),
)

native_workspace_tombstones = Table(
    "native_workspace_tombstones",
    metadata,
    Column("workspace_id", Uuid(as_uuid=True), primary_key=True),
    Column("pwu_id", Uuid(as_uuid=True), nullable=False),
    Column("attempt_id", Uuid(as_uuid=True), nullable=False),
    Column("manifest_digest", String(64), nullable=False),
    Column("last_bundle_digest", String(64), nullable=True),
    Column("retention_action_id", Uuid(as_uuid=True), nullable=False, unique=True),
    Column("deleted_at", DateTime(timezone=True), nullable=False),
)


native_execution_tables = (
    pwu_contract_versions,
    execution_source_vectors,
    execution_source_members,
    execution_resource_envelopes,
    execution_sessions,
    execution_workspaces,
    native_attempt_bindings,
    native_attempt_states,
    executor_queue,
    execution_allocations,
    executor_leases,
    execution_steps,
    execution_effects,
    effect_receipts,
    checkpoint_bundles,
    execution_evidence,
    result_ready_claims,
    execution_resource_usage,
    execution_control_requests,
    execution_recovery_cases,
    self_refine_events,
    self_refine_actions,
    execution_events,
    event_outbox,
    executor_scheduler_state,
    executor_worker_registrations,
    native_candidate_vectors,
    native_vector_verifications,
    native_candidate_vector_targets,
    native_candidate_vector_authorizations,
    native_trusted_source_pointers,
    native_aggregate_runtime_commits,
    native_resource_pins,
    native_retention_actions,
    native_workspace_tombstones,
)
