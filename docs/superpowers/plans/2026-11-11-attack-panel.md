# Painel de Ataques — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Painel separado (porta 8002, somente localhost) para disparar os 8 ataques do catálogo contra o laboratório, com visualização de fases/progresso/log ao vivo e verificação final do alerta no Prometheus.

**Architecture:** Serviço FastAPI no host (`scripts/attack_panel/`) que serve uma página estática sem build, expõe API + SSE, e executa ataques de uma fila (um por vez) em thread de background com runners reversíveis. A verificação lê `ALERTS{alertstate="firing"}` do Prometheus; o painel nunca publica métricas.

**Tech Stack:** Python (FastAPI, uvicorn, httpx) já presentes no ambiente; página estática vanilla JS/CSS; CLI `docker compose` via subprocesso para o ataque 8; lock de instância única via `scripts.scan_vulnerabilities.exclusive_lock`.

**Spec:** `docs/superpowers/specs/2026-11-11-attack-panel-design.md`

## Global Constraints

- Bind somente `127.0.0.1` (constante `HOST = "127.0.0.1"` em `server.py`; nunca `0.0.0.0`).
- O painel nunca publica métricas no Prometheus; dados ausentes na verificação resultam em `available: false` (⚠️), nunca sucesso inventado.
- Alertas reais e seus `for:` (de `infra/alerts.yml`): `AutenticacaoSuspeita` 10s, `ConfiguracaoAlterada` 15s, `HTTPIndisponivel`/`DNSIndisponivel`/`SMTPIndisponivel`/`PostgreSQLIndisponivel` 15s, `AutenticacaoServicoSuspeita`/`TrafegoAnormal`/`RecursoCPUElevada` 30s. Os runners aguardam o necessário; a verificação tenta até 6 vezes com 5 s de intervalo.
- Nada em `infra/alerts.yml`, `compose.yaml` ou frontend React muda neste plano (painel totalmente separado do dashboard).
- Rodar testes a partir da raiz do repositório: `python -m pytest backend/tests/... -v`.
- PowerShell 5.1: não usar `curl.exe` com JSON; scripts Python fazem o HTTP.
- Commits convencionais (`feat:`, `test:`, `docs:`, `fix:`).
- Nenhum ataque toca em volumes de dados; efeitos sempre reversíveis; textos de erro de runner não expõem segredos (motor registra `type(error).__name__`).

---

### Task 1: Catálogo de ataques

**Files:**
- Create: `scripts/attack_panel/__init__.py` (vazio)
- Create: `scripts/attack_panel/catalog.py`
- Test: `backend/tests/test_attack_catalog.py`

**Interfaces:**
- Consumes: nada (folha).
- Produces: `CATALOG` (lista de dicts com `id`, `name`, `target`, `description`, `params`, `expected_alerts`); `SPECS: dict[str, list[dict]]`; `catalog() -> list[dict]` (cópia profunda); `expected_alerts(attack_id) -> list[str]`; `clean_params(attack_id, params) -> dict` (levanta `ValueError`).

- [ ] **Step 1: Write the failing test**

```python
import pytest

from scripts.attack_panel.catalog import catalog, clean_params, expected_alerts, SPECS


def test_catalogo_tem_os_oito_ataques_combinados():
    ids = [ataque["id"] for ataque in catalog()]
    assert ids == ["bruteforce-servico", "bruteforce-painel", "sobrecarga-http",
                   "indisponibilidade-http", "flood-dns", "flood-smtp",
                   "adulteracao-config", "interrupcao-servico"]


def test_cada_ataque_tem_metadados_e_alertas_esperados():
    for ataque in catalog():
        assert ataque["name"] and ataque["target"] and ataque["description"]
        assert ataque["params"]
        if ataque["id"] != "interrupcao-servico":
            assert ataque["expected_alerts"], ataque["id"]


def test_catalogo_retorna_copia_independente():
    copia = catalog()
    copia[0]["name"] = "alterado"
    assert catalog()[0]["name"] != "alterado"


def test_parametros_recebem_defaults_e_rejeitam_invalidos():
    assert clean_params("bruteforce-servico", None) == {"tentativas": 12}
    assert clean_params("sobrecarga-http", {"taxa": 80}) == {"taxa": 80, "duracao": 20}
    with pytest.raises(ValueError): clean_params("bruteforce-servico", {"tentativas": 1000})
    with pytest.raises(ValueError): clean_params("bruteforce-servico", {"tentativas": True})
    with pytest.raises(ValueError): clean_params("bruteforce-servico", {"desconhecido": 1})
    with pytest.raises(ValueError): clean_params("nao-existe", {})
    with pytest.raises(ValueError): clean_params("interrupcao-servico", {"alvo": "prometheus"})
    assert clean_params("interrupcao-servico", {"alvo": "dns"})["alvo"] == "dns"


def test_alertas_esperados_por_ataque():
    assert expected_alerts("flood-dns") == ["TrafegoAnormal"]
    assert expected_alerts("adulteracao-config") == ["ConfiguracaoAlterada"]
    assert expected_alerts("interrupcao-servico") == []
    assert set(SPECS) == {a["id"] for a in catalog()}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_attack_catalog.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'scripts.attack_panel'`

- [ ] **Step 3: Write minimal implementation**

`scripts/attack_panel/__init__.py`: arquivo vazio.

`scripts/attack_panel/catalog.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_attack_catalog.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/attack_panel/__init__.py scripts/attack_panel/catalog.py backend/tests/test_attack_catalog.py
git commit -m "feat: catalogo dos oito ataques do painel"
```

---

### Task 2: Verificação de alertas no Prometheus

**Files:**
- Create: `scripts/attack_panel/verification.py`
- Test: `backend/tests/test_attack_verification.py`

**Interfaces:**
- Consumes: cliente `httpx.Client` (injetado; o runner/servidor cria via `runners.make_client`).
- Produces: `firing_alerts(client, base_url) -> set[str]` (levanta exceção em falha); `verify(expected, firing) -> {"available": bool, "fired": list[str], "missing": list[str]}` (`firing=None` ⇒ `available: False`).

- [ ] **Step 1: Write the failing test**

```python
import httpx
import pytest

from scripts.attack_panel import verification


def transport(payload, status=200):
    def handler(request):
        assert 'ALERTS{alertstate="firing"}' in str(request.url)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_attack_verification.py -v`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

`scripts/attack_panel/verification.py`:

