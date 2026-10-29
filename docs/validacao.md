# Validação da etapa HTTP

Este documento separa verificações automatizadas, demonstração integrada e requisitos ainda em construção.

## Testes automatizados

`backend/tests/test_platform.py` verifica:

- Classificação normal/lenta/falha e ausência ou idade excessiva das sondas.
- Métricas ausentes, NaN e infinito não convertidas em valores saudáveis.
- Persistência, deduplicação e resolução idempotente de incidentes.
- Webhook autenticado e validação do payload.
- Token e origem para alterações do laboratório.
- Prometheus indisponível, janela inválida e séries vazias.
- Serviço HTTP retornando 503 enquanto suas métricas continuam acessíveis.

`frontend/src/api.test.ts` diferencia zero medido de ausência de dados. Build TypeScript verifica contratos da interface. `promtool` e `amtool` validam configurações.

## Evidências da execução

Execução em 28/10/2026, Docker Desktop com containers Linux:

- **10 testes de API passaram**, incluindo regressão de tráfego composto apenas por respostas 503.
- **2 testes de frontend passaram**, incluindo interrupção real após 8 s de uma requisição sem resposta.
- Build TypeScript/Vite concluído; fontes incluídas localmente para não depender de Google Fonts durante a demonstração.
- `promtool`: configuração e três regras válidas.
- `amtool`: configuração válida, com receptor de e-mail e webhook autenticado.
- Cinco serviços em execução: API/dashboard, HTTP demo, Prometheus, Alertmanager e Mailpit.
- **12 verificações de integração passaram** com `scripts/verify_lab.py`: estado normal, erro 0% com tráfego saudável, atenção observada, incidente de lentidão persistido, e-mail recebido, indisponibilidade observada, incidente crítico, métricas durante a falha, recuperação operacional, resolução dos dois incidentes e e-mail de recuperação.
- Durante a primeira demonstração, o Mailpit recebeu quatro mensagens locais: alerta e recuperação para lentidão e indisponibilidade. O script produz `tmp/e2e-result.json`, sem tokens. Esse arquivo é evidência temporária e não é versionado.
- Revisão independente identificou e motivou correções no cálculo de erros, atualização de séries sem respostas 200 e expiração dos dados da interface. Suíte de regressão executada após as correções.
- Navegação real no navegador: visão geral, detalhe HTTP, laboratório e incidentes; token inválido rejeitado com mensagem; seletor de período alterado para uma hora.
- Layout verificado em 1440×1000 e 390×844. Em celular, largura de rolagem do documento igual à largura útil (375 px), sem transbordamento horizontal da página; a tabela mantém rolagem interna.
- Prometheus interrompido por 25 s e reiniciado automaticamente: interface exibiu erro explícito, estado Sem dados e métricas ausentes em vez de conservar o estado operacional.

Evidências visuais em `docs/evidencias/`: `dashboard-desktop.jpg`, `dashboard-mobile.jpg` e `coleta-indisponivel.jpg`. São capturas do laboratório local, sem credenciais.

O script integrado altera somente o serviço de demonstração e restaura o modo normal no bloco `finally`. Não gera testes de carga nem envia mensagens a destinatários externos.

Há um aviso de depreciação da biblioteca Starlette sobre a integração de testes com httpx. Os testes passam; o aviso pertence à dependência e não indica falha funcional da aplicação.

## Etapa PostgreSQL: 28/10/2026

- **18 testes de API passaram**, incluindo os testes HTTP anteriores, contratos SQL, dados ausentes/antigos, falha com estatísticas antigas, distinção QPS/transações, pressão de conexões e duas regressões de recuperação.
- **4 testes de frontend passaram**: formatação, timeout, combinação de estados e expiração independente dos serviços.
- Build TypeScript/Vite concluído; `promtool` validou **7 regras** HTTP/SQL.
- **14 verificações reais passaram** com `scripts/verify_postgres.py`: estatísticas, carga SQL, rollbacks, bloqueio de escrita do monitor, parada real, ocultação de valores antigos, independência do HTTP, persistência de incidente/e-mail, reconexão, retorno das taxas, dados preservados e resolução/e-mail de recuperação.
- O banco permaneceu separado do armazenamento de incidentes. As 1.000 linhas e as atualizações confirmadas foram preservadas após stop/start.
- Revisão independente encontrou duas falhas corrigidas com reprodução antes da correção: NaN comum em counters ausentes atrasava `rate`, e prazo global de coleta confundia estatísticas lentas com falha SQL. Counters ausentes agora são omitidos; conexão/SELECT 1 e estatísticas têm prazos separados.
- Navegação real confirmou o estado consolidado crítico com HTTP operacional e PostgreSQL parado, a recuperação, o detalhe SQL e o seletor de período de uma hora.
- Layout SQL verificado em 390×844 e 1440×1000: largura do documento igual à largura útil da viewport, sem transbordamento. Console do navegador sem erros na conferência final.
- Evidências: `docs/evidencias/postgres-desktop.jpg`, `postgres-mobile.jpg` e `postgres-indisponivel.jpg`. Resultado temporário sem credenciais: `tmp/postgres-e2e-result.json`.

