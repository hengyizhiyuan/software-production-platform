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
from spg.infrastructure.persistence.delivery_schema import delivery_tables
from spg.infrastructure.persistence.asset_schema import repository_intakes
from spg.infrastructure.persistence.steering_schema import steering_tables
from spg.infrastructure.persistence.guided_design_schema import guided_design_tables


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
    Column("selected_design_schema_identity", String(255), nullable=True),
    Column("selected_design_schema_version", String(32), nullable=True),
    Column("design_schema_selection_rationale", Text, nullable=True),
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
    Column("supporting_references", JSONB, nullable=False),
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

interaction_turns = Table(
    "interaction_turns",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "interaction_id",
        Uuid(as_uuid=True),
        ForeignKey("product_interactions.id", name="fk_interaction_turns_interaction"),
        nullable=False,
    ),
    Column(
        "request_record_id",
        Uuid(as_uuid=True),
        ForeignKey("interaction_records.id", name="fk_interaction_turns_request_record"),
        nullable=False,
        unique=True,
    ),
    Column(
        "assessment_id",
        Uuid(as_uuid=True),
        ForeignKey("interaction_assessments.id", name="fk_interaction_turns_assessment", use_alter=True),
        nullable=True,
        unique=True,
    ),
    Column("wic_mode", String(32), nullable=False, server_default="LEGACY_WIC"),
    Column("status", String(32), nullable=False),
    Column("failure_code", String(128), nullable=True),
    Column("failure_message", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "status IN ('RECEIVED', 'PROCESSING', 'COMPLETED', 'FAILED')",
        name="ck_interaction_turns_status_known",
    ),
    CheckConstraint(
        "wic_mode IN ('LEGACY_WIC', 'WIC_VNEXT_SHADOW', 'WIC_VNEXT_CONTROLLED')",
        name="ck_interaction_turns_wic_mode_known",
    ),
)

interaction_response_events = Table(
    "interaction_response_events",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "interaction_id",
        Uuid(as_uuid=True),
        ForeignKey("product_interactions.id", name="fk_interaction_response_events_interaction"),
        nullable=False,
    ),
    Column(
        "turn_id",
        Uuid(as_uuid=True),
        ForeignKey("interaction_turns.id", name="fk_interaction_response_events_turn"),
        nullable=False,
    ),
    Column("response_id", Uuid(as_uuid=True), nullable=False),
    Column("sequence", Integer, nullable=False),
    Column("event_type", String(64), nullable=False),
    Column("content", Text, nullable=True),
    Column("basis_fingerprint", String(64), nullable=True),
    Column("reconciliation", String(32), nullable=True),
    Column("event_metadata", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("turn_id", "sequence", name="uq_interaction_response_events_turn_sequence"),
    CheckConstraint("response_id = turn_id", name="ck_interaction_response_events_response_identity"),
)

