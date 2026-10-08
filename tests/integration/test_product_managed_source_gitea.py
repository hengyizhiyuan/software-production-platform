"""Real Gitea and PostgreSQL proof of Product source continuity."""
from io import BytesIO
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import time
from uuid import UUID, uuid4
from zipfile import ZipFile

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select, update

from spg.api.http import create_http_application
from spg.application.bootstrap import Application
from spg.application.delivery import DeliveryApplicationService
from spg.application.product_assets import ProductAssetService
from spg.application.assets import RepositoryAssetService
from spg.application.product_managed_source import ProductManagedSourceService, _git
from spg.application.decision_context import lineage_for_work_task
from spg.application.work import WorkApplicationService
from spg.application.interaction import WorkInteractionService
from spg.application.production_admission import ProductionAdmissionTrigger
from spg.config import Settings
from spg.domain.delivery import (
    DeliveryTargetKind, DeliveryTargetRequest, HumanAcceptanceDecision,
    HumanAcceptanceRequest,
)
from spg.domain.assets import RepositoryIntakeRequest
from spg.domain.execution import ProviderReportedOutcome
from spg.domain.product import (
    AttentionAction, AttentionKind, AttentionResolutionRequest,
    ProductInvariantViolation, WorkRefinementRequest, WorkStatus,
)
from spg.infrastructure.managed_source_provider import GiteaManagedSourceProvider, ManagedSourceError
from spg.infrastructure.persistence import product_tables, runtime_tables
from spg.infrastructure.persistence.github_delivery_schema import remote_delivery_authorizations, remote_delivery_receipts
from spg.infrastructure.persistence.product_schema import product_works, work_source_bases
from spg.infrastructure.persistence.product_schema import product_workspace_interactions
from spg.infrastructure.persistence.product_store import ProductStore
from spg.domain.interaction import WorkTransitionChoice, WorkFocusClassification, WorkImpactDisposition
from tests.integration.test_wic_governed_work_admission import (
    _ReadyCapability, _ActiveCapability, _DeclaredRepositoryIntent,
)
from spg.providers.contract_verifier import ContractDrivenRepositoryVerifier
from spg.providers.deterministic_executor import (
    DeterministicExecutionSpecification, DeterministicFileOperation,
    DeterministicFileOperationType, DeterministicTestExecutor,
)


pytestmark = [pytest.mark.postgresql, pytest.mark.real_container]
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def managed_source_reality(postgres_database, monkeypatch, tmp_path):
    if os.environ.get("SPG_MANAGED_SOURCE_PROVIDER") != "gitea":
        pytest.skip("Real Gitea configuration is required")
    monkeypatch.setenv("SPG_DATABASE_URL", os.environ["SPG_TEST_DATABASE_URL"])
    monkeypatch.setenv("SPG_MANAGED_SOURCE_WORKSPACE_ROOT", str(tmp_path / "managed"))
    command.upgrade(Config(ROOT / "alembic.ini"), "head")
    tables = ", ".join(f'"{table.name}"' for table in (*product_tables, *runtime_tables))
    with postgres_database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {tables} CASCADE")
        connection.exec_driver_sql('TRUNCATE TABLE "managed_repository_sources" CASCADE')
    yield
    with postgres_database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {tables} CASCADE")
        connection.exec_driver_sql('TRUNCATE TABLE "managed_repository_sources" CASCADE')


def _basis(database, work_id):
    with database.unit_of_work() as uow:
        return dict(uow.session.execute(select(work_source_bases).where(
            work_source_bases.c.work_id == work_id)).mappings().one())


def _scoped_ready(database, product_id):
    interactions = WorkInteractionService(database, capability=_ReadyCapability())
    interaction = interactions.create_interaction(
        human_identity="human:owner", product_id=product_id)
    assessment = interactions.append_and_assess(
        interaction.id, "Build the next bounded Product improvement",
        human_identity="human:owner")
    assert assessment.latest_assessment is not None
    return interactions, assessment


def _admit_scoped(database, assessment):
    return WorkApplicationService(database).admit_interaction_work(
        assessment.interaction.id,
        assessment_id=assessment.latest_assessment.id,
        basis_fingerprint=assessment.latest_assessment.basis_fingerprint,
        authority_identity="human:owner")


