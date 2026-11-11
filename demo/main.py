import asyncio
import hmac
import os
import time
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest
from pydantic import BaseModel
from .config import load_http_config


class Mode(BaseModel):
    mode: Literal["normal", "slow", "offline"]


def create_demo(token=None,runtime_config=None):
    app = FastAPI(title="HTTP de demonstração")
    app.state.mode = "normal"
    config=runtime_config or load_http_config()
    token = token if token is not None else os.getenv("LAB_TOKEN", "")
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

    return app


app = create_demo()
