"""Catálogo dos ataques do painel: metadados, parâmetros e alertas esperados."""
import copy

CATALOG = [
    {
        "id": "bruteforce-servico",
        "name": "Força bruta no serviço",
        "target": "web-demo (:8011)",
        "description": "Tentativas de POST /mode com token inválido; desperta AutenticacaoServicoSuspeita.",
        "params": [{"name": "tentativas", "type": "int", "default": 12, "min": 6, "max": 60}],
        "expected_alerts": ["AutenticacaoServicoSuspeita"],
    },
    {
        "id": "bruteforce-painel",
        "name": "Força bruta no painel",
        "target": "dashboard (:8000)",
        "description": "Logins com senha errada em /api/auth/login; desperta AutenticacaoSuspeita.",
        "params": [{"name": "tentativas", "type": "int", "default": 8, "min": 6, "max": 40}],
        "expected_alerts": ["AutenticacaoSuspeita"],
    },
    {
        "id": "sobrecarga-http",
        "name": "Sobrecarga HTTP na loja",
        "target": "web-demo (:8011)",
        "description": "Rajada concorrente de GET /work na loja para elevar a taxa req/s e despertar TrafegoAnormal.",
        "params": [
            {"name": "taxa", "type": "int", "default": 60, "min": 10, "max": 200},
            {"name": "duracao", "type": "int", "default": 45, "min": 20, "max": 90},
        ],
        "expected_alerts": ["TrafegoAnormal"],
    },
    {
        "id": "lentidao-http",
        "name": "Degradação / Latência HTTP",
        "target": "web-demo (:8011)",
        "description": "Ativa modo slow (+850 ms) na loja via POST /mode; desperta HTTPLento e restaura ao normal.",
        "params": [{"name": "duracao", "type": "int", "default": 45, "min": 30, "max": 120}],
        "expected_alerts": ["HTTPLento"],
    },
    {
        "id": "indisponibilidade-http",
        "name": "Indisponibilidade da loja",
        "target": "web-demo (:8011)",
        "description": "Modo offline (HTTP 503) via POST /mode; sondas HTTP falham e despertam HTTPIndisponivel.",
        "params": [{"name": "duracao", "type": "int", "default": 45, "min": 20, "max": 120}],
        "expected_alerts": ["HTTPIndisponivel"],
    },
    {
        "id": "varredura-404",
        "name": "Varredura de rotas (Erros 404)",
        "target": "web-demo (:8011)",
        "description": "Simula scanner de endpoints inexistentes (/api/products/...) para gerar erros 4xx reais no dashboard.",
        "params": [{"name": "requisicoes", "type": "int", "default": 60, "min": 10, "max": 300}],
        "expected_alerts": [],
    },
    {
        "id": "flood-dns",
        "name": "Flood DNS",
        "target": "dns (:1053)",
        "description": "Rajada controlada de consultas UDP contra o CoreDNS para despertar TrafegoAnormal.",
        "params": [{"name": "duracao", "type": "int", "default": 60, "min": 30, "max": 90}],
        "expected_alerts": ["TrafegoAnormal"],
    },
    {
        "id": "flood-smtp",
        "name": "Flood SMTP",
        "target": "smtp (:2525)",
        "description": "Envio controlado de mensagens contra o servidor SMTP local para despertar TrafegoAnormal.",
        "params": [{"name": "duracao", "type": "int", "default": 60, "min": 30, "max": 90}],
        "expected_alerts": ["TrafegoAnormal"],
    },
    {
        "id": "flood-postgres",
        "name": "Flood de consultas SQL",
        "target": "postgres (:5432)",
        "description": "Rajada controlada de consultas no banco PostgreSQL da loja para despertar TrafegoAnormal.",
        "params": [{"name": "duracao", "type": "int", "default": 60, "min": 30, "max": 90}],
        "expected_alerts": ["TrafegoAnormal"],
    },
    {
        "id": "adulteracao-config",
        "name": "Adulteração de configuração",
        "target": "./infra (host)",
        "description": "Altera arquivo monitorado pela integridade (aprovar referência antes na aba Segurança) e restaura ao final.",
        "params": [
            {
                "name": "arquivo",
                "type": "str",
                "options": ["infra/dns/Corefile", "infra/prometheus.yml", "infra/alertmanager.yml"],
                "default": "infra/dns/Corefile",
            },
            {"name": "duracao", "type": "int", "default": 50, "min": 35, "max": 120},
        ],
        "expected_alerts": ["ConfiguracaoAlterada"],
    },
    {
        "id": "interrupcao-servico",
        "name": "Interrupção de serviço",
        "target": "docker compose",
        "description": "Para temporariamente o container escolhido via Docker API e reinicia automaticamente ao final.",
        "params": [
            {
                "name": "alvo",
                "type": "str",
                "options": ["dns", "smtp", "web-demo", "postgres"],
                "default": "dns",
            },
            {"name": "duracao", "type": "int", "default": 60, "min": 30, "max": 180},
        ],
        "expected_alerts": [],
        "expected_alerts_by_target": {
            "dns": ["DNSIndisponivel"],
            "smtp": ["SMTPIndisponivel"],
            "web-demo": ["HTTPIndisponivel"],
            "postgres": ["PostgreSQLIndisponivel"],
        },
    },
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
