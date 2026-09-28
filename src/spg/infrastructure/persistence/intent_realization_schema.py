"""Turn-scoped immutable semantics and versioned owner-effect obligations."""
from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text, Uuid, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from spg.infrastructure.persistence.metadata import metadata


turn_realizations = Table(
    "interaction_turn_realizations", metadata,
    Column("turn_id", Uuid(as_uuid=True), ForeignKey("interaction_turns.id"), primary_key=True),
    Column("semantic_ir_id", Uuid(as_uuid=True), nullable=False, unique=True),
    Column("assessment_id", Uuid(as_uuid=True), ForeignKey("interaction_assessments.id"), nullable=False),
    Column("payload", JSONB, nullable=False),
)
turn_semantic_envelopes = Table(
    "interaction_turn_semantic_envelopes", metadata,
    Column("turn_id", Uuid(as_uuid=True), ForeignKey("interaction_turns.id"), primary_key=True),
    Column("source_record_id", Uuid(as_uuid=True), ForeignKey("interaction_records.id"), nullable=False),
    Column("human_content_hash", String(64), nullable=False),
    Column("provenance_basis", JSONB, nullable=False),
    Column("state", String(40), nullable=False),
    Column("attempt", Integer, nullable=False),
    Column("basis_fingerprint", String(64), nullable=True),
    Column("semantic_ir_id", Uuid(as_uuid=True), nullable=True),
    Column("blocker", JSONB, nullable=True),
    Column("history", JSONB, nullable=False),
)
turn_obligations = Table(
    "interaction_turn_obligations", metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("turn_id", Uuid(as_uuid=True), ForeignKey("interaction_turn_realizations.turn_id"), nullable=False),
    Column("semantic_item_id", String(100), nullable=False),
    Column("state", String(32), nullable=False),
    Column("version", Integer, nullable=False),
    Column("payload", JSONB, nullable=False),
    UniqueConstraint("turn_id", "semantic_item_id", name="uq_turn_obligations_item"),
)
realization_refinements = Table(
    "interaction_turn_realization_refinements", metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("turn_id", Uuid(as_uuid=True), ForeignKey("interaction_turns.id"), nullable=False),
    Column("obligation_id", Uuid(as_uuid=True), ForeignKey("interaction_turn_obligations.id"), nullable=True),
    Column("parent_id", Uuid(as_uuid=True), ForeignKey("interaction_turn_realization_refinements.id"), nullable=True),
    Column("scope", String(16), nullable=False),
    Column("attempt", Integer, nullable=False),
    Column("signature", Text, nullable=False),
    Column("payload", JSONB, nullable=False),
    UniqueConstraint("turn_id", "signature", "attempt", name="uq_realization_refinement_attempt"),
)
intent_realization_tables = (turn_realizations, turn_semantic_envelopes,
    turn_obligations, realization_refinements)
