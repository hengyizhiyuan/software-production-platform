"""Persisted capability resolution, scope isolation, and resumable gaps."""

import os
import subprocess
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import delete

from spg.application.connectors import ConnectorResolver
from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.application.native_connector_qualification import NativeConnectorQualificationService
from spg.application.runtime import RuntimeService
from spg.application.work import WorkApplicationService
from spg.domain.connectors import (
    CapabilityRequirement,
    CapabilityScope,
    ConnectorAvailability,
    ConnectorMaturity,
    ExecutableCapability,
    SideEffectLevel,
)
from spg.domain.native_execution import SourceMember, SourceVector, WorkspaceManifest, WorkspaceMount
from spg.domain.runtime import BootstrapRequest
from spg.domain.production_environment import (
    EnvironmentCommandObservation, EnvironmentCommandResult,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.connector_schema import capability_gaps, connector_capabilities
from spg.infrastructure.persistence.product_schema import product_works


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_missing_quality_connector_qualifies_and_resumes_same_work(
    postgres_database: Database, tmp_path: Path,
) -> None:
    repository = tmp_path / "qualification-repository"
    repository.mkdir()
    for argv in (
        ("git", "init", "-b", "main"),
        ("git", "config", "user.name", "Connector Test"),
        ("git", "config", "user.email", "connector@example.invalid"),
    ):
        subprocess.run(argv, cwd=repository, check=True, capture_output=True)
    (repository / "README.md").write_text("# Qualification\n", encoding="utf-8")
    subprocess.run(("git", "add", "."), cwd=repository, check=True, capture_output=True)
    subprocess.run(("git", "commit", "-m", "baseline"), cwd=repository, check=True, capture_output=True)
    revision = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=repository, text=True).strip()
    tree = subprocess.check_output(("git", "rev-parse", "HEAD^{tree}"), cwd=repository, text=True).strip()
    baseline = RuntimeService(postgres_database).bootstrap_trusted_baseline(BootstrapRequest(
        repository_path=repository,
        repository_identity=f"repo:connector-qualification:{uuid4()}",
        repository_ref="refs/heads/main",
        authority_identity="human:qualifier",
        scope={"purpose": "connector-qualification-test"},
    )).snapshot
    work_id = WorkApplicationService(postgres_database, workspace_root=tmp_path).submit_work(
        "Run a bounded quality check"
    ).work_id
    requirement = CapabilityRequirement(
        capability_id="quality.run", work_id=work_id, user_id="human:qualifier",
        operation_ref="task-contract:quality-check",
        resume_point={"pwu_id": str(uuid4()), "attempt_id": str(uuid4())},
    )
    resolver = ConnectorResolver(postgres_database)
    candidate = resolver.propose_generic_candidate(requirement)
    assert candidate is not None
    assert resolver.gaps_for_work(work_id)[0]["condition"] == "OPEN"

    class LocalSandboxProvider:
        provider_identity = "test:connector-sandbox"

        def execute_observed(self, _handle, command):
            assert command.working_directory == "/workspace/primary"
            completed = subprocess.run(command.argv, cwd=repository, capture_output=True, text=True)
            return EnvironmentCommandObservation(
                result=EnvironmentCommandResult(
                    command=command, exit_code=completed.returncode,
                    stdout_reference=f"sha256:{sha256(completed.stdout.encode()).hexdigest()}",
                    stderr_reference=f"sha256:{sha256(completed.stderr.encode()).hexdigest()}",
                ),
                stdout=completed.stdout, stderr=completed.stderr,
            )

    source_vector = SourceVector(members=(SourceMember(
        mount_id="primary", repository_identity=baseline.repository_identity,
        source_baseline_ref=baseline.repository_ref,
        source_commit_oid=revision, source_tree_oid=tree,
        container_path="/workspace/primary", read_scope=(), write_scope=(),
        forbidden_paths=(".git",), integration_target=baseline.repository_ref,
    ),))
    manifest = WorkspaceManifest(
        workspace_id=uuid4(), work_id=work_id, pwu_id=uuid4(), attempt_id=uuid4(),
        source_vector_digest=source_vector.digest,
        host_storage_id=str(repository), environment_profile_digest="0" * 64,
        mounts=(WorkspaceMount(
            mount_id="primary", host_path=str(repository),
            container_path="/workspace/primary", writable=True,
            write_scope=(), forbidden_paths=(".git",),
        ),),
        service_resources=(
            f"production-environment:{uuid4()}",
            f"production-workspace:{uuid4()}",
            "production-environment-provider:test:connector-sandbox",
            "production-environment-handle:local-sandbox",
        ),
        evidence_namespace="connector-qualification-test", retention_policy="test",
    )
    qualified = NativeConnectorQualificationService(
        postgres_database, NativeExecutorRuntimeService(postgres_database),
        provider=LocalSandboxProvider(), checkpoint_root=tmp_path / "checkpoints",
    ).qualify(
        candidate, source_baseline_id=baseline.id,
        source_vector=source_vector, workspace=manifest,
        authority_identity="human:qualifier", admitted_permissions=(),
    )
    assert qualified
    assert resolver.resolve(requirement).executable
    assert resolver.gaps_for_work(work_id)[0]["condition"] == "RESOLVED"
    assert not resolver.resolve(requirement.model_copy(update={
        "work_id": uuid4(), "user_id": "human:other",
    }), record_gap=False).executable


