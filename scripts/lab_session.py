"""Authenticate local verification scripts without printing or persisting tokens."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def credentials():
    values = dict(line.split("=", 1) for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines() if "=" in line and not line.lstrip().startswith("#"))
    return {"username": values.get("ADMIN_USERNAME", "admin"), "password": values["ADMIN_PASSWORD"]}


def authenticate(client):
    response = client.post("http://localhost:8000/api/auth/login", json=credentials())
    response.raise_for_status()
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response.json()
