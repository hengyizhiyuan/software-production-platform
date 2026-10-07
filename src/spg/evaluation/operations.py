"""Read-only owner projections plus bounded, timestamped host observations."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import shutil
import subprocess
from threading import Event, Thread

from sqlalchemy import select, text, insert, delete, or_
from spg.infrastructure.performance import timed
from uuid import uuid4

from spg.infrastructure.persistence.quality_schema import operations_metric_samples as samples


@timed("subprocess")
def command(args, timeout=8):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return r.stdout[:100_000] if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


@timed("filesystem")
def read(path):
    try:
        return Path(path).read_text()[:1_000_000]
    except OSError:
        return None


def host_observation(settings, previous=None, *, observed_at=None):
    at = observed_at or datetime.now(UTC)
    proc, data = settings.admin_host_proc, settings.admin_host_data
    available = (proc / "stat").is_file()
    result = {"observed_at": at.isoformat(), "scope": "HOST" if available else "UNAVAILABLE",
        "node_id": settings.admin_node_id or "UNBOUND_NODE", "region": settings.admin_region,
        "hostname": settings.admin_host_name, "cpu_percent": None, "cpu_count": None,
        "memory": None, "disk": None, "network": {}, "uptime_seconds": None,
        "unavailable": [], "provenance": "read-only host proc/data mounts"}
    raw = read(proc / "stat")
    if raw:
        fields = raw.splitlines()[0].split()[1:]
        ticks = [int(x) for x in fields]
        # guest and guest_nice are included in user/nice, never count twice.
        total = sum(ticks[:8])
        idle = ticks[3] + (ticks[4] if len(ticks) > 4 else 0)
        result["cpu_ticks"] = {"total": total, "idle": idle}
        result["cpu_count"] = sum(1 for line in raw.splitlines() if line.startswith("cpu") and line[3:4].isdigit())
        old = (previous or {}).get("cpu_ticks")
        if old and total > old["total"] and idle >= old["idle"]:
            result["cpu_percent"] = round(100 * (1 - (idle - old["idle"]) / (total - old["total"])), 2)
        else:
            result["unavailable"].append("CPU_REQUIRES_TWO_SAMPLES")
    else:
        result["unavailable"].append("HOST_PROC_UNAVAILABLE")
    raw = read(proc / "meminfo")
    if raw:
        values = {line.split()[0].rstrip(":"): int(line.split()[1]) * 1024
                  for line in raw.splitlines() if len(line.split()) >= 2}
        if "MemTotal" in values and "MemAvailable" in values:
            result["memory"] = {"total_bytes": values["MemTotal"], "available_bytes": values["MemAvailable"],
                "used_bytes": values["MemTotal"] - values["MemAvailable"], "method": "MemTotal-MemAvailable"}
    if data.exists():
        usage = shutil.disk_usage(data)
        result["disk"] = {"total_bytes": usage.total, "used_bytes": usage.used,
            "free_bytes": usage.free, "mount": "/data", "method": "statvfs"}
    else:
        result["unavailable"].append("DATA_MOUNT_UNAVAILABLE")
    raw = read(proc / "uptime")
    if raw:
        result["uptime_seconds"] = float(raw.split()[0])
    raw = read(settings.admin_host_network / "dev")
    if raw:
        for line in raw.splitlines()[2:]:
            if ":" not in line:
                continue
            name, counters = line.split(":", 1)
            fields = counters.split()
            if len(fields) >= 9:
                result["network"][name.strip()] = {"rx_bytes": int(fields[0]), "tx_bytes": int(fields[8])}
        # Keep interfaces separate; summing veth/bridge/physical traffic counts twice.
        if previous and previous.get("observed_at"):
            dt = (at - datetime.fromisoformat(previous["observed_at"])).total_seconds()
            if dt > 0:
                for name, values in result["network"].items():
                    old = previous.get("network", {}).get(name)
                    if old and values["rx_bytes"] >= old["rx_bytes"] and values["tx_bytes"] >= old["tx_bytes"]:
                        values["rx_bytes_per_second"] = round((values["rx_bytes"] - old["rx_bytes"]) / dt, 2)
                        values["tx_bytes_per_second"] = round((values["tx_bytes"] - old["tx_bytes"]) / dt, 2)
    return result


class OperationsService:
    def __init__(self, database, settings, runtime=None):
        self.database, self.settings, self.runtime = database, settings, runtime
        self.stop = Event()
        self.thread = None
        self.resource_threads = []

    def production(self):
        workers = [] if self.runtime is None else [w.model_dump(mode="json") for w in self.runtime.list_workers()]
        with self.database.unit_of_work() as u:
            queue = [dict(r) for r in u.session.execute(text("""
                SELECT q.attempt_id, q.work_id, q.pwu_id, q.condition, q.wait_reason, q.enqueued_at,
                       w.refined_title AS work_title, p.objective,
                       EXTRACT(EPOCH FROM now()-q.enqueued_at)::integer AS elapsed_seconds
                FROM executor_queue q LEFT JOIN product_works w ON w.id=q.work_id
                LEFT JOIN production_work_units p ON p.id=q.pwu_id
                WHERE q.condition NOT IN ('COMPLETED','FAILED','CANCELLED')
                ORDER BY q.enqueued_at LIMIT 100
            """)).mappings()]
            total = u.session.execute(text("SELECT count(*) FROM executor_queue WHERE condition NOT IN ('COMPLETED','FAILED','CANCELLED')")).scalar_one()
        return {"workers": workers, "queue": queue, "queue_depth": total,
            "active_executions": sum(w["active_execution_count"] for w in workers),
            "available_slots": sum(w["available_slots"] for w in workers),
            "truth_source": "Worker Registry / native queue / fenced allocations", "queue_display_limit": 100}

    def services(self):
        output = command(["docker", "ps", "-a", "--filter", "label=com.docker.compose.project=watt-cloud-worker",
            '--format', '{{.ID}} {{.Label "com.docker.compose.service"}}'])
        if output is None:
            return {"state": "UNAVAILABLE", "services": [], "reason": "DOCKER_OBSERVATION_UNAVAILABLE"}
        rows = []
        selected = [line.split(maxsplit=1) for line in output.splitlines() if len(line.split(maxsplit=1)) == 2]
        raw = command(["docker", "inspect", "--format", "{{.Id}} {{json .State}}", *[cid for cid, service in selected]]) if selected else None
        inspected = {}
        for line in (raw or '').splitlines():
            identity, state = line.split(maxsplit=1)
            inspected[identity] = json.loads(state)
        for line in output.splitlines():
            cid, service = line.split(maxsplit=1)
            if service == "migrate":
                continue
            s = next((state for identity, state in inspected.items() if identity.startswith(cid)), {})
            health = s.get("Health", {}).get("Status")
            rows.append({"service": service, "container_id": cid, "state": s.get("Status", "UNKNOWN"),
                "health": health or "NOT_CONFIGURED", "started_at": s.get("StartedAt"),
                "node_id": self.settings.admin_node_id or "UNBOUND_NODE", "source": "Docker State/Health"})
        present = {r["service"] for r in rows}
        for required in ("api", "native-worker", "native-coordinator", "native-tool-host", "postgres", "gitea"):
            if required not in present:
                rows.append({"service": required, "container_id": None, "state": "MISSING",
                    "health": "UNAVAILABLE", "started_at": None,
                    "node_id": self.settings.admin_node_id or "UNBOUND_NODE", "source": "Docker project absence"})
        return {"state": "OBSERVED", "services": rows}

    def storage(self):
        with self.database.unit_of_work() as u:
            database_bytes = u.session.execute(text("SELECT pg_database_size(current_database())")).scalar_one()
        out = {"postgresql": {"bytes": database_bytes, "method": "pg_database_size", "scope": "current database"}}
        for label, relative in (("watt_data", "watt/app"), ("execution_data", "watt/native-executor"), ("logs", "logs")):
            value = command(["du", "-sk", "--one-file-system", str(self.settings.admin_host_data / relative)])
            out[label] = {"bytes": int(value.split()[0]) * 1024 if value else None,
                "method": "du allocated blocks", "state": "OBSERVED" if value else "UNAVAILABLE_OR_PERMISSION_DENIED"}
        value = command(["du", "-sk", "--one-file-system", str(self.settings.native_executor_workspace_root)])
        out["workspaces"] = {"bytes": int(value.split()[0]) * 1024 if value else None,
            "method": "du current native workspace volume", "state": "OBSERVED" if value else "UNAVAILABLE"}
        output = command(["docker", "system", "df", "--format", "{{json .}}"])
        out["docker"] = {"categories": [json.loads(x) for x in output.splitlines()] if output else [],
            "state": "OBSERVED" if output else "UNAVAILABLE", "scope": "daemon, shared layers; do not sum with /data"}
        # Gitea volume footprint can be measured through a fixed read-only command.
        services = self.services()["services"]
        gitea = next((x for x in services if x["service"] == "gitea" and x["state"] == "running"), None)
        value = command(["docker", "exec", gitea["container_id"], "du", "-sk", "/var/lib/gitea"]) if gitea else None
        out["gitea"] = {"bytes": int(value.split()[0]) * 1024 if value else None,
            "method": "fixed read-only Gitea du", "state": "OBSERVED" if value else "UNAVAILABLE"}
        out["note"] = "Measurements have different scopes and may overlap; they are not a sum of total disk usage."
        return out

    def assurance(self):
        root = self.settings.owner_runtime_store_root / "guardian"
        results = []
        if root.exists():
            paths = sorted(root.rglob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:100]
            for p in paths:
                try:
                    if p.stat().st_size > 1_000_000:
                        continue
                    r = json.loads(p.read_text())
                    if isinstance(r, dict) and "gate" in r and "request_id" in r:
                        results.append({k: r.get(k) for k in ("request_id", "result_id", "candidate_id",
                            "candidate_fingerprint", "source_revision", "source_tree", "gate", "assessed_at")})
                except (OSError, ValueError):
                    continue
        return {"owner": "Guardian", "mode": self.settings.owner_runtime_mode,
            "store_observed": root.exists(), "results": results[:20], "truth_source": "canonical Guardian result files"}

    def latest(self):
        with self.database.unit_of_work() as u:
            r = u.session.execute(select(samples).where(samples.c.node_id == (self.settings.admin_node_id or "UNBOUND_NODE"),
                    samples.c.record["observation_kind"].astext.is_(None))
                .order_by(samples.c.created_at.desc()).limit(1)).mappings().first()
            if r is None:
                return {"state": "NOT_SAMPLED", "node": None}
            stale = datetime.now(UTC) - r["created_at"] > timedelta(seconds=3 * self.settings.admin_metrics_interval_seconds)
            return {"state": "STALE" if stale else "CURRENT", "node": r["record"]}

    def _resource_latest(self, kind, interval):
        with self.database.unit_of_work() as u:
            row = u.session.execute(select(samples).where(
                samples.c.node_id == (self.settings.admin_node_id or "UNBOUND_NODE"),
                samples.c.record["observation_kind"].astext == kind
            ).order_by(samples.c.created_at.desc()).limit(1)).mappings().first()
        if row is None:
            return {"state": "NOT_SAMPLED", "observed_at": None, "value": None}
        age = (datetime.now(UTC) - row["created_at"]).total_seconds()
        return {"state": "STALE" if age > 3*interval else "CURRENT",
            "observed_at": row["record"]["observed_at"], "age_seconds": round(age, 1),
            "sampling_interval_seconds": interval, "value": row["record"]["value"]}

    def observe_resource(self, kind):
        """Only the background sampler runs infrastructure commands."""
        value = self.services() if kind == "SERVICES" else self.storage()
        record = {"observation_kind": kind, "value": value,
            "observed_at": datetime.now(UTC).isoformat()}
        with self.database.unit_of_work() as u:
            u.session.execute(insert(samples).values(id=uuid4(),
                node_id=self.settings.admin_node_id or "UNBOUND_NODE", record=record))
            u.commit()
        return record

    def observe(self):
        previous = self.latest().get("node")
        observation = host_observation(self.settings, previous)
        production = self.production()
        observation.update(queue_depth=production["queue_depth"], active_executions=production["active_executions"])
        with self.database.unit_of_work() as u:
            u.session.execute(insert(samples).values(id=uuid4(), node_id=observation["node_id"], record=observation))
            u.session.execute(delete(samples).where(samples.c.created_at < datetime.now(UTC) - timedelta(
                hours=self.settings.admin_metrics_retention_hours)))
            u.commit()
        return observation

    def history(self):
        with self.database.unit_of_work() as u:
            rows = u.session.execute(select(samples).where(samples.c.record["observation_kind"].astext.is_(None)).order_by(samples.c.created_at.desc()).limit(720)).mappings().all()
            return [{"observed_at": r["record"]["observed_at"], "node_id": r["node_id"],
                "cpu_percent": r["record"].get("cpu_percent"), "memory": r["record"].get("memory"),
                "disk": r["record"].get("disk"), "queue_depth": r["record"].get("queue_depth"),
                "active_executions": r["record"].get("active_executions")} for r in reversed(rows)]

    def snapshot(self):
        latest = self.latest()
        production = self.production()
        service_sample = self._resource_latest("SERVICES", self.settings.admin_services_interval_seconds)
        storage_sample = self._resource_latest("STORAGE", self.settings.admin_storage_interval_seconds)
        services = service_sample["value"] or {"state": "NOT_SAMPLED", "services": []}
        node = latest.get("node")
        storage = storage_sample["value"] or {"postgresql": {"bytes": None, "method": "not sampled"},
            "docker": {"categories": [], "state": "NOT_SAMPLED"}, "note": "Storage has not yet been sampled."}
        return {**latest, "production": production, "services": services["services"],
            "resource_freshness": {"services": {k:v for k,v in service_sample.items() if k != "value"},
                "storage": {k:v for k,v in storage_sample.items() if k != "value"}},
            "service_observation_state": services["state"], "storage": storage,
            "topology": {"nodes": [] if node is None else [{"id": node["node_id"], "hostname": node["hostname"],
                "region": node["region"], "observed_at": node["observed_at"]}],
                "service_placements": services["services"], "workers": production["workers"],
                "storage_placements": [{"node_id": self.settings.admin_node_id or "UNBOUND_NODE",
                    "storage_id": key, "measurement": value} for key, value in storage.items() if key != "note"],
                "relationships": [{"from": "api", "to": "postgres", "kind": "TRANSACTION_STORE"},
                    {"from": "native-worker", "to": "postgres", "kind": "QUEUE_LEASE"},
                    {"from": "native-worker", "to": "native-tool-host", "kind": "TOOL_EXECUTION"},
                    {"from": "api", "to": "gitea", "kind": "MANAGED_SOURCE"}],
                "relationship_scope": "configured Single ECS topology; cross-host routing is not qualified"}}

    def start(self):
        def sample_loop():
            while not self.stop.is_set():
                try:
                    self.observe()
                except Exception:
                    # No invented zero metrics or crashing production on observer failure.
                    import logging
                    logging.getLogger(__name__).warning("Admin 资源观测暂不可用；保留上次采样并标记时效")
                self.stop.wait(self.settings.admin_metrics_interval_seconds)
        self.thread = Thread(target=sample_loop, name="watt-operations-observer", daemon=True)
        self.thread.start()
        def resource_loop(kind, interval):
            while not self.stop.is_set():
                try:
                    self.observe_resource(kind)
                except Exception:
                    import logging
                    logging.getLogger(__name__).warning("Admin %s 后台观测失败；保留上次观测与真实时效", kind)
                self.stop.wait(interval)
        for kind, interval in (("SERVICES", self.settings.admin_services_interval_seconds),
                ("STORAGE", self.settings.admin_storage_interval_seconds)):
            thread = Thread(target=resource_loop, args=(kind, interval),
                name="watt-observer-"+kind.lower(), daemon=True)
            self.resource_threads.append(thread)
            thread.start()

    def shutdown(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=10)
        for thread in self.resource_threads:
            thread.join(timeout=10)
