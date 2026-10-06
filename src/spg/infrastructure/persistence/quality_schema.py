"""Quality owns cases, measurements and feedback. Owner runtime facts remain elsewhere."""
from sqlalchemy import (Table, Column, Uuid, String, Integer, DateTime, ForeignKey,
                        UniqueConstraint, CheckConstraint, Index, Float)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from spg.infrastructure.persistence.metadata import metadata


def identity():
    return Column("id", Uuid(as_uuid=True), primary_key=True)


def created():
    return Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now())


quality_cases = Table("quality_cases", metadata, identity(),
    Column("key", String(160), nullable=False, unique=True),
    Column("lifecycle", String(20), nullable=False),
    Column("cohorts", JSONB, nullable=False), Column("aliases", JSONB, nullable=False), created(),
    CheckConstraint("lifecycle IN ('ACTIVE','RETIRED')", name="ck_quality_case_lifecycle"))
quality_case_versions = Table("quality_case_versions", metadata, identity(),
    Column("case_id", Uuid(), ForeignKey("quality_cases.id"), nullable=False),
    Column("version", Integer(), nullable=False), Column("fingerprint", String(64), nullable=False),
    Column("definition", JSONB, nullable=False), created(),
    UniqueConstraint("case_id", "version", name="uq_quality_case_version"),
    UniqueConstraint("case_id", "fingerprint", name="uq_quality_case_fingerprint"))
quality_campaigns = Table("quality_campaigns", metadata, identity(),
    Column("key", String(160), nullable=False), Column("version", Integer(), nullable=False),
    Column("name", String(200), nullable=False), Column("fingerprint", String(64), nullable=False), created(),
    UniqueConstraint("key", "version", name="uq_quality_campaign_version"),
    UniqueConstraint("key", "fingerprint", name="uq_quality_campaign_fingerprint"))
quality_campaign_members = Table("quality_campaign_members", metadata,
    Column("campaign_id", Uuid(), ForeignKey("quality_campaigns.id"), primary_key=True),
    Column("case_version_id", Uuid(), ForeignKey("quality_case_versions.id"), primary_key=True),
    Column("ordinal", Integer(), nullable=False), Column("cohorts", JSONB, nullable=False))
quality_experiments = Table("quality_experiments", metadata, identity(),
    Column("case_id", Uuid(), ForeignKey("quality_cases.id"), nullable=False),
    Column("case_version_id", Uuid(), ForeignKey("quality_case_versions.id"), nullable=False),
    Column("version", Integer(), nullable=False), Column("fingerprint", String(64), nullable=False),
    Column("definition", JSONB, nullable=False), Column("authority_identity", String(255), nullable=False), created(),
    UniqueConstraint("case_id", "version", name="uq_quality_experiment_version"))
quality_campaign_runs = Table("quality_campaign_runs", metadata, identity(),
    Column("campaign_id", Uuid(), ForeignKey("quality_campaigns.id"), nullable=False),
    Column("experiment_id", Uuid(), ForeignKey("quality_experiments.id")),
    Column("variant_key", String(80)), Column("watt_revision", String(64), nullable=False),
    Column("policy_fingerprint", String(64), nullable=False), Column("configuration", JSONB, nullable=False),
    Column("state", String(20), nullable=False), Column("authority_identity", String(255), nullable=False),
    Column("lease_token", Uuid()), Column("lease_expires_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)), created(),
    CheckConstraint("state IN ('QUEUED','RUNNING','PASS','FAIL','BLOCKED')", name="ck_quality_run_state"))
Index("ix_quality_runs_queue", quality_campaign_runs.c.state, quality_campaign_runs.c.created_at)
quality_case_runs = Table("quality_case_runs", metadata, identity(),
    Column("campaign_run_id", Uuid(), ForeignKey("quality_campaign_runs.id"), nullable=False),
    Column("case_version_id", Uuid(), ForeignKey("quality_case_versions.id"), nullable=False),
    Column("attempt", Integer(), nullable=False), Column("state", String(20), nullable=False),
    Column("lineage", JSONB, nullable=False), Column("elapsed_seconds", Float()),
    Column("finished_at", DateTime(timezone=True)), created(),
    UniqueConstraint("campaign_run_id", "case_version_id", "attempt", name="uq_quality_case_attempt"))
quality_evaluations = Table("quality_evaluations", metadata, identity(),
    Column("case_run_id", Uuid(), ForeignKey("quality_case_runs.id"), nullable=False),
    Column("evaluator", String(20), nullable=False), Column("outcome", String(20), nullable=False),
    Column("record", JSONB, nullable=False), created())
quality_findings = Table("quality_findings", metadata, identity(),
    Column("case_run_id", Uuid(), ForeignKey("quality_case_runs.id"), nullable=False),
    Column("cluster_key", String(64), nullable=False), Column("stage", String(40)),
    Column("finding_code", String(100), nullable=False), Column("certainty", String(30), nullable=False),
    Column("state", String(20), nullable=False), Column("evidence_refs", JSONB, nullable=False),
    Column("regression_case_id", Uuid(), ForeignKey("quality_cases.id")),
    Column("regression_promotion", JSONB), Column("closure", JSONB), created())
Index("ix_quality_finding_cluster", quality_findings.c.cluster_key)
quality_preferences = Table("quality_preferences", metadata, identity(),
    Column("experiment_id", Uuid(), ForeignKey("quality_experiments.id"), nullable=False),
    Column("case_id", Uuid(), ForeignKey("quality_cases.id"), nullable=False),
    Column("record", JSONB, nullable=False), Column("authority_identity", String(255), nullable=False), created())
quality_learning_signals = Table("quality_learning_signals", metadata, identity(),
    Column("case_id", Uuid(), ForeignKey("quality_cases.id"), nullable=False),
    Column("source_kind", String(20), nullable=False), Column("source_id", Uuid(), nullable=False),
    Column("owner", String(40), nullable=False), Column("record", JSONB, nullable=False),
    Column("authority_identity", String(255), nullable=False), created())
quality_promotion_decisions = Table("quality_promotion_decisions", metadata, identity(),
    Column("experiment_id", Uuid(), ForeignKey("quality_experiments.id"), nullable=False),
    Column("variant_key", String(80), nullable=False), Column("record", JSONB, nullable=False),
    Column("authority_identity", String(255), nullable=False), created(),
    UniqueConstraint("experiment_id", "variant_key", name="uq_quality_promotion_decision"))
operations_metric_samples = Table("operations_metric_samples", metadata, identity(),
    Column("node_id", String(160), nullable=False), Column("record", JSONB, nullable=False), created())
Index("ix_operations_sample_time", operations_metric_samples.c.node_id, operations_metric_samples.c.created_at)
quality_tables = (quality_cases, quality_case_versions, quality_campaigns, quality_campaign_members,
    quality_experiments, quality_campaign_runs, quality_case_runs, quality_evaluations, quality_findings,
    quality_preferences, quality_learning_signals, quality_promotion_decisions, operations_metric_samples)
