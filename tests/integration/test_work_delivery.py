"""Real PostgreSQL/Git proof of Work -> assets -> SPG -> delivery boundaries."""
from io import BytesIO
from uuid import UUID, uuid4
from zipfile import ZipFile
import pytest

from test_wic_governed_work_admission import clean_schema, _GeneralProductDesignCapability, _GuidedDesignSemanticCapability, _SchedulingOrchestrator
from spg.api.dto import SharedUnderstandingResponse
from spg.application.assets import RepositoryAssetService
from spg.application.delivery import DeliveryApplicationService, read_artifact
from spg.application.interaction import WorkInteractionService
from spg.application.work import WorkApplicationService
from spg.application.runtime import RuntimeService
from spg.application.steering_bootstrap import SteeringBootstrapService
from spg.application.steering_driver import PlanSteeringDriver
from spg.application.semantic_steps import SemanticStepApplicationService
from spg.domain.planning import PlannedArtifactOperation
from spg.domain.assets import RepositoryIntakeRequest, AssetScopeAdmissionRequest
from spg.domain.delivery import DeliveryTargetKind, DeliveryTargetRequest, HumanAcceptanceRequest, HumanAcceptanceDecision
from spg.domain.execution import ProviderReportedOutcome
from spg.domain.product import AttentionAction, AttentionKind, AttentionResolutionRequest, ProductInvariantViolation
from spg.domain.runtime import RuntimeInvariantViolation
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.product_store import ProductStore
from spg.providers.deterministic_executor import DeterministicTestExecutor, DeterministicExecutionSpecification, DeterministicFileOperation, DeterministicFileOperationType
from spg.providers.contract_verifier import ContractDrivenRepositoryVerifier

pytestmark = pytest.mark.postgresql


def admit_empty(database, tmp_path):
    interactions = WorkInteractionService(database, capability=_GeneralProductDesignCapability())
    interaction = interactions.create_interaction(human_identity="human:test")
    ready = interactions.append_and_assess(interaction.id, "我要开发一个运营管理平台。先形成可验证的设计文档。", human_identity="human:test")
    work = WorkApplicationService(database, workspace_root=tmp_path / "workspaces")
    projection = work.admit_interaction_work(interaction.id, assessment_id=ready.latest_assessment.id,
        basis_fingerprint=ready.latest_assessment.basis_fingerprint, authority_identity="human:test", use_default_resource=False)
    response = SharedUnderstandingResponse.from_projection(interactions.get_shared_understanding(interaction.id))
    assert response.governed_revision.engineering_resource_id is None
    return work, projection


def create_asset(assets, title):
    request = RepositoryIntakeRequest(request_id=uuid4(), title=title, description="Synthetic acceptance repository", authority_identity="human:test")
    result = assets.intake(request)
    assert assets.intake(request) == result
    return result


def bind(work, projection, observation):
    return work.admit_asset_scope(projection.work_id, AssetScopeAdmissionRequest(resource_id=UUID(observation["resource_id"]),
        expected_work_revision_id=projection.current_work_reality_revision_id, observation_fingerprint=observation["fingerprint"],
        authority_identity="human:test", rationale="Bind this exact repository observation for production"), observation)


class DesignCapability(_GuidedDesignSemanticCapability):
    def execute(self, input):
        result = super().execute(input)
        if result.proposed_production is not None:
            proposal = result.proposed_production
            target = proposal.artifact_targets[0].model_copy(update={"path": "docs/design.md", "operation": PlannedArtifactOperation.CREATE})
            result = result.model_copy(update={"proposed_production": proposal.model_copy(update={"artifact_targets": (target,)})})
        return result


