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

1. PostgreSQL integrado em volume separado: disponibilidade, conexão + SELECT 1, conexões, commits/s, rollbacks/s, tamanho e comandos SQL/s do usuário de laboratório. CPU/memória/disco, pools e consultas lentas exigem instrumentação complementar. O armazenamento de incidentes permanece independente em SQLite.
2. CoreDNS integrado: zona local, sondas UDP/TCP, consultas/s, latência, p95 do servidor, NXDOMAIN separado dos erros e alerta/recuperação. A resolução do host permanece inalterada.
3. SMTP integrado com Python/aiosmtpd e fila SQLite persistente: aceitação, entrega, retry, rejeição, volume, histograma e canal de alertas independente. A proposta inicial de Postfix foi substituída pelo MTA local instrumentado. Paradas do receptor e do SMTP verificadas, com recuperação das pendências.
4. Segurança: login da plataforma, contagem de falhas por conta/IP com janela e limiar; comparação de tráfego com referência; hashes de configuração; resultados periódicos de scanner associados às imagens/serviços.
5. Relatório ABNT, requisitos rastreados ao PDF, testes e roteiro da apresentação.

## Limites de escopo

Uma instância de cada serviço, um ambiente local e um canal de e-mail. Sem Kubernetes, multi-tenant ou aprendizado de máquina. Se houver atraso, priorizar os requisitos de entrega e segurança; reduzir métricas recomendadas e refinamento visual. Confirmar com a professora qualquer redução que afete o critério de avaliação.
