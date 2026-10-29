import hashlib
from pathlib import Path

import pytest


def fixture_files(tmp_path):
    from backend.app.integrity import FILES
    root=tmp_path/"infra"
    for item in FILES.values():
        path=root/item["path"];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b"original configuration\n")
    return root


def test_first_hash_is_not_trusted_and_approval_persists(tmp_path):
    from backend.app.integrity import IntegrityMonitor
    root=fixture_files(tmp_path); monitor=IntegrityMonitor(tmp_path/"integrity.sqlite",root)
    monitor.sample(now=100)
    row=monitor.overview(now=100)["files"][0]
    assert row["status"]=="unapproved" and row["approved_sha256"] is None
    digest=hashlib.sha256(b"original configuration\n").hexdigest()
    assert row["observed_sha256"]==digest
    monitor.approve([{ "file_id":row["id"],"observed_sha256":digest}],"admin",now=101)
    assert monitor.overview(now=101)["files"][0]["status"]=="ok"
    restarted=IntegrityMonitor(tmp_path/"integrity.sqlite",root)
    assert restarted.overview(now=102)["files"][0]["status"]=="unknown"
    restarted.sample(now=102)
    assert restarted.overview(now=102)["files"][0]["approved_sha256"]==digest
    assert restarted.overview(now=125)["files"][0]["status"]=="unknown"


def test_change_missing_restore_and_deduplication(tmp_path):
    from backend.app.integrity import IntegrityMonitor
    root=fixture_files(tmp_path);monitor=IntegrityMonitor(tmp_path/"integrity.sqlite",root)
    monitor.sample(now=100);row=monitor.overview(now=100)["files"][0]
    monitor.approve([{"file_id":row["id"],"observed_sha256":row["observed_sha256"]}],"admin",now=101)
    path=root/row["path"];path.write_bytes(b"changed\n");monitor.sample(now=102)
    assert monitor.overview(now=102)["files"][0]["status"]=="changed"
    before=len(monitor.overview(now=102)["events"])
    monitor.sample(now=103)
    assert len(monitor.overview(now=103)["events"])==before
    path.unlink();monitor.sample(now=104)
    assert monitor.overview(now=104)["files"][0]["status"]=="missing"
    path.write_bytes(b"original configuration\n");monitor.sample(now=105)
    row=monitor.overview(now=105)["files"][0]
    assert row["status"]=="ok" and row["approved_by"]=="admin"
    assert any(event["kind"]=="restored" for event in monitor.overview(now=105)["events"])


def test_stale_or_duplicate_approval_does_not_change_any_reference(tmp_path):
    from backend.app.integrity import IntegrityMonitor
    root=fixture_files(tmp_path);monitor=IntegrityMonitor(tmp_path/"integrity.sqlite",root)
    monitor.sample(now=100);rows=monitor.overview(now=100)["files"]
    items=[{"file_id":row["id"],"observed_sha256":row["observed_sha256"]} for row in rows[:2]]
    (root/rows[1]["path"]).write_bytes(b"changed after review")
    with pytest.raises(ValueError):monitor.approve(items,"admin",now=101)
    assert all(row["approved_sha256"] is None for row in monitor.overview(now=101)["files"])
    with pytest.raises(ValueError):monitor.approve([items[0],items[0]],"admin",now=101)
    with pytest.raises(ValueError):monitor.approve([{"file_id":"../.env","observed_sha256":"0"*64}],"admin",now=101)


def test_safe_reader_rejects_escape_links_special_files_and_large_data(tmp_path):
    from backend.app.integrity_files import observe_file
    root=tmp_path/"infra";root.mkdir()
    (root/"large").write_bytes(b"x"*(1024*1024+1))
    assert observe_file(root,"large")["status"]=="unreadable"
    assert observe_file(root,"../outside")["status"]=="unreadable"
    assert observe_file(root,"missing")["status"]=="missing"
    (root/"directory").mkdir()
    assert observe_file(root,"directory")["status"]=="unreadable"


def test_protected_routes_and_unconfigured_detector(tmp_path):
    from backend.tests.auth_helpers import authenticated_app,AuthenticatedClient
    from backend.app.config import Settings
    with AuthenticatedClient(authenticated_app(Settings(database_path=tmp_path/"events.sqlite",enable_probe=False,lab_token="lab-secret"))) as client:
        response=client.get("/api/security/integrity");assert response.status_code==200
        assert response.json()["enabled"] is False
        body={"items":[{"file_id":"http-runtime","observed_sha256":"0"*64}]}
        assert client.post("/api/security/integrity/approve",json=body).status_code==401
        assert client.post("/api/security/integrity/approve",headers={"X-Lab-Token":"lab-secret"},json=body).status_code==409