def test_product_interaction_forms_exact_v0_work_before_ready(postgres_database):
    product = ProductAssetService(postgres_database).create("human:owner", "Scoped V0")
    product_id = UUID(product["id"])
    accepted = ProductManagedSourceService(postgres_database).describe(
        product_id, "human:owner")["accepted"]
    interactions, assessment = _scoped_ready(postgres_database, product_id)
    with postgres_database.unit_of_work() as uow:
        assert uow.session.execute(select(product_workspace_interactions.c.product_id).where(
            product_workspace_interactions.c.interaction_id == assessment.interaction.id
        )).scalar_one() == product_id
    admitted = _admit_scoped(postgres_database, assessment)
    with postgres_database.unit_of_work() as uow:
        row = uow.session.execute(select(product_works).where(
            product_works.c.id == admitted.work_id)).mappings().one()
    basis = _basis(postgres_database, admitted.work_id)
    assert row["product_id"] == product_id and row["condition"] == "READY"
    assert (basis["product_id"], basis["source_version"],
            basis["source_revision"], basis["source_tree"]) == (
        product_id, 0, accepted["revision"], accepted["tree"])
    assert admitted.engineering_scope is not None
    assert admitted.engineering_scope.bindings[0].resource_id == basis["resource_id"]
    assert interactions.get_shared_understanding(assessment.interaction.id).governed_work_id == admitted.work_id


def test_product_scoped_prework_inherits_context_before_admission(postgres_database):
    product = ProductAssetService(postgres_database).create("human:owner", "Scoped Prework")
    product_id = UUID(product["id"])
    interactions = WorkInteractionService(postgres_database, capability=_ReadyCapability())
    interaction = interactions.create_interaction(human_identity="human:owner",
        product_id=product_id, start_work_context=True)
    with postgres_database.unit_of_work() as uow:
        pre = uow.session.execute(select(product_works).where(
            product_works.c.id == interaction.current_work_id)).mappings().one()
    assert pre["condition"] == "PRE_WORK" and pre["product_id"] == product_id
    ready = interactions.append_and_assess(interaction.id,
        "Build a Product feature", human_identity="human:owner")
    admitted = _admit_scoped(postgres_database, ready)
    assert admitted.work_id == interaction.current_work_id
    assert _basis(postgres_database, admitted.work_id)["product_id"] == product_id


@pytest.mark.parametrize("declared_source", [None, "https://example.invalid/other.git"])
def test_product_source_activates_without_generic_acquisition(postgres_database, declared_source):
    product = ProductAssetService(postgres_database).create("human:owner", "Scoped Activation")
    product_id = UUID(product["id"])
    interactions = WorkInteractionService(postgres_database,
        capability=_DeclaredRepositoryIntent(source=declared_source))
    interaction = interactions.create_interaction(
        human_identity="human:owner", product_id=product_id)
    ready = interactions.append_and_assess(interaction.id,
        "Build a Product improvement using its accepted source. " + (declared_source or ""),
        human_identity="human:owner")
    assert ready.latest_assessment is not None

    class NoGenericAcquisition:
        def latest_attempt_for_work(self, _work_id):
            return None

        def ensure_managed_execution_workspace(self, *_args):
            pytest.fail("Product Work must not acquire an unrelated workspace")

        def record_waiting_source(self, *_args):
            pytest.fail("Product accepted source is already available")

    class Activation:
        work_id = None

        def activate(self, work_id):
            self.work_id = work_id

    activation = Activation()
    ProductionAdmissionTrigger(interactions, WorkApplicationService(postgres_database),
        NoGenericAcquisition(), activation).prepare(
            interaction.id, ready.latest_assessment, ready.records[-1])
    assert activation.work_id is not None
    basis = _basis(postgres_database, activation.work_id)
    assert basis["product_id"] == product_id


def test_product_interaction_uses_current_accepted_vn(postgres_database, tmp_path):
    product = ProductAssetService(postgres_database).create("human:owner", "Scoped Vn")
    product_id = UUID(product["id"])
    _, _, _, accepted = _run_and_accept(postgres_database, product_id,
        "# Scoped Vn\n\nAccepted V1.\n", tmp_path)
    _, assessment = _scoped_ready(postgres_database, product_id)
    admitted = _admit_scoped(postgres_database, assessment)
    basis = _basis(postgres_database, admitted.work_id)
    assert (basis["source_version"], basis["source_revision"], basis["source_tree"]) == (
        1, accepted["accepted"]["revision"], accepted["accepted"]["tree"])


