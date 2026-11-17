# Especificação — Experiência Workbyte para o dashboard principal

Data: 2026-11-13 · Status: aprovada para especificação; aguardando revisão do documento  
Contexto: levar a identidade visual validada na demo ao dashboard principal, sem reduzir suas funcionalidades.

## Objetivo

Em `http://localhost:8000`, oferecer o fluxo **landing pública → login → dashboard completo**, usando a direção visual Workbyte aprovada na comparação visual. Após o login, todas as áreas, dados, ações e controles do dashboard original continuam disponíveis e conectados às APIs existentes.

A demo isolada do serviço HTTP em `http://localhost:8011` permanece disponível, sem se tornar a fonte de autenticação ou de dados do dashboard principal.

## Decisões aprovadas

1. **Base de implementação:** reestilizar o frontend principal existente (`frontend/`) e sua integração atual com o backend. Não substituir o dashboard por `demo-frontend/` nem copiar para lá os recursos da plataforma.
2. **Fluxo em `:8000`:** landing pública; ação de entrada leva ao login da plataforma; sessão válida leva diretamente ao dashboard; logout volta ao login.
3. **Identidade visual:** direção A, “Workbench Workbyte”: superfícies escuras, acentos ciano/neon e linguagem visual da demo, com contraste e hierarquia suficientes para operação prolongada e leitura de tabelas e gráficos.
4. **Navegação:** menu lateral retrátil. Expandido, mostra ícones e rótulos; recolhido, mantém os ícones e o estado ativo, com nomes acessíveis por tooltip. A preferência de expansão pode ser persistida no navegador. Em telas estreitas, usar navegação temporária em drawer.
5. **Preservação funcional:** manter autenticação, autorização, endpoints, formatos de dados e fontes reais. Não usar métricas ou estados simulados na aplicação entregue.
6. **Separação de serviços:** `:8011` continua sendo a demo HTTP, com seu escopo e autenticação próprios; `:8000` continua sendo a plataforma principal.

## Experiência e áreas

### Landing pública

- Apresenta a plataforma AulaRedes/Workbyte e sua finalidade de observabilidade do laboratório.
- CTA principal direciona para o login existente.
- Não exibe dados operacionais privados antes da autenticação.
- Deve funcionar tanto em desktop quanto em telas estreitas.

### Login e sessão

- Preservar a verificação de sessão, login, logout, expiração, tratamento de erros, cookie, CSRF e rotas já implementados no `frontend/src/Auth.tsx` e `frontend/src/api.ts`.
- Não reutilizar o cookie nem o endpoint de autenticação da demo.
- Uma sessão já autenticada pode seguir direto ao dashboard, sem exigir nova entrada pela landing.
- O logout encerra a sessão da plataforma e retorna ao login.

### Dashboard autenticado

O shell visual atualizado envolve a implementação atual de `frontend/src/App.tsx` e mantém as áreas existentes:

1. Visão geral
2. HTTP
3. PostgreSQL
4. DNS
5. SMTP
6. Recursos
7. Segurança
8. Incidentes
9. Laboratório

As páginas e componentes atuais continuam responsáveis por carregar e apresentar dados reais, executar ações existentes e tratar estados de carregamento, indisponibilidade, dados desatualizados e erro. Mudanças de aparência não podem mudar a semântica nem o comportamento dessas funções.

## Arquitetura e fluxo de dados

- O backend principal, servido em `:8000`, continua entregando o frontend principal e as rotas `/api/*`.
- O frontend conserva o cliente autenticado existente, incluindo envio de credenciais same-origin e token CSRF em mutações.
- A landing é uma camada pública do frontend principal; não chama APIs privadas para fabricar uma prévia do dashboard.
- Depois da autenticação, o dashboard carrega dados pelas APIs atuais da plataforma. Prometheus, sondas e demais integrações existentes continuam sendo as fontes de dados.
- `demo-frontend/` e `web-demo` não passam a atuar como proxy, backend ou dependência de runtime do dashboard principal.
- Nenhuma alteração de esquema, API ou credencial faz parte deste escopo.

