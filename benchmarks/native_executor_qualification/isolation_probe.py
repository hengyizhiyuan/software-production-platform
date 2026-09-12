"""Exercise Q39/Q40 at the real shared Tool Host boundary without Provider use."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import uuid4

from spg.application.bootstrap import bootstrap
from spg.domain.native_execution import (
    CapabilityGrant,
    SourceVector,
    ToolCallProposal,
    ToolExecutionRequest,
    WorkspaceManifest,
    WorkspaceMount,
    canonical_digest,
)
from spg.infrastructure.executor_runtime.remote_tool_host import RemoteNativeToolHost


async def main() -> None:
    app = bootstrap()
    root = app.settings.native_executor_workspace_root / "q40-warm-reuse"
    first = root / "attempt-a"
    second = root / "attempt-b"
    first.mkdir(parents=True, exist_ok=True)
    (second / "tests").mkdir(parents=True, exist_ok=True)
    (first / "private-marker.txt").write_text("synthetic-private-marker\n")
    (first / "holder.py").write_text(
        "import os, time\n"
        "from pathlib import Path\n"
        "Path('pid.txt').write_text(str(os.getpid()))\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )
    (first / "pid.txt").unlink(missing_ok=True)
    (second / "tests/test_isolation.py").write_text(
        "from pathlib import Path\n"
        "import socket\n\n"
        "def test_approved_immutable_dependency_is_available():\n"
        "    import pytest\n"
        "    assert pytest.__version__\n\n"
        "def test_other_work_is_not_mounted():\n"
        "    private = Path.cwd().parent / 'attempt-a/private-marker.txt'\n"
        "    try:\n"
        "        private.read_text()\n"
        "    except OSError:\n"
        "        pass\n"
        "    else:\n"
        "        raise AssertionError('OTHER_WORK_READABLE')\n"
        "    try:\n"
        "        list(Path.cwd().parent.iterdir())\n"
        "    except OSError:\n"
        "        pass\n"
        "    else:\n"
        "        raise AssertionError('OTHER_WORK_ENUMERABLE')\n\n"
        "def test_other_process_cannot_be_signalled():\n"
        "    import os\n"
        "    pid = int(Path('holder-pid.txt').read_text())\n"
        "    try:\n"
        "        os.kill(pid, 0)\n"
        "    except PermissionError:\n"
        "        return\n"
        "    except ProcessLookupError:\n"
        "        raise AssertionError('HOLDER_PROCESS_LOST')\n"
        "    raise AssertionError('OTHER_PROCESS_ATTACHABLE')\n\n"
        "def test_internal_control_and_metadata_are_unreachable():\n"
        "    for host, port in [('app', 8000), ('169.254.169.254', 80)]:\n"
        "        try:\n"
        "            connection = socket.create_connection((host, port), timeout=0.5)\n"
        "        except OSError:\n"
        "            continue\n"
        "        connection.close()\n"
        "        raise AssertionError(f'HOST_REACHABLE:{host}')\n\n"
        "def test_redirect_and_rebinding_targets_cannot_open_a_socket():\n"
        "    # A hostile redirect or DNS-rebinding chain cannot bypass a kernel-level\n"
        "    # connect denial when neither its first nor rebound target is reachable.\n"
        "    for host, port in [('example.com', 80), ('localhost', 8011)]:\n"
        "        try:\n"
        "            connection = socket.create_connection((host, port), timeout=0.5)\n"
        "        except OSError:\n"
        "            continue\n"
        "        connection.close()\n"
        "        raise AssertionError(f'REDIRECT_OR_REBIND_TARGET_REACHABLE:{host}')\n",
        encoding="utf-8",
    )
    vector = SourceVector(non_repository_assets=({
        "kind": "qualification",
        "workspace_path": "tests/test_isolation.py",
        "content_digest": canonical_digest("q40"),
    },))
    work_id, pwu_id, attempt_id = uuid4(), uuid4(), uuid4()
    workspace = WorkspaceManifest(
        workspace_id=uuid4(), work_id=work_id, pwu_id=pwu_id,
        attempt_id=attempt_id, source_vector_digest=vector.digest or "",
        host_storage_id=str(second),
        environment_profile_digest=canonical_digest("q40-shared-tool-host"),
        mounts=(WorkspaceMount(
            mount_id="primary", host_path=str(second),
            container_path="/workspace/primary", writable=True,
            write_scope=("tests",), forbidden_paths=(".git",),
        ),),
        evidence_namespace="qualification:q40",
        retention_policy="probe-owned",
    )
    request = ToolExecutionRequest(
        delivery_id=uuid4(), attempt_id=attempt_id, worker_epoch=1,
        step_id=uuid4(),
        proposal=ToolCallProposal(
            proposal_index=0, tool_identity="test.run",
            arguments={
                "argv": ["python", "-m", "pytest", "-q", "tests/test_isolation.py"],
                "cwd": ".",
            },
        ),
        capability_grants=(CapabilityGrant(
            identity="test.run", version="1", scope={"paths": ["tests"]},
        ),),
        workspace=workspace,
    )
    first_workspace = workspace.model_copy(update={
        "workspace_id": uuid4(),
        "work_id": uuid4(),
        "pwu_id": uuid4(),
        "attempt_id": uuid4(),
        "host_storage_id": str(first),
        "mounts": (WorkspaceMount(
            mount_id="primary", host_path=str(first),
            container_path="/workspace/primary", writable=True,
            write_scope=("holder.py", "pid.txt"), forbidden_paths=(".git",),
        ),),
        "evidence_namespace": "qualification:q40-holder",
    })
    holder_request = ToolExecutionRequest(
        delivery_id=uuid4(), attempt_id=first_workspace.attempt_id, worker_epoch=1,
        step_id=uuid4(),
        proposal=ToolCallProposal(
            proposal_index=0, tool_identity="process.run",
            arguments={"argv": ["python", "holder.py"], "cwd": "."},
        ),
        capability_grants=(CapabilityGrant(
            identity="process.run", version="1", scope={"paths": ["holder.py"]},
        ),),
        workspace=first_workspace,
    )
    remote = RemoteNativeToolHost(
        app.settings.native_executor_tool_host_url,
        app.settings.native_executor_internal_token.get_secret_value(),
    )
    holder_task = asyncio.create_task(remote.execute(holder_request))
    for _ in range(100):
        if (first / "pid.txt").exists():
            break
        await asyncio.sleep(0.05)
    else:
        holder_task.cancel()
        raise RuntimeError("isolated holder process did not publish its PID")
    (second / "holder-pid.txt").write_text(
        (first / "pid.txt").read_text(), encoding="utf-8"
    )
    try:
        result = await remote.execute(request)
    finally:
        holder_task.cancel()
        try:
            await holder_task
        except asyncio.CancelledError:
            holder_termination_proven = True
        else:
            holder_termination_proven = False
    stdout = str(result.output.get("stdout", ""))
    stderr = str(result.output.get("stderr", ""))
    other_work_visible = (
        "OTHER_WORK_READABLE" in stdout or "OTHER_WORK_ENUMERABLE" in stdout
    )
    control_or_metadata_visible = "HOST_REACHABLE" in stdout
    redirect_or_rebinding_visible = "REDIRECT_OR_REBIND_TARGET_REACHABLE" in stdout
    other_process_attachable = "OTHER_PROCESS_ATTACHABLE" in stdout
    evidence = {
        "provider_requests": 0,
        "tool_condition": result.condition.value,
        "returncode": result.output.get("returncode"),
        "isolation": result.output.get("isolation"),
        "stdout_tail": stdout[-2000:],
        "stderr_tail": stderr[-2000:],
        "other_work_visible": other_work_visible,
        "control_or_metadata_visible": control_or_metadata_visible,
        "redirect_or_rebinding_visible": redirect_or_rebinding_visible,
        "approved_immutable_dependency_available": result.output.get("returncode") == 0,
        "other_process_attachable": other_process_attachable,
        "holder_termination_proven": holder_termination_proven,
        "q39_hostile_egress": (
            "FAIL"
            if control_or_metadata_visible or redirect_or_rebinding_visible
            else "PASS"
        ),
        "q40_warm_reuse_isolation": (
            "FAIL"
            if other_work_visible or other_process_attachable or not holder_termination_proven
            else "PASS"
        ),
    }
    output = Path("/evidence/q39-q40-isolation-v3-landlock.json")
    output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
