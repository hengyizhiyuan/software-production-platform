"""Consume ECF-owned repository Reality at Watt decision boundaries."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from spg.domain.product import ProductInvariantViolation


def current_owner_repository_reality(reality, resource, root: Path,
    revision: str) -> dict:
    """Refresh superseded/expired ECF Reality and require the observed Git head."""
    current = reality.store.latest("repository", resource.repository_identity)
    expired = (current is None or current.freshness.refresh_after is not None
        and current.freshness.refresh_after <= datetime.now(UTC))
    superseded = current is not None and current.revision != revision
    if expired or superseded:
        observed = reality.discover_repository_payload(root,
            repository_identity=resource.repository_identity,
            requested_branch=resource.authoritative_ref.removeprefix("refs/heads/"))
    else:
        observed = current.model_dump(mode="python")
    if observed["revision"] != revision:
        raise ProductInvariantViolation(
            "ECF Engineering Reality differs from the bound repository revision")
    return {"reality_id": str(observed["reality_id"]),
        "revision": observed["revision"],
        "tree_identity": observed["tree_identity"],
        "source_reference": observed["provenance"]["source_reference"],
        "observed_at": observed["freshness"]["observed_at"],
        "freshness": observed["freshness"]["state"],
        "superseded_previous": superseded}
