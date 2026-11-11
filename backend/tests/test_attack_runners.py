import threading

import httpx

from scripts.attack_panel import catalog, runners
from scripts.attack_panel.engine import Cancelled


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
        contador["n"] += 1
        return httpx.Response(200, json={"message": "ok"})

    monkeypatch.setattr(runners, "make_client", lambda: httpx.Client(transport=httpx.MockTransport(handler), trust_env=False))
    monkeypatch.setattr(runners, "SOBRECARGA_HOLD", 0)
    ctx = FakeCtx()
    runners.sobrecarga_http(ctx, {"taxa": 10, "duracao": 1})
    assert contador["n"] > 0
    assert ctx.counters["requisicoes"] == contador["n"]
    assert ctx.expected == ["RecursoCPUElevada", "TrafegoAnormal"]


def test_sobrecarga_http_interrompida_levanta_cancelled(monkeypatch):
    def handler(request):
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


def test_indisponibilidade_restaura_modo_normal_mesmo_interrompido(monkeypatch):
    modos = []

    def handler(request):
        if request.method == "POST" and request.url.path == "/mode":
            modos.append(request.read())
            if b'"offline"' in modos[-1]:
                return httpx.Response(200, json={"mode": "offline"})
            return httpx.Response(200, json={"mode": "normal"})
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


def test_flood_via_job_de_carga_termina_quando_alerta_fica_firing(monkeypatch):
    consultas = []
    job_state = {"status": "running", "services": {"dns": {"attempted": 10, "successful": 9, "failed": 1}}}

    def handler(request):
        if request.method == "POST" and request.url.path == "/api/lab/traffic":
            return httpx.Response(200, json={"status": "running"})
        if request.method == "DELETE" and request.url.path == "/api/lab/traffic":
            job_state["status"] = "cancelled"
            return httpx.Response(200, json={"status": "cancelled"})
        if request.url.path == "/api/lab/traffic":
            return httpx.Response(200, json=dict(job_state))
        if request.url.path == "/api/v1/query":
            consultas.append(1)
            if len(consultas) >= 2:
                payload = {"status": "success", "data": {"result": [{"metric": {"alertname": "TrafegoAnormal", "alertstate": "firing"}}]}}
            else:
                payload = {"status": "success", "data": {"result": []}}
            return httpx.Response(200, json=payload)
        return httpx.Response(404)

    monkeypatch.setattr(runners, "make_client", lambda: httpx.Client(transport=httpx.MockTransport(handler), trust_env=False))
    monkeypatch.setattr(runners, "lab_token", lambda: "token-de-teste")
    monkeypatch.setattr(runners, "authenticate", lambda client: None)
    ctx = FakeCtx()
    runners.flood_dns(ctx, {"duracao": 60})
    assert ctx.expected == ["TrafegoAnormal"]
    assert ctx.counters["tentativas"] == 10
    assert any("firing" in mensagem for mensagem in ctx.logs)


def test_adulteracao_modifica_e_restaura_bytes_originais(monkeypatch, tmp_path):
    alvo = tmp_path / "infra" / "dns" / "Corefile"
    alvo.parent.mkdir(parents=True)
    original = b"aularedes.local {\n  errors\n}\n"
    alvo.write_bytes(original)
    monkeypatch.setattr(runners, "ROOT", tmp_path)
    ctx = FakeCtx()
    runners.adulteracao_config(ctx, {"arquivo": "infra/dns/Corefile", "duracao": 1})
    assert alvo.read_bytes() == original
    assert ctx.expected == ["ConfiguracaoAlterada"]
    assert any("restaurado" in mensagem for mensagem in ctx.logs)


def test_adulteracao_recusa_arquivo_fora_de_infra(monkeypatch, tmp_path):
    monkeypatch.setattr(runners, "ROOT", tmp_path)
    ctx = FakeCtx()
    try:
        runners.adulteracao_config(ctx, {"arquivo": "../secrets/x", "duracao": 1})
        raise AssertionError("deveria recusar")
    except ValueError as error:
        assert "arquivo_fora_do_escopo" in str(error)


def test_interrupcao_para_e_reinicia_servico_com_alerta_do_alvo(monkeypatch):
    comandos = []

    def docker_falso(*argumentos):
        comandos.append(list(argumentos))

    def handler(request):
        return httpx.Response(200, json={"status": "success", "data": {"result": [{"metric": {"alertname": "DNSIndisponivel", "alertstate": "firing"}}]}})

    monkeypatch.setattr(runners, "_docker_compose", docker_falso)
    monkeypatch.setattr(runners, "make_client", lambda: httpx.Client(transport=httpx.MockTransport(handler), trust_env=False))
    ctx = FakeCtx()
    runners.interrupcao_servico(ctx, {"alvo": "dns", "duracao": 60})
    assert comandos == [["stop", "dns"], ["start", "dns"]]
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


def test_registro_runners_cobre_o_catalogo():
    assert set(runners.RUNNERS) == {ataque["id"] for ataque in catalog.CATALOG}
