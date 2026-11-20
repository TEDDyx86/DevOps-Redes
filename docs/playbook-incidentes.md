# Playbook de Resposta a Incidentes

Este documento define o fluxo operacional único de resposta a incidentes da plataforma de monitoramento **AulaRedes**, integrando os níveis de alerta exigidos, o canal de notificações por e-mail e o roteamento para cada runbook específico.

## 1. Níveis de alerta e ações esperadas

| Nível | Estado no painel | Severidade (Prometheus / Alertmanager) | Ação automática e resposta esperada |
|---|---|---|---|
| **Nível 1 — Verde (OK)** | `Operacional` | — | Estado normal. Nenhuma notificação é disparada. Quando um incidente anterior normaliza, o Alertmanager envia e-mail de resolução (`[AulaRedes] resolved`) e o histórico marca o registro como **Resolvido**. |
| **Nível 2 — Amarelo (Atenção)** | `Atenção` | `warning` | Indica degradação ou condição anômala que exige observação (latência elevada, fila crescendo, orçamento de recurso excedido, tráfego anormal, falha de autenticação, alteração de arquivo ou vulnerabilidade alta). **Ação:** notificação por e-mail em `http://localhost:8025` e triagem pelo runbook da categoria. |
| **Nível 3 — Vermelho (Crítico)** | `Indisponível` / `Achado crítico` | `critical` | Indica serviço indisponível, falha persistente de protocolo, queda da coleta da plataforma ou vulnerabilidade crítica conhecida. **Ação:** notificação imediata por e-mail (`group_wait: 0s`, `group_interval: 5s`), abertura de incidente em `http://localhost:8000/#incidents` e contenção prioritária. |
| **Sem dados (`unknown`)** | `Sem dados` | `*ColetaIndisponivel` / `ColetaIndisponivel` | Coleta ausente ou expirada (> 20 s). **Nunca** deve ser interpretada como estado saudável. |

> **Canal de notificação independente:** o Alertmanager entrega alertas ao Mailpit (`mailpit:1025`, caixa web em `http://localhost:8025`), separado do servidor SMTP monitorado (`smtp:2525` / `http://localhost:8026`). Mesmo quando o SMTP monitorado falha, os e-mails de alerta continuam funcionando.

## 2. Fluxo padrão de resposta (6 etapas)

```mermaid
flowchart LR
    D[1. Detectar] --> C[2. Conter] --> G[3. Diagnosticar] --> R[4. Remediar] --> M[5. Comunicar] --> V[6. Revisar]
```

1. **Detectar:** confirmar o alerta em `http://localhost:8000/#incidents`, no Prometheus (`http://localhost:9090/alerts`) e o recebimento do e-mail em `http://localhost:8025`. Verificar se o alerta está `firing` (confirmado após a janela `for:`) ou apenas `pending`.
2. **Conter:** avaliar se a falha decorre de teste ativo no **Laboratório** (`:8000/#lab`) ou na aba **Ataques** (`:8000/#attacks`), isolar o componente afetado sem destruir volumes de dados (`não` executar `docker compose down -v`).
3. **Diagnosticar:** consultar o dashboard do serviço afetado, logs (`docker compose logs --tail 100 <serviço>`), alvos do Prometheus (`http://localhost:9090/targets`) e estado dos coletores locais (`scan_vulnerabilities.py`, `collect_resources.py`).
4. **Remediar:** executar os passos do runbook correspondente ao alerta (restaurar serviço, normalizar modo do laboratório, aprovar ou reverter arquivo alterado, liberar espaço em disco, corrigir imagem).
5. **Comunicar e confirmar recuperação:** validar que o estado voltou para **Verde (Operacional)** no painel, o incidente foi marcado como **Resolvido** e o e-mail de recuperação chegou ao Mailpit (`:8025`).
6. **Revisar (pós-incidente):** registrar causa raiz, tempo de detecção/recuperação, se houve perda de resolução (casos marcados como **Reconciliado** — ver [runbook de incidentes](runbook-incidentes.md)) e ações preventivas.

## 3. Catálogo de alertas e roteamento para runbooks

### 3.1 Aplicação HTTP (`web-demo`) e coleta da plataforma
| Alerta | Nível | Janela `for:` | Causa provável | Ação imediata | Runbook |
|---|---|---|---|---|---|
| `HTTPIndisponivel` | Crítico | 15 s | `web-demo` em modo `offline` ou contêiner parado/falhando `/health` | Conferir `/health` (`:8011/health`), restaurar modo `normal` em `#lab` ou `docker compose restart web-demo` | [runbook-http.md](runbook-http.md) |
| `HTTPLento` | Atenção | 30 s | `web-demo` em modo `slow` (+850 ms) ou sobrecarga | Verificar modo no Laboratório e latência p95 em `#service` | [runbook-http.md](runbook-http.md) |
| `ColetaIndisponivel` | Crítico | 15 s | API FastAPI (`api`) fora do ar ou inacessível ao Prometheus | Executar `docker compose ps` e `docker compose logs api`; restaurar `api` | [runbook-http.md](runbook-http.md) |

