"""Long-lived software Product ownership over Works and engineering assets."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update

from spg.domain.product import ProductInvariantViolation, ProductRecordNotFound
from spg.infrastructure.persistence.product_schema import (
    engineering_resources, product_works, software_product_assets, software_products,
    work_reality_revisions, work_runtime_bindings,
)
from spg.infrastructure.persistence.runtime_schema import (
    production_work_units, baseline_candidates, verification_records, runtime_commits,
)
from spg.infrastructure.persistence.native_execution_schema import self_refine_events
from spg.infrastructure.persistence.delivery_schema import work_delivery_manifests, work_delivery_acceptances
from spg.application.measurement import ProductionMeasurementService


class ProductAssetService:
    def __init__(self, database):
        self.database = database

    def create(self, owner_id: str, name: str, description: str | None = None) -> dict:
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
            work_ids = [item["id"] for item in works]
            bindings = [] if not work_ids else uow.session.execute(select(
                work_runtime_bindings.c.work_id, work_runtime_bindings.c.production_run_id,
            ).where(work_runtime_bindings.c.work_id.in_(work_ids))).mappings().all()
            run_to_work = {item["production_run_id"]: item["work_id"] for item in bindings}
            commits = [] if not run_to_work else uow.session.execute(select(runtime_commits).where(
                runtime_commits.c.production_run_id.in_(tuple(run_to_work)),
            ).order_by(runtime_commits.c.committed_at, runtime_commits.c.id)).mappings().all()
            latest_by_repository = {}
            for commit in commits:
                latest_by_repository[commit["repository_identity"]] = commit
            current_sources = []
            for asset in assets:
                if asset["asset_kind"] != "REPOSITORY":
                    continue
                source = self._asset(asset)
                committed = latest_by_repository.get(asset["reference"])
                if committed is not None:
                    source["metadata"] = {**source["metadata"],
                        "revision": committed["repository_revision"],
                        "repository_ref": committed["target_authoritative_ref"],
                        "revision_evidence_ref": f"runtime-commit:{committed['id']}",
                        "last_work_id": str(run_to_work[committed["production_run_id"]])}
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
            uow.commit()
        return self.get(product_id, owner_id)

    def history(self, product_id: UUID, owner_id: str) -> dict:
        product = self.get(product_id, owner_id)
        timeline: list[dict] = []
        with self.database.unit_of_work() as uow:
            session = uow.session
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
