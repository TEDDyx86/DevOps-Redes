import json
import time
from pathlib import Path

import httpx
import pytest
from prometheus_client import generate_latest

from backend.app.config import Settings
from backend.app.resources import ResourceMonitor
from backend.app.resource_report import SERVICES, METRICS
from backend.tests.auth_helpers import AuthenticatedClient, authenticated_app
from fastapi.testclient import TestClient


def report(root, at=1000):
    rows = {key: {"container_id": str(i + 1) * 64, "started_at": "1970-01-01T00:00:01Z", "observed_at": at,
                  "running": True, "source_ok": True, "error": None,
                  "values": {"cpu_cores": 0, "memory_bytes": 10, "memory_total_bytes": 20,
                             "engine_memory_limit_bytes": 1000, "read_bps": 0, "write_bps": 0}}
            for i, key in enumerate(SERVICES)}
    value = {"schema_version": 1, "sampled_at": at, "services": rows}
    root.mkdir(exist_ok=True)
    (root / "snapshot.json").write_text(json.dumps(value), encoding="utf-8")
    return value


def test_fresh_zeros_partial_stats_and_expiry(tmp_path):
    data = report(tmp_path)
    monitor = ResourceMonitor(tmp_path); monitor.sample(now=1000)
    assert all(r["status"] == "ok" and r["values"]["cpu_cores"] == 0 for r in monitor.overview(now=1001)["services"])
    assert all(r["status"] == "unknown" and all(v is None for v in r["values"].values()) for r in monitor.overview(now=1021)["services"])
    data["services"]["dns"]["values"]["cpu_cores"] = None
    (tmp_path / "snapshot.json").write_text(json.dumps(data), encoding="utf-8")
    monitor.sample(now=1000)
    dns = next(r for r in monitor.overview(now=1001)["services"] if r["id"] == "dns")
    assert dns["status"] == "partial" and dns["values"]["memory_bytes"] == 10


def test_source_failure_does_not_publish_zero_or_affect_protocols(tmp_path, monkeypatch):
    report(tmp_path)
    monitor = ResourceMonitor(tmp_path); monitor.sample(now=1000)
    monkeypatch.setattr("backend.app.resources.time.time", lambda: 1001)
    metrics = generate_latest(monitor.registry).decode()
    assert 'service_resource_cpu_cores{service="dns"} 0.0' in metrics
    assert "container_id=" not in metrics and "path=" not in metrics
    (tmp_path / "snapshot.json").unlink(); monitor.sample(now=1001)
    metrics = generate_latest(monitor.registry).decode()
    assert 'service_resource_collection_success{service="dns"} 0.0' in metrics
    assert "service_resource_cpu_cores{" not in metrics


def test_warning_budgets_and_stale_api_sample(tmp_path):
    data = report(tmp_path)
    data["services"]["postgres"]["values"]["memory_bytes"] = 300 * 1024**2
    data["services"]["web-demo"]["values"]["cpu_cores"] = 1
    (tmp_path / "snapshot.json").write_text(json.dumps(data), encoding="utf-8")
    monitor = ResourceMonitor(tmp_path); monitor.sample(now=1000)
    assert {r["id"] for r in monitor.overview(now=1001)["services"] if r["status"] == "warning"} == {"postgres", "web-demo"}
    assert all(r["status"] == "unknown" for r in monitor.overview(now=1021)["services"])


def test_excessive_integer_does_not_stop_monitor_and_valid_source_recovers(tmp_path):
    data = report(tmp_path)
    data["sampled_at"] = 10 ** 1000
    (tmp_path / "snapshot.json").write_text(json.dumps(data), encoding="utf-8")
    monitor = ResourceMonitor(tmp_path); monitor.sample(now=1000)
    assert all(r["status"] == "unknown" for r in monitor.overview(now=1001)["services"])
    report(tmp_path); monitor.sample(now=1001)
    assert all(r["status"] == "ok" for r in monitor.overview(now=1002)["services"])


def test_resource_api_authenticated_and_history_failure_is_explicit(tmp_path):
    root = tmp_path / "resources"; report(root, time.time())
    settings = Settings(database_path=tmp_path / "incidents.sqlite", enable_probe=False, resource_root=root)
    def unavailable(request): raise httpx.ConnectError("offline", request=request)
    with AuthenticatedClient(authenticated_app(settings, transport=httpx.MockTransport(unavailable))) as client:
        client.app.state.resources.sample()
        result = client.get("/api/resources?service=postgres").json()
        assert len(result["services"]) == 4 and result["history_available"] is False
        assert all(row["values"]["memory_bytes"] == 10 for row in result["services"])
        assert client.get("/api/resources?service=other").status_code == 422
        assert client.get("/api/resources?window=bad").status_code == 422
    with TestClient(authenticated_app(settings, transport=httpx.MockTransport(unavailable))) as client:
        assert client.get("/api/resources").status_code == 401


def test_historical_gaps_are_not_bridged_and_queries_mask_availability(tmp_path):
    root = tmp_path / "resources"; report(root, time.time())
    queries, stamps = [], []
    def prometheus(request):
        query = request.url.params["query"]; queries.append(query)
        start = float(request.url.params["start"])
        stamps.extend([start, round(start + 10, 3), round(start + 20, 3)])
        assert "service_resource_metric_available" in query and 'service="postgres"' in query and 'up{job="platform"}' in query
        return httpx.Response(200, json={"status": "success", "data": {"result": [
            {"values": [[stamps[0], "1"], [stamps[1], "NaN"], [stamps[2], "2"]]}]}})
    settings = Settings(database_path=tmp_path / "incidents.sqlite", enable_probe=False, resource_root=root)
    with AuthenticatedClient(authenticated_app(settings, transport=httpx.MockTransport(prometheus))) as client:
        result = client.get("/api/resources?service=postgres").json()
        assert result["history_available"] and len(queries) == 4
        rows = {row["timestamp"]: row for row in result["series"]}
        assert rows[stamps[0]]["cpu_cores"] == 1 and rows[stamps[1]]["cpu_cores"] is None
        assert rows[round(stamps[0] + 5, 3)]["cpu_cores"] is None and rows[stamps[2]]["cpu_cores"] == 2