```python
"""Leitura da API do Prometheus para verificar alertas em firing."""
def firing_alerts(client, base_url):
    response = client.get(base_url.rstrip("/") + "/api/v1/query", params={"query": 'ALERTS{alertstate="firing"}'})
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "success":
        raise RuntimeError("prometheus_query_failed")
    return {item["metric"]["alertname"] for item in payload.get("data", {}).get("result", [])}


def verify(expected, firing):
    if firing is None:
        return {"available": False, "fired": [], "missing": list(expected)}
    return {"available": True,
            "fired": [alert for alert in expected if alert in firing],
            "missing": [alert for alert in expected if alert not in firing]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_attack_verification.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/attack_panel/verification.py backend/tests/test_attack_verification.py
git commit -m "feat: verificacao de alertas via API do Prometheus"
```

---

### Task 3: Motor de execução (fila, fases, eventos, interrupção)

**Files:**
- Create: `scripts/attack_panel/engine.py`
- Test: `backend/tests/test_attack_engine.py`

**Interfaces:**
- Consumes: `catalog.clean_params`, `catalog.expected_alerts` (Task 1).
- Produces: `Cancelled` (exceção); `AttackContext` com `cancelled() -> bool`, `check_cancelled()` (levanta `Cancelled`), `request_cancel()`, `set_expected_alerts(list)`, `log(str)`, `progress(**counters)`, `snapshot() -> {"counters": dict, "expected_alerts": list}`; `Engine(runners: dict[str, callable(ctx, params)], verifier: callable(expected, cancelled) -> dict)` com `enqueue(attack_id, params=None) -> dict`, `cancel(entry_id) -> dict|None`, `snapshot() -> {"current", "queue", "history"}`, `recent_events(limit=200) -> list[dict]`, `subscribe() -> generator[str]` (SSE), `stop()`.

- [ ] **Step 1: Write the failing test**

```python
import time

from scripts.attack_panel.engine import Cancelled, Engine


def wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def verify_ok(expected, cancelled):
    assert callable(cancelled)
    return {"available": True, "fired": list(expected), "missing": []}


def make_engine(runner):
    return Engine(runners={"bruteforce-servico": runner}, verifier=verify_ok)


def test_fila_executa_um_ataque_por_vez_com_fases_e_verificacao():
    eventos = []
    def runner(ctx, params):
        ctx.set_expected_alerts(["AutenticacaoServicoSuspeita"])
        ctx.log("executando")
        ctx.progress(tentativas=1)
    engine = make_engine(runner)
    engine.enqueue("bruteforce-servico")
    assert wait_for(lambda: any(e.get("status") == "concluido" for e in engine.recent_events(500)))
    statuses = [e["status"] for e in engine.recent_events(500) if e["type"] == "status"]
    assert "agendado" in statuses and "executando" in statuses and "verificando" in statuses and "concluido" in statuses
    assert "executando" in [e["message"] for e in engine.recent_events(500) if e["type"] == "log"]
    historico = engine.snapshot()["history"]
    assert historico[0]["verification"]["fired"] == ["AutenticacaoServicoSuspeita"]
    assert historico[0]["counters"] == {"tentativas": 1}
    engine.stop()


def test_entrada_desconhecida_e_parametros_invalidos_sao_rejeitados():
    engine = make_engine(lambda ctx, params: None)
    try:
        engine.enqueue("ataque-inexistente")
        raise AssertionError("deveria falhar")
    except ValueError as error:
        assert "ataque_desconhecido" in str(error)
    try:
        engine.enqueue("bruteforce-servico", {"tentativas": 9999})
        raise AssertionError("deveria falhar")
    except ValueError as error:
        assert "parametro_fora_da_faixa" in str(error)
    engine.stop()


def test_cancelamento_da_fila_remove_entrada_sem_executar():
    liberado = time.monotonic() + 10
    executados = []
    def runner(ctx, params):
        executados.append(1)
    engine = make_engine(runner)
    primeira = engine.enqueue("bruteforce-servico")
    assert wait_for(lambda: engine.snapshot()["current"] is not None)
    segunda = engine.enqueue("bruteforce-servico")
    assert engine.cancel(segunda["entry_id"]) is not None
    assert engine.cancel(segunda["entry_id"]) is None
    assert engine.cancel("inexistente") is None
    assert wait_for(lambda: engine.snapshot()["current"] is None)
    assert len(executados) == 1
    engine.stop()


def test_interrupcao_do_ataque_em_execucao_resulta_em_interrompido():
    def runner(ctx, params):
        while not ctx.cancelled():
            ctx.progress(segundos=1)
            time.sleep(0.02)
        raise Cancelled()
    engine = make_engine(runner)
    entrada = engine.enqueue("bruteforce-servico")
    assert wait_for(lambda: engine.snapshot()["current"] is not None)
    engine.cancel(entrada["entry_id"])
    assert wait_for(lambda: engine.snapshot()["current"] is None)
    assert engine.snapshot()["history"][0]["status"] == "interrompido"
    engine.stop()


def test_falha_do_runner_registra_tipo_do_erro_sem_expor_detalhes():
    def runner(ctx, params):
        raise RuntimeError("detalhe sensível do erro")
    engine = make_engine(runner)
    engine.enqueue("bruteforce-servico")
    assert wait_for(lambda: engine.snapshot()["current"] is None)
    historico = engine.snapshot()["history"][0]
    assert historico["status"] == "falhou"
    assert historico["error"] == "RuntimeError"
    corpo = str(engine.recent_events(500))
    assert "detalhe sensível" not in corpo
    engine.stop()


def test_subscribe_reproduz_eventos_anteriores_e_cancel remove_assinante():
    engine = make_engine(lambda ctx, params: ctx.log("linha"))
    engine.enqueue("bruteforce-servico")
    assert wait_for(lambda: engine.snapshot()["current"] is None)
    stream = engine.subscribe()
    primeiro = next(stream)
    assert primeiro.startswith("data: ") and "agendado" in primeiro
    engine.stop()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_attack_engine.py -v`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

`scripts/attack_panel/engine.py`:

