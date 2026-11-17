"""Runners dos ataques: efeitos controlados de dentro do container, sempre reversíveis."""
import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from demo.attacks.engine import Cancelled
from demo.attacks import verification

DEMO_BASE = os.environ.get("DEMO_BASE", "http://web-demo:8001")
PANEL_BASE = os.environ.get("PANEL_BASE", "http://api:8000")
PROMETHEUS_BASE = os.environ.get("PROMETHEUS_BASE", "http://prometheus:9090")
INFRA_ROOT = Path(os.environ.get("INFRA_ROOT", "/etc/aularedes/runtime"))
DOCKER_SOCKET = os.environ.get("DOCKER_SOCKET", "/var/run/docker.sock")

BURST_INTERVAL = 0.15
BRUTEFORCE_HOLD = 40
SOBRECARGA_HOLD = 35
STOP_GRACE_SECONDS = 15


def make_client():
    return httpx.Client(timeout=5, trust_env=False)


def docker_client():
    return httpx.Client(transport=httpx.HTTPTransport(uds=DOCKER_SOCKET),
                        base_url="http://docker", timeout=30, trust_env=False)


def lab_token():
    token = os.environ.get("LAB_TOKEN", "")
    if not token:
        raise RuntimeError("LAB_TOKEN ausente no ambiente do container")
    return token


def panel_session(client):
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not password:
        raise RuntimeError("ADMIN_PASSWORD ausente no ambiente do container")
    response = client.post(PANEL_BASE + "/api/auth/login",
                           json={"username": username, "password": password})
    response.raise_for_status()
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response.json()


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


STOP_ALERTS = {"dns": "DNSIndisponivel", "smtp": "SMTPIndisponivel",
               "web-demo": "HTTPIndisponivel", "postgres": "PostgreSQLIndisponivel"}


def _container_id(client, alvo):
    filtros = json.dumps({"label": [f"com.docker.compose.service={alvo}"]})
    response = client.get("/containers/json", params={"filters": filtros, "all": "true"})
    response.raise_for_status()
    containers = response.json()
    if not containers:
        raise ValueError("container_nao_encontrado")
    return containers[0]["Id"]


def _docker_control(client, container_id, acao):
    if acao == "stop":
        response = client.post(f"/containers/{container_id}/stop", params={"t": str(STOP_GRACE_SECONDS)})
    else:
        response = client.post(f"/containers/{container_id}/start")
    response.raise_for_status()


def _traffic_attack(ctx, service, duracao, expected):
    ctx.set_expected_alerts(expected)
    duracao = int(duracao)
    with make_client() as client:
        panel_session(client)
        response = client.post(PANEL_BASE + "/api/lab/traffic", headers={"X-Lab-Token": lab_token()},
                               json={"service": service, "duration": duracao})
        response.raise_for_status()
        ctx.log(f"Job de carga iniciado contra {service} por {duracao}s")
        try:
            while True:
                ctx.check_cancelled()
                job = client.get(PANEL_BASE + "/api/lab/traffic").json()
                if job.get("status") != "running":
                    break
                counts = job.get("services", {}).get(service, {})
                ctx.progress(tentativas=counts.get("attempted", 0), sucesso=counts.get("successful", 0),
                             falhas=counts.get("failed", 0))
                if expected[0] in _firing(client):
                    ctx.log(f"Alerta {expected[0]} em firing; encerrando execução para verificação")
                    break
                time.sleep(1)
        finally:
            final = client.get(PANEL_BASE + "/api/lab/traffic")
            try:
                status = final.json().get("status")
            except Exception:
                status = "desconhecido"
            if status == "running":
                client.request("DELETE", PANEL_BASE + "/api/lab/traffic")
                ctx.log("Job de carga cancelado no fim do ataque")
            else:
                ctx.log(f"Job de carga terminou com status {status}")


def flood_dns(ctx, params):
    _traffic_attack(ctx, "dns", params["duracao"], ["TrafegoAnormal"])


def flood_smtp(ctx, params):
    _traffic_attack(ctx, "smtp", params["duracao"], ["TrafegoAnormal"])


def adulteracao_config(ctx, params):
    relativo = str(params["arquivo"]).replace("\\", "/").strip("/")
    duracao = int(params["duracao"])
    ctx.set_expected_alerts(["ConfiguracaoAlterada"])
    if not relativo.startswith("infra/"):
        raise ValueError("arquivo_fora_do_escopo")
    dentro = relativo[len("infra/"):]
    raiz = INFRA_ROOT.resolve()
    caminho = (raiz / dentro).resolve()
    if caminho == raiz or not str(caminho).startswith(str(raiz) + os.sep):
        raise ValueError("arquivo_fora_do_escopo")
    if not caminho.is_file():
        raise FileNotFoundError(relativo)
    original = caminho.read_bytes()
    caminho.write_bytes(original + b"\n# linha adulterada pelo painel de ataques\n")
    ctx.log(f"Arquivo {relativo} adulterado; coletor de integridade deve detectar a mudança")
    try:
        _hold(ctx, duracao)
    finally:
        caminho.write_bytes(original)
        ctx.log(f"Arquivo {relativo} restaurado byte a byte")


def interrupcao_servico(ctx, params):
    alvo = str(params["alvo"])
    duracao = int(params["duracao"])
    if alvo not in STOP_ALERTS:
        raise ValueError("alvo_invalido")
    ctx.set_expected_alerts([STOP_ALERTS[alvo]])
    with docker_client() as docker:
        container_id = _container_id(docker, alvo)
        _docker_control(docker, container_id, "stop")
    ctx.log(f"Serviço {alvo} parado; sondas correspondentes devem falhar")
    try:
        deadline = time.monotonic() + max(duracao, 90)
        with make_client() as client:
            while time.monotonic() < deadline:
                ctx.check_cancelled()
                if STOP_ALERTS[alvo] in _firing(client):
                    ctx.log(f"Alerta {STOP_ALERTS[alvo]} em firing; restaurando serviço")
                    break
                ctx.progress(segundos_restantes=max(0, int(deadline - time.monotonic())))
                time.sleep(1)
    finally:
        with docker_client() as docker:
            _docker_control(docker, _container_id(docker, alvo), "start")
        ctx.log(f"Serviço {alvo} reiniciado")


RUNNERS = {
    "bruteforce-servico": bruteforce_servico,
    "bruteforce-painel": bruteforce_painel,
    "sobrecarga-http": sobrecarga_http,
    "indisponibilidade-http": indisponibilidade_http,
    "flood-dns": flood_dns,
    "flood-smtp": flood_smtp,
    "adulteracao-config": adulteracao_config,
    "interrupcao-servico": interrupcao_servico,
}
