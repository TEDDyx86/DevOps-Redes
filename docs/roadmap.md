# Roadmap individual: 20 dias

Data inicial: 28/10/2026. Entrega considerada: 17/11/2026. A implementação pode antecipar tarefas; o calendário é uma orientação, não uma estimativa garantida de esforço.

| Dias | Entrega | Critério de conclusão |
|---|---|---|
| 1–6 | HTTP e plataforma base | Dashboard, coleta real, histórico, alerta, e-mail e recuperação verificados |
| 7–10 | Banco, DNS e SMTP | Cada serviço com coleta real, identificação das métricas e falha demonstrável |
| 11–14 | Segurança e acabamento funcional | Tráfego anormal, autenticação falha, mudança de configuração e vulnerabilidade conhecida por serviço |
| 15–17 | Testes e documentação | Navegação desktop/mobile, instalação reproduzível, procedimentos e relatório completo |
| 18–20 | Correções e apresentação | Ensaio com falhas controladas, evidências e revisão final do PDF |

## Próximas tarefas

1. PostgreSQL integrado em volume separado: disponibilidade, conexão + SELECT 1, conexões, commits/s, rollbacks/s, tamanho e comandos SQL/s do usuário de laboratório. CPU/memória/I/O de blocos foram acrescentados em 04/11; latência de disco, pools e consultas lentas exigem instrumentação complementar. O armazenamento de incidentes permanece independente em SQLite.
2. CoreDNS integrado: zona local, sondas UDP/TCP, consultas/s, latência, p95 do servidor, NXDOMAIN separado dos erros e alerta/recuperação. A resolução do host permanece inalterada.
3. SMTP integrado com Python/aiosmtpd e fila SQLite persistente: aceitação, entrega, retry, rejeição, volume, histograma e canal de alertas independente. A proposta inicial de Postfix foi substituída pelo MTA local instrumentado. Paradas do receptor e do SMTP verificadas, com recuperação das pendências.
4. Autenticação do painel integrada: login, sessão revogável, contagem de falhas por conta/IP, bloqueio temporário, eventos e alerta/e-mail. Em 29/10, comparação de tráfego com referência fixa, integridade de oito configurações e análise real de vulnerabilidades das imagens dos quatro serviços integradas. Syft/Grype separados da API, validade explícita, filtros, alertas e e-mails. Achados altos/críticos permanecem para triagem; os próximos monitores incluem autenticação dos serviços e métricas complementares de recursos.
5. Relatório ABNT, requisitos rastreados ao PDF, testes e roteiro da apresentação.

## Atualização de 30/10 e próximas pendências

Em 30/10, a triagem dos três avisos críticos PostgreSQL levou à recompilação preventiva do gosu com Go 1.27.3, preservando PostgreSQL 17.11 e o volume. Resultado: zero crítico/alto e cinco médio/baixo, com a mesma base e 50 pacotes. Backup restaurado, comparação integral dos dados e regressões SQL/vulnerabilidades concluídos; detalhes em [validação](validacao.md) e [runbook](runbook-postgres-remediation.md).

Também em 30/10, foram reconciliados três ciclos históricos de HTTP/PostgreSQL/SMTP por evidência direta posterior, preservando as 58 chaves originais. O contador manteve apenas os dois alertas altos reais de HTTP/SMTP. Passaram 128 testes backend (um caso POSIX pulado no Windows), 18 frontend, nove verificações da migração e 12 HTTP com alertas/e-mails. QA visual de Incidentes/Segurança concluído em desktop e celular, incluindo filtros, paginação, console e ausência de transbordamento. [Procedimento e limites](runbook-incidentes.md).

## Atualização de 04/11: recursos

CPU em núcleos, working set e I/O de blocos dos quatro serviços implementados com SDK Docker em coletor local isolado, sem socket na API. Página Recursos com histórico e estados parcial/desconhecido, métricas de disponibilidade por campo e quatro regras de atenção. A configuração de alertas passou de 23 para 27 regras; somente sua referência SHA-256 foi atualizada após revisão e promtool.Passaram 162 testes backend (um caso POSIX pulado no Windows), 20 frontend e três cenários promtool. Vinte verificações integradas confirmaram carga CPU real limitada, incidente/e-mail, recuperação, interrupção/retomada do coletor, quatro protocolos, oito configurações e 1.000 linhas SQL. O reinício imediato do worker também foi verificado com medições novas após seu retorno. QA desktop/celular concluído, com filtros, gráficos, rolagem interna e console sem erros/avisos. [Evidências](evidencias/resources.json) e [runbook](runbook-recursos.md).

## Atualização de 09/11: métricas finais

