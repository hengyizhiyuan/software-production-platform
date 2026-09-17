"""Local static-web adapter for immutable software deliveries, separate from Watt's origin."""
from datetime import UTC, datetime
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import logging
from threading import RLock, Thread
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen
from uuid import UUID

from sqlalchemy import insert, select

from spg.application.delivery import DeliveryApplicationService, artifact_media_type
from spg.domain.product import ProductInvariantViolation
from spg.infrastructure.persistence.delivery_schema import work_delivery_runtimes

logger = logging.getLogger(__name__)


class SoftwareRuntimeService:
    """Serve only published bytes. Never execute a repository-supplied host command.

    One port/origin per manifest keeps browser storage separate between deliveries.
    Persistent recipes are restored after restart; live probes determine readiness.
    This adapter supports one application process, not a deployment platform.
    """
    def __init__(self, delivery: DeliveryApplicationService, *, enabled=False,
                 bind_host="127.0.0.1", first_port=8010, port_count=10):
        self.delivery = delivery
        self.database = delivery.database
        self.enabled = enabled
        self.bind_host = bind_host
        self.ports = range(first_port, first_port + port_count)
        self._servers = {}
        self._lock = RLock()

    def _record(self, manifest_id):
        with self.database.unit_of_work() as uow:
            return uow.session.execute(select(work_delivery_runtimes.c.payload).where(
                work_delivery_runtimes.c.manifest_id == manifest_id)).scalar_one_or_none()

    def _manifest(self, work_id, manifest_id):
        with self.database.unit_of_work() as uow:
            manifest = self.delivery._manifest(uow.session, work_id, manifest_id)
        if manifest.software is None or manifest.software.runtime_recipe.adapter != "STATIC_WEB":
            raise ProductInvariantViolation("This delivery has no supported software runtime recipe")
        return manifest

    def _serve(self, work_id, manifest, port):
        if manifest.id in self._servers:
            return
        # A bounded immutable in-memory export, revalidated against hashes on every start.
        content = {item.path: self.delivery.artifact(work_id, manifest.id, item.path) for item in manifest.artifacts}
        entrypoint = manifest.software.runtime_recipe.entrypoint
        allowed = {".html", ".js", ".mjs", ".css", ".json", ".svg", ".png", ".ico"}
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
                    self.send_error(403)
                    return
                path = unquote(urlsplit(self.path).path).removeprefix("/") or entrypoint
                if path not in content or not any(path.endswith(suffix) for suffix in allowed):
                    self.send_error(404)
                    return
                data = content[path]
                self.send_response(200)
                self.send_header("Content-Type", artifact_media_type(path))
                self.send_header("Content-Length", str(len(data)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'none'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
                self.send_header("X-Watt-Delivery", str(manifest.id))
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *_args):
                pass
        server = ThreadingHTTPServer((self.bind_host, port), Handler)
        server.daemon_threads = True
        thread = Thread(target=server.serve_forever, name=f"delivery-{manifest.id}", daemon=True)
        thread.start()
        self._servers[manifest.id] = (server, thread)

    def start(self, work_id: UUID, manifest_id: UUID):
        if not self.enabled:
            raise ProductInvariantViolation("Software runtime adapter is not enabled on this host")
        with self._lock:
            manifest = self._manifest(work_id, manifest_id)
            view = self.delivery.view(work_id)
            if not any(item['current'] and item['manifest']['id'] == str(manifest_id) for item in view['deliveries']):
                raise ProductInvariantViolation("Start the current exact delivery; this manifest is historical")
            record = self._record(manifest_id)
            if record is None:
                with self.database.unit_of_work() as uow:
                    used = set(uow.session.execute(select(work_delivery_runtimes.c.port)).scalars())
                for port in self.ports:
                    if port in used:
                        continue
                    try:
                        self._serve(work_id, manifest, port)
                        break
                    except OSError:
                        continue
                else:
                    raise ProductInvariantViolation("No free configured software runtime port is available")
                record = {"manifest_id": str(manifest_id), "work_id": str(work_id),
                    "adapter": "STATIC_WEB", "port": port,
                    "url": f"http://127.0.0.1:{port}/" + manifest.software.runtime_recipe.entrypoint,
                    "manifest_fingerprint": manifest.fingerprint, "repository_revision": manifest.repository_revision,
                    "started_at": datetime.now(UTC).isoformat()}
                try:
                    record["startup_evidence"] = self._probe(record, manifest)["evidence"]
                    with self.database.unit_of_work() as uow:
                        uow.session.execute(insert(work_delivery_runtimes).values(manifest_id=manifest_id,
                            port=port, payload=record, created_at=datetime.now(UTC)))
                        uow.commit()
                except Exception:
                    self._stop(manifest_id)
                    raise
            else:
                try:
                    self._serve(work_id, manifest, record['port'])
                except OSError as exc:
                    raise ProductInvariantViolation("The recorded software runtime port is unavailable") from exc
            return self._probe(record, manifest)

    @staticmethod
    def _probe(record, manifest):
        entrypoint = manifest.software.runtime_recipe.entrypoint
        expected = next(item for item in manifest.artifacts if item.path == entrypoint)
        try:
            with urlopen(record['url'], timeout=3) as response:
                body = response.read(expected.size_bytes + 1)
                if response.headers.get('X-Watt-Delivery') != str(manifest.id) or sha256(body).hexdigest() != expected.sha256:
                    raise ValueError("runtime subject differs")
        except Exception as exc:
            raise ProductInvariantViolation("The exact software runtime is not accessible; start it again") from exc
        return {**record, "status": "READY", "checked_at": datetime.now(UTC).isoformat(),
            "evidence": {"http_status": 200, "entrypoint_sha256": expected.sha256, "exact_manifest": True}}

    def probe(self, work_id, manifest_id):
        manifest = self._manifest(work_id, manifest_id)
        record = self._record(manifest_id)
        if record is None:
            raise ProductInvariantViolation("Start and inspect this exact software runtime before acceptance")
        return self._probe(record, manifest)

    def view(self, work_id, manifest_id):
        try:
            return self.probe(work_id, manifest_id)
        except ProductInvariantViolation as exc:
            return {"status": "NOT_READY", "reason": str(exc)}

    def restore(self):
        if not self.enabled:
            return
        with self.database.unit_of_work() as uow:
            rows = list(uow.session.execute(select(work_delivery_runtimes.c.payload)).scalars())
        for record in rows:
            try:
                work_id, manifest_id = UUID(record['work_id']), UUID(record['manifest_id'])
                manifest = self._manifest(work_id, manifest_id)
                if record['port'] not in self.ports:
                    continue
                with self._lock:
                    self._serve(work_id, manifest, record['port'])
                self._probe(record, manifest)
            except Exception:
                logger.exception("Could not restore delivery runtime %s", record['manifest_id'])

    def _stop(self, manifest_id):
        active = self._servers.pop(manifest_id, None)
        if active:
            server, thread = active
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def shutdown(self):
        with self._lock:
            for manifest_id in tuple(self._servers):
                self._stop(manifest_id)
