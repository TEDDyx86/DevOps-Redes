"""Persistent, single-worker laboratory spool. No external relay configuration."""
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from prometheus_client import CollectorRegistry
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily, HistogramMetricFamily


class SMTPQueue:
    def __init__(self, path, capacity=1000):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.capacity = capacity
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY, sender TEXT NOT NULL, recipient TEXT NOT NULL,
                    content BLOB NOT NULL, state TEXT NOT NULL, accepted_at REAL NOT NULL,
                    delivered_at REAL, next_at REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS pending ON messages(state, next_at);
                CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL);
                INSERT OR IGNORE INTO counters VALUES ('rejected', 0), ('attempts_sent', 0), ('attempts_failed', 0);
                UPDATE messages SET state='pending' WHERE state='sending';
            """)
        self.registry = CollectorRegistry()
        self.registry.register(self)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def accept(self, sender, recipient, content, now=None):
        now = time.time() if now is None else now
        key = uuid.uuid4().hex
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT count(*) FROM messages WHERE state IN ('pending','sending')").fetchone()[0] >= self.capacity:
                raise OverflowError("queue full")
            db.execute("INSERT INTO messages VALUES (?,?,?,?, 'pending',?,NULL,?)",
                       (key, sender, recipient, content, now, now))
        return key

    def reject(self):
        with self.connection() as db:
            db.execute("UPDATE counters SET value=value+1 WHERE name='rejected'")

    def claim(self, now=None):
        now = time.time() if now is None else now
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM messages WHERE state='pending' AND next_at<=? ORDER BY accepted_at LIMIT 1", (now,)).fetchone()
            if row is None:
                return None
            db.execute("UPDATE messages SET state='sending' WHERE id=?", (row["id"],))
            return dict(row)

    def finish(self, key, outcome, now=None):
        if outcome not in {"sent", "retry", "failed"}:
            raise ValueError("invalid outcome")
        now = time.time() if now is None else now
        state = {"sent": "delivered", "retry": "pending", "failed": "failed"}[outcome]
        with self.connection() as db:
            cursor = db.execute("""UPDATE messages SET state=?, delivered_at=?, next_at=?,
                content=CASE WHEN ?='pending' THEN content ELSE X'' END WHERE id=? AND state='sending'""",
                (state, now if outcome == "sent" else None, now + 5, state, key))
            if cursor.rowcount:
                name = "attempts_sent" if outcome == "sent" else "attempts_failed"
                db.execute("UPDATE counters SET value=value+1 WHERE name=?", (name,))

    def stats(self, now=None):
        now = time.time() if now is None else now
        with self.connection() as db:
            db.execute("BEGIN")
            row = db.execute("""SELECT count(*) AS accepted,
                coalesce(sum(state='delivered'),0) AS delivered, coalesce(sum(state='failed'),0) AS failed,
                coalesce(sum(state IN ('pending','sending')),0) AS queue,
                coalesce(sum(accepted_at>=?),0) AS last_minute, coalesce(sum(accepted_at>=?),0) AS last_hour
                FROM messages""", (now-60, now-3600)).fetchone()
            stats = dict(row)
            stats.update({row["name"]: row["value"] for row in db.execute("SELECT * FROM counters")})
            stats["latencies"] = [max(0, row[0]) for row in db.execute("SELECT delivered_at-accepted_at FROM messages WHERE state='delivered'")]
        return stats

    def collect(self):
        stats = self.stats()
        for name in ("accepted", "delivered", "failed"):
            yield CounterMetricFamily(f"smtp_{name}", f"Persisted {name} messages", value=stats[name])
        yield CounterMetricFamily("smtp_rejected_recipients", "Rejected RCPT commands", value=stats["rejected"])
        attempts = CounterMetricFamily("smtp_delivery_attempts", "Completed forwarding attempts", labels=["outcome"])
        attempts.add_metric(["sent"], stats["attempts_sent"])
        attempts.add_metric(["failed"], stats["attempts_failed"])
        yield attempts
        for name, key in [("queue_messages", "queue"), ("accepted_last_minute", "last_minute"), ("accepted_last_hour", "last_hour")]:
            yield GaugeMetricFamily(f"smtp_{name}", key, value=stats[key])
        latencies = stats["latencies"]
        bounds = [.01, .025, .05, .1, .25, .5, 1, 2, 5, 15, 30, 60, 120, 300, float("inf")]
        buckets = [(str(bound), sum(value <= bound for value in latencies)) for bound in bounds]
        yield HistogramMetricFamily("smtp_delivery_latency_seconds", "Acceptance to local receiver confirmation; delivered messages only", buckets=buckets, sum_value=sum(latencies))
