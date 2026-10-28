import hashlib
import hmac
import math
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from prometheus_client import CollectorRegistry
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

from .passwords import parse_hash, verify_password


WINDOW = 60
IP_LIMIT = 5
ACCOUNT_LIMIT = 10
SESSION_SECONDS = 8 * 3600


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class AuthStore:
    def __init__(self, path, username, password_hash):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.username = username.casefold()
        self.password_hash = password_hash
        self.configured = bool(self.username and parse_hash(password_hash))
        self.version = token_hash(self.username + ":" + password_hash)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS auth_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL,
                    username TEXT NOT NULL, ip TEXT NOT NULL, outcome TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS auth_time ON auth_events(at);
                CREATE INDEX IF NOT EXISTS auth_ip ON auth_events(ip, at);
                CREATE INDEX IF NOT EXISTS auth_user ON auth_events(username, at);
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, csrf TEXT NOT NULL,
                    expires_at REAL NOT NULL, version TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS auth_totals (outcome TEXT PRIMARY KEY, total INTEGER NOT NULL);
                INSERT OR IGNORE INTO auth_totals VALUES ('success',0),('failure',0),('blocked',0);
                CREATE TABLE IF NOT EXISTS auth_budget (
                    id INTEGER PRIMARY KEY, at REAL NOT NULL, username TEXT NOT NULL,
                    ip TEXT NOT NULL, outcome TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS budget_time ON auth_budget(at);
                CREATE TABLE IF NOT EXISTS auth_blocks (second INTEGER PRIMARY KEY, total INTEGER NOT NULL);
            """)
            interrupted = db.execute("UPDATE auth_budget SET outcome='failure' WHERE outcome='pending'").rowcount
            db.execute("UPDATE auth_events SET outcome='failure' WHERE outcome='pending'")
            db.execute("UPDATE auth_totals SET total=total+? WHERE outcome='failure'", (interrupted,))
            db.execute("DELETE FROM auth_sessions WHERE version != ?", (self.version,))
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

    @staticmethod
    def record(db, now, username, ip, outcome):
        key = db.execute("INSERT INTO auth_events(at,username,ip,outcome) VALUES (?,?,?,?)", (now,username,ip,outcome)).lastrowid
        # The history is bounded independently of the short-lived rate budget.
        db.execute("DELETE FROM auth_events WHERE id<=? OR at<?", (key-10000, now-7*86400))
        return key

    def login(self, username, password, ip, now=None, previous_token=""):
        now = time.time() if now is None else now
        if not self.configured:
            return {"status": 503}
        username = username.casefold()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM auth_budget WHERE at<=?", (now-WINDOW,))
            db.execute("DELETE FROM auth_blocks WHERE second<=?", (int(now)-WINDOW,))
            db.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now,))
            waits = []
            for column, value, limit in [("ip", ip, IP_LIMIT), ("username", username, ACCOUNT_LIMIT)]:
                # Column is selected from fixed literals, never supplied by the request.
                rows = db.execute(f"SELECT at FROM auth_budget WHERE {column}=? AND at>? AND at<=? AND outcome IN ('failure','pending') ORDER BY at", (value, now-WINDOW, now)).fetchall()
                if len(rows) >= limit:
                    waits.append(math.ceil(rows[-limit]["at"] + WINDOW-now))
            if waits:
                self.record(db,now,username,ip,"blocked")
                db.execute("INSERT INTO auth_blocks VALUES (?,1) ON CONFLICT(second) DO UPDATE SET total=total+1", (int(now),))
                db.execute("UPDATE auth_totals SET total=total+1 WHERE outcome='blocked'")
                return {"status": 429, "retry_after": max(1, max(waits))}
            event_id = self.record(db,now,username,ip,"pending")
            db.execute("INSERT INTO auth_budget VALUES (?,?,?,?,'pending')", (event_id,now,username,ip))
        # Reserve before hashing; do not hold a write lock during expensive work.
        valid_password = verify_password(password, self.password_hash)
        valid = valid_password and hmac.compare_digest(username.encode(), self.username.encode())
        outcome = "success" if valid else "failure"
        with self.connect() as db:
            db.execute("UPDATE auth_events SET outcome=? WHERE id=?", (outcome, event_id))
            if valid:
                db.execute("DELETE FROM auth_budget WHERE id=?", (event_id,))
            else:
                db.execute("UPDATE auth_budget SET outcome='failure' WHERE id=?", (event_id,))
            db.execute("UPDATE auth_totals SET total=total+1 WHERE outcome=?", (outcome,))
            if not valid:
                return {"status": 401}
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            db.execute("DELETE FROM auth_sessions WHERE token_hash=?", (token_hash(previous_token),))
            db.execute("INSERT INTO auth_sessions VALUES (?,?,?,?,?)", (token_hash(token), self.username, csrf, now+SESSION_SECONDS, self.version))
        return {"status": 200, "token": token, "csrf_token": csrf, "username": self.username, "expires_at": now+SESSION_SECONDS}

    def session(self, token, now=None):
        if not token or len(token) > 128 or not self.configured:
            return None
        now = time.time() if now is None else now
        with self.connect() as db:
            row = db.execute("SELECT username,csrf,expires_at FROM auth_sessions WHERE token_hash=? AND expires_at>? AND version=?", (token_hash(token), now, self.version)).fetchone()
        return {"username": row["username"], "csrf_token": row["csrf"], "expires_at": row["expires_at"]} if row else None

    def logout(self, token, username, ip):
        with self.connect() as db:
            db.execute("DELETE FROM auth_sessions WHERE token_hash=?", (token_hash(token),))
            self.record(db,time.time(),username,ip,"logout")

    def stats(self, now=None):
        now = time.time() if now is None else now
        with self.connect() as db:
            db.execute("BEGIN")
            totals = {row["outcome"]: row["total"] for row in db.execute("SELECT * FROM auth_totals")}
            maxima = {}
            for scope, column in [("ip", "ip"), ("account", "username")]:
                row = db.execute(f"SELECT max(failures) FROM (SELECT count(*) failures FROM auth_budget WHERE outcome='failure' AND at>? AND at<=? GROUP BY {column})", (now-WINDOW, now)).fetchone()
                maxima[scope] = row[0] or 0
            blocked = db.execute("SELECT coalesce(sum(total),0) FROM auth_blocks WHERE second>? AND second<=?", (int(now)-WINDOW,int(now))).fetchone()[0]
            events = [dict(row) for row in db.execute("SELECT id,at,username,ip,outcome FROM auth_events WHERE outcome!='pending' AND at>=? ORDER BY id DESC LIMIT 100", (now-7*86400,))]
        return {"totals": totals, "failures_recent": maxima, "blocked_recent": blocked, "events": events,
                "window_seconds": WINDOW, "ip_limit": IP_LIMIT, "account_limit": ACCOUNT_LIMIT, "generated_at": now}

    def collect(self):
        stats = self.stats()
        counter = CounterMetricFamily("security_auth_attempts", "Completed login attempts", labels=["outcome"])
        for outcome, value in stats["totals"].items():
            counter.add_metric([outcome], value)
        yield counter
        gauge = GaugeMetricFamily("security_auth_failures_recent", "Maximum failed logins per IP/account in the last 60 seconds", labels=["scope"])
        for scope, value in stats["failures_recent"].items():
            gauge.add_metric([scope], value)
        yield gauge
        yield GaugeMetricFamily("security_auth_blocked_recent", "Blocked login attempts in the last 60 seconds", value=stats["blocked_recent"])
