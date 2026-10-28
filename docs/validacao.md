# Validação da etapa HTTP

Este documento separa verificações automatizadas, demonstração integrada e requisitos ainda em construção.

## Testes automatizados

`backend/tests/test_platform.py` verifica:

- Classificação normal/lenta/falha e ausência ou idade excessiva das sondas.
- Métricas ausentes, NaN e infinito não convertidas em valores saudáveis.
- Persistência, deduplicação e resolução idempotente de incidentes.
- Webhook autenticado e validação do payload.
- Token e origem para alterações do laboratório.
- Prometheus indisponível, janela inválida e séries vazias.
- Serviço HTTP retornando 503 enquanto suas métricas continuam acessíveis.

`frontend/src/api.test.ts` diferencia zero medido de ausência de dados. Build TypeScript verifica contratos da interface. `promtool` e `amtool` validam configurações.

## Evidências da execução

Execução em 28/10/2026, Docker Desktop com containers Linux:

- **10 testes de API passaram**, incluindo regressão de tráfego composto apenas por respostas 503.
- **2 testes de frontend passaram**, incluindo interrupção real após 8 s de uma requisição sem resposta.
- Build TypeScript/Vite concluído; fontes incluídas localmente para não depender de Google Fonts durante a demonstração.
- `promtool`: configuração e três regras válidas.
- `amtool`: configuração válida, com receptor de e-mail e webhook autenticado.
- Cinco serviços em execução: API/dashboard, HTTP demo, Prometheus, Alertmanager e Mailpit.
- **12 verificações de integração passaram** com `scripts/verify_lab.py`: estado normal, erro 0% com tráfego saudável, atenção observada, incidente de lentidão persistido, e-mail recebido, indisponibilidade observada, incidente crítico, métricas durante a falha, recuperação operacional, resolução dos dois incidentes e e-mail de recuperação.
- Durante a primeira demonstração, o Mailpit recebeu quatro mensagens locais: alerta e recuperação para lentidão e indisponibilidade. O script produz `tmp/e2e-result.json`, sem tokens. Esse arquivo é evidência temporária e não é versionado.
- Revisão independente identificou e motivou correções no cálculo de erros, atualização de séries sem respostas 200 e expiração dos dados da interface. Suíte de regressão executada após as correções.
- Navegação real no navegador: visão geral, detalhe HTTP, laboratório e incidentes; token inválido rejeitado com mensagem; seletor de período alterado para uma hora.
- Layout verificado em 1440×1000 e 390×844. Em celular, largura de rolagem do documento igual à largura útil (375 px), sem transbordamento horizontal da página; a tabela mantém rolagem interna.
- Prometheus interrompido por 25 s e reiniciado automaticamente: interface exibiu erro explícito, estado Sem dados e métricas ausentes em vez de conservar o estado operacional.

Evidências visuais em `docs/evidencias/`: `dashboard-desktop.jpg`, `dashboard-mobile.jpg` e `coleta-indisponivel.jpg`. São capturas do laboratório local, sem credenciais.

O script integrado altera somente o serviço de demonstração e restaura o modo normal no bloco `finally`. Não gera testes de carga nem envia mensagens a destinatários externos.

Há um aviso de depreciação da biblioteca Starlette sobre a integração de testes com httpx. Os testes passam; o aviso pertence à dependência e não indica falha funcional da aplicação.

## Requisitos ainda em construção

Banco, DNS, SMTP monitorado, CPU/memória/I/O, detecção de anomalias e força bruta, monitoramento de arquivos, vulnerabilidades conhecidas, autenticação da interface e relatório ABNT. A etapa atual entrega a base HTTP e a infraestrutura de alertas.
