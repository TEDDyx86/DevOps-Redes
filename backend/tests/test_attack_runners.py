import threading

import dns.exception
import httpx
import pytest

from backend.app.attacks import catalog, runners
from backend.app.attacks.engine import Cancelled


class FakeCtx:
    def __init__(self):
        self.expected = []
        self.counters = {}
        self.logs = []
        self._cancel = threading.Event()

    def cancelled(self):
        return self._cancel.is_set()

    def check_cancelled(self):
        if self._cancel.is_set():
            raise Cancelled()

    def request_cancel(self):
        self._cancel.set()

    def set_expected_alerts(self, alerts):
        self.expected = list(alerts)

    def log(self, message):
        self.logs.append(str(message))

    def progress(self, **counters):
        self.counters.update(counters)


def test_forca_bruta_no_servico_faz_tentativas_401_e_define_alerta(monkeypatch):
    chamadas = []

    def handler(request):
        chamadas.append(request.url.path)
        return httpx.Response(401, json={"detail": "Token inválido"})

    monkeypatch.setattr(runners, "make_client", lambda: httpx.Client(transport=httpx.MockTransport(handler), trust_env=False))
    monkeypatch.setattr(runners, "BRUTEFORCE_HOLD", 0)
    ctx = FakeCtx()
    runners.bruteforce_servico(ctx, {"tentativas": 6})
    assert len(chamadas) == 6
    assert ctx.counters == {"tentativas": 6, "rejeitadas": 6, "segundos_restantes": 0}
    assert ctx.expected == ["AutenticacaoServicoSuspeita"]


def test_forca_bruta_no_painel_ataca_login_e_define_alerta(monkeypatch):
    corpos = []

    def handler(request):
        corpos.append(request.read())
        return httpx.Response(401, json={"detail": "Credenciais inválidas"})

    monkeypatch.setattr(runners, "make_client", lambda: httpx.Client(transport=httpx.MockTransport(handler), trust_env=False))
    monkeypatch.setattr(runners, "BRUTEFORCE_HOLD", 0)
    ctx = FakeCtx()
    runners.bruteforce_painel(ctx, {"tentativas": 6})
    assert len(corpos) == 6
    assert b'"username":' in corpos[0]
    assert ctx.expected == ["AutenticacaoSuspeita"]
    assert ctx.counters["tentativas"] == 6


def test_sobrecarga_http_dispara_mare(monkeypatch):
    contador = {"n": 0}

    def handler(request):
        if request.url.path == "/api/v1/query":
            return httpx.Response(200, json={"status": "success", "data": {"result": []}})
        contador["n"] += 1
        return httpx.Response(200, json={"message": "ok"})

    monkeypatch.setattr(runners, "make_client", lambda: httpx.Client(transport=httpx.MockTransport(handler), trust_env=False))
    monkeypatch.setattr(runners, "SOBRECARGA_HOLD", 0)
    ctx = FakeCtx()
    runners.sobrecarga_http(ctx, {"taxa": 10, "duracao": 1})
    assert contador["n"] > 0
    assert ctx.counters["requisicoes"] == contador["n"]
    assert ctx.expected == ["TrafegoAnormal"]


def test_sobrecarga_http_interrompida_levanta_cancelled(monkeypatch):
    def handler(request):
        if request.url.path == "/api/v1/query":
            return httpx.Response(200, json={"status": "success", "data": {"result": []}})
        return httpx.Response(200, json={"message": "ok"})

    monkeypatch.setattr(runners, "make_client", lambda: httpx.Client(transport=httpx.MockTransport(handler), trust_env=False))
    monkeypatch.setattr(runners, "SOBRECARGA_HOLD", 0)
    ctx = FakeCtx()
    threading.Timer(0.1, ctx.request_cancel).start()
    try:
        runners.sobrecarga_http(ctx, {"taxa": 10, "duracao": 5})
        raise AssertionError("deveria interromper")
    except Cancelled:
        pass


def test_lentidao_http_ativa_slow_e_restaura_normal(monkeypatch):
    modos = []

    def handler(request):
        if request.method == "POST" and request.url.path == "/mode":
            modos.append(request.read())
            return httpx.Response(200, json={"mode": "slow"})
        if request.url.path == "/api/v1/query":
            return httpx.Response(200, json={"status": "success", "data": {"result": [{"metric": {"alertname": "HTTPLento"}}]}})
        return httpx.Response(404)

    monkeypatch.setattr(runners, "make_client", lambda: httpx.Client(transport=httpx.MockTransport(handler), trust_env=False))
    monkeypatch.setattr(runners, "lab_token", lambda: "token-de-teste")
    ctx = FakeCtx()
    runners.lentidao_http(ctx, {"duracao": 5})
    assert modos[0] == b'{"mode":"slow"}'
    assert modos[-1] == b'{"mode":"normal"}'
    assert ctx.expected == ["HTTPLento"]


