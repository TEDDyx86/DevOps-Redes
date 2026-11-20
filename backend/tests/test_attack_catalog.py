import pytest

from backend.app.attacks.catalog import catalog, clean_params, expected_alerts, SPECS


def test_catalogo_tem_os_onze_ataques():
    ids = [ataque["id"] for ataque in catalog()]
    assert ids == [
        "bruteforce-servico",
        "bruteforce-painel",
        "sobrecarga-http",
        "lentidao-http",
        "indisponibilidade-http",
        "varredura-404",
        "flood-dns",
        "flood-smtp",
        "flood-postgres",
        "adulteracao-config",
        "interrupcao-servico",
    ]


def test_cada_ataque_tem_metadados_e_alertas_esperados():
    for ataque in catalog():
        assert ataque["name"] and ataque["target"] and ataque["description"]
        assert ataque["params"]
        if ataque["id"] not in ("interrupcao-servico", "varredura-404"):
            assert ataque["expected_alerts"], ataque["id"]


def test_catalogo_retorna_copia_independente():
    copia = catalog()
    copia[0]["name"] = "alterado"
    assert catalog()[0]["name"] != "alterado"


def test_parametros_recebem_defaults_e_rejeitam_invalidos():
    assert clean_params("bruteforce-servico", None) == {"tentativas": 12}
    assert clean_params("sobrecarga-http", {"taxa": 80}) == {"taxa": 80, "duracao": 45}
    with pytest.raises(ValueError):
        clean_params("bruteforce-servico", {"tentativas": 1000})
    with pytest.raises(ValueError):
        clean_params("bruteforce-servico", {"tentativas": True})
    with pytest.raises(ValueError):
        clean_params("bruteforce-servico", {"desconhecido": 1})
    with pytest.raises(ValueError):
        clean_params("nao-existe", {})
    with pytest.raises(ValueError):
        clean_params("interrupcao-servico", {"alvo": "prometheus"})
    assert clean_params("interrupcao-servico", {"alvo": "dns"})["alvo"] == "dns"


def test_alertas_esperados_por_ataque():
    assert expected_alerts("flood-dns") == ["TrafegoAnormal"]
    assert expected_alerts("flood-postgres") == ["TrafegoAnormal"]
    assert expected_alerts("lentidao-http") == ["HTTPLento"]
    assert expected_alerts("adulteracao-config") == ["ConfiguracaoAlterada"]
    assert expected_alerts("varredura-404") == []
    assert expected_alerts("interrupcao-servico") == []
    interrupcao = next(item for item in catalog() if item["id"] == "interrupcao-servico")
    assert interrupcao["expected_alerts_by_target"] == {
        "dns": ["DNSIndisponivel"],
        "smtp": ["SMTPIndisponivel"],
        "web-demo": ["HTTPIndisponivel"],
        "postgres": ["PostgreSQLIndisponivel"],
    }
    assert set(SPECS) == {a["id"] for a in catalog()}
