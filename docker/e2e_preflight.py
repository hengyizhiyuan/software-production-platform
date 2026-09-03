"""Safe in-container Dedicated Executor Codex binding preflight (zero Turns)."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import tempfile
from uuid import uuid4

from spg.domain.execution import ExecutorDispatchRequest
from spg.domain.materialization import (
    MaterializedContextArtifact,
    MaterializedExecutionInputRecord,
)
from spg.domain.preparation import (
    ContextSemanticRole,
    ExecutorBinding,
    PreparedExecutionRequest,
    WorkspaceBinding,
)
from spg.infrastructure.codex_executor_binding import CODEX_STATE_RUNTIME_BINDING
from spg.infrastructure.executor_boundary import (
    DedicatedExecutorClient,
    SubprocessExecutorTransport,
)


def _run(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("preflight Git setup failed")
    return result.stdout.strip()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="spg-e2e-preflight-") as root_value:
        root = Path(root_value)
        repository = root / "repository"
        workspace = root / "workspace"
        repository.mkdir()
        _run(repository, "init", "-b", "main")
        _run(repository, "config", "user.name", "SPG Preflight")
        _run(repository, "config", "user.email", "spg-preflight@example.invalid")
        (repository / "AI_context.md").write_text("preflight context\n", encoding="utf-8")
        _run(repository, "add", "AI_context.md")
        _run(repository, "commit", "-m", "preflight baseline")
        revision = _run(repository, "rev-parse", "HEAD")
        _run(repository, "worktree", "add", "--detach", str(workspace), revision)

        attempt_id = uuid4()
        run_id = uuid4()
        work_unit_id = uuid4()
        plan_id = uuid4()
        baseline_id = uuid4()
        package_id = uuid4()
        binding = ExecutorBinding(
            binding_ref="binding:codex-sdk-preflight",
            capability_identity="capability:executor",
            profile_identity="profile:local-docker-codex-e2e",
        )
        prepared = PreparedExecutionRequest(
            attempt_id=attempt_id,
            generation=1,
            production_run_id=run_id,
            work_unit_id=work_unit_id,
            plan_revision_id=plan_id,
            source_baseline_id=baseline_id,
            context_package_id=package_id,
            context_package_version=1,
            completion_contract_fingerprint="preflight-contract",
            executor_binding=binding,
            workspace=WorkspaceBinding(
                workspace_identity=f"attempt-worktree:{attempt_id}",
                workspace_path=workspace,
                repository_identity="preflight://local-e2e",
                repository_path=repository,
                source_revision=revision,
            ),
        )
        materialized = MaterializedExecutionInputRecord(
            id=uuid4(),
            attempt_id=attempt_id,
            generation=1,
            production_run_id=run_id,
            work_unit_id=work_unit_id,
            plan_revision_id=plan_id,
            source_baseline_id=baseline_id,
            context_package_id=package_id,
            context_package_version=1,
            context_package_content_fingerprint="preflight-context",
            completion_contract_fingerprint="preflight-contract",
            prepared_execution_request=prepared,
            instruction_content="No-Turn binding preflight only",
            context_projection=(
                MaterializedContextArtifact(
                    semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                    repository_relative_path="AI_context.md",
                    source_revision=revision,
                    blob_fingerprint="preflight-blob",
                    content="preflight context\n",
                ),
            ),
            input_fingerprint="preflight-input",
            created_at=datetime.now(UTC),
        )
        response = DedicatedExecutorClient(
            materialized,
            transport=SubprocessExecutorTransport(
                provider_binding=CODEX_STATE_RUNTIME_BINDING,
                timeout_seconds=60,
            ),
        ).preflight_provider_binding(
            ExecutorDispatchRequest(dispatch_id=uuid4(), execution=prepared)
        )
        safe = {
            "binding_status": response.binding_status,
            "authentication_readiness": response.authentication_readiness,
            "provider_turn_started": response.provider_turn_started,
            "provider_outcome": response.provider_outcome.value,
            "sdk_version": response.sdk_version,
            "adapter_identity": response.adapter_identity,
            "spg_database_configuration_present": response.metadata.get(
                "spg_database_configuration_present"
            ),
            "authentication_secret_inspected": response.metadata.get(
                "authentication_secret_inspected"
            ),
            "codex_home_writable": response.metadata.get("codex_home_writable"),
            "state_runtime_initialization": response.metadata.get(
                "state_runtime_initialization"
            ),
            "sqlite_state_artifact_present": response.metadata.get(
                "sqlite_state_artifact_present"
            ),
            "provider_threads_started": response.metadata.get(
                "provider_threads_started"
            ),
            "provider_turns_started": response.metadata.get(
                "provider_turns_started"
            ),
        }
        print(json.dumps(safe, sort_keys=True))
        return 0 if (
            response.binding_status == "READY_FOR_THREAD_CREATION"
            and response.authentication_readiness == "AVAILABLE"
            and response.provider_turn_started is False
            and response.metadata.get("codex_home_writable") is True
            and response.metadata.get("state_runtime_initialization")
            == "APP_SERVER_INITIALIZED"
            and response.metadata.get("provider_threads_started") == 0
            and response.metadata.get("provider_turns_started") == 0
        ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