## Contrato visual e de interação

- Aplicar a identidade Workbyte sem reproduzir elementos puramente decorativos que prejudiquem a leitura ou a acessibilidade.
- Preservar contraste legível em cartões, gráficos, tabelas, badges, estados de alerta e texto secundário.
- O controle do menu deve ter rótulo acessível e indicar seu estado expandido/recolhido (`aria-expanded`).
- A navegação deve ser utilizável por teclado e exibir foco visível.
- No modo recolhido, os nomes dos itens não podem depender exclusivamente de hover: disponibilizar tooltip e nome acessível para leitores de tela.
- No drawer móvel, abrir e fechar por controles explícitos; a navegação não deve reduzir a área de conteúdo a uma coluna ilegível.
- A página ativa e indicadores reais (por exemplo, incidentes ativos) permanecem compreensíveis nos dois estados do menu.
- Preferência de expansão persistida localmente é uma conveniência de interface; não é dado de conta nem exige API.

## Estados e erros

- Landing e login devem oferecer estados de carregamento e erro sem expor informações da sessão.
- O fluxo deve continuar distinguindo falta de sessão (`401`) de falha de conectividade ou erro do backend.
- Dashboard conserva estados atuais de indisponibilidade, dados antigos/parciais e falhas por área; erro em uma área não deve apagar dados de outras áreas que carregaram corretamente.
- Uma sessão expirada durante o uso deve retornar ao login pelo mecanismo já existente.

## Fora de escopo

- Alterar ou aposentar o painel de ataques, a demo `:8011`, serviços Docker ou as integrações de observabilidade.
- Criar novas funcionalidades de monitoramento, endpoints, alertas ou dados.
- Reformular os contratos das APIs ou o mecanismo de autenticação.
- Substituir páginas atuais por dados ilustrativos ou por uma versão reduzida do painel.
- Fazer uma migração simultânea de framework, roteador ou backend.

## Critérios de aceitação

1. A rota principal em `:8000` mostra uma landing pública Workbyte com CTA para o login.
2. A ação do CTA abre o login da plataforma, e não o login independente da demo.
3. Credenciais válidas autenticam pela API existente e abrem o dashboard principal; sessão válida reconhecida ao carregar a aplicação abre diretamente o dashboard.
4. Logout e expiração continuam encerrando o acesso protegido conforme o fluxo atual.
5. O dashboard autenticado oferece as nove áreas listadas, sem remover dados, ações ou estados da versão original.
6. O menu pode ser expandido/recolhido, mantém a área ativa reconhecível e funciona por teclado; a preferência persiste entre recargas.
7. Em viewport estreito, o menu vira drawer e tabelas/gráficos continuam utilizáveis sem overflow horizontal da página inteira.
8. Nenhum indicador operacional do dashboard é preenchido com valores de demonstração; os dados vêm das APIs existentes.
9. A demo em `:8011` continua isolada e funcionando independentemente do fluxo principal.
10. Build e testes dos frontends/backend passam; testes de integração cobrem entrada pública, sessão existente, login, acesso autenticado, logout e navegação para as nove áreas.

## Verificação planejada

- Testes do frontend para landing, estado de autenticação e alternância/persistência do menu.
- Testes de integração do fluxo real de sessão e login usando os endpoints existentes.
- Regressão das páginas e ações atuais do dashboard, incluindo testes já existentes de recursos e incidentes.
- Build de produção do frontend principal e execução da suíte de testes relevante.
- Verificação visual em desktop e viewport móvel, com menu expandido, recolhido e drawer aberto.

## Aprovações e histórico

- Fluxo “Landing → login → dashboard”: aprovado pelo usuário em 2026-11-13.
- Direção visual A — Workbench Workbyte: escolhida pelo usuário em 2026-11-13.
- Menu lateral retrátil, com estado expandido/recolhido e adaptação móvel: validado visualmente em 2026-11-13.
- Arquitetura de reestilizar o frontend principal preservando APIs, sessão e funcionalidades: aprovada pelo usuário em 2026-11-13.