def test_empty_work_then_two_repository_namespaces(postgres_database, tmp_path):
    work, projection = admit_empty(postgres_database, tmp_path)
    assert projection.engineering_scope.bindings == ()
    SteeringBootstrapService(postgres_database).bootstrap(projection.work_id)
    semantic = SemanticStepApplicationService(postgres_database, DesignCapability())
    assert semantic.assemble_input(projection.work_id).engineering_resource_id is None
    class NeedsClarification(DesignCapability):
        def execute(self, input):
            return super().execute(input).model_copy(update={
                "completion_claimed": False, "unresolved_questions": ("Which repository should hold the design?",),
                "human_attention_recommendation": "Select the repository for this Work",
            })
    driver = PlanSteeringDriver(postgres_database, work, _SchedulingOrchestrator(), semantic_capability=NeedsClarification())
    driver.activate(projection.work_id)
    assert work.list_attention(work_id=projection.work_id)
    driver.shutdown()
    assets = RepositoryAssetService(postgres_database, tmp_path / "assets", tmp_path / "imports")
    a, b = create_asset(assets, "A"), create_asset(assets, "B")
    projection = bind(work, projection, a)
    assert not work.list_attention(work_id=projection.work_id)
    first_revision = projection.current_work_reality_revision_id
    projection = bind(work, projection, b)
    assert len(projection.engineering_scope.bindings) == 2
    with postgres_database.unit_of_work() as uow:
        product, runtime = ProductStore(uow.session), RuntimeStore(uow.session)
        assert product.resource_for_work(projection.work_id).id == UUID(b["resource_id"])
        revision = product.work_reality_revision(first_revision)
        assert revision.engineering_resource_id == UUID(a["resource_id"])
        interaction_id = revision.source_interaction_id
        pa = runtime.current_pointer(repository_identity=a["repository_identity"], repository_ref=a["repository_ref"])
        pb = runtime.current_pointer(repository_identity=b["repository_identity"], repository_ref=b["repository_ref"])
        assert pa.snapshot_id != pb.snapshot_id
        with pytest.raises(RuntimeInvariantViolation, match="explicit"):
            runtime.current_pointer()
        with pytest.raises(RuntimeInvariantViolation, match="conflicts"):
            runtime.current_pointer(source_baseline_id=pa.snapshot_id, repository_ref="refs/heads/wrong")
        with pytest.raises(RuntimeInvariantViolation, match="cross repository"):
            runtime.update_baseline_pointer(pa.version, pb.snapshot_id, expected_snapshot_id=pa.snapshot_id)

    response = SharedUnderstandingResponse.from_projection(WorkInteractionService(postgres_database, capability=_GeneralProductDesignCapability()).get_shared_understanding(interaction_id))
    assert response.governed_revision.source_kind == "ASSET_SCOPE_ADMISSION"
    assert response.governed_revision.source_assessment_id is None


def test_unconfirmed_remote_repository_remains_nonblocking_asset_candidate(
    postgres_database,
    tmp_path,
    monkeypatch,
):
    work, projection = admit_empty(postgres_database, tmp_path)
    assets = RepositoryAssetService(
        postgres_database,
        tmp_path / "assets",
        tmp_path / "imports",
    )
    original_git = assets._git
    clone_arguments = []

    def inaccessible(path, *args):
        if args and args[0] == "clone":
            clone_arguments.append(args)
            raise ProductInvariantViolation("synthetic access denial")
        return original_git(path, *args)

    monkeypatch.setattr(assets, "_git", inaccessible)
    request = RepositoryIntakeRequest(
        request_id=uuid4(),
        source="https://example.invalid/private/repository.git",
        title="Unconfirmed external repository",
        description="Candidate input; access has not been authorized",
        authority_identity="human:test",
    )

    candidate = assets.intake(request)

    assert assets.intake(request) == candidate
    assert candidate["condition"] == "UNRESOLVED"
    assert clone_arguments == [(
        "clone",
        "--no-local",
        "--single-branch",
        "--",
        request.source,
        str(tmp_path / "assets" / str(request.request_id)),
    )]
    assert candidate["resource_id"] is None
    assert set(candidate["authorization"].values()) == {"UNKNOWN"}
    assert "Work may continue" in candidate["message"]
    assert assets.list_assets(work_id=projection.work_id) == [
        {**candidate, "bound": False, "selected_for_production": False}
    ]
    assert work.get_work(projection.work_id).engineering_scope.bindings == ()


