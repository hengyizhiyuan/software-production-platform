"""Versioned release evaluation evidence; distinct from Human Acceptance."""

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, Text, Uuid, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from spg.infrastructure.persistence.metadata import metadata


evaluation_runs = Table(
    "evaluation_runs", metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("version", String(128), nullable=False),
    Column("revision", String(64), nullable=False),
    Column("corpus_version", String(64), nullable=False),
    Column("purpose", String(16), nullable=False),
    Column("qualification", String(16), nullable=False),
    Column("baseline_run_id", Uuid(as_uuid=True), ForeignKey("evaluation_runs.id")),
    Column("report", JSONB, nullable=False),
    Column("trend", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
Index("ix_evaluation_runs_purpose_created", evaluation_runs.c.purpose, evaluation_runs.c.created_at)
