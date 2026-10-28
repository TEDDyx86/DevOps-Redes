"""Exercise Uvicorn itself: TestClient cannot test proxy-header handling."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
from backend.app.passwords import hash_password


def test_native_server_ignores_forwarded_identity(tmp_path):
    secret = tmp_path / "password-hash"
    secret.write_text(hash_password("runtime-test-password"), encoding="utf-8")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    environment = {**os.environ, "DATABASE_PATH":str(tmp_path / "incidents.sqlite"),
                   "AUTH_PASSWORD_HASH_FILE":str(secret), "ADMIN_USERNAME":"admin",
                   "ENABLE_PROBE":"false", "FRONTEND_PATH":str(tmp_path / "unused-frontend"),
                   "POSTGRES_MONITOR_DSN":"", "POSTGRES_WORKLOAD_DSN":"", "DNS_SERVER":"", "SMTP_HOST":""}
    process = subprocess.Popen([sys.executable,"-m","uvicorn","backend.app.main:app","--host","127.0.0.1","--port",str(port),"--no-proxy-headers"],
                               cwd=Path(__file__).resolve().parents[2], env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}",timeout=3,trust_env=False) as client:
            deadline = time.monotonic()+10
            while True:
                try:
                    if client.get("/health").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                assert time.monotonic() < deadline and process.poll() is None
                time.sleep(.05)
            for index in range(5):
                assert client.post("/api/auth/login",headers={"X-Forwarded-For":f"192.0.2.{index}"},json={"username":f"unknown{index}","password":"wrong"}).status_code == 401
            assert client.post("/api/auth/login",headers={"X-Forwarded-For":"192.0.2.99"},json={"username":"another","password":"wrong"}).status_code == 429
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