def test_runtime_config_is_used_and_invalid_limits_are_rejected(tmp_path):
    from demo.config import load_http_config,load_smtp_config
    from demo.main import create_demo
    from fastapi.testclient import TestClient
    config=tmp_path/"http.json";config.write_text('{"message":"configured reply","work_delay_seconds":0.001,"slow_delay_seconds":0.85}')
    with TestClient(create_demo("token",runtime_config=load_http_config(config))) as client:
        assert client.get("/work").json()["message"]=="configured reply"
    config.write_text('{"work_delay_seconds":1000}')
    with pytest.raises(ValueError):load_http_config(config)
    smtp=tmp_path/"smtp.json";smtp.write_text('{"message_size_limit":65536,"queue_capacity":1000}')
    assert load_smtp_config(smtp).message_size_limit==65536
    smtp.write_text('{"queue_capacity":1000000}')
    with pytest.raises(ValueError):load_smtp_config(smtp)


def test_approval_is_idempotent_and_restart_does_not_duplicate_events(tmp_path):
    from backend.app.integrity import IntegrityMonitor
    root=fixture_files(tmp_path);path=tmp_path/"integrity.sqlite"
    monitor=IntegrityMonitor(path,root);monitor.sample(now=100)
    row=monitor.overview(now=100)["files"][0]
    items=[{"file_id":row["id"],"observed_sha256":row["observed_sha256"]}]
    monitor.approve(items,"admin",now=101)
    before=monitor.overview(now=101)
    monitor.approve(items,"other",now=102)
    assert monitor.overview(now=102)["events"]==before["events"]
    assert monitor.overview(now=102)["files"][0]["approved_by"]=="admin"
    monitor=IntegrityMonitor(path,root);monitor.sample(now=103)
    assert monitor.overview(now=103)["events"]==before["events"]


def test_metrics_do_not_depend_on_event_database_and_omit_unknown_change(tmp_path,monkeypatch):
    import time
    from prometheus_client import generate_latest
    from backend.app.integrity import IntegrityMonitor
    root=fixture_files(tmp_path);monitor=IntegrityMonitor(tmp_path/"integrity.sqlite",root)
    monitor.sample()
    def unavailable():raise OSError("storage unavailable")
    monkeypatch.setattr(monitor,"connect",unavailable)
    text=generate_latest(monitor.registry).decode()
    assert 'security_config_check_success{file_id="http-runtime",service="web-demo"} 1.0' in text
    assert 'security_config_changed{file_id="http-runtime"' not in text
    monitor.snapshot["http-runtime"]["checked_at"]=time.time()-21
    text=generate_latest(monitor.registry).decode()
    assert 'security_config_check_success{file_id="http-runtime",service="web-demo"} 0.0' in text


def test_failed_transaction_does_not_publish_approval(tmp_path,monkeypatch):
    import sqlite3
    from backend.app.integrity import IntegrityMonitor
    root=fixture_files(tmp_path);monitor=IntegrityMonitor(tmp_path/"integrity.sqlite",root)
    monitor.sample(now=100);row=monitor.overview(now=100)["files"][0]
    def fail(*args,**kwargs):raise sqlite3.OperationalError("disk full")
    monkeypatch.setattr(monitor,"record",fail)
    with pytest.raises(sqlite3.Error):monitor.approve([{"file_id":row["id"],"observed_sha256":row["observed_sha256"]}],"admin",now=101)
    assert monitor.overview(now=101)["files"][0]["approved_sha256"] is None
    restarted=IntegrityMonitor(tmp_path/"integrity.sqlite",root)
    assert restarted.overview(now=101)["files"][0]["approved_sha256"] is None


def test_unreadable_is_not_a_change_or_healthy_state(tmp_path,monkeypatch):
    from backend.app.integrity import IntegrityMonitor
    root=fixture_files(tmp_path);monitor=IntegrityMonitor(tmp_path/"integrity.sqlite",root)
    monitor.sample(now=100)
    monkeypatch.setattr("backend.app.integrity.observe_file",lambda *_:{"status":"unreadable","sha256":None,"reason":"permission_or_io"})
    monitor.sample(now=101)
    assert all(row["status"]=="unreadable" and row["observed_sha256"] is None for row in monitor.overview(now=101)["files"])
    with pytest.raises(ValueError):monitor.approve([{"file_id":"http-runtime","observed_sha256":"a"*64}],"admin",now=102)


