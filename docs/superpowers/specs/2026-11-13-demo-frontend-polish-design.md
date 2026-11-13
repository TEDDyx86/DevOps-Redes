# Especificação — Refinamento visual do web-demo

Data: 2026-11-13 · Status: aguardando revisão do usuário
Escopo: `demo-frontend` — landing pública e painel do serviço de demonstração (`:8001`).

## Objetivo

Reduzir ruído visual e melhorar a leitura da landing e do painel, preservando a identidade pixel/retro e os comportamentos já existentes. A interface deve distinguir claramente dados reais, estado do serviço e elementos meramente decorativos.

## Direção visual aprovada

- Manter a paleta escura e acentos ciano/magenta/âmbar, mas reduzir brilho, sombras, bordas duplas e ornamentos.
- Remover o overlay de scanlines aplicado globalmente, que interfere na leitura e cria o efeito de grade sobre os cards.
- Evitar grades decorativas sobre superfícies de conteúdo; reservar qualquer textura sutil para o hero, se não prejudicar contraste.
- Cards com fundo uniforme, contorno discreto, espaçamento consistente e cor de destaque usada principalmente para estado e ação.

## Landing pública

- Preservar a navegação e o hero com CTA claro para `/login`.
- Substituir o excesso de seções interativas por uma apresentação curta do web-demo e de capacidades verificáveis.
- Retirar da composição principal pop-ups fictícios, carrossel de capacidades redundante, HUD de cockpit e desktop simulado.
- Não remover nem alterar endpoints ou contratos do backend. Não apresentar afirmações como operação ou telemetria em tempo real sem fonte verificável.

## Painel autenticado

- Hierarquia: estado/sinal e modo atuais; ação `/work` com latência e log da sessão; contadores reais de `/metrics` e distribuição por status.
- Remover o HUD decorativo e seus indicadores calculados localmente (barras CPU/rede/sessão, radar de serviços e throughput simulado), que podem ser confundidos com métricas observadas.
- Manter os controles de modo de falha e entrada `LAB_TOKEN`, mas apresentá-los como ferramenta secundária de laboratório, separada da leitura operacional.
- Manter saída da sessão e todos os estados de carregamento, erro e indisponibilidade.

## Contratos e limites

- Não alterar autenticação, endpoints (`/health`, `/mode`, `/work`, `/metrics`), cadência de polling ou comportamento do laboratório.
- Valores ausentes continuam desconhecidos/aguardando dados; não convertê-los em zero nem em estados saudáveis.
- Não tocar no frontend principal da plataforma (`frontend/`, porta `:8000`) nem no backend.
- As alterações locais já existentes em `demo-frontend` são trabalho do usuário e devem ser preservadas; mudanças devem ser integradas aos arquivos atuais, não substituídas por versões antigas.

## Validação

- Testes do `demo-frontend` e build de produção.
- Verificação visual da landing, login e painel em larguras desktop e mobile.
- Confirmar que login, logout, consulta periódica, execução `/work`, dados `/metrics` e controles de modo continuam operacionais.
