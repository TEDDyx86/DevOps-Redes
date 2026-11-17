"""Servidor do painel de ataques: API + SSE + pÃ¡gina estÃ¡tica, apenas localhost."""
import argparse
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from demo.attacks import runners, verification
from demo.attacks.catalog import SPECS, catalog
from demo.attacks.engine import Engine

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent / "static"
HOST = "127.0.0.1"
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


def create_app(engine=None):
    if engine is None:
        engine = Engine(runners=runners.RUNNERS, verifier=build_verifier())
    app = FastAPI(title="Painel de Ataques do LaboratÃ³rio")
    app.state.engine = engine

    @app.get("/api/attacks")
    def attacks():
        return {"attacks": catalog()}

    @app.get("/api/queue")
    def queue_view():
        return engine.snapshot()

    @app.post("/api/attacks/{attack_id}/start")
    def start(attack_id: str, body: StartBody | None = None):
        if attack_id not in SPECS:
            raise HTTPException(404, "ataque_desconhecido")
        try:
            return engine.enqueue(attack_id, (body.params if body else None) or {})
        except ValueError as error:
            raise HTTPException(400, str(error))

    @app.post("/api/queue/{entry_id}/cancel")
    def cancel(entry_id: str):
        view = engine.cancel(entry_id)
        if view is None:
            raise HTTPException(404, "entrada_desconhecida")
        return view

    @app.get("/api/events")
    def events():
        return StreamingResponse(engine.subscribe(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store"})

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/panel.js")
    def js():
        return FileResponse(STATIC / "panel.js", media_type="application/javascript")

    @app.get("/panel.css")
    def css():
        return FileResponse(STATIC / "panel.css", media_type="text/css")

    return app


def main():
    parser = argparse.ArgumentParser(description="Painel de ataques do laboratÃ³rio (somente localhost)")
    parser.add_argument("--port", type=int, default=8002)
    arguments = parser.parse_args()
    uvicorn.run(create_app(), host=HOST, port=arguments.port, log_level="info")


if __name__ == "__main__":
    from scripts.scan_vulnerabilities import exclusive_lock
    with exclusive_lock(ROOT / ".runtime/attack-panel.lock"):
        main()
