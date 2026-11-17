import httpx
import pytest
from fastapi.testclient import TestClient

from demo.attacks.catalog import CATALOG
from scripts.attack_panel import server


class FakeEngine:
    def __init__(self):
        self.started = []
        self.cancelled = []

    def enqueue(self, attack_id, params=None):
        if params and any(value == 9999 for value in params.values()):
            raise ValueError("parametro_fora_da_faixa")
        self.started.append((attack_id, params))
        return {"entry_id": "e1", "attack": attack_id, "status": "agendado"}

    def cancel(self, entry_id):
        if entry_id == "desconhecido":
            return None
        self.cancelled.append(entry_id)
        return {"entry_id": entry_id, "status": "interrompendo"}

    def snapshot(self):
        return {"current": None, "queue": [], "history": []}

    def subscribe(self):
        yield "data: {}\n\n"


@pytest.fixture()
def client():
    app = server.create_app(engine=FakeEngine())
    return TestClient(app)


def test_bind_e_exclusivamente_localhost():
    assert server.HOST == "127.0.0.1"


def test_saude_e_catalogo(client):
    assert client.get("/health").json() == {"status": "ok"}
    corpo = client.get("/api/attacks").json()
    assert [a["id"] for a in corpo["attacks"]] == [a["id"] for a in CATALOG]


def test_disparo_valido_invalido_e_desconhecido(client):
    engine = client.app.state.engine
    resposta = client.post("/api/attacks/flood-dns/start", json={"params": {"duracao": 60}})
    assert resposta.status_code == 200 and resposta.json()["status"] == "agendado"
    assert engine.started == [("flood-dns", {"duracao": 60})]
    assert client.post("/api/attacks/flood-dns/start", json={"params": {"duracao": 9999}}).status_code == 400
    assert client.post("/api/attacks/ataque-falso/start", json={}).status_code == 404


def test_cancelamento_e_fila(client):
    assert client.post("/api/queue/e1/cancel").status_code == 200
    assert client.app.state.engine.cancelled == ["e1"]
    assert client.post("/api/queue/desconhecido/cancel").status_code == 404
    assert client.get("/api/queue").json() == {"current": None, "queue": [], "history": []}


def test_sse_e_pagina_estatica_servida(client):
    with client.stream("GET", "/api/events") as resposta:
        assert resposta.status_code == 200
        assert "text/event-stream" in resposta.headers["content-type"]
    pagina = client.get("/")
    assert pagina.status_code == 200 and "Painel de Ataques" in pagina.text
    resposta_js = client.get("/panel.js")
    resposta_css = client.get("/panel.css")
    assert resposta_js.status_code == 200
    assert resposta_css.status_code == 200
    assert resposta_js.headers["content-type"].startswith("application/javascript")
    assert resposta_css.headers["content-type"].startswith("text/css")


def test_verificador_tenta_ate_conseguir_e_nunca_inventa_sucesso(monkeypatch):
    tentativas = []

    class ClientFalso:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, params=None):
            tentativas.append(1)
            raise httpx.ConnectError("prometheus fora do ar")

    monkeypatch.setattr(server.runners, "make_client", lambda: ClientFalso())
    monkeypatch.setattr(server.time, "sleep", lambda segundos: None)
    resultado = server.build_verifier()(["TrafegoAnormal"], lambda: False)
    assert resultado == {"available": False, "fired": [], "missing": ["TrafegoAnormal"]}
    assert len(tentativas) == 6


def test_verificador_repete_ate_o_alerta_disparar(monkeypatch):
    tentativas = []

    def resposta():
        if len(tentativas) < 3:
            return {"status": "success", "data": {"result": []}}
        return {"status": "success", "data": {"result": [{"metric": {"alertname": "AutenticacaoServicoSuspeita", "alertstate": "firing"}}]}}

    class ClientFalso:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, params=None):
            tentativas.append(1)
            return httpx.Response(200, json=resposta(), request=httpx.Request("GET", url))

    monkeypatch.setattr(server.runners, "make_client", lambda: ClientFalso())
    monkeypatch.setattr(server.time, "sleep", lambda segundos: None)
    resultado = server.build_verifier()(["AutenticacaoServicoSuspeita"], lambda: False)
    assert resultado == {"available": True, "fired": ["AutenticacaoServicoSuspeita"], "missing": []}
    assert len(tentativas) == 3


def test_verificador_para_quando_a_execucao_foi_interrompida(monkeypatch):
    tentativas = []

    class ClientFalso:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, params=None):
            tentativas.append(1)
            return httpx.Response(200, json={"status": "success", "data": {"result": []}}, request=httpx.Request("GET", url))

    monkeypatch.setattr(server.runners, "make_client", lambda: ClientFalso())
    monkeypatch.setattr(server.time, "sleep", lambda segundos: None)
    resultado = server.build_verifier()(["TrafegoAnormal"], lambda: len(tentativas) >= 1)
    assert resultado == {"available": True, "fired": [], "missing": ["TrafegoAnormal"]}
    assert len(tentativas) == 1
