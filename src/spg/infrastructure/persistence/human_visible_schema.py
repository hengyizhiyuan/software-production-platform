"""Disposable derived expression cache, never owner truth."""
from sqlalchemy import Table, Column, String, Uuid, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from spg.infrastructure.persistence.metadata import metadata

wic_human_realizations = Table('wic_human_realizations', metadata,
    Column('basis_fingerprint', String(64), primary_key=True),
    Column('work_id', Uuid(), ForeignKey('product_works.id'), nullable=True),
    Column('projection', JSONB, nullable=False),
    Column('realization', JSONB, nullable=False),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False))
