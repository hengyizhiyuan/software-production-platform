"""Long-lived software Product ownership over Works and engineering assets."""

from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update

from spg.domain.product import ProductInvariantViolation, ProductRecordNotFound
from spg.infrastructure.persistence.product_schema import (
    engineering_resources, product_works, software_product_assets, software_products,
    work_reality_revisions, work_runtime_bindings, product_managed_sources,
    product_source_versions,
)
from spg.infrastructure.persistence.runtime_schema import (
    production_work_units, baseline_candidates, verification_records, runtime_commits,
)
from spg.infrastructure.persistence.native_execution_schema import self_refine_events
from spg.infrastructure.persistence.delivery_schema import work_delivery_manifests, work_delivery_acceptances
from spg.application.measurement import ProductionMeasurementService


class ProductAssetService:
    def __init__(self, database, settings=None):
        self.database = database
        from spg.config import Settings
        self.settings = settings or Settings()

    def create(self, owner_id: str, name: str, description: str | None = None,
               *, provision_source: bool = True) -> dict:
        if not name.strip():
            raise ProductInvariantViolation("Product name is required")
        product_id = uuid4()
        now = datetime.now(UTC)
        with self.database.unit_of_work() as uow:
            uow.session.execute(insert(software_products).values(
                id=product_id, owner_id=owner_id, name=name.strip(),
                description=description, lifecycle="ACTIVE", created_at=now,
                updated_at=now,
            ))
            uow.commit()
        if provision_source and self.settings.managed_source_provider == "gitea":
            from spg.application.product_managed_source import ProductManagedSourceService
            ProductManagedSourceService(self.database, self.settings).provision(product_id, owner_id, name.strip())
        return self.get(product_id, owner_id)

    def list(self, owner_id: str) -> list[dict]:
        with self.database.unit_of_work() as uow:
            ids = uow.session.execute(select(software_products.c.id).where(
                software_products.c.owner_id == owner_id,
            ).order_by(software_products.c.created_at, software_products.c.id)).scalars().all()
        return [self.get(item, owner_id) for item in ids]

    def get(self, product_id: UUID, owner_id: str) -> dict:
        with self.database.unit_of_work() as uow:
            row = self._owned(uow.session, product_id, owner_id)
            assets = uow.session.execute(select(software_product_assets).where(
                software_product_assets.c.product_id == product_id,
            ).order_by(software_product_assets.c.created_at)).mappings().all()
            works = uow.session.execute(select(
                product_works.c.id, product_works.c.raw_user_requirement,
                product_works.c.condition, product_works.c.created_at,
            ).where(product_works.c.product_id == product_id).order_by(
                product_works.c.created_at, product_works.c.id,
            )).mappings().all()
            managed = uow.session.execute(select(product_managed_sources).where(
                product_managed_sources.c.product_id == product_id)).mappings().one_or_none()
            current_sources = []
            for asset in assets:
                if asset["asset_kind"] != "REPOSITORY":
                    continue
                source = self._asset(asset)
                if managed is not None and asset["reference"] == managed["repository_identity"]:
                    source["metadata"] = {**source["metadata"],
                        "revision": managed["accepted_revision"],
                        "tree": managed["accepted_tree"],
                        "repository_ref": managed["accepted_ref"],
                        "accepted_version": managed["version"],
                        "revision_evidence_ref": f"product-source:{product_id}:{managed['version']}"}
                current_sources.append(source)
            return {
                "id": str(row["id"]), "owner_id": row["owner_id"],
                "name": row["name"], "description": row["description"],
                "lifecycle": row["lifecycle"],
                "assets": [self._asset(item) for item in assets],
                "works": [{"id": str(item["id"]),
                           "requirement": item["raw_user_requirement"],
                           "condition": item["condition"],
                           "created_at": item["created_at"].isoformat()} for item in works],
                "current_sources": current_sources,
                "managed_source": None if managed is None else {
                    "repository_identity": managed["repository_identity"],
                    "provider_kind": managed["provider_kind"],
                    "accepted_revision": managed["accepted_revision"],
                    "accepted_tree": managed["accepted_tree"],
                    "accepted_version": managed["version"],
                    "origin": managed["origin"],
                },
            }

    def bind_work(self, product_id: UUID, work_id: UUID, owner_id: str) -> dict:
        with self.database.unit_of_work() as uow:
            product = self._owned(uow.session, product_id, owner_id)
            if product["lifecycle"] == "ARCHIVED":
                raise ProductInvariantViolation("Archived Product cannot receive Work")
            work = uow.session.execute(select(product_works.c.product_id).where(
                product_works.c.id == work_id,
            ).with_for_update()).first()
            if work is None:
                raise ProductRecordNotFound(f"Work not found: {work_id}")
            if work.product_id is not None and work.product_id != product_id:
                raise ProductInvariantViolation("Work is already bound to another Product")
            if work.product_id is None:
                uow.session.execute(update(product_works).where(
                    product_works.c.id == work_id,
                ).values(product_id=product_id))
            managed = uow.session.execute(select(product_managed_sources.c.product_id).where(
                product_managed_sources.c.product_id == product_id)).scalar_one_or_none()
            if managed is None and self.settings.managed_source_provider == "gitea":
                repository_asset = uow.session.execute(select(software_product_assets.c.id).where(
                    software_product_assets.c.product_id == product_id,
                    software_product_assets.c.asset_kind == "REPOSITORY").limit(1)).scalar_one_or_none()
                if repository_asset is None:
                    raise ProductInvariantViolation("Product source must be provisioned or imported before Work binding")
            if managed is not None:
                condition = uow.session.execute(select(product_works.c.condition).where(
                    product_works.c.id == work_id)).scalar_one()
                if condition != "DRAFT":
                    from spg.infrastructure.persistence.product_schema import work_source_bases
                    basis = uow.session.execute(select(work_source_bases.c.work_id).where(
                        work_source_bases.c.work_id == work_id)).scalar_one_or_none()
                    if basis is None:
                        raise ProductInvariantViolation("Managed Product requires source binding before Work refinement")
            uow.commit()
        if managed is not None and condition == "DRAFT":
            from spg.application.product_managed_source import ProductManagedSourceService
            ProductManagedSourceService(self.database, self.settings).prepare_work(work_id, product_id)
        return self.get(product_id, owner_id)

    def ensure_repository_work(
        self, work_id: UUID | None, resource_id: UUID, owner_id: str,
        *, revision: str, repository_ref: str, tree: str | None,
    ) -> UUID:
        """Retain acquired Product Reality, independently of production admission.

        The Engineering Resource row serializes concurrent admissions of the
        same repository. An existing owner Product is reused, while an already
        bound Work keeps its explicit Product choice.
        """

        now = datetime.now(UTC)
        with self.database.unit_of_work() as uow:
            session = uow.session
            resource = session.execute(select(engineering_resources).where(
                engineering_resources.c.id == resource_id,
            ).with_for_update()).mappings().one_or_none()
            if resource is None:
                raise ProductRecordNotFound(f"Engineering Resource not found: {resource_id}")
            work = None if work_id is None else session.execute(select(product_works.c.product_id).where(
                product_works.c.id == work_id,
            ).with_for_update()).one_or_none()
            if work is None and work_id is not None:
                raise ProductRecordNotFound(f"Work not found: {work_id}")
            identity = resource["repository_identity"]
            product_id = None if work is None else work.product_id
            if product_id is None:
                product_id = session.execute(
                    select(software_product_assets.c.product_id)
                    .join(software_products,
                          software_products.c.id == software_product_assets.c.product_id)
                    .where(
                        software_products.c.owner_id == owner_id,
                        software_products.c.lifecycle == "ACTIVE",
                        software_product_assets.c.asset_kind == "REPOSITORY",
                        software_product_assets.c.reference == identity,
                    )
                    .order_by(software_product_assets.c.created_at,
                              software_product_assets.c.id)
                    .limit(1)
                ).scalar_one_or_none()
                if product_id is None:
                    path = urlparse(identity).path or identity
                    name = PurePosixPath(path.rstrip("/")).name.removesuffix(".git")
                    product_id = uuid4()
                    session.execute(insert(software_products).values(
                        id=product_id, owner_id=owner_id,
                        name=(name or "Repository Product")[:255],
                        description=f"Watt-managed Product for {identity}",
                        lifecycle="ACTIVE", created_at=now, updated_at=now,
                    ))
                if work_id is not None:
                    session.execute(update(product_works).where(
                        product_works.c.id == work_id,
                    ).values(product_id=product_id))
            else:
                product = self._owned(session, product_id, owner_id)
                if product["lifecycle"] != "ACTIVE":
                    raise ProductInvariantViolation("Inactive Product cannot receive a repository")
            existing = session.execute(select(software_product_assets.c.id).where(
                software_product_assets.c.product_id == product_id,
                software_product_assets.c.asset_kind == "REPOSITORY",
                software_product_assets.c.reference == identity,
            )).scalar_one_or_none()
            if existing is None:
                session.execute(insert(software_product_assets).values(
                    id=uuid4(), product_id=product_id, asset_kind="REPOSITORY",
                    reference=identity, resource_id=resource_id,
                    metadata={"revision": revision, "repository_ref": repository_ref,
                              "tree": tree, "source": "WORK_REPOSITORY_ACQUISITION"},
                    created_at=now,
                ))
            uow.commit()
        return product_id

    def history(self, product_id: UUID, owner_id: str) -> dict:
        product = self.get(product_id, owner_id)
        timeline: list[dict] = []
        with self.database.unit_of_work() as uow:
            session = uow.session
            for source_version in session.execute(select(product_source_versions).where(
                product_source_versions.c.product_id == product_id)).mappings():
                timeline.append({"at": source_version["created_at"].isoformat(),
                    "kind": "PRODUCT_SOURCE_ACCEPTED" if source_version["version"] else "PRODUCT_SOURCE_INITIALIZED",
                    "version": source_version["version"],
                    "revision": source_version["revision"], "tree": source_version["tree"],
                    "work_id": str(source_version["work_id"]) if source_version["work_id"] else None,
                    "candidate_id": str(source_version["candidate_id"]) if source_version["candidate_id"] else None,
                    "acceptance_id": str(source_version["acceptance_id"]) if source_version["acceptance_id"] else None})
            works = session.execute(select(product_works).where(
                product_works.c.product_id == product_id,
            )).mappings().all()
            for work in works:
                work_id = work["id"]
                timeline.append({"at": work["created_at"].isoformat(),
                    "kind": "WORK_REQUESTED", "work_id": str(work_id),
                    "requirement": work["raw_user_requirement"]})
                for reality in session.execute(select(work_reality_revisions).where(
                    work_reality_revisions.c.work_id == work_id,
                )).mappings():
                    timeline.append({"at": reality["created_at"].isoformat(),
                        "kind": "WORK_REALITY", "work_id": str(work_id),
                        "revision": reality["revision_number"],
                        "motive": reality["motive"], "desired_outcome": reality["desired_outcome"],
                        "source_revision": reality["source_revision"],
                        "evidence_ref": f"work-reality:{reality['id']}"})
                for cycle in session.execute(select(work_runtime_bindings).where(
                    work_runtime_bindings.c.work_id == work_id,
                )).mappings():
                    run_id = cycle["production_run_id"]
                    timeline.append({"at": cycle["created_at"].isoformat(),
                        "kind": "PRODUCTION_CYCLE", "work_id": str(work_id),
                        "cycle_number": cycle["cycle_number"],
                        "run_id": str(run_id), "plan_revision_id": str(cycle["plan_revision_id"])})
                    for unit in session.execute(select(production_work_units).where(
                        production_work_units.c.production_run_id == run_id,
                    )).mappings():
                        timeline.append({"at": unit["created_at"].isoformat(),
                            "kind": "PWU", "work_id": str(work_id), "pwu_id": str(unit["id"]),
                            "node_id": unit["node_id"], "objective": unit["objective"],
                            "condition": unit["condition"]})
                    for candidate in session.execute(select(baseline_candidates).where(
                        baseline_candidates.c.production_run_id == run_id,
                    )).mappings():
                        timeline.append({"at": candidate["sealed_at"].isoformat(),
                            "kind": "CANDIDATE", "work_id": str(work_id),
                            "candidate_id": str(candidate["id"]),
                            "revision": candidate["proposed_commit_identity"],
                            "pwu_ids": candidate["satisfied_work_unit_ids"]})
                    for verification in session.execute(select(verification_records).where(
                        verification_records.c.production_run_id == run_id,
                    )).mappings():
                        timeline.append({"at": verification["created_at"].isoformat(),
                            "kind": "VERIFICATION", "work_id": str(work_id),
                            "pwu_id": str(verification["work_unit_id"]),
                            "result": verification["result"],
                            "evidence_ref": f"verification:{verification['id']}"})
                    for commit in session.execute(select(runtime_commits).where(
                        runtime_commits.c.production_run_id == run_id,
                    )).mappings():
                        timeline.append({"at": commit["committed_at"].isoformat(),
                            "kind": "SOURCE_COMMITTED", "work_id": str(work_id),
                            "repository_identity": commit["repository_identity"],
                            "repository_ref": commit["target_authoritative_ref"],
                            "revision": commit["repository_revision"],
                            "evidence_ref": f"runtime-commit:{commit['id']}"})
                for event in session.execute(select(self_refine_events).where(
                    self_refine_events.c.work_id == work_id,
                )).mappings():
                    timeline.append({"at": event["created_at"].isoformat(),
                        "kind": "SELF_REFINE", "work_id": str(work_id),
                        "classification": event["refinement_class"],
                        "diagnosis": event["diagnosis_summary"],
                        "result": event["final_result"],
                        "evidence_ref": f"self-refine:{event['id']}"})
                manifests = session.execute(select(work_delivery_manifests).where(
                    work_delivery_manifests.c.work_id == work_id,
                )).mappings().all()
                for manifest in manifests:
                    timeline.append({"at": manifest["created_at"].isoformat(),
                        "kind": "DELIVERY_READY", "work_id": str(work_id),
                        "manifest_id": str(manifest["id"]),
                        "runtime_commit_id": str(manifest["runtime_commit_id"])})
                    acceptance = session.execute(select(work_delivery_acceptances).where(
                        work_delivery_acceptances.c.manifest_id == manifest["id"],
                    )).mappings().one_or_none()
                    if acceptance is not None:
                        timeline.append({"at": acceptance["created_at"].isoformat(),
                            "kind": "HUMAN_ACCEPTANCE", "work_id": str(work_id),
                            "manifest_id": str(manifest["id"]),
                            "decision": acceptance["payload"].get("decision")})
        return {"product_id": str(product_id), "name": product["name"],
                "current_sources": product["current_sources"],
                "timeline": sorted(timeline, key=lambda row: (row["at"], row["kind"]))}

    def economics(self, product_id: UUID, owner_id: str) -> dict:
        product = self.get(product_id, owner_id)
        works = [ProductionMeasurementService(self.database).graph_economics(UUID(row["id"]))
                 for row in product["works"]]
        currencies: dict[str, float] = {}
        unknown = 0
        for work in works:
            spend = work["observed_provider_spend"]
            unknown += spend.get("unreported_attempt_count", 0)
            for currency, amount in spend.get("by_currency", {}).items():
                currencies[currency] = currencies.get(currency, 0) + amount
        return {"product_id": str(product_id), "work_count": len(works),
                "pwu_count": sum(work["pwu_count"] for work in works),
                "execution_seconds": sum(work["execution_seconds"] for work in works),
                "token_usage": {
                    "total_tokens": sum(work["token_usage"].get("total_tokens", 0) for work in works),
                    "status": "OBSERVED" if works and all(work["token_usage"]["status"] == "OBSERVED" for work in works)
                              else "PARTIAL" if any(work["token_usage"]["status"] != "UNREPORTED" for work in works)
                              else "UNREPORTED"},
                "observed_provider_spend": {"by_currency": currencies,
                    "unreported_attempt_count": unknown,
                    "status": "PARTIAL" if currencies and unknown else
                              "OBSERVED" if currencies else "UNREPORTED"},
                "works": works}

    def attach_asset(self, product_id: UUID, owner_id: str, *, kind: str,
                     reference: str, resource_id: UUID | None = None,
                     metadata: dict | None = None) -> dict:
        if kind not in {"REPOSITORY", "RUNTIME", "DATABASE", "DOCUMENT", "ENVIRONMENT", "DELIVERY_TARGET"}:
            raise ProductInvariantViolation("Unsupported Product asset kind")
        if not reference.strip():
            raise ProductInvariantViolation("Product asset reference is required")
        if kind == "REPOSITORY" and self.settings.managed_source_provider == "gitea":
            with self.database.unit_of_work() as uow:
                self._owned(uow.session, product_id, owner_id)
                managed = uow.session.execute(select(product_managed_sources.c.repository_identity).where(
                    product_managed_sources.c.product_id == product_id)).scalar_one_or_none()
                resource = None if resource_id is None else uow.session.execute(
                    select(engineering_resources).where(engineering_resources.c.id == resource_id)
                ).mappings().one_or_none()
            if managed is not None:
                if (reference != managed or resource is None
                        or resource["repository_identity"] != reference):
                    raise ProductInvariantViolation("Product already owns a managed source")
                return self.get(product_id, owner_id)
            elif resource is not None and resource["repository_identity"] == reference:
                from spg.application.product_managed_source import ProductManagedSourceService
                observed = metadata or {}
                ProductManagedSourceService(self.database, self.settings).import_existing(
                    product_id, owner_id, reference, Path(resource["location_ref"]),
                    observed.get("revision") or "", observed.get("tree") or "")
                return self.get(product_id, owner_id)
        with self.database.unit_of_work() as uow:
            self._owned(uow.session, product_id, owner_id)
            if kind == "REPOSITORY":
                if resource_id is None:
                    raise ProductInvariantViolation("Repository asset requires an admitted Engineering Resource")
                resource = uow.session.execute(select(engineering_resources).where(
                    engineering_resources.c.id == resource_id,
                )).mappings().one_or_none()
                if resource is None or resource["repository_identity"] != reference:
                    raise ProductInvariantViolation("Repository identity does not match Engineering Resource")
            elif resource_id is not None:
                raise ProductInvariantViolation("Only repository assets bind an Engineering Resource")
            existing = uow.session.execute(select(software_product_assets.c.id).where(
                software_product_assets.c.product_id == product_id,
                software_product_assets.c.asset_kind == kind,
                software_product_assets.c.reference == reference,
            )).scalar_one_or_none()
            if existing is None:
                uow.session.execute(insert(software_product_assets).values(
                    id=uuid4(), product_id=product_id, asset_kind=kind,
                    reference=reference, resource_id=resource_id,
                    metadata=metadata or {}, created_at=datetime.now(UTC),
                ))
            uow.commit()
        return self.get(product_id, owner_id)

    @staticmethod
    def _owned(session, product_id: UUID, owner_id: str):
        row = session.execute(select(software_products).where(
            software_products.c.id == product_id,
            software_products.c.owner_id == owner_id,
        )).mappings().one_or_none()
        if row is None:
            raise ProductRecordNotFound(f"Product not found: {product_id}")
        return row

    @staticmethod
    def _asset(row) -> dict:
        return {"id": str(row["id"]), "kind": row["asset_kind"],
                "reference": row["reference"],
                "resource_id": None if row["resource_id"] is None else str(row["resource_id"]),
                "metadata": row["metadata"]}
