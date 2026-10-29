# AulaRedes

Plataforma de monitoramento para o trabalho final de Redes de Computadores e Internet. Desenvolvimento individual, entrega prevista em **17/11/2026**.

## Estado da construção

**Etapa 7: integridade das configurações.** O painel acompanha oito arquivos reais com SHA-256, referência aprovada e persistente, eventos, alertas e recuperação por e-mail. HTTP, PostgreSQL, DNS e SMTP também possuem comparação de tráfego com referência fixa. Login, sessões revogáveis e eventos de autenticação estão integrados. Vulnerabilidades dos serviços são a próxima entrega.

## Iniciar no Windows

Pré-requisitos: Docker Desktop com containers Linux e Python 3.13 ou mais recente (usado somente para gerar os segredos locais). A primeira construção precisa de internet para baixar imagens e dependências.

Na pasta do projeto:

```powershell
python scripts/configure.py
docker compose up -d --build --wait
```

Ou execute `./scripts/start.ps1` no PowerShell. Se a política do computador impedir scripts, use os dois comandos acima, sem alterar a política.

- Dashboard: **http://localhost:8000**
- Caixa de e-mails de alerta: **http://localhost:8025**
- Caixa de mensagens do SMTP monitorado: **http://localhost:8026**
- Documentação da API: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093
- Serviço HTTP monitorado: http://localhost:8001/work
- Dashboard PostgreSQL: http://localhost:8000/#postgres
- Dashboard DNS: http://localhost:8000/#dns
- Dashboard SMTP: http://localhost:8000/#smtp
- Eventos de autenticação: http://localhost:8000/#security

O painel exige login. No primeiro acesso, use `ADMIN_USERNAME` e `ADMIN_PASSWORD` do arquivo local `.env`, gerados por `scripts/configure.py`. Ao atualizar uma instalação existente, execute novamente esse script antes de reconstruir a stack. Ele preserva os segredos anteriores. O botão de sair revoga a sessão; o [runbook de autenticação](docs/runbook-autenticacao.md) detalha limites e demonstração.

O detector de tráfego aparece na aba Segurança. Na primeira execução, aguarde pelo menos dois minutos de coleta contínua em operação habitual para formar a referência de cada serviço. Em Laboratório, o teste de tráfego gera carga local por até 90 s com o LAB_TOKEN, sem enviar tráfego a destinos externos. Veja os limites no [runbook de tráfego](docs/runbook-trafego.md).

Na mesma aba, **Integridade das configurações** acompanha oito arquivos reais. Confira os arquivos do repositório e aprove os primeiros hashes com sessão e LAB_TOKEN; o monitor não confia automaticamente no primeiro conteúdo observado. Alterações e arquivos ausentes geram alertas. O [runbook de integridade](docs/runbook-integridade.md) explica aprovação, estados, limites e a demonstração restaurável com `python scripts/verify_integrity.py`.

O SMTP de laboratório usa Python/aiosmtpd e uma fila SQLite em volume separado. Aceita mensagens somente para `aluno@aularedes.test`, mede aceitação e entrega separadamente e tenta novamente quando o receptor cai. O canal de alertas usa outro Mailpit, portanto continua funcionando durante uma falha no SMTP monitorado. Detalhes e limites em [runbook SMTP](docs/runbook-smtp.md).

Ao atualizar uma stack já em execução, reinicie o Prometheus após reconstruir os serviços para carregar mudanças nos arquivos montados: `docker compose restart prometheus`.

CoreDNS responde por uma zona local em UDP/TCP, sem alterar o DNS do computador nem publicar portas no host. A sonda verifica `app.aularedes.test. A = 192.0.2.10`; o painel separa nomes inexistentes (NXDOMAIN) de erros do servidor.

O banco SQL usa PostgreSQL 17.11 com volume persistente e usuários separados para administração, monitoramento e carga. Sua porta não é publicada no host. Ao atualizar uma instalação da etapa HTTP, execute novamente `python scripts/configure.py` antes do Compose para gerar os três novos segredos SQL.

Aguarde cerca de 15 segundos para as primeiras taxas. O coletor faz uma sonda HTTP e uma requisição real de trabalho a cada ciclo (mínimo de 5 segundos, somado ao tempo das respostas). Toda métrica exibida vem desse tráfego ou de requisições feitas pelo usuário.

## Testar alertas

1. Abra **Laboratório** no dashboard.
2. Abra o arquivo local `.env` e copie apenas o valor de `LAB_TOKEN` para o campo do laboratório. Não publique esse arquivo.
3. Aplique **Resposta lenta**. Após 30 segundos de degradação persistente, mais os intervalos de coleta/avaliação, confira o incidente e o e-mail no Mailpit.
4. Aplique **Indisponibilidade**. O serviço responde HTTP 503; a coleta de métricas continua. O alerta crítico exige 15 segundos de falha persistente.
5. Volte para **Operação normal** e confira a resolução e a mensagem de recuperação.