## Etapa DNS: 28/10/2026

- **26 testes de API passaram**, incluindo contratos DNS, validação de respostas reais codificadas, endereço incorreto, NXDOMAIN, falha de um protocolo, latência, dados antigos e preservação das lacunas do histórico.
- **6 testes de frontend passaram**, incluindo a participação do terceiro serviço no estado consolidado e o destino correto ao selecionar uma linha da tabela.
- Build TypeScript/Vite concluído; `promtool` validou **10 regras** HTTP/SQL/DNS.
- **18 verificações reais passaram** com `scripts/verify_dns.py`: resolução UDP/TCP dos registros, segundo nome, NXDOMAIN distinto de falha, consultas/s, SERVFAIL e sua taxa, parada real, ocultação de dados antigos, HTTP/SQL independentes, incidente, e-mail, recuperação e retorno das métricas.
- O primeiro roteiro revelou que uma série de rcode recém-criada precisa de baseline e incremento posterior para formar uma taxa. O teste agora espera a coleta do contador e envia um segundo SERVFAIL, sem inventar valores.
- Revisão independente encontrou e confirmou correção de lacunas no gráfico: a grade temporal recebe valores nulos antes das amostras, evitando ligar pontos através de uma indisponibilidade. Teste de regressão executado antes e depois da correção.
- Navegação real: visão consolidada com três serviços, detalhe DNS aberto pela linha correspondente e seleção de uma hora. UDP/TCP e NOERROR aparecem com dados reais.
- Layout verificado em 390×844 e 1440×1000: largura de rolagem igual à largura útil da viewport (375 e 1425 px). Console sem erros na conferência final.
- Evidências: `docs/evidencias/dns-desktop.jpg` e `dns-mobile.jpg`. Resultado temporário sem credenciais em `tmp/dns-e2e-result.json`.
- O DNS do host não foi alterado; portas UDP/TCP do CoreDNS continuam restritas à rede Compose.

## Etapa SMTP: 28/10/2026

- **33 testes de API/protocolo/fila passaram**, incluindo SMTP real, destinatário externo rejeitado com 550, limite SIZE de 64 KiB, persistência, claim exclusivo, retry temporário, falha definitiva e recuperação de erros SQLite sem reenvio duplicado no processo ativo.
- **6 testes de frontend passaram**, com navegação para o quarto serviço. Build TypeScript/Vite concluído; `promtool` validou **14 regras** HTTP/SQL/DNS/SMTP.
- **23 verificações reais passaram** com `scripts/verify_smtp.py`: entrega correlacionada por Message-ID, rejeição contabilizada, volume e histograma, receptor parado com SMTP funcionando, fila crescente, tentativas falhas, aviso e e-mail, reinício do MTA preservando pendências/contadores, entrega de todas as mensagens após recuperação e resolução do aviso.
- A mesma execução parou o SMTP monitorado, confirmou ocultação de estatísticas antigas, independência de HTTP/SQL/DNS, incidente crítico e e-mail recebido no outro Mailpit, recuperação e resolução com novo e-mail. Ambos os serviços foram restaurados no `finally`.
- Revisão independente identificou parada do worker após erro temporário de armazenamento. Reproduzido em teste antes da correção: o worker agora repete claim/finish e conserva o resultado de envio enquanto o commit falha.
- O primeiro roteiro integrado encontrou uma condição de corrida temporal: uma coleta concluída durante as consultas podia parecer ligeiramente posterior ao início da requisição, ocultando dados novos. Reproduzido em teste e corrigido com a mesma tolerância de relógio de 5 s da classificação. Amostras antigas continuam expirando em 20 s.
- Layout SMTP conferido em 390×844 e 1440×1000: largura de rolagem igual à largura útil (375 e 1425 px), sem transbordamento horizontal.
- Navegação real confirmou quatro serviços operacionais na visão geral, abertura do detalhe pela linha SMTP e console sem erros. Evidências: `docs/evidencias/smtp-desktop.jpg` e `smtp-mobile.jpg`.
- Resultado temporário sem credenciais: `tmp/smtp-e2e-result.json`. O roteiro restaura os serviços e não envia correio externo.

