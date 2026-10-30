# Atualização preventiva do utilitário gosu

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remover os três avisos críticos de versão Go da imagem PostgreSQL, preservando o banco e a detecção real de vulnerabilidades.

**Architecture:** Imagem derivada da mesma base PostgreSQL 17.11/Alpine 3.24, fixada por digest. Compilar o mesmo código gosu 1.19, verificado por SHA-256, com Go 1.27.3 fixado por digest; copiar apenas o binário e sua licença para a imagem final. Sem alterações no servidor SQL, entrypoint, volume, configuração, scanner, severidades ou supressões.

**Tech Stack:** Docker multi-stage, Go, PostgreSQL 17.11, Syft/Grype, Python para verificação local.

## Restrições

- Avisos GO-2026-4337/6604/6612 vêm de `stdlib go1.24.6` no gosu; não demonstram exploração do PostgreSQL. Conferir avisos oficiais e política de segurança do gosu.
- Preservar dependências do gosu via go.mod/go.sum; não incluir compilador ou código-fonte na imagem final. Não remover símbolos necessários à análise Go com `-s`.
- Nova análise do candidato deve ter inventário real, mesmo image ID e zero crítico antes de trocar o serviço.
- Manter a análise em funcionamento; analisar candidato com worker separado em pasta temporária, sem publicar inventário falso nem disputar o cache com atualização simultânea.
- Fazer backup lógico local ignorado pelo Git, registrar volume original e comparar todos os dados com a carga pausada durante a troca. Nunca remover ou reinicializar o volume existente.
- Verificar primeiro inicialização em volume temporário novo, inclusive permissões/usuário e scripts de bootstrap; depois volume real e alertas.
- Não alterar arquivos de trabalho concorrente, `.env` ou referências de integridade.

## Tarefa 1: Candidato reproduzível

Arquivos: criar `infra/postgres-image/Dockerfile`; ajustar apenas o serviço postgres em `compose.yaml` após aprovação técnica do candidato.

- [x] Conferir imagem oficial: mesma versão Go antiga; relatório inicial real com três críticos.
- [x] Consultar fontes oficiais: TLS, junção Windows e HTTP/2; fix Go 1.27.3 atual.
- [x] Construir candidato com base, compilador e fonte fixados.
- [x] Verificar versão gosu, usuário/grupo/HOME, exec/sinais e inicialização nova com papéis/tabela.
- [x] Analisar candidato isolado e exigir ausência dos três avisos, sem supressões.

## Tarefa 2: Troca preservando dados

Arquivos: `compose.yaml`; backup e evidência privada em `.runtime/backups/` e `tmp/`.

- [x] Registrar imagem, volume e relatório antes; pausar API para suspender carga SQL.
- [x] Fazer pg_dump custom de lab_network e dump de globais, sem imprimir conteúdo; validar restauração em banco temporário, inclusive papéis e dados.
- [x] Comparar impressão digital de toda a tabela sem carga concorrente; substituir somente PostgreSQL mantendo o volume original.
- [x] Confirmar impressão digital, versão 17.11 e volume; retomar API após sucesso ou reversão validada. Se ambos falharem, manter carga pausada. Preservar imagem original para reversão.
- [x] Esperar inventário/relatório da imagem efetivamente em execução, aviso crítico resolvido e avisos restantes corretamente classificados.

## Tarefa 3: Validação e documentação

Arquivos: `docs/runbook-postgres-remediation.md`, `docs/evidencias/postgres-remediation.json`, `README.md`, `docs/roadmap.md`, `docs/validacao.md`.

- [x] Executar `scripts/verify_postgres.py`: parada, recuperação, dados, permissões e notificações reais.
- [x] Executar `scripts/verify_vulnerabilities.py`: identidade, páginas, contagens, métricas, notificações, persistência e quatro protocolos.
- [x] Registrar contagens antes/depois e limites, procedimentos reproduzíveis e rollback sem exclusão de volume.
- [x] Revisão independente conforme skill requesting-code-review; corrigir achados relevantes antes de concluir.
- [x] Revisar diff/segredos, salvar somente arquivos desta tarefa em commit local.

## Resultado

Concluídos 14 checks SQL, 11 de vulnerabilidades, cinco direcionados e quatro de inicialização, além de backup restaurado. Mesmos 50 pacotes; zero crítico/alto, quatro médios e um baixo. Mesma impressão digital de todos os dados no mesmo volume. Evento atual resolvido, com e-mail; permanece um incidente histórico órfão de 29/10 para reconciliação futura, preservado e documentado na evidência. QA visual continua pendente.

Atualização posterior em 30/10: incidente histórico e QA visual atendidos na etapa de reconciliação. Três ciclos históricos foram reconciliados por prova posterior direta, preservando os registros e o término desconhecido. Ver docs/runbook-incidentes.md e docs/evidencias/incident-reconciliation.json. A descrição acima registra o estado observado ao concluir a atualização PostgreSQL.
