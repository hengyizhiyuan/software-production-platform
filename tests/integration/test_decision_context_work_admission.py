"""Real PostgreSQL and canonical ECF owner proof for Watt self-source policy."""

from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert, update

from spg.application.decision_context import (
    DecisionContextAuthorityMissing, DecisionContextChanged,
    DecisionContextRequirement, MANAGED_WEB_SURFACE, MILESTONE_SURFACE,
    MilestoneClosureContextService, WORKSPACE_SURFACE,
    assert_task_context_fresh, lineage_for_work_task,
)
from spg.application.production_intelligence import (
    TaskContractRequest, default_task_contract_builder,
)
from spg.infrastructure.persistence.product_schema import (
    engineering_resources, product_managed_sources, product_works,
    software_products, work_source_bases,
)


pytestmark = [pytest.mark.postgresql, pytest.mark.cross_repository]
ROOT = Path(__file__).resolve().parents[2]
REMOTE = "git@github.com:hengyizhiyuan/software-production-platform.git"


def test_managed_web_work_binds_exact_product_source_and_ecf(
    postgres_database, tmp_path,
):
    from tests.qualification_owner_sources import owner_source_root
    owner = owner_source_root("ecf", ROOT.parent / "engineering-context-fabric" / "src")
    sys.path.insert(0, str(owner))
    product_id, work_id, resource_id = (uuid4() for _ in range(3))
    repository = tmp_path / "web"
    repository.mkdir()
    for args in (("init", "-b", "work"), ("config", "user.name", "ECF test"),
                 ("config", "user.email", "ecf@example.invalid"),
                 ("remote", "add", "origin", "http://gitea.invalid/product.git")):
        subprocess.run(["git", "-C", str(repository), *args], check=True,
                       capture_output=True)
    (repository / "README.md").write_text(
        "# Web\n\n## Product Intent\nCompany homepage.\n\n"
        "## Product Invariant\nKeep navigation.\n\n"
        "## Approved Decision\nAdd an entry.\n", encoding="utf-8")
    (repository / "index.html").write_text("<main>Home</main>\n")
    for args in (("add", "."), ("commit", "-m", "baseline")):
        subprocess.run(["git", "-C", str(repository), *args], check=True,
                       capture_output=True)
    revision = subprocess.check_output(
        ["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip()
    tree = subprocess.check_output(
        ["git", "-C", str(repository), "rev-parse", "HEAD^{tree}"], text=True).strip()
    identity = f"watt://work-branches/{work_id}"
    try:
        with postgres_database.unit_of_work() as uow:
            uow.session.execute(insert(software_products).values(
                id=product_id, owner_id="human:ecf-web", name="Web",
                lifecycle="ACTIVE", description="managed web qualification"))
            uow.session.execute(insert(product_works).values(
                id=work_id, product_id=product_id, work_mode="IMMEDIATE_PRODUCTION",
                raw_user_requirement="Add a page entry", desired_outcome="Add a page entry",
                constraints=[], tags=[], condition="READY",
                production_objective="Add a page entry"))
            uow.session.execute(insert(engineering_resources).values(
                id=resource_id, kind="REPOSITORY", repository_identity=identity,
                location_ref=str(repository), authoritative_ref="refs/heads/work",
                context_references=[], is_default=False))
            uow.session.execute(insert(product_managed_sources).values(
                product_id=product_id,
                repository_identity=f"watt://repositories/products/{product_id}",
                provider_kind="gitea", provider_reference="product-test",
                accepted_ref="refs/heads/accepted", accepted_revision=revision,
                accepted_tree=tree, origin={}))
            uow.session.execute(insert(work_source_bases).values(
                work_id=work_id, product_id=product_id, resource_id=resource_id,
                source_version=0, source_revision=revision, source_tree=tree,
                work_ref="refs/heads/work"))
            uow.commit()
        lineage = lineage_for_work_task(
            postgres_database, work_id=work_id, repository_identity=identity,
            repository_path=repository, repository_revision=revision,
            target_paths=("index.html",))
        assert lineage is not None and lineage.surface == MANAGED_WEB_SURFACE
        task = default_task_contract_builder().build(TaskContractRequest(
            objective="Add a page entry", scope=("UPDATE:index.html",),
            acceptance_meaning=("Check page entry",),
            out_of_scope=("Other paths",), authority_lineage=(f"work:{work_id}",),
            work_reality_references=(f"work:{work_id}",),
            ecf_references=(f"repository:{identity}",),
            decision_reference=f"work:{work_id}", governed_surface=lineage.surface,
            decision_context=lineage))
        assert_task_context_fresh(postgres_database, task)
    finally:
        with postgres_database.unit_of_work() as uow:
            uow.session.execute(delete(work_source_bases).where(
                work_source_bases.c.work_id == work_id))
            uow.session.execute(delete(product_managed_sources).where(
                product_managed_sources.c.product_id == product_id))
            uow.session.execute(delete(engineering_resources).where(
                engineering_resources.c.id == resource_id))
            uow.session.execute(delete(product_works).where(
                product_works.c.id == work_id))
            uow.session.execute(delete(software_products).where(
                software_products.c.id == product_id))
            uow.commit()
        sys.path.remove(str(owner))


def test_exact_product_owner_and_current_work_bind_canonical_ecf(postgres_database):
    from tests.qualification_owner_sources import owner_source_root
    owner = owner_source_root("ecf", ROOT.parent / "engineering-context-fabric" / "src")
    if not (owner / "ecf" / "decision_context.py").exists():
        pytest.skip("BLOCKED_EXTERNAL_DEPENDENCY: canonical ECF v0.1 unavailable")
    sys.path.insert(0, str(owner))
    product_a, product_b, work_a, work_b = (uuid4() for _ in range(4))
    revision = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()
    tree = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD^{tree}"],
                          check=True, capture_output=True, text=True).stdout.strip()
    try:
        with postgres_database.unit_of_work() as uow:
            for product_id, name in ((product_a, "Watt"), (product_b, "Other Product")):
                uow.session.execute(insert(software_products).values(
                    id=product_id, owner_id="human:ecf-dogfood", name=name,
                    lifecycle="ACTIVE", description="isolated ECF qualification",
                ))
            uow.session.execute(insert(product_managed_sources).values(
                product_id=product_a, repository_identity=REMOTE,
                provider_kind="GITHUB", provider_reference=REMOTE,
                accepted_ref="refs/heads/main", accepted_revision=revision,
                accepted_tree=tree, origin={},
            ))
            for work_id, product_id in ((work_a, product_a), (work_b, product_b)):
                uow.session.execute(insert(product_works).values(
                    id=work_id, product_id=product_id,
                    work_mode="IMMEDIATE_PRODUCTION",
                    raw_user_requirement="Modify Workspace Product UI",
                    desired_outcome="Preserve Agenda, Reality, Actions, Production",
                    constraints=[], tags=[], condition="READY",
                    production_objective="Modify Workspace Product UI",
                ))
            uow.commit()
        lineage = lineage_for_work_task(
            postgres_database, work_id=work_a, repository_identity=REMOTE,
            repository_path=ROOT, repository_revision=revision,
            target_paths=("src/spg/web/experience.js",),
        )
        assert lineage is not None and lineage.surface == WORKSPACE_SURFACE
        task = default_task_contract_builder().build(TaskContractRequest(
            objective="Modify Workspace Product UI",
            scope=("UPDATE:src/spg/web/experience.js",),
            acceptance_meaning=("Verify quadrants",),
            out_of_scope=("Do not change layout",),
            authority_lineage=(f"work:{work_a}",),
            work_reality_references=(f"work:{work_a}",),
            ecf_references=(f"repository:{REMOTE}",),
            decision_reference=f"work:{work_a}",
            governed_surface=WORKSPACE_SURFACE, decision_context=lineage,
        ))
        assert task.decision_context.package_fingerprint == lineage.package_fingerprint
        assert_task_context_fresh(postgres_database, task)
        closure = MilestoneClosureContextService(postgres_database).assess(
            DecisionContextRequirement(
                MILESTONE_SURFACE, product_a, work_a,
                f"milestone:work:{work_a}", ROOT, revision, REMOTE,
            ))
        assert closure.status == "DECISION_CONTEXT_NOT_READY"
        assert "VERIFICATION_EVIDENCE" in closure.missing_classes
        with pytest.raises(DecisionContextAuthorityMissing):
            lineage_for_work_task(
                postgres_database, work_id=work_b, repository_identity=REMOTE,
                repository_path=ROOT, repository_revision=revision,
                target_paths=("src/spg/web/experience.js",),
            )
        with postgres_database.unit_of_work() as uow:
            uow.session.execute(update(product_works).where(
                product_works.c.id == work_a).values(
                    desired_outcome="A later governed Work revision changed the intent"))
            uow.commit()
        with pytest.raises(DecisionContextChanged):
            assert_task_context_fresh(postgres_database, task)
    finally:
        with postgres_database.unit_of_work() as uow:
            uow.session.execute(delete(product_works).where(
                product_works.c.id.in_((work_a, work_b))))
            uow.session.execute(delete(product_managed_sources).where(
                product_managed_sources.c.product_id == product_a))
            uow.session.execute(delete(software_products).where(
                software_products.c.id.in_((product_a, product_b))))
            uow.commit()
        sys.path.remove(str(owner))
