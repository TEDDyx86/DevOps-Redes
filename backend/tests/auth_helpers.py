"""Explicit test-only authenticated clients; production always requires a session."""
from dataclasses import replace
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.passwords import hash_password

PASSWORD = "fixture-password"
PASSWORD_HASH = hash_password(PASSWORD)


def authenticated_app(settings, transport=None):
    return create_app(replace(settings, auth_password_hash=PASSWORD_HASH, frontend_path=settings.database_path.parent / "unused-frontend"), transport)


class AuthenticatedClient(TestClient):
    def __enter__(self):
        super().__enter__()
        response = self.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
        assert response.status_code == 200
        self.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        return self
