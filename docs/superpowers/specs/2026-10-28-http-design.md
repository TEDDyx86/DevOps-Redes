# AulaRedes: primeiro ciclo de monitoramento

Decisão aprovada na conversa: iniciar a construção da proposta de dashboard próprio com React, FastAPI, Prometheus e Alertmanager. Trabalho individual, prazo de 20 dias (17/11/2026).

## Entrega desta etapa

Um laboratório local reproduzível com HTTP real, coleta periódica, armazenamento temporal, gráficos, estados OK/Atenção/Crítico/Sem dados, alertas e recuperação. E-mails vão inicialmente para uma caixa SMTP local (Mailpit). Nenhuma conta externa é necessária.

## Arquitetura

- `demo/`: serviço HTTP instrumentado, com modos normal, lento e indisponível. O endpoint de métricas permanece acessível para observar falhas HTTP reais.
- `backend/`: FastAPI; sonda de saúde independente, cliente Prometheus com consultas fixas, API do dashboard e recebimento autenticado de eventos do Alertmanager.
- `frontend/`: React/TypeScript/Vite; visão geral, detalhe HTTP, incidentes e laboratório. Gráficos usam amostras reais, sem séries fabricadas.
- `infra/`: Prometheus coleta a cada 5 s e avalia regras; Alertmanager encaminha e-mails e webhooks; Mailpit recebe e-mails locais.
- SQLite persiste incidentes nesta primeira etapa. PostgreSQL para dados da plataforma e um banco monitorado separado serão incluídos na etapa de banco.
- Docker Compose é a execução principal. O daemon Docker foi iniciado e validado durante a construção; scripts Windows iniciam e encerram a stack. Desenvolvimento nativo da API e interface é opcional e depende dos serviços auxiliares.

## Contratos e limites

- Disponibilidade HTTP: status 2xx de `/health`, não apenas disponibilidade do exporter.
- RPS, erros e p95 de latência: requisições reais a `/work`, incluindo tráfego periódico do laboratório identificado na interface.
- Disponibilidade no período: percentual de sondas bem-sucedidas entre as amostras existentes; não pressupõe histórico anterior à instalação.
- Falta de Prometheus, sonda desatualizada ou resultado ausente nunca significa OK nem zero latência.
- Alerta crítico: falha de sonda por 15 s. Atenção: latência da sonda acima de 500 ms por 30 s. Recuperação também gera evento/e-mail.
- Webhook tem segredo compartilhado. Operações do laboratório exigem origem local e token configurado, não são oferecidas a visitantes remotos.
- Serviços escutam em loopback no host. Sem publicação externa nesta etapa.

## Interface

Aluno demonstra o laboratório em notebook em sala iluminada: superfície clara, texto grafite, acento violeta discreto, cores semânticas acompanhadas de rótulos. Navegação lateral compacta e tabela de serviços; gráfico e histórico ao centro. Estados vazios explicam a primeira coleta. Layout mobile com navegação compacta e tabelas roláveis.

## Verificação

Testes de fronteira para consultas, dados ausentes e timestamps; webhook idempotente, persistência e autenticação; demonstração com HTTP normal, lento, falha e recuperação; navegação desktop/mobile. Configurações validadas por promtool/amtool e Compose. Componentes indisponíveis no ambiente serão registrados explicitamente.

## Continuidade

Esta etapa não conclui o trabalho final. Restam PostgreSQL, DNS, SMTP monitorado (separado do canal de alertas), os quatro monitoramentos de segurança, configurações de produção e relatório ABNT. Documentação de instalação e runbook HTTP começam nesta entrega.
