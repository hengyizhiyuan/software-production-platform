"""Run the image's uncommitted source for isolated pre-commit qualification only.

The normal product launcher intentionally activates the Current Trusted Baseline.
This explicit qualification launcher retains its database/repository foundation
checks but serves the package built from the current worktree without claiming
that it is an admitted application revision.
"""

from __future__ import annotations

import os
import sys

from start_app import (
    ensure_local_databases,
    ensure_local_product_foundation,
    migrate_product_database,
    prepare_repository_snapshot,
    synchronize_repository_checkout,
)


def main() -> None:
    if os.environ.get("SPG_RUNTIME_PROFILE") != "uncommitted-qualification":
        raise RuntimeError("uncommitted launcher requires its explicit qualification profile")
    ensure_local_databases()
    migrate_product_database()
    repository = prepare_repository_snapshot()
    synchronize_repository_checkout(repository)
    ensure_local_product_foundation(repository)
    print("uncommitted image source active for isolated qualification only", flush=True)
    os.execv(
        sys.executable,
        (
            sys.executable, "-m", "uvicorn",
            "spg.api.http:create_http_application", "--factory",
            "--host", "0.0.0.0", "--port", "8000",
        ),
    )


if __name__ == "__main__":
    main()
