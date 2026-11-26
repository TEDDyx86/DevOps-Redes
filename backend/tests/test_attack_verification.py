import httpx
import pytest

from backend.app.attacks import verification


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


def test_live_alerts_separa_pending_e_firing():
    def handler(request):
        assert request.url.params["query"] == "ALERTS"
        return httpx.Response(200, json={"status": "success", "data": {"result": [
            {"metric": {"alertname": "HTTPLento", "alertstate": "pending", "service": "web-demo", "severity": "warning"}},
            {"metric": {"alertname": "TrafegoAnormal", "alertstate": "firing", "service": "dns", "severity": "warning"}},
        ]}})

    with httpx.Client(transport=httpx.MockTransport(handler), trust_env=False) as client:
        state = verification.live_alerts(client, "http://prom:9090")
    assert state["available"] is True
    assert state["pending"] == ["HTTPLento"]
    assert state["firing"] == ["TrafegoAnormal"]
    summary = verification.summarize_live(["HTTPLento", "TrafegoAnormal", "DNSIndisponivel"], state)
    assert summary == {
        "available": True,
        "pending": ["HTTPLento"],
        "fired": ["TrafegoAnormal"],
        "missing": ["DNSIndisponivel"],
    }


def test_summarize_live_sem_prometheus():
    assert verification.summarize_live(["HTTPLento"], None) == {
        "available": False,
        "pending": [],
        "fired": [],
        "missing": ["HTTPLento"],
    }
