"""Q43 real Tool Host receipt-spool execute/restart/query probe."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID, uuid4

from spg.config import Settings
from spg.domain.native_execution import (
    CapabilityGrant, ToolCallProposal, ToolExecutionRequest,
    WorkspaceManifest, WorkspaceMount, canonical_digest,
)
from spg.infrastructure.executor_runtime.remote_tool_host import RemoteNativeToolHost


def manifest(root: Path, attempt_id: UUID) -> WorkspaceManifest:
    return WorkspaceManifest(
        workspace_id=uuid4(), work_id=uuid4(), pwu_id=uuid4(), attempt_id=attempt_id,
        source_vector_digest=canonical_digest({"q43": "spool"}),
        host_storage_id=str(root),
        environment_profile_digest=canonical_digest({"profile": "q43"}),
        mounts=(WorkspaceMount(
            mount_id="primary", host_path=str(root), container_path="/workspace/primary",
            writable=True, write_scope=("result.txt",), forbidden_paths=(".git",),
        ),),
        evidence_namespace="qualification:q43", retention_policy="probe-owned",
    )


async def main() -> None:
    parser=argparse.ArgumentParser();parser.add_argument("mode",choices=("execute","query"))
    parser.add_argument("--evidence", default="/evidence/q43-tool-spool.json")
    parser.add_argument("--context", default="tool-host-restart")
    args=parser.parse_args();settings=Settings()
    evidence=Path(args.evidence)
    remote=RemoteNativeToolHost(
        settings.native_executor_tool_host_url,
        settings.native_executor_internal_token.get_secret_value(),
    )
    if args.mode == "execute":
        root=settings.native_executor_workspace_root/"q43-tool-spool";root.mkdir(parents=True,exist_ok=True)
        attempt_id=uuid4();delivery_id=uuid4()
        request=ToolExecutionRequest(
            delivery_id=delivery_id, attempt_id=attempt_id, worker_epoch=1, step_id=uuid4(),
            proposal=ToolCallProposal(
                proposal_index=0, tool_identity="file.write",
                arguments={"path":"result.txt","content":"Q43_SPOOLED"},
            ),
            capability_grants=(CapabilityGrant(
                identity="file.write",version="1",scope={"paths":["result.txt"]},
            ),),
            workspace=manifest(root,attempt_id),
        )
        result=await remote.execute(request)
        payload={
            "delivery_id":str(delivery_id),"attempt_id":str(attempt_id),
            "workspace":str(root),"execute_condition":result.condition.value,
            "execute_digest":result.output_digest,
            "qualification_context":args.context,
        }
        evidence.write_text(json.dumps(payload,indent=2)+"\n")
        print(json.dumps(payload,sort_keys=True));return
    payload=json.loads(evidence.read_text());delivery_id=UUID(payload["delivery_id"])
    receipt=await remote.receipt(delivery_id)
    content=(Path(payload["workspace"])/"result.txt").read_text()
    payload.update({
        "after_restart_receipt_found":receipt is not None,
        "after_restart_digest":receipt.output_digest if receipt else None,
        "workspace_content_preserved":content=="Q43_SPOOLED",
        "provider_requests":0,
        "q43_tool_spool":"PASS" if receipt and receipt.output_digest==payload["execute_digest"] and content=="Q43_SPOOLED" else "FAIL",
    })
    evidence.write_text(json.dumps(payload,indent=2)+"\n")
    print(json.dumps(payload,sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
