import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.metrics import classify, scalar
from backend.app.storage import IncidentStore


def test_missing_and_stale_probes_are_not_healthy():
    assert classify(None, None, None, 100) == "unknown"
    assert classify(1, 0.01, 60, 100) == "unknown"
    assert classify(0, 0.01, 99, 100) == "critical"
    assert classify(1, 0.8, 99, 100) == "warning"
    assert classify(1, 0.1, 99, 100) == "ok"
    assert classify(1, None, 99, 100) == "unknown"


def test_empty_nan_and_infinite_metrics_remain_absent():
    assert scalar({"result": []}) is None
    for value in ["NaN", "+Inf", "-Inf"]:
        assert scalar({"result": [{"value": [100, value]}]}) is None


def alert(status="firing"):
    return {
        "status": status,
        "fingerprint": "http-down",
        "startsAt": "2026-10-28T12:00:00Z",
        "endsAt": "2026-10-28T12:05:00Z" if status == "resolved" else "0001-01-01T00:00:00Z",
        "labels": {"alertname": "HTTPIndisponivel", "service": "web-demo", "severity": "critical"},
        "annotations": {"summary": "HTTP indisponível", "description": "Sonda falhando"},
    }


def test_incidents_are_idempotent_persistent_and_resolve(tmp_path):
    path = tmp_path / "incidents.db"
    store = IncidentStore(path)
    store.ingest([alert(), alert()])
    assert len(store.list()) == 1
    store.ingest([alert("resolved")])
    # A delayed duplicate firing notification cannot reopen a resolved incident.
    store.ingest([alert()])
    row = IncidentStore(path).list()[0]
    assert row["status"] == "resolved"
    assert row["ended_at"] == "2026-10-28T12:05:00Z"


def settings(tmp_path):
    return Settings(database_path=tmp_path / "db.sqlite", webhook_token="test-secret", lab_token="lab-secret", enable_probe=False)


def test_webhook_requires_secret_and_accepts_real_event_shape(tmp_path):
    with TestClient(create_app(settings(tmp_path))) as client:
        assert client.post("/api/webhooks/alerts", json={"alerts": [alert()]}).status_code == 401
        assert client.post("/api/webhooks/alerts", headers={"Authorization": "Bearer test-secret"}, json={"alerts": [alert()]}).status_code == 200
        assert client.get("/api/incidents").json()["incidents"][0]["severity"] == "critical"
        assert client.post("/api/webhooks/alerts", headers={"Authorization": "Bearer test-secret"}, json={"alerts": [{}]}).status_code == 422


def test_unavailable_prometheus_returns_explicit_error(tmp_path):
    def unavailable(request):
        raise httpx.ConnectError("connection refused", request=request)

    with TestClient(create_app(settings(tmp_path), transport=httpx.MockTransport(unavailable))) as client:
        response = client.get("/api/overview")
        assert response.status_code == 503
        assert "Prometheus" in response.json()["detail"]
        assert client.get("/api/overview?window=forever").status_code == 422


def test_lab_mutation_requires_token_and_rejects_foreign_origin(tmp_path):
    with TestClient(create_app(settings(tmp_path))) as client:
        assert client.post("/api/lab/mode", json={"mode": "slow"}).status_code == 401
        assert client.post("/api/lab/mode", headers={"X-Lab-Token": "lab-secret", "Origin": "https://foreign.example"}, json={"mode": "slow"}).status_code == 403


def test_empty_prometheus_is_unknown_not_zero(tmp_path):
    def empty(request):
        kind = "matrix" if request.url.path.endswith("query_range") else "vector"
        return httpx.Response(200, json={"status": "success", "data": {"resultType": kind, "result": []}})

    with TestClient(create_app(settings(tmp_path), transport=httpx.MockTransport(empty))) as client:
        data = client.get("/api/overview").json()
        assert data["service"]["status"] == "unknown"
        assert data["service"]["rps"] is None
        assert data["series"] == []


def test_overview_uses_probe_age_and_real_series(tmp_path):
    now = time.time()

    def metrics(request):
        query = request.url.params["query"]
        if request.url.path.endswith("query_range"):
            data = {"resultType": "matrix", "result": [{"values": [[now - 5, "0.1"], [now, "0.2"]]}]}
        else:
            value = str(now) if "timestamp(" in query or query.startswith("probe_checked_at_seconds") else "1"
            data = {"resultType": "vector", "result": [{"value": [now, value]}]}
        return httpx.Response(200, json={"status": "success", "data": data})

    with TestClient(create_app(settings(tmp_path), transport=httpx.MockTransport(metrics))) as client:
        data = client.get("/api/overview").json()
        assert data["service"]["status"] == "warning"
        assert data["service"]["latency_ms"] == 1000
        assert len(data["series"]) == 2


def test_demo_failure_preserves_metrics_endpoint():
    from demo.main import create_demo

    with TestClient(create_demo("demo-secret")) as client:
        assert client.get("/health").status_code == 200
        assert client.post("/mode", json={"mode": "offline"}).status_code == 401
        assert client.post("/mode", headers={"X-Lab-Token": "demo-secret"}, json={"mode": "offline"}).status_code == 200
        assert client.get("/health").status_code == 503
        assert client.get("/work").status_code == 503
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert 'status="503"' in metrics.text


def test_failed_only_traffic_still_has_metrics(tmp_path):
    now = time.time()

    def failed_only(request):
        query = request.url.params["query"]
        if request.url.path.endswith("query_range"):
            data = {"result": []}
        elif 'status="200"' in query:
            data = {"result": []}
        else:
            value = str(now) if "timestamp(" in query or query.startswith("probe_checked_at_seconds") else "0" if query.startswith("probe_success") else "1"
            data = {"result": [{"value": [now, value]}]}
        return httpx.Response(200, json={"status": "success", "data": data})

    with TestClient(create_app(settings(tmp_path), transport=httpx.MockTransport(failed_only))) as client:
        data = client.get("/api/overview").json()
        assert data["service"]["status"] == "critical"
        assert data["service"]["rps"] == 1
