"""Read-only resource snapshots. Missing measurements never become healthy zeros."""
import asyncio
import threading
import time
from pathlib import Path

from prometheus_client import CollectorRegistry
from prometheus_client.core import GaugeMetricFamily

from .resource_report import SERVICES, METRICS, MEMORY_BUDGETS, CPU_BUDGET, IO_BUDGET, MAX_BYTES, validate_snapshot
from .vulnerabilities import read_document, fresh

CORE_METRICS = ("cpu_cores", "memory_bytes", "read_bps", "write_bps")


class ResourceMonitor:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else None
        self.lock = threading.Lock()
        self.snapshot = self.sampled_at = None
        self.registry = CollectorRegistry()
        self.registry.register(self)

    def sample(self, now=None):
        now = time.time() if now is None else now
        value = None
        if self.root is not None:
            try:
                value = validate_snapshot(read_document(self.root, "snapshot.json", MAX_BYTES))
            except (OSError, ValueError, TypeError, RecursionError):
                pass
        with self.lock:
            self.snapshot, self.sampled_at = value, now

    def overview(self, now=None):
        now = time.time() if now is None else now
        with self.lock:
            snapshot, sampled = self.snapshot, self.sampled_at
        current = snapshot is not None and fresh(sampled, now, 20) and fresh(snapshot["sampled_at"], now, 20)
        host = snapshot.get("host") if snapshot is not None else None
        host_available = bool(current and host is not None and fresh(host["sampled_at"], now, 20))
        rows = []
        for service, name in SERVICES.items():
            source = snapshot["services"][service] if snapshot is not None else None
            available = bool(current and source["source_ok"] and source["running"] and fresh(source["observed_at"], now, 20))
            values = dict(source["values"]) if available else dict.fromkeys(METRICS)
            reason = None if available else "source_unavailable"
            status = "unknown"
            if available:
                cpu, memory = values["cpu_cores"], values["memory_bytes"]
                io = values["read_bps"] + values["write_bps"] if values["read_bps"] is not None and values["write_bps"] is not None else None
                warning = ((cpu is not None and cpu > CPU_BUDGET)
                           or (memory is not None and memory > MEMORY_BUDGETS[service])
                           or (io is not None and io > IO_BUDGET))
                partial = any(values[field] is None for field in CORE_METRICS)
                status = "warning" if warning else "partial" if partial else "ok"
                reason = "warming_or_partial" if partial else None
            elif self.root is None:
                reason = "not_configured"
            elif source is not None and current and source["error"] is not None:
                reason = source["error"]
            rows.append({"id": service, "name": name, "status": status, "available": available, "reason": reason,
                         "observed_at": source["observed_at"] if source else None,
                         "container_id": source["container_id"] if source else None,
                         "started_at": source["started_at"] if source else None, "values": values,
                         "budgets": {"cpu_cores": CPU_BUDGET, "memory_bytes": MEMORY_BUDGETS[service], "io_bps": IO_BUDGET}})
        return {"generated_at": now, "services": rows,
                "host": {"available": host_available,
                         "free_bytes": host["free_bytes"] if host_available else None,
                         "total_bytes": host["total_bytes"] if host_available else None}}

    async def run(self):
        while True:
            await asyncio.to_thread(self.sample)
            await asyncio.sleep(5)

    def collect(self):
        state = self.overview()
        rows = state["services"]
        host = state["host"]
        enabled = GaugeMetricFamily("service_resource_monitor_enabled", "Local resource monitoring configured")
        enabled.add_metric([], float(self.root is not None))
        yield enabled
        host_free = GaugeMetricFamily("service_resource_host_free_bytes", "Free bytes on the volume hosting the project")
        if host["available"]:
            host_free.add_metric([], host["free_bytes"])
        yield host_free
        host_total = GaugeMetricFamily("service_resource_host_total_bytes", "Total bytes on the volume hosting the project")
        if host["available"]:
            host_total.add_metric([], host["total_bytes"])
        yield host_total
        success = GaugeMetricFamily("service_resource_collection_success", "Fresh Engine snapshot available", labels=["service"])
        availability = GaugeMetricFamily("service_resource_metric_available", "Fresh individual metric available", labels=["service", "metric"])
        checked = GaugeMetricFamily("service_resource_observed_at_seconds", "Engine sample time", labels=["service"])
        for row in rows:
            success.add_metric([row["id"]], float(row["available"]))
            if row["available"]: checked.add_metric([row["id"]], row["observed_at"])
            for metric in METRICS:
                availability.add_metric([row["id"], metric], float(row["values"][metric] is not None))
        yield success
        yield availability
        yield checked
        for metric in METRICS:
            gauge = GaugeMetricFamily("service_resource_" + metric, "Current " + metric, labels=["service"])
            for row in rows:
                if row["values"][metric] is not None: gauge.add_metric([row["id"]], row["values"][metric])
            yield gauge
        for metric in ("cpu_cores", "memory_bytes", "io_bps"):
            gauge = GaugeMetricFamily("service_resource_budget_" + metric, "Laboratory observation budget", labels=["service"])
            for row in rows: gauge.add_metric([row["id"]], row["budgets"][metric])
            yield gauge
