"""Export only exact, already qualified image lineage into persistent Watt storage."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
import subprocess
import tarfile
from uuid import uuid4

from spg.domain.cloud_delivery import CloudPreparedArtifact


class CloudArtifactError(RuntimeError):
    pass


class CloudDeliveryArtifactBuilder:
    def __init__(self, delivery, preview, root: Path, static_base_image: str | None):
        self.delivery = delivery
        self.preview = preview
        self.root = root.resolve() / "cloud-delivery-artifacts"
        self.static_base_image = static_base_image

    @staticmethod
    def _docker(*args: str, timeout: int = 900) -> str:
        try:
            completed = subprocess.run(["docker", *args], capture_output=True,
                text=True, timeout=timeout, check=True)
            return completed.stdout.strip()
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            raise CloudArtifactError("EXACT_IMAGE_EXPORT_UNAVAILABLE") from error

    @staticmethod
    def archive_image_identity(archive: Path) -> str:
        """Return the image ID Docker load assigns from the saved config blob."""
        try:
            with tarfile.open(archive, "r") as saved:
                manifest_member = saved.getmember("manifest.json")
                if not manifest_member.isfile() or manifest_member.size > 1_000_000:
                    raise CloudArtifactError("EXPORTED_IMAGE_IDENTITY_UNAVAILABLE")
                manifest_file = saved.extractfile(manifest_member)
                if manifest_file is None:
                    raise CloudArtifactError("EXPORTED_IMAGE_IDENTITY_UNAVAILABLE")
                entries = json.loads(manifest_file.read())
                if not isinstance(entries, list) or len(entries) != 1 or \
                        not isinstance(entries[0], dict):
                    raise CloudArtifactError("EXPORTED_IMAGE_IDENTITY_UNAVAILABLE")
                config_name = entries[0].get("Config")
                if not isinstance(config_name, str) or not re.fullmatch(
                        r"(?:blobs/sha256/)?[0-9a-f]{64}(?:\.json)?", config_name):
                    raise CloudArtifactError("EXPORTED_IMAGE_IDENTITY_UNAVAILABLE")
                config_member = saved.getmember(config_name)
                if not config_member.isfile() or config_member.size > 10_000_000:
                    raise CloudArtifactError("EXPORTED_IMAGE_IDENTITY_UNAVAILABLE")
                config_file = saved.extractfile(config_member)
                if config_file is None:
                    raise CloudArtifactError("EXPORTED_IMAGE_IDENTITY_UNAVAILABLE")
                digest = sha256(config_file.read()).hexdigest()
                if digest not in config_name:
                    raise CloudArtifactError("EXPORTED_IMAGE_IDENTITY_UNAVAILABLE")
                return f"sha256:{digest}"
        except (OSError, ValueError, KeyError, json.JSONDecodeError,
                tarfile.TarError) as error:
            raise CloudArtifactError("EXPORTED_IMAGE_IDENTITY_UNAVAILABLE") from error

    def prepare(self, manifest, candidate_id) -> CloudPreparedArtifact:
        if manifest.software is None:
            raise CloudArtifactError("SOFTWARE_DELIVERY_REQUIRED")
        adapter = manifest.software.runtime_recipe.adapter
        # A fresh context prevents a failed earlier build from carrying public
        # files that are absent from this exact manifest into a later image.
        destination = self.root / manifest.fingerprint / uuid4().hex
        destination.mkdir(parents=True, exist_ok=True)
        archive = destination / "image.tar"
        if adapter == "STATIC_WEB":
            base = self.static_base_image
            if not base or not re.fullmatch(r"[a-zA-Z0-9./_-]+@sha256:[0-9a-f]{64}", base):
                raise CloudArtifactError("PINNED_STATIC_BASE_IMAGE_REQUIRED")
            site = destination / "site"
            site.mkdir(exist_ok=True)
            entrypoint = PurePosixPath(manifest.software.runtime_recipe.entrypoint)
            base_directory = entrypoint.parent
            copied = set()
            for item in manifest.artifacts:
                source = PurePosixPath(item.path)
                if source.suffix.lower() not in {".html", ".css", ".js", ".json",
                        ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp",
                        ".ico", ".woff", ".woff2", ".txt"}:
                    continue
                if any(part.startswith(".") for part in source.parts):
                    continue
                try:
                    relative = source.relative_to(base_directory)
                except ValueError:
                    continue
                path = (site / str(relative)).resolve()
                if not path.is_relative_to(site.resolve()):
                    raise CloudArtifactError("ARTIFACT_PATH_UNSAFE")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(self.delivery.artifact(manifest.work_id, manifest.id, item.path))
                copied.add(source)
            if entrypoint not in copied or not (site / "index.html").is_file():
                raise CloudArtifactError("STATIC_ENTRYPOINT_NOT_SELF_CONTAINED")
            (destination / "Dockerfile").write_text(
                f"FROM {base}\n"
                "ENV PYTHONDONTWRITEBYTECODE=1\n"
                "WORKDIR /site\n"
                "COPY --chown=101:101 site/ /site/\n"
                "USER 101\n"
                "EXPOSE 8080\n"
                'CMD ["python", "-m", "http.server", "8080", "--bind", "0.0.0.0", "--directory", "/site"]\n',
                encoding="utf-8")
            tag = f"watt-static-delivery:{manifest.fingerprint}"
            self._docker("build", "--pull=false", "--network=none", "-t", tag,
                "--label", f"watt.manifest={manifest.id}", str(destination))
            image = self._docker("image", "inspect", "--format", "{{.Id}}", tag)
            internal_port = 8080
        elif adapter == "FULL_APPLICATION_RUNTIME":
            if self.preview is None:
                raise CloudArtifactError("EXACT_CANDIDATE_PREVIEW_REQUIRED")
            session = self.preview.require_served_for_delivery(manifest.work_id,
                candidate_id, manifest.repository_revision, self.delivery.candidate_context(
                    manifest.work_id)["tree"])
            image = session.image_reference
            internal_port = 8000
        else:
            raise CloudArtifactError("UNSUPPORTED_RUNTIME_RECIPE")
        if not image or not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
            raise CloudArtifactError("IMAGE_IDENTITY_UNAVAILABLE")
        self._docker("save", "-o", str(archive), image)
        loaded_image = self.archive_image_identity(archive)
        digest = sha256()
        with archive.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return CloudPreparedArtifact(id=uuid4(), manifest_id=manifest.id,
            manifest_fingerprint=manifest.fingerprint,
            candidate_revision=manifest.repository_revision,
            artifact_sha256=digest.hexdigest(), archive_path=str(archive),
            image_identity=loaded_image, internal_port=internal_port,
            artifact_kind=adapter, created_at=datetime.now(UTC))
