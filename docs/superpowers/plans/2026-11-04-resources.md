# Recursos — plano de implementação

**Goal:** medir CPU, RAM e I/O reais dos quatro serviços, com histórico e alertas.
**Architecture:** SDK local isolado → snapshot somente leitura → API/métricas → Prometheus/painel.
**Tech Stack:** Python padrão + Docker SDK local, FastAPI, Prometheus, React/TypeScript.

Aplicar o contrato de `../specs/2026-11-04-resources-design.md`. Usuário autorizou esta etapa; executar nesta sessão.

## 1. Medição e coletor

Arquivos: backend/app/resource_report.py, scripts/collect_resources.py, requirements-resources.lock.txt, testes específicos; configure.py/start.ps1/compose.yaml.

- [x] Ler escopo e investigar fontes/alternativas oficiais; verificar SDK em venv isolada.
- [x] Testes falhando para normalização, deltas e leituras/execuções inválidas.
- [x] Implementar conversão, worker de leitura local, dependências fixadas e snapshot atômico; validar medições reais.
- [x] Integrar configuração e inicialização oculta, sem socket na API ou mudança de volumes dos serviços.

## 2. API, histórico e alertas

Arquivos: backend/app/resources.py, resource_metrics.py, config.py/main.py; infra/alerts.yml e fixture promtool.

- [x] Testes falhando de validade, campos ausentes, autenticação, métricas e histórico com lacunas.
- [x] Implementar leitor/registry/API protegida e histórico por serviço/período.
- [x] Acrescentar quatro regras e testes isolados, validar configurações.

## 3. Interface

Arquivos: frontend/src/Resources.tsx, resourceState.ts/testes, App.tsx/types.ts/components.tsx/styles.css.

- [x] Testes de estado/expiração e apresentação; implementar página seguindo os componentes existentes.
- [x] Executar testes/backend/frontend e build.

## 4. Verificação e entrega

Arquivos: scripts/verify_resources.py, runbook, documentação e evidência sem segredos.

- [x] Revisão independente conforme requesting-code-review; corrigir achados.
- [x] Aplicar API/regras preservando serviços; revisar/aprovar somente hash conhecido de alerts.yml.
- [x] Demonstrar alerta/recuperação com CPU real e perda/recuperação do coletor; confirmar quatro protocolos, dados SQL e persistência.
- [x] QA desktop/mobile, console, histórico, filtros e capturas.
- [x] Atualizar documentação/roadmap, revisar diff e commit local sem arquivos de trabalho do usuário.

## Resultado

162 testes backend passaram (um caso POSIX pulado no Windows), 20 frontend, build TypeScript/Vite e três cenários promtool/27 regras. Vinte verificações integradas com carga CPU real, alertas/e-mails e parada/recuperação do coletor; reinício imediato adicional confirmado com observações posteriores ao retorno em cerca de 9 s. QA desktop 1439×1000 e celular 390×844, sem transbordamento de página nem erros/avisos no console.

Revisão independente encerrada após regressões para falha isolada/duplicidade, cache cgroup v1, número JSON extremo, contrato de fonte ausente e reinício do worker. Quatro imagens/identidades monitoradas e 1.000 linhas SQL preservadas. Evidência pública: `docs/evidencias/resources.json`; operação: `docs/runbook-recursos.md`. `gerarrelatório.py` preexistente permanece fora da entrega.
