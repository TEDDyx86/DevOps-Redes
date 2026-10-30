# Incidentes e reconciliação do histórico

## O que foi corrigido

O Alertmanager envia eventos firing/resolved pelo webhook autenticado. Cada ciclo tem chave `(fingerprint, started_at)`. Uma interrupção pode impedir a chegada da resolução de um ciclo; antes da correção, ciclos posteriores resolvidos não encerravam o registro antigo.

Em 30/10/2026, havia 58 registros e cinco marcados firing. Três eram ciclos históricos de 29/10, dos serviços HTTP, PostgreSQL e SMTP, com resoluções posteriores já persistidas. A migração preservou todas as 58 chaves e os textos originais, reconciliou esses três e manteve os dois alertas altos atuais de HTTP/SMTP. Reinícios podem gerar ciclos novos de alertas quando suas métricas ficam temporariamente indisponíveis; esses registros também são preservados.

## Fontes e limites da evidência

| Origem da resolução | Término original | Apresentação |
|---|---|---|
| Webhook direto, `resolution_source=alertmanager` | `ended_at` recebido e validado | Resolvido |
| Resolução posterior do mesmo alerta, `later_resolved_event` | `ended_at=null`; horário original desconhecido | Reconciliado, com nota e horário da confirmação posterior |

Não basta o alerta desaparecer do Prometheus, a fonte ficar indisponível ou chegar outro evento firing. Para reconciliar, é necessário um ciclo direto resolved posterior, com **mesmo fingerprint, nome, serviço e severidade**. Seu início precisa ser estritamente posterior ao original; início/fim devem ter timezone, estar em ordem e o fim não pode ultrapassar o relógio atual em mais de cinco segundos. Os instantes são comparados em UTC. A implementação considera uma origem Alertmanager no laboratório local.

Uma resolução inferida não serve de prova para outra inferência. A API expõe `reconciled_at`, `resolution_evidence_started_at` e `resolution_evidence_ended_at`. O painel mantém o início original e informa que seu término não foi recebido. Se chegar a resolução direta válida daquele ciclo antigo, ela substitui a inferência e preenche o término verdadeiro. Um firing atrasado não reabre um incidente resolvido; um ciclo recente ainda firing permanece aberto.

Resoluções novas inválidas são rejeitadas com HTTP 422 antes da persistência; a ingestão direta também rejeita o lote inteiro, preservando a prova anterior. Datas inválidas em registros legados são conservadas, sem serem usadas como evidência. A reconciliação não envia e-mail sintético nem demonstra correção de uma vulnerabilidade: as análises de imagem e os protocolos continuam sendo verificados separadamente.

Referência primária: [campos de notificação do Alertmanager](https://prometheus.io/docs/alerting/latest/notifications/), incluindo fingerprint, início, término e estado do evento. A regra de reconciliação é uma decisão desta aplicação; não é uma funcionalidade de backfill do Alertmanager.

## Persistência e aplicação

O IncidentStore faz migração aditiva idempotente e reconciliação em uma transação `BEGIN IMMEDIATE` ao abrir o banco. Repete a reconciliação dentro da transação de cada lote recebido. Um índice parcial dos registros firing evita percorrer todos os ciclos resolvidos quando não há candidato; as provas são consultadas por identidade. A alteração não depende de nova chamada ao Prometheus e não altera os segredos do webhook.

Antes de atualizar uma instalação com histórico, fazer um backup consistente do SQLite. Não copiar apenas o arquivo enquanto a aplicação escreve, nem redirecionar bytes SQLite usando modos de texto do PowerShell. Exemplo na raiz:

```powershell
@'
import subprocess
from datetime import datetime, timezone
from pathlib import Path
code = "import sqlite3,sys; src=sqlite3.connect('/data/incidents.sqlite'); dst=sqlite3.connect(':memory:'); src.backup(dst); sys.stdout.buffer.write(dst.serialize())"
data = subprocess.check_output(['docker','compose','exec','-T','api','python','-c',code], timeout=30)
assert data.startswith(b'SQLite format 3\x00')
path = Path('.runtime/backups') / ('incidents-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.sqlite')
path.parent.mkdir(parents=True, exist_ok=True)
path.write_bytes(data)
'@ | .\.venv\Scripts\python.exe -
```

Conferir `PRAGMA integrity_check` na cópia. O backup é local e ignorado pelo Git. Construir e aplicar somente a API:

```powershell
docker compose build api
if ($LASTEXITCODE -ne 0) { throw 'Build falhou; não aplicar.' }
docker compose up -d --no-deps --no-build --wait api
```

Manter o volume `incidents`; não usar `down -v`. A imagem/volume dos serviços monitorados não precisa mudar. Depois recarregar o navegador para carregar o frontend atualizado.

Se a migração falhar, sua transação deve ser revertida; consultar logs antes de permitir nova atualização. **Voltar apenas à imagem antiga não é uma reversão segura do esquema:** versões anteriores usam INSERT posicional com nove colunas, enquanto a migração acrescenta campos. Preservar o banco atual e o backup, pausar a API e investigar compatibilidade/recuperação, incluindo quaisquer eventos recebidos após o backup. Não sobrescrever automaticamente o histórico corrente com uma cópia antiga.

## Conferência

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_incident_reconciliation.py backend/tests/test_platform.py -q
cd frontend
npm test
npm run build
```

O teste de custo usa 8.000 ciclos resolvidos e limite de instruções da VM SQLite, sem cronômetro dependente da máquina. Os demais casos incluem banco legado, persistência, identidade, UTC/fuso/fração, futuro, eventos fora de ordem, lote inválido, rollback, concorrência, HTTP 422 e apresentação dos três estados.

Na instalação já atualizada, conferir Incidentes: **Reconciliado** deve mostrar o evento de confirmação posterior e término original desconhecido. Comparar alertas atuais com Prometheus, sem apagar eventos para ajustar o contador. Na seção Segurança, confirmar imagem/data/base das análises, filtros, paginação e cinco achados médios/baixos do PostgreSQL. Os avisos altos HTTP/SMTP continuam sendo reais e não devem desaparecer por essa correção.

O roteiro existente `scripts/verify_lab.py` demonstra alertas e resoluções diretas reais por HTTP, com e-mails locais. A evidência específica da migração fica em `docs/evidencias/incident-reconciliation.json`; os artefatos completos do ensaio e da verificação desta sessão permanecem em `tmp/`, sem injeção de incidentes fictícios no ambiente em execução.
