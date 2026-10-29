import asyncio
from prometheus_client import generate_latest


def test_learning_requires_continuous_valid_samples_and_persists(tmp_path):
    from backend.app.traffic import TrafficMonitor
    monitor = TrafficMonitor(tmp_path / "traffic.sqlite")
    for index in range(24):
        monitor.ingest({"web-demo": .2}, now=100+index*5)
    assert monitor.overview(now=216)["services"][0]["status"] == "learning"
    monitor.ingest({"web-demo": .2}, now=220)
    row = monitor.overview(now=220)["services"][0]
    assert row["status"] == "normal" and abs(row["baseline"]-.2) < .0001
    assert row["threshold"] == 2
    restarted = TrafficMonitor(tmp_path / "traffic.sqlite")
    restarted.ingest({"web-demo": 5}, now=225)
    row = restarted.overview(now=225)["services"][0]
    assert row["status"] == "anomalous" and row["baseline"] == monitor.overview(now=225)["services"][0]["baseline"]
    assert restarted.overview(now=250)["services"][0]["status"] == "unknown"


def test_missing_gap_and_zero_are_distinct(tmp_path):
    from backend.app.traffic import TrafficMonitor
    monitor = TrafficMonitor(tmp_path / "traffic.sqlite")
    for index in range(20):
        monitor.ingest({"smtp": 0}, now=100+index*5)
    monitor.ingest({}, now=200)
    assert monitor.overview(now=200)["services"][3]["status"] == "unknown"
    monitor.ingest({"smtp": 0}, now=220)
    assert monitor.overview(now=220)["services"][3]["learning_seconds"] == 0
    for index in range(1,25):
        monitor.ingest({"smtp": 0}, now=220+index*5)
    row = monitor.overview(now=340)["services"][3]
    assert row["baseline"] == 0 and row["status"] == "normal"
    assert row["threshold"] == .15
    monitor.ingest({"smtp": .15}, now=345)
    assert monitor.overview(now=345)["services"][3]["status"] == "normal"
    monitor.ingest({"smtp": .16}, now=350)
    assert monitor.overview(now=350)["services"][3]["status"] == "anomalous"


def test_reference_does_not_learn_sustained_peak_and_unknown_is_not_zero(tmp_path):
    from backend.app.traffic import TrafficMonitor
    monitor = TrafficMonitor(tmp_path / "traffic.sqlite")
    for index in range(25):
        monitor.ingest({"dns": 3}, now=100+index*5)
    for index in range(40):
        monitor.ingest({"dns": 30}, now=225+index*5)
    row = monitor.overview(now=420)["services"][2]
    assert row["baseline"] == 3 and row["threshold"] == 9
    assert row["status"] == "anomalous"
    monitor.ingest({}, now=425)
    row = monitor.overview(now=425)["services"][2]
    assert row["rate"] is None and row["status"] == "unknown"
    assert row["baseline"] == 3


def test_route_protection_and_missing_data(tmp_path):
    from backend.tests.auth_helpers import authenticated_app, AuthenticatedClient
    from backend.app.config import Settings
    with AuthenticatedClient(authenticated_app(Settings(database_path=tmp_path / "events.sqlite",enable_probe=False,lab_token="lab-secret"))) as client:
        data = client.get("/api/security/traffic").json()
        assert len(data["services"]) == 4
        assert all(row["status"] == "unknown" for row in data["services"])
        assert client.post("/api/lab/traffic",json={"service":"all","duration":90}).status_code == 401
        assert client.post("/api/lab/traffic",headers={"X-Lab-Token":"lab-secret"},json={"service":"all","duration":1000}).status_code == 422
        assert client.post("/api/security/traffic/calibrate",headers={"X-Lab-Token":"lab-secret"},json={"service":"dns"}).status_code == 409


def test_recalibrate_is_explicit_and_metrics_do_not_retain_old_peak(tmp_path, monkeypatch):
    from backend.app.traffic import TrafficMonitor
    monitor = TrafficMonitor(tmp_path / "traffic.sqlite")
    for index in range(25):
        monitor.ingest({"dns": 1},now=100+index*5)
    monitor.recalibrate("dns",now=220)
    assert monitor.overview(now=220)["services"][2]["status"] == "learning"
    monkeypatch.setattr("backend.app.traffic.time.time",lambda:220)
    metrics = generate_latest(monitor.registry).decode()
    assert 'security_traffic_baseline_ready{service="dns"} 0.0' in metrics
    assert 'security_traffic_rate_per_second{service="web-demo"}' not in metrics


