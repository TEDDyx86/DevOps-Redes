import threading

import httpx

from scripts.attack_panel import runners
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
