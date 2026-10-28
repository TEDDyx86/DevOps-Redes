# Autenticação e eventos de acesso

Continuação autorizada pelo usuário após a proposta de login e detecção de acessos repetidos. Escopo desta etapa: proteger o dashboard/API, registrar autenticação e demonstrar alerta; os demais monitores de segurança ficam na etapa seguinte.

## Decisões

Uma conta `admin`, provisionada por `scripts/configure.py`. Senha aleatória preservada no `.env` ignorado; apenas hash scrypt é montado na API. Scrypt da biblioteca padrão evita dependências na configuração inicial: N=131072, r=8, p=1, salt aleatório de 16 bytes, derivação de 32 bytes. Duas verificações simultâneas no máximo. Alternativas: provedor externo acrescentaria dependência de conta/rede; JWT não oferece benefício para este servidor único e complicaria revogação.

SQLite próprio no volume de incidentes armazena eventos e sessões, independente dos serviços monitorados. Cookie aleatório de 256 bits, HttpOnly, SameSite=Strict, duração absoluta de 8 h; só SHA-256 do token no banco. CSRF por sessão e validação de origem em mutações. Secure configurável para HTTPS; laboratório permanece HTTP em loopback. Sem tokens em localStorage. Logout revoga no servidor; mudar credenciais invalida sessões antigas.

Rotas de dados e controles `/api/*`, docs e OpenAPI exigem sessão. `/health`, `/metrics` e assets permanecem acessíveis para operação. Webhook continua com seu Bearer próprio e não exige sessão/CSRF. Sem configuração de credenciais, login retorna 503 e dados ficam protegidos. Não confiar em X-Forwarded-For: IP vem da conexão efetiva.

Cinco falhas em 60 s por IP ou dez por conta bloqueiam novas tentativas por tempo restante da janela (429 + Retry-After). Reservar tentativa atomicamente antes do hash para cobrir concorrência. Tentativas bloqueadas não prolongam a janela de falhas. Mensagem de credencial inválida não revela existência da conta. Sessões já autenticadas continuam funcionando durante bloqueio de login.

Eventos: sucesso, credencial inválida, bloqueio e logout; sem senha, hash, cookie ou CSRF. Retenção 7 dias e limite 10.000 eventos, interface últimos 100; orçamento do limitador é separado do histórico e contadores agregados persistem independentemente da limpeza. Bloqueios recentes são agregados por segundo, sem perda por truncamento do histórico. Prometheus recebe contadores por resultado e maior quantidade de falhas recentes por IP/conta, sem rótulos de identidade. Regra `AutenticacaoSuspeita` por 10 s confirma limite excedido; incidente e e-mail locais usam a infraestrutura existente.

## Interface e validação

Tela de entrada conserva DM Sans/IBM Plex Mono, grafite e violeta da plataforma. Formulário com usuário/senha, estado de envio, erro genérico e instrução de onde encontrar a credencial local. Gate monta o dashboard apenas com sessão válida, retorna ao login em 401, permite sair e recuperar sessão após recarga. Aba Segurança apresenta janela/limites, eventos e incidentes de autenticação; não diz que os demais detectores já existem.

Testar proteção dos endpoints, hash e configuração idempotente, login incorreto/correto, expiração/revogação/rotação, CSRF/origem, persistência, concorrência, limites por conta/IP, recuperação temporal e métricas sem segredos. Demonstração real: cinco falhas, 429, incidente/e-mail, aguardar janela, resolução e login; monitoramento dos quatro protocolos continua. Adaptar scripts de demonstração para sessão autenticada.

Referências: [OWASP senhas](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), [sessões](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).
