# Validação da etapa HTTP

## Reconciliação e QA visual: 30/10/2026

- Causa reproduzida: o armazenamento atualizava somente a chave `(fingerprint, started_at)` do webhook, deixando ciclos antigos firing quando a resolução se perdia. Oito testes falharam antes da correção inicial. A migração e a ingestão agora reconciliam somente por resolução direta posterior da mesma identidade, com datas UTC válidas; guardam a prova e mantêm `ended_at=null`, sem inventar o término original. Resoluções inferidas não servem de prova; ciclos recentes firing não são encerrados por falta de dados.
- Backup consistente SQLite com `backup()`/`serialize()`, 58 registros e `integrity_check=ok`. Ensaio em cópia confirmou todas as chaves e textos preservados e três ciclos históricos reconciliados. Na aplicação real, somente API/frontend foram substituídos; as quatro imagens monitoradas e os oito arquivos de configuração permaneceram intactos.
- **128 testes backend passaram**, um caso POSIX foi pulado no Windows. **18 testes frontend passaram** e build TypeScript/Vite concluiu. A interface mostra **Reconciliado**, confirmação posterior e término original desconhecido; resoluções diretas continuam **Resolvido** e alertas ativos preservam sua severidade.
- A revisão independente reproduziu dois problemas adicionais: resolução direta inválida podia apagar a inferência válida, e consulta correlacionada crescia quadraticamente sem candidatos ativos. Sete regressões falharam antes das correções. Agora o webhook rejeita datas inconsistentes com 422; ingestão inválida reverte todo o lote. Consulta começa por candidatos firing com índice parcial e busca provas por identidade. O cenário de 8.000 ciclos resolvidos passou com orçamento de instruções SQLite, sem depender do relógio da máquina. Revisor confirmou os dois achados encerrados.
- **Nove verificações integradas passaram**: login exigido, 58 chaves/textos originais preservados, três reconciliações sustentadas por prova direta, dois alertas atuais consistentes com Prometheus, imagens monitoradas iguais, integridade SQLite, sessão/metadados persistentes após restart, quatro protocolos/oito configurações operacionais e PostgreSQL ainda com zero crítico/alto e cinco achados restantes. Reinícios da fonte de métricas criam ciclos novos reais; a verificação aceita novos registros e exige preservação dos originais, em vez de fixar a contagem total durante operação contínua.
- **12 verificações HTTP passaram** novamente após a mudança no webhook: lentidão, indisponibilidade, métricas durante falha, incidente/e-mail, recuperação e resolução dos dois incidentes com e-mail. Nenhum incidente fictício foi inserido no ambiente em execução para testar a reconciliação.
- Navegador real: Incidentes/Segurança em desktop aproximadamente 1440×1000 e celular **390×844**. As dimensões CSS exatas estão no JSON (o navegador usa zoom/escala). Largura rolável da página igual à largura útil em todas as medições; tabelas mantêm rolagem interna, operada no celular. Confirmados três rótulos Reconciliado/notas, PostgreSQL com cinco achados e crítico vazio, próxima/anterior HTTP com mudança de achados, 55 altos HTTP em duas páginas e três achados DNS. Console sem erros ou avisos na captura.
- Evidência atual: [incident-reconciliation.json](evidencias/incident-reconciliation.json), `incidents-reconciled-desktop.png`, `incidents-reconciled-mobile.png`, `vulnerabilities-desktop.png` e `vulnerabilities-mobile.png`. [Runbook](runbook-incidentes.md). Evidências anteriores preservam o estado histórico, incluindo a pendência que agora foi resolvida. Métricas de recursos, autenticação dos serviços e relatório ABNT seguem no roadmap.

## Atualização preventiva PostgreSQL: 30/10/2026

