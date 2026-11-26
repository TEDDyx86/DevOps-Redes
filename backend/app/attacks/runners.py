"""Runners dos ataques: efeitos controlados dentro da plataforma, sempre reversíveis."""
import json
import os
import smtplib
import socket
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage
from pathlib import Path

import dns.exception
import dns.message
import dns.query
import httpx
import psycopg

from backend.app.attacks import verification
from backend.app.attacks.engine import Cancelled

DEMO_BASE = os.environ.get("DEMO_URL", os.environ.get("DEMO_BASE", "http://web-demo:8001"))
PANEL_BASE = os.environ.get("PANEL_BASE", "http://127.0.0.1:8000")
PROMETHEUS_BASE = os.environ.get("PROMETHEUS_URL", os.environ.get("PROMETHEUS_BASE", "http://prometheus:9090"))
INFRA_ROOT = Path(os.environ.get("INFRA_WRITE_ROOT", os.environ.get("INFRA_ROOT", "/etc/aularedes/runtime")))
DOCKER_SOCKET = os.environ.get("DOCKER_SOCKET", "/var/run/docker.sock")

BURST_INTERVAL = 0.15
BRUTEFORCE_HOLD = 60
SOBRECARGA_HOLD = 45
STOP_GRACE_SECONDS = 15
POST_FIRE_OBSERVE_SECONDS = 8


def make_client():
    return httpx.Client(timeout=5, trust_env=False)


def docker_client():
    return httpx.Client(
        transport=httpx.HTTPTransport(uds=DOCKER_SOCKET),
        base_url="http://docker",
        timeout=30,
        trust_env=False,
    )


def lab_token():
    token = os.environ.get("LAB_TOKEN", "")
    if not token:
        raise RuntimeError("LAB_TOKEN ausente no ambiente do container")
    return token


def _firing(client):
    try:
        return verification.firing_alerts(client, PROMETHEUS_BASE)
    except Exception:
        return set()


def _poll_alerts(ctx, client, watch_alert, seen_state):
    try:
        state = verification.live_alerts(client, PROMETHEUS_BASE)
    except Exception:
        state = None
    expected = [watch_alert] if watch_alert else (
        ctx.snapshot().get("expected_alerts", []) if hasattr(ctx, "snapshot") else getattr(ctx, "expected", [])
    )
    live = verification.summarize_live(expected, state)
    if hasattr(ctx, "report_alerts"):
        ctx.report_alerts(live)
    target_pending = watch_alert in live["pending"] if watch_alert else bool(live["pending"])
    target_fired = watch_alert in live["fired"] if watch_alert else bool(live["fired"])
    if target_pending and not seen_state["pending"]:
        seen_state["pending"] = True
        name = watch_alert or ", ".join(live["pending"])
        ctx.log(f"Detectado no Prometheus ({name}: pending — aguardando confirmação da regra)")
    if target_fired and not seen_state["firing"]:
        seen_state["firing"] = True
        name = watch_alert or ", ".join(live["fired"])
        ctx.log(f"Alerta {name} em firing (incidente/e-mail disparados em tempo real)")
    return target_fired


def _hold(ctx, seconds, watch_alert=None):
    if seconds <= 0:
        ctx.progress(segundos_restantes=0)
        return
    deadline = time.monotonic() + seconds
    seen = {"pending": False, "firing": False}
    fired_at = None
    with make_client() as client:
        while True:
            ctx.check_cancelled()
            now = time.monotonic()
            restante = max(0, int(deadline - now))
            ctx.progress(segundos_restantes=restante)
            if watch_alert and _poll_alerts(ctx, client, watch_alert, seen):
                if POST_FIRE_OBSERVE_SECONDS <= 0:
                    ctx.log(f"Alerta {watch_alert} em firing; seguindo para verificação")
                    return
                if fired_at is None:
                    fired_at = now
                if now - fired_at >= POST_FIRE_OBSERVE_SECONDS:
                    ctx.log(f"Alerta {watch_alert} confirmado durante o ataque; encerrando")
                    return
            if restante <= 0:
                return
            time.sleep(1)


