# Cobertura de Requisitos — Plano de Implementação

> **For agentic workers:** executar inline com TDD (RED→GREEN por passo),
> commit atômico por tarefa. Steps usam checkbox (`- [ ]`).

**Goal:** fechar as 4 lacunas da análise de requisitos — conexões ativas HTTP
(métrica → API → frontend), playbook de incidentes, guia de instalação e testes
E2E de navegação com Playwright.

**Spec:** `docs/superpowers/specs/2026-11-17-cobertura-requisitos-design.md`

## Global Constraints

- Nada muda nos endpoints existentes; apenas campos novos.
- Testes backend no venv: `.venv\Scripts\python.exe -m pytest backend/tests -q`.
- Frontend: `npm test` e `npm run build` em `frontend/`.
- Commits convencionais.

---

### Task 1: Gauge de conexões ativas no demo (TDD)

**Files:** Update `demo/main.py`, `backend/tests/test_platform.py`
- [ ] RED: com `create_demo` + ASGITransport, duas requisições `/work` concorrentes
  (work_delay alto) → `demo_http_requests_inflight` atinge 2 e volta a 0;
  `/metrics` contém a série.
- [ ] GREEN: `Gauge("demo_http_requests_inflight")` inc no início do middleware e
  `dec()` em `finally`; `app.state.registry = registry` para leitura nos testes.
- [ ] Commit `feat(demo): gauge de conexoes ativas http`.

### Task 2: `service.connections` no overview (TDD)

**Files:** Update `backend/app/metrics.py`, `backend/tests/test_platform.py`
- [ ] RED: fake do Prometheus devolve valor do gauge → `data["service"]["connections"]`
  igual ao valor; demo stale → `None`; Prometheus vazio → `None`.
- [ ] GREEN: query `demo_http_requests_inflight{job="web-demo"}` mapeada em
  `connections`; zerada junto com rps/p95 quando demo stale.
- [ ] Suíte backend completa verde.
- [ ] Commit `feat(metrics): conexoes ativas http no overview`.

### Task 3: Tile "Conexões ativas" no frontend (TDD)

**Files:** Update `frontend/src/types.ts`, `frontend/src/components.tsx`,
`frontend/src/App.tsx`; create `frontend/src/serviceDetails.test.tsx`
- [ ] RED: renderizar componente de detalhes com service.connections=12 →
  "Conexões ativas" e "12"; null → "—".
- [ ] GREEN: extrair `ServiceDetails` para `components.tsx` (requisições/s,
  erros 4xx/5xx, conexões ativas, estado da sonda, botão Testar falha) e usar
  em `App.tsx`; `ServiceSummary.connections: number | null`.
- [ ] `npm test` e `npm run build` verdes.
- [ ] Commit `feat(frontend): conexoes ativas na pagina do servico http`.

### Task 4: Playbook de incidentes (docs)

**Files:** Create `docs/playbook-incidentes.md`
- [ ] Fluxo de resposta em níveis (verde/amarelo/vermelho + ação e-mail),
  tabela alerta → causa provável → ação → runbook, pós-incidente.
- [ ] Commit `docs: playbook de incidentes da plataforma`.

### Task 5: Guia de instalação (docs)

**Files:** Create `docs/instalacao.md`
- [ ] Pré-requisitos, configuração (`scripts/configure.py`), subida, verificação
  de portas, Mailpit, encerramento/preservação; README aponta para ele.
- [ ] Commit `docs: guia de instalacao dedicado`.

### Task 6: Playwright E2E de navegação

**Files:** Update `frontend/package.json`; create `frontend/playwright.config.ts`,
`frontend/e2e/navegacao.spec.ts`
- [ ] Instalar `@playwright/test` + chromium; config com baseURL `http://127.0.0.1:8000`
  e credenciais do `.env`.
- [ ] Teste: login pela UI → percorrer as 9 páginas → marcadores reais por página;
  execução real contra a stack local.
- [ ] Commit `test(frontend): navegacao e2e com playwright`.

### Deploy e verificação final

- [ ] `docker compose up -d --build --no-deps api web-demo`; smoke `curl.exe --noproxy "*"`.
- [ ] Confirmar `connections` em `/api/overview` (com sessão) e tile no `:8000`.