def test_product_transition_retains_scope_and_source(postgres_database):
    product = ProductAssetService(postgres_database).create("human:owner", "Scoped Transition")
    product_id = UUID(product["id"])
    accepted = ProductManagedSourceService(postgres_database).describe(
        product_id, "human:owner")["accepted"]
    _, assessment = _scoped_ready(postgres_database, product_id)
    first = _admit_scoped(postgres_database, assessment)
    active = WorkInteractionService(postgres_database, capability=_ActiveCapability(
        focus=WorkFocusClassification.UNRELATED_NEW_DEMAND,
        impact=WorkImpactDisposition.NEW_WORK_RECOMMENDED,
        motive="Build a separate feature within this Product."))
    pending = active.append_and_assess(assessment.interaction.id,
        "Build a separate feature within this Product.", human_identity="human:owner")
    transition = pending.latest_work_transition
    assert transition is not None
    switched = active.decide_work_transition(assessment.interaction.id,
        transition_id=transition.id, expected_originating_work_id=first.work_id,
        choice=WorkTransitionChoice.START_NEW_WORK,
        authority_identity="human:owner")
    next_id = switched.interaction.current_work_id
    assert next_id is not None and next_id != first.work_id
    with postgres_database.unit_of_work() as uow:
        pre = uow.session.execute(select(product_works).where(
            product_works.c.id == next_id)).mappings().one()
    assert pre["condition"] == "PRE_WORK" and pre["product_id"] == product_id
    restarted = WorkInteractionService(postgres_database, capability=_ReadyCapability())
    next_assessment = restarted.append_and_assess(assessment.interaction.id,
        "Please implement the separate Product feature.", human_identity="human:owner")
    second = _admit_scoped(postgres_database, next_assessment)
    assert second.work_id == next_id
    basis = _basis(postgres_database, second.work_id)
    assert (basis["product_id"], basis["source_version"],
            basis["source_revision"], basis["source_tree"]) == (
        product_id, 0, accepted["revision"], accepted["tree"])


def test_product_source_unavailable_cannot_form_ready_orphan(postgres_database, monkeypatch):
    product = ProductAssetService(postgres_database).create(
        "human:owner", "Unprovisioned Scoped Product", provision_source=False)
    product_id = UUID(product["id"])
    _, assessment = _scoped_ready(postgres_database, product_id)
    with pytest.raises(ProductInvariantViolation, match="accepted source is unavailable"):
        _admit_scoped(postgres_database, assessment)
    with postgres_database.unit_of_work() as uow:
        rows = uow.session.execute(select(product_works.c.condition,
            product_works.c.product_id)).all()
    assert not any(condition == "READY" for condition, _ in rows)
    assert all(owner in {None, product_id} for _, owner in rows)

    provisioned = ProductAssetService(postgres_database).create(
        "human:owner", "Provider Outage Scoped Product")
    _, ready = _scoped_ready(postgres_database, UUID(provisioned["id"]))
    monkeypatch.setenv("SPG_MANAGED_SOURCE_ENDPOINT", "http://127.0.0.1:9")
    with pytest.raises(ManagedSourceError):
        _admit_scoped(postgres_database, ready)
    with postgres_database.unit_of_work() as uow:
        orphan = uow.session.execute(select(product_works.c.id).where(
            product_works.c.condition == "READY",
            product_works.c.product_id.is_(None))).all()
        provisional = uow.session.execute(select(product_works.c.condition).where(
            product_works.c.product_id == UUID(provisioned["id"]))).scalar_one()
    assert orphan == []
    assert provisional == "PRE_WORK"


def test_global_advisory_and_late_binding_protection(postgres_database):
    interaction = WorkInteractionService(postgres_database,
        capability=_ReadyCapability()).create_interaction(human_identity="human:owner")
    with postgres_database.unit_of_work() as uow:
        assert uow.session.execute(select(product_workspace_interactions.c.product_id).where(
            product_workspace_interactions.c.interaction_id == interaction.id
        )).scalar_one_or_none() is None
        assert uow.session.execute(select(func.count()).select_from(product_works)).scalar_one() == 0
    product = ProductAssetService(postgres_database).create("human:owner", "Late Binding Guard")
    legacy = WorkApplicationService(postgres_database).submit_work("Legacy unbound Work")
    with postgres_database.unit_of_work() as uow:
        uow.session.execute(update(product_works).where(
            product_works.c.id == legacy.work_id).values(condition="READY"))
        uow.commit()
    with pytest.raises(ProductInvariantViolation, match="source binding before Work refinement"):
        ProductAssetService(postgres_database).bind_work(
            UUID(product["id"]), legacy.work_id, "human:owner")
    with postgres_database.unit_of_work() as uow:
        assert uow.session.execute(select(product_works.c.product_id).where(
            product_works.c.id == legacy.work_id)).scalar_one_or_none() is None