Pendências técnicas do PostgreSQL resolvidas: consultas lentas por `pg_stat_statements` (média > 100 ms), conexões ativas/ociosas por `pg_stat_activity`, latência de disco por contadores `pg_stat_io` (leitura e gravação separadas) e crescimento projetado do banco em GiB/dia. Alertas novos: `PostgreSQLConsultasLentas` e `PostgreSQLDiscoLento`. Falhas de token no serviço HTTP monitorado agora têm contador `demo_auth_attempts_total` e o alerta `AutenticacaoServicoSuspeita` (cinco em um minuto, 30 s). O coletor de recursos publica o espaço livre do volume do projeto (`shutil.disk_usage`, schema 2 do snapshot) com o alerta `RecursoDiscoLivreBaixo` abaixo de 2 GiB; a página Recursos exibe o valor. Alertas passaram de 27 para 31 regras, com quatro cenários sintéticos promtool novos. Passaram 165 testes backend, 20 frontend e build do frontend sem erros.

Próximas pendências: relatório ABNT com rastreabilidade ao PDF; roteiro da apresentação. A triagem das vulnerabilidades das imagens novas foi concluída em 11/11 com uma remediação real: a imagem PostgreSQL ganhou 1 crítico/12 altos com a base de avisos atualizada e foi corrigida fixando as versões publicadas do Alpine no Dockerfile (zlib, krb5-libs, libxslt) e atualizando o pin da base — 0 críticos/0 altos após reanálise, dados preservados. Um bug do worker (corrida `os.replace`/leitor no Windows) foi corrigido com retry testado; contêineres órfãos de imagens não exportáveis foram recriados. Achados residuais triados e documentados em `docs/runbook-vulnerabilidades.md`: 59 dos 61 altos da plataforma são avisos `wont-fix` da Debian 13 (os 2 corrigíveis ainda não propagaram na base Python); DNS depende de tag nova do upstream CoreDNS; PostgreSQL mantém 5 residuais (busybox sem correção, gosu de build). Pools externos e latência de disco por contêiner do Engine continuam fora de escopo, com justificativa registrada nos runbooks.

## Atualização de 11/11: painel de ataques

Ferramenta separada (porta 8002, somente localhost) para disparar os oito ataques do catálogo contra o laboratório e observar os alertas correspondentes: força bruta no serviço e no painel, sobrecarga HTTP, indisponibilidade, floods de DNS/SMTP (reusando o job de carga limitada da plataforma), adulteração de configuração e interrupção de serviço. Execução em fila com um ataque por vez, fases, log de eventos ao vivo via SSE, contadores/taxa e verificação final lendo `ALERTS{alertstate="firing"}` do Prometheus — o painel nunca publica métricas e nunca inventa sucesso. Efeitos sempre reversíveis (modo restaurado, serviço reiniciado, arquivo restaurado byte a byte). Operação e roteiro de demonstração em `docs/runbook-painel-ataques.md`; especificação em `docs/superpowers/specs/2026-11-11-attack-panel-design.md` e plano em `docs/superpowers/plans/2026-11-11-attack-panel.md`.

Próximas pendências: relatório ABNT com rastreabilidade ao PDF; roteiro da apresentação; frontend realista do web-demo (sub-projeto seguinte).

## Atualização de 12/11: frontend realista do web-demo (WORKBYTE)

O web-demo (porta 8001) ganhou frontend próprio — landing 8-bit futurista (CRT synthwave: fundo preto-azulado, tipografia Press Start 2P, acentos neon magenta/ciano/violeta, scanlines, diálogos estilo RPG) → tela de login → painel protegido. Fluxo de aplicação real para a apresentação: hero pixel-art em SVG, marquee estilo VHS, cards de features e footer 1-bit. Login real com `POST /login` novo no `demo/main.py`, reutilizando `ADMIN_USERNAME`/`ADMIN_PASSWORD` do `.env` com sessão em cookie assinado por HMAC-SHA256 (`demo/session.py`); `/painel` exibe SINAL (`/health`, poll 3 s — vira `✖ SIGNAL LOST` com glitch quando o ataque de modo offline derruba o serviço), MODO (`/mode`), CONTADORES (`/metrics` parseado — `AGUARDANDO DADOS` quando vazio, nunca zero falsificado) e CONSOLE DE TRABALHO (`/work` com latência medida no browser). Os contratos `GET /health`, `GET /work`, `GET /metrics`, `GET/POST /mode` ficaram byte a byte e o middleware intocado; estáticos buildados em `demo/static/` por estágio novo do Dockerfile, servidos com fallback SPA. Desvios registrados: o item do shoogle `@cult-ui/feature-carousel` é Next.js-only e foi substituído pelo `FeatureGrid` previsto no plano; a arte do hero foi desenhada em SVG próprio (geração de imagem indisponível). Testes: suíte backend 213 passed/1 skipped, frontend vitest 9 passed, builds limpos, validação ponta a ponta com script em `tmp/validate_demo_frontend.py`. Especificação em `docs/superpowers/specs/2026-11-12-demo-frontend-design.md` e plano em `docs/superpowers/plans/2026-11-12-demo-frontend.md`.

Próximas pendências: relatório ABNT com rastreabilidade ao PDF; roteiro da apresentação.

## Limites de escopo

Uma instância de cada serviço, um ambiente local e um canal de e-mail. Sem Kubernetes, multi-tenant ou aprendizado de máquina. Se houver atraso, priorizar os requisitos de entrega e segurança; reduzir métricas recomendadas e refinamento visual. Confirmar com a professora qualquer redução que afete o critério de avaliação.
