"""Explicit PostgreSQL persistence boundary for the SPG runtime foundation."""

from spg.infrastructure.persistence.concurrency import (
    OptimisticConcurrencyConflict,
    update_versioned_row,
)
from spg.infrastructure.persistence.database import (
    Database,
    DatabaseConfigurationError,
    DatabaseHealth,
    configured_database_url,
)
from spg.infrastructure.persistence.metadata import metadata
from spg.infrastructure.persistence.product_schema import product_tables
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_schema import runtime_tables
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.steering_schema import steering_tables
from spg.infrastructure.persistence.steering_store import SteeringStore
from spg.infrastructure.persistence.unit_of_work import UnitOfWork

__all__ = [
    "Database",
    "DatabaseConfigurationError",
    "DatabaseHealth",
    "OptimisticConcurrencyConflict",
    "ProductStore",
    "RuntimeStore",
    "SteeringStore",
    "UnitOfWork",
    "configured_database_url",
    "metadata",
    "product_tables",
    "runtime_tables",
    "steering_tables",
    "update_versioned_row",
]
