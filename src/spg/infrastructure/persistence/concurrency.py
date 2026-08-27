"""Reusable expected-version update primitive for later authoritative records."""

from collections.abc import Mapping
from typing import Any

from sqlalchemy import Table, update
from sqlalchemy.orm import Session


class OptimisticConcurrencyConflict(RuntimeError):
    """Raised when an expected row version is no longer current."""


def update_versioned_row(
    session: Session,
    table: Table,
    *,
    identity: Mapping[str, Any],
    expected_version: int,
    values: Mapping[str, Any],
) -> int:
    """Update exactly one identified row from version N to N+1 or reject it."""

    if not identity:
        raise ValueError("version-aware update requires row identity")
    if expected_version < 0:
        raise ValueError("expected_version must be non-negative")
    if "version" not in table.c:
        raise ValueError("version-aware table must define a version column")
    if "version" in values:
        raise ValueError("version is advanced only by the concurrency primitive")

    conditions = [table.c.version == expected_version]
    for column_name, value in identity.items():
        if column_name not in table.c:
            raise ValueError(f"unknown identity column: {column_name}")
        conditions.append(table.c[column_name] == value)

    result = session.execute(
        update(table)
        .where(*conditions)
        .values(**values, version=expected_version + 1)
    )
    if result.rowcount != 1:
        raise OptimisticConcurrencyConflict(
            f"stale version for {table.name}: expected {expected_version}"
        )
    return expected_version + 1
