# Runbook HTTP e playbook de incidentes

## Operação diária

1. Verifique se Docker Desktop está em execução.
2. Execute `python scripts/configure.py` na primeira instalação.
3. Execute `docker compose up -d --build --wait`.
4. Confira `docker compose ps` e o dashboard em http://localhost:8000.
5. Aguarde as primeiras coletas antes de interpretar taxas.

## HTTP indisponível

**Sinal:** estado vermelho e, após confirmação de 15 s, alerta HTTPIndisponivel.

**Investigar:**

1. Consulte `/health` do serviço em http://localhost:8011/health.
2. Abra Laboratório e confira se o modo indisponível foi aplicado intencionalmente.
3. Execute `docker compose logs --tail 100 web-demo api`.
4. Verifique alvos de coleta em http://localhost:9090/targets.

**Recuperar:** volte ao modo normal pelo Laboratório, usando LAB_TOKEN do `.env`. Se o processo não responde, execute `docker compose restart web-demo`. Reinício encerra o modo de falha controlado.

**Confirmar:** HTTP 200, estado verde no dashboard, incidente resolvido e mensagem de recuperação no Mailpit. Registre horários e evidências no relatório.

## HTTP lento

**Sinal:** sonda acima de 500 ms; alerta HTTPLento após 30 s persistentes.

**Investigar:** compare duração da sonda e p95, observe RPS e modo do laboratório. O modo lento adiciona 850 ms às respostas; é uma injeção controlada, não congestionamento real de rede.

**Recuperar:** restaure modo normal. Aguarde atualização da sonda; o p95 móvel pode continuar elevado enquanto amostras lentas ainda estiverem na janela de um minuto.

## Sem dados

**Sinal:** estado desconhecido ou aviso de indisponibilidade do Prometheus.

1. Execute `docker compose ps`.
2. Consulte `docker compose logs --tail 100 prometheus api`.
3. Confira alvos no Prometheus. Um alvo UP não comprova que o HTTP monitorado está saudável.
4. Reative o componente parado. Não interprete ausência de coleta como disponibilidade.

## E-mail não aparece

1. Confirme se a regra está firing em http://localhost:9090/alerts, não apenas pending.
2. Confira o alerta em http://localhost:9093.
3. Abra http://localhost:8025; não procure na caixa pessoal, pois o destino é local.
4. Execute `docker compose logs --tail 100 alertmanager mailpit`.
5. Se o incidente não aparece, confira API, segredo e logs do webhook. Reexecute `python scripts/configure.py` e reinicie API/Alertmanager se o segredo local tiver mudado.

## Encerramento

Restaure o modo normal antes de encerrar a demonstração. Use `docker compose down` para parar sem remover os volumes. Preserve o `.env` local e não inclua segredos em capturas de tela ou no relatório.
