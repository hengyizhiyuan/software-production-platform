"""Read-only Work source inspection and Human-owned working agreements."""

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
import subprocess
from uuid import UUID, uuid4

from sqlalchemy import insert, select

from spg.infrastructure.persistence import Database, ProductStore
from spg.infrastructure.persistence.control_room_schema import work_agreement_events
from spg.infrastructure.persistence.product_schema import product_works
from spg.application.connectors import ConnectorResolver
from spg.application.measurement import ProductionMeasurementService
from spg.infrastructure.persistence.native_execution_schema import (
    executor_queue, execution_allocations, executor_leases,
    executor_worker_registrations, native_attempt_states, self_refine_events,
)
from spg.infrastructure.persistence.runtime_schema import (
    production_work_units, execution_attempts, baseline_candidates, verification_records,
)
from spg.infrastructure.persistence.product_schema import work_runtime_bindings
from spg.infrastructure.persistence.delivery_schema import (
    work_delivery_manifests, work_delivery_acceptances, work_delivery_runtimes,
)
from spg.application.owner_reality import current_owner_repository_reality
from spg.domain.product import ProductInvariantViolation


class ControlRoomError(ValueError):
    pass


_DOCUMENT_SUFFIXES = {".md", ".markdown", ".rst", ".txt", ".adoc"}
_CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".html", ".sql", ".sh", ".yaml", ".yml", ".json", ".toml", ".rs", ".go"}
_MAX_FILE_BYTES = 512_000


def _git(root: Path, *arguments: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments], capture_output=True,
            timeout=8, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ControlRoomError("Repository source is unavailable for inspection") from error
    if result.returncode:
        raise ControlRoomError("Repository revision is unavailable for inspection")
    return result.stdout


def _kind(path: str) -> str | None:
    suffix = PurePosixPath(path).suffix.lower()
    if path.startswith("docs/") and suffix in _DOCUMENT_SUFFIXES | _CODE_SUFFIXES:
        return "DOCUMENTATION"
    if suffix in _DOCUMENT_SUFFIXES or path.lower() in {"readme", "license"}:
        return "DOCUMENTATION"
    if suffix in _CODE_SUFFIXES:
        return "CODE"
    return None


