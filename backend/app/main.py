import asyncio
import hmac
import logging
import sqlite3
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import Settings
from .metrics import PrometheusClient
from .probe import Probe
from .storage import IncidentStore, resolution_window
from .postgres_metrics import PostgresMetrics
from .postgres_probe import PostgresProbe, run_workload
from .dns_metrics import DNSMetrics
from .dns_probe import DNSProbe, run_dns_workload
from .smtp_metrics import SMTPMetrics
from .smtp_probe import SMTPProbe, run_smtp_workload
from .auth_store import AuthStore
from .auth import install_auth
from .traffic import TrafficMonitor
from .traffic_load import TrafficLoad
from .integrity import IntegrityMonitor
from .vulnerabilities import VulnerabilityMonitor


class Alert(BaseModel):
    status: Literal["firing", "resolved"]
    fingerprint: str = Field(min_length=1, max_length=128)
    startsAt: datetime
    endsAt: datetime | None = None
    labels: dict[str, str]
    annotations: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_resolution(self):
        if self.status == "resolved" and resolution_window(
                self.startsAt.isoformat(), self.endsAt.isoformat() if self.endsAt is not None else None) is None:
            raise ValueError("Resolução exige início/término com fuso, em ordem e sem término futuro.")
        return self


class AlertBatch(BaseModel):
    alerts: list[Alert] = Field(max_length=100)


class ModeRequest(BaseModel):
    mode: Literal["normal", "slow", "offline"]


class TrafficRequest(BaseModel):
    service: Literal["web-demo","postgres","dns","smtp","all"]
    duration: int = Field(default=90,ge=30,le=90,strict=True)


class CalibrationRequest(BaseModel):
    service: Literal["web-demo","postgres","dns","smtp"]


class IntegrityApprovalItem(BaseModel):
    file_id: str = Field(min_length=1,max_length=64)
    observed_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class IntegrityApprovalRequest(BaseModel):
    items: list[IntegrityApprovalItem] = Field(min_length=1,max_length=8)


def create_app(settings: Settings | None = None, transport=None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        app.state.store = IncidentStore(settings.database_path)
        app.state.auth = AuthStore(settings.database_path.with_name("security.sqlite"), settings.auth_username, settings.auth_password_hash)
        app.state.traffic = TrafficMonitor(settings.database_path.with_name("traffic.sqlite"))
        app.state.traffic_load = TrafficLoad(settings)
        app.state.traffic_control_lock = asyncio.Lock()
        app.state.integrity = IntegrityMonitor(settings.database_path.with_name("integrity.sqlite"),settings.integrity_root)
        app.state.vulnerabilities = VulnerabilityMonitor(settings.vulnerability_root)
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
            traffic_task = asyncio.create_task(app.state.traffic.run(app.state.prometheus)) if settings.enable_probe else None
            integrity_task = asyncio.create_task(app.state.integrity.run()) if settings.integrity_root is not None else None
            vulnerability_task = asyncio.create_task(app.state.vulnerabilities.run()) if settings.vulnerability_root is not None else None
            try:
                yield
            finally:
                await app.state.traffic_load.stop()
                tasks = [item for item in [task, postgres_task, workload_task, dns_task, dns_workload_task, smtp_task, smtp_workload_task, traffic_task, integrity_task, vulnerability_task] if item is not None]
                for item in tasks:
                    item.cancel()
                for item in tasks:
                    with suppress(asyncio.CancelledError):
                        await item

    app = FastAPI(title="AulaRedes API", version="0.8.0", lifespan=lifespan)
    install_auth(app, settings)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "api", "testserver"])

    def require_lab(request: Request, x_lab_token: str = Header(default="")):
        if not settings.lab_token or not hmac.compare_digest(x_lab_token, settings.lab_token):
            raise HTTPException(401, "Informe o token do laboratório configurado no arquivo .env.")
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            raise HTTPException(403, "Operação permitida apenas pela própria plataforma.")

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "0.8.0"}

    @app.get("/api/security/vulnerabilities")
    def vulnerabilities(request: Request, service: Literal["web-demo","postgres","dns","smtp"]="web-demo",
                        severity: Literal["all","critical","high","medium","low","negligible","unknown"]="all",
                        page: int=Query(default=1,ge=1,le=200)):
        return request.app.state.vulnerabilities.overview(service,severity,page)

    @app.get("/api/security/integrity")
    def integrity_overview(request: Request):
        try:
            return request.app.state.integrity.overview()
        except (sqlite3.Error,OSError):
            raise HTTPException(503,"Histórico de integridade indisponível.") from None

    @app.post("/api/security/integrity/approve",dependencies=[Depends(require_lab)])
    async def approve_integrity(body: IntegrityApprovalRequest,request: Request):
        try:
            await asyncio.to_thread(request.app.state.integrity.approve,[item.model_dump() for item in body.items],request.state.session["username"])
            return request.app.state.integrity.overview()
        except ValueError as error:
            raise HTTPException(409,str(error)) from None
        except (sqlite3.Error,OSError):
            raise HTTPException(503,"Não foi possível persistir a referência de integridade.") from None

    @app.get("/api/security/traffic")
    def traffic_overview(request: Request):
        return request.app.state.traffic.overview()

    @app.post("/api/security/traffic/calibrate",dependencies=[Depends(require_lab)])
    async def calibrate_traffic(body: CalibrationRequest, request: Request):
        async with request.app.state.traffic_control_lock:
            if request.app.state.traffic_load.overview()["status"] == "running":
                raise HTTPException(409,"Encerre o teste de tráfego antes de recalibrar.")
            try:
                await asyncio.to_thread(request.app.state.traffic.recalibrate,body.service)
            except ValueError as error:
                raise HTTPException(409,str(error)) from None
        return request.app.state.traffic.overview()

    @app.get("/api/lab/traffic")
    def traffic_job(request: Request):
        return request.app.state.traffic_load.overview()

    @app.post("/api/lab/traffic",dependencies=[Depends(require_lab)])
    async def start_traffic(body: TrafficRequest,request: Request):
        async with request.app.state.traffic_control_lock:
            selected = [item for item in request.app.state.traffic.overview()["services"] if body.service=="all" or item["id"]==body.service]
            if any(item["status"]!="normal" for item in selected):
                raise HTTPException(409,"Aguarde referências prontas, dados atuais e volume normal antes de iniciar o teste.")
            try:
                return request.app.state.traffic_load.start(body.service,body.duration)
            except ValueError as error:
                raise HTTPException(409,str(error)) from None

    @app.delete("/api/lab/traffic",dependencies=[Depends(require_lab)])
    async def stop_traffic(request: Request):
        async with request.app.state.traffic_control_lock:
            return await request.app.state.traffic_load.stop()

    @app.get("/metrics")
    def metrics(request: Request):
        # Avoid exporting zero-initialized gauges before the first real probe.
        content = generate_latest(request.app.state.probe.registry) if request.app.state.probe.ready else b""
        content += generate_latest(request.app.state.postgres_probe.registry)
        content += generate_latest(request.app.state.dns_probe.registry)
        content += generate_latest(request.app.state.smtp_probe.registry)
        content += generate_latest(request.app.state.auth.registry)
        content += generate_latest(request.app.state.traffic.registry)
        content += generate_latest(request.app.state.integrity.registry)
        content += generate_latest(request.app.state.vulnerabilities.registry)
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
