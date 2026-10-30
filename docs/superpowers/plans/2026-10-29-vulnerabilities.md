# Vulnerabilities Implementation Plan

**Goal:** analisar imagens reais dos quatro serviços, mostrar achados atuais no painel e emitir alertas sem conceder acesso ao Docker à API.
**Architecture:** worker Python padrão no host exporta imagens fixas, scanner Grype isolado produz relatórios normalizados, API lê snapshot somente leitura e exporta métricas; UI filtra/pagina resultados.
**Tech Stack:** Python subprocess/json/threading, Grype 0.121.0, Docker, FastAPI, Prometheus/Alertmanager, React.

## Restrições

Aplicar `docs/superpowers/specs/2026-10-29-vulnerabilities-design.md`. Sem exploração, correção automática, socket Docker nos containers ou segredos em relatórios. Preservar as referências de integridade; qualquer edição em `infra/alerts.yml` requer revisão explícita da nova referência após validar regras.

## 1. Relatório e API

- [x] Criar testes em `backend/tests/test_vulnerabilities.py` para normalização, deduplicação, falhas/expiração/IDs divergentes e contrato protegido; executar e observar falhas.
- [x] Criar `backend/app/vulnerability_report.py`: `normalize_report(raw, sbom, expected_image, scanned_at, expected_config=None)` e leitura validada de metadados, sem conteúdo/raw.
- [x] Criar `backend/app/vulnerabilities.py`: coletor de manifesto/relatórios limitados, estado por serviço e paginação, snapshots e métricas; integrar configuração/main sem quebrar outros monitores.
- [x] Verificar testes e falha isolada da fonte.

## 2. Worker local

- [x] Criar testes em `backend/tests/test_vulnerability_worker.py` para comandos fixos sem shell/socket, lock e escrita atômica/erros.
- [x] Criar `scripts/scan_vulnerabilities.py`: inventário Compose, rodada deduplicada de imagens, normalize/persist, heartbeat independente, watch/retry, limites e cleanup de arquivos conhecidos.
- [x] Integrar pasta de relatórios no Compose/configure e inicialização oculta no `scripts/start.ps1`; validar scan real sem volumes dos serviços.

## 3. Interface, alertas e entrega

- [x] Criar estados/testes frontend e `Vulnerabilities.tsx`, incorporar à Segurança com filtros fixos e paginação; validar build.
- [x] Adicionar regras e testes promtool, revisar/aprovar somente novo hash conhecido das regras; reconstruir stack preservando dados/referências.
- [x] Executar análise real e verificar contratos, inventário/imagem, contagens e alertas/e-mails aplicáveis: nove verificações iniciais passaram em 29/10.
- [x] Revisão independente usando requesting-code-review; corrigir limites de saída e encerramento de subprocessos, reproduzidos em testes.
- [x] Concluir teste integrado de interrupção/recuperação do coletor e persistência final após recuperação do ambiente Docker: 18 verificações passaram em 30/10.
- [ ] Conferir desktop/mobile e evidências quando a automação visual estiver disponível.
- [x] Atualizar README, arquitetura, roadmap, validação e runbook.
- [x] Salvar commit local com o estado validado e pendências explícitas.