interaction_messages = Table(
    "interaction_messages",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "interaction_id",
        Uuid(as_uuid=True),
        ForeignKey("product_interactions.id", name="fk_interaction_messages_interaction"),
        nullable=False,
    ),
    Column(
        "turn_id",
        Uuid(as_uuid=True),
        ForeignKey("interaction_turns.id", name="fk_interaction_messages_turn"),
        nullable=True,
    ),
    Column("sequence", Integer, nullable=False),
    Column("actor", String(32), nullable=False),
    Column("content", Text, nullable=False),
    Column("processing_status", String(32), nullable=False),
    Column(
        "interaction_record_id",
        Uuid(as_uuid=True),
        ForeignKey("interaction_records.id", name="fk_interaction_messages_record"),
        nullable=True,
        unique=True,
    ),
    Column(
        "interpretation_assessment_id",
        Uuid(as_uuid=True),
        ForeignKey("interaction_assessments.id", name="fk_interaction_messages_assessment", use_alter=True),
        nullable=True,
        unique=True,
    ),
    Column("design_result_references", JSONB, nullable=False),
    Column("governance_event_references", JSONB, nullable=False),
    Column("supporting_references", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("interaction_id", "sequence", name="uq_interaction_messages_interaction_sequence"),
    UniqueConstraint("turn_id", "actor", name="uq_interaction_messages_turn_actor"),
    CheckConstraint("actor IN ('HUMAN', 'WATT')", name="ck_interaction_messages_actor_known"),
    CheckConstraint(
        "processing_status IN ('RECEIVED', 'PROCESSING', 'COMPLETED', 'FAILED')",
        name="ck_interaction_messages_status_known",
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
    Column("design_intent_frame", JSONB, nullable=True),
    Column("candidate_context", JSONB, nullable=False),
    Column("candidate_constraints", JSONB, nullable=False),
    Column("current_requests", JSONB, nullable=False),
    Column("unresolved_material_questions", JSONB, nullable=False),
    Column("neutral_semantic_extractions", JSONB, nullable=False),
    Column("engineering_semantic_facts", JSONB, nullable=False),
    Column("meanings", JSONB, nullable=False),
    Column("focus_classification", String(32), nullable=True),
    Column("impact_disposition", String(48), nullable=True),
    Column("candidate_change", JSONB, nullable=True),
    Column(
        "basis_work_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "work_reality_revisions.id",
            name="fk_interaction_assessments_basis_work_revision",
            use_alter=True,
        ),
        nullable=True,
    ),
    Column(
        "basis_steering_plan_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "steering_plan_revisions.id",
            name="fk_interaction_assessments_basis_steering_revision",
        ),
        nullable=True,
    ),
    Column(
        "basis_steering_step_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "steering_steps.id",
            name="fk_interaction_assessments_basis_steering_step",
        ),
        nullable=True,
    ),
    Column(
        "basis_active_runtime_binding_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "work_runtime_bindings.id",
            name="fk_interaction_assessments_basis_runtime_binding",
            use_alter=True,
        ),
        nullable=True,
    ),
    Column("supporting_references", JSONB, nullable=False),
    Column("natural_response", Text, nullable=False),
    Column("readiness", JSONB, nullable=False),
    Column("progressive_semantics", JSONB, nullable=True),
    Column("provider_identity", String(255), nullable=False),
    Column("model_identity", String(255), nullable=True),
    Column("schema_version", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint(
        "interaction_id",
        "basis_fingerprint",
        name="uq_interaction_assessments_interaction_basis",
    ),
    CheckConstraint(
        "focus_classification IS NULL OR focus_classification IN "
        "('ON_TOPIC', 'RELEVANT_EXPLORATION', 'SIDE_QUESTION', "
        "'MATERIAL_BRANCH', 'UNRELATED_NEW_DEMAND')",
        name="ck_interaction_assessments_focus_known",
    ),
    CheckConstraint(
        "impact_disposition IS NULL OR impact_disposition IN "
        "('NO_GOVERNED_CHANGE', 'CURRENT_CYCLE_REMAINS_VALID', "
        "'DEFER_TO_PRODUCTION_BOUNDARY', 'CURRENT_RESULT_MAY_BE_INSUFFICIENT', "
        "'HUMAN_GOVERNANCE_REQUIRED', 'NEW_WORK_RECOMMENDED')",
        name="ck_interaction_assessments_impact_known",
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
    Column("revision_fingerprint", String(64), nullable=False),
    Column(
        "source_interaction_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "product_interactions.id",
            name="fk_work_reality_revisions_source_interaction",
        ),
        nullable=False,
    ),
    Column(
        "source_assessment_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "interaction_assessments.id",
            name="fk_work_reality_revisions_source_assessment",
        ),
        nullable=True,
    ),
    Column("source_kind", String(32), nullable=False, server_default="INTERACTION_ASSESSMENT"),
    Column("source_record_ids", JSONB, nullable=False),
    Column("motive", Text, nullable=False),
    Column("desired_outcome", Text, nullable=False),
    Column("context_facts", JSONB, nullable=False),
    Column("constraints", JSONB, nullable=False),
    Column("requests", JSONB, nullable=False),
    Column("engineering_semantic_facts", JSONB, nullable=False),
    Column(
        "engineering_scope_id",
        Uuid(as_uuid=True),
        ForeignKey("engineering_scopes.id", name="fk_work_reality_revisions_scope"),
        nullable=False,
    ),
    Column(
        "engineering_resource_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "engineering_resources.id",
            name="fk_work_reality_revisions_resource",
        ),
        nullable=True,
    ),
    Column("scope_basis_fingerprint", String(64), nullable=False),
    Column("repository_identity", String(255), nullable=True),
    Column("repository_ref", String(512), nullable=True),
    Column(
        "source_baseline_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "production_snapshots.id",
            name="fk_work_reality_revisions_baseline",
        ),
        nullable=True,
    ),
    Column("source_revision", String(64), nullable=True),
    Column(
        "governance_record_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "governance_records.id",
            name="fk_work_reality_revisions_governance",
        ),
        nullable=False,
    ),
    Column("supporting_references", JSONB, nullable=False),
    Column("change_set", JSONB, nullable=False),
    Column("rationale", Text, nullable=False),
    Column("admitted_by", String(255), nullable=False),
    Column("schema_version", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("(source_kind = 'INTERACTION_ASSESSMENT' AND source_assessment_id IS NOT NULL) OR (source_kind = 'ASSET_SCOPE_ADMISSION' AND source_assessment_id IS NULL)", name="ck_work_revision_source_kind"),
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
    UniqueConstraint(
        "revision_fingerprint",
        name="uq_work_reality_revisions_fingerprint",
    ),
    UniqueConstraint(
        "source_assessment_id",
        name="uq_work_reality_revisions_source_assessment",
    ),
    UniqueConstraint(
        "governance_record_id",
        name="uq_work_reality_revisions_governance",
    ),
)

