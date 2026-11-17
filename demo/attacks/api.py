"""Rotas do painel de ataques do web-demo, acopladas à sessão da demo."""
import time

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from demo.attacks import runners, verification
from demo.attacks.catalog import SPECS, catalog
from demo.attacks.engine import Engine
from demo.session import SESSION_COOKIE, read_session

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
            if ultimo["fired"] or cancelled():
                return ultimo
            if attempt < VERIFY_ATTEMPTS - 1:
                time.sleep(VERIFY_INTERVAL)
        return ultimo
    return verify


class StartBody(BaseModel):
    params: dict | None = None


def build_engine():
    return Engine(runners=runners.RUNNERS, verifier=build_verifier())


def register(app, token, engine=None):
    if engine is None:
        engine = build_engine()
    app.state.attack_engine = engine

    def usuario(request: Request):
        session = read_session(request.cookies.get(SESSION_COOKIE, ""), token)
        if session is None:
            raise HTTPException(401, "Sessão obrigatória")
        return session

    @app.get("/api/attacks")
    def attacks(request: Request):
        usuario(request)
        return {"attacks": catalog()}

    @app.get("/api/queue")
    def queue_view(request: Request):
        usuario(request)
        return engine.snapshot()

    @app.post("/api/attacks/{attack_id}/start")
    def start(attack_id: str, request: Request, body: StartBody | None = None):
        usuario(request)
        if attack_id not in SPECS:
            raise HTTPException(404, "ataque_desconhecido")
        try:
            return engine.enqueue(attack_id, (body.params if body else None) or {})
        except ValueError as error:
            raise HTTPException(400, str(error))

    @app.post("/api/queue/{entry_id}/cancel")
    def cancel(entry_id: str, request: Request):
        usuario(request)
        view = engine.cancel(entry_id)
        if view is None:
            raise HTTPException(404, "entrada_desconhecida")
        return view

    @app.get("/api/events")
    def events(request: Request):
        usuario(request)
        return StreamingResponse(engine.subscribe(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store"})

    return engine
