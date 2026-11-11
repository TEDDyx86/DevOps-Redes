# Especificação: métricas finais da plataforma técnica

Data: 09/11/2026. Objetivo: fechar as pendências técnicas do roadmap antes da
documentação de entrega (relatório ABNT e apresentação).

## Escopo

1. **PostgreSQL — métricas recomendadas restantes**
   - Consultas lentas: contador de comandos do `lab_workload` em
     `pg_stat_statements` com `mean_exec_time` acima de 100 ms
     (`postgres_slow_statements`, gauge).
   - Conexões por estado: ativas e ociosas em `pg_stat_activity`
     (`postgres_connections_active`, `postgres_connections_idle`), como
     alternativa honesta a "pools": o laboratório não tem pool externo.
   - Latência de disco: contadores `pg_stat_io` agregados
     (`postgres_io_reads_total`, `postgres_io_read_time_milliseconds_total`,
     `postgres_io_writes_total`, `postgres_io_write_time_milliseconds_total`).
     A latência média é derivada no PromQL como `rate(tempo)/rate(operações)`;
     divisão por zero vira `None` (desconhecido), nunca zero.
   - Crescimento do banco: `rate(postgres_database_bytes[1h]) * 86400`
     convertido para GiB/dia na API e na página.
   - Alertas novos (atenção, 30 s): `PostgreSQLConsultasLentas`
     (`postgres_slow_statements > 0`) e `PostgreSQLDiscoLento`
     (latência média de leitura ou gravação acima de 50 ms).
   - A disponibilidade das estatísticas continua gating: sem
     `postgres_stats_success`, os campos novos aparecem como desconhecidos.

2. **Autenticação do serviço monitorado (web-demo)**
   - Contadores no serviço de demonstração: `demo_auth_failures_total{path}`
     para tentativas de `POST /mode` com token inválido e
     `demo_auth_accepted_total{path}` para aceitações. O job `web-demo` do
     Prometheus já coleta `/metrics`.
   - Alerta novo (atenção): `AutenticacaoServicoSuspeita` quando
     `increase(demo_auth_failures_total[1m]) >= 5` por 10 s — brute-force no
     serviço monitorado, distinto do painel (já coberto por
     `AutenticacaoSuspeita`).
   - DNS e SMTP não têm superfície de autenticação própria no laboratório
     (CoreDNS sem AUTH; SMTP de laboratório aceita por endereço). O
     PostgreSQL tem autenticação em nível de conexão; falhas aparecem nas
     sondas. Limitação registrada no runbook.

3. **Espaço livre do host**
   - O coletor local de recursos acrescenta ao snapshot um bloco `host` com
     `free_bytes` e `total_bytes` de `shutil.disk_usage` na pasta do projeto
     (somente biblioteca padrão; nenhuma dependência nova).
   - `schema_version` vai a 2; a validação aceita snapshot sem `host`
     (compatibilidade durante a reconstrução).
   - Novo gauge sem rótulo de serviço:
     `service_resource_host_free_bytes` e
     `service_resource_host_total_bytes`.
   - Alerta novo (atenção, 30 s): `RecursoDiscoLivreBaixo` quando o espaço
     livre fica abaixo de 2 GiB.
   - A página Recursos mostra o espaço livre do host; ausência do bloco fica
     como desconhecido.

## Fora do escopo desta especificação

- Triagem operacional dos achados médios/baixos de vulnerabilidade: exige a
  stack em execução e decisão registrada no runbook; feito após esta etapa.
- Relatório ABNT, roteiro de apresentação e revisão final: próxima fase.
- Latência de disco do host inteiro e por contêiner do Engine: o Docker não
  expõe latência por contêiner; para o banco, `pg_stat_io` cobre o
  requisito. Registrado como limitação.

## Critérios de aceite

- Todos os campos novos aparecem como desconhecidos quando a fonte falha
  (sem zeros inventados nem NaN na API).
- Testes backend e frontend passam; `promtool check config` e `amtool
  check-config` válidos após mudar `alerts.yml`.
- Demonstrações verificáveis: consulta lenta provocável no laboratório,
  falhas de token contadas e alerta disparável, espaço livre visível.