def test_design_to_trusted_delivery_and_explicit_acceptance(postgres_database, tmp_path):
    work, projection = admit_empty(postgres_database, tmp_path)
    assets = RepositoryAssetService(postgres_database, tmp_path / "assets", tmp_path / "imports")
    observation = create_asset(assets, "Document package")
    projection = bind(work, projection, observation)
    # A second repository must not interfere with any phase of this Work.
    unrelated = create_asset(assets, "Unrelated repository")
    unrelated_before = RuntimeService(postgres_database).current_baseline(repository_identity=unrelated["repository_identity"], repository_ref=unrelated["repository_ref"])
    target_path = "docs/design.md"
    executor = DeterministicTestExecutor(DeterministicExecutionSpecification(operations=(DeterministicFileOperation(
        operation=DeterministicFileOperationType.CREATE, repository_relative_path=target_path,
        content="# Operations platform design\n\nUsers: operations staff.\n\nScope: reviewed design package.\n"),), reported_outcome=ProviderReportedOutcome.SUCCESS))
    service = WorkApplicationService(postgres_database, workspace_root=tmp_path / "workspaces", executor=executor, verifier=ContractDrivenRepositoryVerifier(postgres_database))
    SteeringBootstrapService(postgres_database).bootstrap(projection.work_id)
    driver = PlanSteeringDriver(postgres_database, service, _SchedulingOrchestrator(), semantic_capability=DesignCapability())
    driver.activate(projection.work_id)
    attention = service.list_attention(work_id=projection.work_id)
    proposal = next(item for item in attention if item.kind is AttentionKind.PRODUCTION_PROPOSAL_REVIEW)
    service.resolve_attention(proposal.id, AttentionResolutionRequest(action=AttentionAction.APPROVE, authority_identity="human:test"))
    driver.activate(projection.work_id)
    delivery = DeliveryApplicationService(postgres_database)
    delivery.set_target(projection.work_id, DeliveryTargetRequest(kind=DeliveryTargetKind.DOCUMENT_PACKAGE, title="Reviewed design",
        acceptance_criteria=("Inspect the operations design",), authority_identity="human:test"))
    with pytest.raises(ProductInvariantViolation, match="Verification"):
        delivery.publish(projection.work_id)
    for _ in range(20):
        service.advance_work(projection.work_id)
        candidates = [item for item in service.list_attention(work_id=projection.work_id) if item.kind is AttentionKind.CANDIDATE_AUTHORIZATION]
        if candidates:
            service.resolve_attention(candidates[0].id, AttentionResolutionRequest(action=AttentionAction.AUTHORIZE, authority_identity="human:test"))
        if service.get_work_result(projection.work_id).trusted_result:
            break
    assert service.get_work_result(projection.work_id).trusted_result
    manifest = delivery.publish(projection.work_id)
    assert delivery.publish(projection.work_id).id == manifest.id
    assert delivery.view(projection.work_id)["deliveries"][0]["acceptance"] is None
    content = delivery.artifact(projection.work_id, manifest.id, target_path)
    assert b"Operations platform" in content
    with ZipFile(BytesIO(delivery.package(projection.work_id, manifest.id))) as archive:
        assert archive.read("artifacts/" + target_path) == content
    with pytest.raises(ProductInvariantViolation, match="fingerprint"):
        delivery.decide(projection.work_id, manifest.id, HumanAcceptanceRequest(manifest_fingerprint="0"*64,
            decision=HumanAcceptanceDecision.ACCEPT, authority_identity="human:test", rationale="Reviewed"))
    accepted = delivery.decide(projection.work_id, manifest.id, HumanAcceptanceRequest(manifest_fingerprint=manifest.fingerprint,
        decision=HumanAcceptanceDecision.ACCEPT, authority_identity="human:test", rationale="Reviewed exact design package"))
    assert accepted.decision is HumanAcceptanceDecision.ACCEPT
    assert RuntimeService(postgres_database).current_baseline(repository_identity=unrelated["repository_identity"], repository_ref=unrelated["repository_ref"]).id == unrelated_before.id
    driver.shutdown()


