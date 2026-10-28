from fastapi.testclient import TestClient
from backend.app.config import Settings
from backend.app.main import create_app


def configured(tmp_path):
    from backend.app.passwords import hash_password
    return Settings(database_path=tmp_path / "incidents.sqlite", enable_probe=False,
                    frontend_path=tmp_path / "unused-frontend", auth_password_hash=hash_password("test-password-123"))


def test_protected_data_and_monitoring_exceptions(tmp_path):
    with TestClient(create_app(configured(tmp_path))) as client:
        for path in ["/api/incidents", "/api/overview", "/api/postgres", "/api/dns", "/api/smtp", "/api/lab", "/api/settings", "/api/security", "/docs", "/openapi.json"]:
            assert client.get(path).status_code == 401
        assert client.get("/health").status_code == 200
        assert client.get("/metrics").status_code == 200
        assert client.post("/api/webhooks/alerts", json={"alerts": []}).status_code == 401


def test_login_cookie_csrf_logout_and_no_secrets(tmp_path):
    with TestClient(create_app(configured(tmp_path))) as client:
        assert client.post("/api/auth/login", json={"username": "admin", "password": "wrong"}).status_code == 401
        response = client.post("/api/auth/login", json={"username": "admin", "password": "test-password-123"})
        assert response.status_code == 200
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie and "SameSite=strict" in cookie
        csrf = response.json()["csrf_token"]
        assert client.get("/api/incidents").status_code == 200
        assert client.get("/api/auth/session").json()["csrf_token"] == csrf
        assert client.post("/api/auth/logout").status_code == 403
        assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf, "Origin": "http://evil.test"}).status_code == 403
        events = client.get("/api/security").json()["events"]
        assert {e["outcome"] for e in events} == {"success", "failure"}
        assert "test-password" not in str(events)
        assert csrf not in str(events)
        assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
        assert client.get("/api/incidents").status_code == 401


def test_store_rate_limit_recovers_and_sessions_expire(tmp_path):
    from backend.app.auth_store import AuthStore
    settings = configured(tmp_path)
    store = AuthStore(tmp_path / "auth.sqlite", "admin", settings.auth_password_hash)
    for i in range(5):
        assert store.login("admin", "wrong", "127.0.0.1", now=100+i)["status"] == 401
    assert store.login("admin", "test-password-123", "127.0.0.1", now=106)["status"] == 429
    result = store.login("admin", "test-password-123", "127.0.0.1", now=165)
    assert result["status"] == 200
    token = result["token"]
    assert store.session(token, now=166)["username"] == "admin"
    restarted = AuthStore(tmp_path / "auth.sqlite", "admin", settings.auth_password_hash)
    assert restarted.session(token, now=167) is not None
    assert restarted.session(token, now=165+28801) is None
    assert store.session("unknown", now=166) is None


def test_account_limit_applies_across_ips_and_ignores_proxy_headers(tmp_path):
    from backend.app.auth_store import AuthStore
    settings = configured(tmp_path)
    store = AuthStore(tmp_path / "auth.sqlite", "admin", settings.auth_password_hash)
    for i in range(10):
        assert store.login("admin", "wrong", f"192.0.2.{i}", now=100)["status"] == 401
    assert store.login("admin", "test-password-123", "192.0.2.99", now=101)["status"] == 429
    with TestClient(create_app(settings)) as client:
        for i in range(5):
            assert client.post("/api/auth/login", headers={"X-Forwarded-For": f"192.0.2.{i}"}, json={"username": "admin", "password": "wrong"}).status_code == 401
        assert client.post("/api/auth/login", json={"username": "other", "password": "wrong"}).status_code == 429


def test_missing_configuration_is_closed_and_rotation_revokes(tmp_path):
    from backend.app.auth_store import AuthStore
    from backend.app.passwords import hash_password
    with TestClient(create_app(Settings(database_path=tmp_path / "incidents.sqlite", enable_probe=False, frontend_path=tmp_path / "unused-frontend"))) as client:
        assert client.post("/api/auth/login", json={"username": "admin", "password": "anything"}).status_code == 503
        assert client.get("/api/incidents").status_code == 401
    path = tmp_path / "rotation.sqlite"
    password_hash = hash_password("test-password-123")
    store = AuthStore(path, "admin", password_hash)
    result = store.login("admin", "test-password-123", "127.0.0.1")
    assert AuthStore(path, "admin", hash_password("new-password-123")).session(result["token"]) is None


def test_parallel_attempts_reserve_rate_budget_and_hide_identities(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from prometheus_client import generate_latest
    from backend.app.auth_store import AuthStore
    settings = configured(tmp_path)
    store = AuthStore(tmp_path / "parallel.sqlite", "admin", settings.auth_password_hash)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: store.login("admin", "wrong", "192.0.2.25", now=100), range(6)))
    assert sorted(result["status"] for result in results) == [401]*5+[429]
    metrics = generate_latest(store.registry).decode()
    assert 'security_auth_attempts_total{outcome="failure"} 5.0' in metrics
    assert "192.0.2.25" not in metrics and "admin" not in metrics
    assert settings.auth_password_hash not in metrics
    assert store.stats(now=161)["failures_recent"]["ip"] == 0


def test_bootstrap_preserves_credentials_and_hash(tmp_path, capsys):
    from scripts.configure import configure
    from backend.app.passwords import verify_password
    configure(tmp_path)
    env = (tmp_path / ".env").read_text()
    secret = (tmp_path / ".runtime/secrets/admin-password-hash").read_text()
    configure(tmp_path)
    assert (tmp_path / ".env").read_text() == env
    assert (tmp_path / ".runtime/secrets/admin-password-hash").read_text() == secret
    password = dict(line.split("=", 1) for line in env.splitlines() if "=" in line)["ADMIN_PASSWORD"]
    assert verify_password(password, secret)
    assert password not in capsys.readouterr().out


def test_event_cap_keeps_limiter_and_persistent_totals(tmp_path):
    from backend.app.auth_store import AuthStore
    settings = configured(tmp_path)
    store = AuthStore(tmp_path / "cap.sqlite", "admin", settings.auth_password_hash)
    for i in range(5):
        assert store.login("admin", "wrong", "192.0.2.1", now=100)["status"] == 401
    with store.connect() as db:
        db.executemany("INSERT INTO auth_events(at,username,ip,outcome) VALUES (100,'other','192.0.2.1','blocked')", [()]*10001)
    assert store.login("another", "wrong", "192.0.2.1", now=101)["status"] == 429
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM auth_events").fetchone()[0] <= 10000
    assert store.stats(now=101)["failures_recent"]["ip"] == 5
    assert store.stats(now=101)["totals"]["failure"] == 5
