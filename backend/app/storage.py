import sqlite3
from pathlib import Path


class IncidentStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS incidents (
                fingerprint TEXT NOT NULL, started_at TEXT NOT NULL,
                ended_at TEXT, name TEXT NOT NULL, summary TEXT NOT NULL,
                description TEXT NOT NULL, severity TEXT NOT NULL,
                service TEXT NOT NULL, status TEXT NOT NULL,
                PRIMARY KEY(fingerprint, started_at)
            )""")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        return db

    def ingest(self, alerts):
        with self.connect() as db:
            for alert in alerts:
                labels = alert["labels"]
                annotations = alert.get("annotations", {})
                ended_at = alert.get("endsAt") if alert["status"] == "resolved" else None
                db.execute("""INSERT INTO incidents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(fingerprint, started_at) DO UPDATE SET
                    ended_at = COALESCE(excluded.ended_at, incidents.ended_at),
                    status = CASE WHEN incidents.status = 'resolved' THEN 'resolved' ELSE excluded.status END
                """, (alert["fingerprint"], alert["startsAt"], ended_at,
                      labels.get("alertname", "Alerta"), annotations.get("summary", "Alerta recebido"),
                      annotations.get("description", ""), labels.get("severity", "warning"),
                      labels.get("service", "web-demo"), alert["status"]))

    def list(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM incidents ORDER BY started_at DESC LIMIT 100")]