def _run_and_accept(database, product_id, content, tmp_path):
    executor = DeterministicTestExecutor(DeterministicExecutionSpecification(
        operations=(DeterministicFileOperation(
            operation=DeterministicFileOperationType.MODIFY,
            repository_relative_path="README.md", content=content),),
        reported_outcome=ProviderReportedOutcome.SUCCESS))
    work = WorkApplicationService(database, workspace_root=tmp_path / "workspaces",
        executor=executor, verifier=ContractDrivenRepositoryVerifier(database))
    submitted = work.submit_work("Update README.md in the Product source", product_id=product_id)
    basis = _basis(database, submitted.work_id)
    refined = work.refine_work(submitted.work_id,
        WorkRefinementRequest(code_exact_targets=("README.md",)))
    assert refined.status is WorkStatus.AWAITING_APPROVAL
    assert work.approve_work(submitted.work_id, authority_identity="human:owner").status is WorkStatus.READY
    for _ in range(60):
        projection = work.advance_work(submitted.work_id)
        for attention in work.list_attention(work_id=submitted.work_id):
            if attention.kind is AttentionKind.CANDIDATE_AUTHORIZATION:
                work.resolve_attention(attention.id, AttentionResolutionRequest(
                    action=AttentionAction.AUTHORIZE, authority_identity="human:owner",
                    rationale="Authorize exact verified Candidate"))
        if projection.status is WorkStatus.COMPLETED:
            break
    assert work.get_work_result(submitted.work_id).trusted_result
    delivery = DeliveryApplicationService(database)
    delivery.set_target(submitted.work_id, DeliveryTargetRequest(
        kind=DeliveryTargetKind.DOCUMENT_PACKAGE,
        title="Reviewed source change", acceptance_criteria=("Inspect exact README",),
        authority_identity="human:owner"))
    manifest = delivery.publish(submitted.work_id)
    before = ProductManagedSourceService(database).describe(product_id, "human:owner")
    assert before["accepted"]["revision"] == basis["source_revision"]
    assert any(item["revision"] == manifest.repository_revision for item in before["candidates"])
    acceptance = delivery.decide(submitted.work_id, manifest.id,
        HumanAcceptanceRequest(manifest_fingerprint=manifest.fingerprint,
            decision=HumanAcceptanceDecision.ACCEPT, authority_identity="human:owner",
            rationale="Reviewed exact Candidate source and delivery"))
    after = ProductManagedSourceService(database).describe(product_id, "human:owner")
    assert after["accepted"]["revision"] == manifest.repository_revision
    assert after["versions"][-1]["acceptance_id"] == str(acceptance.id)
    return submitted.work_id, basis, manifest, after


def test_accepted_v1_new_work_uses_exact_product_source_and_ecf(postgres_database, tmp_path):
    product = ProductAssetService(postgres_database).create(
        "human:owner", "N1 accepted-source qualification")
    product_id = UUID(product["id"])
    first_work, _basis_v0, manifest, accepted = _run_and_accept(
        postgres_database, product_id,
        "# N1 source\n\n## Product Intent\nA bounded public site.\n\n"
        "## Product Invariant\nKeep the page accessible.\n\n"
        "## Approved Decision\nProduce one reviewed landing page.\n", tmp_path)
    assert accepted["accepted"]["version"] == 1
    assert accepted["versions"][-1]["work_id"] == str(first_work)
    submitted = WorkApplicationService(postgres_database).submit_work(
        "Revise the accepted Product with one landing page", product_id=product_id)
    following = _basis(postgres_database, submitted.work_id)
    assert following["source_version"] == 1
    assert following["source_revision"] == manifest.repository_revision
    work = WorkApplicationService(postgres_database)
    work.refine_work(submitted.work_id,
        WorkRefinementRequest(code_exact_targets=("index.html",)))
    assert work.approve_work(submitted.work_id,
        authority_identity="human:owner").status is WorkStatus.READY
    with postgres_database.unit_of_work() as uow:
        resource = ProductStore(uow.session).resource_for_work(submitted.work_id)
    lineage = lineage_for_work_task(postgres_database, work_id=submitted.work_id,
        repository_identity=resource.repository_identity,
        repository_path=Path(resource.location_ref),
        repository_revision=following["source_revision"],
        target_paths=("index.html",))
    assert lineage.contract_id == "PRODUCT_UI_CHANGE"
    assert {item.context_class for item in lineage.protected_obligations} == {
        "PRODUCT_INTENT", "PRODUCT_INVARIANT", "APPROVED_DECISION"}