def test_failed_commit_does_not_publish_reference(tmp_path,monkeypatch):
    import sqlite3
    import pytest
    from contextlib import contextmanager
    from backend.app.traffic import TrafficMonitor
    monitor = TrafficMonitor(tmp_path / "traffic.sqlite")
    for index in range(24):
        monitor.ingest({"dns":1},now=100+index*5)
    original = monitor.connect
    class Connection:
        def __init__(self,db): self.db=db
        def __getattr__(self,name): return getattr(self.db,name)
        def commit(self): raise sqlite3.OperationalError("commit unavailable")
    @contextmanager
    def broken():
        with original() as db:
            yield Connection(db)
    monkeypatch.setattr(monitor,"connect",broken)
    with pytest.raises(sqlite3.OperationalError):
        monitor.ingest({"dns":1},now=220)
    assert monitor.overview(now=220)["services"][2]["baseline"] is None


def test_job_cancels_siblings_when_one_worker_fails(monkeypatch):
    import pytest
    from backend.app.traffic_load import TrafficLoad
    from backend.app.config import Settings
    async def scenario():
        load=TrafficLoad(Settings())
        stopped=asyncio.Event()
        async def worker(service,duration):
            if service=="smtp":
                await asyncio.sleep(.01)
                raise RuntimeError("worker failed")
            try:
                await asyncio.sleep(1)
            finally:
                stopped.set()
        monkeypatch.setattr(load,"worker",worker)
        await load.run(["dns","smtp"],30)
        assert load.overview()["status"]=="failed"
        assert stopped.is_set()
    asyncio.run(scenario())


def test_job_bounds_and_cancellation(monkeypatch):
    import pytest
    from backend.app.traffic_load import TrafficLoad
    from backend.app.config import Settings
    async def scenario():
        load=TrafficLoad(Settings())
        with pytest.raises(ValueError): load.start("http://external.test",30)
        with pytest.raises(ValueError): load.start("web-demo",91)
        async def worker(service,duration): await asyncio.sleep(3600)
        monkeypatch.setattr(load,"worker",worker)
        assert load.start("web-demo",30)["status"]=="running"
        with pytest.raises(ValueError): load.start("web-demo",30)
        assert (await load.stop())["status"]=="cancelled"
    asyncio.run(scenario())


def test_smtp_job_cancel_closes_pending_connection():
    from backend.app.traffic_load import TrafficLoad
    from backend.app.config import Settings
    async def scenario():
        accepted=asyncio.Event(); closed=asyncio.Event()
        async def handler(reader,writer):
            try:
                writer.write(b"220 local test\r\n"); await writer.drain()
                for code in [b"250 OK\r\n",b"250 OK\r\n",b"250 OK\r\n",b"354 Continue\r\n"]:
                    await reader.readline();writer.write(code);await writer.drain()
                await reader.readuntil(b"\r\n.\r\n")
                accepted.set()
                # Hold the final DATA response; cancellation must close the socket.
                await reader.read()
            finally:
                closed.set();writer.close()
        server=await asyncio.start_server(handler,"127.0.0.1",0)
        port=server.sockets[0].getsockname()[1]
        load=TrafficLoad(Settings(smtp_host="127.0.0.1",smtp_port=port))
        try:
            load.start("smtp",30)
            await asyncio.wait_for(accepted.wait(),2)
            await load.stop()
            await asyncio.wait_for(closed.wait(),.3)
            assert load.overview()["status"]=="cancelled"
        finally:
            await load.stop();server.close();await server.wait_closed()
    asyncio.run(scenario())


def test_prometheus_failure_and_invalid_rates_are_independent(tmp_path,monkeypatch):
    import httpx
    from backend.app.traffic import TrafficMonitor
    monitor=TrafficMonitor(tmp_path / "traffic.sqlite")
    for index in range(25):
        monitor.ingest({service:1 for service in ["web-demo","postgres","dns","smtp"]},now=100+index*5)
    monkeypatch.setattr("backend.app.traffic.time.time",lambda:225)
    class Prometheus:
        async def query(self,query):
            if "smtp_accepted_total" in query: raise httpx.ConnectError("unavailable")
            value="NaN" if "demo_http" in query else "-1" if "postgres" in query else ".2"
            return {"result":[{"value":[225,value]}]}
    asyncio.run(monitor.sample(Prometheus()))
    states={row["id"]:row for row in monitor.overview(now=225)["services"]}
    assert states["dns"]["status"]=="normal"
    for service in ["web-demo","postgres","smtp"]:
        assert states[service]["status"]=="unknown" and states[service]["rate"] is None
        assert states[service]["baseline"]==1
