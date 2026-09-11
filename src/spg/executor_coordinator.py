"""Container entrypoint for native lease reconciliation coordination."""

from __future__ import annotations

import time

from spg.application.bootstrap import bootstrap


def main() -> None:
    application = bootstrap()
    if not application.settings.native_executor_enabled:
        raise RuntimeError("SPG_NATIVE_EXECUTOR_ENABLED must be true")
    database = application.persistence()
    runtime = application.native_executor_runtime(database)
    try:
        while True:
            runtime.reconcile_expired_leases()
            time.sleep(application.settings.native_executor_poll_seconds)
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
