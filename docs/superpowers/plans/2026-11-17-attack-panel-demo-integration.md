# Painel de Ataques Integrado ao Web-Demo — Plano de Implementação

> **For agentic workers:** executar inline com TDD (RED→GREEN por passo),
> commit atômico por tarefa. Steps usam checkbox (`- [ ]`).

**Goal:** o web-demo (`:8011`) se torna o único painel de simulação de
ataques do laboratório: engine embutido no container, API acoplada ao
login retrô da demo e aba "Ataques" no painel pixel. O painel do host
(`:8002`) é aposentado. Dashboard `:8000` intocado.

**Architecture:** módulos de engine migram de `scripts/attack_panel/` para
`demo/attacks/` (única forma de entrar na imagem). Runners passam a atacar
serviços da rede interna via env, usam `LAB_TOKEN`/`ADMIN_*` do ambiente do
container e a Docker Engine API por socket Unix para interrupção de
serviço. `demo/main.py` expõe `/api/attacks`, `/api/queue`,
`/api/attacks/{id}/start`, `/api/queue/{entry_id}/cancel` e `/api/events`
(SSE), todos exigindo a sessão da demo. `demo-frontend` ganha a aba
"Ataques" no `Panel.tsx`.

**Tech Stack:** Python (FastAPI, uvicorn, httpx — já na imagem), React +
Vitest (`demo-frontend`), Docker Engine API (HTTP sobre UDS) em vez de CLI.

**Spec:** `docs/superpowers/specs/2026-11-17-attack-panel-demo-integration-design.md`

## Global Constraints

- Nada muda no `frontend/` (dashboard `:8000`), no backend do dashboard ou
  nos contratos/endpoint existentes do demo (`/health`, `/work`,
  `/metrics`, `/mode`, `/login`, `/logout`).
- Runners permanecem reversíveis: modo do demo restaurado, arquivo
  restaurado byte a byte, serviço reiniciado — inclusive no cancelamento.
- Erros de runner não expõem segredos (motor registra `type(error).__name__`).
- A API de ataques exige sessão da demo (401 sem cookie); nada de credenciais
  na URL ou em query string.
- Testes backend: `python -m pytest backend/tests/... -v` da raiz.
- Testes frontend: `npm test` em `demo-frontend/`.
- Commits convencionais (`feat:`, `refactor:`, `docs:`, `chore:`).

---

### Task 1: Migração do engine para `demo/attacks/` (refactor)

**Files:**
- Create: `demo/attacks/__init__.py`, `demo/attacks/catalog.py`,
  `demo/attacks/engine.py`, `demo/attacks/verification.py` (movidos de
  `scripts/attack_panel/`, imports internos ajustados)
- Update: `backend/tests/test_attack_catalog.py`,
  `backend/tests/test_attack_engine.py`,
  `backend/tests/test_attack_verification.py` (import de `demo.attacks`)
- `scripts/attack_panel/` permanece nesta tarefa (apagado na Task 5)

- [ ] **Step 1:** mover os três módulos; trocar imports
  `scripts.attack_panel.*` → `demo.attacks.*` (entre módulos e nos testes).
- [ ] **Step 2:** `pytest backend/tests/test_attack_catalog.py
  backend/tests/test_attack_engine.py backend/tests/test_attack_verification.py`
  — todos verdes (refatoração sem mudança de comportamento).
- [ ] **Step 3:** commit `refactor(attacks): migra engine do painel para demo/attacks`.

### Task 2: Runners adaptados ao contexto do container (TDD)

**Files:**
- Create: `demo/attacks/runners.py`
- Update: `backend/tests/test_attack_runners.py` (import `demo.attacks`)

**Interfaces:**
- Consumes: `demo.attacks.engine.AttackContext`, `verification`.
- Produces: `RUNNERS` dict com os 8 runners; helpers
  `lab_token() -> str` (env `LAB_TOKEN`, `RuntimeError` se ausente),
  `panel_session(client)` (login em `PANEL_BASE/api/auth/login` com
  `ADMIN_USERNAME`/`ADMIN_PASSWORD` do env + CSRF), `docker_client()`
  (httpx com `HTTPTransport(uds=DOCKER_SOCKET)`).

**Mudanças de contexto:**
- `DEMO_BASE` = env ou `http://web-demo:8001`; `PANEL_BASE` = env ou
  `http://api:8000`; `PROMETHEUS_BASE` = env ou `http://prometheus:9090`.
- `lab_token()` lê `os.environ` (não `.env`).
- `_traffic_attack`: autentica via `panel_session` (env) em vez de
  `scripts.lab_session`.
- `adulteracao-config`: raiz `INFRA_ROOT` (env, default
  `/etc/aularedes/runtime`); caminho `infra/x/y` → `INFRA_ROOT/x/y`;
  guard de escopo e restauração byte a byte mantidos.
- `interrupcao-servico`: Docker API por UDS —
  `GET /containers/json?filters={"label":["com.docker.compose.service=<alvo>"]}`
  para achar o id, `POST /containers/{id}/stop?t=15` e
  `POST /containers/{id}/start`; sem subprocesso/CLI.

