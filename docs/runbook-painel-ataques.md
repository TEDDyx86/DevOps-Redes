# Runbook — Painel de Ataques

Ferramenta do laboratório para disparar ataques controlados e observar os
alertas correspondentes no dashboard de monitoramento. Desde 17/11/2026 o
painel vive **dentro do web-demo**, em `http://localhost:8011`, na aba
**Simulação de ataques** (após o login da demo). O painel do host na porta
8002 foi aposentado; o engine agora roda no container `web-demo`
(`demo/attacks/`).

## Iniciar

1. Stack: `docker compose up -d --build web-demo` (a mesma imagem serve o
   painel; o engine é parte do serviço).
2. Abrir `http://localhost:8011`, fazer login com as credenciais da demo
   (`ADMIN_USERNAME`/`ADMIN_PASSWORD` do `.env`) e abrir a aba
   **Simulação de ataques**.
3. O Docker Desktop precisa estar em execução (a interrupção de serviço
   usa o socket do Docker montado no container).

## Catálogo e alertas esperados

| Ataque | Efeito | Alerta esperado (`for:`) |
|---|---|---|
| Força bruta no serviço | 12× `POST /mode` com token inválido | `AutenticacaoServicoSuspeita` (30s) |
| Força bruta no painel | 8× login com senha errada | `AutenticacaoSuspeita` (10s) |
| Sobrecarga HTTP | Maré em `GET /work` no próprio web-demo | `RecursoCPUElevada` ou `TrafegoAnormal` (30s) |
| Indisponibilidade | Modo offline do web-demo (`POST /mode` com `LAB_TOKEN`) | `HTTPIndisponivel` (15s) |
| Flood DNS | Job de carga limitada da plataforma (`POST /api/lab/traffic`) | `TrafegoAnormal` (30s) |
| Flood SMTP | Job de carga limitada da plataforma (`POST /api/lab/traffic`) | `TrafegoAnormal` (30s) |
| Adulteração de config | Altera arquivo em `./infra` e restaura byte a byte | `ConfiguracaoAlterada` (15s) |
| Interrupção de serviço | `stop`/`start` de container via Docker API (socket montado) | `*Indisponivel` do alvo (15s) |

Alvos por env no container: `DEMO_BASE` (self), `PANEL_BASE` (`api:8000`),
`PROMETHEUS_BASE` (`prometheus:9090`), `INFRA_ROOT`
(`/etc/aularedes/runtime`, montagem `rw` de `./infra`),
`DOCKER_SOCKET` (`/var/run/docker.sock`, com `group_add: [0]`).

## Visualização

- **Cartões do catálogo** com parâmetros (intensidade, duração, alvo) e
  botão Iniciar.
- **Execução**: fases (`agendado → preparando → executando → verificando`),
  contadores em tempo real (tentativas, rejeitadas, requisições,
  segundos restantes) e fila com um ataque por vez.
- **Log do motor ao vivo** via SSE (`/api/events`).
- **Resultado**: consulta `ALERTS{alertstate="firing"}` no Prometheus até
  6 vezes (5 s de intervalo); "Disparou: …", "Não disparou (verificar)"
  ou "Verificação indisponível" (Prometheus fora do ar).

## Segurança e reversibilidade

- A API de ataques exige sessão da demo (401 sem login); nada é exposto
  fora de `127.0.0.1:8011`.
- O socket do Docker no `web-demo` concede acesso root-equivalente ao
  host: aceito por decisão do projeto (laboratório local, ataques 7 e 8
  completos). Não reproduzir em ambiente compartilhado.
- Todos os efeitos são reversíveis: modo do web-demo restaurado, arquivo
  adulterado restaurado byte a byte, serviço reiniciado — inclusive no
  cancelamento. Nenhum ataque toca volumes de dados.
- Fila e histórico vivem em memória: reiniciar o container limpa a fila.

## Código e testes

- Engine: `demo/attacks/` (`catalog`, `engine`, `verification`, `runners`,
  `api`).
- Testes: `backend/tests/test_attack_catalog.py`,
  `test_attack_engine.py`, `test_attack_verification.py`,
  `test_attack_runners.py`, `test_demo_attack_api.py`; frontend:
  `demo-frontend/src/pages/attacksView.test.ts`,
  `attacksPanel.test.tsx`.
- Especificação: `docs/superpowers/specs/2026-11-17-attack-panel-demo-integration-design.md`.
