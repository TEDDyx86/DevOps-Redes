"""Runners dos ataques: efeitos controlados a partir do host, sempre reversíveis."""
import os
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from scripts.attack_panel.engine import Cancelled
from scripts.attack_panel import verification
from scripts.lab_session import authenticate

ROOT = Path(__file__).resolve().parents[2]
DEMO_BASE = "http://localhost:8001"
PANEL_BASE = "http://localhost:8000"
PROMETHEUS_BASE = "http://localhost:9090"

BURST_INTERVAL = 0.15
BRUTEFORCE_HOLD = 40
SOBRECARGA_HOLD = 35


def make_client():
    return httpx.Client(timeout=5, trust_env=False)


def lab_token():
    values = dict(line.split("=", 1) for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
                  if "=" in line and not line.lstrip().startswith("#"))
    token = values.get("LAB_TOKEN", "")
    if not token:
        raise RuntimeError("LAB_TOKEN ausente no .env")
    return token


def _hold(ctx, seconds):
    deadline = time.monotonic() + seconds
    while True:
        ctx.check_cancelled()
        restante = max(0, int(deadline - time.monotonic()))
        ctx.progress(segundos_restantes=restante)
        if restante <= 0:
            return
        time.sleep(1)


def _firing(client):
    try:
        return verification.firing_alerts(client, PROMETHEUS_BASE)
    except Exception:
        return set()


def bruteforce_servico(ctx, params):
    tentativas = int(params["tentativas"])
    ctx.set_expected_alerts(["AutenticacaoServicoSuspeita"])
    feitas = rejeitadas = 0
    with make_client() as client:
        for index in range(tentativas):
            ctx.check_cancelled()
            started = time.perf_counter()
            try:
                response = client.post(DEMO_BASE + "/mode", json={"mode": "normal"},
                                       headers={"X-Lab-Token": "ataque-" + uuid.uuid4().hex[:12]})
                codigo = response.status_code
            except httpx.HTTPError:
                codigo = None
            feitas += 1
            rejeitadas += 1 if codigo == 401 else 0
            ctx.progress(tentativas=feitas, rejeitadas=rejeitadas)
            if index % 4 == 0:
                ctx.log(f"Tentativa {index + 1}/{tentativas}: " + (f"HTTP {codigo}" if codigo else "sem resposta"))
            espera = BURST_INTERVAL - (time.perf_counter() - started)
            if espera > 0:
                time.sleep(espera)
    ctx.log("Maré de tentativas concluída; aguardando janela de 1 minuto e o 'for: 30s' do alerta")
    _hold(ctx, BRUTEFORCE_HOLD)


def bruteforce_painel(ctx, params):
    tentativas = int(params["tentativas"])
    ctx.set_expected_alerts(["AutenticacaoSuspeita"])
    feitas = 0
    with make_client() as client:
        for index in range(tentativas):
            ctx.check_cancelled()
            started = time.perf_counter()
            try:
                response = client.post(PANEL_BASE + "/api/auth/login",
                                       json={"username": "admin", "password": "senha-errada-" + uuid.uuid4().hex[:12]})
                codigo = response.status_code
            except httpx.HTTPError:
                codigo = None
            feitas += 1
            ctx.progress(tentativas=feitas, rejeitadas=feitas if codigo == 401 else 0)
            if index % 4 == 0:
                ctx.log(f"Login {index + 1}/{tentativas}: " + (f"HTTP {codigo}" if codigo else "sem resposta"))
            espera = BURST_INTERVAL - (time.perf_counter() - started)
            if espera > 0:
                time.sleep(espera)
    ctx.log("Logins com senha errada concluídos; aguardando janela de falhas recentes e o 'for: 10s' do alerta")
    _hold(ctx, BRUTEFORCE_HOLD)


def sobrecarga_http(ctx, params):
    taxa = int(params["taxa"])
    duracao = int(params["duracao"])
    ctx.set_expected_alerts(["RecursoCPUElevada", "TrafegoAnormal"])
    workers = max(2, min(8, taxa // 5))
    stop = time.monotonic() + duracao
    shared = {"requisicoes": 0, "erros": 0}
    guard = threading.Lock()

    def worker(client):
        local = 0
        while time.monotonic() < stop:
            if ctx.cancelled():
                return
            try:
                response = client.get(DEMO_BASE + "/work")
                aceito = response.status_code < 500
            except httpx.HTTPError:
                aceito = False
            with guard:
                shared["requisicoes"] += 1
                if not aceito:
                    shared["erros"] += 1
                snapshot = dict(shared)
            ctx.progress(**snapshot)
            local += 1
            if local % 50 == 0:
                ctx.log(f"Maré em andamento: {snapshot['requisicoes']} requisições")

    clientes = [make_client() for _ in range(workers)]
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for future in [pool.submit(worker, client) for client in clientes]:
                future.result()
    finally:
        for client in clientes:
            client.close()
    if ctx.cancelled():
        raise Cancelled()
    ctx.log(f"Maré concluída: {shared['requisicoes']} requisições; aguardando 'for: 30s' dos alertas")
    _hold(ctx, SOBRECARGA_HOLD)


def indisponibilidade_http(ctx, params):
    duracao = int(params["duracao"])
    ctx.set_expected_alerts(["HTTPIndisponivel"])
    token = lab_token()
    with make_client() as client:
        response = client.post(DEMO_BASE + "/mode", json={"mode": "offline"}, headers={"X-Lab-Token": token})
        response.raise_for_status()
        ctx.log("Web-demo em modo offline; sondas HTTP do painel devem falhar")
        try:
            _hold(ctx, duracao)
        finally:
            restore = client.post(DEMO_BASE + "/mode", json={"mode": "normal"}, headers={"X-Lab-Token": token})
            if restore.status_code == 200:
                ctx.log("Modo normal restaurado")
            else:
                ctx.log(f"ATENÇÃO: restauração do modo falhou com HTTP {restore.status_code}; restaurar manualmente")
