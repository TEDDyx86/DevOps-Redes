# Integrity Implementation Plan

**Goal:** detectar alterações/ausência de configurações e demonstrar incidente, e-mail e recuperação.
**Architecture:** lista fixa de arquivos montados somente leitura, SHA-256 e referência aprovada em SQLite independente dos serviços. Coletor publica snapshots após commit e registra transições. API protege aprovação; UI permite revisar metadados.
**Tech Stack:** Python hashlib/os/sqlite3, FastAPI, Prometheus/Alertmanager, React, Docker Compose.

## Restrições

Seguir `docs/superpowers/specs/2026-10-29-integrity-design.md`. Não ler/retornar segredos nem aceitar caminhos livres. Preservar o comportamento atual dos quatro serviços. Executar rebuilds e demonstrações sequencialmente.

## 1. Detector e uso das configurações

- [x] Escrever testes de referência explícita, persistência, mudanças/ausência/erro, deduplicação, aprovação atômica/obsoleta, links/especiais/tamanho e publicação após commit; observar falha antes de implementar.
- [x] Criar `backend/app/integrity.py`, `integrity_files.py`, testes `backend/tests/test_integrity.py`.
- [x] Extrair configurações HTTP/SMTP sem alterar limites; criar arquivo PostgreSQL e montar diretórios reais somente leitura no Compose.
- [x] Integrar coletor independente e rotas protegidas; validar API e protocolos existentes.

## 2. Aprovação e interface

- [x] Adicionar `frontend/src/Integrity.tsx`, estado/tipos e testes de expiração/exibição; incorporar à Segurança.
- [x] Mostrar hashes/estados sem conteúdo, eventos e formulário de aprovação com token, IDs fixos e hash observado.
- [x] Validar testes, build, desktop/mobile e revisão independente.

## 3. Demonstração e entrega

- [x] Adicionar regras e `scripts/verify_integrity.py`, validar promtool e iniciar stack.
- [x] Aprovar referências iniciais conhecidas, alterar de forma inofensiva um arquivo por serviço, confirmar quatro alertas/e-mails e restaurar tudo em finally.
- [x] Verificar persistência, deduplicação e operação normal após recuperação; documentar limites e evidências.
- [x] Salvar commit da etapa.
