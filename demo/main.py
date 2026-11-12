import asyncio
import hashlib
import hmac
import os
import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest
from pydantic import BaseModel
from .config import load_http_config
from .session import SESSION_COOKIE, SESSION_TTL_SECONDS, make_session, read_session


class Mode(BaseModel):
    mode: Literal["normal", "slow", "offline"]


class LoginRequest(BaseModel):
    username: str
    password: str


def create_demo(token=None,runtime_config=None, admin_username=None, admin_password=None, static_path=None):
    app = FastAPI(title="HTTP de demonstração")
    app.state.mode = "normal"
    config=runtime_config or load_http_config()
    token = token if token is not None else os.getenv("LAB_TOKEN", "")
    username = admin_username if admin_username is not None else os.getenv("ADMIN_USERNAME", "admin")
    password = admin_password if admin_password is not None else os.getenv("ADMIN_PASSWORD", "")
    static_dir = static_path if static_path is not None else Path(__file__).resolve().parent / "static"
    registry = CollectorRegistry()
    requests = Counter("demo_http_requests_total", "Completed HTTP requests", ["path", "status"], registry=registry)
    duration = Histogram("demo_http_duration_seconds", "HTTP duration", ["path"], buckets=[.01, .025, .05, .1, .25, .5, 1, 2, 5], registry=registry)
    auth = Counter("demo_auth_attempts_total", "Service authentication attempts", ["path", "result"], registry=registry)

    @app.middleware("http")
    async def instrument(request: Request, call_next):
        if request.url.path not in ("/work", "/health"):
            return await call_next(request)
        started = time.perf_counter()
        if app.state.mode == "slow":
            await asyncio.sleep(config.slow_delay_seconds)
        response = JSONResponse({"detail": "Indisponibilidade controlada do laboratório"}, status_code=503) if app.state.mode == "offline" else await call_next(request)
        requests.labels(request.url.path, str(response.status_code)).inc()
        duration.labels(request.url.path).observe(time.perf_counter() - started)
        return response

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/work")
    async def work():
        await asyncio.sleep(config.work_delay_seconds)
        return {"message": config.message, "timestamp": time.time()}

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

    @app.get("/mode")
    def mode():
        return {"mode": app.state.mode}

    @app.post("/mode")
    def set_mode(body: Mode, x_lab_token: str = Header(default="")):
        if not token or not hmac.compare_digest(token, x_lab_token):
            auth.labels("/mode", "failed").inc()
            raise HTTPException(401, "Token inválido")
        auth.labels("/mode", "accepted").inc()
        app.state.mode = body.mode
        return {"mode": app.state.mode}

    @app.post("/login")
    def login(body: LoginRequest, response: Response):
        if not password:
            raise HTTPException(503, "Login indisponível no serviço de demonstração")
        user_ok = hmac.compare_digest(body.username.encode(), username.encode())
        pass_ok = hmac.compare_digest(hashlib.sha256(body.password.encode()).hexdigest(), hashlib.sha256(password.encode()).hexdigest())
        if not (user_ok and pass_ok):
            auth.labels("/login", "failed").inc()
            raise HTTPException(401, "Credenciais inválidas")
        auth.labels("/login", "accepted").inc()
        response.set_cookie(SESSION_COOKIE, make_session(body.username, token), max_age=SESSION_TTL_SECONDS, httponly=True, samesite="lax")
        return {"authenticated": True}

    @app.get("/login")
    def login_status(request: Request):
        session = read_session(request.cookies.get(SESSION_COOKIE, ""), token)
        return {"authenticated": session is not None}

    @app.post("/logout")
    def logout(response: Response):
        response.delete_cookie(SESSION_COOKIE, path="/")
        return {"authenticated": False}

    if static_dir.exists() and (static_dir / "assets").exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="demo-assets")

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str):
            return FileResponse(static_dir / "index.html")

    return app


app = create_demo()
