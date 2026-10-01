"""Bounded, read-only Product Experience projections over canonical owners."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from spg.domain.model_runtime import ModelProfile, ModelProvider, ModelPurpose
from spg.infrastructure.model_runtime import DeepSeekResponsesModelAdapter, ModelProviderError
from spg.infrastructure.persistence.product_schema import (
    product_works, software_products, product_managed_sources,
    product_workspace_interactions,
)
from spg.infrastructure.persistence.delivery_schema import (
    work_delivery_manifests, work_delivery_acceptances, work_delivery_runtimes,
)
from spg.domain.product import ProductInvariantViolation


class QueryIntent(BaseModel):
    """The only collection dimensions a semantic model may propose."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["products", "works", "deliverables"]
    product_id: UUID | None = None
    state: Literal["ANY", "ACTIVE", "COMPLETED", "BLOCKED", "ATTENTION"] = "ANY"
    days: Literal[0, 7, 30, 90] = 0
    guardian: Literal["ANY", "PASS", "FINDINGS"] = "ANY"
    acceptance: Literal["ANY", "ACCEPTED", "PENDING"] = "ANY"
    deployed: Literal["ANY", "YES", "NO"] = "ANY"
    unsupported: tuple[str, ...] = ()


class RouteIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["EXISTING", "NEW", "ADVISORY", "CLARIFY"]
    product_id: UUID | None = None
    product_name: str | None = Field(default=None, max_length=255)
    persistent_outcome: bool = False
    confidence: float = Field(ge=0, le=1)
    clarification: str | None = Field(default=None, max_length=300)


class SemanticExperienceCompiler:
    """Reuse Watt's Responses transport; never let model output become SQL or authority."""

    def __init__(self, settings):
        self.settings = settings

    def _compile(self, text: str, schema: type[BaseModel], instructions: str):
        credential = self.settings.deepseek_api_key
        if credential is None or not credential.get_secret_value():
            raise ValueError("SEMANTIC_PROVIDER_UNAVAILABLE")
        adapter = DeepSeekResponsesModelAdapter(
            api_key=credential.get_secret_value,
            base_url=self.settings.deepseek_base_url,
        )
        try:
            profile = ModelProfile(
                purpose=ModelPurpose.WIC_SEMANTIC,
                provider=ModelProvider.DEEPSEEK,
                model=self.settings.wic_provider_model or "deepseek-flash",
                reasoning_effort=self.settings.wic_provider_reasoning_effort,
                timeout_seconds=min(self.settings.collaboration_provider_timeout_seconds, 30),
                max_output_tokens=500,
            )
            result = adapter.generate(
                profile=profile,
                instructions=instructions,
                input_text=text,
                output_schema=schema.model_json_schema(),
            )
            return schema.model_validate_json(result.output_text)
        finally:
            adapter.close()

    def route(self, text: str, products: list[dict]) -> RouteIntent:
        catalog = [{"id": item["id"], "name": item["name"],
                    "description": item["description"]} for item in products[:50]]
        return self._compile(json.dumps({"human_turn": text, "products": catalog},
                                        ensure_ascii=False), RouteIntent,
            "Classify one Human turn for Watt Home. EXISTING only for one clear catalog Product; "
            "NEW only for a persistent software outcome the Human wants to build, with a concise "
            "Product name; ADVISORY for questions or analysis without production commitment; "
            "CLARIFY for genuinely ambiguous Product reference. Do not infer authority or create Work. "
            "Return only the schema fields and cite an exact catalog product_id for EXISTING.")

    def query(self, text: str, kind: str, products: list[dict]) -> QueryIntent:
        catalog = [{"id": item["id"], "name": item["name"]}
                   for item in products[:50]]
        return self._compile(json.dumps({"kind": kind, "human_query": text,
                                         "products": catalog}, ensure_ascii=False),
            QueryIntent,
            "Translate the Human's collection request into the typed bounded query schema. "
            "Use only listed Product IDs, allowed enum values, and days 0/7/30/90. "
            "No SQL, unsupported dimensions, inferred facts, or prose. "
            "If a requested dimension is unsupported, put its short name in unsupported; "
            "retain ANY for that dimension so the server can disclose the limit.")


def _iso(value):
    return None if value is None else value.isoformat()


def _fingerprint(*rows) -> str:
    payload = json.dumps(rows, sort_keys=True, ensure_ascii=False, default=str)
    return sha256(payload.encode()).hexdigest()


