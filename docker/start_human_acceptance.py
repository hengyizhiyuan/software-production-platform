"""Start an isolated acceptance Runtime from the current source overlay."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys


CURRENT_SOURCE = "/acceptance-source"
IMAGE_STARTUP = "/app/docker/start_app.py"
REVIEW_CONFIGURATION = Path("/review-config")
REVIEW_VERSIONS = Path("/var/lib/spg/human-review-versions")


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
    if os.environ.get("SPG_RUNTIME_ACTIVATION_MODE", "NORMAL") == "HUMAN_REVIEW":
        from spg.config import Settings
        from spg.infrastructure.runtime_activation import GitLocalRuntimeActivation
        from spg.infrastructure.persistence.runtime_store import RuntimeStore
        from spg.domain.runtime import SnapshotCondition

        database = startup.bootstrap().persistence()
        try:
            with database.unit_of_work() as unit_of_work:
                pointer = RuntimeStore(unit_of_work.session).current_pointer(
                    repository_identity=startup.REPOSITORY_IDENTITY,
                    repository_ref=startup._current_repository_ref(repository),
                )
                baseline = None if pointer is None else RuntimeStore(unit_of_work.session).snapshot(pointer.snapshot_id)
            if baseline is None or baseline.condition is not SnapshotCondition.TRUSTED:
                raise RuntimeError("Human Review requires the normal initial Trusted Baseline")
            inspector = GitLocalRuntimeActivation()
            version = inspector.prepare_review(
                repository_path=repository,
                trusted_revision=baseline.repository_revision,
                trusted_tree_identity=inspector.tree_identity(repository, baseline.repository_revision),
                source_root=Path(CURRENT_SOURCE),
                configuration_root=REVIEW_CONFIGURATION,
                settings=Settings(),
            )
        finally:
            database.dispose()
        REVIEW_VERSIONS.mkdir(parents=True, exist_ok=True)
        if REVIEW_VERSIONS.is_symlink():
            raise RuntimeError("Human Review evidence directory cannot be a symlink")
        version_file = REVIEW_VERSIONS / f"{version.version_id}.json"
        payload = version.model_dump_json()
        if version_file.exists() or version_file.is_symlink():
            if version_file.is_symlink() or version_file.read_text(encoding="utf-8") != payload:
                raise RuntimeError("Human Review version ID collided with existing evidence")
        else:
            with version_file.open("x", encoding="utf-8") as record:
                record.write(payload)
        environment = dict(os.environ)
        environment["SPG_HUMAN_REVIEW_VERSION_FILE"] = str(version_file)
        environment["SPG_HUMAN_REVIEW_VERSION_ID"] = version.version_id
        print(f"Human Review Runtime Version {version.version_id}", flush=True)
    else:
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
