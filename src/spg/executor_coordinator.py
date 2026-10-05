"""Container entrypoint for native lease reconciliation coordination."""

from __future__ import annotations

import time

from spg.application.bootstrap import bootstrap
from spg.application.native_retention import NativeRetentionService
from spg.infrastructure.executor_runtime.local_storage import WorkspaceArchiveStore


def main() -> None:
    application = bootstrap()
    if not application.settings.native_executor_enabled:
        raise RuntimeError("SPG_NATIVE_EXECUTOR_ENABLED must be true")
    database = application.persistence()
    runtime = application.native_executor_runtime(database)
    retention = NativeRetentionService(
        database,
        WorkspaceArchiveStore(application.settings.native_executor_storage_root / "archives"),
    )
    next_retention_at = 0.0
    try:
        while True:
            runtime.reconcile_worker_liveness()
            runtime.reconcile_expired_leases()
            runtime.reconcile_queue_ownership()
            if time.monotonic() >= next_retention_at:
                retention.cleanup_expired(limit=100)
                next_retention_at = time.monotonic() + 3600
            time.sleep(application.settings.native_executor_poll_seconds)
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