def bruteforce_servico(ctx, params):
    tentativas = int(params["tentativas"])
    ctx.set_expected_alerts(["AutenticacaoServicoSuspeita"])
    feitas = rejeitadas = 0
    with make_client() as client:
        for index in range(tentativas):
            ctx.check_cancelled()
            started = time.perf_counter()
            try:
                response = client.post(
                    DEMO_BASE.rstrip("/") + "/mode",
                    json={"mode": "normal"},
                    headers={"X-Lab-Token": "ataque-" + uuid.uuid4().hex[:12]},
                )
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
        ctx.log("Rajada concluída; mantendo taxa e aguardando 'for: 30s' de AutenticacaoServicoSuspeita")
        if BRUTEFORCE_HOLD <= 0:
            ctx.progress(segundos_restantes=0)
            return
        deadline = time.monotonic() + BRUTEFORCE_HOLD
        seen = {"pending": False, "firing": False}
        fired_at = None
        while True:
            ctx.check_cancelled()
            now = time.monotonic()
            restante = max(0, int(deadline - now))
            ctx.progress(tentativas=feitas, rejeitadas=rejeitadas, segundos_restantes=restante)
            if _poll_alerts(ctx, client, "AutenticacaoServicoSuspeita", seen):
                if POST_FIRE_OBSERVE_SECONDS <= 0:
                    ctx.log("Alerta AutenticacaoServicoSuspeita em firing; seguindo para verificação")
                    return
                if fired_at is None:
                    fired_at = now
                if now - fired_at >= POST_FIRE_OBSERVE_SECONDS:
                    ctx.log("Alerta AutenticacaoServicoSuspeita confirmado durante o ataque; encerrando")
                    return
            if restante <= 0:
                return
            try:
                response = client.post(
                    DEMO_BASE.rstrip("/") + "/mode",
                    json={"mode": "normal"},
                    headers={"X-Lab-Token": "ataque-" + uuid.uuid4().hex[:12]},
                )
                if response.status_code == 401:
                    rejeitadas += 1
            except httpx.HTTPError:
                pass
            feitas += 1
            time.sleep(2)


def bruteforce_painel(ctx, params):
    tentativas = int(params["tentativas"])
    ctx.set_expected_alerts(["AutenticacaoSuspeita"])
    feitas = rejeitadas = 0
    with make_client() as client:
        for index in range(tentativas):
            ctx.check_cancelled()
            started = time.perf_counter()
            try:
                response = client.post(
                    PANEL_BASE.rstrip("/") + "/api/auth/login",
                    json={"username": "admin", "password": "senha-errada-" + uuid.uuid4().hex[:12]},
                )
                codigo = response.status_code
            except httpx.HTTPError:
                codigo = None
            feitas += 1
            if codigo in (401, 429):
                rejeitadas += 1
            ctx.progress(tentativas=feitas, rejeitadas=rejeitadas)
            if index % 4 == 0:
                ctx.log(f"Login {index + 1}/{tentativas}: " + (f"HTTP {codigo}" if codigo else "sem resposta"))
            espera = BURST_INTERVAL - (time.perf_counter() - started)
            if espera > 0:
                time.sleep(espera)
    ctx.log("Logins inválidos concluídos; aguardando 'for: 10s' de AutenticacaoSuspeita")
    _hold(ctx, BRUTEFORCE_HOLD, watch_alert="AutenticacaoSuspeita")


