"""Inspectable delivery from exact governed Runtime Commit evidence."""
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from sqlalchemy import insert, select

from spg.domain.delivery import (
    DeliveryArtifact, DeliveryManifest, DeliveryTarget, DeliveryTargetKind,
    DeliveryTargetRequest, HumanAcceptance, HumanAcceptanceRequest, SoftwareDeliveryDetails,
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


def read_artifact(repository: str, revision: str, path: str, *, software: bool = False) -> bytes:
    """Read a bounded regular blob at an immutable Git revision, never a working tree."""
    parts = PurePosixPath(path)
    if (not re.fullmatch(r"[0-9a-f]{40,64}", revision)
            or parts.is_absolute() or str(parts) != path
            or any(part in {".", "..", ".git"} for part in parts.parts)
            or "\\" in path or ":" in path or "\x00" in path
            or any(ord(char) < 32 for char in path)
            or (not software and not path.endswith(".md"))):
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
    if not software:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProductInvariantViolation("Document Package requires UTF-8 Markdown artifacts") from exc
    return data


def artifact_media_type(path: str) -> str:
    return {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
        ".mjs": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".json": "application/json", ".md": "text/markdown; charset=utf-8",
        ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}.get(PurePosixPath(path).suffix, "application/octet-stream")


def git_bytes(repository: str, *args: str) -> bytes:
    try:
        return subprocess.run(["git", "--no-replace-objects", "-C", str(repository), *args], check=True, capture_output=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise ProductInvariantViolation("Exact software repository evidence is unavailable") from exc


class DeliveryApplicationService:
    """Product acceptance never authorizes a Candidate or advances a PWU."""
    def __init__(self, database: Database):
        self.database = database
        self.runtime_probe = None

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

    def candidate_context(self, work_id: UUID) -> dict | None:
        """Read the current sealed, verified result without granting integration authority."""
        with self.database.unit_of_work() as uow:
            product, runtime = ProductStore(uow.session), RuntimeStore(uow.session)
            work = product.work(work_id)
            if work is None:
                raise ProductRecordNotFound(f"Work not found: {work_id}")
            binding = product.runtime_binding(work_id)
            if binding is None or binding.work_reality_revision_id != work.current_work_reality_revision_id:
                return None
            summary = product.runtime_summary(binding)
            if summary.candidate_id is None:
                return None
            candidate = runtime.baseline_candidate(summary.candidate_id)
            if (candidate is None or binding.work_unit_id not in candidate.satisfied_work_unit_ids
                    or candidate.proposed_snapshot_id != summary.proposed_snapshot_id
                    or not candidate.verification_record_ids or
                    any(result != "PASS" for result in summary.verification_results)):
                raise ProductInvariantViolation("Current Candidate lacks exact passing Verification")
            snapshot = runtime.proposed_snapshot(candidate.proposed_snapshot_id)
            observation = None if snapshot is None else runtime.repository_observation_by_id(snapshot.repository_observation_id)
            dispatch = None if observation is None else runtime.execution_dispatch(observation.dispatch_id)
            if dispatch is None:
                raise ProductInvariantViolation("Current Candidate has no exact repository workspace")
            repository = dispatch.workspace.repository_path
            tree = git_bytes(repository, "rev-parse", candidate.proposed_commit_identity + "^{tree}").decode().strip()
            if tree != candidate.proposed_tree_identity:
                raise ProductInvariantViolation("Candidate preview tree differs from sealed Reality")
            paths = git_bytes(repository, "ls-tree", "-r", "--name-only", "-z", candidate.proposed_commit_identity).decode().split("\0")[:-1]
            if len(paths) > 500:
                raise ProductInvariantViolation("Candidate preview exceeds the bounded file inventory")
            entrypoint = "index.html" if "index.html" in paths else next(
                (path for path in summary.artifact_paths if path.endswith(".html") and path in paths), None)
            return {"candidate_id": str(candidate.id), "candidate_fingerprint": candidate.fingerprint,
                    "repository_revision": candidate.proposed_commit_identity, "tree": tree,
                    "repository_path": repository, "paths": paths, "entrypoint": entrypoint,
                    "artifacts": list(summary.artifact_paths),
                    "verification": [f"{name}: {result}" for name, result in zip(
                        summary.verification_obligations, summary.verification_results, strict=True)],
                    "authorization_pending": summary.authorization_id is None}

    @staticmethod
    def _derived_target(work, summary) -> DeliveryTargetRequest | None:
        """Only one unambiguous current artifact form is defaultable."""
        paths = set(summary.artifact_paths)
        html = [path for path in paths if path.endswith(".html")]
        if (work.production_plan is not None
                and work.production_plan.target_kind.value == "CODE_WORK" and len(html) == 1):
            criteria = (work.desired_outcome, *work.constraints,
                f"{html[0]} opens as a browser-runnable static Web result.",
                "All governed verification obligations for the current repository revision pass.")
            return DeliveryTargetRequest(kind=DeliveryTargetKind.SOFTWARE_ARTIFACT,
                title=work.refined_title or work.desired_outcome[:255],
                acceptance_criteria=tuple(dict.fromkeys(criteria)),
                authority_identity="system:governed-delivery-context",
                software_form=DeliveryTargetKind.WEB_APPLICATION,
                runtime_recipe={"adapter": "STATIC_WEB", "entrypoint": html[0]})
        return None

    def context(self, work_id: UUID) -> dict:
        """Explain known delivery facts before any Human input or publication."""
        with self.database.unit_of_work() as uow:
            work = ProductStore(uow.session).work(work_id)
            if work is None:
                raise ProductRecordNotFound(f"Work not found: {work_id}")
            target = self._target(uow.session, work_id)
            binding = ProductStore(uow.session).runtime_binding(work_id)
            summary = None if binding is None or binding.work_reality_revision_id != work.current_work_reality_revision_id else ProductStore(uow.session).runtime_summary(binding)
            commit = None if summary is None or summary.runtime_commit_id is None else RuntimeStore(uow.session).runtime_commit(summary.runtime_commit_id)
            derived = None if target or commit is None else self._derived_target(work, summary)
            chosen = target or derived
            target_source = (
                "GOVERNED_REALITY"
                if chosen is not None and chosen.authority_identity == "system:governed-delivery-context"
                else "HUMAN"
                if target is not None
                else "GOVERNED_REALITY"
                if derived is not None
                else None
            )
            return {"work_id": str(work_id), "desired_outcome": work.desired_outcome,
                "target": None if chosen is None else chosen.model_dump(mode="json"),
                "target_source": target_source,
                "artifacts": [] if summary is None else list(summary.artifact_paths),
                "verification": [] if summary is None else [f"{name}: {result}" for name, result in zip(
                    summary.verification_obligations, summary.verification_results, strict=True)],
                "repository_revision": None if commit is None else commit.repository_revision,
                "trusted": commit is not None,
                "blocker": None if chosen is not None else "No single supported current delivery target can be derived; choose the missing target."}

    def candidate_artifact(self, work_id: UUID, candidate_fingerprint: str, path: str) -> bytes:
        """Read one current sealed-Candidate blob; preview never grants integration authority."""
        context = self.candidate_context(work_id)
        if context is None or context["candidate_fingerprint"] != candidate_fingerprint:
            raise ProductInvariantViolation("Candidate preview is stale against current Work Reality")
        if path not in context["paths"] or not path.endswith((".html", ".js", ".mjs", ".css", ".json", ".svg", ".png", ".ico")):
            raise ProductRecordNotFound("Candidate artifact is not previewable")
        return read_artifact(context["repository_path"], context["repository_revision"], path, software=True)

    def candidate_download(self, work_id: UUID, candidate_fingerprint: str, path: str) -> bytes:
        """Download a declared produced artifact from the same immutable Candidate binding."""
        context = self.candidate_context(work_id)
        if context is None or context["candidate_fingerprint"] != candidate_fingerprint:
            raise ProductInvariantViolation("Candidate download is stale against current Work Reality")
        if path not in context["artifacts"] or path not in context["paths"]:
            raise ProductRecordNotFound("Artifact is not included in the current produced result")
        return read_artifact(context["repository_path"], context["repository_revision"], path, software=True)

    @staticmethod
    def _manifest(session, work_id: UUID, manifest_id: UUID):
        payload = session.execute(select(work_delivery_manifests.c.payload).where(
            (work_delivery_manifests.c.work_id == work_id) & (work_delivery_manifests.c.id == manifest_id)
        )).scalar_one_or_none()
        if payload is None:
            raise ProductRecordNotFound("Delivery manifest not found for this Work")
        return DeliveryManifest.model_validate(payload)

    def set_target(self, work_id: UUID, request: DeliveryTargetRequest) -> DeliveryTarget:
        if request.kind not in {DeliveryTargetKind.DOCUMENT_PACKAGE, DeliveryTargetKind.SOFTWARE_ARTIFACT}:
            raise ProductInvariantViolation("Choose Document Package or Software Artifact with a supported runtime adapter")
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

    @staticmethod
    def _software_basis(session, target, binding, commit, resource):
        from spg.domain.verification import VerificationResultValue
        runtime = RuntimeStore(session)
        unit = runtime.work_unit(binding.work_unit_id)
        contract = None if unit is None else unit.completion_contract.change_contract
        if contract is None:
            raise ProductInvariantViolation("Software delivery requires a governed Code Work contract")
        records = [runtime.verification_record(identity) for identity in commit.verification_record_ids]
        if not records or any(record is None or record.result is not VerificationResultValue.PASS
                or record.proposed_commit_identity != commit.repository_revision
                or record.work_unit_id != binding.work_unit_id for record in records):
            raise ProductInvariantViolation("Software delivery requires exact-commit passing Verification")
        # A minimal static page may have only PATH_SCOPE/GIT_DIFF_CHECK evidence.
        # Report that exact coverage; never imply its browser behavior was tested.
        paths = git_bytes(resource.location_ref, "ls-tree", "-r", "--name-only", "-z", commit.repository_revision).decode("utf-8").split("\0")[:-1]
        if len(paths) > 500:
            raise ProductInvariantViolation("Software package exceeds the 500-file limit")
        if target.runtime_recipe.entrypoint not in paths:
            raise ProductInvariantViolation("Software package requires its declared entrypoint")
        changes_raw = git_bytes(resource.location_ref, "diff-tree", "--no-commit-id", "--no-renames", "--name-status", "-z", "-r", contract.source_revision, commit.repository_revision).decode("utf-8").split("\0")[:-1]
        changes = tuple({"status": changes_raw[i], "path": changes_raw[i + 1]} for i in range(0, len(changes_raw), 2))
        if not any(item["path"].endswith((".js", ".mjs", ".cjs", ".html", ".css")) for item in changes):
            raise ProductInvariantViolation("Software delivery requires a software change in this production cycle")
        test_commands = tuple(
            ("node --test " if record.obligation.startswith("NODE_TEST_TARGET:") else "python -m pytest -q ")
            + record.obligation.split(":", 1)[1]
            for record in records
            if record.obligation.startswith(("NODE_TEST_TARGET:", "PYTEST_TARGET:"))
        )
        return SoftwareDeliveryDetails(
            form=target.software_form, runtime_recipe=target.runtime_recipe,
            repository_ref=resource.authoritative_ref, source_revision=contract.source_revision,
            commit_message=git_bytes(resource.location_ref, "show", "-s", "--format=%B", commit.repository_revision).decode("utf-8").strip(),
            changed_files=changes, verification=tuple(record.model_dump(mode="json") for record in records),
            reproduction=("Extract the package and open a terminal in source/.", "Prerequisites: Node.js 18+ for JavaScript tests; Python 3 for the optional local HTTP server.", *test_commands,
                "python -m http.server 8080 --bind 127.0.0.1", "Open http://127.0.0.1:8080/" + target.runtime_recipe.entrypoint,
                "Review delivery-target.json and verification.json for the exact acceptance and evidence basis. No build or dependency download is required by STATIC_WEB."),
        ), sorted(paths)

    def publish(self, work_id: UUID) -> DeliveryManifest:
        with self.database.unit_of_work() as uow:
            self._work(uow.session, work_id)
            target = self._target(uow.session, work_id)
            work, binding, summary, commit, resource = self._trusted_basis(uow.session, work_id)
            if target is None:
                request = self._derived_target(work, summary)
                if request is None:
                    raise ProductInvariantViolation("No single supported current delivery target can be derived")
                target = DeliveryTarget(**request.model_dump(), id=uuid4(), work_id=work_id, created_at=datetime.now(UTC))
                uow.session.execute(insert(work_delivery_targets).values(
                    id=target.id, work_id=work_id, payload=target.model_dump(mode="json"), created_at=target.created_at))
            artifacts = []
            total_size = 0
            software = None
            paths = sorted(set(summary.artifact_paths))
            if target.kind is DeliveryTargetKind.SOFTWARE_ARTIFACT:
                software, paths = self._software_basis(uow.session, target, binding, commit, resource)
            for path in paths:
                data = read_artifact(resource.location_ref, commit.repository_revision, path, software=software is not None)
                total_size += len(data)
                if total_size > MAX_PACKAGE_BYTES:
                    raise ProductInvariantViolation("Delivery package exceeds the 10 MiB inspection limit")
                artifacts.append(DeliveryArtifact(path=path, sha256=sha256(data).hexdigest(), size_bytes=len(data), media_type=artifact_media_type(path) if software else "text/markdown; charset=utf-8"))
            if not artifacts:
                raise ProductInvariantViolation("The trusted cycle has no inspectable artifacts")
            payload = {
                "work_id": str(work_id), "target_id": str(target.id),
                "work_reality_revision_id": str(work.current_work_reality_revision_id) if work.current_work_reality_revision_id else None,
                "runtime_binding_id": str(binding.id), "runtime_commit_id": str(commit.id),
                "repository_identity": commit.repository_identity,
                "repository_revision": commit.repository_revision,
                "verification_record_ids": [str(item) for item in commit.verification_record_ids],
                "artifacts": [item.model_dump(mode="json") for item in artifacts],
            }
            if software is not None:
                payload["software"] = software.model_dump(mode="json")
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
                    "supported_target_kinds": [DeliveryTargetKind.DOCUMENT_PACKAGE.value, DeliveryTargetKind.SOFTWARE_ARTIFACT.value], "deliveries": manifests}

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
        data = read_artifact(resource.location_ref, manifest.repository_revision, path, software=manifest.software is not None)
        if len(data) != descriptor.size_bytes or sha256(data).hexdigest() != descriptor.sha256:
            raise ProductInvariantViolation("Delivery bytes differ from the exact published manifest")
        return data

    def package(self, work_id: UUID, manifest_id: UUID) -> bytes:
        with self.database.unit_of_work() as uow:
            manifest = self._manifest(uow.session, work_id, manifest_id)
            target = self._target(uow.session, work_id)
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as archive:
            def write(path, data):
                info = ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
            write("delivery-manifest.json", manifest.model_dump_json(indent=2))
            write("delivery-target.json", target.model_dump_json(indent=2))
            if manifest.software:
                write("verification.json", json.dumps(manifest.software.verification, ensure_ascii=False, indent=2))
                write("DELIVERY_README.md", "# Software delivery\n\nExact commit: " + manifest.repository_revision + "\n\n" + "\n".join(manifest.software.reproduction) + "\n")
            for artifact in manifest.artifacts:
                write(("source/" if manifest.software else "artifacts/") + artifact.path, self.artifact(work_id, manifest_id, artifact.path))
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
            if manifest.software is not None and request.decision.value == "ACCEPT":
                if self.runtime_probe is None:
                    raise ProductInvariantViolation("Software acceptance requires an accessible exact-manifest runtime")
                self.runtime_probe(work_id, manifest_id)
            record = HumanAcceptance(**request.model_dump(), id=uuid4(), manifest_id=manifest_id, created_at=datetime.now(UTC))
            uow.session.execute(insert(work_delivery_acceptances).values(
                id=record.id, manifest_id=manifest_id, payload=record.model_dump(mode="json"), created_at=record.created_at,
            ))
            uow.commit()
        return record
