"""Inspectable delivery from exact governed Runtime Commit evidence."""
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5
from zipfile import ZipFile, ZIP_DEFLATED

from sqlalchemy import insert, select

from spg.domain.delivery import (
    DeliveryArtifact, DeliveryManifest, DeliveryTarget, DeliveryTargetKind,
    DeliveryTargetRequest, HumanAcceptance, HumanAcceptanceRequest,
)
from spg.domain.product import ProductInvariantViolation, ProductRecordNotFound
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.delivery_schema import (
    work_delivery_targets, work_delivery_manifests, work_delivery_acceptances,
)
from spg.infrastructure.persistence.product_schema import product_works
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore

MAX_ARTIFACT_BYTES = 1024 * 1024
MAX_PACKAGE_BYTES = 10 * MAX_ARTIFACT_BYTES


def fingerprint(payload: dict) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def read_artifact(repository: str, revision: str, path: str) -> bytes:
    """Read only a bounded regular Markdown blob at an immutable Git revision."""
    parts = PurePosixPath(path)
    if (not re.fullmatch(r"[0-9a-f]{40,64}", revision)
            or parts.is_absolute() or str(parts) != path
            or any(part in {".", "..", ".git"} for part in parts.parts)
            or "\\" in path or ":" in path or "\x00" in path
            or not path.endswith(".md")):
        raise ProductInvariantViolation("Delivery artifact path or exact revision is invalid")
    def git(*args):
        try:
            return subprocess.run(
                ["git", "--no-replace-objects", "-C", str(Path(repository).resolve()), *args],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
            ).stdout
        except (OSError, subprocess.SubprocessError) as exc:
            raise ProductInvariantViolation("The exact delivery artifact is unavailable in its bound repository") from exc
    tree = git("ls-tree", revision, "--", ":(literal)" + path).decode("utf-8")
    if not tree.startswith(("100644 blob ", "100755 blob ")) or len(tree.splitlines()) != 1:
        raise ProductInvariantViolation("Delivery requires a regular Git blob; links and submodules are not deliverables")
    blob = revision + ":" + path
    size = int(git("cat-file", "-s", blob))
    if size > MAX_ARTIFACT_BYTES:
        raise ProductInvariantViolation("Delivery artifact exceeds the 1 MiB inspection limit")
    data = git("cat-file", "blob", blob)
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProductInvariantViolation("Document Package requires UTF-8 Markdown artifacts") from exc
    return data


