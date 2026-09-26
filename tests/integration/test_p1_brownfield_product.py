"""P1-Q4: a real existing Git repository becomes long-lived Product source."""

from pathlib import Path
import os
import subprocess
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
import pytest

from spg.application.assets import RepositoryAssetService
from spg.application.product_assets import ProductAssetService
from spg.application.work import WorkApplicationService
from spg.domain.assets import RepositoryIntakeRequest
from spg.domain.product import ProductInvariantViolation, WorkRefinementRequest
from spg.infrastructure.persistence import product_tables, runtime_tables


pytestmark = pytest.mark.postgresql


@pytest.fixture(autouse=True)
def clean_p1_product_reality(postgres_database):
    previous = os.environ.get("SPG_DATABASE_URL")
    os.environ["SPG_DATABASE_URL"] = postgres_database.engine.url.render_as_string(hide_password=False)
    command.upgrade(Config(Path(__file__).resolve().parents[2] / "alembic.ini"), "head")
    names = ", ".join(f'"{table.name}"' for table in (*product_tables, *runtime_tables))
    with postgres_database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {names} CASCADE")
    yield
    with postgres_database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {names} CASCADE")
    if previous is None:
        os.environ.pop("SPG_DATABASE_URL", None)
    else:
        os.environ["SPG_DATABASE_URL"] = previous


def _git(root: Path, *args: str) -> str:
    return subprocess.run(("git", "-C", str(root), *args), check=True,
                          capture_output=True, text=True).stdout.strip()


def test_p1_q4_brownfield_intake_product_work_and_delivery_boundary(
    postgres_database, tmp_path: Path,
) -> None:
    imports = tmp_path / "imports"
    repository = imports / "legacy-finance"
    repository.mkdir(parents=True)
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "P1 Qualification")
    _git(repository, "config", "user.email", "p1@example.invalid")
    (repository / "README.md").write_text("# Existing Finance Product\n", encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "existing baseline")
    exact_revision = _git(repository, "rev-parse", "HEAD")

    products = ProductAssetService(postgres_database)
    product = products.create("human:owner", "Finance Management")
    assets = RepositoryAssetService(postgres_database, tmp_path / "assets", imports)
    observation = assets.intake(RepositoryIntakeRequest(
        request_id=uuid4(), source=str(repository), title="Legacy finance repository",
        description="Onboard the existing repository", authority_identity="human:owner"))
    assert observation["condition"] == "READY"
    assert observation["repository_ref"] == "refs/heads/main"
    assert observation["revision"] == exact_revision
    products.attach_asset(UUID(product["id"]), "human:owner", kind="REPOSITORY",
        reference=observation["repository_identity"],
        resource_id=UUID(observation["resource_id"]),
        metadata={"revision": exact_revision,
                  "repository_ref": observation["repository_ref"],
                  "context_path": observation["context_path"]})
    work_service = WorkApplicationService(postgres_database, workspace_root=tmp_path / "workspaces")
    work = work_service.submit_work(
        "Add reimbursement to the existing Finance Product", product_id=UUID(product["id"]))
    with pytest.raises(ProductInvariantViolation, match="not attached"):
        work_service.refine_work(work.work_id, WorkRefinementRequest(
            engineering_resource_id=uuid4(), code_exact_targets=("reimbursements.py",),
        ))
    work_service.refine_work(work.work_id, WorkRefinementRequest(
        code_exact_targets=("reimbursements.py",),
    ))
    with postgres_database.unit_of_work() as uow:
        from spg.infrastructure.persistence.product_store import ProductStore
        selected = ProductStore(uow.session).resource_for_work(work.work_id)
    assert selected.id == UUID(observation["resource_id"])
    current = products.get(UUID(product["id"]), "human:owner")
    assert current["works"][0]["id"] == str(work.work_id)
    assert current["current_sources"][0]["metadata"]["revision"] == exact_revision
    assert products.history(UUID(product["id"]), "human:owner")["timeline"][0]["kind"] == "WORK_REQUESTED"
    with pytest.raises(ProductInvariantViolation):
        assets.intake(RepositoryIntakeRequest(
            request_id=uuid4(), source="ftp://unsupported.example/repository",
            title="Unsupported source", description="Unsupported protocol",
            authority_identity="human:owner"))