- Os três críticos provinham de `stdlib go1.24.6` no gosu 1.19 da imagem PostgreSQL 17.11: GO-2026-4337 (TLS), GO-2026-6604 (junção Windows) e GO-2026-6612 (HTTP/2). Conferidos os avisos Go e a política oficial do gosu: achado de versão não demonstra exploração SQL; Windows não é a plataforma da imagem e o helper não oferece TLS/HTTP/2. Não foi realizado govulncheck completo nem exploração.
- A imagem derivada mantém base/entrypoint/servidor SQL/volume e recompila o mesmo gosu com Go 1.27.3, base/compilador por digest e fonte por SHA-256. Dependências preservadas/verificadas, sem compilador na imagem final, sem supressão ou mudança de severidade do scanner.
- Candidato isolado e imagem efetivamente observada pelo worker: **50 pacotes** (45 APK, quatro módulos Go e um binário), de **3 críticos / 32 altos / 26 médios / 2 baixos / 1 não classificado** para **0 críticos / 0 altos / 4 médios / 1 baixo**, com a mesma base Grype. Os três avisos alvo estão ausentes; os cinco restantes continuam publicados. Outras imagens conservam seus achados próprios.
- **Quatro verificações do candidato passaram**: bootstrap com 1.000 linhas, papéis/extensão e postmaster final pronto; UID/GID/HOME; PostgreSQL 17.11 sem compilador/fonte; encerramento normal por SIGINT. A espera distingue o servidor temporário do initdb do processo final.
- Backup `pg_dump -Fc` e globais restaurados em contêiner isolado, com SHA-256 de toda a tabela idêntico e papéis/permissões conferidos. A restauração usa `lab_admin`, preservando os `GRANTED BY`, e omite somente seu `CREATE ROLE` duplicado no fluxo restaurado. Backups originais e hashes de senha não foram publicados. Na troca real, carga pausada, mesmo volume e **SHA-256 exato de todos os 1.000 registros antes/depois**.
- **14 verificações PostgreSQL passaram** novamente: permissões, estatísticas, parada real, estado sem dados, independência HTTP, incidente/e-mail, reconexão, dados preservados e resolução/e-mail. **11 verificações de vulnerabilidades passaram** novamente: identidade real, filtros/paginação, métricas, incidentes/e-mails aplicáveis, restart da API, quatro protocolos e oito referências de integridade.
- **Cinco verificações direcionadas passaram**: nova imagem/análise válida com zero crítico/alto; três avisos alvo ausentes e cinco achados restantes visíveis; evento crítico desta atualização resolvido sem alerta de vulnerabilidade PostgreSQL ativo no Prometheus; novo e-mail de resolução; protocolos/configurações operacionais. Há **um incidente crítico histórico de 29/10 ainda firing no SQLite**, após interrupção anterior do monitoramento. Uma tentativa de exigir resolução de todos os registros históricos revelou essa pendência. Não foi apagado nem marcado resolvido manualmente; a reconciliação é trabalho posterior. O resultado atual foi confirmado pela imagem, relatório e fonte Prometheus, não pela ausência de registros históricos.
- Revisão independente não encontrou bloqueante no Dockerfile/Compose; corrigiu o runbook para só retomar a carga após validação da atualização ou reversão, mantendo API pausada se ambas falharem. Não houve alteração no código frontend/backend, regras ou referências de integridade. QA visual desktop/mobile de vulnerabilidades segue pendente.
- Evidência pública resumida: [postgres-remediation.json](evidencias/postgres-remediation.json). Procedimento e fontes primárias: [runbook da atualização](runbook-postgres-remediation.md). Artefatos completos de execução e backups em `tmp/` e `.runtime/`, ignorados pelo Git.

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

CPU/memória/I/O, pools e consultas lentas, tentativas de autenticação nos serviços monitorados e relatório ABNT. Autenticação da interface, falhas repetidas no painel, comparação de volume, integridade dos oito arquivos listados e análise de vulnerabilidades das imagens dos quatro serviços já estão implementadas. Os achados reais exigem triagem e eventual correção; detecção não significa remediação.

## Etapa de integridade: 29/10/2026