- [ ] **Step 1 (RED):** adaptar testes: runners usam env monkeypatched
  (`LAB_TOKEN`, `ADMIN_PASSWORD`, `INFRA_ROOT` via tmp_path), fake de
  docker via `httpx.MockTransport` no `docker_client`, mantendo os fakes
  de contexto existentes.
- [ ] **Step 2:** rodar — falha (módulo `demo.attacks.runners` não existe).
- [ ] **Step 3 (GREEN):** implementar `demo/attacks/runners.py` até verde.
- [ ] **Step 4:** commit `feat(attacks): runners do engine no contexto do container`.

### Task 3: API de ataques no demo (TDD)

**Files:**
- Create: `demo/attacks/api.py` (`register(app, engine)` com as rotas)
- Update: `demo/main.py` (instancia engine com verificador e registra)
- Create test: `backend/tests/test_demo_attack_api.py` (substitui o papel
  de `test_attack_panel_api.py`, que é apagado na Task 5)

**Interfaces:**
- Consumes: `demo.attacks.{catalog,engine,verification}`,
  `demo.session.read_session`.
- Produces: rotas `GET /api/attacks`, `GET /api/queue`,
  `POST /api/attacks/{id}/start`, `POST /api/queue/{entry_id}/cancel`,
  `GET /api/events` (SSE), todas 401 sem sessão válida.

- [ ] **Step 1 (RED):** teste com `TestClient` de `demo.main.create_demo`
  + cookie de sessão forjado (helper existente dos testes da demo, se
  houver; senão criar via `make_session`): sem sessão → 401 nas 5 rotas;
  com sessão → catálogo completo, start válido/inválido/desconhecido
  (400/404) contra engine fake, cancel e snapshot.
- [ ] **Step 2:** rodar — falha (rotas não existem).
- [ ] **Step 3 (GREEN):** implementar `api.py` + registro em `main.py`
  (engine em `app.state.engine`; verificador reaproveitando
  `verification` com tentativas 6×5 s); SSE por `StreamingResponse`.
- [ ] **Step 4:** suíte backend inteira verde.
- [ ] **Step 5:** commit `feat(demo): api do painel de ataques com sessao obrigatoria`.

### Task 4: Aba "Ataques" no painel retrô (TDD)

**Files:**
- Update: `demo-frontend/src/api.ts` (métodos `attacks`, `queue`,
  `startAttack`, `cancelAttack`, `subscribeEvents` via `EventSource`)
- Update: `demo-frontend/src/pages/Panel.tsx` (tab "status"/"ataques")
- Update: `demo-frontend/src/styles.css` (estilos pixel da aba, se faltarem)
- Update test: `demo-frontend/src/pages/visualStructure.test.tsx` ou novo
  `attacksPanel.test.tsx`

- [ ] **Step 1 (RED):** teste da seção Ataques: renderiza catálogo fake
  (cartão com nome/alvo/botão Iniciar), estado da fila e link para login
  em 401. Padrão dos testes existentes da demo.
- [ ] **Step 2:** rodar — falha.
- [ ] **Step 3 (GREEN):** implementar `api.ts` + aba no `Panel.tsx`
  (cartões com parâmetros, fila com fase/contadores, log ao vivo SSE,
  resultado da verificação, redirecionamento ao login em 401).
- [ ] **Step 4:** `npm test` e `npm run build` verdes em `demo-frontend/`.
- [ ] **Step 5:** commit `feat(demo): aba de ataques no painel retro`.

### Task 5: Compose, aposentação do :8002 e deploy

**Files:**
- Update: `compose.yaml` (web-demo: `./infra:...:rw`, socket docker,
  `group_add: [0]`, envs `DEMO_BASE`/`PANEL_BASE`/`PROMETHEUS_BASE`/
  `INFRA_ROOT`)
- Delete: `scripts/attack_panel/` (engine já migrado) e
  `backend/tests/test_attack_panel_api.py` (substituído na Task 3)
- Update: `docs/runbook-painel-ataques.md` (painel em `:8011`), `README.md`

- [ ] **Step 1:** atualizar compose e runbook/README.
- [ ] **Step 2:** apagar `scripts/attack_panel/` e o teste antigo;
  grep para garantir zero referências restantes a
  `scripts.attack_panel`/`:8002`.
- [ ] **Step 3:** suíte backend completa verde (213+ testes).
- [ ] **Step 4:** deploy: `docker compose up -d --build --no-deps web-demo`;
  verificar com `curl.exe --noproxy "*"`:
  - `/` e `/login` → 200;
  - `/api/attacks` sem sessão → 401;
  - `/api/attacks` com sessão da demo → 8 ataques;
  - dashboard `:8000` continua saudável (regressão).
- [ ] **Step 5:** commit `chore: aposenta painel de ataques do host e monta contexto no web-demo`.

### Verificação final (manual, com o usuário)

- Login retrô em `:8011` → aba Ataques → disparar um ataque leve
  (ex.: indisponibilidade 20 s) e confirmar alerta `HTTPIndisponivel` no
  dashboard `:8000` e resultado da verificação na própria aba.
