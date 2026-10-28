# AulaRedes

Plataforma de monitoramento para o trabalho final de Redes de Computadores e Internet. Desenvolvimento individual, entrega prevista em **17/11/2026**.

## Estado da construção

**Etapa 1: HTTP.** Serviço real instrumentado, sonda de disponibilidade, séries no Prometheus, dashboard React, incidentes persistidos e e-mails locais pelo Alertmanager/Mailpit. PostgreSQL, DNS, SMTP monitorado e monitoramentos de segurança são as próximas entregas; não aparecem como integrados.

## Iniciar no Windows

Pré-requisitos: Docker Desktop com containers Linux e Python 3.13 ou mais recente (usado somente para gerar os segredos locais). A primeira construção precisa de internet para baixar imagens e dependências.

Na pasta do projeto:

```powershell
python scripts/configure.py
docker compose up -d --build --wait
```

Ou execute `./scripts/start.ps1` no PowerShell. Se a política do computador impedir scripts, use os dois comandos acima, sem alterar a política.

- Dashboard: **http://localhost:8000**
- Caixa de e-mail de testes: **http://localhost:8025**
- Documentação da API: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093
- Serviço HTTP monitorado: http://localhost:8001/work

Aguarde cerca de 15 segundos para as primeiras taxas. O coletor faz uma sonda HTTP e uma requisição real de trabalho a cada ciclo (mínimo de 5 segundos, somado ao tempo das respostas). Toda métrica exibida vem desse tráfego ou de requisições feitas pelo usuário.

## Testar alertas

1. Abra **Laboratório** no dashboard.
2. Abra o arquivo local `.env` e copie apenas o valor de `LAB_TOKEN` para o campo do laboratório. Não publique esse arquivo.
3. Aplique **Resposta lenta**. Após 30 segundos de degradação persistente, mais os intervalos de coleta/avaliação, confira o incidente e o e-mail no Mailpit.
4. Aplique **Indisponibilidade**. O serviço responde HTTP 503; a coleta de métricas continua. O alerta crítico exige 15 segundos de falha persistente.
5. Volte para **Operação normal** e confira a resolução e a mensagem de recuperação.

Os tempos das regras começam quando o Prometheus observa a condição, portanto não são cronômetros exatos a partir do clique. A mudança de estado no dashboard pode preceder a confirmação do alerta.

## Encerrar e preservar o histórico

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

O frontend usa Vite (`npm run dev`) e encaminha `/api` para `127.0.0.1:8000`. A API pode ser iniciada por `.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000` na raiz. Ela requer Prometheus, o serviço de demonstração e as variáveis descritas em `backend/app/config.py`; o arquivo `.env` é carregado pelo Compose, não automaticamente pelo Python. Essa opção não inicia o laboratório completo.

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

- [Arquitetura e métricas](docs/arquitetura.md)
- [Runbook HTTP e playbook de incidentes](docs/runbook-http.md)
- [Roadmap dos 20 dias](docs/roadmap.md)
- [Validação e limites](docs/validacao.md)

## Limites de uso desta etapa

Ambiente acadêmico local. As portas do host são vinculadas a `127.0.0.1`. Não exponha a plataforma à internet: ainda não existe autenticação de usuários no dashboard. Operações do laboratório exigem token e rejeitam origem diferente; o webhook tem segredo próprio. Os dados do laboratório são de teste. A caixa SMTP local recebe mensagens e não comprova entrega em provedores externos. Mailpit é o canal de alertas, não a integração SMTP monitorada do escopo.
