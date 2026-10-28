# Arquitetura e métricas

## Fluxo da etapa HTTP

```mermaid
flowchart LR
    UI[React] --> API[FastAPI]
    API -->|consultas fixas PromQL| P[Prometheus]
    API -->|sonda health e tráfego work| D[HTTP de demonstração]
    P -->|scrape 5 s| API
    P -->|scrape 5 s| D
    P -->|regras confirmadas| A[Alertmanager]
    A -->|webhook autenticado| API
    API --> S[(SQLite: incidentes)]
    A -->|SMTP| M[Mailpit: caixa local]
```

O frontend compilado é servido pelo FastAPI, no mesmo host e porta. Apenas o backend acessa Prometheus a partir da interface. Consultas PromQL são fixas no código, sem entrada livre do navegador. O backend também executa a sonda do laboratório; um worker separado pode ser extraído quando houver outros serviços.

## Componentes e dados

| Componente | Persistência | Responsabilidade |
|---|---|---|
| API | Volume incidents | Consultas, sonda, controles e recebimento de eventos |
| Serviço demo | Modo em memória | Respostas e métricas HTTP reais |
| Prometheus | Volume metrics, 7 dias | Séries temporais e avaliação de regras |
| Alertmanager | Volume alerts | Deduplicação, e-mail e webhook |
| Mailpit | Volume mail, até 200 mensagens | Recebimento local de SMTP |

SQLite é suficiente para eventos desta primeira etapa. A expansão para banco inclui um PostgreSQL para a aplicação e outro serviço monitorado separado, evitando que uma falha didática interrompa o armazenamento de incidentes.

## Significado dos indicadores

| Indicador | Fonte | Observação |
|---|---|---|
| Estado HTTP | GET /health | 2xx significa sucesso; timeout/erro significa falha |
| Última coleta | probe_checked_at_seconds | Momento real da conclusão da sonda |
| Latência da sonda | probe_duration_seconds | Tempo de uma verificação, em ms na interface |
| Disponibilidade | avg_over_time(probe_success[período]) | Percentual sobre sondas existentes, não sobre o tempo anterior à instalação |
| RPS | rate(demo_http_requests_total[1m]) | Somente /work; exclui tráfego de health e métricas |
| Erros | rate(4xx + 5xx) / rate(total) | Percentual no último minuto; sem tráfego significa sem valor |
| p95 | histogram_quantile(0.95, rate(buckets[1m])) | Estimativa por histograma, não duração exata de cada requisição |

Taxas usam janela móvel de um minuto. O seletor 15m/1h/6h/24h define o intervalo exibido e o cálculo de disponibilidade. Histogramas preservam as falhas HTTP 503. O endpoint `/metrics` continua acessível nos modos de falha, permitindo distinguir um serviço HTTP com erro de um coletor indisponível.

## Estado observado e alerta confirmado

- OK: última sonda bem-sucedida, duração até 500 ms.
- Atenção: última sonda bem-sucedida acima de 500 ms.
- Crítico: última sonda falhou.
- Sem dados: ausência de resultado ou sonda com mais de 20 s, incluindo Prometheus indisponível.

Um estado pontual não é um incidente confirmado. As regras exigem 30 s de lentidão ou 15 s de falha, avaliadas a cada 5 s. A indisponibilidade da API/coletor também tem alerta próprio, emitido pelo Prometheus. E-mails desse alerta podem chegar enquanto o webhook aguarda a API voltar.

O webhook usa a chave composta `(fingerprint, startsAt)` para manter um evento por ocorrência. Resoluções são persistidas; uma notificação firing atrasada não reabre um evento resolvido. Os horários são armazenados em UTC e exibidos no fuso do navegador.

## Referências técnicas

- [Prometheus: visão geral](https://prometheus.io/docs/introduction/overview/)
- [HTTP API do Prometheus](https://prometheus.io/docs/prometheus/latest/querying/api/)
- [Configuração do Alertmanager](https://prometheus.io/docs/alerting/latest/configuration/)
- [Lifespan do FastAPI](https://fastapi.tiangolo.com/advanced/events/)
- [Redes no Docker Compose](https://docs.docker.com/compose/how-tos/networking/)