- **67 testes backend passaram** no ambiente de desenvolvimento (66 na suíte completa e uma regressão adicional de falha de commit). O caso POSIX foi pulado no Windows e validado no Linux: os **15 testes de integridade da imagem**, incluindo links simbólicos de arquivo/pasta e FIFO, passaram; uma verificação DNS repetida isoladamente também passou, totalizando 16 nessa execução.
- **13 testes frontend passaram**, incluindo expiração sem apagar a referência, seleção inicial somente de arquivos sem referência e preservação do hash em revisão. Build TypeScript/Vite concluído na imagem final; `promtool` validou **20 regras** e `amtool` validou a configuração de notificações e o caminho separado do segredo.
- **16 verificações reais passaram**, repetidas após os ajustes de revisão, com `scripts/verify_integrity.py`: login/token, oito arquivos legíveis com hashes iguais aos bytes do host, aprovação inicial explícita, rejeição de hash falso, quatro alterações reais, referências fixas, quatro incidentes e quatro e-mails, restauração exata, quatro resoluções e quatro e-mails de recuperação, restart da API com referências e eventos preservados, quatro protocolos operacionais ao final.
- HTTP/SMTP carregam os JSON monitorados; PostgreSQL confirmou `config_file=/etc/postgresql/postgresql.conf`, HBA/dados no volume anterior, `max_connections=100`, `pg_stat_statements` e **1.000 linhas preservadas** em `lab_items`. DNS continua resolvendo UDP/TCP. Os testes não alteraram o DNS do host.
- Revisão independente apontou mounts individuais que não acompanhavam substituição atômica, falha do SQLite de integridade interrompendo startup e retenção que dependia de novo evento. Corrigidos com mounts de diretório, inicialização degradada com nova tentativa e poda em cada coleta. Regressões reproduziram os dois últimos casos antes das correções; revisão final sem bloqueantes.
- Falhas de transação/commit não publicam referência nem persistem aprovação parcial. Erro de leitura, ausência, tamanho acima de 1 MiB, mudança durante leitura e observação vencida não aparecem como estado íntegro. Conteúdo e segredos não são retornados pelo detector.
- Navegação real confirmou revisão com hash completo, botão desabilitado sem token e aprovação idempotente com feedback de sucesso. Layout desktop/celular sem transbordamento horizontal da página; a tabela tem rolagem interna. Os overrides solicitados foram 1440×1000 e 390×844; com a escala atual do navegador, as larguras úteis medidas foram **1331 e 351 px**, iguais às larguras de rolagem. Console sem erros na conferência final.
- Evidências: `docs/evidencias/integrity-desktop.jpg` e `integrity-mobile.jpg`. Relatório sem credenciais: `tmp/integrity-e2e-result.json`. Todos os oito arquivos retornaram à referência e os quatro serviços ficaram operacionais.
- A tentativa de executar toda a suíte na imagem de produção não foi usada como verificação final: ela não inclui `scripts.configure`, necessário para um teste de bootstrap. Também ocorreu uma expiração do fixture temporal DNS sob carga, que passou na execução isolada. A suíte completa foi validada no ambiente de desenvolvimento; a cobertura POSIX foi executada separadamente no container.

## Etapa de vulnerabilidades: 29/10/2026

- **95 testes backend passaram**, com um caso POSIX pulado no Windows. Os 28 testes novos cobrem normalização, inventário real obrigatório, deduplicação, severidade desconhecida, URL insegura, datas inválidas/antigas, imagem divergente, contagens inconsistentes, falhas de scanner, filtros, métricas sem falso zero, trava, publicação atômica, retry e persistência de falha após restart.
- **16 testes frontend passaram** e o build TypeScript/Vite foi concluído na imagem. Os três testes novos verificam validade independente de inventário/análise/base e preservação de metadados quando contagens expiram. A conferência visual desktop/mobile desta etapa ficou pendente: a ferramenta de Computer Use interrompeu a execução por não conseguir confirmar a URL do navegador. Não foram produzidas novas capturas nem declarada navegação real concluída.
- `promtool` validou **23 regras**. Os três cenários isolados em `backend/tests/fixtures/vulnerability-rules.test.yml` passaram: confirmação em 30 s e prioridade crítico/alto, confirmação em 2 min de análise indisponível, e análise válida sem achados. Nenhuma série sintética foi publicada no laboratório.
- Syft 1.55.0 e Grype 0.121.0, com digests fixados, analisaram imagens locais reais. O índice OCI observado no Docker foi associado à exportação; o digest de configuração foi calculado dos bytes do archive e conferido com as duas ferramentas. O formato real do SBOM usa `source.metadata`, enquanto o relatório Grype usa `source.target`; ambos foram validados.