Os tempos das regras começam quando o Prometheus observa a condição, portanto não são cronômetros exatos a partir do clique. A mudança de estado no dashboard pode preceder a confirmação do alerta.

## Encerrar e preservar o histórico

Para testar a parada e recuperação do banco, use `docker compose stop postgres` e depois `docker compose start postgres`. O dashboard e os incidentes continuam disponíveis durante a falha. O roteiro completo está no runbook PostgreSQL.

```powershell
docker compose down
```

Os volumes preservam métricas (retenção de 7 dias), incidentes e e-mails. O histórico de incidentes mostra os últimos 100 registros. O modo de falha do serviço de demonstração volta ao normal ao reiniciar seu processo. Não use `down -v` se quiser preservar os dados.

## Desenvolvimento

Containers são a forma mais simples de executar tudo. Para editar frontend/backend fora dos containers, mantenha o ambiente principal parado e prepare:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
cd frontend
npm ci
```

O frontend usa Vite (`npm run dev`) e encaminha `/api` para `127.0.0.1:8000`. A API pode ser iniciada por `.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers` na raiz. Ela requer Prometheus, o serviço de demonstração e as variáveis descritas em `backend/app/config.py`; o arquivo `.env` é carregado pelo Compose, não automaticamente pelo Python. Essa opção não inicia o laboratório completo.

## Verificações

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
cd frontend
npm test
npm run build
```

```powershell
docker compose run --rm --no-deps --entrypoint /bin/promtool prometheus check config /etc/prometheus/prometheus.yml
docker compose run --rm --no-deps --entrypoint /bin/amtool alertmanager check-config /etc/alertmanager/alertmanager.yml
```

## Documentação

Para repetir a demonstração automatizada com a stack em execução:

```powershell
.\.venv\Scripts\python.exe scripts/verify_lab.py
```

O roteiro muda o modo do serviço de demonstração, verifica incidentes e e-mails locais e restaura o modo normal. Leva alguns minutos por respeitar as janelas reais dos alertas.

Para verificar especificamente o PostgreSQL, incluindo parada real e preservação do volume:

```powershell
.\.venv\Scripts\python.exe scripts/verify_postgres.py
```

O banco é restaurado ao final do teste, inclusive se uma verificação falhar.

Para verificar o DNS, incluindo UDP/TCP, NXDOMAIN/SERVFAIL e parada/recuperação:

```powershell
.\.venv\Scripts\python.exe scripts/verify_dns.py
```

O DNS é restaurado ao final do teste. A documentação traz também os comandos de demonstração manual.

Para verificar SMTP, fila persistente, entrega e alertas em canal independente:

```powershell
.\.venv\Scripts\python.exe scripts/verify_smtp.py
```

O roteiro para e recupera o receptor e o servidor SMTP, restaurando ambos ao final.

Para verificar autenticação, bloqueio temporário, incidente e recuperação:

```powershell
.\.venv\Scripts\python.exe scripts/verify_auth.py
```

O roteiro reinicia a API, confirma a sessão persistente e provoca cinco falhas locais. Aguarda a janela de bloqueio expirar, verifica e-mails e conclui com os quatro serviços operacionais.

Para demonstrar detecção de volume nos quatro protocolos:

```powershell
.\.venv\Scripts\python.exe scripts/verify_traffic.py
```

Execute os roteiros de demonstração sequencialmente, sem reconstruir ou interromper serviços enquanto um teste estiver em andamento.

- [Arquitetura e métricas](docs/arquitetura.md)
- [Runbook HTTP e playbook de incidentes](docs/runbook-http.md)
- [Runbook PostgreSQL](docs/runbook-postgres.md)
- [Runbook DNS](docs/runbook-dns.md)
- [Runbook SMTP](docs/runbook-smtp.md)
- [Runbook de autenticação](docs/runbook-autenticacao.md)
- [Runbook de tráfego e referências](docs/runbook-trafego.md)
- [Runbook de integridade das configurações](docs/runbook-integridade.md)
- [Roadmap dos 20 dias](docs/roadmap.md)
- [Validação e limites](docs/validacao.md)

## Limites de uso desta etapa

Ambiente acadêmico local. As portas do host são vinculadas a `127.0.0.1`. Não exponha a plataforma à internet: o login protege o dashboard, mas as ferramentas auxiliares continuam sendo interfaces locais de laboratório. Operações do laboratório exigem token e rejeitam origem diferente; o webhook tem segredo próprio. Os dados do laboratório são de teste. A entrega SMTP é confirmada apenas no receptor local, sem comprovar entrega em provedores externos. Há duas caixas Mailpit separadas: alertas em 8025 e mensagens do serviço monitorado em 8026.
