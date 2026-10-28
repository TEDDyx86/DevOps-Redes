import asyncio
import time

import httpx
import pytest
from backend.tests.auth_helpers import AuthenticatedClient as TestClient

from backend.app.config import Settings
from backend.tests.auth_helpers import authenticated_app as create_app


def response(values=None, stale=False):
    values = values or {}
    now = time.time()

    def handler(request):
        if request.url.path.endswith("query_range"):
            return httpx.Response(200, json={"status": "success", "data": {"result": []}})
        query = request.url.params["query"]
        if query in values:
            value = values[query]
        elif "checked_at_seconds" in query:
            value = now - 45 if stale else now
        else:
            value = None
        result = [] if value is None else [{"value": [now, str(value)]}]
        return httpx.Response(200, json={"status": "success", "data": {"result": result}})

    return httpx.MockTransport(handler)


def client(tmp_path, transport):
    return TestClient(create_app(Settings(database_path=tmp_path / "events.sqlite", enable_probe=False), transport=transport))


def test_postgres_absent_is_unknown_and_does_not_break_http(tmp_path):
    with client(tmp_path, response()) as api:
        result = api.get("/api/postgres")
        assert result.status_code == 200
        data = result.json()
        assert data["service"]["status"] == "unknown"
        assert data["stats"]["connections"] is None
        assert data["series"] == []
        assert api.get("/api/overview").status_code == 200
        assert api.get("/api/postgres?window=invalid").status_code == 422


def postgres_values(success=1):
    return {
        'postgres_probe_success{job="platform"}': success,
        'postgres_probe_duration_seconds{job="platform"}': .025,
        'postgres_stats_success{job="platform"}': 1,
        'postgres_connections{job="platform"}': 3,
        'postgres_connections_limit{job="platform"}': 100,
        'postgres_database_bytes{job="platform"}': 9000000,
        'rate(postgres_commits_total{job="platform"}[1m])': 2,
        'rate(postgres_rollbacks_total{job="platform"}[1m])': .2,
        'rate(postgres_workload_statements_total{job="platform"}[1m])': 4,
    }


def test_postgres_returns_sql_metrics_distinct_from_transactions(tmp_path):
    with client(tmp_path, response(postgres_values())) as api:
        data = api.get("/api/postgres").json()
        assert data["service"]["status"] == "ok"
        assert data["service"]["latency_ms"] == 25
        assert data["stats"]["connections"] == 3
        assert data["stats"]["qps"] == 4
        assert data["stats"]["commits_per_second"] == 2
        assert data["stats"]["rollbacks_per_second"] == .2
        assert data["stats"]["database_bytes"] == 9000000


def test_down_postgres_hides_old_statistics(tmp_path):
    with client(tmp_path, response(postgres_values(success=0))) as api:
        data = api.get("/api/postgres").json()
        assert data["service"]["status"] == "critical"
        assert data["stats"]["connections"] is None
        assert data["stats"]["qps"] is None


def test_stale_postgres_and_failed_stats_do_not_look_current(tmp_path):
    with client(tmp_path, response(postgres_values(), stale=True)) as api:
        data = api.get("/api/postgres").json()
        assert data["service"]["status"] == "unknown"
        assert data["stats"]["connections"] is None
    values = postgres_values()
    values['postgres_stats_success{job="platform"}'] = 0
    with client(tmp_path, response(values)) as api:
        data = api.get("/api/postgres").json()
        assert data["service"]["status"] == "ok"
        assert data["stats"]["available"] is False
        assert data["stats"]["database_bytes"] is None


def test_connection_pressure_is_warning(tmp_path):
    values = postgres_values()
    values['postgres_connections{job="platform"}'] = 85
    with client(tmp_path, response(values)) as api:
        assert api.get("/api/postgres").json()["service"]["status"] == "warning"


def test_postgres_metrics_unavailable_returns_503(tmp_path):
    def unavailable(request):
        raise httpx.ConnectError("unavailable", request=request)

    with client(tmp_path, httpx.MockTransport(unavailable)) as api:
        assert api.get("/api/postgres").status_code == 503


def test_absent_statistics_are_omitted_instead_of_nan_counters():
    from prometheus_client import generate_latest
    from backend.app.postgres_probe import PostgresProbe

    probe = PostgresProbe()
    assert generate_latest(probe.registry) == b""
    probe.snapshot = {"probe_success": 0, "stats_success": 0, "probe_checked_at_seconds": 100}
    text = generate_latest(probe.registry).decode()
    assert "postgres_probe_success 0.0" in text
    assert "postgres_commits_total" not in text
    assert "NaN" not in text
    probe.snapshot = {"probe_success": 1, "commits": 10}
    text = generate_latest(probe.registry).decode()
    assert "# TYPE postgres_commits_total counter" in text
    assert "postgres_commits_total 10.0" in text


def test_statistics_timeout_preserves_successful_sql_probe(monkeypatch):
    import psycopg
    from backend.app.postgres_probe import PostgresProbe

    class Connection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def close(self):
            pass

        async def execute(self, query):
            if query == "SELECT 1":
                return None
            await asyncio.Future()  # Statistics do not respond; SELECT 1 already did.

    async def connect(*args, **kwargs):
        return Connection()

    monkeypatch.setattr(psycopg.AsyncConnection, "connect", staticmethod(connect))
    probe = PostgresProbe()

    async def exercise():
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(probe.run("unused", interval=60), timeout=5.2)

    asyncio.run(exercise())
    assert probe.snapshot["probe_success"] == 1
    assert probe.snapshot["stats_success"] == 0
