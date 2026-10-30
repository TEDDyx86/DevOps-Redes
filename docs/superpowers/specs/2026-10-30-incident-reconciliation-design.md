# Reconciliação de incidentes históricos

## Problema e decisão

O SQLite identifica cada ciclo por `(fingerprint, started_at)`. A resolução de um ciclo posterior não fecha um anterior cujo webhook de resolução se perdeu durante interrupção. Em 30/10, existe um evento crítico PostgreSQL de 29/10 ainda firing, apesar de eventos posteriores resolvidos do mesmo alerta.

Alternativas consideradas: fechamento manual apagaria a evidência causal e não corrigiria recorrências; consultar o estado atual do Prometheus adicionaria dependência e não comprovaria o horário original de término. A solução escolhida usa exclusivamente uma resolução posterior já recebida pelo webhook autenticado e persistida no mesmo banco.

## Contrato

- Reconciliar somente registros firing que tenham resolução posterior direta com mesmo fingerprint, nome, serviço e severidade, início estritamente posterior ao original e término válido, com timezone, não anterior ao próprio início nem no futuro além de cinco segundos. Comparar instantes UTC, nunca strings lexicograficamente.
- Não interpretar falta de dados, Prometheus indisponível, silêncio ou evento firing posterior como recuperação. Ciclo mais novo ainda firing permanece aberto. Resoluções inferidas não servem como prova para outros registros.
- Executar na abertura do IncidentStore (migração idempotente) e na mesma transação de ingestão de novos eventos. Preservar todos os registros, chaves, textos e início; não inventar o término original.
- O registro reconciliado passa a resolved, com `ended_at=null`, `resolution_source=later_resolved_event`, `reconciled_at` e início/término do evento usado como evidência. Resolução direta usa `resolution_source=alertmanager`. Um webhook direto atrasado pode preencher o término verdadeiro e substituir a inferência; firing atrasado não reabre nada.
- Resoluções diretas novas também precisam de início/fim com fuso, ordem válida e término não futuro além de cinco segundos. Webhook inválido recebe 422; ingestão direta inválida rejeita o lote inteiro sem apagar uma prova anterior. Registros legados inválidos são preservados, mas não servem de prova.
- Índice parcial para registros firing e busca de provas por identidade, começando pelos candidatos. Sem candidatos, retornar imediatamente, sem consulta correlacionada sobre todo o histórico. Verificar custo com 8.000 ciclos já resolvidos e orçamento de instruções SQLite.
- Campos adicionais opcionais no contrato TypeScript. Mostrar **Reconciliado**, com nota de resolução posterior, instante de confirmação e término original desconhecido. Demais estados mantêm a apresentação existente. Não enviar e-mails sintéticos nem criar alertas por corrigir o histórico.
- Preservar volume SQL, referências de integridade e secrets. Backup SQLite consistente antes de atualizar a API. Não incluir `gerarrelatório.py`, arquivo de trabalho preexistente, no commit.

## Validação

Reproduzir o caso em testes antes da implementação: migração de banco antigo com resolução posterior, persistência/idempotência, UTC/offset/fração, outras identidades, futuro/ausência/término inválido, ciclo recente ainda firing, eventos atrasados e atualização transacional. Verificar integração do webhook/API e renderização da nota no HTML. Depois reconstruir apenas a API e seu frontend, confirmar correção do caso real sem excluir linhas, persistência após restart, estado real dos quatro protocolos e alertas/notificações. Conferir Incidentes e Segurança em desktop/mobile, filtros/paginação e console; guardar evidências sem credenciais.
