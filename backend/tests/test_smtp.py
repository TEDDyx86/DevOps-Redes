import asyncio
import time

import pytest
from prometheus_client import generate_latest


def test_real_smtp_accept_reject_limit_and_forward(tmp_path):
    import socket
    import smtplib
    from aiosmtpd.controller import Controller
    from demo.smtp_queue import SMTPQueue
    from demo.smtp_server import QueueHandler, forward

    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    queue = SMTPQueue(tmp_path / "smtp.sqlite")
    controller = Controller(QueueHandler(queue), hostname="127.0.0.1", port=port, data_size_limit=65536)
    controller.start()
    try:
        with smtplib.SMTP("127.0.0.1", port, timeout=2) as smtp:
            assert smtp.ehlo()[0] == 250
            assert smtp.noop()[0] == 250
            with pytest.raises(smtplib.SMTPRecipientsRefused) as refused:
                smtp.sendmail("lab@aularedes.test", ["outside@example.org"], "Subject: no\r\n\r\nx")
            assert refused.value.recipients["outside@example.org"][0] == 550
            smtp.sendmail("lab@aularedes.test", ["aluno@aularedes.test"], "Subject: yes\r\n\r\nhello")
            with pytest.raises(smtplib.SMTPSenderRefused) as too_large:
                smtp.sendmail("lab@aularedes.test", ["aluno@aularedes.test"], "x" * 65537)
            assert too_large.value.smtp_code == 552
        assert queue.stats()["accepted"] == 1
        item = queue.claim()
        # Same test-only receiver accepts forwarding through the real protocol.
        assert forward(item, "127.0.0.1", port) == "sent"
        assert queue.stats()["accepted"] == 2
        assert queue.stats()["rejected"] == 1
    finally:
        controller.stop()


def test_probe_requires_both_smtp_commands(monkeypatch):
    from backend.app.smtp_probe import check

    class Connection:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def ehlo(self): return (250, b"hello")
        def noop(self): return (500, b"error")

    monkeypatch.setattr("backend.app.smtp_probe.smtplib.SMTP", Connection)
    assert check("unused", 2525) == {"success": 0}


def test_worker_recovers_storage_failure_without_forwarding_twice(tmp_path, monkeypatch):
    import sqlite3
    from demo.smtp_queue import SMTPQueue
    from demo.smtp_server import deliver

    queue = SMTPQueue(tmp_path / "queue.sqlite")
    queue.accept("lab@aularedes.test", "aluno@aularedes.test", b"hello")
    claim, finish = queue.claim, queue.finish
    calls = {"claim": 0, "finish": 0, "forward": 0}

    def flaky_claim():
        calls["claim"] += 1
        if calls["claim"] == 1:
            raise sqlite3.OperationalError("database locked")
        return claim()

    def flaky_finish(*args):
        calls["finish"] += 1
        if calls["finish"] == 1:
            raise sqlite3.OperationalError("database locked")
        return finish(*args)

    def forwarding(*args):
        calls["forward"] += 1
        return "sent"

    async def pause(seconds):
        if queue.stats()["delivered"] == 1:
            raise asyncio.CancelledError()

    monkeypatch.setattr(queue, "claim", flaky_claim)
    monkeypatch.setattr(queue, "finish", flaky_finish)
    monkeypatch.setattr("demo.smtp_server.forward", forwarding)
    monkeypatch.setattr("demo.smtp_server.asyncio.sleep", pause)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(deliver(queue, "unused", 1025))
    assert calls["forward"] == 1
    assert queue.stats()["queue"] == 0


