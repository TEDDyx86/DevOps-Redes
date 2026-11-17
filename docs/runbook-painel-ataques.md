# Runbook — Painel de Ataques

Ferramenta local para demonstrar ataques controlados contra o laboratório e
observar os alertas correspondentes no painel de monitoramento. Acesso
exclusivamente em `127.0.0.1:8002`; nunca exposta na rede. Totalmente
separada do dashboard React (porta 8000) e do web-demo (porta 8011 no host;
porta 8001 dentro da rede Docker).

## Iniciar

1. Stack de pé (`scripts/start.ps1` ou `docker compose up -d --wait`).
2. Painel: `python -m scripts.attack_panel.server` (porta 8002).
3. Abrir `http://localhost:8002`. O lock de instância única está em
   `.runtime/attack-panel.lock` (erro `worker_already_running` significa que
   já há uma instância ativa).
4. Porta ocupada: `--port 8003` (a página usa caminhos relativos).

## Catálogo e alertas esperados

| Ataque | Efeito | Alerta esperado (`for:`) |
|---|---|---|
| Força bruta no serviço | 12× `POST /mode` com token inválido | `AutenticacaoServicoSuspeita` (30s) |
| Força bruta no painel | 8× login com senha errada | `AutenticacaoSuspeita` (10s) |
| Sobrecarga HTTP | Maré em `GET /work` a partir do host | `RecursoCPUElevada` ou `TrafegoAnormal` (30s) |
| Indisponibilidade | Modo offline do web-demo (`POST /mode` com `LAB_TOKEN` do `.env`) | `HTTPIndisponivel` (15s) |
| Flood DNS | Job de carga limitada da plataforma (`POST /api/lab/traffic`) | `TrafegoAnormal` (30s) |
| Flood SMTP | Job de carga limitada da plataforma (`POST /api/lab/traffic`) | `TrafegoAnormal` (30s) |
| Adulteração de config | Altera arquivo em `./infra` e restaura byte a byte | `ConfiguracaoAlterada` (15s) |
| Interrupção de serviço | `docker compose stop/start` no alvo (dns, smtp, web-demo, postgres) | `*Indisponivel` do alvo (15s) |

## Visualização

- **Cartões do catálogo** com parâmetros (intensidade, duração, alvo) e botão Iniciar.
- **Execução**: fases (`agendado → preparando → executando → verificando`),
  contadores em tempo real (tentativas, rejeitadas, requisições,
  segundos restantes) e fila com um ataque por vez.
- **Log de eventos ao vivo** via SSE (`/api/events`).
- **Resultado**: consulta `ALERTS{alertstate="firing"}` no Prometheus até
  6 vezes (5 s de intervalo); "✅ Alerta disparou", "⚠️ Não disparou
  (verificar)" ou "⚠️ Verificação indisponível" (Prometheus fora do ar).
  Botão "Interromper" aborta o ataque em execução ou remove da fila.

## Regras de segurança

- O painel só **lê** o Prometheus; nunca publica métricas sintéticas.
- Efeitos são reversíveis: modo normal restaurado, serviço reiniciado,
  arquivo restaurado byte a byte (hash volta a bater com a referência —
  `approve_integrity.py` não é necessário após restauração).
- Interrupção a meio do ataque dispara a limpeza no `finally` do runner.
- Falha de runner é reportada pelo tipo do erro (`RuntimeError` etc.), sem
  expor detalhes que possam conter segredos.
- Ataque 8 nunca aceita `api`, `prometheus` ou `alertmanager` como alvo.

## Verificação manual (roteiro de demonstração)

Para cada ataque: iniciar no painel → acompanhar fases/log → conferir o
resultado (✅/⚠️) → abrir o dashboard `:8000` e ver o incidente com o mesmo
nome → e-mail no Mailpit (`:8025`). Os floods exigem referências de tráfego
calibradas: aguardar status `normal` na tabela de tráfego do dashboard
antes de atacar (o detector precisa de baseline; sem ela fica em
`learning` e não dispara `TrafegoAnormal`).

## Solução de problemas

- `worker_already_running`: painel já aberto em outro terminal.
- Alerta não disparou (⚠️): conferir coletores ativos (`up{job="platform"}`),
  baseline de tráfego pronta, e se o efeito durou o `for:` do alerta.
- Verificação indisponível: Prometheus fora do ar no momento da checagem;
  rodar o ataque de novo com a stack completa.
- Correção do arquivo monitorado acidentalmente permanente: restaurar o
  conteúdo original do arquivo e rodar `scripts/approve_integrity.py`
  (somente se a restauração byte a byte não ocorreu).
