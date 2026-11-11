"""Catálogo dos ataques do painel: metadados, parâmetros e alertas esperados."""
import copy

CATALOG = [
    {"id": "bruteforce-servico", "name": "Força bruta no serviço", "target": "web-demo (:8001)",
     "description": "Tentativas de POST /mode com token inválido; desperta AutenticacaoServicoSuspeita.",
     "params": [{"name": "tentativas", "type": "int", "default": 12, "min": 6, "max": 60}],
     "expected_alerts": ["AutenticacaoServicoSuspeita"]},
    {"id": "bruteforce-painel", "name": "Força bruta no painel", "target": "dashboard (:8000)",
     "description": "Logins com senha errada em /api/auth/login; desperta AutenticacaoSuspeita.",
     "params": [{"name": "tentativas", "type": "int", "default": 8, "min": 6, "max": 40}],
     "expected_alerts": ["AutenticacaoSuspeita"]},
    {"id": "sobrecarga-http", "name": "Sobrecarga HTTP em /work", "target": "web-demo (:8001)",
     "description": "Maré de requisições GET /work a partir do host; CPU e tráfego acima do normal.",
     "params": [{"name": "taxa", "type": "int", "default": 50, "min": 10, "max": 200},
                {"name": "duracao", "type": "int", "default": 20, "min": 10, "max": 60}],
     "expected_alerts": ["RecursoCPUElevada", "TrafegoAnormal"]},
    {"id": "indisponibilidade-http", "name": "Indisponibilidade do web-demo", "target": "web-demo (:8001)",
     "description": "Modo offline via POST /mode (token do operador do .env); sondas HTTP falham.",
     "params": [{"name": "duracao", "type": "int", "default": 45, "min": 20, "max": 120}],
     "expected_alerts": ["HTTPIndisponivel"]},
    {"id": "flood-dns", "name": "Flood DNS", "target": "dns (:1053)",
     "description": "Job de carga limitada da plataforma contra o DNS; tráfego acima da referência.",
     "params": [{"name": "duracao", "type": "int", "default": 60, "min": 30, "max": 90}],
     "expected_alerts": ["TrafegoAnormal"]},
    {"id": "flood-smtp", "name": "Flood SMTP", "target": "smtp (:2525)",
     "description": "Job de carga limitada da plataforma contra o SMTP; tráfego acima da referência.",
     "params": [{"name": "duracao", "type": "int", "default": 60, "min": 30, "max": 90}],
     "expected_alerts": ["TrafegoAnormal"]},
    {"id": "adulteracao-config", "name": "Adulteração de configuração", "target": "./infra (host)",
     "description": "Altera arquivo monitorado pela integridade e restaura os bytes originais ao final.",
     "params": [{"name": "arquivo", "type": "str", "default": "infra/dns/Corefile"},
                {"name": "duracao", "type": "int", "default": 45, "min": 20, "max": 120}],
     "expected_alerts": ["ConfiguracaoAlterada"]},
    {"id": "interrupcao-servico", "name": "Interrupção de serviço", "target": "docker compose",
     "description": "docker compose stop no serviço escolhido e start ao final.",
     "params": [{"name": "alvo", "type": "str", "options": ["dns", "smtp", "web-demo", "postgres"], "default": "dns"},
                {"name": "duracao", "type": "int", "default": 60, "min": 30, "max": 180}],
     "expected_alerts": []},
]

SPECS = {ataque["id"]: ataque["params"] for ataque in CATALOG}


def catalog():
    return copy.deepcopy(CATALOG)


def expected_alerts(attack_id):
    for ataque in CATALOG:
        if ataque["id"] == attack_id:
            return list(ataque["expected_alerts"])
    raise ValueError("ataque_desconhecido")


def clean_params(attack_id, params):
    specs = SPECS.get(attack_id)
    if specs is None:
        raise ValueError("ataque_desconhecido")
    cleaned = {spec["name"]: spec["default"] for spec in specs}
    for key, value in (params or {}).items():
        spec = next((item for item in specs if item["name"] == key), None)
        if spec is None:
            raise ValueError("parametro_desconhecido")
        if spec["type"] == "int":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("parametro_invalido")
            if value < spec["min"] or value > spec["max"]:
                raise ValueError("parametro_fora_da_faixa")
        else:
            if not isinstance(value, str) or not value:
                raise ValueError("parametro_invalido")
            if "options" in spec and value not in spec["options"]:
                raise ValueError("parametro_invalido")
        cleaned[key] = value
    return cleaned
