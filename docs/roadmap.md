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

CPU em núcleos, working set e I/O de blocos dos quatro serviços implementados com SDK Docker em coletor local isolado, sem socket na API. Página Recursos com histórico e estados parcial/desconhecido, métricas de disponibilidade por campo e quatro regras de atenção. A configuração de alertas passou de 23 para 27 regras; somente sua referência SHA-256 foi atualizada após revisão e promtool.

Passaram 162 testes backend (um caso POSIX pulado no Windows), 20 frontend e três cenários promtool. Vinte verificações integradas confirmaram carga CPU real limitada, incidente/e-mail, recuperação, interrupção/retomada do coletor, quatro protocolos, oito configurações e 1.000 linhas SQL. O reinício imediato do worker também foi verificado com medições novas após seu retorno. QA desktop/celular concluído, com filtros, gráficos, rolagem interna e console sem erros/avisos. [Evidências](evidencias/resources.json) e [runbook](runbook-recursos.md).

Próximas pendências: tentativas de autenticação dos serviços monitorados; pools/consultas SQL lentas e demais métricas recomendadas; relatório ABNT com rastreabilidade ao PDF e apresentação. Latência de disco e espaço livre do host ainda não são medidos. Os demais achados das imagens continuam para triagem; o resultado de 30/10 é histórico e deve ser reavaliado com a base atual.

## Limites de escopo

Uma instância de cada serviço, um ambiente local e um canal de e-mail. Sem Kubernetes, multi-tenant ou aprendizado de máquina. Se houver atraso, priorizar os requisitos de entrega e segurança; reduzir métricas recomendadas e refinamento visual. Confirmar com a professora qualquer redução que afete o critério de avaliação.