def test_indisponibilidade_restaura_modo_normal_mesmo_interrompido(monkeypatch):
    modos = []

    def handler(request):
        if request.method == "POST" and request.url.path == "/mode":
            modos.append(request.read())
            if b'"offline"' in modos[-1]:
                return httpx.Response(200, json={"mode": "offline"})
            return httpx.Response(200, json={"mode": "normal"})
        if request.url.path == "/api/v1/query":
            return httpx.Response(200, json={"status": "success", "data": {"result": []}})
        return httpx.Response(404)

    monkeypatch.setattr(runners, "make_client", lambda: httpx.Client(transport=httpx.MockTransport(handler), trust_env=False))
    monkeypatch.setattr(runners, "lab_token", lambda: "token-de-teste")
    ctx = FakeCtx()
    threading.Timer(0.2, ctx.request_cancel).start()
    try:
        runners.indisponibilidade_http(ctx, {"duracao": 5})
        raise AssertionError("deveria interromper")
    except Cancelled:
        pass
    assert modos[0] == b'{"mode":"offline"}'
    assert modos[-1] == b'{"mode":"normal"}'
    assert ctx.expected == ["HTTPIndisponivel"]


def test_varredura_404_gera_erros_4xx(monkeypatch):
    rotas = []

    def handler(request):
        rotas.append(request.url.path)
        return httpx.Response(404, json={"detail": "Produto não encontrado"})

    monkeypatch.setattr(runners, "make_client", lambda: httpx.Client(transport=httpx.MockTransport(handler), trust_env=False))
    monkeypatch.setattr(runners.time, "sleep", lambda _s: None)
    ctx = FakeCtx()
    runners.varredura_404(ctx, {"requisicoes": 10})
    assert len(rotas) == 10
    assert ctx.counters == {"requisicoes": 10, "erros_4xx": 10}
    assert ctx.expected == []