```python
"""Motor do painel de ataques: fila com um ataque por vez, fases e eventos."""
import copy
import json
import queue
import threading
import time
import uuid
from datetime import datetime, timezone

from scripts.attack_panel import catalog

FINAL = ("concluido", "interrompido", "falhou")


class Cancelled(Exception):
    """Sinal interno de interrupção solicitada."""


def _now():
    return datetime.now(timezone.utc).isoformat()


def _format(event):
    return "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"


class AttackContext:
    def __init__(self, publish):
        self._publish = publish
        self._lock = threading.Lock()
        self.expected_alerts = []
        self.counters = {}
        self._cancel = threading.Event()

    def cancelled(self):
        return self._cancel.is_set()

    def check_cancelled(self):
        if self.cancelled():
            raise Cancelled()

    def request_cancel(self):
        self._cancel.set()

    def set_expected_alerts(self, alerts):
        with self._lock:
            self.expected_alerts = list(alerts)

    def log(self, message):
        self._publish("log", message=str(message))

    def progress(self, **counters):
        with self._lock:
            self.counters.update(counters)
            snapshot = dict(self.counters)
        self._publish("progress", counters=snapshot)

    def snapshot(self):
        with self._lock:
            return {"counters": dict(self.counters), "expected_alerts": list(self.expected_alerts)}


class Engine:
    def __init__(self, runners, verifier):
        self._runners = runners
        self._verifier = verifier
        self._lock = threading.Lock()
        self._wakeup = threading.Event()
        self._stopping = threading.Event()
        self._queue = []
        self._current = None
        self._contexts = {}
        self._history = []
        self._events = []
        self._seq = 0
        self._subscribers = []
        self._worker = threading.Thread(target=self._loop, name="attack-engine", daemon=True)
        self._worker.start()

    def enqueue(self, attack_id, params=None):
        cleaned = catalog.clean_params(attack_id, params)
        entry = {"entry_id": uuid.uuid4().hex, "attack": attack_id, "status": "agendado",
                 "params": cleaned, "expected_alerts": catalog.expected_alerts(attack_id),
                 "counters": {}, "verification": None, "error": None,
                 "started_at": None, "ended_at": None}
        with self._lock:
            self._queue.append(entry)
        self._publish("status", entry_id=entry["entry_id"], attack=attack_id, status="agendado", message="Ataque na fila")
        self._wakeup.set()
        return self._view(entry)

    def cancel(self, entry_id):
        with self._lock:
            current = self._current
            if current is not None and current["entry_id"] == entry_id:
                context = self._contexts.get(entry_id)
            else:
                context = None
                for index, entry in enumerate(self._queue):
                    if entry["entry_id"] == entry_id:
                        del self._queue[index]
                        break
                else:
                    return None
        if context is not None:
            context.request_cancel()
        self._publish("status", entry_id=entry_id, status="interrompendo", message="Interrupção solicitada")
        return {"entry_id": entry_id, "status": "interrompendo"}

    def snapshot(self):
        with self._lock:
            return {"current": self._view(self._current) if self._current else None,
                    "queue": [self._view(entry) for entry in self._queue],
                    "history": [dict(entry) for entry in self._history]}

    def recent_events(self, limit=200):
        with self._lock:
            return copy.deepcopy(self._events[-limit:])

    def subscribe(self):
        mailbox = queue.Queue()
        with self._lock:
            backlog = list(self._events)
            self._subscribers.append(mailbox)

        def stream():
            try:
                for event in backlog:
                    yield _format(event)
                while True:
                    try:
                        event = mailbox.get(timeout=15)
                    except queue.Empty:
                        yield ": ping\n\n"
                        continue
                    yield _format(event)
            finally:
                with self._lock:
                    if mailbox in self._subscribers:
                        self._subscribers.remove(mailbox)

        return stream()

    def stop(self):
        self._stopping.set()
        self._wakeup.set()
        self._worker.join(timeout=5)

    # ---- interno ------------------------------------------------------
    def _publish(self, event_type, **payload):
        with self._lock:
            self._seq += 1
            event = {"seq": self._seq, "type": event_type, **payload}
            self._events.append(event)
            if len(self._events) > 500:
                self._events.pop(0)
            for mailbox in self._subscribers:
                mailbox.put(event)

    def _view(self, entry):
        view = dict(entry)
        context = self._contexts.get(entry["entry_id"])
        if context is not None:
            state = context.snapshot()
            view["counters"] = state["counters"]
            view["expected_alerts"] = state["expected_alerts"]
        return view

    def _loop(self):
        while not self._stopping.is_set():
            self._wakeup.wait(0.2)
            self._wakeup.clear()
            with self._lock:
                if self._current is None and self._queue:
                    entry = self._queue.pop(0)
                    self._current = entry
                    entry["status"] = "preparando"
                    entry["started_at"] = _now()
                else:
                    entry = None
            if entry is not None:
                self._run(entry)

    def _run(self, entry):
        attack_id = entry["attack"]
        context = AttackContext(lambda event_type, **payload: self._publish(event_type, entry_id=entry["entry_id"], attack=attack_id, **payload))
        with self._lock:
            self._contexts[entry["entry_id"]] = context
            entry["status"] = "executando"
        self._publish("status", entry_id=entry["entry_id"], attack=attack_id, status="executando", message="Executando ataque")
        try:
            self._runners[attack_id](context, dict(entry["params"]))
            with self._lock:
                entry["status"] = "verificando"
            self._publish("status", entry_id=entry["entry_id"], status="verificando", message="Verificando alertas no Prometheus")
            result = self._verifier(context.snapshot()["expected_alerts"], context.cancelled)
            with self._lock:
                entry["verification"] = result
            self._publish("verification", entry_id=entry["entry_id"], data=result)
            entry["status"] = "concluido"
        except Cancelled:
            entry["status"] = "interrompido"
        except Exception as error:
            entry["status"] = "falhou"
            entry["error"] = type(error).__name__
        finally:
            state = context.snapshot()
            entry["counters"] = state["counters"]
            with self._lock:
                entry["ended_at"] = _now()
                self._history.append(entry)
                if len(self._history) > 10:
                    self._history.pop(0)
                self._current = None
                self._contexts.pop(entry["entry_id"], None)
            self._publish("status", entry_id=entry["entry_id"], attack=attack_id, status=entry["status"], message="Fim do ataque")
            self._wakeup.set()
```

Nota de design (para o executor): `_publish` nunca é chamado enquanto `self._lock` está retido — o lock não é reentrante. Toda mutação de fila/entrada acontece sob o lock e a publicação logo depois, fora dele.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_attack_engine.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/attack_panel/engine.py backend/tests/test_attack_engine.py
git commit -m "feat: motor do painel com fila, fases, eventos e interrupcao"
```

---

### Task 4: Runners de autenticação e HTTP (ataques 1–4)

**Files:**
- Create: `scripts/attack_panel/runners.py`
- Test: `backend/tests/test_attack_runners.py`

**Interfaces:**
- Consumes: `Cancelled` de `engine` (Task 3); `verification.firing_alerts` (Task 2); `.env` (`LAB_TOKEN`).
- Produces: funções `bruteforce_servico(ctx, params)`, `bruteforce_painel(ctx, params)`, `sobrecarga_http(ctx, params)`, `indisponibilidade_http(ctx, params)`; helpers reusados pela Task 5: `make_client() -> httpx.Client`, `lab_token() -> str`, `_hold(ctx, seconds)`; constantes `ROOT`, `DEMO_BASE`, `PANEL_BASE`, `PROMETHEUS_BASE`, `BURST_INTERVAL`, `BRUTEFORCE_HOLD`, `SOBRECARGA_HOLD`.

- [ ] **Step 1: Write the failing test**

```python
import threading
import time

