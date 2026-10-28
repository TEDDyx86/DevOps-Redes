import asyncio
import hmac
import logging
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import Settings
from .metrics import PrometheusClient
from .probe import Probe
from .storage import IncidentStore
from .postgres_metrics import PostgresMetrics
from .postgres_probe import PostgresProbe, run_workload
from .dns_metrics import DNSMetrics
from .dns_probe import DNSProbe, run_dns_workload
from .smtp_metrics import SMTPMetrics
from .smtp_probe import SMTPProbe, run_smtp_workload


class Alert(BaseModel):
    status: Literal["firing", "resolved"]
    fingerprint: str = Field(min_length=1, max_length=128)
    startsAt: datetime
    endsAt: datetime | None = None
    labels: dict[str, str]
    annotations: dict[str, str] = Field(default_factory=dict)


class AlertBatch(BaseModel):
    alerts: list[Alert] = Field(max_length=100)


class ModeRequest(BaseModel):
    mode: Literal["normal", "slow", "offline"]


def create_app(settings: Settings | None = None, transport=None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        app.state.store = IncidentStore(settings.database_path)
        app.state.probe = Probe()
        app.state.postgres_probe = PostgresProbe()
        app.state.dns_probe = DNSProbe()
        app.state.smtp_probe = SMTPProbe()
        async with httpx.AsyncClient(timeout=5, transport=transport, trust_env=False) as client:
            app.state.client = client
            app.state.prometheus = PrometheusClient(client, settings.prometheus_url)
            task = asyncio.create_task(app.state.probe.run(client, settings.demo_url, settings.probe_interval)) if settings.enable_probe else None
            postgres_task = asyncio.create_task(app.state.postgres_probe.run(settings.postgres_monitor_dsn)) if settings.postgres_monitor_dsn else None
            workload_task = asyncio.create_task(run_workload(settings.postgres_workload_dsn)) if settings.postgres_workload_dsn else None
            dns_task = asyncio.create_task(app.state.dns_probe.run(settings.dns_server, settings.dns_port, settings.dns_name, settings.dns_expected)) if settings.dns_server else None
            dns_workload_task = asyncio.create_task(run_dns_workload(settings.dns_server, settings.dns_port)) if settings.dns_server else None
            smtp_task = asyncio.create_task(app.state.smtp_probe.run(settings.smtp_host, settings.smtp_port)) if settings.smtp_host else None
            smtp_workload_task = asyncio.create_task(run_smtp_workload(settings.smtp_host, settings.smtp_port)) if settings.smtp_host else None
            try:
                yield
            finally:
                tasks = [item for item in [task, postgres_task, workload_task, dns_task, dns_workload_task, smtp_task, smtp_workload_task] if item is not None]
                for item in tasks:
                    item.cancel()
                for item in tasks:
                    with suppress(asyncio.CancelledError):
                        await item

    app = FastAPI(title="AulaRedes API", version="0.4.0", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "api", "testserver"])

    def require_lab(request: Request, x_lab_token: str = Header(default="")):
        if not settings.lab_token or not hmac.compare_digest(x_lab_token, settings.lab_token):
            raise HTTPException(401, "Informe o token do laboratório configurado no arquivo .env.")
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            raise HTTPException(403, "Operação permitida apenas pela própria plataforma.")

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "0.4.0"}

    @app.get("/metrics")
    def metrics(request: Request):
        # Avoid exporting zero-initialized gauges before the first real probe.
        content = generate_latest(request.app.state.probe.registry) if request.app.state.probe.ready else b""
        content += generate_latest(request.app.state.postgres_probe.registry)
        content += generate_latest(request.app.state.dns_probe.registry)
        content += generate_latest(request.app.state.smtp_probe.registry)
        return Response(content=content, media_type=CONTENT_TYPE_LATEST)

    @app.get("/api/smtp")
    async def smtp_overview(request: Request, window: Literal["15m", "1h", "6h", "24h"] = "15m"):
        try:
            return await SMTPMetrics(request.app.state.prometheus).overview(window)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            logging.exception("Falha ao consultar métricas SMTP")
            raise HTTPException(503, "Prometheus indisponível. Não foi possível consultar as métricas SMTP.") from None

    @app.get("/api/dns")
    async def dns_overview(request: Request, window: Literal["15m", "1h", "6h", "24h"] = "15m"):
        try:
            return await DNSMetrics(request.app.state.prometheus, settings.dns_name, settings.dns_expected).overview(window)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            logging.exception("Falha ao consultar métricas DNS")
            raise HTTPException(503, "Prometheus indisponível. Não foi possível consultar as métricas DNS.") from None

    @app.get("/api/postgres")
    async def postgres(request: Request, window: Literal["15m", "1h", "6h", "24h"] = "15m"):
        try:
            return await PostgresMetrics(request.app.state.prometheus).overview(window)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            logging.exception("Falha ao consultar métricas PostgreSQL")
            raise HTTPException(503, "Prometheus indisponível. Não foi possível consultar as métricas do PostgreSQL.") from None

    @app.get("/api/overview")
    async def overview(request: Request, window: Literal["15m", "1h", "6h", "24h"] = "15m"):
        try:
            return await request.app.state.prometheus.overview(window)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            logging.exception("Falha ao consultar Prometheus")
            raise HTTPException(503, "Prometheus indisponível. Verifique os serviços do laboratório e tente atualizar.") from None

    @app.get("/api/incidents")
    def incidents(request: Request):
        return {"incidents": request.app.state.store.list()}

    @app.post("/api/webhooks/alerts")
    def receive_alerts(batch: AlertBatch, request: Request, authorization: str = Header(default="")):
        expected = f"Bearer {settings.webhook_token}"
        if not settings.webhook_token or not hmac.compare_digest(authorization, expected):
            raise HTTPException(401, "Credencial de webhook inválida.")
        # Keep Alertmanager's canonical timestamp strings, including its UTC suffix.
        payload = [item.model_dump(mode="json") for item in batch.alerts]
        request.app.state.store.ingest(payload)
        return {"accepted": len(payload)}

    @app.get("/api/lab")
    async def lab(request: Request):
        try:
            response = await request.app.state.client.get(f"{settings.demo_url}/mode")
            response.raise_for_status()
            return {**response.json(), "available": True, "traffic_interval_seconds": settings.probe_interval}
        except (httpx.HTTPError, ValueError):
            return {"mode": None, "available": False, "traffic_interval_seconds": settings.probe_interval}

    @app.post("/api/lab/mode", dependencies=[Depends(require_lab)])
    async def change_mode(body: ModeRequest, request: Request):
        try:
            response = await request.app.state.client.post(f"{settings.demo_url}/mode", json=body.model_dump(), headers={"X-Lab-Token": settings.lab_token})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            raise HTTPException(502, "Não foi possível alterar o serviço de demonstração.") from None

    @app.get("/api/settings")
    def public_settings():
        return {"scrape_seconds": 5, "refresh_seconds": 5, "warning_ms": 500, "warning_for_seconds": 30, "critical_for_seconds": 15,
                "email_mode": "local", "email_url": "http://localhost:8025", "retention_days": 7}

    if settings.frontend_path.exists():
        app.mount("/assets", StaticFiles(directory=settings.frontend_path / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(settings.frontend_path / "index.html")

    return app


app = create_app()