class ControlRoomService:
    def __init__(self, database: Database, work_service, asset_service=None,
                 candidate_preview_service=None, delivery_runtime_service=None) -> None:
        self.database = database
        self.work_service = work_service
        self.asset_service = asset_service
        self.candidate_preview_service = candidate_preview_service
        self.delivery_runtime_service = delivery_runtime_service

    def platform_summary(self) -> dict:
        """Bounded platform health from current queue, worker and Work facts."""
        now = datetime.now(UTC)
        with self.database.unit_of_work() as uow:
            session = uow.session
            workers = session.execute(select(executor_worker_registrations)).mappings().all()
            queue = session.execute(select(executor_queue).where(
                executor_queue.c.condition.in_((
                    "QUEUED", "WAITING_RESOURCE", "WAITING_HUMAN", "ALLOCATED",
                    "EXECUTING", "CHECKPOINTED", "RETURNED_TO_QUEUE",
                )),
            )).mappings().all()
            leases = session.execute(select(executor_leases).where(
                executor_leases.c.released_at.is_(None),
            )).mappings().all()
            recent = session.execute(select(product_works.c.id).order_by(
                product_works.c.updated_at.desc(), product_works.c.id.desc(),
            ).limit(20)).scalars().all()
            recent_failures = session.execute(select(self_refine_events.c.id).where(
                self_refine_events.c.final_result.in_(("FAILED", "ESCALATED")),
            ).order_by(self_refine_events.c.created_at.desc()).limit(20)).scalars().all()
        live_worker_ids = {row["worker_id"] for row in workers if row["expires_at"] > now}
        expired_leases = [row for row in leases if row["deadline"] <= now or
                          row["worker_id"] not in live_worker_ids]
        conditions = {}
        for item in queue:
            conditions[item["condition"]] = conditions.get(item["condition"], 0) + 1
        diagnoses = [self.diagnosis(work_id) for work_id in recent]
        by_state = {}
        for item in diagnoses:
            by_state[item["state"]] = by_state.get(item["state"], 0) + 1
        spend = {}
        unreported = 0
        for item in diagnoses:
            observed = item["economics"]["observed_provider_spend"]
            unreported += observed.get("unreported_attempt_count", 0)
            for currency, amount in observed.get("by_currency", {}).items():
                spend[currency] = spend.get(currency, 0) + amount
        return {"observed_at": now.isoformat(),
                "workers": {"registered": len(workers), "healthy": len(live_worker_ids),
                            "expired": len(workers) - len(live_worker_ids)},
                "queue": {"active_count": len(queue), "by_condition": conditions},
                "leases": {"active_count": len(leases), "unhealthy_count": len(expired_leases)},
                "recent_works": {"sample_size": len(diagnoses), "by_state": by_state,
                                 "diagnostics": [{"work_id": item["work_id"],
                                                  "state": item["state"],
                                                  "root_cause": item["root_cause"],
                                                  "evidence_refs": item["evidence_refs"]}
                                                 for item in diagnoses]},
                "recent_self_refine_failures": len(recent_failures),
                "recent_work_provider_spend": {"sample_size": len(diagnoses),
                    "by_currency": spend,
                    "unreported_attempt_count": unreported,
                    "status": "PARTIAL" if spend and unreported else
                              "OBSERVED" if spend else "UNREPORTED"}}

    def diagnosis(self, work_id: UUID) -> dict:
        """Correlate the Work's current production facts into one operator view."""
        work = self.work_service.get_work(work_id)
        economics = ProductionMeasurementService(self.database).graph_economics(work_id)
        gaps = [item for item in ConnectorResolver(self.database).gaps_for_work(work_id)
                if item["condition"] == "OPEN"]
        now = datetime.now(UTC)
        with self.database.unit_of_work() as uow:
            session = uow.session
            product_id = session.execute(select(product_works.c.product_id).where(
                product_works.c.id == work_id,
            )).scalar_one_or_none()
            runs = session.execute(select(work_runtime_bindings.c.production_run_id).where(
                work_runtime_bindings.c.work_id == work_id,
            )).scalars().all()
            units = [] if not runs else session.execute(select(production_work_units).where(
                production_work_units.c.production_run_id.in_(runs),
            )).mappings().all()
            unit_ids = [row["id"] for row in units]
            attempts = [] if not unit_ids else session.execute(select(execution_attempts).where(
                execution_attempts.c.work_unit_id.in_(unit_ids),
            )).mappings().all()
            attempt_ids = [row["id"] for row in attempts]
            queues = [] if not attempt_ids else session.execute(select(executor_queue).where(
                executor_queue.c.attempt_id.in_(attempt_ids),
            )).mappings().all()
            leases = [] if not attempt_ids else session.execute(select(executor_leases).where(
                executor_leases.c.attempt_id.in_(attempt_ids),
                executor_leases.c.released_at.is_(None),
            )).mappings().all()
            states = [] if not attempt_ids else session.execute(select(native_attempt_states).where(
                native_attempt_states.c.attempt_id.in_(attempt_ids),
            )).mappings().all()
            worker_ids = [row["worker_id"] for row in leases]
            workers = [] if not worker_ids else session.execute(select(executor_worker_registrations).where(
                executor_worker_registrations.c.worker_id.in_(worker_ids),
            )).mappings().all()
            refine = session.execute(select(self_refine_events).where(
                self_refine_events.c.work_id == work_id,
            ).order_by(self_refine_events.c.created_at.desc()).limit(5)).mappings().all()
            candidates = [] if not runs else session.execute(select(baseline_candidates).where(
                baseline_candidates.c.production_run_id.in_(runs),
            ).order_by(baseline_candidates.c.sealed_at.desc())).mappings().all()
            verifications = [] if not runs else session.execute(select(verification_records).where(
                verification_records.c.production_run_id.in_(runs),
            )).mappings().all()
            manifests = session.execute(select(work_delivery_manifests).where(
                work_delivery_manifests.c.work_id == work_id,
            )).mappings().all()
            manifest_ids = [row["id"] for row in manifests]
            acceptances = [] if not manifest_ids else session.execute(select(work_delivery_acceptances).where(
                work_delivery_acceptances.c.manifest_id.in_(manifest_ids),
            )).mappings().all()
            previews = [] if not manifest_ids else session.execute(select(work_delivery_runtimes).where(
                work_delivery_runtimes.c.manifest_id.in_(manifest_ids),
            )).mappings().all()
        worker_by_id = {row["worker_id"]: row for row in workers}
        live = [row for row in leases if row["deadline"] <= now or
                worker_by_id.get(row["worker_id"]) is None or
                worker_by_id[row["worker_id"]]["expires_at"] <= now]
        waiting = [row for row in queues if row["condition"] in {"QUEUED", "WAITING_RESOURCE", "RETURNED_TO_QUEUE"}]
        preview_status = []
        preview_unhealthy = []
        if self.candidate_preview_service is not None:
            try:
                candidate_preview = self.candidate_preview_service.store.current_candidate_preview(work_id)
                if candidate_preview is not None:
                    status = candidate_preview.status.value
                    if status == "READY":
                        healthy = self.candidate_preview_service.provider.probe(
                            candidate_preview.id, candidate_preview.repository_revision,
                            candidate_preview.repository_tree, mode=candidate_preview.mode)
                        if not healthy:
                            status = "UNHEALTHY"
                    preview_status.append({"preview_id": str(candidate_preview.id), "status": status})
                    if status in {"FAILED", "UNHEALTHY"}:
                        preview_unhealthy.append(f"candidate-preview:{candidate_preview.id}")
            except Exception:
                preview_status.append({"preview_id": None, "status": "UNHEALTHY"})
                preview_unhealthy.append(f"work:{work_id}:candidate-preview")
        for row in previews:
            status = (row["payload"] or {}).get("status", "UNKNOWN")
            if self.delivery_runtime_service is not None:
                try:
                    status = self.delivery_runtime_service.view(work_id, row["manifest_id"]).get("status", status)
                except Exception:
                    status = "UNHEALTHY"
            preview_status.append({"manifest_id": str(row["manifest_id"]), "status": status})
            if status in {"FAILED", "UNHEALTHY", "NOT_READY", "STOPPED"}:
                preview_unhealthy.append(f"delivery-manifest:{row['manifest_id']}")
        if gaps:
            cause = "BLOCKED_BY_CREDENTIAL" if any("credential" in row["reason"].lower() or
                "authorization" in row["reason"].lower() for row in gaps) else "BLOCKED_BY_CAPABILITY"
            explanation = gaps[0]["reason"]
            evidence = [f"capability-gap:{row['id']}" for row in gaps]
        elif live:
            cause, explanation = "WORKER_LOST", "Worker lease or registration expired"
            evidence = [f"executor-lease:{row['id']}" for row in live]
        elif any(row["condition"] == "WAITING_RESOURCE" for row in waiting):
            cause, explanation = "WAITING_FOR_CAPACITY", "PWU is waiting for execution resources"
            evidence = [f"executor-queue:{row['id']}" for row in waiting]
        elif waiting:
            cause, explanation = "QUEUED", "PWU is queued for an Executor worker"
            evidence = [f"executor-queue:{row['id']}" for row in waiting]
        elif preview_unhealthy:
            cause, explanation = "PREVIEW_UNHEALTHY", "Delivery preview runtime is unhealthy"
            evidence = preview_unhealthy
        elif any(row["runtime_mode"] in {"RECONCILING", "RESUME_REQUESTED"} for row in states):
            cause, explanation = "RECOVERING", "Native Executor is reconciling an interrupted attempt"
            evidence = [f"execution-attempt:{row['attempt_id']}" for row in states]
        elif any(row["runtime_mode"] in {"RUNNING", "PAUSING"} for row in states):
            cause, explanation = "RUNNING", "Native Executor is active"
            evidence = [f"execution-attempt:{row['attempt_id']}" for row in states]
        elif work.human_attention_required or any(row["id"] not in {item["manifest_id"] for item in acceptances}
                                                       for row in manifests):
            cause, explanation = "WAITING_FOR_HUMAN", "Human decision or delivery acceptance is pending"
            evidence = [f"delivery-manifest:{row['id']}" for row in manifests]
        elif work.status.value == "COMPLETED":
            cause, explanation, evidence = "COMPLETED", "Work completed", []
        elif work.status.value in {"BLOCKED", "NEEDS_ATTENTION"}:
            cause, explanation, evidence = "BLOCKED", work.most_recent_meaningful_event, []
        else:
            cause, explanation, evidence = "HEALTHY", work.what_happens_next, []
        return {"work_id": str(work_id), "product_id": None if product_id is None else str(product_id),
                "state": cause, "root_cause": explanation, "evidence_refs": evidence,
                "work_status": work.status.value,
                "pwu": [{"id": str(row["id"]), "node_id": row["node_id"],
                         "condition": row["condition"]} for row in units],
                "queue": [{"id": str(row["id"]), "pwu_id": str(row["pwu_id"]),
                           "condition": row["condition"], "wait_reason": row["wait_reason"]} for row in queues],
                "worker": [{"id": row["worker_id"], "lease_deadline": row["deadline"].isoformat(),
                            "healthy": row not in live} for row in leases],
                "self_refine": [{"id": str(row["id"]), "status": row["status"],
                                 "diagnosis": row["diagnosis_summary"]} for row in refine],
                "candidate_ids": [str(row["id"]) for row in candidates],
                "verification": {"count": len(verifications),
                                 "failed": sum(row["result"] not in {"PASS", "PASSED"} for row in verifications)},
                "preview": preview_status,
                "economics": economics}

    def _repository(self, work_id: UUID):
        work = self.work_service.get_work(work_id)
        with self.database.unit_of_work() as uow:
            resource = ProductStore(uow.session).resource_for_work(work_id)
        if resource is None or resource.kind.value != "REPOSITORY":
            raise ControlRoomError("This Work has no bound repository to inspect")
        if (self.asset_service is not None
                and self.asset_service.managed_source.has_source(
                    resource.repository_identity)
                and not Path(resource.location_ref).exists()):
            self.asset_service.managed_source.recover(
                resource.repository_identity, Path(resource.location_ref))
        try:
            root = Path(resource.location_ref).resolve(strict=True)
        except OSError as error:
            raise ControlRoomError("Bound repository source is unavailable for inspection") from error
        revision = _git(root, "rev-parse", "--verify", f"{resource.authoritative_ref}^{{commit}}").decode().strip()
        return work, resource, root, revision

    def _owner_repository_reality(self, resource, root: Path, revision: str) -> dict | None:
        recorder = getattr(self.work_service, "production_recorder", None)
        reality = getattr(recorder, "reality", None)
        if reality is None:
            return None
        try:
            return current_owner_repository_reality(reality, resource, root, revision)
        except ProductInvariantViolation as error:
            raise ControlRoomError(str(error)) from error

    def sources(self, work_id: UUID) -> dict:
        gaps = [
            {
                "capability_id": item["capability_id"],
                "condition": item["condition"],
                "reason": item["reason"],
            }
            for item in (
                ConnectorResolver(self.database).gaps_for_work(work_id)
                if self.database is not None else ()
            )
            if item["condition"] == "OPEN"
        ]
        try:
            work, resource, root, revision = self._repository(work_id)
        except ControlRoomError:
            latest = (
                None
                if self.asset_service is None
                else self.asset_service.latest_attempt_for_work(work_id)
            )
            if latest is None:
                raise
            condition = latest.get("condition", "NOT_STARTED")
            return {
                "revision": None,
                "repository_identity": latest.get("repository_identity"),
                "selection": "ACQUISITION_STATE",
                "sources": [],
                "capability_gaps": gaps,
                "acquisition": {
                    "state": condition,
                    "attempt_number": latest.get("attempt_number"),
                    "failure_category": latest.get("failure_category"),
                    "message": latest.get("human_message") or latest.get("message"),
                    "retry_available": condition in {
                        "WAITING_FOR_AUTHORIZATION",
                        "FAILED_RETRYABLE",
                    },
                    "authorization": {
                        "required": condition == "WAITING_FOR_AUTHORIZATION",
                        "integration_available": bool(
                            getattr(getattr(getattr(self.asset_service,
                                "github_delivery", None), "settings", None),
                                "github_read_token", None)),
                        "human_action": (
                            "Create a scoped GitHub READ Access Grant, then retry "
                            "this persisted acquisition."
                            if condition == "WAITING_FOR_AUTHORIZATION"
                            else None
                        ),
                    },
                    "source": latest.get("source"),
                },
            }
        relevance: set[str] = {
            item.repository_relative_path for item in resource.context_references
        }
        if work.artifact_target:
            relevance.add(work.artifact_target.path)
        if work.change_contract:
            relevance.update(item.path for item in work.change_contract.exact_targets)
        if work.change_proposal:
            relevance.update(item.path for item in work.change_proposal.proposed_targets)
        try:
            result = self.work_service.get_work_result(work_id)
            relevance.update(result.produced_artifacts)
        except (AttributeError, ValueError):
            pass
        tree = _git(root, "ls-tree", "-r", "-z", revision)
        entries = []
        for record in tree.split(b"\0"):
            if not record:
                continue
            meta, raw_path = record.split(b"\t", 1)
            mode, object_type, _object_id = meta.split(b" ", 2)
            if object_type != b"blob" or mode == b"120000":
                continue
            path = raw_path.decode("utf-8", errors="surrogateescape")
            kind = _kind(path)
            if kind:
                entries.append({"path": path, "kind": kind, "relevant": path in relevance})
        entries.sort(key=lambda item: item["path"].casefold())
        return {
            "revision": revision, "repository_identity": resource.repository_identity,
            "selection": "WORK_RELEVANT" if any(item["relevant"] for item in entries) else "REPOSITORY_OVERVIEW",
            "sources": entries,
            "engineering_reality": self._owner_repository_reality(
                resource, root, revision),
            "capability_gaps": gaps,
            "branch_operation": (
                {
                    "intake_request_id": latest.get("intake_request_id"),
                    "condition": latest.get("condition"),
                    "target_branch": latest.get("target_branch"),
                    "human_message": latest.get("human_message"),
                }
                if self.asset_service is not None
                and (latest := self.asset_service.latest_attempt_for_work(work_id))
                and latest.get("operation_kind") == "CREATE_BRANCH"
                else None
            ),
            "acquisition": {
                "state": "READY",
                "attempt_number": None,
                "failure_category": None,
                "message": "Repository is ready.",
                "retry_available": False,
                "authorization": {
                    "required": False,
                    "integration_available": False,
                    "human_action": None,
                },
                "branch": getattr(resource, "authoritative_ref", None),
                "revision": revision,
            },
        }

    def file(self, work_id: UUID, path: str, revision: str) -> dict:
        source = self.sources(work_id)
        if revision != source["revision"]:
            raise ControlRoomError("Repository revision changed; refresh the source list")
        if path not in {item["path"] for item in source["sources"]}:
            raise ControlRoomError("File is not in this Work's inspected source list")
        parts = PurePosixPath(path).parts
        if not parts or path.startswith("/") or any(part in {".", ".."} for part in parts):
            raise ControlRoomError("Invalid repository path")
        _work, _resource, root, _revision = self._repository(work_id)
        raw = _git(root, "show", f"{revision}:{path}")
        if len(raw) > _MAX_FILE_BYTES or b"\0" in raw:
            raise ControlRoomError("This file is not available in the text viewer")
        return {"path": path, "kind": _kind(path), "revision": revision, "content": raw.decode("utf-8", errors="replace")}

    def agreements(self, work_id: UUID) -> list[dict]:
        self.work_service.get_work(work_id)
        with self.database.unit_of_work() as uow:
            rows = uow.session.execute(
                select(work_agreement_events).where(work_agreement_events.c.work_id == work_id)
                .order_by(work_agreement_events.c.created_at, work_agreement_events.c.sequence)
            ).mappings().all()
        groups: dict[UUID, list] = defaultdict(list)
        for row in rows:
            groups[row["agreement_id"]].append(row)
        return [
            {
                "agreement_id": str(agreement_id), "work_id": str(work_id),
                "type": history[0]["agreement_type"], "content": history[0]["content"],
                "state": "ACTIVE" if history[-1]["kind"] == "CREATED" else "ABANDONED",
                "persistence_state": history[0]["persistence_state"],
                "persistence_path": history[0]["persistence_path"],
                "history": [
                    {"kind": event["kind"], "actor_identity": event["actor_identity"],
                     "created_at": event["created_at"].isoformat()}
                    for event in history
                ],
            }
            for agreement_id, history in groups.items()
        ]

    def create_agreement(self, work_id: UUID, *, content: str, agreement_type: str, actor_identity: str) -> dict:
        self.work_service.get_work(work_id)
        content = content.strip()
        if not 3 <= len(content) <= 500 or agreement_type not in {"DECISION", "CONSTRAINT", "REMINDER", "DEFERRED", "CANDIDATE"}:
            raise ControlRoomError("Agreement type or content is invalid")
        if not actor_identity.strip():
            raise ControlRoomError("Human identity is required")
        with self.database.unit_of_work() as uow:
            uow.session.execute(select(product_works.c.id).where(product_works.c.id == work_id).with_for_update()).one()
            rows = uow.session.execute(
                select(work_agreement_events).where(work_agreement_events.c.work_id == work_id)
                .order_by(work_agreement_events.c.agreement_id, work_agreement_events.c.sequence)
            ).mappings().all()
            latest = {row["agreement_id"]: row["kind"] for row in rows}
            if sum(kind == "CREATED" for kind in latest.values()) >= 12:
                raise ControlRoomError("This Work already has 12 active agreements; abandon one before adding more")
            agreement_id = uuid4()
            uow.session.execute(insert(work_agreement_events).values(
                id=uuid4(), work_id=work_id, agreement_id=agreement_id, sequence=1, kind="CREATED",
                agreement_type=agreement_type, content=content, actor_identity=actor_identity.strip(),
                persistence_state="NOT_PERSISTED", persistence_path=None,
            ))
            uow.commit()
        return next(item for item in self.agreements(work_id) if item["agreement_id"] == str(agreement_id))

    def abandon_agreement(self, work_id: UUID, agreement_id: UUID, *, actor_identity: str) -> dict:
        self.work_service.get_work(work_id)
        if not actor_identity.strip():
            raise ControlRoomError("Human identity is required")
        with self.database.unit_of_work() as uow:
            uow.session.execute(select(product_works.c.id).where(product_works.c.id == work_id).with_for_update()).one()
            history = uow.session.execute(
                select(work_agreement_events).where(
                    work_agreement_events.c.work_id == work_id,
                    work_agreement_events.c.agreement_id == agreement_id,
                ).order_by(work_agreement_events.c.sequence).with_for_update()
            ).mappings().all()
            if not history or history[-1]["kind"] != "CREATED":
                raise ControlRoomError("No active agreement with this identity exists in the Work")
            original = history[0]
            uow.session.execute(insert(work_agreement_events).values(
                id=uuid4(), work_id=work_id, agreement_id=agreement_id, sequence=2, kind="ABANDONED",
                agreement_type=original["agreement_type"], content=original["content"],
                actor_identity=actor_identity.strip(), persistence_state=original["persistence_state"],
                persistence_path=original["persistence_path"],
            ))
            uow.commit()
        return next(item for item in self.agreements(work_id) if item["agreement_id"] == str(agreement_id))
