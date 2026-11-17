import pytest
from fastapi.testclient import TestClient

import demo.main as demo_main
from demo.attacks.api import register as registrar_real
from demo.attacks.catalog import CATALOG
from demo.session import make_session

TOKEN = "demo-secret"
COOKIE = {"demo_session": make_session("admin", TOKEN)}


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
        return {"current": None, "queue": [], "history": [{"entry_id": "e0", "status": "concluido"}]}

    def subscribe(self):
        yield 'data: {"type": "status"}\n\n'


def registrar_fake(app, token, engine=None):
    registrar_real(app, token, FakeEngine())


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(demo_main, "register_attacks", registrar_fake)
    with TestClient(demo_main.create_demo(TOKEN, admin_username="admin", admin_password="monitor-pass")) as test_client:
        yield test_client


def rotas_protegidas(client):
    return [
        client.get("/api/attacks"),
        client.get("/api/queue"),
        client.post("/api/attacks/sobrecarga-http/start", json={"params": {}}),
        client.post("/api/queue/e1/cancel"),
        client.get("/api/events"),
    ]


def test_sem_sessao_todas_as_rotas_devolvem_401(client):
    for resposta in rotas_protegidas(client):
        assert resposta.status_code == 401, resposta.request.url


def test_sessao_valida_ve_o_catalogo_completo(client):
    resposta = client.get("/api/attacks", cookies=COOKIE)
    assert resposta.status_code == 200
    assert [ataque["id"] for ataque in resposta.json()["attacks"]] == [ataque["id"] for ataque in CATALOG]


def test_disparo_com_sessao_valida_invalido_e_desconhecido(client):
    engine = client.app.state.attack_engine
    resposta = client.post("/api/attacks/flood-dns/start", json={"params": {"duracao": 60}}, cookies=COOKIE)
    assert resposta.status_code == 200 and resposta.json()["status"] == "agendado"
    assert engine.started == [("flood-dns", {"duracao": 60})]
    fora_de_faixa = client.post("/api/attacks/flood-dns/start", json={"params": {"duracao": 9999}}, cookies=COOKIE)
    assert fora_de_faixa.status_code == 400 and "parametro_fora_da_faixa" in fora_de_faixa.text
    desconhecido = client.post("/api/attacks/ataque-falso/start", json={}, cookies=COOKIE)
    assert desconhecido.status_code == 404 and "ataque_desconhecido" in desconhecido.text


def test_fila_e_cancelamento_com_sessao(client):
    engine = client.app.state.attack_engine
    fila = client.get("/api/queue", cookies=COOKIE)
    assert fila.status_code == 200
    assert fila.json() == {"current": None, "queue": [], "history": [{"entry_id": "e0", "status": "concluido"}]}
    cancelado = client.post("/api/queue/e1/cancel", cookies=COOKIE)
    assert cancelado.status_code == 200 and cancelado.json()["status"] == "interrompendo"
    assert engine.cancelled == ["e1"]
    inexistente = client.post("/api/queue/desconhecido/cancel", cookies=COOKIE)
    assert inexistente.status_code == 404


def test_stream_de_eventos_com_sessao(client):
    with client.stream("GET", "/api/events", cookies=COOKIE) as resposta:
        assert resposta.status_code == 200
        corpo = b"".join(resposta.iter_bytes())
    assert b'type": "status"' in corpo