def test_lab_token_vem_do_ambiente(monkeypatch):
    monkeypatch.setenv("LAB_TOKEN", "token-do-container")
    assert runners.lab_token() == "token-do-container"
    monkeypatch.delenv("LAB_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        runners.lab_token()


def test_flood_dns_para_quando_alerta_fica_firing(monkeypatch):
    queries = []

    def fake_getaddrinfo(_host, _port, type=None):
        return [(None, None, None, None, ("127.0.0.1", 1053))]

    def fake_udp(_msg, _addr, port=1053, timeout=1.5):
        queries.append(port)
        return object()

    def handler(request):
        if request.url.path == "/api/v1/query":
            return httpx.Response(200, json={"status": "success", "data": {"result": [{"metric": {"alertname": "TrafegoAnormal"}}]}})
        return httpx.Response(404)

    monkeypatch.setattr(runners.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(runners.dns.query, "udp", fake_udp)
    monkeypatch.setattr(runners, "make_client", lambda: httpx.Client(transport=httpx.MockTransport(handler), trust_env=False))
    monkeypatch.setattr(runners.time, "sleep", lambda _s: None)
    ctx = FakeCtx()
    runners.flood_dns(ctx, {"duracao": 3})
    assert len(queries) > 0
    assert ctx.expected == ["TrafegoAnormal"]
    assert any("firing" in m for m in ctx.logs)


def test_flood_postgres_para_quando_alerta_fica_firing(monkeypatch):
    execs = []

    class FakeConn:
        closed = False

        def execute(self, sql):
            execs.append(sql)

        def close(self):
            self.closed = True

    def handler(request):
        return httpx.Response(200, json={"status": "success", "data": {"result": [{"metric": {"alertname": "TrafegoAnormal"}}]}})

    monkeypatch.setenv("POSTGRES_WORKLOAD_DSN", "postgresql://lab:secret@postgres:5432/lab")
    monkeypatch.setattr(runners.psycopg, "connect", lambda *a, **kw: FakeConn())
    monkeypatch.setattr(runners, "make_client", lambda: httpx.Client(transport=httpx.MockTransport(handler), trust_env=False))
    monkeypatch.setattr(runners.time, "sleep", lambda _s: None)
    ctx = FakeCtx()
    runners.flood_postgres(ctx, {"duracao": 3})
    assert execs and execs[0] == "SELECT 1"
    assert ctx.expected == ["TrafegoAnormal"]


def test_adulteracao_mapeia_para_a_raiz_do_container_e_restaura(monkeypatch, tmp_path):
    alvo = tmp_path / "dns" / "Corefile"
    alvo.parent.mkdir(parents=True)
    original = b"aularedes.local {\n  errors\n}\n"
    alvo.write_bytes(original)
    monkeypatch.setattr(runners, "INFRA_ROOT", tmp_path)
    monkeypatch.setattr(
        runners,
        "make_client",
        lambda: httpx.Client(
            transport=httpx.MockTransport(
                lambda _req: httpx.Response(200, json={"status": "success", "data": {"result": [{"metric": {"alertname": "ConfiguracaoAlterada"}}]}})
            ),
            trust_env=False,
        ),
    )
    ctx = FakeCtx()
    runners.adulteracao_config(ctx, {"arquivo": "infra/dns/Corefile", "duracao": 5})
    assert alvo.read_bytes() == original
    assert ctx.expected == ["ConfiguracaoAlterada"]
    assert any("restaurado" in mensagem for mensagem in ctx.logs)


def test_adulteracao_recusa_arquivo_fora_da_raiz(monkeypatch, tmp_path):
    monkeypatch.setattr(runners, "INFRA_ROOT", tmp_path)
    ctx = FakeCtx()
    for relativo in ("../secrets/x", "backend/app/config.py", "infra/../../compose.yaml"):
        try:
            runners.adulteracao_config(ctx, {"arquivo": relativo, "duracao": 1})
            raise AssertionError("deveria recusar " + relativo)
        except ValueError as error:
            assert "arquivo_fora_do_escopo" in str(error)


def _docker_falso(registro):
    def handler(request):
        if request.url.path == "/containers/json":
            registro.append(("list", request.url.params.get("filters", "")))
            if registro and registro[0][0] == "parado":
                return httpx.Response(200, json=[])
            registro.append(("listado", None))
            return httpx.Response(200, json=[{"Id": "abc123", "Names": ["/aularedes-dns-1"]}])
        if request.url.path == "/containers/abc123/stop":
            registro.append(("stop", None))
            return httpx.Response(204)
        if request.url.path == "/containers/abc123/start":
            registro.append(("start", None))
            return httpx.Response(204)
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler), trust_env=False, base_url="http://docker")


def test_interrupcao_para_e_reinicia_via_api_do_docker(monkeypatch):
    registro = []

    def disparo_firing(request):
        return httpx.Response(200, json={"status": "success", "data": {"result": [{"metric": {"alertname": "DNSIndisponivel", "alertstate": "firing"}}]}})

    monkeypatch.setattr(runners, "docker_client", lambda: _docker_falso(registro))
    monkeypatch.setattr(runners, "make_client", lambda: httpx.Client(transport=httpx.MockTransport(disparo_firing), trust_env=False))
    ctx = FakeCtx()
    runners.interrupcao_servico(ctx, {"alvo": "dns", "duracao": 1})
    acoes = [item[0] for item in registro if item[0] in ("stop", "start")]
    assert acoes == ["stop", "start"]
    filtros = registro[0][1]
    assert "com.docker.compose.service" in filtros and "dns" in filtros
    assert ctx.expected == ["DNSIndisponivel"]
    assert any("reiniciado" in mensagem for mensagem in ctx.logs)


def test_interrupcao_recusa_alvos_proibidos():
    ctx = FakeCtx()
    for alvo in ("api", "prometheus", "alertmanager"):
        try:
            runners.interrupcao_servico(ctx, {"alvo": alvo, "duracao": 30})
            raise AssertionError("deveria recusar " + alvo)
        except ValueError as error:
            assert "alvo_invalido" in str(error)


def test_interrupcao_falha_se_container_nao_for_localizado(monkeypatch):
    def handler(request):
        if request.url.path == "/containers/json":
            return httpx.Response(200, json=[])
        return httpx.Response(404)

    monkeypatch.setattr(runners, "docker_client", lambda: httpx.Client(transport=httpx.MockTransport(handler), trust_env=False, base_url="http://docker"))
    ctx = FakeCtx()
    with pytest.raises(ValueError) as excinfo:
        runners.interrupcao_servico(ctx, {"alvo": "dns", "duracao": 30})
    assert "container_nao_encontrado" in str(excinfo.value)


def test_registro_runners_cobre_o_catalogo():
    assert set(runners.RUNNERS) == {ataque["id"] for ataque in catalog.CATALOG}