interaction_work_transitions = Table(
    "interaction_work_transitions",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "interaction_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "product_interactions.id",
            name="fk_interaction_work_transitions_interaction",
        ),
        nullable=False,
    ),
    Column(
        "source_record_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "interaction_records.id",
            name="fk_interaction_work_transitions_source_record",
        ),
        nullable=False,
    ),
    Column(
        "source_assessment_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "interaction_assessments.id",
            name="fk_interaction_work_transitions_source_assessment",
        ),
        nullable=False,
        unique=True,
    ),
    Column(
        "originating_work_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "product_works.id",
            name="fk_interaction_work_transitions_originating_work",
        ),
        nullable=False,
    ),
    Column(
        "target_work_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "product_works.id",
            name="fk_interaction_work_transitions_target_work",
        ),
        nullable=True,
        unique=True,
    ),
    Column("reason", Text, nullable=False),
    Column("focus_classification", String(32), nullable=False),
    Column("impact_disposition", String(48), nullable=False),
    Column("choice", String(32), nullable=False),
    Column("decided_by", String(255), nullable=True),
    Column("decision_rationale", Text, nullable=True),
    Column("decided_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "focus_classification IN ('MATERIAL_BRANCH', 'UNRELATED_NEW_DEMAND')",
        name="ck_interaction_work_transitions_focus_known",
    ),
    CheckConstraint(
        "impact_disposition = 'NEW_WORK_RECOMMENDED'",
        name="ck_interaction_work_transitions_impact_known",
    ),
    CheckConstraint(
        "choice IN ('PENDING_HUMAN', 'CONTINUE_CURRENT_WORK', "
        "'START_NEW_WORK', 'DISMISSED')",
        name="ck_interaction_work_transitions_choice_known",
    ),
    CheckConstraint(
        "(choice = 'PENDING_HUMAN' AND decided_by IS NULL AND decided_at IS NULL) "
        "OR (choice <> 'PENDING_HUMAN' AND decided_by IS NOT NULL "
        "AND decided_at IS NOT NULL)",
        name="ck_interaction_work_transitions_decision_coherent",
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
    interaction_turns,
    interaction_response_events,
    interaction_messages,
    interaction_assessments,
    work_reality_revisions,
    interaction_work_transitions,
    work_runtime_bindings,
    *steering_tables,
    *guided_design_tables,
    repository_intakes,
    *delivery_tables,
)