def test_work_user_scope_gap_resume_and_external_authority(
    postgres_database: Database,
    tmp_path: Path,
) -> None:
    previous_url = os.environ.get("SPG_DATABASE_URL")
    os.environ["SPG_DATABASE_URL"] = postgres_database.engine.url.render_as_string(
        hide_password=False
    )
    try:
        command.upgrade(Config(PROJECT_ROOT / "alembic.ini"), "head")
    finally:
        if previous_url is None:
            os.environ.pop("SPG_DATABASE_URL", None)
        else:
            os.environ["SPG_DATABASE_URL"] = previous_url

    works = WorkApplicationService(postgres_database, workspace_root=tmp_path)
    first = works.submit_work("Inspect one repository with a learned connector")
    second = works.submit_work("Inspect another repository")
    resolver = ConnectorResolver(postgres_database)

    def requirement(work_id, user_id):
        return CapabilityRequirement(
            capability_id="custom.repository.inspect",
            work_id=work_id,
            user_id=user_id,
            operation_ref="task-contract:inspect-repository",
            resume_point={"current_step": "inspect", "workspace": "primary"},
        )

    def learned(scope, owner_id, capability_id, version="1", effect=SideEffectLevel.READ):
        return ExecutableCapability(
            capability_id=capability_id,
            connector_id="learned:bounded-native-process",
            capability_family="custom",
            operation="inspect",
            scope=scope,
            owner_id=owner_id,
            maturity=ConnectorMaturity.PROVISIONAL,
            availability=ConnectorAvailability.AVAILABLE,
            permissions_required=("work.command.execute",),
            side_effect_level=effect,
            execution_provider="native-tool:process.run",
            version=version,
            provenance=("work-verification:test",),
            created_from_work=first.work_id,
            verification_evidence=("sandbox-verification:passed",),
        )

    try:
        quality_requirement = CapabilityRequirement(
            capability_id="quality.run",
            work_id=first.work_id,
            user_id="user:A",
            operation_ref="task-contract:quality-check",
            resume_point={"pwu_id": "preserved"},
        )
        candidate = resolver.propose_generic_candidate(quality_requirement)
        assert candidate is not None
        assert candidate.execution_provider == "native-tool:process.run"
        assert resolver.gaps_for_work(first.work_id)[0]["resume_point"]["pwu_id"] == "preserved"
        with pytest.raises(Exception):
            resolver.admit_qualified_candidate(candidate, qualification_attempt_id=uuid4())
        assert resolver.resolve(quality_requirement, record_gap=False).executable is False

        missing = resolver.resolve(requirement(first.work_id, "user:A"))
        assert missing.executable is False
        assert missing.gap_id is not None
        assert next(
            gap for gap in resolver.gaps_for_work(first.work_id)
            if gap["capability_id"] == "custom.repository.inspect"
        )["resume_point"]["current_step"] == "inspect"

        resolver.register_learned(learned(CapabilityScope.WORK, str(first.work_id), "custom.repository.inspect"))
        assert resolver.resolve(requirement(first.work_id, "user:A")).executable is True
        assert "custom.repository.inspect" in {
            item.capability_id for item in resolver.visible_capabilities(first.work_id, "user:A")
            if item.availability is ConnectorAvailability.AVAILABLE
        }
        assert next(
            gap for gap in resolver.gaps_for_work(first.work_id)
            if gap["capability_id"] == "custom.repository.inspect"
        )["condition"] == "RESOLVED"
        assert resolver.resolve(requirement(second.work_id, "user:B"), record_gap=False).executable is False
        assert "custom.repository.inspect" not in {
            item.capability_id for item in resolver.visible_capabilities(second.work_id, "user:B")
        }
        with pytest.raises(ValueError, match="real Native checkpoint identity"):
            resolver.retain_successful_work_capability_for_user(
                requirement(first.work_id, "user:A"),
                successful_execution_evidence="native-checkpoint:verified-result",
            )
        assert resolver.resolve(requirement(second.work_id, "user:A"), record_gap=False).executable is False
        assert resolver.resolve(requirement(second.work_id, "user:B"), record_gap=False).executable is False

        resolver.register_learned(learned(CapabilityScope.USER, "user:A", "custom.user.inspect"))
        user_requirement = requirement(second.work_id, "user:A").model_copy(update={"capability_id": "custom.user.inspect"})
        other_user = user_requirement.model_copy(update={"user_id": "user:B"})
        assert resolver.resolve(user_requirement, record_gap=False).executable is True
        assert resolver.resolve(other_user, record_gap=False).executable is False
        assert "custom.user.inspect" not in {
            item.capability_id for item in resolver.visible_capabilities(second.work_id, "user:B")
        }

        resolver.register_learned(learned(
            CapabilityScope.USER, "user:A", "custom.remote.write", effect=SideEffectLevel.EXTERNAL_WRITE,
        ))
        remote = user_requirement.model_copy(update={"capability_id": "custom.remote.write"})
        assert resolver.resolve(remote, record_gap=False).executable is True
        with pytest.raises(ValueError, match="separate Work authorization"):
            resolver.require_local_execution(remote)
    finally:
        with postgres_database.unit_of_work() as uow:
            uow.session.execute(delete(capability_gaps).where(capability_gaps.c.work_id.in_((first.work_id, second.work_id))))
            uow.session.execute(delete(connector_capabilities).where(connector_capabilities.c.owner_id.in_((str(first.work_id), "user:A"))))
            uow.session.execute(delete(product_works).where(product_works.c.id.in_((first.work_id, second.work_id))))
            uow.commit()
