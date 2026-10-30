import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.app.config import Settings
from backend.app.storage import IncidentStore
from backend.tests.auth_helpers import AuthenticatedClient, authenticated_app


OLD = "2020-01-01T12:00:00Z"
LATER = "2020-01-02T12:00:00Z"
END = "2020-01-02T12:05:00Z"


def event(start=OLD, end=None, **changes):
    value = {"fingerprint": "same-alert", "startsAt": start, "endsAt": end,
             "status": "resolved" if end else "firing",
             "labels": {"alertname": "PostgreSQLIndisponivel", "service": "postgres", "severity": "critical"},
             "annotations": {"summary": "Banco indisponível", "description": "Evidência original"}}
    value.update(changes)
    return value


def by_start(store, start):
    return next(row for row in store.list() if row["started_at"] == start)


def legacy_database(path, alerts):
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE incidents (
            fingerprint TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT,
            name TEXT NOT NULL, summary TEXT NOT NULL, description TEXT NOT NULL,
            severity TEXT NOT NULL, service TEXT NOT NULL, status TEXT NOT NULL,
            PRIMARY KEY(fingerprint, started_at))""")
        for alert in alerts:
            labels, annotations = alert["labels"], alert["annotations"]
            db.execute("INSERT INTO incidents VALUES (?,?,?,?,?,?,?,?,?)",
                       (alert["fingerprint"], alert["startsAt"], alert["endsAt"], labels["alertname"],
                        annotations["summary"], annotations["description"], labels["severity"], labels["service"], alert["status"]))


def assert_reconciled(row, start=LATER, end=END):
    assert row["status"] == "resolved"
    assert row["ended_at"] is None  # Do not invent the original end time.
    assert row["resolution_source"] == "later_resolved_event"
    assert row["reconciled_at"]
    assert row["resolution_evidence_started_at"] == start
    assert row["resolution_evidence_ended_at"] == end


def test_later_resolution_reconciles_missing_cycle_without_deleting_history(tmp_path):
    store = IncidentStore(tmp_path / "incidents.sqlite")
    store.ingest([event()])
    store.ingest([event(LATER, END)])
    assert len(store.list()) == 2
    old = by_start(store, OLD)
    assert_reconciled(old)
    assert old["description"] == "Evidência original" and old["started_at"] == OLD
    direct = by_start(store, LATER)
    assert direct["ended_at"] == END and direct["resolution_source"] == "alertmanager"


def test_legacy_migration_uses_persisted_proof_and_is_idempotent(tmp_path):
    path = tmp_path / "incidents.sqlite"
    legacy_database(path, [event(), event(LATER, END)])
    first = IncidentStore(path).list()
    assert_reconciled(next(row for row in first if row["started_at"] == OLD))
    assert IncidentStore(path).list() == first


def test_newer_firing_cycle_remains_open_and_delayed_duplicate_does_not_reopen_old(tmp_path):
    store = IncidentStore(tmp_path / "incidents.sqlite")
    store.ingest([event(), event(LATER, END), event("2020-01-03T12:00:00Z")])
    saved = by_start(store, OLD)
    store.ingest([event(), event(LATER)])
    assert by_start(store, OLD) == saved
    assert by_start(store, "2020-01-03T12:00:00Z")["status"] == "firing"


def test_actual_late_resolution_replaces_inference_and_preserves_original_timestamp(tmp_path):
    store = IncidentStore(tmp_path / "incidents.sqlite")
    store.ingest([event(), event(LATER, END)])
    original_end = "2020-01-01T12:05:00Z"
    store.ingest([event(OLD, original_end), event()])
    old = by_start(store, OLD)
    assert old["status"] == "resolved" and old["ended_at"] == original_end
    assert old["resolution_source"] == "alertmanager"
    assert old["reconciled_at"] is None
    assert old["resolution_evidence_started_at"] is None
    assert old["resolution_evidence_ended_at"] is None


@pytest.mark.parametrize("change", [
    {"fingerprint": "different-alert"},
    {"labels": {"alertname": "OtherAlert", "service": "postgres", "severity": "critical"}},
    {"labels": {"alertname": "PostgreSQLIndisponivel", "service": "dns", "severity": "critical"}},
    {"labels": {"alertname": "PostgreSQLIndisponivel", "service": "postgres", "severity": "warning"}},
    {"startsAt": "2019-12-31T12:00:00Z", "endsAt": "2019-12-31T12:05:00Z"},
    {"endsAt": None},
    {"endsAt": "2020-01-01T12:05:00Z"},
    {"endsAt": "2999-01-02T12:05:00Z"},
    {"endsAt": "invalid"},
    {"endsAt": "2020-01-02T12:05:00"},
    {"startsAt": "invalid"},
    {"startsAt": "2020-01-02T12:00:00"},
    {"status": "firing"},
])
def test_unconfirmed_or_unrelated_proof_does_not_close_incident(tmp_path, change):
    path = tmp_path / "incidents.sqlite"
    legacy_database(path, [event(), event(LATER, END, **change)])
    assert by_start(IncidentStore(path), OLD)["status"] == "firing"


def test_utc_comparison_handles_offsets_and_fractional_seconds(tmp_path):
    store = IncidentStore(tmp_path / "incidents.sqlite")
    old = "2020-01-02T13:00:00+02:00"  # 11:00 UTC; lexical ordering would be wrong.
    later = "2020-01-02T11:00:00.100000Z"
    end = "2020-01-02T11:01:00Z"
    store.ingest([event(old), event(later, end)])
    assert_reconciled(by_start(store, old), later, end)


def test_equivalent_start_instants_do_not_prove_a_later_cycle(tmp_path):
    store = IncidentStore(tmp_path / "incidents.sqlite")
    store.ingest([event(OLD), event("2020-01-01T13:00:00+01:00", "2020-01-01T13:05:00+01:00")])
    assert by_start(store, OLD)["status"] == "firing"


def test_late_out_of_order_cycle_is_reconciled_from_existing_direct_proof(tmp_path):
    store = IncidentStore(tmp_path / "incidents.sqlite")
    store.ingest([event(LATER, END)])
    store.ingest([event()])
    assert_reconciled(by_start(store, OLD))


def test_failed_ingestion_rolls_back_proof_and_reconciliation(tmp_path, monkeypatch):
    store = IncidentStore(tmp_path / "incidents.sqlite")
    store.ingest([event()])
    original = store._reconcile
    def fail_after_update(db):
        original(db)
        raise sqlite3.OperationalError("simulated commit failure")
    monkeypatch.setattr(store, "_reconcile", fail_after_update)
    with pytest.raises(sqlite3.OperationalError):
        store.ingest([event(LATER, END)])
    rows = store.list()
    assert len(rows) == 1 and rows[0]["status"] == "firing"


def test_concurrent_duplicate_ingestion_remains_consistent(tmp_path):
    store = IncidentStore(tmp_path / "incidents.sqlite")
    batches = [[event()], [event(LATER, END)], [event()], [event(LATER, END)]]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(store.ingest, batches))
    assert len(store.list()) == 2
    assert_reconciled(by_start(store, OLD))


@pytest.mark.parametrize("end", [None, "2019-12-31T12:00:00Z", "2999-01-01T12:05:00Z", "invalid", "2020-01-01T12:05:00"])
def test_invalid_direct_resolution_cannot_erase_valid_reconciliation(tmp_path, end):
    store = IncidentStore(tmp_path / "incidents.sqlite")
    store.ingest([event(), event(LATER, END)])
    saved = store.list()
    with pytest.raises(ValueError):
        store.ingest([event("2020-01-03T12:00:00Z"), event(OLD, end, status="resolved")])
    assert store.list() == saved  # The whole batch is rolled back, including the new firing.


def test_all_resolved_history_has_bounded_reconciliation_cost(tmp_path):
    store = IncidentStore(tmp_path / "incidents.sqlite")
    with store.connect() as db:
        db.executemany("""INSERT INTO incidents
            (fingerprint, started_at, ended_at, name, summary, description, severity, service, status, resolution_source)
            VALUES ('same-alert', ?, ?, 'PostgreSQLIndisponivel', '', '', 'critical', 'postgres', 'resolved', 'alertmanager')""",
            [(f"2020-01-01T12:00:00.{n:06d}Z", END) for n in range(8000)])
        calls = 0
        def budget():
            nonlocal calls
            calls += 1
            return calls > 5000  # Five million SQLite VM operations, independent of wall-clock speed.
        db.set_progress_handler(budget, 1000)
        store._reconcile(db)
        db.set_progress_handler(None, 0)
        assert db.execute("SELECT count(*) FROM incidents").fetchone()[0] == 8000


def test_webhook_rejects_invalid_resolution_without_mutating_history(tmp_path):
    settings = Settings(database_path=tmp_path / "incidents.sqlite", webhook_token="test-hook", enable_probe=False)
    with AuthenticatedClient(authenticated_app(settings)) as client:
        headers = {"Authorization": "Bearer test-hook"}
        client.post("/api/webhooks/alerts", headers=headers, json={"alerts": [event(), event(LATER, END)]}).raise_for_status()
        saved = client.get("/api/incidents").json()
        response = client.post("/api/webhooks/alerts", headers=headers,
                               json={"alerts": [event(OLD, "2019-12-31T12:00:00Z")]})
        assert response.status_code == 422
        assert client.get("/api/incidents").json() == saved


def test_webhook_exposes_evidence_and_cannot_be_used_without_credential(tmp_path):
    settings = Settings(database_path=tmp_path / "incidents.sqlite", webhook_token="test-hook", enable_probe=False)
    with AuthenticatedClient(authenticated_app(settings)) as client:
        payload = {"alerts": [event(), event(LATER, END)]}
        assert client.post("/api/webhooks/alerts", json=payload).status_code == 401
        assert client.get("/api/incidents").json()["incidents"] == []
        response = client.post("/api/webhooks/alerts", headers={"Authorization": "Bearer test-hook"}, json=payload)
        assert response.status_code == 200 and response.json()["accepted"] == 2
        rows = client.get("/api/incidents").json()["incidents"]
        assert_reconciled(next(row for row in rows if row["started_at"].startswith("2020-01-01")),
                          "2020-01-02T12:00:00Z", "2020-01-02T12:05:00Z")