### 3.2 Banco de Dados (`postgres`)
| Alerta | Nível | Janela `for:` | Causa provável | Ação imediata | Runbook |
|---|---|---|---|---|---|
| `PostgreSQLIndisponivel` | Crítico | 15 s | Contêiner `postgres` parado, sem aceitar conexões ou credenciais inválidas | `docker compose start postgres` e checar `pg_isready` | [runbook-postgres.md](runbook-postgres.md) |
| `PostgreSQLLento` | Atenção | 30 s | Conexão + `SELECT 1` > 500 ms | Conferir carga, recursos do host/contêiner e logs do `postgres` | [runbook-postgres.md](runbook-postgres.md) |
| `PostgreSQLConexoesElevadas` | Atenção | 30 s | Mais de 80% do `max_connections` ocupado | Inspecionar sessões ativas/ociosas em `#postgres` | [runbook-postgres.md](runbook-postgres.md) |
| `PostgreSQLEstatisticasIndisponiveis` | Atenção | 30 s | `pg_stat_statements` ausente ou permissão `pg_monitor` revogada | Verificar extensões e papéis SQL conforme runbook | [runbook-postgres.md](runbook-postgres.md) |
| `PostgreSQLConsultasLentas` | Atenção | 30 s | Comandos de `lab_workload` com média > 100 ms | Investigar consultas e índices no banco | [runbook-postgres.md](runbook-postgres.md) |
| `PostgreSQLDiscoLento` | Atenção | 30 s | Latência média de leitura/gravação (`pg_stat_io`) > 50 ms | Avaliar I/O do volume e disco do host | [runbook-postgres.md](runbook-postgres.md) |

### 3.3 DNS (`dns` — CoreDNS)
| Alerta | Nível | Janela `for:` | Causa provável | Ação imediata | Runbook |
|---|---|---|---|---|---|
| `DNSIndisponivel` | Crítico | 15 s | CoreDNS parado ou zona `aularedes.test` retornando resposta incorreta em UDP/TCP | Checar `docker compose logs dns`, `Corefile` e `db.aularedes.test`; reiniciar `dns` | [runbook-dns.md](runbook-dns.md) |
| `DNSLento` | Atenção | 30 s | Sonda UDP/TCP > 100 ms | Verificar contenção de CPU/rede e flood DNS | [runbook-dns.md](runbook-dns.md) |
| `DNSErrosElevados` | Atenção | 30 s | Mais de 10% de respostas `SERVFAIL`/`REFUSED`/`FORMERR`/`NOTIMP` | Inspecionar consultas de erro e logs do CoreDNS | [runbook-dns.md](runbook-dns.md) |

### 3.4 SMTP (`smtp` + `smtp-inbox`)
| Alerta | Nível | Janela `for:` | Causa provável | Ação imediata | Runbook |
|---|---|---|---|---|---|
| `SMTPIndisponivel` | Crítico | 15 s | Servidor `smtp:2525` parado ou recusando `EHLO`/`NOOP` | `docker compose start smtp` e checar logs | [runbook-smtp.md](runbook-smtp.md) |
| `SMTPFilaElevada` | Atenção | 30 s | 5 ou mais mensagens pendentes (ex.: `smtp-inbox` parado) | Verificar `smtp-inbox` (`docker compose start smtp-inbox`) | [runbook-smtp.md](runbook-smtp.md) |
| `SMTPLento` | Atenção | 30 s | Resposta `EHLO` + `NOOP` > 500 ms | Avaliar carga no `smtp` e lock do spool SQLite | [runbook-smtp.md](runbook-smtp.md) |
| `SMTPEstatisticasIndisponiveis` | Atenção | 30 s | SMTP responde, mas `/metrics` (`:8027`) falhou | Reiniciar/inspecionar o container `smtp` | [runbook-smtp.md](runbook-smtp.md) |

