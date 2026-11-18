from fastapi.testclient import TestClient as PublicClient
import pytest

import backend.app.main as platform_main
import demo.main as demo_main
from backend.app.attacks.catalog import CATALOG
from backend.app.config import Settings
from backend.tests.auth_helpers import AuthenticatedClient as TestClient, PASSWORD


class FakeEngine:
    def __init__(self):
        self.started = []
        self.cancelled = []
        self.stopped = False

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

    def stop(self):
        self.stopped = True


@pytest.fixture()
def auth_client(tmp_path, monkeypatch):
    from backend.app.passwords import hash_password

    monkeypatch.setattr(platform_main, "build_attack_engine", FakeEngine)
    settings = Settings(
        database_path=tmp_path / "incidents.sqlite",
        webhook_token="wh",
        lab_token="lab",
        enable_probe=False,
        auth_username="admin",
        auth_password_hash=hash_password(PASSWORD),
    )
    with TestClient(platform_main.create_app(settings)) as client:
        yield client


def test_web_demo_nao_expoe_rotas_de_ataque(tmp_path):
    with PublicClient(demo_main.create_demo("demo-secret", static_path=tmp_path / "sem-static")) as client:
        assert not hasattr(client.app.state, "attack_engine")
        assert client.get("/api/attacks").status_code == 404
        assert client.get("/api/queue").status_code == 404
        assert client.post("/api/attacks/sobrecarga-http/start", json={}).status_code == 404


def test_sem_sessao_rotas_de_ataques_no_painel_devolvem_401(tmp_path, monkeypatch):
    monkeypatch.setattr(platform_main, "build_attack_engine", FakeEngine)
    settings = Settings(database_path=tmp_path / "incidents.sqlite", enable_probe=False)
    with PublicClient(platform_main.create_app(settings)) as client:
        assert client.get("/api/attacks").status_code == 401
        assert client.get("/api/queue").status_code == 401
        assert client.post("/api/attacks/sobrecarga-http/start", json={"params": {}}).status_code == 401
        assert client.post("/api/queue/e1/cancel").status_code == 401
        assert client.get("/api/events").status_code == 401


def test_sessao_valida_ve_o_catalogo_completo(auth_client):
    resposta = auth_client.get("/api/attacks")
    assert resposta.status_code == 200
    assert [a["id"] for a in resposta.json()["attacks"]] == [a["id"] for a in CATALOG]


def test_disparo_com_sessao_valida_invalido_e_desconhecido(auth_client):
    engine = auth_client.app.state.attack_engine
    resposta = auth_client.post("/api/attacks/flood-dns/start", json={"params": {"duracao": 60}})
    assert resposta.status_code == 200 and resposta.json()["status"] == "agendado"
    assert engine.started == [("flood-dns", {"duracao": 60})]

    fora_de_faixa = auth_client.post("/api/attacks/flood-dns/start", json={"params": {"duracao": 9999}})
    assert fora_de_faixa.status_code == 400 and "parametro_fora_da_faixa" in fora_de_faixa.text

    desconhecido = auth_client.post("/api/attacks/ataque-falso/start", json={})
    assert desconhecido.status_code == 404 and "ataque_desconhecido" in desconhecido.text


def test_fila_e_cancelamento_com_sessao(auth_client):
    engine = auth_client.app.state.attack_engine
    fila = auth_client.get("/api/queue")
    assert fila.status_code == 200
    assert fila.json() == {"current": None, "queue": [], "history": [{"entry_id": "e0", "status": "concluido"}]}

    cancelado = auth_client.post("/api/queue/e1/cancel")
    assert cancelado.status_code == 200 and cancelado.json()["status"] == "interrompendo"
    assert engine.cancelled == ["e1"]

    inexistente = auth_client.post("/api/queue/desconhecido/cancel")
    assert inexistente.status_code == 404


def test_stream_de_eventos_com_sessao(auth_client):
    with auth_client.stream("GET", "/api/events") as resposta:
        assert resposta.status_code == 200
        corpo = b"".join(resposta.iter_bytes())
    assert b'type": "status"' in corpo
