# Especificação — Frontend do web-demo (CRT synthwave + pixel)

Data: 2026-11-12 · Status: aprovado pelo usuário
Contexto: Trabalho final de Redes — entrega 17/11/2026. Sucessor do Painel de Ataques (sub-projeto 2 das pendências).

## Objetivo

Dar ao web-demo (porta 8001) um frontend que pareça um produto/aplicação real: landing estática 8-bit futurista → login com credenciais autorizadas → painel com informações vivas do serviço. Para a apresentação, o site deve reagir em tempo real quando ataques atingirem o demo (ex.: modo offline → "SIGNAL LOST").

## Decisões (aprovadas)

1. **Stack**: React 19 + Vite + TypeScript + Tailwind + shadcn CLI, em pasta nova `demo-frontend/`. Componentes prontos buscados no MCP **shoogle** (`search_registry_items`) e instalados via `npx shadcn@latest add {addCommandArgument}`.
2. **Servimento**: build vai para `demo/static/`; Dockerfile ganha estágio `demo-frontend` que compila e copia o `dist/`. O comando/serviço `web-demo` no compose não muda. Em dev, `npm run dev` com proxy para `127.0.0.1:8001`.
3. **Login**: `POST /login` novo no `demo/main.py`, validando credenciais **reutilizadas do dashboard**: `ADMIN_USERNAME` (default `admin`) e `ADMIN_PASSWORD` (env do `web-demo` no compose, vindas do `.env` que o `scripts/configure.py` já gera — nada novo nele). O demo deriva o hash SHA-256 em memória no startup. Sessão = cookie assinado (HMAC-HS256 com `LAB_TOKEN`, HttpOnly, SameSite=Lax, path=/). Sem segredo novo no bundle.
4. **Visual**: CRT synthwave + pixel (ver Direção visual).

## Contratos preservados (byte a byte)

- `GET /health` · `GET /work` · `GET /metrics` · `GET /mode` · `POST /mode`
- Middleware de instrumentação (só `/work` e `/health`) intocado
- `POST /login` e `GET /login` são **endpoints novos**; nada dos existentes muda

## Rotas da SPA

| Rota | Conteúdo | Proteção |
|---|---|---|
| `/` | Landing estática (hero, features, CTA "Entrar") | pública |
| `/login` | Tela de login estilo terminal/CRT | pública |
| `/painel` | Painel com status e informações | exige sessão (cookie) |

Estáticos: `/` e rotas desconhecidas → `index.html` (fallback SPA); `/assets/*` → StaticFiles. Rotas de API (`/health`, `/work`, `/metrics`, `/mode`, `/login`) têm precedência sobre o fallback.

## API nova

- `POST /login` — body `{username, password}`; valida SHA-256 da senha contra o hash derivado de `ADMIN_PASSWORD` em memória; sucesso → cookie `demo_session` + `200 {"authenticated": true}`; falha → `401` (counter de auth reutilizado do demo, labels `path=/login`)
- `GET /login` — `{authenticated: true|false}` conforme cookie válido
- `POST /logout` — limpa o cookie
- Assinatura do cookie: `HMAC-SHA256(payload)` com chave = `LAB_TOKEN`; payload = `{"u": username, "exp": epoch}`; exp 12h

## Painel (após login)

| Card | Fonte | Poll | Estados |
|---|---|---|---|
| Sinal | `GET /health` | 3 s | `● ONLINE` / `✖ SIGNAL LOST` (glitch) |
| Modo do sistema | `GET /mode` | 3 s | NORMAL / SLOW / OFFLINE ("fase do jogo") |
| Console de trabalho | `GET /work` (botão manual) | — | log estilo terminal: resposta + latência medida no browser |
| Contadores | `GET /metrics` (parse texto de `demo_http_requests_total`) | 10 s | total e por status; vazio → `AGUARDANDO DADOS` |

Sem controle de modo no painel: `POST /mode` exige `X-Lab-Token` e continua operado pela plataforma/painel de ataques.

## Direção visual (CRT synthwave + pixel)

- Fundo preto-azulado (`#05060f` / `#0a0b14`), grade em perspectiva sutil no hero
- Tipografia: `Press Start 2P` (`@fontsource/press-start-2p`) para títulos/labels; `IBM Plex Mono` para corpo e dados
- Neon: magenta `#ff2fd6`, ciano `#00e5ff`, violeta `#8b5cf6`, âmbar p/ warnings; glow pixel controlado
- CRT: overlay scanlines (CSS), flicker leve no hero, molduras de cantos pixelados, diálogos estilo RPG (`* mensagem`, borda dupla branca)
- Landing: hero com título pixel chunky + arte pixel (sprite/cenário gerado como asset), features em cards pixel, marquee estilo VHS, footer 1-bit (ícones em linha, bordas finas — ref. imagem MoonByte)
- Login: formulário terminal, cursor piscando, erro em diálogo RPG (`! Credenciais inválidas`)

## Erros e estados

- `/health` falha → card `SIGNAL LOST` com glitch (momento-chave da apresentação)
- Login inválido → diálogo RPG, form não trava
- Sessão expira → redirect `/login` com mensagem
- Métricas ausentes → `AGUARDANDO DADOS` (nunca zero falsificado — princípio do projeto)

## Testes

- Backend: `backend/tests/test_demo_login.py` — login ok (200 + cookie), credencial errada (401), `GET /login` autenticado/não autenticado, assinatura inválida rejeitada, contratos existentes verdes
- Frontend: vitest (`demo-frontend/src`) — cliente de API, sessão (login/logout/redirect), parse de métricas, estados do painel
- Build: `tsc -b && vite build` limpo; imagem com estáticos servidos

## Fluxo de entrega

Fase única, ordem: estrutura `demo-frontend` → `POST/GET/DELETE /login` no backend (TDD) → shell visual (tema, tokens, fonts, CRT) → landing → tela de login → painel → build Docker e validação `docker compose up -d --build --wait`.

## Fora de escopo

- Autenticação no dashboard ou no painel de ataques
- Novos endpoints de dados no demo além de `/login`
- Páginas adicionais (documentação fake, multi-SPA)
- Controle de modo pelo site
