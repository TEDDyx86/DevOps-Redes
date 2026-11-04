# Runbook PostgreSQL

## Iniciar e consultar

Na raiz do projeto, execute `python scripts/configure.py` para acrescentar os segredos SQL e preservar os tokens HTTP existentes. Depois execute `docker compose up -d --build --wait`. O serviço `postgres` não publica porta no host.

Abra http://localhost:8000/#postgres. A coleta ocorre a cada ciclo de aproximadamente 5 s; as taxas exigem pelo menos duas amostras. A conexão do monitor usa o papel `lab_monitor` com `pg_monitor` e transações somente leitura. A carga usa outro papel, com permissão apenas para ler/atualizar `lab_items`.

## O que os números representam

- **Disponibilidade SQL:** conexão autenticada e `SELECT 1` bem-sucedidos.
- **Latência:** abertura da conexão e execução de `SELECT 1`; não é p95 nem duração média das queries de aplicação.
- **Conexões:** `pg_stat_database.numbackends` do banco `lab_network`. O denominador é `max_connections` do cluster dedicado, incluindo seus slots reservados; não representa capacidade útil restante.
- **Commits e rollbacks/s:** taxas dos contadores do banco, incluindo monitoramento e carga. Rollback intencional não é necessariamente falha de consulta.
- **Comandos SQL/s:** taxa de `calls` do `pg_stat_statements`, limitada ao usuário `lab_workload`, incluindo comandos de controle de transação rastreados pela extensão.
- **Tamanho:** `pg_database_size`, exibido em MiB, sem inventar crescimento anterior à instalação.

O gerador lê e atualiza uma tabela fixa de 1.000 registros a cada 2 s. A cada cinco transações, uma é desfeita propositalmente. Não há crescimento ilimitado de registros. Estatísticas do PostgreSQL são atualizadas de forma assíncrona e podem atrasar um ciclo.

## Indisponibilidade: demonstração e recuperação

1. Confirme HTTP e PostgreSQL operacionais na visão geral.
2. Execute `docker compose stop postgres`.
3. Observe PostgreSQL indisponível; HTTP, API e registro de incidentes continuam funcionando.
4. Aguarde 15 s de falha persistente, além dos intervalos de coleta e avaliação.
5. Confira o incidente PostgreSQL e a caixa local em http://localhost:8025.
6. Execute `docker compose start postgres`.
7. Confirme reconexão, retorno das métricas e resolução do incidente com e-mail de recuperação.

Os dados ficam no volume `postgres-data`. Não use `docker compose down -v` para parar o laboratório, pois remove os volumes.

Desde 30/10, a imagem mantém PostgreSQL 17.11 e recompila o gosu com Go 1.27.3. Para atualizar uma instalação com dados, consultar o [procedimento de triagem, backup validado e reversão](runbook-postgres-remediation.md) antes de reconstruir/substituir o serviço.

## Investigar falha inesperada

```powershell
docker compose ps
docker compose logs --tail 100 postgres api
docker compose exec postgres pg_isready -U lab_admin -d lab_network
```

Se SQL responde mas as estatísticas não, confira a extensão e as permissões:

```powershell
docker compose exec postgres psql -U lab_admin -d lab_network -c "SELECT extname FROM pg_extension"
docker compose exec postgres psql -U lab_admin -d lab_network -c "SELECT pg_has_role('lab_monitor', 'pg_monitor', 'member')"
```

Arquivos de inicialização só são aplicados ao criar um volume vazio. Alterar senhas em `.env` não muda os papéis já persistidos. Em um ambiente existente, faça a rotação no banco e atualize a configuração correspondente; não remova o volume como solução automática.

## Repetir a verificação integrada

```powershell
.\.venv\Scripts\python.exe scripts/verify_postgres.py
```

O roteiro verifica métricas, privilégios, parada real, independência do HTTP, alerta, e-mail, recuperação e preservação dos registros. Restaura o banco no bloco `finally`. Resultados temporários ficam em `tmp/postgres-e2e-result.json`, sem credenciais.

## Limites

A página [Recursos](http://localhost:8000/#resources) complementa o monitor SQL com CPU, memória e I/O de blocos do contêiner. [Unidades e limites](runbook-recursos.md). Latência de disco, espaço livre do host, pools de conexão e contagem de cada consulta lenta ainda exigem instrumentação complementar. Não confundir SQL respondendo com aplicação saudável em todas as consultas.