## Etapa de autenticação: 28/10/2026

- **42 testes backend passaram**, incluindo os 33 anteriores, proteção de APIs/docs, hash e bootstrap idempotente, sessão persistente, expiração, revogação por logout/rotação, CSRF/origem, falhas por IP/conta, concorrência, cap do histórico e Uvicorn real ignorando `X-Forwarded-For`.
- **8 testes frontend passaram**, incluindo CSRF e distinção entre sessão expirada e token de laboratório inválido. Build TypeScript/Vite concluído. `promtool` validou **15 regras**.
- **19 verificações reais passaram** com `scripts/verify_auth.py`: dados anônimos negados, health/métricas disponíveis, sessão real, proteção CSRF/origem, reinício da API preservando sessão, cinco falhas e sexta tentativa 429/Retry-After, eventos sem segredos, sessão anterior operante, incidente/e-mail de autenticação, expiração da janela, resolução/e-mail, logout revogado e novo login.
- **12 verificações HTTP passaram novamente** com login e CSRF em `scripts/verify_lab.py`, incluindo controle de lentidão/falha, métricas, incidentes, alertas SMTP e recuperação. Os quatro serviços permaneceram recuperáveis e voltaram ao estado operacional.
- Revisão independente motivou três correções: desabilitar proxy headers no servidor nativo/container; separar orçamento do limitador do histórico de 10.000 eventos; repassar cookie Secure pelo Compose. Testes cobrem IP informado pelo cliente e histórico cheio sem perder orçamento/counters.
- Navegação real confirmou formulário de entrada, login, aba Segurança, eventos persistidos, logout e nova entrada, além de sessão preservada após recarga. Login e eventos foram conferidos em 390×844 e 1440×1000, com largura de página igual à largura útil da viewport (375 e 1425 px), sem transbordamento horizontal.
- Evidências: `docs/evidencias/login-desktop.jpg`, `login-mobile.jpg`, `security-desktop.jpg` e `security-mobile.jpg`. Relatório sem segredos: `tmp/auth-e2e-result.json`.

## Etapa de tráfego: 29/10/2026

- **52 testes backend passaram** (suíte com 51 e teste adicional de fonte com erro/taxa inválida), incluindo aprendizado contínuo, zero real, fonte desconhecida, referência fixa/persistente, commit antes de publicar estado, teto de duração, cancelamento imediato, encerramento de tarefas irmãs e fechamento da conexão SMTP durante cancelamento.
- **10 testes frontend passaram**, incluindo conversão consistente de taxa/referência/limiar SMTP para msg/min e expiração do estado atual sem apagar referência. Build TypeScript/Vite concluído; `promtool` validou **17 regras**.
- **20 verificações reais passaram** com `scripts/verify_traffic.py`: proteção de sessão/token, quatro referências prontas, job único/cancelamento, carga local dos quatro protocolos, quatro taxas acima dos limiares, referências fixas durante o pico, recalibração bloqueada, quatro incidentes e quatro e-mails, encerramento automático com contadores dentro dos tetos, recuperação das taxas, quatro resoluções e quatro e-mails de recuperação, referências preservadas após restart da API e serviços operacionais.
- O job de 90 s confirmou 448 requisições HTTP, 893 comandos SQL, 893 consultas DNS e 90 mensagens SMTP, sem falhas ou cancelamentos em voo nessa execução. Todos ficaram dentro dos limites definidos.
- Revisão independente encontrou SMTP em thread que podia sobreviver ao cancelamento. Reproduzido em teste com receptor retendo confirmação de DATA; substituído por cliente de streams com fechamento da conexão. Também corrigida mensagem de erro de polling que não desaparecia após a recuperação. Revisor confirmou os ajustes sem novo achado bloqueante.
- Navegação real: Segurança com quatro volumes elevados e quatro incidentes, recuperação para volume normal, Laboratório com início e cancelamento de carga HTTP e contadores reais. Referências permaneceram iguais. Layout 1440×1000 e 390×844 sem transbordamento horizontal da página (larguras úteis 1425 e 375 px); tabela usa rolagem interna no celular.
- Evidências: `traffic-anomalous.jpg`, `traffic-desktop.jpg` e `traffic-mobile.jpg` em `docs/evidencias/`. Relatório temporário sem segredos: `tmp/traffic-e2e-result.json`.

## Requisitos ainda em construção

CPU/memória/I/O, pools e consultas lentas, tentativas de autenticação nos serviços monitorados, monitoramento de arquivos, vulnerabilidades conhecidas e relatório ABNT. Autenticação da interface, detecção de falhas repetidas no painel e comparação de volume dos quatro serviços com referência fixa já estão implementadas.
