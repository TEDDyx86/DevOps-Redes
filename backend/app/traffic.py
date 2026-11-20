"""Fixed measured traffic references, separate from the monitored services."""
import asyncio
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from prometheus_client import CollectorRegistry
from prometheus_client.core import GaugeMetricFamily

from .metrics import finite, scalar


SERVICES = {
    "web-demo": {"name":"HTTP", "floor":2, "unit":"req/s", "scale":1,
                 "rate":'sum(rate(demo_http_requests_total{job="web-demo",path!="/health"}[1m]))', "job":"web-demo", "probe":"probe"},
    "postgres": {"name":"PostgreSQL", "floor":5, "unit":"comandos/s", "scale":1,
                 "rate":'rate(postgres_workload_statements_total{job="platform"}[1m])', "job":"platform", "probe":"postgres_probe"},
    "dns": {"name":"DNS", "floor":5, "unit":"consultas/s", "scale":1,
            "rate":'sum(rate(coredns_dns_requests_total{job="dns"}[1m]))', "job":"dns", "probe":"dns_probe"},
    "smtp": {"name":"SMTP", "floor":.15, "unit":"msg/min", "scale":60,
             "rate":'rate(smtp_accepted_total{job="smtp"}[1m])', "job":"smtp", "probe":"smtp_probe"},
}


def expression(service):
    item = SERVICES[service]
    probe = item["probe"]
    gates = [f'min(up{{job="{item["job"]}"}}) == 1',
             f'max(time() - timestamp(up{{job="{item["job"]}"}})) < 20',
             f'min({probe}_success{{job="platform"}}) == 1',
             f'time() - max({probe}_checked_at_seconds{{job="platform"}}) < 20',
             f'time() - max({probe}_checked_at_seconds{{job="platform"}}) >= -5']
    if service == "postgres":
        gates.extend(['min(postgres_stats_success{job="platform"}) == 1',
                      'time() - max(postgres_stats_checked_at_seconds{job="platform"}) < 20',
                      'time() - max(postgres_stats_checked_at_seconds{job="platform"}) >= -5'])
    return f'({item["rate"]})' + ''.join(f' and on() ({gate})' for gate in gates)


class TrafficMonitor:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS traffic_baselines (service TEXT PRIMARY KEY, rate REAL NOT NULL, calibrated_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS traffic_samples (service TEXT NOT NULL, at REAL NOT NULL, rate REAL NOT NULL, PRIMARY KEY(service,at));
            """)
            self.baselines = {row["service"]:dict(row) for row in db.execute("SELECT * FROM traffic_baselines")}
        self.snapshot = {}
        self.registry = CollectorRegistry()
        self.registry.register(self)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def ingest(self, rates, now=None):
        now = time.time() if now is None else now
        with self.lock, self.connect() as db:
            baselines = dict(self.baselines)
            snapshot = {}
            for service in SERVICES:
                rate = finite(rates.get(service))
                if rate is not None and rate < 0:
                    rate = None
                seconds = 0
                if service not in baselines:
                    last = db.execute("SELECT max(at) FROM traffic_samples WHERE service=?", (service,)).fetchone()[0]
                    if rate is None or (last is not None and (now-last>15 or now<last)):
                        db.execute("DELETE FROM traffic_samples WHERE service=?",(service,))
                    if rate is not None:
                        db.execute("INSERT OR REPLACE INTO traffic_samples VALUES (?,?,?)",(service,now,rate))
                        sample = db.execute("SELECT count(*), min(at), avg(rate) FROM traffic_samples WHERE service=?", (service,)).fetchone()
                        seconds = max(0,now-sample[1])
                        if sample[0]>=25 and seconds>=120:
                            db.execute("INSERT OR REPLACE INTO traffic_baselines VALUES (?,?,?)",(service,sample[2],now))
                            baselines[service] = {"rate":sample[2],"calibrated_at":now}
                            db.execute("DELETE FROM traffic_samples WHERE service=?",(service,))
                snapshot[service] = {"rate":rate,"checked_at":now,"learning_seconds":min(120,seconds)}
            # Publish only after the transaction succeeds, while still holding
            # the lock so API/scrapes cannot observe partial state.
            db.commit()
            self.baselines, self.snapshot = baselines, snapshot

    def overview(self, now=None):
        now = time.time() if now is None else now
        rows = []
        with self.lock:
            for service,item in SERVICES.items():
                sample = self.snapshot.get(service,{})
                checked = sample.get("checked_at")
                fresh = checked is not None and -5 <= now-checked <= 20
                rate = sample.get("rate") if fresh else None
                reference = self.baselines.get(service)
                baseline = reference["rate"] if reference else None
                threshold = max(baseline*3,item["floor"]) if baseline is not None else None
                status = "unknown" if rate is None else "learning" if baseline is None else "anomalous" if rate>threshold else "normal"
                rows.append({"id":service,"name":item["name"],"unit":item["unit"],"scale":item["scale"],
                             "status":status,"rate":rate,"baseline":baseline,"threshold":threshold,
                             "calibrated_at":reference["calibrated_at"] if reference else None,
                             "learning_seconds":sample.get("learning_seconds",0),"checked_at":checked})
        return {"generated_at":now,"window_seconds":60,"learning_required_seconds":120,"factor":3,"services":rows}

    def recalibrate(self, service, now=None):
        now = time.time() if now is None else now
        with self.lock:
            row = next(item for item in self.overview(now)["services"] if item["id"]==service)
            if row["status"] != "normal":
                raise ValueError("Recalibre somente um serviço com dados atuais e volume normal.")
            with self.connect() as db:
                db.execute("DELETE FROM traffic_baselines WHERE service=?",(service,))
                db.execute("DELETE FROM traffic_samples WHERE service=?",(service,))
                db.execute("INSERT INTO traffic_samples VALUES (?,?,?)",(service,now,row["rate"]))
            self.baselines.pop(service,None)
            self.snapshot[service] = {"rate":row["rate"],"checked_at":now,"learning_seconds":0}

    async def sample(self, prometheus):
        results = await asyncio.gather(*(prometheus.query(expression(service)) for service in SERVICES),return_exceptions=True)
        rates = {}
        for service,result in zip(SERVICES,results):
            try:
                rates[service] = scalar(result) if not isinstance(result,BaseException) else None
            except (ValueError,TypeError,KeyError):
                rates[service] = None
        await asyncio.to_thread(self.ingest,rates)

    async def run(self, prometheus):
        while True:
            try:
                await self.sample(prometheus)
            except (sqlite3.Error,OSError):
                logging.exception("Referência de tráfego indisponível; nova tentativa no próximo ciclo")
                with self.lock:
                    self.snapshot = {}
            await asyncio.sleep(5)

    def collect(self):
        rows = self.overview()["services"]
        fields = {"sample_success":lambda r:int(r["rate"] is not None),
                  "baseline_ready":lambda r:int(r["baseline"] is not None),
                  "rate_per_second":lambda r:r["rate"],"baseline_per_second":lambda r:r["baseline"],
                  "threshold_per_second":lambda r:r["threshold"],
                  "anomaly":lambda r:None if r["status"] in {"unknown","learning"} else int(r["status"]=="anomalous")}
        for name, value_for in fields.items():
            metric = GaugeMetricFamily(f"security_traffic_{name}",name,labels=["service"])
            for row in rows:
                value = value_for(row)
                if value is not None:
                    metric.add_metric([row["id"]],value)
            yield metric