def test_safe_reader_rejects_symbolic_files_parents_and_fifo(tmp_path):
    import os
    from backend.app.integrity_files import observe_file
    if os.name!="posix":pytest.skip("POSIX descriptor and FIFO verification runs in Docker")
    root=tmp_path/"infra";root.mkdir();outside=tmp_path/"outside";outside.mkdir();(outside/"config").write_bytes(b"secret")
    (root/"file").symlink_to(outside/"config");(root/"parent").symlink_to(outside,target_is_directory=True)
    os.mkfifo(root/"fifo")
    for path in ["file","parent/config","fifo"]:
        observed=observe_file(root,path)
        assert observed["status"]=="unreadable" and observed["sha256"] is None


def test_reader_rejects_changes_during_read_and_root_permission_failure(tmp_path,monkeypatch):
    from backend.app import integrity_files
    root=tmp_path/"infra";root.mkdir();(root/"config").write_bytes(b"original")
    calls=iter([(1,),(2,)])
    monkeypatch.setattr(integrity_files,"signature",lambda _:next(calls))
    assert integrity_files.observe_file(root,"config")["reason"]=="changed_during_read"
    def denied(_):raise PermissionError()
    monkeypatch.setattr(integrity_files,"linked",denied)
    assert integrity_files.observe_file(root,"config")["status"]=="unreadable"


def test_quiet_history_is_pruned_without_new_events(tmp_path):
    from backend.app.integrity import IntegrityMonitor
    root=fixture_files(tmp_path);monitor=IntegrityMonitor(tmp_path/"integrity.sqlite",root)
    monitor.sample(now=100);monitor.sample(now=100+8*86400)
    with monitor.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM integrity_events").fetchone()[0]==0


def test_startup_storage_failure_does_not_stop_other_monitoring_and_retries(tmp_path):
    from backend.app.integrity import IntegrityMonitor
    from prometheus_client import generate_latest
    root=fixture_files(tmp_path);path=tmp_path/"integrity.sqlite"
    path.mkdir()  # Cannot open a directory as a SQLite database.
    monitor=IntegrityMonitor(path,root)
    assert not monitor.initialized
    assert all(row["status"]=="unknown" for row in monitor.overview(include_events=False)["files"])
    assert b"security_config_check_success" in generate_latest(monitor.registry)
    path.rmdir();monitor.sample(now=100)
    assert monitor.initialized
    assert all(row["status"]=="unapproved" for row in monitor.overview(now=100)["files"])


def test_api_survives_integrity_storage_failure(tmp_path):
    from backend.tests.auth_helpers import authenticated_app,AuthenticatedClient
    from backend.app.config import Settings
    (tmp_path/"integrity.sqlite").mkdir()
    with AuthenticatedClient(authenticated_app(Settings(database_path=tmp_path/"events.sqlite",enable_probe=False))) as client:
        assert client.get("/health").status_code==200
        assert client.get("/metrics").status_code==200
        assert client.get("/api/security").status_code==200
        assert client.get("/api/security/integrity").status_code==503


def test_commit_failure_rolls_back_the_entire_approval_batch(tmp_path,monkeypatch):
    import sqlite3
    from contextlib import contextmanager
    from backend.app.integrity import IntegrityMonitor
    root=fixture_files(tmp_path);monitor=IntegrityMonitor(tmp_path/"integrity.sqlite",root)
    monitor.sample(now=100)
    items=[{"file_id":row["id"],"observed_sha256":row["observed_sha256"]} for row in monitor.overview(now=100)["files"][:2]]
    original_connect=monitor.connect
    class FailedCommit:
        def __init__(self,db):self.db=db
        def __getattr__(self,key):return getattr(self.db,key)
        def commit(self):raise sqlite3.OperationalError("commit failed")
    @contextmanager
    def connect():
        with original_connect() as db:yield FailedCommit(db)
    monkeypatch.setattr(monitor,"connect",connect)
    with pytest.raises(sqlite3.Error):monitor.approve(items,"admin",now=101)
    monkeypatch.setattr(monitor,"connect",original_connect)
    assert all(row["approved_sha256"] is None for row in monitor.overview(now=101)["files"])
    with original_connect() as db:
        assert db.execute("SELECT COUNT(*) FROM integrity_files WHERE approved_sha256 IS NOT NULL").fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM integrity_events WHERE kind='approved'").fetchone()[0]==0