class ProductExperienceProjection:
    """Read-model composition; Product, Work, Guardian, Source and Delivery keep truth."""

    def __init__(self, database, products, work, delivery, guardian=None):
        self.database = database
        self.products = products
        self.work = work
        self.delivery = delivery
        self.guardian = guardian

    def collections(self, owner_id: str) -> dict:
        with self.database.unit_of_work() as uow:
            session = uow.session
            products = session.execute(select(software_products).where(
                software_products.c.owner_id == owner_id).order_by(
                software_products.c.updated_at.desc()).limit(100)).mappings().all()
            product_ids = [row["id"] for row in products]
            works = [] if not product_ids else session.execute(select(product_works).where(
                product_works.c.product_id.in_(product_ids)).order_by(
                product_works.c.updated_at.desc()).limit(300)).mappings().all()
            work_ids = [row["id"] for row in works]
            sources = [] if not product_ids else session.execute(select(
                product_managed_sources).where(
                product_managed_sources.c.product_id.in_(product_ids))).mappings().all()
            manifests = [] if not work_ids else session.execute(select(
                work_delivery_manifests).where(
                work_delivery_manifests.c.work_id.in_(work_ids)).order_by(
                work_delivery_manifests.c.created_at.desc()).limit(300)).mappings().all()
            manifest_ids = [row["id"] for row in manifests]
            acceptances = [] if not manifest_ids else session.execute(select(
                work_delivery_acceptances).where(
                work_delivery_acceptances.c.manifest_id.in_(manifest_ids))).mappings().all()
            runtimes = [] if not manifest_ids else session.execute(select(
                work_delivery_runtimes).where(
                work_delivery_runtimes.c.manifest_id.in_(manifest_ids))).mappings().all()
        source_by_product = {row["product_id"]: row for row in sources}
        acceptance_by_manifest = {row["manifest_id"]: row for row in acceptances}
        runtime_by_manifest = {row["manifest_id"]: row for row in runtimes}
        product_by_id = {row["id"]: row for row in products}
        work_by_id = {row["id"]: row for row in works}
        work_rows = [{"id": str(row["id"]), "product_id": str(row["product_id"]),
                      "product_name": product_by_id[row["product_id"]]["name"],
                      "title": row["refined_title"] or row["raw_user_requirement"] or "待明确的事项",
                      "requirement": row["raw_user_requirement"],
                      "status": row["condition"], "created_at": _iso(row["created_at"]),
                      "updated_at": _iso(row["updated_at"]),
                      "reality_revision_id": str(row["current_work_reality_revision_id"])
                          if row["current_work_reality_revision_id"] else None}
                     for row in works]
        deliveries = []
        for row in manifests:
            work = work_by_id[row["work_id"]]
            product = product_by_id[work["product_id"]]
            payload = row["payload"]
            acceptance = acceptance_by_manifest.get(row["id"])
            deliveries.append({"id": str(row["id"]), "product_id": str(product["id"]),
                "product_name": product["name"], "work_id": str(work["id"]),
                "work_title": work["refined_title"] or work["raw_user_requirement"],
                "title": payload.get("software", {}).get("title") if isinstance(payload.get("software"), dict)
                    else work["refined_title"] or work["raw_user_requirement"],
                "created_at": _iso(row["created_at"]),
                "source_revision": payload.get("repository_revision"),
                "artifact_count": len(payload.get("artifacts", [])),
                "acceptance": None if acceptance is None else acceptance["payload"].get("decision"),
                "deployed": row["id"] in runtime_by_manifest,
                "fingerprint": payload.get("fingerprint")})
        product_rows = []
        for row in products:
            associated = [work for work in work_rows if work["product_id"] == str(row["id"])]
            associated_delivery = [item for item in deliveries if item["product_id"] == str(row["id"])]
            source = source_by_product.get(row["id"])
            product_rows.append({"id": str(row["id"]), "name": row["name"],
                "description": row["description"], "status": row["lifecycle"],
                "updated_at": _iso(row["updated_at"]),
                "accepted_version": None if source is None else source["version"],
                "accepted_revision": None if source is None else source["accepted_revision"],
                "current_work": next((work for work in associated
                    if work["status"] not in {"COMPLETED", "DISCARDED"}), None),
                "recent_works": associated[:5], "recent_deliverables": associated_delivery[:5],
                "work_count": len(associated), "deliverable_count": len(associated_delivery)})
        attention = []
        work_index = {row["id"]: row for row in work_rows}
        for item in self.work.list_attention():
            work = work_index.get(str(item.work_id))
            if work is None or not item.available_actions:
                continue
            attention.append({"id": str(item.id), "work_id": work["id"],
                "product_id": work["product_id"], "product_name": work["product_name"],
                "work_title": work["title"], "kind": item.kind.value,
                "reason": item.reason, "decision": item.decision,
                "actions": [action.value for action in item.available_actions]})
            if len(attention) >= 30:
                break
        return {"revision": _fingerprint(product_rows, work_rows, deliveries, attention),
                "products": product_rows, "works": work_rows,
                "deliverables": deliveries, "attention": attention}

    def home(self, owner_id: str) -> dict:
        collections = self.collections(owner_id)
        return {"revision": collections["revision"],
                "recent_products": collections["products"][:4],
                "active_works": [row for row in collections["works"]
                    if row["status"] not in {"COMPLETED", "DISCARDED"}][:5],
                "attention": collections["attention"][:5]}

    def product(self, owner_id: str, product_id: UUID) -> dict:
        collections = self.collections(owner_id)
        product = next((row for row in collections["products"]
                        if row["id"] == str(product_id)), None)
        if product is None:
            raise ProductInvariantViolation("Product is unavailable to this owner")
        return {**product, "revision": collections["revision"]}

    def workspace(self, owner_id: str, product_id: UUID,
                  work_id: UUID | None = None) -> dict:
        product = self.product(owner_id, product_id)
        selected = next((row for row in product["recent_works"]
                         if row["id"] == str(work_id)), None) if work_id else product["current_work"]
        if work_id is not None and selected is None:
            with self.database.unit_of_work() as uow:
                row = uow.session.execute(select(product_works.c.product_id).where(
                    product_works.c.id == work_id)).scalar_one_or_none()
            if row != product_id:
                raise ProductInvariantViolation("Work does not belong to this Product")
            selected = {"id": str(work_id)}
        work = None if selected is None else self.work.get_work(UUID(selected["id"]))
        work_data = None if work is None else work.model_dump(mode="json")
        delivery = None if work is None else self.delivery.view(work.work_id)
        candidate = None if work is None else self.delivery.candidate_context(work.work_id)
        guardian = ({"status": "NOT_STARTED", "finding_count": 0}
                    if work is None or self.guardian is None else
                    self.guardian.projection(work.work_id))
        attention = [] if work is None else [{"id": str(item.id),
            "kind": item.kind.value, "reason": item.reason,
            "actions": [action.value for action in item.available_actions]}
            for item in self.work.list_attention(work_id=work.work_id)
            if item.available_actions]
        steps = [] if work is None or work.production_plan is None else [
            {"title": step.instruction, "state": "current" if index == 0 else "upcoming"}
            for index, step in enumerate(work.production_plan.ordered_steps[:8])]
        focus = None if work is None else {
            "title": work.title or work.raw_user_requirement,
            "status": work.current_production_step,
            "reason": work.most_recent_meaningful_event,
            "next": work.what_happens_next,
            "human_action": bool(attention),
        }
        candidate_view = None if candidate is None else {key: candidate.get(key) for key in
            ("candidate_id", "candidate_fingerprint", "repository_revision", "tree",
             "entrypoint", "preview_kind", "artifacts", "verification", "authorization_pending")}
        return {"revision": _fingerprint(product["revision"], work_data, delivery,
                                         candidate_view, guardian, attention),
                "product": product, "work": work_data, "historical": bool(
                    work_id is not None and product["current_work"] is not None and
                    str(work_id) != product["current_work"]["id"]),
                "agenda": steps, "focus": focus, "reality": {
                    "work_status": None if work is None else work.status.value,
                    "accepted_version": product["accepted_version"],
                    "accepted_revision": product["accepted_revision"],
                    "candidate": candidate_view,
                    "guardian": guardian,
                    "deliveries": [] if delivery is None else delivery["deliveries"][:5],
                }, "actions": attention}

    def deliverable(self, owner_id: str, manifest_id: UUID) -> dict:
        collection = self.collections(owner_id)
        summary = next((row for row in collection["deliverables"]
                        if row["id"] == str(manifest_id)), None)
        if summary is None:
            raise ProductInvariantViolation("Deliverable is unavailable to this owner")
        detail = self.delivery.view(UUID(summary["work_id"]))
        exact = next(item for item in detail["deliveries"]
                     if item["manifest"]["id"] == str(manifest_id))
        guardian = ({"status": "NOT_STARTED", "finding_count": 0}
                    if self.guardian is None else
                    self.guardian.projection(UUID(summary["work_id"])))
        return {"revision": _fingerprint(summary, exact, guardian),
                "summary": summary, "manifest": exact["manifest"],
                "acceptance": exact["acceptance"], "current": exact["current"],
                "guardian": guardian}

    def bind_interaction(self, owner_id: str, product_id: UUID,
                         interaction_id: UUID) -> None:
        self.product(owner_id, product_id)
        with self.database.unit_of_work() as uow:
            uow.session.execute(product_workspace_interactions.insert().values(
                interaction_id=interaction_id, product_id=product_id))
            uow.commit()

    def interaction_product(self, owner_id: str, interaction_id: UUID) -> str | None:
        with self.database.unit_of_work() as uow:
            product_id = uow.session.execute(select(
                product_workspace_interactions.c.product_id).join(software_products,
                software_products.c.id == product_workspace_interactions.c.product_id).where(
                product_workspace_interactions.c.interaction_id == interaction_id,
                software_products.c.owner_id == owner_id)).scalar_one_or_none()
        return None if product_id is None else str(product_id)

    def latest_interaction(self, owner_id: str, product_id: UUID) -> str | None:
        self.product(owner_id, product_id)
        with self.database.unit_of_work() as uow:
            value = uow.session.execute(select(
                product_workspace_interactions.c.interaction_id).where(
                product_workspace_interactions.c.product_id == product_id).order_by(
                product_workspace_interactions.c.created_at.desc()).limit(1)
            ).scalar_one_or_none()
        return None if value is None else str(value)

    def query(self, owner_id: str, intent: QueryIntent) -> dict:
        collection = self.collections(owner_id)
        if intent.unsupported:
            raise ValueError("UNSUPPORTED_QUERY_DIMENSIONS: " + ", ".join(intent.unsupported))
        if intent.product_id is not None and str(intent.product_id) not in {
                row["id"] for row in collection["products"]}:
            raise ValueError("UNKNOWN_PRODUCT")
        if intent.guardian != "ANY" and self.guardian is None:
            raise ValueError("GUARDIAN_QUERY_UNAVAILABLE")
        if intent.kind == "products":
            rows = collection["products"]
        else:
            rows = collection[intent.kind]
        cutoff = None if intent.days == 0 else datetime.now(UTC) - timedelta(days=intent.days)
        result = []
        for row in rows:
            if intent.product_id is not None and str(intent.product_id) != row.get(
                    "product_id", row.get("id")):
                continue
            timestamp = row.get("created_at", row.get("updated_at"))
            if cutoff is not None and (timestamp is None or datetime.fromisoformat(timestamp) < cutoff):
                continue
            status = row.get("status", "")
            if intent.state == "ACTIVE" and status in {"COMPLETED", "DISCARDED", "ARCHIVED"}:
                continue
            if intent.state == "COMPLETED" and status not in {"COMPLETED"}:
                continue
            if intent.state == "BLOCKED" and status not in {"BLOCKED", "NEEDS_ATTENTION"}:
                continue
            if intent.state == "ATTENTION" and not any(
                    item["work_id"] == row.get("id") or
                    item["product_id"] == row.get("id")
                    for item in collection["attention"]):
                continue
            if intent.acceptance == "ACCEPTED" and row.get("acceptance") != "ACCEPT":
                continue
            if intent.acceptance == "PENDING" and row.get("acceptance") is not None:
                continue
            if intent.deployed != "ANY" and bool(row.get("deployed")) != (intent.deployed == "YES"):
                continue
            if intent.guardian != "ANY":
                work_id = row.get("work_id") if intent.kind == "deliverables" else row.get("id")
                if intent.kind == "products":
                    work_id = (row.get("current_work") or {}).get("id")
                if not work_id:
                    continue
                observed = self.guardian.projection(UUID(work_id))
                if intent.guardian == "PASS" and observed.get("gate") != "PASS":
                    continue
                if intent.guardian == "FINDINGS" and not observed.get("finding_count"):
                    continue
            result.append(row)
        return {"revision": collection["revision"], "query": intent.model_dump(mode="json"),
                "items": result[:100], "total": len(result)}
