"""Work-scoped Human working-agreement history for the Control Room."""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Table, Text, Uuid, UniqueConstraint, func

from spg.infrastructure.persistence.metadata import metadata


work_agreement_events = Table(
    "work_agreement_events",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("work_id", Uuid(as_uuid=True), ForeignKey("product_works.id"), nullable=False),
    Column("agreement_id", Uuid(as_uuid=True), nullable=False),
    Column("sequence", Integer, nullable=False),
    Column("kind", String(16), nullable=False),
    Column("agreement_type", String(16), nullable=False),
    Column("content", Text, nullable=False),
    Column("actor_identity", String(255), nullable=False),
    Column("persistence_state", String(24), nullable=False),
    Column("persistence_path", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("kind IN ('CREATED', 'ABANDONED')", name="ck_agreement_event_kind"),
    UniqueConstraint("agreement_id", "sequence", name="uq_work_agreement_event_sequence"),
    CheckConstraint(
        "agreement_type IN ('DECISION', 'CONSTRAINT', 'REMINDER', 'DEFERRED', 'CANDIDATE')",
        name="ck_agreement_type",
    ),
    CheckConstraint(
        "persistence_state IN ('NOT_PERSISTED', 'PERSISTED')",
        name="ck_agreement_persistence_state",
    ),
)
Index("ix_work_agreement_events_work_time", work_agreement_events.c.work_id, work_agreement_events.c.created_at)
Index("ix_work_agreement_events_agreement_time", work_agreement_events.c.agreement_id, work_agreement_events.c.created_at)
