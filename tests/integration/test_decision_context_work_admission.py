"""Real PostgreSQL and canonical ECF owner proof for Watt self-source policy."""

from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert, update

from spg.application.decision_context import (
    DecisionContextAuthorityMissing, DecisionContextChanged,
    DecisionContextRequirement, MILESTONE_SURFACE,
    MilestoneClosureContextService, WORKSPACE_SURFACE,
    assert_task_context_fresh, lineage_for_work_task,
)
from spg.application.production_intelligence import (
    TaskContractRequest, default_task_contract_builder,
)
from spg.infrastructure.persistence.product_schema import (
    product_managed_sources, product_works, software_products,
)


pytestmark = [pytest.mark.postgresql, pytest.mark.cross_repository]
ROOT = Path(__file__).resolve().parents[2]
REMOTE = "git@github.com:hengyizhiyuan/software-production-platform.git"


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
