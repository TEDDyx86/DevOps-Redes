# Cobertura de Requisitos — Especificação

Corrige as 4 lacunas da análise contra o PDF "Plataforma de Monitoramento DevOps".

## 1. Conexões ativas HTTP (métrica ausente)
- Demo publica Gauge `demo_http_requests_inflight` (requests em andamento, todos os
  caminhos que passam pelo middleware `instrument`), decrementado em `finally`.
- Backend (`/api/overview` e `/api/service`) expõe `service.connections`
  (valor instantâneo; `null` quando demo stale ou Prometheus indisponível).
- Frontend: `ServiceSummary.connections: number | null`; página Serviço HTTP
  mostra tile "Conexões ativas".

## 2. Playbook de incidentes
- Novo `docs/playbook-incidentes.md`: fluxo de resposta (detectar → conter →
  diagnosticar → remediar → comunicar → revisar), tabela por alerta apontando ao
  runbook específico, níveis verde/amarelo/vermelho com ação e-mail.

## 3. Guia de instalação dedicado
- Novo `docs/instalacao.md`: pré-requisitos, `scripts/configure.py`, `docker
  compose up`, verificação das portas, e-mail (Mailpit), parada/preservação.

## 4. Testes E2E de navegação (Playwright)
- `frontend/` ganha `@playwright/test` (`npm run test:e2e`), config apontando
  para `http://127.0.0.1:8000`, credenciais do `.env`.
- Teste de navegação: login pela UI → percorre as 9 páginas do sidebar →
  valida marcadores reais de cada página (health strip, métricas, incidentes).

## Contratos inalterados
- Endpoints existentes do demo (`/work`, `/health`, `/metrics`, `/mode`) e do
  dashboard: apenas adições de campo (`service.connections`).
- Visual Workbyte e aba de ataques `:8011` intocados.
