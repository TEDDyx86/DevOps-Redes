"""Rotas do painel de ataques integradas à autenticação do painel de monitoramento."""
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.app.attacks import runners, verification
from backend.app.attacks.catalog import SPECS, catalog
from backend.app.attacks.engine import Engine

VERIFY_ATTEMPTS = 6
VERIFY_INTERVAL = 5


def build_verifier():
    def verify(expected, cancelled=lambda: False):
        if not expected:
            return {"available": True, "fired": [], "missing": []}
        ultimo = verification.verify(expected, None)
        for attempt in range(VERIFY_ATTEMPTS):
            try:
                with runners.make_client() as client:
                    firing = verification.firing_alerts(client, runners.PROMETHEUS_BASE)
                ultimo = verification.verify(expected, firing)
            except Exception:
                ultimo = verification.verify(expected, None)
            if not ultimo["missing"] or cancelled():
                return ultimo
            if attempt < VERIFY_ATTEMPTS - 1:
                time.sleep(VERIFY_INTERVAL)
        return ultimo

    return verify


class StartBody(BaseModel):
    params: dict | None = None


def build_engine():
    return Engine(runners=runners.RUNNERS, verifier=build_verifier())


def register(app, engine=None):
    if engine is None:
        engine = build_engine()
    app.state.attack_engine = engine

    router = APIRouter(prefix="/api")

    @router.get("/attacks")
    def attacks():
        return {"attacks": catalog()}

    @router.get("/queue")
    def queue_view():
        return engine.snapshot()

    @router.post("/attacks/{attack_id}/start")
    def start(attack_id: str, body: StartBody | None = None):
        if attack_id not in SPECS:
            raise HTTPException(404, "ataque_desconhecido")
        try:
            return engine.enqueue(attack_id, (body.params if body else None) or {})
        except ValueError as error:
            raise HTTPException(400, str(error))

    @router.post("/queue/{entry_id}/cancel")
    def cancel(entry_id: str):
        view = engine.cancel(entry_id)
        if view is None:
            raise HTTPException(404, "entrada_desconhecida")
        return view

    @router.get("/events")
    def events():
        return StreamingResponse(
            engine.subscribe(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store"},
        )

    app.include_router(router)
    return engine
