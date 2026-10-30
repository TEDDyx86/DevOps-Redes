# Reconciliação de incidentes — plano

**Goal:** corrigir o incidente órfão e prevenir recorrência com evidência explícita, preservando o histórico.
**Architecture:** migração SQLite e reconciliação transacional por evento posterior resolvido; UI distingue reconciliação de término diretamente recebido.
**Tech Stack:** Python/sqlite3, FastAPI, React/TypeScript, pytest/Vitest, Docker e navegador.

Aplicar o contrato de `../specs/2026-10-30-incident-reconciliation-design.md`. Executar nesta sessão; usuário autorizou o próximo passo. Sem alteração de regras, supressões ou referências de configuração.

## 1. Persistência e API

Arquivos: `backend/app/storage.py`, novo `backend/tests/test_incident_reconciliation.py`.

- [x] Reproduzir caso real e salvar snapshot antes em tmp.
- [x] Escrever e executar testes falhando para perda de resolução, migração, datas/identidade e eventos atrasados.
- [x] Implementar migração e reconciliação conservadora, dentro da transação de ingestão e na inicialização.
- [x] Testar autenticação/contrato do webhook, persistência, concorrência e falha de commit sem estado parcial.

## 2. Apresentação

Arquivos: `frontend/src/types.ts`, `frontend/src/components.tsx`, novo teste de renderização de incidentes.

- [x] Teste falhando para nota/estado Reconciliado e preservação de estados normais.
- [x] Apresentar motivo/instante da confirmação e término desconhecido, usando componentes/estilos existentes.
- [x] Executar suites backend/frontend e build.

## 3. Verificação real e entrega

Arquivos: roteiro integrado desta sessão em `tmp/verify_incident_reconciliation.py` (ignorado pelo Git, sem injetar incidentes), documentação e evidência pública. Regressão reproduzível também usa `scripts/verify_lab.py` e os testes versionados.

- [x] Fazer backup SQLite consistente e reconstruir somente API, mantendo volumes e imagens dos serviços.
- [x] Conferir evento órfão reconciliado, evidência válida, linhas preservadas, ciclos recentes operacionais e persistência após restart.
- [x] Conferir Incidentes/Segurança, desktop/mobile, filtros/páginas e console; guardar capturas sem segredos.
- [x] Revisão independente conforme requesting-code-review; corrigir achados relevantes.
- [x] Atualizar runbook/validação/roadmap, revisar diff e salvar commit local excluindo arquivo preexistente do usuário.

## Resultado

128 testes backend passaram, um caso POSIX pulado no Windows; 18 frontend e build aprovados. Nove verificações de migração/persistência e 12 HTTP reais com notificações concluídas. Todas as 58 chaves/textos originais preservados, três ciclos reconciliados e dois alertas altos reais mantidos. QA real desktop/mobile concluído, oito verificações visuais e console sem erros/avisos. Revisão encerrou os dois P2 após reproduções antes da correção. Evidência pública em docs/evidencias/incident-reconciliation.json.