def test_new_product_lineage_restart_head_isolation_export_and_authority(postgres_database, tmp_path):
    settings = Settings()
    products = ProductAssetService(postgres_database)
    product = products.create("human:owner", "Managed Qualification")
    product_id = UUID(product["id"])
    source = ProductManagedSourceService(postgres_database)
    initial = source.describe(product_id, "human:owner")
    assert initial["origin"] == {}
    assert initial["accepted"]["version"] == 0
    assert source.provider.inspect("product-" + product_id.hex,
        initial["accepted"]["revision"]).tree == initial["accepted"]["tree"]
    with postgres_database.unit_of_work() as uow:
        before_remote = (
            uow.session.scalar(select(func.count()).select_from(remote_delivery_authorizations)),
            uow.session.scalar(select(func.count()).select_from(remote_delivery_receipts)),
        )
    _, first_basis, manifest, accepted = _run_and_accept(postgres_database, product_id,
        "# Managed Qualification\n\nAccepted V1.\n", tmp_path)
    assert first_basis["source_revision"] == initial["accepted"]["revision"]
    assert accepted["accepted"]["version"] == 1
    next_work = WorkApplicationService(postgres_database).submit_work(
        "Continue from accepted V1", product_id=product_id)
    assert _basis(postgres_database, next_work.work_id)["source_revision"] == manifest.repository_revision

    # A container is replaced while its independent named volumes remain mounted.
    env = {**os.environ, "SPG_OPERATOR_TOKEN": "qualification-only-operator-token-0001",
           "WATT_GITEA_PASSWORD": settings.managed_source_password.get_secret_value()}
    subprocess.run(["docker", "compose", "-f", "compose.yaml", "-f",
        "compose.managed-source.yaml", "up", "-d", "--force-recreate", "gitea"],
        cwd=ROOT, env=env, check=True, capture_output=True, timeout=120)
    for _ in range(30):
        try:
            assert source.provider.inspect("product-" + product_id.hex,
                manifest.repository_revision).tree == accepted["accepted"]["tree"]
            break
        except ManagedSourceError:
            time.sleep(1)
    else:
        pytest.fail("Gitea repository did not survive container recreation")

    with TemporaryDirectory() as temporary:
        checkout = Path(temporary) / "source"
        source.provider.materialize("product-" + product_id.hex,
            manifest.repository_revision, checkout, "accepted")
        _git(checkout, "config", "user.name", "Unaccepted provider writer")
        _git(checkout, "config", "user.email", "unaccepted@example.invalid")
        (checkout / "UNACCEPTED.txt").write_text("Not accepted by Watt\n")
        _git(checkout, "add", ".")
        _git(checkout, "commit", "-m", "Unaccepted provider HEAD")
        ambient = _git(checkout, "rev-parse", "HEAD")
        source.provider._transport(checkout, "push", "origin", "HEAD:refs/heads/accepted")
    assert source.provider.resolve_ref("product-" + product_id.hex).revision == ambient
    later = WorkApplicationService(postgres_database).submit_work(
        "Ambient HEAD must not become source", product_id=product_id)
    assert _basis(postgres_database, later.work_id)["source_revision"] == manifest.repository_revision
    assert _basis(postgres_database, later.work_id)["source_revision"] != ambient

    archive, exact = source.export_archive(product_id, "human:owner")
    assert exact == manifest.repository_revision
    with TemporaryDirectory() as temporary:
        target = Path(temporary)
        with ZipFile(BytesIO(archive)) as package:
            package.extractall(target)
        _git(target, "init", "-b", "main")
        _git(target, "add", ".")
        assert _git(target, "write-tree") == accepted["accepted"]["tree"]
    with postgres_database.unit_of_work() as uow:
        after_remote = (
            uow.session.scalar(select(func.count()).select_from(remote_delivery_authorizations)),
            uow.session.scalar(select(func.count()).select_from(remote_delivery_receipts)),
        )
    assert after_remote == before_remote
    client = TestClient(create_http_application(
        Application(settings), database=postgres_database,
        work_service=WorkApplicationService(postgres_database)))
    response = client.get(f"/api/products/{product_id}/code-assets")
    assert response.status_code == 200, response.text
    assert response.json()["accepted"]["revision"] == exact
    files = client.get(f"/api/products/{product_id}/code-assets/files")
    assert files.status_code == 200 and files.json()["files"] == ["README.md"]
    exported = client.get(f"/api/products/{product_id}/code-assets/export")
    assert exported.status_code == 200 and exported.headers["x-watt-source-revision"] == exact
    assert client.get(f"/api/products/{product_id}/code-assets/export?revision={ambient}").status_code == 409
    assert "Code Assets" in (ROOT / "src/spg/web/index.html").read_text()
    assert "inspectCodeVersion" in (ROOT / "src/spg/web/p1-readiness.js").read_text()


