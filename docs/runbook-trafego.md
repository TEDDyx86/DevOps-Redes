# Detecção de tráfego acima da referência

## Acompanhar

Abra [Segurança](http://localhost:8000/#security) após entrar no painel. A tabela mostra a taxa estimada no último minuto, a referência persistida e o limiar de aviso de cada serviço.

| Serviço | Tráfego medido | Piso do limiar |
|---|---|---|
| HTTP | Requisições `/work` por segundo, incluindo respostas com erro | 2 req/s |
| PostgreSQL | Comandos/s registrados em pg_stat_statements para lab_workload | 5 comandos/s |
| DNS | Consultas/s no CoreDNS, incluindo as sondas | 5 consultas/s |
| SMTP | Mensagens aceitas no SMTP; interface converte para msg/min | 9 msg/min |

A taxa usa `rate(contador[1m])`; é uma estimativa com tratamento de resets, não uma contagem exata da janela. Consulte a [documentação de funções Prometheus](https://prometheus.io/docs/prometheus/latest/querying/functions/#rate).

## Referência e estados

Na primeira execução, mantenha o laboratório em operação habitual. Cada referência exige **pelo menos 25 amostras válidas cobrindo 120 segundos**, com intervalo máximo de 15 s entre amostras. A carga periódica existente fornece o tráfego real. Uma falha ou lacuna reinicia apenas o aprendizado ainda não concluído do serviço afetado.

A média dessas amostras é persistida em `traffic.sqlite`, no volume de incidentes, separado de PostgreSQL/DNS/SMTP. Depois de pronta, fica fixa, inclusive durante picos e reinícios da API. O limiar é `max(3 × referência, piso do serviço)`; somente taxa **maior** que esse limiar indica volume elevado. Uma referência zero é válida e usa o piso.

- **Aprendendo:** há taxa válida, mas a referência ainda não ficou pronta.
- **Volume normal:** taxa válida, referência pronta e limiar não excedido.
- **Acima do limiar:** taxa válida superior ao limiar. O estado pode preceder o incidente.
- **Sem dados:** Prometheus, sonda ou estatísticas necessárias indisponíveis/antigas; não equivale a volume zero ou normal.

O coletor roda em tarefa independente a cada ciclo de aproximadamente 5 s. Só considera taxas com sonda bem-sucedida e fonte recente. PostgreSQL exige também estatísticas válidas; HTTP/SQL/DNS/SMTP não se substituem quando uma fonte falha. Interface e exportador expiram o estado atual em 20 s.

O alerta `TrafegoAnormal` confirma 30 s acima do limiar por serviço. `TrafegoColetaIndisponivel` confirma 30 s sem taxa válida. Se uma fonte desaparecer, o alerta de volume pode resolver por ausência da série; isso não prova recuperação do serviço. Confira o estado “Sem dados” e os alertas de coleta/disponibilidade. A [documentação de regras Prometheus](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) explica a confirmação pela cláusula `for`.

## Demonstrar carga controlada

1. Abra [Laboratório](http://localhost:8000/#lab) e informe `LAB_TOKEN` do `.env` no campo existente.
2. Aguarde os quatro serviços em **Volume normal** na aba Segurança, com referências prontas.
3. Em **Teste de tráfego**, selecione um serviço ou todos e inicie a carga de 90 s.
4. Acompanhe taxas, incidentes e os e-mails em http://localhost:8025.
5. O job termina automaticamente; também é possível usar **Encerrar carga**. Aguarde a janela móvel de 1 minuto escoar e confira a resolução e os e-mails de recuperação.

Limites de geração: HTTP até 5 req/s, SQL até 10 SELECT 1/s com lab_workload, DNS até 10 consultas A/s, SMTP até 1 mensagem/s para aluno@aularedes.test. Só um job por vez; teto de operações = taxa limite × duração. Uma operação por serviço de cada vez, sem rajadas de compensação. Cada operação tem prazo global de 3 s, com fechamento de conexões no cancelamento; mensagens já aceitas podem continuar sua entrega pela fila SMTP independente. Contadores distinguem sucessos, falhas e cancelamentos em voo.

O cliente SMTP da demonstração usa streams assíncronos canceláveis, respostas limitadas e DATA de conteúdo fixo. Não deixa uma thread de envio trabalhando após encerrar o job. Nenhum alvo, endereço de e-mail, comando SQL ou URL livre é recebido do navegador. São usados apenas os serviços configurados na stack local. Não há acesso ao socket Docker.

Os controles exigem sessão, CSRF, origem permitida e LAB_TOKEN; consultar o estado exige sessão. Não inicie a demonstração simultaneamente com scripts que param serviços ou com rebuilds da stack. O estado/counters do job ficam em memória e voltam a “nenhum teste iniciado” após reiniciar a API. As referências persistem.

## Recalibrar após uma mudança de uso

Na tabela de tráfego, expanda **Recalibrar referência em operação habitual**, escolha o serviço e informe LAB_TOKEN. Isso remove apenas sua referência e começa outro aprendizado. A ação exige dados atuais e volume normal e é bloqueada durante o teste de carga. Controles de iniciar/cancelar/recalibrar são serializados para impedir disputas.

Use após uma mudança intencional no padrão habitual. A referência inicial pressupõe que o ambiente era representativo durante o aprendizado; não sabe, sozinha, se aquele tráfego era legítimo. Não há aprendizado automático de picos, modelo de ML, atribuição por IP ou comprovação de DDoS.

## Repetir a verificação automatizada

```powershell
.\.venv\Scripts\python.exe scripts/verify_traffic.py
```

O roteiro aguarda referências prontas, testa proteção/concorrência/cancelamento, gera os quatro protocolos por 90 s e confirma taxas, quatro incidentes, quatro e-mails de abertura, fim automático, recuperação e quatro e-mails de resolução. Também reinicia a API e verifica a persistência das referências. Cancela qualquer job em `finally`; relatório sem credenciais em `tmp/traffic-e2e-result.json`.

Em 29/10/2026, as 20 verificações passaram com os quatro serviços operacionais ao final. Imagens em `docs/evidencias/traffic-anomalous.jpg`, `traffic-desktop.jpg` e `traffic-mobile.jpg`.
