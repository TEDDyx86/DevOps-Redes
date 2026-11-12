from fastapi.testclient import TestClient

from demo.session import make_session


def demo_client():
    from demo.main import create_demo
    return create_demo("demo-secret", admin_username="admin", admin_password="monitor-pass")


def test_login_accepts_authorized_credentials():
    with TestClient(demo_client()) as client:
        data = client.post("/login", json={"username": "admin", "password": "monitor-pass"})
        assert data.status_code == 200
        assert data.json() == {"authenticated": True}
        assert "demo_session" in data.cookies


def test_login_rejects_wrong_password_and_counts():
    with TestClient(demo_client()) as client:
        assert client.post("/login", json={"username": "admin", "password": "errada"}).status_code == 401
        metrics = client.get("/metrics").text
        assert 'demo_auth_attempts_total{path="/login",result="failed"} 1.0' in metrics


def test_login_status_and_logout_flow():
    with TestClient(demo_client()) as client:
        assert client.get("/login").json() == {"authenticated": False}
        client.post("/login", json={"username": "admin", "password": "monitor-pass"})
        assert client.get("/login").json() == {"authenticated": True}
        client.post("/logout")
        assert client.get("/login").json() == {"authenticated": False}


def test_tampered_session_cookie_is_rejected():
    with TestClient(demo_client()) as client:
        client.cookies.set("demo_session", "abc.def")
        assert client.get("/login").json() == {"authenticated": False}
        client.cookies.set("demo_session", make_session("admin", "outra-chave"))
        assert client.get("/login").json() == {"authenticated": False}


def test_login_without_configured_password_returns_503():
    from demo.main import create_demo

    with TestClient(create_demo("demo-secret", admin_username="admin", admin_password="")) as client:
        assert client.post("/login", json={"username": "admin", "password": "qualquer"}).status_code == 503


def test_existing_contracts_survive_login_endpoints():
    with TestClient(demo_client()) as client:
        assert client.get("/health").status_code == 200
        assert client.post("/mode", json={"mode": "offline"}).status_code == 401
        assert client.post("/mode", headers={"X-Lab-Token": "demo-secret"}, json={"mode": "offline"}).status_code == 200
        assert client.get("/health").status_code == 503
        assert client.get("/work").status_code == 503
        assert client.get("/metrics").status_code == 200


def test_static_fallback_serves_index_html(tmp_path):
    from demo.main import create_demo

    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<html><body>WORKBYTE</body></html>", encoding="utf-8")
    with TestClient(create_demo("demo-secret", static_path=static)) as client:
        page = client.get("/rota-qualquer-da-spa")
        assert page.status_code == 200
        assert "WORKBYTE" in page.text
        # contratos de API continuam acima do fallback
        assert client.get("/health").status_code == 200
