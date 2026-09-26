"""Read-only Work source inspection and Human-owned working agreements."""

from collections import defaultdict
from pathlib import Path, PurePosixPath
import subprocess
from uuid import UUID, uuid4

from sqlalchemy import insert, select

from spg.infrastructure.persistence import Database, ProductStore
from spg.infrastructure.persistence.control_room_schema import work_agreement_events
from spg.infrastructure.persistence.product_schema import product_works
from spg.application.connectors import ConnectorResolver
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
    def __init__(self, database: Database, work_service, asset_service=None) -> None:
        self.database = database
        self.work_service = work_service
        self.asset_service = asset_service

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