def test_brownfield_import_acceptance_next_work_and_provider_fail_closed(postgres_database, tmp_path, monkeypatch):
    repository = tmp_path / "origin"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Brownfield Fixture")
    _git(repository, "config", "user.email", "fixture@example.invalid")
    (repository / "README.md").write_text("# Existing Product\n")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "Existing exact source")
    revision, tree = _git(repository, "rev-parse", "HEAD"), _git(repository, "rev-parse", "HEAD^{tree}")
    product = ProductAssetService(postgres_database).create(
        "human:owner", "Imported Product", provision_source=False)
    product_id = UUID(product["id"])
    with pytest.raises(ProductInvariantViolation, match="provisioned or imported"):
        WorkApplicationService(postgres_database).submit_work(
            "Source is still pending", product_id=product_id)
    intake = RepositoryAssetService(postgres_database, tmp_path / "assets", tmp_path)
    observation = intake.intake(RepositoryIntakeRequest(request_id=uuid4(),
        source=str(repository), title="Existing source", description="Brownfield import",
        authority_identity="human:owner"))
    assert observation["condition"] == "READY"
    assert (observation["revision"], observation["tree"]) == (revision, tree)
    product = ProductAssetService(postgres_database).attach_asset(product_id, "human:owner",
        kind="REPOSITORY", reference=observation["repository_identity"],
        resource_id=UUID(observation["resource_id"]),
        metadata={"revision": revision, "tree": tree})
    source = ProductManagedSourceService(postgres_database)
    imported = source.describe(product_id, "human:owner")
    assert product["managed_source"] is not None
    assert imported["origin"] == {"repository_identity": observation["repository_identity"],
        "revision": revision, "tree": tree}
    assert imported["accepted"]["revision"] == revision
    _, first_basis, manifest, accepted = _run_and_accept(postgres_database, product_id,
        "# Existing Product\n\nAccepted change.\n", tmp_path)
    assert first_basis["source_revision"] == revision
    following = WorkApplicationService(postgres_database).submit_work(
        "Continue imported Product", product_id=product_id)
    assert _basis(postgres_database, following.work_id)["source_revision"] == manifest.repository_revision

    monkeypatch.setenv("SPG_MANAGED_SOURCE_ENDPOINT", "http://127.0.0.1:9")
    with pytest.raises(ManagedSourceError) as failure:
        WorkApplicationService(postgres_database).submit_work(
            "Provider outage must not choose ambient source", product_id=product_id)
    assert failure.value.category == "PROVIDER_UNAVAILABLE"
    with postgres_database.unit_of_work() as uow:
        failed_work_id = uow.session.execute(select(product_works.c.id).where(
            product_works.c.raw_user_requirement == "Provider outage must not choose ambient source")
        ).scalar_one()
        assert uow.session.execute(select(work_source_bases.c.work_id).where(
            work_source_bases.c.work_id == failed_work_id)).scalar_one_or_none() is None
    with pytest.raises(ProductInvariantViolation, match="exact Product accepted source basis"):
        WorkApplicationService(postgres_database).refine_work(failed_work_id,
            WorkRefinementRequest(code_exact_targets=("README.md",)))