class DeliveryApplicationService:
    """Product acceptance never authorizes a Candidate or advances a PWU."""
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _work(session, work_id: UUID):
        # Serialize target publication and Human decisions for the same Work.
        if session.execute(select(product_works.c.id).where(product_works.c.id == work_id).with_for_update()).scalar_one_or_none() is None:
            raise ProductRecordNotFound(f"Work not found: {work_id}")
        return ProductStore(session).work(work_id)

    @staticmethod
    def _target(session, work_id: UUID):
        payload = session.execute(select(work_delivery_targets.c.payload).where(work_delivery_targets.c.work_id == work_id)).scalar_one_or_none()
        return None if payload is None else DeliveryTarget.model_validate(payload)

    @staticmethod
    def _manifest(session, work_id: UUID, manifest_id: UUID):
        payload = session.execute(select(work_delivery_manifests.c.payload).where(
            (work_delivery_manifests.c.work_id == work_id) & (work_delivery_manifests.c.id == manifest_id)
        )).scalar_one_or_none()
        if payload is None:
            raise ProductRecordNotFound("Delivery manifest not found for this Work")
        return DeliveryManifest.model_validate(payload)

    def set_target(self, work_id: UUID, request: DeliveryTargetRequest) -> DeliveryTarget:
        if request.kind is not DeliveryTargetKind.DOCUMENT_PACKAGE:
            raise ProductInvariantViolation("This first delivery adapter supports Document Package only")
        with self.database.unit_of_work() as uow:
            self._work(uow.session, work_id)
            existing = self._target(uow.session, work_id)
            if existing is not None:
                if all(getattr(existing, field) == getattr(request, field) for field in DeliveryTargetRequest.model_fields):
                    return existing
                raise ProductInvariantViolation("The recorded delivery target is immutable for this first slice")
            target = DeliveryTarget(**request.model_dump(), id=uuid4(), work_id=work_id, created_at=datetime.now(UTC))
            uow.session.execute(insert(work_delivery_targets).values(
                id=target.id, work_id=work_id, payload=target.model_dump(mode="json"), created_at=target.created_at,
            ))
            uow.commit()
        return target

    @staticmethod
    def _trusted_basis(session, work_id):
        product = ProductStore(session)
        runtime = RuntimeStore(session)
        work = product.work(work_id)
        if work is None:
            raise ProductRecordNotFound(f"Work not found: {work_id}")
        binding = product.runtime_binding(work_id)
        if binding is None or binding.work_reality_revision_id != work.current_work_reality_revision_id:
            raise ProductInvariantViolation("Delivery requires a production cycle for the current Work Reality")
        summary = product.runtime_summary(binding)
        if (summary.runtime_commit_id is None or not summary.verification_results
                or any(value != "PASS" for value in summary.verification_results)):
            raise ProductInvariantViolation("Delivery requires passing Verification and a trusted Runtime Commit")
        commit = runtime.runtime_commit(summary.runtime_commit_id)
        resource = product.resource(binding.resource_id)
        if (commit is None or resource is None
                or binding.work_unit_id not in commit.satisfied_work_unit_ids
                or commit.repository_identity != resource.repository_identity):
            raise ProductInvariantViolation("Delivery evidence is outside this Work's exact production cycle")
        return work, binding, summary, commit, resource

    def publish(self, work_id: UUID) -> DeliveryManifest:
        with self.database.unit_of_work() as uow:
            self._work(uow.session, work_id)
            target = self._target(uow.session, work_id)
            if target is None:
                raise ProductInvariantViolation("Choose the Work delivery target and acceptance criteria first")
            work, binding, summary, commit, resource = self._trusted_basis(uow.session, work_id)
            artifacts = []
            total_size = 0
            for path in sorted(set(summary.artifact_paths)):
                data = read_artifact(resource.location_ref, commit.repository_revision, path)
                total_size += len(data)
                if total_size > MAX_PACKAGE_BYTES:
                    raise ProductInvariantViolation("Delivery package exceeds the 10 MiB inspection limit")
                artifacts.append(DeliveryArtifact(path=path, sha256=sha256(data).hexdigest(), size_bytes=len(data), media_type="text/markdown; charset=utf-8"))
            if not artifacts:
                raise ProductInvariantViolation("The trusted cycle has no inspectable document artifacts")
            payload = {
                "work_id": str(work_id), "target_id": str(target.id),
                "work_reality_revision_id": str(work.current_work_reality_revision_id) if work.current_work_reality_revision_id else None,
                "runtime_binding_id": str(binding.id), "runtime_commit_id": str(commit.id),
                "repository_identity": commit.repository_identity,
                "repository_revision": commit.repository_revision,
                "verification_record_ids": [str(item) for item in commit.verification_record_ids],
                "artifacts": [item.model_dump(mode="json") for item in artifacts],
            }
            digest = fingerprint(payload)
            manifest_id = uuid5(NAMESPACE_URL, "spg:delivery:" + digest)
            existing = uow.session.execute(select(work_delivery_manifests.c.payload).where(work_delivery_manifests.c.id == manifest_id)).scalar_one_or_none()
            if existing:
                return DeliveryManifest.model_validate(existing)
            manifest = DeliveryManifest(**payload, id=manifest_id, fingerprint=digest, created_at=datetime.now(UTC))
            uow.session.execute(insert(work_delivery_manifests).values(
                id=manifest.id, work_id=work_id, target_id=target.id, runtime_commit_id=commit.id,
                payload=manifest.model_dump(mode="json"), created_at=manifest.created_at,
            ))
            uow.commit()
        return manifest

    def view(self, work_id: UUID) -> dict:
        with self.database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            work = product.work(work_id)
            if work is None:
                raise ProductRecordNotFound(f"Work not found: {work_id}")
            target = self._target(uow.session, work_id)
            rows = uow.session.execute(select(work_delivery_manifests.c.payload).where(work_delivery_manifests.c.work_id == work_id).order_by(work_delivery_manifests.c.created_at.desc())).scalars().all()
            binding = product.runtime_binding(work_id)
            current_commit = None if binding is None else product.runtime_summary(binding).runtime_commit_id
            manifests = []
            for row in rows:
                manifest = DeliveryManifest.model_validate(row)
                decision = uow.session.execute(select(work_delivery_acceptances.c.payload).where(work_delivery_acceptances.c.manifest_id == manifest.id)).scalar_one_or_none()
                current = bool(binding and binding.id == manifest.runtime_binding_id and current_commit == manifest.runtime_commit_id and work.current_work_reality_revision_id == manifest.work_reality_revision_id)
                manifests.append({"manifest": row, "current": current, "acceptance": decision})
            return {"work_id": str(work_id), "target": None if target is None else target.model_dump(mode="json"),
                    "supported_target_kinds": [DeliveryTargetKind.DOCUMENT_PACKAGE.value], "deliveries": manifests}

    def artifact(self, work_id: UUID, manifest_id: UUID, path: str) -> bytes:
        with self.database.unit_of_work() as uow:
            manifest = self._manifest(uow.session, work_id, manifest_id)
            descriptor = next((item for item in manifest.artifacts if item.path == path), None)
            if descriptor is None:
                raise ProductRecordNotFound("Artifact is not included in this exact delivery manifest")
            product = ProductStore(uow.session)
            binding = next((item for item in product.runtime_bindings(work_id) if item.id == manifest.runtime_binding_id), None)
            resource = None if binding is None else product.resource(binding.resource_id)
            if resource is None:
                raise ProductInvariantViolation("Delivery's bound repository is unavailable")
        data = read_artifact(resource.location_ref, manifest.repository_revision, path)
        if len(data) != descriptor.size_bytes or sha256(data).hexdigest() != descriptor.sha256:
            raise ProductInvariantViolation("Delivery bytes differ from the exact published manifest")
        return data

    def package(self, work_id: UUID, manifest_id: UUID) -> bytes:
        with self.database.unit_of_work() as uow:
            manifest = self._manifest(uow.session, work_id, manifest_id)
            target = self._target(uow.session, work_id)
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as archive:
            archive.writestr("delivery-manifest.json", manifest.model_dump_json(indent=2))
            archive.writestr("delivery-target.json", target.model_dump_json(indent=2))
            for artifact in manifest.artifacts:
                archive.writestr("artifacts/" + artifact.path, self.artifact(work_id, manifest_id, artifact.path))
        return output.getvalue()

    def decide(self, work_id: UUID, manifest_id: UUID, request: HumanAcceptanceRequest) -> HumanAcceptance:
        with self.database.unit_of_work() as uow:
            self._work(uow.session, work_id)
            manifest = self._manifest(uow.session, work_id, manifest_id)
            if manifest.fingerprint != request.manifest_fingerprint:
                raise ProductInvariantViolation("Human acceptance must reference the exact displayed manifest fingerprint")
            work, binding, _, commit, _ = self._trusted_basis(uow.session, work_id)
            if (manifest.runtime_binding_id != binding.id or manifest.runtime_commit_id != commit.id
                    or manifest.work_reality_revision_id != work.current_work_reality_revision_id):
                raise ProductInvariantViolation("Delivery is stale against current Work Reality or production cycle")
            existing = uow.session.execute(select(work_delivery_acceptances.c.payload).where(work_delivery_acceptances.c.manifest_id == manifest_id)).scalar_one_or_none()
            if existing:
                record = HumanAcceptance.model_validate(existing)
                if all(getattr(record, field) == getattr(request, field) for field in HumanAcceptanceRequest.model_fields):
                    return record
                raise ProductInvariantViolation("This exact delivery already has an immutable Human decision")
            record = HumanAcceptance(**request.model_dump(), id=uuid4(), manifest_id=manifest_id, created_at=datetime.now(UTC))
            uow.session.execute(insert(work_delivery_acceptances).values(
                id=record.id, manifest_id=manifest_id, payload=record.model_dump(mode="json"), created_at=record.created_at,
            ))
            uow.commit()
        return record
