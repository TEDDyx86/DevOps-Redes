import asyncio
import hashlib
import hmac
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field
from .config import load_http_config
from .session import SESSION_COOKIE, SESSION_TTL_SECONDS, make_session, read_session
from .store import (
    ProductNotFoundError,
    StockConflictError,
    StoreBackend,
    StoreUnavailableError,
)


class Mode(BaseModel):
    mode: Literal["normal", "slow", "offline"]


class LoginRequest(BaseModel):
    username: str
    password: str


class OrderItemRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=64)
    quantity: int = Field(ge=1, le=20)


class CreateOrderRequest(BaseModel):
    customer_name: str = Field(min_length=2, max_length=120)
    customer_email: str = Field(min_length=3, max_length=160, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    items: list[OrderItemRequest] = Field(min_length=1, max_length=20)


def _metric_path(path: str) -> str | None:
    if path in ("/work", "/health", "/api/products", "/api/orders", "/api/store/status"):
        return path
    if path.startswith("/api/products/"):
        return "/api/products/{slug}"
    return None


def create_demo(token=None, runtime_config=None, admin_username=None, admin_password=None, static_path=None, store=None):
    store_backend = store if store is not None else StoreBackend()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield

    app = FastAPI(title="Workbyte Store · E-commerce de demonstração", lifespan=lifespan)
    app.state.mode = "normal"
    app.state.store = store_backend
    config=runtime_config or load_http_config()
    token = token if token is not None else os.getenv("LAB_TOKEN", "")
    username = admin_username if admin_username is not None else os.getenv("ADMIN_USERNAME", "admin")
    password = admin_password if admin_password is not None else os.getenv("ADMIN_PASSWORD", "")
    static_dir = static_path if static_path is not None else Path(__file__).resolve().parent / "static"
    registry = CollectorRegistry()
    app.state.registry = registry
    requests = Counter("demo_http_requests_total", "Completed HTTP requests", ["path", "status"], registry=registry)
    inflight = Gauge("demo_http_requests_inflight", "HTTP requests currently being served", registry=registry)
    duration = Histogram("demo_http_duration_seconds", "HTTP duration", ["path"], buckets=[.01, .025, .05, .1, .25, .5, 1, 2, 5], registry=registry)
    auth = Counter("demo_auth_attempts_total", "Service authentication attempts", ["path", "result"], registry=registry)

    @app.middleware("http")
    async def instrument(request: Request, call_next):
        inflight.inc()
        try:
            metric_path = _metric_path(request.url.path)
            if metric_path is None:
                return await call_next(request)
            started = time.perf_counter()
            if app.state.mode == "slow":
                await asyncio.sleep(config.slow_delay_seconds)
            response = JSONResponse({"detail": "Indisponibilidade controlada do laboratório"}, status_code=503) if app.state.mode == "offline" else await call_next(request)
            requests.labels(metric_path, str(response.status_code)).inc()
            duration.labels(metric_path).observe(time.perf_counter() - started)
            return response
        finally:
            inflight.dec()

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

    @app.get("/api/store/status")
    async def store_status():
        deps = await store_backend.status()
        return {"http": "ok", **deps}

    @app.get("/api/products")
    async def list_products(category: str | None = None, q: str | None = None):
        try:
            return {"products": await store_backend.list_products(category=category, query=q)}
        except StoreUnavailableError as error:
            raise HTTPException(503, str(error)) from None

    @app.get("/api/products/{slug}")
    async def get_product(slug: str):
        try:
            return await store_backend.get_product(slug)
        except ProductNotFoundError:
            raise HTTPException(404, "Produto não encontrado.") from None
        except StoreUnavailableError as error:
            raise HTTPException(503, str(error)) from None

    @app.get("/api/orders")
    async def list_orders():
        try:
            return {"orders": await store_backend.list_orders()}
        except StoreUnavailableError as error:
            raise HTTPException(503, str(error)) from None

    @app.post("/api/orders", status_code=201)
    async def create_order(body: CreateOrderRequest):
        try:
            return await store_backend.create_order(
                body.customer_name.strip(),
                body.customer_email.strip(),
                [item.model_dump() for item in body.items],
            )
        except ProductNotFoundError:
            raise HTTPException(404, "Produto informado não existe no catálogo.") from None
        except StockConflictError as error:
            raise HTTPException(409, str(error)) from None
        except StoreUnavailableError as error:
            raise HTTPException(503, str(error)) from None

    if static_dir.exists() and (static_dir / "assets").exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="demo-assets")

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str):
            return FileResponse(static_dir / "index.html")

    return app


app = create_demo()
