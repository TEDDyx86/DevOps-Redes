import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def utc_instant(value):
    """Only timezone-aware, representable timestamps can support reconciliation."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def resolution_window(started_at, ended_at, ceiling=None):
    start, end = utc_instant(started_at), utc_instant(ended_at)
    ceiling = ceiling or datetime.now(timezone.utc) + timedelta(seconds=5)
    return (start, end) if start is not None and end is not None and start <= end <= ceiling else None


class IncidentStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            # Serialize schema migration and its data updates across API processes.
            db.execute("BEGIN IMMEDIATE")
            db.execute("""CREATE TABLE IF NOT EXISTS incidents (
                fingerprint TEXT NOT NULL, started_at TEXT NOT NULL,
                ended_at TEXT, name TEXT NOT NULL, summary TEXT NOT NULL,
                description TEXT NOT NULL, severity TEXT NOT NULL,
                service TEXT NOT NULL, status TEXT NOT NULL,
                PRIMARY KEY(fingerprint, started_at)
            )""")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(incidents)")}
            for name in ("resolution_source", "reconciled_at", "resolution_evidence_started_at", "resolution_evidence_ended_at"):
                if name not in columns:
                    db.execute(f"ALTER TABLE incidents ADD COLUMN {name} TEXT")
            db.execute("""CREATE INDEX IF NOT EXISTS incidents_firing_identity
                          ON incidents(fingerprint, name, service, severity) WHERE status = 'firing'""")
            db.execute("""UPDATE incidents SET resolution_source = 'alertmanager'
                          WHERE status = 'resolved' AND resolution_source IS NULL""")
            self._reconcile(db)

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
                if alert["status"] == "resolved" and resolution_window(alert["startsAt"], ended_at) is None:
                    raise ValueError("Resolução exige início/término com fuso, em ordem e sem término futuro.")
                db.execute("""INSERT INTO incidents
                    (fingerprint, started_at, ended_at, name, summary, description, severity, service, status, resolution_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(fingerprint, started_at) DO UPDATE SET
                    ended_at = COALESCE(excluded.ended_at, incidents.ended_at),
                    status = CASE WHEN incidents.status = 'resolved' THEN 'resolved' ELSE excluded.status END,
                    resolution_source = CASE WHEN excluded.ended_at IS NOT NULL THEN 'alertmanager' ELSE incidents.resolution_source END,
                    reconciled_at = CASE WHEN excluded.ended_at IS NOT NULL THEN NULL ELSE incidents.reconciled_at END,
                    resolution_evidence_started_at = CASE WHEN excluded.ended_at IS NOT NULL THEN NULL ELSE incidents.resolution_evidence_started_at END,
                    resolution_evidence_ended_at = CASE WHEN excluded.ended_at IS NOT NULL THEN NULL ELSE incidents.resolution_evidence_ended_at END
                """, (alert["fingerprint"], alert["startsAt"], ended_at,
                      labels.get("alertname", "Alerta"), annotations.get("summary", "Alerta recebido"),
                      annotations.get("description", ""), labels.get("severity", "warning"),
                      labels.get("service", "web-demo"), alert["status"],
                      "alertmanager" if alert["status"] == "resolved" else None))
            self._reconcile(db)

    def _reconcile(self, db):
        """A later direct resolution proves closure, never its missing original time."""
        now = datetime.now(timezone.utc)
        ceiling = now + timedelta(seconds=5)
        candidates = db.execute("SELECT * FROM incidents WHERE status = 'firing'").fetchall()
        if not candidates:
            return
        proofs = {}
        identities = {(row["fingerprint"], row["name"], row["service"], row["severity"]) for row in candidates}
        for key in identities:
            # The primary key narrows this to one fingerprint; no correlated full-history scan.
            for row in db.execute("""SELECT started_at, ended_at FROM incidents
                    WHERE fingerprint = ? AND name = ? AND service = ? AND severity = ?
                      AND status = 'resolved' AND resolution_source = 'alertmanager' AND ended_at IS NOT NULL""", key):
                window = resolution_window(row["started_at"], row["ended_at"], ceiling)
                if window is not None:
                    start, end = window
                    proofs.setdefault(key, []).append((end, start, row["started_at"], row["ended_at"]))
        for row in candidates:
            start = utc_instant(row["started_at"])
            if start is None:
                continue
            key = (row["fingerprint"], row["name"], row["service"], row["severity"])
            later = [proof for proof in proofs.get(key, []) if proof[1] > start]
            if not later:
                continue
            proof = min(later)  # Earliest confirmed later end, compared as UTC instants.
            db.execute("""UPDATE incidents SET status = 'resolved', ended_at = NULL,
                    resolution_source = 'later_resolved_event', reconciled_at = ?,
                    resolution_evidence_started_at = ?, resolution_evidence_ended_at = ?
                    WHERE fingerprint = ? AND started_at = ? AND status = 'firing'""",
                (now.isoformat().replace("+00:00", "Z"), proof[2], proof[3], row["fingerprint"], row["started_at"]))

    def list(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM incidents ORDER BY started_at DESC LIMIT 100")]