def sobrecarga_http(ctx, params):
    taxa = int(params["taxa"])
    duracao = int(params["duracao"])
    ctx.set_expected_alerts(["TrafegoAnormal"])
    workers = max(2, min(8, taxa // 5))
    stop = time.monotonic() + duracao
    shared = {"requisicoes": 0, "erros": 0}
    guard = threading.Lock()
    fired_early = threading.Event()

    def worker(client):
        local = 0
        while time.monotonic() < stop and not fired_early.is_set():
            if ctx.cancelled():
                return
            try:
                response = client.get(DEMO_BASE.rstrip("/") + "/work")
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
            time.sleep(max(0.0, (workers / max(taxa, 1)) * 0.5))

    clientes = [make_client() for _ in range(workers)]
    seen = {"pending": False, "firing": False}
    fired_at = None
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(worker, client) for client in clientes]
            with make_client() as probe_client:
                while any(not future.done() for future in futures):
                    if ctx.cancelled():
                        break
                    if _poll_alerts(ctx, probe_client, "TrafegoAnormal", seen):
                        if POST_FIRE_OBSERVE_SECONDS <= 0:
                            ctx.log("Alerta TrafegoAnormal em firing; encerrando rajada")
                            fired_early.set()
                            break
                        if fired_at is None:
                            fired_at = time.monotonic()
                        if time.monotonic() - fired_at >= POST_FIRE_OBSERVE_SECONDS:
                            ctx.log("Alerta TrafegoAnormal confirmado durante o ataque; encerrando rajada")
                            fired_early.set()
                            break
                    time.sleep(1)
            for future in futures:
                future.result()
    finally:
        for client in clientes:
            client.close()
    if ctx.cancelled():
        raise Cancelled()
    if not fired_early.is_set():
        ctx.log(f"Maré concluída ({shared['requisicoes']} req); aguardando consolidação de TrafegoAnormal")
        _hold(ctx, SOBRECARGA_HOLD, watch_alert="TrafegoAnormal")


def lentidao_http(ctx, params):
    duracao = int(params["duracao"])
    ctx.set_expected_alerts(["HTTPLento"])
    token = lab_token()
    with make_client() as client:
        response = client.post(DEMO_BASE.rstrip("/") + "/mode", json={"mode": "slow"}, headers={"X-Lab-Token": token})
        response.raise_for_status()
        ctx.log("Loja em modo slow (+850 ms); sondas devem ultrapassar 500 ms e despertar HTTPLento")
        try:
            _hold(ctx, duracao, watch_alert="HTTPLento")
        finally:
            restore = client.post(DEMO_BASE.rstrip("/") + "/mode", json={"mode": "normal"}, headers={"X-Lab-Token": token})
            if restore.status_code == 200:
                ctx.log("Modo normal restaurado")
            else:
                ctx.log(f"ATENÇÃO: restauração falhou com HTTP {restore.status_code}; restaurar manualmente")


def indisponibilidade_http(ctx, params):
    duracao = int(params["duracao"])
    ctx.set_expected_alerts(["HTTPIndisponivel"])
    token = lab_token()
    with make_client() as client:
        response = client.post(DEMO_BASE.rstrip("/") + "/mode", json={"mode": "offline"}, headers={"X-Lab-Token": token})
        response.raise_for_status()
        ctx.log("Loja em modo offline (503); sondas HTTP do painel devem falhar")
        try:
            _hold(ctx, duracao, watch_alert="HTTPIndisponivel")
        finally:
            restore = client.post(DEMO_BASE.rstrip("/") + "/mode", json={"mode": "normal"}, headers={"X-Lab-Token": token})
            if restore.status_code == 200:
                ctx.log("Modo normal restaurado")
            else:
                ctx.log(f"ATENÇÃO: restauração falhou com HTTP {restore.status_code}; restaurar manualmente")


def varredura_404(ctx, params):
    total = int(params["requisicoes"])
    ctx.set_expected_alerts([])
    alvos = [
        "/api/products/scan-admin-config",
        "/api/products/scan-backup-sql",
        "/api/products/scan-wp-login",
        "/api/products/scan-env-secret",
    ]
    feitas = erros_4xx = 0
    with make_client() as client:
        for index in range(total):
            ctx.check_cancelled()
            rota = alvos[index % len(alvos)] + f"-{index}"
            try:
                response = client.get(DEMO_BASE.rstrip("/") + rota)
                if 400 <= response.status_code < 500:
                    erros_4xx += 1
            except httpx.HTTPError:
                pass
            feitas += 1
            ctx.progress(requisicoes=feitas, erros_4xx=erros_4xx)
            if index % 15 == 0:
                ctx.log(f"Varredura {feitas}/{total} · respostas 4xx registradas: {erros_4xx}")
            time.sleep(0.05)
    ctx.log(f"Varredura concluída ({erros_4xx} respostas 4xx enviadas para métricas HTTP)")


def flood_dns(ctx, params):
    duracao = int(params["duracao"])
    ctx.set_expected_alerts(["TrafegoAnormal"])
    server = os.environ.get("DNS_SERVER", "dns")
    port = int(os.environ.get("DNS_PORT", "1053"))
    qname = os.environ.get("DNS_PROBE_NAME", "app.aularedes.test.")
    addr = socket.getaddrinfo(server, port, type=socket.SOCK_DGRAM)[0][4][0]
    deadline = time.monotonic() + duracao
    tentativas = sucesso = falhas = 0
    seen = {"pending": False, "firing": False}
    fired_at = None
    with make_client() as prom_client:
        ctx.log(f"Enviando rajada de consultas DNS contra {server}:{port} por até {duracao}s")
        while time.monotonic() < deadline:
            ctx.check_cancelled()
            batch_end = time.monotonic() + 1.0
            while time.monotonic() < batch_end:
                tentativas += 1
                try:
                    msg = dns.message.make_query(qname, "A")
                    dns.query.udp(msg, addr, port=port, timeout=1.5)
                    sucesso += 1
                except (OSError, dns.exception.DNSException):
                    falhas += 1
                time.sleep(0.05)
            ctx.progress(
                tentativas=tentativas,
                sucesso=sucesso,
                falhas=falhas,
                segundos_restantes=max(0, int(deadline - time.monotonic())),
            )
            if _poll_alerts(ctx, prom_client, "TrafegoAnormal", seen):
                if POST_FIRE_OBSERVE_SECONDS <= 0:
                    ctx.log("Alerta TrafegoAnormal em firing; encerrando flood DNS")
                    return
                if fired_at is None:
                    fired_at = time.monotonic()
                if time.monotonic() - fired_at >= POST_FIRE_OBSERVE_SECONDS:
                    ctx.log("Alerta TrafegoAnormal confirmado durante o flood DNS; encerrando")
                    return
    ctx.log("Flood DNS concluído (nota: requer baseline calibrada após 120s para disparar TrafegoAnormal)")


def flood_smtp(ctx, params):
    duracao = int(params["duracao"])
    ctx.set_expected_alerts(["TrafegoAnormal"])
    host = os.environ.get("SMTP_HOST", "smtp")
    port = int(os.environ.get("SMTP_PORT", "2525"))
    deadline = time.monotonic() + duracao
    tentativas = sucesso = falhas = 0
    seen = {"pending": False, "firing": False}
    fired_at = None
    with make_client() as prom_client:
        ctx.log(f"Enviando rajada SMTP contra {host}:{port} por até {duracao}s")
        while time.monotonic() < deadline:
            ctx.check_cancelled()
            tentativas += 1
            msg = EmailMessage()
            msg["Subject"] = f"Carga SMTP {tentativas}"
            msg["From"] = "lab-carga@aularedes.test"
            msg["To"] = "aluno@aularedes.test"
            msg.set_content("Mensagem sintética controlada pelo painel de ataques.")
            try:
                with smtplib.SMTP(host, port, timeout=3) as client:
                    client.send_message(msg)
                sucesso += 1
            except (OSError, smtplib.SMTPException):
                falhas += 1
            ctx.progress(
                tentativas=tentativas,
                sucesso=sucesso,
                falhas=falhas,
                segundos_restantes=max(0, int(deadline - time.monotonic())),
            )
            if _poll_alerts(ctx, prom_client, "TrafegoAnormal", seen):
                if POST_FIRE_OBSERVE_SECONDS <= 0:
                    ctx.log("Alerta TrafegoAnormal em firing; encerrando flood SMTP")
                    return
                if fired_at is None:
                    fired_at = time.monotonic()
                if time.monotonic() - fired_at >= POST_FIRE_OBSERVE_SECONDS:
                    ctx.log("Alerta TrafegoAnormal confirmado durante o flood SMTP; encerrando")
                    return
            time.sleep(0.5)
    ctx.log("Flood SMTP concluído (nota: requer baseline calibrada após 120s para disparar TrafegoAnormal)")


def flood_postgres(ctx, params):
    duracao = int(params["duracao"])
    ctx.set_expected_alerts(["TrafegoAnormal"])
    dsn = os.environ.get("POSTGRES_WORKLOAD_DSN", "")
    if not dsn:
        raise RuntimeError("POSTGRES_WORKLOAD_DSN ausente no ambiente do container")
    deadline = time.monotonic() + duracao
    consultas = sucesso = falhas = 0
    conn = None
    seen = {"pending": False, "firing": False}
    fired_at = None
    try:
        with make_client() as prom_client:
            ctx.log(f"Executando rajada de consultas PostgreSQL por até {duracao}s")
            while time.monotonic() < deadline:
                ctx.check_cancelled()
                batch_end = time.monotonic() + 1.0
                while time.monotonic() < batch_end:
                    consultas += 1
                    try:
                        if conn is None or conn.closed:
                            conn = psycopg.connect(dsn, autocommit=True, connect_timeout=2)
                        conn.execute("SELECT 1")
                        sucesso += 1
                    except psycopg.Error:
                        falhas += 1
                        if conn is not None:
                            try:
                                conn.close()
                            except Exception:
                                pass
                            conn = None
                    time.sleep(0.04)
                ctx.progress(
                    consultas=consultas,
                    sucesso=sucesso,
                    falhas=falhas,
                    segundos_restantes=max(0, int(deadline - time.monotonic())),
                )
                if _poll_alerts(ctx, prom_client, "TrafegoAnormal", seen):
                    if POST_FIRE_OBSERVE_SECONDS <= 0:
                        ctx.log("Alerta TrafegoAnormal em firing; encerrando flood PostgreSQL")
                        return
                    if fired_at is None:
                        fired_at = time.monotonic()
                    if time.monotonic() - fired_at >= POST_FIRE_OBSERVE_SECONDS:
                        ctx.log("Alerta TrafegoAnormal confirmado durante o flood PostgreSQL; encerrando")
                        return
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    ctx.log("Flood PostgreSQL concluído (nota: requer baseline calibrada após 120s para disparar TrafegoAnormal)")


STOP_ALERTS = {
    "dns": "DNSIndisponivel",
    "smtp": "SMTPIndisponivel",
    "web-demo": "HTTPIndisponivel",
    "postgres": "PostgreSQLIndisponivel",
}


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
    ctx.log(f"Arquivo {relativo} adulterado; coletor de integridade (5s) e Prometheus (for: 15s) devem detectar")
    try:
        _hold(ctx, duracao, watch_alert="ConfiguracaoAlterada")
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
        _hold(ctx, max(duracao, 45), watch_alert=STOP_ALERTS[alvo])
    finally:
        with docker_client() as docker:
            _docker_control(docker, _container_id(docker, alvo), "start")
        ctx.log(f"Serviço {alvo} reiniciado")


RUNNERS = {
    "bruteforce-servico": bruteforce_servico,
    "bruteforce-painel": bruteforce_painel,
    "sobrecarga-http": sobrecarga_http,
    "lentidao-http": lentidao_http,
    "indisponibilidade-http": indisponibilidade_http,
    "varredura-404": varredura_404,
    "flood-dns": flood_dns,
    "flood-smtp": flood_smtp,
    "flood-postgres": flood_postgres,
    "adulteracao-config": adulteracao_config,
    "interrupcao-servico": interrupcao_servico,
}