import httpx

from scripts.attack_panel import runners
from scripts.attack_panel.engine import Cancelled


class FakeCtx:
    def __init__(self):
        self.expected = []
        self.counters = {}
        self.logs = []
        self._cancel = threading.Event()

    def cancelled(self): return self._cancel.is_set()

    def check_cancelled(self):
        if self._cancel.is_set():
            raise Cancelled()

    def request_cancel(self): self._cancel.set()

    def set_expected_alerts(self, alerts): self.expected = list(alerts)

    def log(self, message): self.logs.append(str(message))

    def progress(self, **counters): self.counters.update(counters)


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
    assert ctx.counters == {"tentativas": 6, "rejeitadas": 6}
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


def test_sobrecarga_http_dispara_mare_e_restaura_nada(monkeypatch):
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_attack_runners.py -v`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

`scripts/attack_panel/runners.py`:

```python
"""Runners dos ataques: efeitos controlados a partir do host, sempre reversíveis."""
import os
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from scripts.attack_panel.engine import Cancelled

ROOT = Path(__file__).resolve().parents[2]
DEMO_BASE = "http://localhost:8001"
PANEL_BASE = "http://localhost:8000"
PROMETHEUS_BASE = "http://localhost:9090"

BURST_INTERVAL = 0.15
BRUTEFORCE_HOLD = 40
SOBRECARGA_HOLD = 35


def make_client():
    return httpx.Client(timeout=5, trust_env=False)


def lab_token():
    values = dict(line.split("=", 1) for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
                  if "=" in line and not line.lstrip().startswith("#"))
    token = values.get("LAB_TOKEN", "")
    if not token:
        raise RuntimeError("LAB_TOKEN ausente no .env")
    return token


def _hold(ctx, seconds):
    deadline = time.monotonic() + seconds
    while True:
        ctx.check_cancelled()
        restante = max(0, int(deadline - time.monotonic()))
        ctx.progress(segundos_restantes=restante)
        if restante <= 0:
            return
        time.sleep(1)


def bruteforce_servico(ctx, params):
    tentativas = int(params["tentativas"])
    ctx.set_expected_alerts(["AutenticacaoServicoSuspeita"])
    feitas = rejeitadas = 0
    with make_client() as client:
        for index in range(tentativas):
            ctx.check_cancelled()
            started = time.perf_counter()
            try:
                response = client.post(DEMO_BASE + "/mode", json={"mode": "normal"},
                                       headers={"X-Lab-Token": "ataque-" + uuid.uuid4().hex[:12]})
                codigo = response.status_code
            except httpx.HTTPError:
                codigo = None
            feitas += 1
            rejeitadas += 1 if codigo == 401 else 0
            ctx.progress(tentativas=feitas, rejeitadas=rejeitadas)
            if index % 4 == 0:
                ctx.log(f"Tentativa {index + 1}/{tentativas}: " + (f"HTTP {codigo}" if codigo else "sem resposta"))
            espera = BURST_INTERVAL - (time.perf_counter() - started)
            if espera > 0:
                time.sleep(espera)
    ctx.log("Maré de tentativas concluída; aguardando janela de 1 minuto e o 'for: 30s' do alerta")
    _hold(ctx, BRUTEFORCE_HOLD)


def bruteforce_painel(ctx, params):
    tentativas = int(params["tentativas"])
    ctx.set_expected_alerts(["AutenticacaoSuspeita"])
    feitas = 0
    with make_client() as client:
        for index in range(tentativas):
            ctx.check_cancelled()
            started = time.perf_counter()
            try:
                response = client.post(PANEL_BASE + "/api/auth/login",
                                       json={"username": "admin", "password": "senha-errada-" + uuid.uuid4().hex[:12]})
                codigo = response.status_code
            except httpx.HTTPError:
                codigo = None
            feitas += 1
            ctx.progress(tentativas=feitas, rejeitadas=feitas if codigo == 401 else 0)
            if index % 4 == 0:
                ctx.log(f"Login {index + 1}/{tentativas}: " + (f"HTTP {codigo}" if codigo else "sem resposta"))
            espera = BURST_INTERVAL - (time.perf_counter() - started)
            if espera > 0:
                time.sleep(espera)
    ctx.log("Logins com senha errada concluídos; aguardando janela de falhas recentes e o 'for: 10s' do alerta")
    _hold(ctx, BRUTEFORCE_HOLD)


