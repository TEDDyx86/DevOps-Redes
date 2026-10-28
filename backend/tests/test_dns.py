import asyncio
import time

import httpx
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app


def transport(values=None, stale=False):
    values = values or {}
    now = time.time()

    def handler(request):
        if request.url.path.endswith("query_range"):
            result = []
        else:
            query = request.url.params["query"]
            value = values.get(query)
            if "checked_at_seconds" in query or "timestamp(" in query:
                value = now - 45 if stale else now
            result = [] if value is None else [{"value": [now, str(value)]}]
        return httpx.Response(200, json={"status": "success", "data": {"result": result}})

    return httpx.MockTransport(handler)


def client(tmp_path, connection):
    return TestClient(create_app(Settings(database_path=tmp_path / "incidents.sqlite", enable_probe=False), transport=connection))


def values(success=1):
    return {
        'dns_probe_success{job="platform"}': success,
        'dns_probe_duration_seconds{job="platform"}': .015,
        'dns_probe_udp_success{job="platform"}': success,
        'dns_probe_tcp_success{job="platform"}': success,
        'dns_probe_udp_rcode{job="platform"}': 0,
        'dns_probe_tcp_rcode{job="platform"}': 0,
        'up{job="dns"}': 1,
    }


def test_dns_absent_is_unknown_and_other_routes_work(tmp_path):
    with client(tmp_path, transport()) as api:
        response = api.get("/api/dns")
        assert response.status_code == 200
        data = response.json()
        assert data["service"]["status"] == "unknown"
        assert data["stats"]["qps"] is None
        assert data["series"] == []
        assert api.get("/api/dns?window=invalid").status_code == 422
        assert api.get("/api/overview").status_code == 200
        assert api.get("/api/postgres").status_code == 200


def test_dns_probe_and_native_metrics_are_independent(tmp_path):
    with client(tmp_path, transport(values())) as api:
        data = api.get("/api/dns").json()
        assert data["service"]["status"] == "ok"
        assert data["service"]["latency_ms"] == 15
        assert data["stats"]["udp_success"] is True
        assert data["stats"]["tcp_success"] is True
        assert data["stats"]["udp_rcode"] == "NOERROR"
    missing_native = values()
    missing_native['up{job="dns"}'] = 0
    with client(tmp_path, transport(missing_native)) as api:
        data = api.get("/api/dns").json()
        assert data["service"]["status"] == "ok"
        assert data["stats"]["available"] is False
        assert data["stats"]["qps"] is None


def test_dns_failure_and_staleness_hide_old_stats(tmp_path):
    with client(tmp_path, transport(values(0))) as api:
        data = api.get("/api/dns").json()
        assert data["service"]["status"] == "critical"
        assert data["service"]["latency_ms"] is None
        assert data["stats"]["qps"] is None
    with client(tmp_path, transport(values(), stale=True)) as api:
        data = api.get("/api/dns").json()
        assert data["service"]["status"] == "unknown"
        assert data["stats"]["udp_success"] is None


def test_dns_latency_threshold_is_100_ms(tmp_path):
    slow = values()
    slow['dns_probe_duration_seconds{job="platform"}'] = .15
    with client(tmp_path, transport(slow)) as api:
        assert api.get("/api/dns").json()["service"]["status"] == "warning"


def test_dns_prometheus_failure_is_explicit(tmp_path):
    def unavailable(request):
        raise httpx.ConnectError("unavailable", request=request)

    with client(tmp_path, httpx.MockTransport(unavailable)) as api:
        assert api.get("/api/dns").status_code == 503


def test_dns_answer_validation_checks_rcode_address_and_empty_answer():
    import dns.message
    import dns.rrset
    from backend.app.dns_probe import valid_answer

    query = dns.message.make_query("app.aularedes.test.", "A")
    answer = dns.message.make_response(query)
    answer.answer.append(dns.rrset.from_text("app.aularedes.test.", 60, "IN", "A", "192.0.2.10"))
    assert valid_answer(answer, "app.aularedes.test.", "192.0.2.10")
    assert not valid_answer(answer, "app.aularedes.test.", "192.0.2.99")
    assert not valid_answer(answer, "wrong.aularedes.test.", "192.0.2.10")
    answer.set_rcode(3)
    assert not valid_answer(answer, "app.aularedes.test.", "192.0.2.10")
    assert not valid_answer(dns.message.make_response(query), "app.aularedes.test.", "192.0.2.10")


def test_dns_one_failed_protocol_is_not_healthy(monkeypatch):
    from backend.app.dns_probe import DNSProbe

    probe = DNSProbe()

    async def address(server, port):
        return "127.0.0.1"

    async def query(address, port, name, expected, tcp=False):
        return {"success": 0} if tcp else {"success": 1, "duration": .01, "rcode": 0}

    monkeypatch.setattr(probe, "server_address", address)
    monkeypatch.setattr(probe, "query", query)
    asyncio.run(probe.sample("unused", 1053, "app.aularedes.test.", "192.0.2.10"))
    assert probe.snapshot["success"] == 0
    assert probe.snapshot["udp_success"] == 1
    assert probe.snapshot["tcp_success"] == 0


def test_dns_history_preserves_missing_intervals():
    from backend.app.dns_metrics import merge_series

    ranges = [
        {"result": [{"values": [[100, "2"], [105, "2"], [120, "1"]]}]},
        {"result": [{"values": [[100, ".01"], [105, ".02"], [120, ".015"]]}]},
    ]
    rows = merge_series(ranges, 100, 125, 5)
    assert [row["timestamp"] for row in rows] == [100, 105, 110, 115, 120, 125]
    assert rows[2]["qps"] is None and rows[2]["latency_ms"] is None
    assert rows[3]["qps"] is None and rows[3]["latency_ms"] is None
    assert rows[4]["latency_ms"] == 15
    assert merge_series([{"result": []}, {"result": []}], 100, 125, 5) == []