### 3.5 Segurança e monitoramentos extras
| Alerta | Nível | Janela `for:` | Causa provável | Ação imediata | Runbook |
|---|---|---|---|---|---|
| `TrafegoAnormal` | Atenção | 30 s | Taxa do serviço > `max(3× referência, piso)` (pico/flood) | Conferir origem do tráfego, job de carga em `#lab` ou `#attacks` | [runbook-trafego.md](runbook-trafego.md) |
| `TrafegoColetaIndisponivel` | Atenção | 30 s | Sonda/fonte indisponível para calcular taxa de tráfego | Verificar Prometheus e o serviço correspondente | [runbook-trafego.md](runbook-trafego.md) |
| `AutenticacaoSuspeita` | Atenção | 10 s | >= 5 falhas por IP ou >= 10 por conta em 60 s no painel (`:8000`) | Conferir IPs/usuários em `#security`; aguardar janela de bloqueio (60 s) | [runbook-autenticacao.md](runbook-autenticacao.md) |
| `AutenticacaoServicoSuspeita` | Atenção | 30 s | >= 5 tentativas com token inválido em `POST /mode` no `web-demo` | Conferir origem de chamadas ao `web-demo` | [runbook-autenticacao.md](runbook-autenticacao.md) |
| `ConfiguracaoAlterada` | Atenção | 15 s | SHA-256 diferente da referência ou arquivo ausente em `infra/` | Comparar diff no Git; restaurar arquivo ou aprovar novo hash em `#security` | [runbook-integridade.md](runbook-integridade.md) |
| `ConfiguracaoVerificacaoIndisponivel` | Atenção | 30 s | Erro de leitura ou snapshot antigo (> 30 s) | Verificar montagem `./infra:/etc/aularedes/observed:ro` e logs da `api` | [runbook-integridade.md](runbook-integridade.md) |
| `ConfiguracaoReferenciaPendente` | Atenção | 2 min | Arquivo legível ainda sem hash aprovado inicialmente | Revisar conteúdo e aprovar hashes em `#security` com `LAB_TOKEN` | [runbook-integridade.md](runbook-integridade.md) |
| `VulnerabilidadeCritica` | Crítico | 30 s | CVE crítica detectada na imagem do serviço | Avaliar aplicabilidade e atualizar/recompilar imagem | [runbook-vulnerabilidades.md](runbook-vulnerabilidades.md) / [runbook-postgres-remediation.md](runbook-postgres-remediation.md) |
| `VulnerabilidadeAlta` | Atenção | 30 s | CVE alta (sem crítica) na imagem do serviço | Fazer triagem na aba `#security` (checar estado `wont-fix` ou correção) | [runbook-vulnerabilidades.md](runbook-vulnerabilidades.md) |
| `VulnerabilidadeAnaliseIndisponivel` | Atenção | 2 min | Worker `scan_vulnerabilities.py` parado ou relatório/base vencido | Iniciar/verificar `python scripts/scan_vulnerabilities.py --background` | [runbook-vulnerabilidades.md](runbook-vulnerabilidades.md) |

### 3.6 Recursos de infraestrutura (CPU, memória, I/O e disco)
| Alerta | Nível | Janela `for:` | Causa provável | Ação imediata | Runbook |
|---|---|---|---|---|---|
| `RecursoCPUElevada` | Atenção | 30 s | Contêiner acima de 0,8 núcleo equivalente | Identificar carga/flood e estabilizar serviço | [runbook-recursos.md](runbook-recursos.md) |
| `RecursoMemoriaElevada` | Atenção | 30 s | Working set > 128 MiB (ou > 256 MiB no PostgreSQL) | Inspecionar consumo de processos no contêiner | [runbook-recursos.md](runbook-recursos.md) |
| `RecursoIOElevado` | Atenção | 30 s | Leitura + gravação de blocos > 10 MiB/s | Identificar consultas ou cargas gerando I/O | [runbook-recursos.md](runbook-recursos.md) |
| `RecursosColetaIndisponivel` | Atenção | 30 s | Worker `collect_resources.py` parado ou snapshot expirado | Iniciar `python scripts/collect_resources.py --background` | [runbook-recursos.md](runbook-recursos.md) |
| `RecursoDiscoLivreBaixo` | Atenção | 30 s | Menos de 2 GiB livres no volume que hospeda o projeto | Liberar espaço em disco no host antes de perder persistência | [runbook-recursos.md](runbook-recursos.md) |

## 4. Pós-incidente e reconciliação

- O histórico em `http://localhost:8000/#incidents` exibe os últimos 100 registros persistidos no volume `incidents` (`incidents.sqlite`), independentemente do PostgreSQL monitorado.
- Se uma interrupção impedir o recebimento de um evento `resolved`, resoluções diretas posteriores do mesmo incidente reconciliam automaticamente o ciclo antigo como **Reconciliado**, preservando o início original sem inventar um horário de término falso ([runbook-incidentes.md](runbook-incidentes.md)).