def test_queue_persists_and_only_claims_once(tmp_path):
    from demo.smtp_queue import SMTPQueue

    path = tmp_path / "queue.sqlite"
    queue = SMTPQueue(path)
    key = queue.accept("lab@aularedes.test", "aluno@aularedes.test", b"Subject: test\r\n\r\nhello", now=100)
    item = queue.claim(now=101)
    assert item["id"] == key
    assert queue.claim(now=101) is None
    restarted = SMTPQueue(path)
    assert restarted.claim(now=102)["id"] == key
    restarted.finish(key, "sent", now=103)
    assert restarted.claim(now=104) is None
    stats = restarted.stats(now=110)
    assert stats["accepted"] == stats["delivered"] == 1
    assert stats["queue"] == 0
    assert stats["last_minute"] == 1
    assert stats["latencies"] == [3]


def test_retry_keeps_message_and_permanent_failure_is_distinct(tmp_path):
    from demo.smtp_queue import SMTPQueue

    queue = SMTPQueue(tmp_path / "queue.sqlite")
    key = queue.accept("lab@aularedes.test", "aluno@aularedes.test", b"x", now=100)
    queue.claim(now=100)
    queue.finish(key, "retry", now=101)
    assert queue.claim(now=105) is None
    assert queue.claim(now=106)["content"] == b"x"
    queue.finish(key, "failed", now=107)
    stats = queue.stats(now=200)
    assert stats["accepted"] == 1 and stats["delivered"] == 0
    assert stats["failed"] == 1 and stats["attempts_failed"] == 2
    assert stats["queue"] == 0 and stats["last_minute"] == 0
    assert stats["last_hour"] == 1


def test_queue_capacity_and_metrics(tmp_path):
    from demo.smtp_queue import SMTPQueue

    queue = SMTPQueue(tmp_path / "queue.sqlite", capacity=1)
    queue.accept("lab@aularedes.test", "aluno@aularedes.test", b"x")
    with pytest.raises(OverflowError):
        queue.accept("lab@aularedes.test", "aluno@aularedes.test", b"y")
    queue.reject()
    metrics = generate_latest(queue.registry).decode()
    assert "smtp_queue_messages 1.0" in metrics
    assert "smtp_rejected_recipients_total 1.0" in metrics
    assert 'smtp_delivery_attempts_total{outcome="sent"} 0.0' in metrics


def test_smtp_route_missing_failed_and_exporter_independent(tmp_path):
    import httpx
    from fastapi.testclient import TestClient
    from backend.app.config import Settings
    from backend.app.main import create_app

    values = {}
    skew = .1
    def respond(request):
        query = request.url.params.get("query", "")
        value = values.get(query)
        if "checked_at_seconds" in query or "timestamp(" in query:
            value = time.time() + skew
        result = [] if value is None else [{"value": [time.time(), str(value)]}]
        if request.url.path.endswith("query_range"):
            result = []
        return httpx.Response(200, json={"status": "success", "data": {"result": result}})

    settings = Settings(database_path=tmp_path / "incidents.sqlite", enable_probe=False)
    with TestClient(create_app(settings, httpx.MockTransport(respond))) as api:
        response = api.get("/api/smtp")
        assert response.status_code == 200
        assert response.json()["service"]["status"] == "unknown"
        values.update({'smtp_probe_success{job="platform"}': 1, 'smtp_probe_duration_seconds{job="platform"}': .01, 'up{job="smtp"}': 0})
        data = api.get("/api/smtp").json()
        assert data["service"]["status"] == "ok"
        assert data["stats"]["available"] is False
        assert data["stats"]["queue"] is None
        values['up{job="smtp"}'] = 1
        values['smtp_queue_messages{job="smtp"}'] = 3
        data = api.get("/api/smtp").json()
        assert data["stats"]["available"] is True
        assert data["stats"]["queue"] == 3
        skew = -45
        data = api.get("/api/smtp").json()
        assert data["service"]["status"] == "unknown"
        assert data["stats"]["queue"] is None
        skew = 0
        values['smtp_probe_success{job="platform"}'] = 0
        data = api.get("/api/smtp").json()
        assert data["service"]["status"] == "critical"
        assert data["service"]["latency_ms"] is None
        assert api.get("/api/smtp?window=bad").status_code == 422