def sobrecarga_http(ctx, params):
    taxa = int(params["taxa"])
    duracao = int(params["duracao"])
    ctx.set_expected_alerts(["RecursoCPUElevada", "TrafegoAnormal"])
    workers = max(2, min(8, taxa // 5))
    stop = time.monotonic() + duracao
    shared = {"requisicoes": 0, "erros": 0}
    guard = threading.Lock()

    def worker(client):
        local = 0
        while time.monotonic() < stop:
            if ctx.cancelled():
                return
            try:
                response = client.get(DEMO_BASE + "/work")
                aceito = response.status_code < 500
            except httpx.HTTPError:
                aceito = False
            with guard:
                shared["requisicoes"] += 1
                if not aceito:
                    shared["erros"] += 1
                snapshot = dict(shared)
            ctx.progress(**snapshot)
            local += 1
            if local % 50 == 0:
                ctx.log(f"Maré em andamento: {snapshot['requisicoes']} requisições")

    clientes = [make_client() for _ in range(workers)]
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for future in [pool.submit(worker, client) for client in clientes]:
                future.result()
    finally:
        for client in clientes:
            client.close()
    if ctx.cancelled():
        raise Cancelled()
    ctx.log(f"Maré concluída: {shared['requisicoes']} requisições; aguardando 'for: 30s' dos alertas")
    _hold(ctx, SOBRECARGA_HOLD)


def indisponibilidade_http(ctx, params):
    duracao = int(params["duracao"])
    ctx.set_expected_alerts(["HTTPIndisponivel"])
    token = lab_token()
    with make_client() as client:
        response = client.post(DEMO_BASE + "/mode", json={"mode": "offline"}, headers={"X-Lab-Token": token})
        response.raise_for_status()
        ctx.log("Web-demo em modo offline; sondas HTTP do painel devem falhar")
        try:
            _hold(ctx, duracao)
        finally:
            restore = client.post(DEMO_BASE + "/mode", json={"mode": "normal"}, headers={"X-Lab-Token": token})
            if restore.status_code == 200:
                ctx.log("Modo normal restaurado")
            else:
                ctx.log(f"ATENÇÃO: restauração do modo falhou com HTTP {restore.status_code}; restaurar manualmente")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_attack_runners.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/attack_panel/runners.py backend/tests/test_attack_runners.py
git commit -m "feat: runners de forca bruta, sobrecarga e indisponibilidade"
```

---

### Task 5: Runners de tráfego, integridade e Docker (ataques 5–8)

**Files:**
- Modify: `scripts/attack_panel/runners.py` (acrescentar funções e `RUNNERS`)
- Test: `backend/tests/test_attack_runners.py` (acrescentar testes)

**Interfaces:**
- Consumes: `verification.firing_alerts` (Task 2); `scripts.lab_session.authenticate` (padrão dos scripts de verificação).
- Produces: `flood_dns`, `flood_smtp`, `adulteracao_config`, `interrupcao_servico` (mesma assinatura `fn(ctx, params)`); `RUNNERS: dict[str, callable]` com as oito chaves do catálogo; helper `_docker_compose(*arguments)`; constante `STOP_ALERTS`.

- [ ] **Step 1: Write the failing tests (acrescentar ao arquivo da Task 4)**

```python
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
    from scripts.attack_panel import catalog
    assert set(runners.RUNNERS) == {ataque["id"] for ataque in catalog.CATALOG}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_attack_runners.py -v`
Expected: os testes novos FAILAM com `AttributeError` (`flood_dns` etc. não existem)

- [ ] **Step 3: Write minimal implementation (acrescentar ao `runners.py`)**

Acrescentar ao topo do arquivo o import e as constantes:

```python
from scripts.attack_panel import verification
from scripts.lab_session import authenticate
```

E ao final:

```python
STOP_ALERTS = {"dns": "DNSIndisponivel", "smtp": "SMTPIndisponivel",
               "web-demo": "HTTPIndisponivel", "postgres": "PostgreSQLIndisponivel"}


def _docker_compose(*arguments):
    flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    return subprocess.run(["docker", "compose", *arguments], cwd=str(ROOT), check=True,
                          capture_output=True, timeout=90, **flags)


def _firing(client):
    try:
        return verification.firing_alerts(client, PROMETHEUS_BASE)
    except Exception:
        return set()


def _traffic_attack(ctx, service, duracao, expected):
    ctx.set_expected_alerts(expected)
    duracao = int(duracao)
    with make_client() as client:
        authenticate(client)
        response = client.post(PANEL_BASE + "/api/lab/traffic", headers={"X-Lab-Token": lab_token()},
                               json={"service": service, "duration": duracao})
        response.raise_for_status()
        ctx.log(f"Job de carga iniciado contra {service} por {duracao}s")
        try:
            while True:
                ctx.check_cancelled()
                job = client.get(PANEL_BASE + "/api/lab/traffic").json()
                if job.get("status") != "running":
                    break
                counts = job.get("services", {}).get(service, {})
                ctx.progress(tentativas=counts.get("attempted", 0), sucesso=counts.get("successful", 0),
                             falhas=counts.get("failed", 0))
                if expected[0] in _firing(client):
                    ctx.log(f"Alerta {expected[0]} em firing; encerrando execução para verificação")
                    break
                time.sleep(1)
        finally:
            final = client.get(PANEL_BASE + "/api/lab/traffic")
            try:
                status = final.json().get("status")
            except Exception:
                status = "desconhecido"
            if status == "running":
                client.request("DELETE", PANEL_BASE + "/api/lab/traffic")
                ctx.log("Job de carga cancelado no fim do ataque")
            else:
                ctx.log(f"Job de carga terminou com status {status}")


def flood_dns(ctx, params):
    _traffic_attack(ctx, "dns", params["duracao"], ["TrafegoAnormal"])


def flood_smtp(ctx, params):
    _traffic_attack(ctx, "smtp", params["duracao"], ["TrafegoAnormal"])


def adulteracao_config(ctx, params):
    relativo = str(params["arquivo"])
    duracao = int(params["duracao"])
    ctx.set_expected_alerts(["ConfiguracaoAlterada"])
    raiz = ROOT.resolve()
    caminho = (raiz / relativo).resolve()
    if not str(caminho).startswith(str(raiz / "infra") + os.sep):
        raise ValueError("arquivo_fora_do_escopo")
    if not caminho.is_file():
        raise FileNotFoundError(relativo)
    original = caminho.read_bytes()
    caminho.write_bytes(original + b"\n# linha adulterada pelo painel de ataques\n")
    ctx.log(f"Arquivo {relativo} adulterado; coletor de integridade deve detectar a mudança")
    try:
        _hold(ctx, duracao)
    finally:
        caminho.write_bytes(original)
        ctx.log(f"Arquivo {relativo} restaurado byte a byte")


def interrupcao_servico(ctx, params):
    alvo = str(params["alvo"])
    duracao = int(params["duracao"])
    if alvo not in STOP_ALERTS:
        raise ValueError("alvo_invalido")
    ctx.set_expected_alerts([STOP_ALERTS[alvo]])
    _docker_compose("stop", alvo)
    ctx.log(f"Serviço {alvo} parado; sondas correspondentes devem falhar")
    try:
        deadline = time.monotonic() + max(duracao, 90)
        with make_client() as client:
            while time.monotonic() < deadline:
                ctx.check_cancelled()
                if STOP_ALERTS[alvo] in _firing(client):
                    ctx.log(f"Alerta {STOP_ALERTS[alvo]} em firing; restaurando serviço")
                    break
                ctx.progress(segundos_restantes=max(0, int(deadline - time.monotonic())))
                time.sleep(1)
    finally:
        _docker_compose("start", alvo)
        ctx.log(f"Serviço {alvo} reiniciado")


RUNNERS = {
    "bruteforce-servico": bruteforce_servico,
    "bruteforce-painel": bruteforce_painel,
    "sobrecarga-http": sobrecarga_http,
    "indisponibilidade-http": indisponibilidade_http,
    "flood-dns": flood_dns,
    "flood-smtp": flood_smtp,
    "adulteracao-config": adulteracao_config,
    "interrupcao-servico": interrupcao_servico,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_attack_runners.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/attack_panel/runners.py backend/tests/test_attack_runners.py
git commit -m "feat: runners de trafego, adulteracao e interrupcao de servico"
```

---

### Task 6: Servidor da API (SSE + página + bind localhost)

**Files:**
- Create: `scripts/attack_panel/server.py`
- Test: `backend/tests/test_attack_panel_api.py`

**Interfaces:**
- Consumes: `catalog` (Task 1), `Engine`/`AttackContext` (Task 3), `runners.RUNNERS`/`runners.make_client`/`runners.PROMETHEUS_BASE` (Tasks 4–5), `verification` (Task 2), `exclusive_lock` de `scripts.scan_vulnerabilities`.
- Produces: `HOST = "127.0.0.1"`; `build_verifier() -> callable(expected, cancelled) -> dict` (até 6 tentativas com 5 s de intervalo); `create_app(engine=None) -> FastAPI` com rotas `GET /api/attacks`, `GET /api/queue`, `POST /api/attacks/{id}/start` (400 params inválidos, 404 desconhecido), `POST /api/queue/{entry_id}/cancel` (404), `GET /api/events` (SSE), `GET /health`, `GET /`, `GET /panel.js`, `GET /panel.css`; `main()` com `--port` (default 8002) fixando `host=HOST`.

- [ ] **Step 1: Write the failing test**

```python
import httpx
import pytest
from fastapi.testclient import TestClient

from scripts.attack_panel import server
from scripts.attack_panel.catalog import CATALOG


class FakeEngine:
    def __init__(self):
        self.started = []
        self.cancelled = []

    def enqueue(self, attack_id, params=None):
        if params and params.get("tentativas") == 9999:
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
    assert client.get("/panel.js").status_code == 200
    assert client.get("/panel.css").status_code == 200
    assert client.get("/panel.js").headers["content-type"].startswith("application/javascript")
    assert client.get("/panel.css").headers["content-type"].startswith("text/css")


def test_verificador_tenta_ate_conseguir_e_nunca_inventa_sucesso(monkeypatch):
    tentativas = []

    class ClientFalso:
        def __enter__(self): return self

        def __exit__(self, *args): return False

        def get(self, url, params=None):
            tentativas.append(1)
            raise httpx.ConnectError("prometheus fora do ar")

    monkeypatch.setattr(server.runners, "make_client", lambda: ClientFalso())
    monkeypatch.setattr(server.time, "sleep", lambda segundos: None)
    resultado = server.build_verifier()(["TrafegoAnormal"], lambda: False)
    assert resultado == {"available": False, "fired": [], "missing": ["TrafegoAnormal"]}
    assert len(tentativas) == 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_attack_panel_api.py -v`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

`scripts/attack_panel/server.py`:

```python
"""Servidor do painel de ataques: API + SSE + página estática, apenas localhost."""
import argparse
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from scripts.attack_panel import runners, verification
from scripts.attack_panel.catalog import SPECS, catalog
from scripts.attack_panel.engine import Engine

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent / "static"
HOST = "127.0.0.1"
VERIFY_ATTEMPTS = 6
VERIFY_INTERVAL = 5


def build_verifier():
    def verify(expected, cancelled=lambda: False):
        if not expected:
            return {"available": True, "fired": [], "missing": []}
        for attempt in range(VERIFY_ATTEMPTS):
            try:
                with runners.make_client() as client:
                    firing = verification.firing_alerts(client, runners.PROMETHEUS_BASE)
                return verification.verify(expected, firing)
            except Exception:
                if cancelled() or attempt == VERIFY_ATTEMPTS - 1:
                    return verification.verify(expected, None)
                time.sleep(VERIFY_INTERVAL)
    return verify


class StartBody(BaseModel):
    params: dict | None = None


def create_app(engine=None):
    if engine is None:
        engine = Engine(runners=runners.RUNNERS, verifier=build_verifier())
    app = FastAPI(title="Painel de Ataques do Laboratório")
    app.state.engine = engine

    @app.get("/api/attacks")
    def attacks():
        return {"attacks": catalog()}

    @app.get("/api/queue")
    def queue_view():
        return engine.snapshot()

    @app.post("/api/attacks/{attack_id}/start")
    def start(attack_id: str, body: StartBody | None = None):
        if attack_id not in SPECS:
            raise HTTPException(404, "ataque_desconhecido")
        try:
            return engine.enqueue(attack_id, (body.params if body else None) or {})
        except ValueError as error:
            raise HTTPException(400, str(error))

    @app.post("/api/queue/{entry_id}/cancel")
    def cancel(entry_id: str):
        view = engine.cancel(entry_id)
        if view is None:
            raise HTTPException(404, "entrada_desconhecida")
        return view

    @app.get("/api/events")
    def events():
        return StreamingResponse(engine.subscribe(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store"})

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/panel.js")
    def js():
        return FileResponse(STATIC / "panel.js", media_type="application/javascript")

    @app.get("/panel.css")
    def css():
        return FileResponse(STATIC / "panel.css", media_type="text/css")

    return app


def main():
    parser = argparse.ArgumentParser(description="Painel de ataques do laboratório (somente localhost)")
    parser.add_argument("--port", type=int, default=8002)
    arguments = parser.parse_args()
    uvicorn.run(create_app(), host=HOST, port=arguments.port, log_level="info")


if __name__ == "__main__":
    from scripts.scan_vulnerabilities import exclusive_lock
    with exclusive_lock(ROOT / ".runtime/attack-panel.lock"):
        main()
```

Nota: `HOST` é constante deliberada — o `main()` não aceita `--host`; a garantia de localhost não depende do operador.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_attack_panel_api.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/attack_panel/server.py backend/tests/test_attack_panel_api.py
git commit -m "feat: servidor do painel com API, SSE e bind localhost"
```

---

### Task 7: Página estática do painel (três camadas)

**Files:**
- Create: `scripts/attack_panel/static/index.html`
- Create: `scripts/attack_panel/static/panel.js`
- Create: `scripts/attack_panel/static/panel.css`
- Test: `backend/tests/test_attack_panel_api.py` (acrescentar smoke — servidor já serve os arquivos; o teste da Task 6 exige `Painel de Ataques` no HTML, então criar os arquivos faz os testes de página passarem de fato)

**Interfaces:**
- Consumes: rotas da Task 6 (`/api/attacks`, `/api/queue`, `/api/attacks/{id}/start`, `/api/queue/{entry_id}/cancel`, `/api/events`).
- Produces: nada (apresentação).

- [ ] **Step 1: Criar os três arquivos**

`scripts/attack_panel/static/index.html`:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel de Ataques — Laboratório AulaRedes</title>
<link rel="stylesheet" href="/panel.css">
</head>
<body>
<header>
  <h1>Painel de Ataques</h1>
  <p class="sub">Ferramenta local do laboratório AulaRedes (127.0.0.1). Os efeitos geram alertas no
  <a href="http://localhost:8000" target="_blank" rel="noreferrer">painel de monitoramento</a>.</p>
</header>
<main>
  <section>
    <h2>Catálogo</h2>
    <div id="ataques" class="grid"></div>
  </section>
  <section>
    <h2>Execução</h2>
    <div id="atual"></div>
    <div id="fila"></div>
    <div id="historico"></div>
  </section>
  <section>
    <h2>Log de eventos</h2>
    <pre id="log-box" aria-live="polite"></pre>
  </section>
</main>
<script src="/panel.js"></script>
</body>
</html>
```

`scripts/attack_panel/static/panel.js`:

```javascript
const PHASES = ["agendado", "preparando", "executando", "verificando", "concluido"];
const FINAL_ICONS = { concluido: "✅", interrompido: "🛑", falhou: "❌" };

async function jfetch(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function renderCatalog(attacks) {
  const grid = document.getElementById("ataques");
  grid.innerHTML = "";
  for (const attack of attacks) {
    const card = document.createElement("article");
    card.className = "card";
    const inputs = (attack.params || []).map((spec) => {
      if (spec.type === "int") {
        return `<label>${spec.name} <input type="number" data-param="${spec.name}" value="${spec.default}" min="${spec.min}" max="${spec.max}"></label>`;
      }
      const options = (spec.options || []).map((option) => `<option ${option === spec.default ? "selected" : ""}>${option}</option>`).join("");
      return `<label>${spec.name} <select data-param="${spec.name}">${options}</select></label>`;
    }).join("");
    card.innerHTML = `<h3>${attack.name}</h3><p class="target">${attack.target}</p><p>${attack.description}</p>
      <p class="alerts">Alertas esperados: ${attack.expected_alerts.join(", ") || "depende do alvo"}</p>
      <div class="params">${inputs}</div>
      <button data-start="${attack.id}">Iniciar</button>`;
    grid.appendChild(card);
  }
}

function phases(entry) {
  const current = PHASES.indexOf(entry.status);
  return PHASES.map((phase, index) => `<span class="phase ${index <= current ? "done" : ""}">${phase}</span>`).join(" → ");
}

function verification(entry) {
  if (!entry || !entry.verification) return "";
  const result = entry.verification;
  if (!result.available) return `<p class="warn">⚠️ Verificação indisponível (Prometheus fora do ar?)</p>`;
  if (result.fired.length) return `<p class="ok">✅ Alerta disparou: ${result.fired.join(", ")}</p>`;
  return `<p class="warn">⚠️ Não disparou (verificar): ${result.missing.join(", ")}</p>`;
}

function counters(entry) {
  const items = Object.entries(entry.counters || {});
  return items.length ? `<p class="counters">${items.map(([key, value]) => `${key}: ${value}`).join(" · ")}</p>` : "";
}

function entryView(entry) {
  const aberto = !["concluido", "falhou", "interrompido"].includes(entry.status);
  return `<article class="entry status-${entry.status}">
    <h4>${entry.attack} <span class="status">${entry.status}${FINAL_ICONS[entry.status] ? " " + FINAL_ICONS[entry.status] : ""}</span></h4>
    <p class="phases">${phases(entry)}</p>
    ${counters(entry)}
    ${verification(entry)}
    ${aberto ? `<button data-cancel="${entry.entry_id}">Interromper</button>` : ""}
  </article>`;
}

async function refresh() {
  try {
    const snapshot = await jfetch("/api/queue");
    document.getElementById("atual").innerHTML = snapshot.current
      ? entryView(snapshot.current) : `<p class="idle">Nenhum ataque em execução.</p>`;
    document.getElementById("fila").innerHTML = snapshot.queue.length
      ? `<h3>Fila</h3>${snapshot.queue.map(entryView).join("")}` : "";
    document.getElementById("historico").innerHTML = snapshot.history.length
      ? `<h3>Histórico</h3>${snapshot.history.slice().reverse().map(entryView).join("")}` : "";
  } catch (error) { /* servidor fora do ar; próxima tentativa em 2 s */ }
}

document.addEventListener("click", async (event) => {
  if (event.target.dataset && event.target.dataset.cancel) {
    await jfetch(`/api/queue/${event.target.dataset.cancel}/cancel`, { method: "POST" }).catch(() => {});
    refresh();
  }
  if (event.target.dataset && event.target.dataset.start) {
    const id = event.target.dataset.start;
    const card = event.target.closest(".card");
    const params = {};
    card.querySelectorAll("[data-param]").forEach((input) => {
      params[input.dataset.param] = input.tagName === "SELECT" ? input.value : Number(input.value);
    });
    try {
      await jfetch(`/api/attacks/${id}/start`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ params }) });
    } catch (error) { alert("Falha ao iniciar: " + error.message); }
    refresh();
  }
});

const logBox = document.getElementById("log-box");
logBox.textContent = "";
const source = new EventSource("/api/events");
source.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "log") {
    logBox.textContent += `[${new Date().toLocaleTimeString("pt-BR")}] ${data.message}\n`;
    logBox.scrollTop = logBox.scrollHeight;
  }
};

jfetch("/api/attacks").then((data) => renderCatalog(data.attacks)).catch(() => {});
refresh();
setInterval(refresh, 2000);
```

`scripts/attack_panel/static/panel.css`:

```css
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; font-family: "Segoe UI", system-ui, sans-serif; background: #0d1117; color: #e6edf3; }
header { padding: 16px 24px; border-bottom: 1px solid #21262d; }
header h1 { margin: 0; font-size: 22px; }
.sub { margin: 4px 0 0; color: #8b949e; font-size: 14px; }
.sub a { color: #58a6ff; }
main { max-width: 1100px; margin: 0 auto; padding: 16px 24px 48px; }
h2 { font-size: 16px; text-transform: uppercase; letter-spacing: 0.06em; color: #8b949e; margin: 24px 0 8px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
.card, .entry { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 14px 16px; }
.card h3 { margin: 0 0 4px; font-size: 16px; }
.target { color: #58a6ff; font-size: 13px; margin: 0 0 8px; }
.card p { font-size: 14px; margin: 6px 0; }
.alerts { color: #d29922; font-size: 13px; }
.params label { display: inline-block; margin-right: 12px; font-size: 13px; color: #8b949e; }
input, select { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 4px 8px; margin-left: 6px; width: 90px; }
select { width: auto; }
button { background: #238636; color: #fff; border: 0; border-radius: 6px; padding: 6px 14px; font-size: 14px; cursor: pointer; margin-top: 8px; }
button:hover { background: #2ea043; }
.entry h4 { margin: 0 0 6px; font-size: 15px; display: flex; gap: 8px; align-items: baseline; }
.status { color: #8b949e; font-weight: 400; font-size: 13px; }
.phases { font-size: 13px; color: #8b949e; }
.phase.done { color: #58a6ff; font-weight: 600; }
.counters { font-family: Consolas, monospace; font-size: 13px; color: #7ee787; }
.ok { color: #7ee787; font-size: 14px; }
.warn { color: #d29922; font-size: 14px; }
.idle { color: #8b949e; }
#log-box { background: #0d1117; border: 1px solid #21262d; border-radius: 8px; padding: 12px; height: 220px; overflow-y: auto; font-size: 13px; white-space: pre-wrap; }
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest backend/tests/test_attack_panel_api.py -v`
Expected: 6 passed (o teste de página estática agora valida os arquivos reais)

- [ ] **Step 3: Verificação manual rápida (local, sem laboratório)**

Run: `python -m scripts.attack_panel.server --port 8002` e abrir `http://localhost:8002`
Expected: catálogo com 8 cartões, log vazio, "Nenhum ataque em execução."; `Ctrl+C` encerra. (Segunda instância na mesma porta falha com erro de lock/porta — comportamento esperado.)

- [ ] **Step 4: Commit**

```bash
git add scripts/attack_panel/static/
git commit -m "feat: pagina estatica do painel de ataques com log ao vivo"
```

---

### Task 8: Runbook, suíte completa e verificação no laboratório

**Files:**
- Create: `docs/runbook-painel-ataques.md`
- Modify: `docs/roadmap.md` (marcar painel de ataques como concluído na lista de pendências)

**Interfaces:**
- Consumes: tudo das Tasks 1–7.
- Produces: documentação de operação.

- [ ] **Step 1: Suíte completa**

Run: `python -m pytest backend/tests -q`
Expected: todos passam (167 anteriores + ~34 novos)

Run: `docker compose exec prometheus promtool check config /etc/prometheus/prometheus.yml` (rotina: nada em `alerts.yml` mudou; só confere que a stack continua válida). Se a stack não estiver de pé, pular com nota.

- [ ] **Step 2: Escrever o runbook**

`docs/runbook-painel-ataques.md`:

```markdown
# Runbook — Painel de Ataques

Ferramenta local para demonstrar ataques controlados contra o laboratório e
observar os alertas correspondentes no painel de monitoramento. Acesso
exclusivamente em `127.0.0.1:8002`; nunca exposta na rede.

## Iniciar

1. Stack de pé (`scripts/start.ps1` ou `docker compose up -d --wait`).
2. Painel: `python -m scripts.attack_panel.server` (porta 8002).
3. Abrir `http://localhost:8002`. O lock de instância única está em
   `.runtime/attack-panel.lock` (erro `worker_already_running` significa que
   já há uma instância ativa).

## Catálogo e alertas esperados

| Ataque | Efeito | Alerta esperado (`for:`) |
|---|---|---|
| Força bruta no serviço | 12× `POST /mode` com token inválido | `AutenticacaoServicoSuspeita` (30s) |
| Força bruta no painel | 8× login com senha errada | `AutenticacaoSuspeita` (10s) |
| Sobrecarga HTTP | Maré em `GET /work` | `RecursoCPUElevada` ou `TrafegoAnormal` (30s) |
| Indisponibilidade | Modo offline do web-demo | `HTTPIndisponivel` (15s) |
| Flood DNS | Job de carga limitada (`/api/lab/traffic`) | `TrafegoAnormal` (30s) |
| Flood SMTP | Job de carga limitada (`/api/lab/traffic`) | `TrafegoAnormal` (30s) |
| Adulteração de config | Altera arquivo em `./infra` e restaura byte a byte | `ConfiguracaoAlterada` (15s) |
| Interrupção de serviço | `docker compose stop/start` no alvo | `*Indisponivel` do alvo (15s) |

## Regras de segurança

- O painel só **lê** o Prometheus; nunca publica métricas sintéticas.
- Efeitos são reversíveis: modo normal restaurado, serviço reiniciado,
  arquivo restaurado byte a byte (hash volta a bater com a referência —
  `approve_integrity.py` não é necessário após restauração).
- Interrupção a meio do ataque dispara a limpeza no `finally` do runner.
- Falha de verificação com Prometheus fora do ar aparece como
  "⚠️ Verificação indisponível", nunca como sucesso.

## Verificação manual (roteiro de demonstração)

Para cada ataque: iniciar no painel → acompanhar fases/log → conferir o
resultado (✅/⚠️) → abrir o dashboard `:8000` e ver o incidente com o mesmo
nome → e-mail no Mailpit (`:8025`). Floods exigem referências de tráfego
calibradas (aguardar status `normal` na tabela de tráfego antes de atacar).

## Solução de problemas

- `worker_already_running`: painel já aberto em outro terminal.
- Porta 8002 ocupada: `--port 8003` (a página usa caminhos relativos).
- Alerta não disparou (⚠️): conferir coletores ativos; floods precisam de
  baseline pronta; verificar `up{job="platform"}` no dashboard.
```

- [ ] **Step 3: Atualizar roadmap**

Em `docs/roadmap.md`, marcar a entrada do painel de ataques como concluída (manter pendentes: relatório ABNT, apresentação, frontend realista do web-demo).

- [ ] **Step 4: Verificação ponta a ponta no laboratório (manual)**

1. `python -m scripts.attack_panel.server`
2. Executar os ataques 1, 4, 8 (os mais rápidos) e conferir ✅ e incidentes no dashboard.
3. Interromper o ataque 4 a meio e conferir que o modo normal voltou.

- [ ] **Step 5: Commit**

```bash
git add docs/runbook-painel-ataques.md docs/roadmap.md
git commit -m "docs: runbook do painel de ataques e roadmap atualizado"
```

---

## Self-Review (realizado)

1. **Cobertura da spec:** catálogo 1–8 (Tasks 1, 4, 5); fila/fases/interrupção (Task 3); visualização em três camadas (Tasks 6–7: cartões+fases, SSE de log/progresso, verificação final com link para o dashboard); API conforme seção 5 (Task 6); bind localhost e sem métricas sintéticas (Tasks 2, 6); efeitos reversíveis (Tasks 4–5, `finally`); tempos honestos (`for:` conferidos em `alerts.yml`, holds + verificador com 6 tentativas); reuso de `/api/lab/traffic` (Task 5); critérios de aceite cobertos pela Task 8.
2. **Placeholders:** nenhum; todos os passos têm código/commands completos.
3. **Consistência de tipos:** assinaturas conferidas entre tasks — `clean_params`/`expected_alerts` (1→3), `firing_alerts`/`verify` (2→4,5,6), `Cancelled`/`AttackContext`/`Engine` (3→4,5,6), `make_client`/`lab_token`/`_hold`/`_firing` (4→5), `RUNNERS` (5→6), rotas (6→7). `Engine.cancel` publica `interrompendo` e o runner interrompido termina em `interrompido`.
