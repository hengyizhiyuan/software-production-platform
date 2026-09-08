"""Normalized persistence for reconstructable guided design process truth."""

from sqlalchemy import (
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


guided_design_processes = Table(
    "guided_design_processes",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "work_id",
        Uuid(as_uuid=True),
        ForeignKey("product_works.id", name="fk_guided_design_processes_work"),
        nullable=False,
        unique=True,
    ),
    Column("schema_identity", String(255), nullable=False),
    Column("schema_version", String(32), nullable=False),
    Column("schema_selection_rationale", Text, nullable=False),
    Column("objective", Text, nullable=False),
    Column("condition", String(32), nullable=False),
    Column(
        "basis_work_reality_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "work_reality_revisions.id",
            name="fk_guided_design_processes_work_reality",
        ),
        nullable=True,
    ),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "condition IN ('ACTIVE', 'READY', 'COMPLETE')",
        name="ck_guided_design_processes_condition_known",
    ),
)


guided_design_agenda_revisions = Table(
    "guided_design_agenda_revisions",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column(
        "process_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "guided_design_processes.id",
            name="fk_guided_design_agenda_revisions_process",
        ),
        nullable=False,
    ),
    Column(
        "work_id",
        Uuid(as_uuid=True),
        ForeignKey("product_works.id", name="fk_guided_design_agenda_revisions_work"),
        nullable=False,
    ),
    Column("revision_number", Integer, nullable=False),
    Column("condition", String(32), nullable=False),
    Column(
        "supersedes_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "guided_design_agenda_revisions.id",
            name="fk_guided_design_agenda_revisions_supersedes",
        ),
        nullable=True,
        unique=True,
    ),
    Column(
        "basis_work_reality_revision_id",
        Uuid(as_uuid=True),
        ForeignKey(
            "work_reality_revisions.id",
            name="fk_guided_design_agenda_revisions_work_reality",
        ),
        nullable=True,
    ),
    Column("rationale", Text, nullable=False),
    Column("reality_refs", JSONB, nullable=False),
    Column("issues", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint(
        "process_id",
        "revision_number",
        name="uq_guided_design_agenda_process_revision",
    ),
    CheckConstraint(
        "revision_number >= 1",
        name="ck_guided_design_agenda_revision_positive",
    ),
    CheckConstraint(
        "condition IN ('ACTIVE', 'SUPERSEDED')",
        name="ck_guided_design_agenda_condition_known",
    ),
)

Index(
    "uq_guided_design_agenda_one_active",
    guided_design_agenda_revisions.c.process_id,
    unique=True,
    postgresql_where=text("condition = 'ACTIVE'"),
)


guided_design_tables = (
    guided_design_processes,
    guided_design_agenda_revisions,
)
