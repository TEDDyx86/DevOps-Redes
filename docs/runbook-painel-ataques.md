# Runbook — Painel de Ataques

Ferramenta do laboratório para disparar ataques controlados e acompanhar em tempo real os eventos e alertas correspondentes no Prometheus. Desde a migração para o dashboard principal, o painel vive **dentro da plataforma de monitoramento**, em `http://localhost:8000/#attacks` (protegido pela sessão administrativa e validação CSRF), deixando a loja pública `web-demo` (`http://localhost:8011`) dedicada apenas ao e-commerce 8-bit monitorado.

## Iniciar e pré-requisitos de demonstração

1. Subir a stack completa (contêineres + coletores locais):
   - `./scripts/start.ps1` (ou `docker compose up -d --build --wait` acompanhado de `scan_vulnerabilities.py` e `collect_resources.py`).
2. Abrir `http://localhost:8000`, autenticar com `ADMIN_USERNAME`/`ADMIN_PASSWORD` (do `.env`) e acessar a aba **Ataques** no menu lateral.
3. **Pré-requisitos importantes:**
   - Para `adulteracao-config` disparar `ConfiguracaoAlterada`, aprove antes as referências SHA-256 em `#security` → **Integridade das configurações**.
   - Para `sobrecarga-http`, `flood-dns`, `flood-smtp` e `flood-postgres` dispararem `TrafegoAnormal`, aguarde ~2 minutos após o boot até que os serviços saiam de `Aprendendo` para `Volume normal` em `#security` → **Tráfego dos serviços**.
   - O Docker Desktop precisa estar em execução (o ataque `interrupcao-servico` usa o socket do Docker montado no container `api`).

## Catálogo e alertas esperados (11 vetores)

| ID | Ataque | Efeito | Alerta esperado (`for:`) |
|---|---|---|---|
| `bruteforce-servico` | Força bruta no serviço | Rajada + sustentação de `POST /mode` com token inválido no `web-demo` | `AutenticacaoServicoSuspeita` (30s) |
| `bruteforce-painel` | Força bruta no painel | Logins com senha errada em `/api/auth/login` no dashboard | `AutenticacaoSuspeita` (10s) |
| `sobrecarga-http` | Sobrecarga HTTP na loja | Maré concorrente de `GET /work` no `web-demo` | `TrafegoAnormal` (30s) |
| `lentidao-http` | Degradação / Latência HTTP | Ativa modo `slow` (+850 ms) no `web-demo` e restaura ao normal | `HTTPLento` (30s) |
| `indisponibilidade-http` | Indisponibilidade da loja | Ativa modo `offline` (HTTP 503) no `web-demo` e restaura ao normal | `HTTPIndisponivel` (15s) |
| `varredura-404` | Varredura de rotas (Erros 404) | Scanner de `/api/products/scan-...` gerando erros 4xx reais nas métricas HTTP | *(Telemetria HTTP, sem alerta específico)* |
| `flood-dns` | Flood DNS | Rajada controlada de consultas UDP contra CoreDNS (`dns:1053`) | `TrafegoAnormal` (30s) |
| `flood-smtp` | Flood SMTP | Envio controlado para `aluno@aularedes.test` no SMTP local (`smtp:2525`) | `TrafegoAnormal` (30s) |
| `flood-postgres` | Flood de consultas SQL | Rajada controlada de `SELECT 1` no PostgreSQL (`postgres:5432`) | `TrafegoAnormal` (30s) |
| `adulteracao-config` | Adulteração de configuração | Altera arquivo monitorado em `./infra` e restaura byte a byte ao final | `ConfiguracaoAlterada` (15s) |
| `interrupcao-servico` | Interrupção de serviço | `stop`/`start` de container (`dns`, `smtp`, `web-demo` ou `postgres`) via Docker API | `DNSIndisponivel` / `SMTPIndisponivel` / `HTTPIndisponivel` / `PostgreSQLIndisponivel` (15s) |

Alvos configurados por variáveis de ambiente no container `api`: `DEMO_URL` (`http://web-demo:8001`), `PANEL_BASE` (`http://127.0.0.1:8000`), `PROMETHEUS_URL` (`http://prometheus:9090`), `INFRA_WRITE_ROOT` (`/etc/aularedes/runtime`, montagem `rw` de `./infra`) e `DOCKER_SOCKET` (`/var/run/docker.sock`, com `group_add: [0]`).

## Visualização e fila de execução

- **Filtros por categoria:** `Todos`, `Loja / HTTP`, `Autenticação` e `Banco / Rede / Infra`.
- **Cartões do catálogo:** parâmetros validados (limites min/max ou opções fixas) e botão **Iniciar ataque**.
- **Execução sequencial:** um ataque por vez (`agendado → preparando → executando → verificando`), contadores em tempo real e botão **Interromper**.
- **Log do motor ao vivo:** via SSE (`/api/events`).
- **Verificação automática:** consulta `ALERTS{alertstate="firing"}` no Prometheus durante o hold (com encerramento rápido ao detectar `firing`) e até 6 vezes após a conclusão, exibindo `Disparou: …`, `Não disparou: …` ou `Prometheus indisponível durante a verificação`.

## Segurança e reversibilidade

- Toda a API (`/api/attacks`, `/api/queue`, `/api/attacks/{id}/start`, `/api/queue/{id}/cancel`, `/api/events`) exige sessão autenticada do painel (`401` sem login) e proteção CSRF nas mutações, vinculada exclusivamente a `127.0.0.1:8000`.
- O container `api` recebe `/var/run/docker.sock` e `./infra` em modo leitura/escrita exclusivamente para executar de forma automatizada e reversível os cenários `interrupcao-servico` e `adulteracao-config` neste laboratório acadêmico local (`127.0.0.1`). A coleta de métricas de recursos e a análise de vulnerabilidades continuam isoladas nos workers do host. Não reproduzir a exposição do socket em ambiente compartilhado/produção.
- Todos os efeitos são reversíveis (inclusive ao cancelar): modo HTTP do `web-demo` volta a `normal`, arquivos adulterados são restaurados byte a byte e contêineres parados são reiniciados automaticamente. Nenhum ataque altera volumes de dados.
- Fila e histórico vivem em memória: reiniciar o container `api` limpa a fila.

## Código e testes

- **Backend (Engine):** `backend/app/attacks/` (`catalog.py`, `engine.py`, `verification.py`, `runners.py`, `api.py`).
- **Testes Backend:** `backend/tests/test_attack_catalog.py`, `test_attack_engine.py`, `test_attack_verification.py`, `test_attack_runners.py`, `test_demo_attack_api.py`.
- **Frontend e Testes:** `frontend/src/Attacks.tsx`, `frontend/src/attacks.test.tsx`, `frontend/e2e/navegacao.spec.ts`.
