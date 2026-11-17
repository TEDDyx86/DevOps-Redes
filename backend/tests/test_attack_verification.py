import httpx
import pytest

from demo.attacks import verification


def transport(payload, status=200):
    def handler(request):
        assert request.url.params["query"] == 'ALERTS{alertstate="firing"}'
        return httpx.Response(status, json=payload)
    return httpx.MockTransport(handler)


def test_alertas_firing_sao_extraidos_da_resposta():
    payload = {"status": "success", "data": {"result": [
        {"metric": {"alertname": "TrafegoAnormal", "alertstate": "firing"}},
        {"metric": {"alertname": "AutenticacaoSuspeita", "alertstate": "firing"}},
    ]}}
    with httpx.Client(transport=transport(payload), trust_env=False) as client:
        assert verification.firing_alerts(client, "http://prom:9090") == {"TrafegoAnormal", "AutenticacaoSuspeita"}


def test_resposta_de_erro_levanta_excecao():
    with httpx.Client(transport=transport({"status": "error", "error": "bad query"}), trust_env=False) as client:
        with pytest.raises(RuntimeError):
            verification.firing_alerts(client, "http://prom:9090")


def test_verify_com_para_de_alertas():
    resultado = verification.verify(["TrafegoAnormal", "AutenticacaoSuspeita"], {"TrafegoAnormal"})
    assert resultado == {"available": True, "fired": ["TrafegoAnormal"], "missing": ["AutenticacaoSuspeita"]}


def test_verify_sem_dados_nunca_inventa_sucesso():
    resultado = verification.verify(["TrafegoAnormal"], None)
    assert resultado == {"available": False, "fired": [], "missing": ["TrafegoAnormal"]}


def test_verify_sem_alertas_esperados():
    assert verification.verify([], {"AutenticacaoSuspeita"}) == {"available": True, "fired": [], "missing": []}