@pytest.mark.parametrize('cut', ['BEFORE_GIT', 'AFTER_GIT', 'BEFORE_SQL_COMMIT'])
def test_durable_promotion_replays_exact_authorized_decision_after_interruption(
    postgres_database, tmp_path, monkeypatch, cut,
):
    from spg.infrastructure.persistence.product_schema import (
        product_source_promotion_intents, product_source_versions)
    from spg.infrastructure.persistence.delivery_schema import work_delivery_acceptances, work_delivery_manifests
    from spg.infrastructure.persistence.unit_of_work import UnitOfWork

    class PowerLoss(BaseException):
        pass

    product = ProductAssetService(postgres_database).create('human:owner', 'Promotion interruption ' + cut)
    product_id = UUID(product['id'])
    source = ProductManagedSourceService(postgres_database)
    before = source.describe(product_id, 'human:owner')['accepted']
    original_promote = GiteaManagedSourceProvider.promote
    interrupted = False
    def promote(provider, reference, revision, expected):
        nonlocal interrupted
        if interrupted:
            return original_promote(provider, reference, revision, expected)
        if cut == 'BEFORE_GIT':
            interrupted = True
            raise ManagedSourceError('PROVIDER_UNAVAILABLE', 'bounded qualification interruption')
        observed = original_promote(provider, reference, revision, expected)
        if cut == 'AFTER_GIT':
            interrupted = True
            raise PowerLoss()
        return observed
    monkeypatch.setattr(GiteaManagedSourceProvider, 'promote', promote)
    original_commit = UnitOfWork.commit
    def commit(uow):
        nonlocal interrupted
        # An updated intent in this transaction marks the Git→SQL boundary.
        if cut == 'BEFORE_SQL_COMMIT' and not interrupted and uow.session.execute(
                select(product_source_promotion_intents.c.state).where(
                    product_source_promotion_intents.c.product_id == product_id)).scalar_one_or_none() == 'COMPLETED':
            interrupted = True
            raise PowerLoss()
        return original_commit(uow)
    monkeypatch.setattr(UnitOfWork, 'commit', commit)
    with pytest.raises((PowerLoss, ManagedSourceError)):
        _run_and_accept(postgres_database, product_id, '# Durable acceptance\n\nExact V1.\n', tmp_path)
    assert interrupted
    with postgres_database.unit_of_work() as u:
        intent = dict(u.session.execute(select(product_source_promotion_intents).where(
            product_source_promotion_intents.c.product_id == product_id)).mappings().one())
        acceptance = u.session.execute(select(work_delivery_acceptances.c.payload).where(
            work_delivery_acceptances.c.id == intent['acceptance_id'])).scalar_one()
        manifest = u.session.execute(select(work_delivery_manifests.c.payload).where(
            work_delivery_manifests.c.id == UUID(acceptance['manifest_id']))).scalar_one()
        assert u.session.scalar(select(func.count()).select_from(product_source_versions).where(
            product_source_versions.c.product_id == product_id)) == 1
    assert intent['state'] == ('BLOCKED' if cut == 'BEFORE_GIT' else 'PENDING')
    assert source.describe(product_id, 'human:owner')['accepted'] == before
    assert source.provider.resolve_ref('product-' + product_id.hex).revision == (
        before['revision'] if cut == 'BEFORE_GIT' else intent['revision'])
    with pytest.raises(ProductInvariantViolation, match='PRODUCT_SOURCE_PROMOTION_PENDING'):
        WorkApplicationService(postgres_database).submit_work('New Work cannot consume ambiguous source', product_id=product_id)
    decision = HumanAcceptanceRequest(**{k: acceptance[k] for k in HumanAcceptanceRequest.model_fields})
    delivery = DeliveryApplicationService(postgres_database)
    for _ in range(3):
        result = delivery.decide(intent['work_id'], UUID(manifest['id']), decision)
        assert str(result.id) == acceptance['id']
    after = source.describe(product_id, 'human:owner')
    assert after['accepted'] == {'version': 1, 'revision': intent['revision'], 'tree': intent['tree']}
    assert len(after['versions']) == 2 and after['versions'][-1]['acceptance_id'] == acceptance['id']
    assert not source.pending_promotions()
    next_work = WorkApplicationService(postgres_database).submit_work('Continue exact accepted baseline', product_id=product_id)
    assert _basis(postgres_database, next_work.work_id)['source_revision'] == intent['revision']
