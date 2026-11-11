# CPU, memória e I/O dos serviços

A página [Recursos](http://localhost:8000/#resources) reúne HTTP, PostgreSQL, DNS e SMTP. Os valores vêm de estatísticas reais dos contêineres; a disponibilidade dos protocolos continua nas sondas de cada serviço.

## Inicializar e encerrar

Na raiz do projeto, com Docker Desktop em modo Linux e Python 3.13 ou posterior:

```powershell
python scripts/configure.py
docker compose up -d --build --wait
python scripts/collect_resources.py --background
```

`scripts/start.ps1` também inicia o coletor. O primeiro uso prepara `.runtime/resource-worker-venv` com Docker SDK 7.2.0 e dependências fixadas por SHA-256 em `requirements-resources.lock.txt`, baixadas do PyPI oficial. Não instala pacotes globais nem acrescenta o SDK à imagem da API. Aguarde duas rodadas para as primeiras taxas; cada rodada é seguida por 5 s de intervalo.

```powershell
python scripts/collect_resources.py --stop
```

O comando solicita encerramento; o processo conclui a rodada limitada por timeout. `--background` pode ser chamado logo depois: aguarda a saída anterior antes de iniciar outro worker. Sem pedido de parada pendente, um worker existente é preservado. Após reiniciar o computador, execute novamente a inicialização. Para diagnóstico em primeiro plano use `--watch`; sem opções, coleta apenas uma rodada.

## Interpretar as medidas

| Medida | Cálculo e unidade | Limite de interpretação |
|---|---|---|
| CPU | Delta do tempo CPU do contêiner dividido pelo tempo real da amostra; núcleos equivalentes | 1,0 = um núcleo ocupado; pode ultrapassar 1,0. Não é percentual do host |
| RAM | Uso menos cache inativo; MiB na interface | Working set, não memória exclusiva de um processo. cgroup v1 prioriza `total_inactive_file`; v2 usa `inactive_file` |
| Leitura/gravação | Delta dos contadores de bytes de blocos dividido pelo intervalo; KiB/s na interface | Sujeito ao cache e à VM. Não mede espaço ocupado, latência nem IOPS |
| Limite de memória do Engine | Campo adicional em bytes na API | Pode ser a memória compartilhada da VM, não orçamento individual |
| Espaço livre do volume do projeto | `shutil.disk_usage` na pasta do projeto, a cada rodada; GiB na interface | É o volume que hospeda o projeto, não o disco virtual interno do Docker; não mede ocupação dos volumes nomeados |

Primeira amostra, troca/reinício do contêiner, contador regressivo ou intervalo inválido interrompem as taxas até duas amostras comparáveis. ID e início da execução são conferidos antes e depois da coleta. Falha de um serviço não remove as medidas dos outros. Zero aparece somente quando há uma medição válida de zero.

Snapshot/medição com mais de 20 s, data futura além de 5 s, arquivo ausente ou inválido deixam as medidas desconhecidas. Durante aquecimento, a memória pode estar disponível antes de CPU/I/O; a interface mostra **Coleta parcial**. O histórico mantém lacunas, com disponibilidade individual e `up` da API, sem prolongar linhas sobre períodos sem coleta. Se o Prometheus falhar, as medidas atuais ainda podem ser consultadas, mas o histórico fica indisponível.

## Alertas e resposta

| Regra | Condição por 30 s | Ação sugerida |
|---|---|---|
| `RecursoCPUElevada` | CPU > 0,8 núcleo | Correlacionar com tráfego, latência e consultas; confirmar coleta atual antes de concluir recuperação |
| `RecursoMemoriaElevada` | RAM > 128 MiB; PostgreSQL > 256 MiB | Conferir crescimento, carga e reinícios; o limiar não é o limite da VM |
| `RecursoIOElevado` | Leitura + gravação > 10 MiB/s | Correlacionar com SQL/fila e atividade; taxa alta não prova disco lento |
| `RecursosColetaIndisponivel` | Snapshot válido indisponível | Verificar Docker, contexto local e worker; consultar as sondas dos protocolos separadamente |
| `RecursoDiscoLivreBaixo` | Espaço livre do volume do projeto < 2 GiB | Liberar espaço antes de continuar; métricas, incidentes e e-mails podem deixar de persistir |

São avisos com orçamentos didáticos; não limitam CPU/RAM/I/O dos contêineres. Prometheus avalia as regras, Alertmanager envia e-mails para a caixa local em [8025](http://localhost:8025), e o webhook persiste incidentes. Os 30 s começam quando a condição é observada; também há intervalos de coleta/avaliação e agrupamento. Uma resolução de consumo durante falta de dados não comprova normalização: observe também a coleta e as medidas atuais.

## Demonstração reproduzível

Com a stack e o coletor ativos, execute os roteiros sequencialmente:

```powershell
.\.venv\Scripts\python.exe scripts/verify_resources.py --exercise-outage
```

O roteiro exige login, valida filtros e histórico, executa um processo temporário no HTTP consumindo CPU por no máximo 75 s, espera incidente/e-mail e cancela a carga. Em seguida confirma recuperação e e-mail, interrompe somente o coletor, aguarda expiração/alertas/e-mails dos quatro serviços e retoma com novas medições. Reinicia a API para conferir persistência, verifica quatro protocolos, oito configurações e 1.000 linhas SQL. O `finally` cancela a carga e tenta retomar o coletor quando necessário; falhas de recuperação são informadas explicitamente. O teste completo leva alguns minutos.

O resultado detalhado de execução fica em `tmp/resources-e2e-result.json`, ignorado pelo Git. A evidência resumida da entrega de 04/11 está em [resources.json](evidencias/resources.json), junto das capturas desktop, celular e aquecimento. Naquela execução passaram 20 verificações, incluindo alertas e e-mails reais. As regras de RAM/I/O foram verificadas com casos isolados no promtool, sem esgotar memória/disco do ambiente.

## Isolamento e limites

O worker usa somente o endpoint local do contexto Docker atual: named pipe Windows ou socket Unix. Contextos TCP/SSH são rejeitados. Ele descobre quatro serviços fixos por labels, consulta apenas identidade/início/estado e estatísticas; não lê variáveis de ambiente. Respostas e subprocessos têm limites de tempo/tamanho, e somente o snapshot normalizado de até 64 KiB é persistido atomicamente.

A API monta `.runtime/resources` somente para leitura em `/etc/aularedes/resources`, sem socket Docker. `/api/resources` exige sessão e aceita apenas serviços/períodos fixos; `/metrics` usa labels limitadas a serviço/métrica, sem IDs nem caminhos. O snapshot depende da integridade do host e do usuário local com acesso ao Docker: não é uma fonte assinada contra adulteração pelo administrador do computador.

Latência de disco por contêiner, IOPS não fornecidas pelo Engine e pools externos permanecem fora desta entrega. O tamanho do banco já possui métrica SQL própria; a latência de disco do PostgreSQL vem de `pg_stat_io` e está documentada no [runbook PostgreSQL](runbook-postgres.md). O espaço livre do volume do projeto é medido a cada rodada do coletor e aparece na página Recursos.

## Referências técnicas

- [Docker: estatísticas e tratamento de cache](https://docs.docker.com/reference/cli/docker/container/stats/)
- [Docker: métricas e cgroups](https://docs.docker.com/engine/containers/runmetrics/)
- [Engine API v1.44](https://docs.docker.com/reference/api/engine/version/v1.44/)
- [SDK oficial para Python](https://docker-py.readthedocs.io/en/stable/containers.html)
- [Pacote Docker SDK 7.2.0](https://pypi.org/project/docker/7.2.0/)
