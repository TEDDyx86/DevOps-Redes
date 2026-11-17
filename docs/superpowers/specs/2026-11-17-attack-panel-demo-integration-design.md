# Especificação: painel de simulação de ataques integrado ao web-demo

Data: 17/11/2026. Objetivo: transformar o web-demo (`:8011`) no painel único
de simulação de ataques do laboratório, absorvendo o painel do host
(`:8002`, `scripts/attack_panel`), com a identidade retrô-pixel da demo. O
dashboard Workbyte (`:8000`) não muda.

## Decisões aprovadas

1. **8 ataques completos**, inclusive interrupção de serviço (Docker API via
   socket montado no container — laboratório local, risco aceito).
2. **Aposentar `:8002`**: o web-demo `:8011` passa a ser o único painel de
   ataques; `scripts/attack_panel/server.py` e a página estática do host
   são removidos; os módulos de engine migram para `demo/attacks/`.
3. **Aba "Ataques"** dentro do painel existente da demo (retrô-pixel), ao
   lado de saúde/modo/métricas.

## Restrições encontradas

- A imagem Docker só copia `backend/` e `demo/`: `scripts/` não existe no
  container. O engine precisa viver em `demo/attacks/` (mesma imagem
  `aularedes-platform:local`).
- Os runners atuais atacam URLs do host e leem `.env` do repositório; no
  container os alvos viram nomes de serviço e o `LAB_TOKEN` vem do env.
- A montagem `./infra` do web-demo é read-only; adulteração de config
  exige reabrir como `rw` (a API de monitoramento enxerga a mesma mudança
  porque os dois containers compartilham o bind do `./infra`).

## Arquitetura

### Backend: `demo/attacks/` (novo pacote)

- `catalog.py`: os 8 ataques, textos de alvo atualizados (`web-demo :8011`
  passa a ser o próprio serviço; painel = `api :8000` interno).
- `engine.py`: fila de um ataque por vez, fases
  (`agendado → preparando → executando → verificando → concluído` /
  `interrompido` / `falhou`), eventos SSE — módulo movido sem mudança de
  comportamento, apenas de import.
- `verification.py`: consulta `ALERTS{alertstate="firing"}` no Prometheus;
  até 6 tentativas com 5 s de intervalo.
- `runners.py`: adaptado ao contexto do container:
  - Alvos por env com default: `DEMO_BASE` (`http://web-demo:8001`),
    `PANEL_BASE` (`http://api:8000`), `PROMETHEUS_BASE`
    (`http://prometheus:9090`).
  - `LAB_TOKEN` do env do container (não mais do `.env` do host).
  - Autenticação no painel para flood DNS/SMTP: `POST /api/auth/login` com
    `ADMIN_USERNAME`/`ADMIN_PASSWORD` do env (mesma senha do hash da API) +
    header `X-CSRF-Token`.
  - `adulteracao-config`: raiz `INFRA_ROOT` (default `/etc/aularedes/runtime`),
    mapeando caminho `infra/dns/Corefile` → `INFRA_ROOT/dns/Corefile`;
    guard de escopo permanece (só arquivos sob a raiz observada) e
    restauração byte a byte no final/cancelamento.
  - `interrupcao-servico`: Docker Engine API por socket Unix
    (`/var/run/docker.sock`) via httpx: localiza o container pelo label
    `com.docker.compose.service`, faz `stop` (com timeout) e `start` no
    fim/cancelamento. Sem CLI do docker no container.

### API no web-demo (`demo/main.py`)

Rotas acopladas à sessão da demo (cookie HMAC do login retrô):

| Rota | Descrição |
|---|---|
| `GET /api/attacks` | catálogo com metadados e parâmetros |
| `GET /api/queue` | snapshot da fila (atual, aguardando, histórico) |
| `POST /api/attacks/{id}/start` | enfileira ataque; 400 fora de faixa, 404 desconhecido |
| `POST /api/queue/{entry_id}/cancel` | interrompe entrada; 404 desconhecida |
| `GET /api/events` | SSE do engine (log ao vivo, progresso, fase) |

- Toda rota exige sessão válida (401 caso contrário); o `EventSource` do
  navegador envia o cookie same-origin, então o SSE autentica pelo cookie.
- Engine único em `app.state.engine` (uvicorn de um worker; fila em
  memória — reinício do container limpa fila e histórico, aceitável).
- As rotas `/health`, `/work`, `/metrics`, `/mode` e o SPA atual ficam
  exatamente como estão.

### Compose (`compose.yaml`, serviço `web-demo`)

- `volumes`: `./infra:/etc/aularedes/runtime:rw` (antes `ro`) e
  `/var/run/docker.sock:/var/run/docker.sock`.
- `group_add: [0]` para o usuário `app` (uid 10001) acessar o socket
  (root:root 660 no Docker Desktop).
- `environment`: `PANEL_BASE`, `DEMO_BASE`, `PROMETHEUS_BASE`,
  `INFRA_ROOT` com os defaults acima (explícitos no compose).

### Frontend (`demo-frontend`)

- Aba **"Ataques"** no `Panel.tsx`, estilo retrô-pixel existente:
  - Cartões do catálogo (nome, alvo, descrição, parâmetros editáveis com
    defaults, alertas esperados, botão Iniciar).
  - Fila: ataque em execução com fase atual, contadores e barra; próximos
    da fila; histórico recente.
  - Log ao vivo via `EventSource` (`/api/events`) com fase/progresso.
  - Resultado da verificação do alerta: disparou / não disparou
    (verificar) / verificação indisponível.
  - `401` em qualquer chamada redireciona ao login (padrão existente).
- `api.ts` ganha os métodos do painel (mesma origem, sem CSRF).
- Landing, Login e o restante do painel da demo não mudam.

### Aposentação do `:8002`

- Remover `scripts/attack_panel/` (server.py, static/, runners.py,
  engine.py, catalog.py, verification.py, __init__.py) após a migração.
- `docs/runbook-painel-ataques.md` reescrito: painel em `http://localhost:8011`
  (aba Ataques, após login da demo), sem seção de início no host.
- Referências em `README.md` atualizadas.

## Testes (TDD)

- `backend/tests`: os 5 arquivos de teste existentes migram para
  `demo.attacks` (catalog, engine, verification, runners com fakes, API).
  Novos: API do demo exige sessão (401 sem cookie), start valida
  parâmetros, cancelamento; runner de interrupção usa fake de socket/
  httpx (sem Docker real); runner de autenticação do painel usa env em vez
  de `.env`.
- `demo-frontend`: testes vitest da aba Ataques (renderização dos cartões
  a partir do catálogo fake, estado da fila, mensagem de 401 → login).

## Fora de escopo

- Visual do dashboard Workbyte (`:8000`) — mantido como está; ajustes
  ficam para depois, a pedido.
- Novos ataques além do catálogo atual.
- Persistência de fila/histórico entre reinícios.
