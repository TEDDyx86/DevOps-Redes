# Especificação: painel de ataques automatizados

Data: 11/11/2026. Objetivo: criar uma ferramenta separada para disparar
ataques controlados contra o laboratório, com visualização do andamento, de
modo que os efeitos gerem alertas reais no painel de monitoramento existente.

## Visão geral

Serviço local no host, porta **8002**, acesso restrito a `127.0.0.1`:
pequeno servidor HTTP (FastAPI, mesmo estilo do web-demo) que serve uma
página estática própria (sem build) e expõe uma API com streaming de eventos
(SSE). Um motor em thread de background executa os ataques de uma fila, um
por vez. O painel de ataques não publica métricas no Prometheus; ele apenas
**lê** a API do Prometheus para verificar se o alerta esperado disparou.
Código em `scripts/attack_panel/`, seguindo o padrão dos coletores locais
(lock exclusivo, estado em `tmp/`, venv do projeto).

## Catálogo de ataques (1–8)

| # | Nome | Execução | Alerta alvo |
|---|------|----------|-------------|
| 1 | Brute-force no serviço | N tentativas de `POST /mode` com token inválido no web-demo (`:8001`) | `AutenticacaoServicoSuspeita` |
| 2 | Brute-force no painel | Tentativas de login com senha errada no dashboard (`:8000`) | `AutenticacaoSuspeita` |
| 3 | Sobrecarga HTTP | Maré de requisições `GET /work` no web-demo a partir do host | `RecursoCPUElevada` e `TrafegoAnormal` (qualquer um) |
| 4 | Indisponibilidade | Modo `offline` do web-demo via `POST /mode` (token `LAB_TOKEN` do `.env`) | `HTTPIndisponivel` |
| 5 | Flood DNS | Job de carga limitada da plataforma (`POST /api/lab/traffic`, serviço `dns`) | `TrafegoAnormal` (DNS) |
| 6 | Flood SMTP | Job de carga limitada da plataforma (`POST /api/lab/traffic`, serviço `smtp`) | `TrafegoAnormal` (SMTP) |
| 7 | Adulteração de configuração | Modifica arquivo em `./infra` no host (montagem do contêiner é somente leitura) | `ConfiguracaoAlterada` |
| 8 | Interrupção de serviço | `docker compose stop` em um serviço escolhido | `Indisponibilidade*` do protocolo (`DNSIndisponivel`, `SMTPIndisponivel`, `HTTPIndisponivel`, `PostgreSQLIndisponivel`) |

Cada ataque define parâmetros padrão sensatos (intensidade, duração,
alvo) e um alerta esperado ("deve disparar"). Parâmetros são opcionais na
disparada — o padrão basta para demonstração.

## Modelo de execução

- **Fila com um ataque por vez**: sinais limpos para leitura dos alertas;
  próximos ataques entram em fila visível.
- **Fases**: `agendado → preparando → executando → verificando →
  concluído` (ou `interrompido`/`falhou`).
- **Interrupção**: botão aborta o ataque atual e limpa efeitos reversíveis
  (restaura modo do web-demo, reinicia serviço parado, restaura arquivo
  adulterado byte a byte).
- **Efeitos reversíveis**: ataque 7 copia os bytes originais antes de
  adulterar e restaura no final (hash volta a bater com a referência
  aprovada, sem necessidade de `approve_integrity.py`); ataque 8 executa
  `docker compose start` no serviço parado. Nenhum ataque toca em volumes
  de dados do laboratório.
- **Tempos honestos**: cada alerta tem `for:` de 10–30 s; os runners
  mantêm o efeito ou aguardam o tempo necessário antes da verificação, e a
  verificação do motor tenta até 6 vezes (5 s entre tentativas). Ataques
  cujo alerta só existe enquanto o efeito está ativo (5, 6, 8) aguardam
  até ver o alerta `firing` no Prometheus antes de encerrar.
- **Reuso da plataforma**: ataques 5 e 6 usam o job de carga limitada
  `POST /api/lab/traffic` (autenticação + `X-Lab-Token` do `.env`), em vez
  de reimplementar geração de carga.

## Visualização (três camadas)

1. **Cartão do ataque**: fases com cores, barra de progresso, contadores
   (tentativas, respostas 401, mensagens enviadas — conforme o ataque) e
   taxa em tempo real (tentativas/s).
2. **Log de eventos ao vivo** via SSE: cada evento tem
   `timestamp, fase, mensagem`. Em marés grandes, tentativas são
   amostradas em lotes (não um evento por requisição).
3. **Verificação final**: consulta `GET /api/v1/query` do Prometheus pelo
   alerta esperado; resultado exibido como "✅ alerta disparou" /
   "⚠️ não disparou (verificar)", com link para o dashboard `:8000`.

## API

- `GET /api/attacks` — catálogo com parâmetros e alerta alvo de cada ataque.
- `GET /api/queue` — fila + ataque atual com progresso.
- `POST /api/attacks/{id}/start` — dispara ataque; parâmetros opcionais no
  corpo JSON; rejeita se já há ataque em execução (mas permite enfileirar).
- `POST /api/queue/{entry_id}/cancel` — remove da fila; se for o ataque em
  execução, atua como interrupção.
- `GET /api/events` — **SSE** com eventos de progresso, log e verificação.
- `GET /health` — verificação de vida do próprio painel.

## Segurança e limites

- Bind em `127.0.0.1` apenas; o servidor recusa interfaces externas.
- Sem autenticação: ferramenta de laboratório não exposta (decisão de
  hospedagem aprovada).
- Sem métricas sintéticas: o painel nunca escreve no Prometheus; dados
  ausentes na verificação aparecem como "não disparou (verificar)", nunca
  como sucesso inventado.
- Ataque 8 usa a CLI do Docker via subprocesso (`docker compose stop/start`
  com `cwd` no projeto, padrão já usado pelos scripts do host), restrito a
  `dns`, `smtp`, `web-demo` e `postgres` (nunca `api` ou `prometheus`,
  para não derrubar a própria verificação).

## Testes (TDD)

- **Motor**: fila um-por-vez, sequência de fases, interrupção com limpeza
  de efeitos reversíveis — com alvos falsos (servidores de teste locais)
  para não depender do Docker.
- **API**: catálogo, disparo, fila, cancelamento, SSE emite eventos, bind
  recusa interface externa.
- **Página estática**: smoke leve (estrutura e arquivos servidos), sem
  build; verificação visual fica para a apresentação.

## Critérios de aceite

- Cada um dos 8 ataques disparado pelo painel gera o alerta esperado no
  Prometheus (verificado pela ferramenta com "✅").
- Painel de ataques e dashboard de monitoramento permanecem independentes
  (portas e processos separados; nenhum acoplamento de código).
- Testes backend passam; `promtool check config` e `amtool check-config`
  válidos (nada em `alerts.yml` muda; conferência de rotina).
- A interrupção a meio do ataque restaura o laboratório ao estado anterior
  (modo do web-demo, serviço parado reiniciado).

## Fora do escopo

- Frontend realista do web-demo (sub-projeto 2, próxima especificação).
- Vários ataques simultâneos e modo apresentação roteirizado (decidido:
  um por vez, com fila).
- Autenticação no painel de ataques (acesso localhost, ferramenta de
  laboratório).
