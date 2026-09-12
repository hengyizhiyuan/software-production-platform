"""Start an isolated acceptance Runtime from the current source overlay."""

from __future__ import annotations

import importlib.util
import os
import sys


CURRENT_SOURCE = "/acceptance-source"
IMAGE_STARTUP = "/app/docker/start_app.py"


def main() -> None:
    sys.path.insert(0, CURRENT_SOURCE)
    spec = importlib.util.spec_from_file_location("watt_image_startup", IMAGE_STARTUP)
    if spec is None or spec.loader is None:
        raise RuntimeError("image startup module is unavailable")
    startup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(startup)
    startup.prepare_optional_codex_state()
    startup.ensure_local_databases()
    startup.migrate_product_database()
    repository = startup.prepare_repository_snapshot()
    startup.synchronize_repository_checkout(repository)
    startup.ensure_local_product_foundation(repository)
    activation = startup.prepare_local_runtime_activation(repository)
    environment = startup._activated_environment(activation)
    environment["PYTHONPATH"] = os.pathsep.join(
        item for item in (CURRENT_SOURCE, environment.get("PYTHONPATH", "")) if item
    )
    os.execvpe(
        sys.executable,
        (
            sys.executable,
            "-m",
            "uvicorn",
            "spg.api.http:create_http_application",
            "--factory",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ),
        environment,
    )


if __name__ == "__main__":
    main()
