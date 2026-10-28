# PostgreSQL monitorado

Autorização: o usuário escolheu PostgreSQL local após comparar com Supabase e pediu para iniciar a integração.

## Entrega

Adicionar o segundo serviço real ao dashboard, com disponibilidade SQL, duração de conexão + SELECT 1, conexões abertas, commits/s, rollbacks/s, tamanho do banco e comandos SQL/s do usuário de laboratório. O PostgreSQL monitorado fica em volume próprio; incidentes continuam no SQLite independente.

## Decisões

- PostgreSQL 17.11 em Docker, sem porta publicada no host; acesso pelo backend e por `docker compose exec`.
- Coletor SQL próprio, pequeno e somente leitura, integrado ao endpoint `/metrics` existente. Isso evita um container adicional de exporter e permite explicar cada consulta no relatório.
- `pg_stat_statements` habilitado para contar comandos executados pelo usuário de laboratório. Comandos SQL/s não são transações/s: ambos aparecem com rótulos distintos.
- Credenciais distintas para administração, monitoramento (`pg_monitor`) e carga de demonstração (apenas a tabela de teste). Geradas localmente e ignoradas no Git.
- Sonda e gerador SQL executam em tarefas independentes do monitor HTTP. Falhas do banco têm timeout e reconexão; não interrompem API, métricas HTTP ou persistência dos incidentes.
- Rota `/api/postgres?window=15m` retorna detalhe e séries; a visão geral contém os dois serviços. Compatibilidade com o contrato HTTP existente é preservada.
- Estado desconhecido em dados ausentes ou com idade acima de 20 s; falha SQL confirmada é crítica. Estatísticas antigas são ocultadas quando o banco está indisponível.
- Alertas: PostgreSQL indisponível por 15 s; conexões acima de 80% por 30 s; falha da coleta de estatísticas por 30 s. E-mail e webhook usam infraestrutura existente.
- Controle de interrupção por comandos explícitos no terminal, sem dar acesso ao Docker à API: `docker compose stop postgres` / `docker compose start postgres`.
- CPU, memória, disco, slow queries e pools não são inventados: precisam de instrumentação complementar em etapas posteriores.

## Verificação

Testes de ausência e staleness, falha com métricas antigas, independência de HTTP, estatísticas reais, privilégios dos usuários, persistência após restart, alerta/e-mail e recuperação. Navegação desktop/mobile mantém o sistema visual existente.