def test_recovery_resolves_exact_namespace_with_another_repository_present(postgres_database, tmp_path):
    import test_s5b_recovery_reconciliation as recovery_fixture
    from spg.application.runtime_commit import RuntimeCommitService
    from spg.domain.integration import RepositoryEffectState
    from spg.infrastructure.persistence.runtime_schema import repository_integration_effects
    from sqlalchemy import select

    repository = recovery_fixture.s5a.git_repository.__wrapped__(tmp_path)
    facts = recovery_fixture._facts(postgres_database, repository, tmp_path, mode="prepared-proposed")
    assets = RepositoryAssetService(postgres_database, tmp_path / "assets", tmp_path / "imports")
    other = create_asset(assets, "B remains independent during A recovery")
    runtime = RuntimeService(postgres_database)
    before = runtime.current_baseline(repository_identity=other["repository_identity"], repository_ref=other["repository_ref"])
    # A's exact prior assessment remains actionable after unrelated B is bootstrapped.
    facts.service.record_external_convergence(facts.request)
    with postgres_database.unit_of_work() as uow:
        state = uow.session.execute(select(repository_integration_effects.c.state).where(repository_integration_effects.c.id == facts.repository.effect.id)).scalar_one()
    assert state == RepositoryEffectState.CONVERGED.value
    result = RuntimeCommitService(postgres_database).commit_runtime_candidate(facts.repository.runtime_commit_request)
    assert result is not None
    assert runtime.current_baseline(source_baseline_id=facts.repository.candidate.source_baseline_id).id != facts.repository.candidate.source_baseline_id
    assert runtime.current_baseline(repository_identity=other["repository_identity"], repository_ref=other["repository_ref"]).id == before.id
    assert facts.git.mutation_calls == 0


def test_namespace_migration_preserves_legacy_baseline_and_refuses_lossy_downgrade(postgres_database, tmp_path):
    from alembic import command
    from alembic.config import Config
    from pathlib import Path
    from sqlalchemy import text
    import os
    import test_s5a_recovery_assessment as fixtures
    from spg.domain.runtime import BootstrapRequest

    repository = fixtures.git_repository.__wrapped__(tmp_path)
    runtime = RuntimeService(postgres_database)
    baseline = runtime.bootstrap_trusted_baseline(BootstrapRequest(repository_path=repository,
        repository_identity="test://legacy-migration", repository_ref="refs/heads/main",
        authority_identity="human:test", scope={"proof": "legacy baseline preservation"})).snapshot
    before = baseline.model_dump(mode="json")
    os.environ["SPG_DATABASE_URL"] = postgres_database.engine.url.render_as_string(hide_password=False)
    config = Config(Path(__file__).resolve().parents[2] / "alembic.ini")
    command.downgrade(config, "20260909_29")
    with postgres_database.engine.connect() as connection:
        assert connection.execute(text("SELECT singleton_id FROM current_trusted_baseline_pointer")).scalar_one() == 1
    command.upgrade(config, "head")
    assert runtime.current_baseline().model_dump(mode="json") == before
    assets = RepositoryAssetService(postgres_database, tmp_path / "assets", tmp_path / "imports")
    create_asset(assets, "Second namespace after legacy upgrade")
    with pytest.raises(RuntimeError, match="Cannot collapse multiple"):
        command.downgrade(config, "20260909_29")
    # PostgreSQL rolls back the entire failed schema migration transaction.
    assert runtime.current_baseline(repository_identity="test://legacy-migration", repository_ref="refs/heads/main").model_dump(mode="json") == before
