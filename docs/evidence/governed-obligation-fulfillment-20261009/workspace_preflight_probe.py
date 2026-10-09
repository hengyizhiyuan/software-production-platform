"""Read-only persisted Attempt replay plus isolated negative workspace probes.

Run inside the existing isolated Worker container. No Work/Product is created;
temporary Git clones and observation blobs are removed on exit.
"""

import json
from pathlib import Path
import subprocess
import tempfile

from sqlalchemy import create_engine, text

from spg.config import Settings
from spg.domain.native_execution import ExecutionBindingV2
from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
from spg.infrastructure.executor_runtime.production_evidence import (
    ProductionWorkspaceVerificationFailed, observe_production_workspace,
)


ATTEMPT = "e3addc05-7ee4-49f4-9043-c69b6466bcf8"


def replace_mount(binding, path, container_path=None):
    mount = binding.workspace.mounts[0]
    mount = mount.model_copy(update={
        "host_path": str(path),
        "container_path": container_path or mount.container_path,
    })
    return binding.model_copy(update={"workspace": binding.workspace.model_copy(
        update={"mounts": (mount,)})})


def expect_failure(name, binding, storage, *, require_change=False):
    try:
        observe_production_workspace(binding, storage,
                                     require_change=require_change)
    except ProductionWorkspaceVerificationFailed as error:
        return {"case": name, "result": "REJECTED", "reason": str(error)}
    raise AssertionError(name + " was unexpectedly accepted")


def main():
    engine = create_engine(Settings().database_url)
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        raw = connection.execute(text("""
            SELECT binding_payload FROM native_attempt_bindings
            WHERE attempt_id = :attempt
        """), {"attempt": ATTEMPT}).scalar_one()
    binding = ExecutionBindingV2.model_validate(raw)
    mount = binding.workspace.mounts[0]
    actual = Path(mount.host_path)
    worker_root = Settings().native_executor_workspace_root.resolve()
    assert actual.resolve().is_relative_to(worker_root)
    assert binding.source_vector.members[0].container_path == mount.container_path
    assert actual.is_dir() and not actual.is_symlink()
    with tempfile.TemporaryDirectory(prefix="gof-preflight-") as temporary:
        root = Path(temporary)
        storage = ContentAddressedStorage(root / "evidence")
        positive = observe_production_workspace(binding, storage,
                                                require_change=False)
        checks = []
        checks.append(expect_failure("wrong-path", replace_mount(binding, root / "absent"),
                                     storage))
        wrong_context = binding.production_context.model_copy(
            update={"repository_revision": "0" * 40})
        checks.append(expect_failure("wrong-revision", binding.model_copy(
            update={"production_context": wrong_context}), storage))
        link = root / "link"
        link.symlink_to(actual, target_is_directory=True)
        checks.append(expect_failure("symlink", replace_mount(binding, link), storage))
        clone = root / "clone"
        subprocess.run(["git", "clone", "--no-hardlinks", "--", str(actual), str(clone)],
                       check=True, capture_output=True, timeout=30)
        (clone / "outside-scope.html").write_text("out of scope", encoding="utf-8")
        checks.append(expect_failure("wrong-scope", replace_mount(binding, clone),
                                     storage, require_change=True))
        print(json.dumps({
            "attempt_id": ATTEMPT,
            "worker_root": str(worker_root),
            "persisted_mount_path": str(actual),
            "source_revision": positive["repository_revision"],
            "positive": "PASS_NOW_ONLY",
            "checks": checks,
        }, sort_keys=True))


if __name__ == "__main__":
    main()
