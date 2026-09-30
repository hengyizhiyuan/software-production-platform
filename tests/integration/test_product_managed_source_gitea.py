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
from sqlalchemy import func, select

from spg.api.http import create_http_application
from spg.application.bootstrap import Application
from spg.application.delivery import DeliveryApplicationService
from spg.application.product_assets import ProductAssetService
from spg.application.assets import RepositoryAssetService
from spg.application.product_managed_source import ProductManagedSourceService, _git
from spg.application.work import WorkApplicationService
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