| Imagem/serviço analisado | Pacotes | Críticos | Altos | Médios | Baixos | Desprezíveis | Não classificados |
|---|---:|---:|---:|---:|---:|---:|---:|
| HTTP/SMTP (mesma imagem) | 127 | 0 | 55 | 50 | 10 | 46 | 0 |
| PostgreSQL | 50 | 3 | 32 | 26 | 2 | 0 | 1 |
| DNS | 202 | 0 | 0 | 0 | 0 | 0 | 3 |

Essas contagens são a fotografia da execução registrada, não uma garantia de explorabilidade ou estado permanente. As contagens por serviço da imagem compartilhada não devem ser somadas como achados distintos de duas imagens.

- A demonstração real confirmou inicialmente nove verificações: login, filtros/ausência de execução pela API, quatro análises atuais, IDs conferidos independentemente com Docker, resultado compartilhado, paginação/deduplicação/seis severidades, cardinalidade fixa, incidentes e e-mails aplicáveis aos achados reais. A fase de interrupção do coletor foi interrompida por timeouts simultâneos de API, Prometheus e Mailpit, seguidos de falha do engine Docker; não foi contada como ciclo completo.
- A revisão independente encontrou dois problemas no worker: saída limitada somente após término e exportação Docker podendo sobreviver à liberação da trava. Reproduzidos antes das correções. Agora stdout tem limite durante a leitura de 32 MiB, stderr de 64 KiB, processos são terminados/recolhidos e novos comandos são bloqueados após shutdown. A thread é aguardada integralmente antes de liberar a trava. Nove testes de worker passaram e o revisor confirmou os dois ajustes sem novo bloqueante.
- O hash revisado de `infra/alerts.yml` foi aprovado explicitamente após validar as 23 regras; as demais referências foram preservadas. Arquivos raw/exportações não são servidos pela API; os relatórios normalizados ficam em `.runtime/vulnerabilities`, ignorado pelo Git e montado somente leitura.

## Retomada e conclusão funcional: 30/10/2026

- Docker Desktop voltou a responder com engine 29.9.2. A stack foi iniciada com os volumes existentes. Os **35 testes de vulnerabilidades/integridade no Linux passaram**, incluindo os casos POSIX; os três cenários isolados de regras passaram novamente.
- A primeira tentativa após iniciar a stack encontrou inventário temporariamente indisponível entre páginas. O painel omitiu corretamente os achados atuais; o roteiro foi ajustado para exigir a mesma imagem, data de análise/base e contagens em todas as respostas. Se uma análise expira ou é substituída, repete a leitura consistente. Três regressões foram observadas falhando antes da implementação e passaram após o ajuste.
- A suíte completa final apresentou **98 testes backend aprovados e um caso POSIX pulado no Windows**, além dos **16 testes frontend já aprovados** e do build TypeScript/Vite concluído. Não houve mudança na lógica de produção do monitor durante o ajuste do roteiro.
- **18 verificações integradas passaram** em `scripts/verify_vulnerabilities.py --exercise-outage`: dados reais dos quatro serviços, IDs conferidos com Docker, paginação/deduplicação/filtros, métricas fixas, incidentes/e-mails dos achados, parada do worker, contagens ocultas após expiração, métricas omitidas sem falso zero, quatro incidentes e quatro e-mails de análise indisponível, recuperação das mesmas contagens, quatro resoluções e quatro e-mails de recuperação, persistência após restart da API, quatro protocolos operacionais e oito configurações íntegras.
- A reanálise confirmou as contagens da tabela anterior. Permanecem **3 achados críticos e 32 altos na imagem PostgreSQL**, **55 altos na imagem compartilhada HTTP/SMTP** e **3 não classificados no DNS**, sujeitos a triagem de aplicabilidade. As 1.000 linhas de `lab_items` foram confirmadas após a recuperação. Estado operacional dos protocolos não implica ausência de risco na imagem.
- Inspeção do container confirmou mount dos relatórios com `RW=false` e ausência de socket Docker na API. Segredos, cache de execução e relatório de teste continuam ignorados pelo Git. O resultado completo sem credenciais está em `tmp/vulnerabilities-e2e-result.json`.
- A automação visual continuou indisponível: as tentativas de conectar ao Docker Desktop e à aba existente do painel terminaram com timeout e reinicialização do helper. A navegação real e as capturas desktop/mobile desta etapa permanecem pendentes; as evidências das etapas anteriores não foram reutilizadas como prova da interface nova.
