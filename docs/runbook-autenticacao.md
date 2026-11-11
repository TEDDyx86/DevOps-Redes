# Acesso ao painel e tentativas repetidas

## Entrar

Execute `python scripts/configure.py` antes de atualizar a stack com `docker compose up -d --build --wait`. Abra http://localhost:8000. O arquivo `.env` contém `ADMIN_USERNAME` (inicialmente `admin`) e `ADMIN_PASSWORD`. Copie a senha somente para a tela de entrada do seu laboratório; ela não aparece na documentação nem nos logs dos testes.

A configuração preserva os segredos existentes. A API recebe apenas o hash em `.runtime/secrets/admin-password-hash`, montado como arquivo somente leitura. Esse arquivo e `.env` são ignorados pelo Git. O Alertmanager recebe apenas seu segredo de webhook.

Sessões duram até 8 horas, com expiração absoluta. O botão de sair revoga a sessão no servidor; recarregar o navegador ou reiniciar a API preserva uma sessão ainda válida. A aplicação exige nova entrada após expiração. Usuários de versões anteriores precisam recarregar a página para carregar a tela de login.

## Proteções implementadas

- Hash scrypt: N=131072, r=8, p=1, salt aleatório de 16 bytes e derivação de 32 bytes. Até duas verificações simultâneas. Parâmetros baseados na [orientação OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
- Cookie aleatório de 256 bits, HttpOnly e SameSite=Strict. O banco armazena apenas SHA-256 do identificador de sessão. Token CSRF fica apenas na memória do frontend.
- CSRF de sessão e verificação de origem em operações de escrita. Sessão e token do laboratório têm funções distintas; controles de falha continuam exigindo `LAB_TOKEN`.
- Dados `/api/*`, eventos, controles, `/docs`, `/redoc` e OpenAPI exigem autenticação. Assets e `/health` são públicos. `/metrics` permanece acessível ao Prometheus; o webhook mantém Bearer próprio e não depende do login do usuário.
- Sem credencial configurada, login retorna 503 e os dados permanecem inacessíveis. Não existe opção de desligar autenticação em produção.
- Proxy headers desabilitados no comando Uvicorn da API. `X-Forwarded-For` não é fonte de identidade. No Docker Desktop, vários clientes locais podem aparecer com o mesmo IP de gateway.

O laboratório usa HTTP em loopback, portanto o cookie não exige TLS. Para uma implantação HTTPS futura, `AUTH_COOKIE_SECURE=true` é repassado pelo Compose. Isso, isoladamente, não publica HTTPS nem torna esta stack pronta para internet; infraestrutura de laboratório como Prometheus e caixas Mailpit permanece local e sem login próprio.

## Limites e eventos

Cinco falhas em 60 segundos por IP ou dez por usuário bloqueiam **novos logins**. As primeiras tentativas inválidas recebem 401; após atingir o limite, a próxima recebe 429 com `Retry-After`. O bloqueio também vale para uma senha correta enquanto a janela não expirar. Tentativas bloqueadas não prolongam a janela. Sessões já autenticadas continuam funcionando.

O orçamento de tentativas é reservado atomicamente antes da verificação de senha, em SQLite independente dos serviços monitorados. O histórico conserva até 10.000 eventos por até 7 dias, exibindo os últimos 100. A limpeza do histórico não apaga o orçamento recente, nem reduz os contadores acumulados. A contagem de bloqueios na janela usa agregação por segundo; falhas por IP/usuário usam horários precisos das tentativas.

Eventos registram horário, usuário informado, IP da conexão e resultado: entrada autorizada, credencial inválida, bloqueio ou saída. Nunca incluem senha, hash, cookie ou CSRF. Prometheus recebe contadores por resultado e o maior número de falhas recentes por IP/conta, sem rótulos com identidade.

A seção **Acesso ao painel** da aba [Segurança](http://localhost:8000/#security) acompanha autenticação da plataforma. Ela não representa detecção de força bruta em PostgreSQL, DNS ou SMTP. A mesma aba apresenta agora volume de tráfego dos quatro serviços; hashes de configuração e vulnerabilidades têm monitores próprios na mesma aba.

## Autenticação do serviço monitorado

O serviço HTTP de demonstração também tem superfície de autenticação: `POST /mode` exige `X-Lab-Token`. Tentativas com token inválido são contadas por `demo_auth_attempts_total{path="/mode",result="failed"}` em `/metrics` do próprio serviço, coletado pelo job `web-demo` do Prometheus. O alerta `AutenticacaoServicoSuspeita` (atenção) dispara com cinco ou mais falhas em um minuto, mantidas por 30 segundos, e envia e-mail à caixa local.

Acessos normais nunca contam como falha: o painel muda o modo pela API, que envia o token no servidor. Demonstração direta do contador (o `Invoke-WebRequest` do Windows PowerShell 5.1 não tem `-SkipHttpErrorCheck` e o `curl.exe` corrompe o JSON com aspas; o script usa a biblioteca padrão):

```powershell
.\.venv\Scripts\python.exe scripts/demo_auth_failures.py
```

Cada tentativa rejeitada incrementa o contador; o alerta confirma após a janela. Limitações: DNS e SMTP de laboratório não têm autenticação própria (CoreDNS sem AUTH; o SMTP aceita por endereço de destino), e o PostgreSQL autentica em nível de conexão — falhas de credencial SQL aparecem como sonda indisponível e não como evento de força bruta. Esse é o mesmo isolamento de rótulos do restante da plataforma: contadores sem identidade de origem.

## Demonstrar alerta e recuperação

```powershell
.\.venv\Scripts\python.exe scripts/verify_auth.py
```

O roteiro valida acesso anônimo negado, login, CSRF/origem, persistência após reinício da API, cinco falhas, bloqueio e manutenção da sessão anterior. `AutenticacaoSuspeita` confirma o limite por 10 segundos observados pelo Prometheus e envia incidente/e-mail à caixa http://localhost:8025.

Após expirar a janela de falhas, o alerta resolve e chega um e-mail de recuperação. O roteiro confirma logout com revogação, nova entrada e funcionamento dos quatro protocolos. O relatório sem segredos fica em `tmp/auth-e2e-result.json`. Não há limpeza manual de falhas nem botão que desligue o limitador. Se repetir imediatamente após uma execução interrompida, aguarde 60 segundos desde a última falha para iniciar a demonstração novamente.

Os outros roteiros `verify_lab.py`, `verify_postgres.py`, `verify_dns.py` e `verify_smtp.py` agora autenticam por `scripts/lab_session.py`; não imprimem ou salvam tokens.

## Alterar a senha local

Edite `ADMIN_PASSWORD` no arquivo `.env`, execute `python scripts/configure.py` e reinicie a API (`docker compose restart api`). Uma mudança real de usuário/hash invalida sessões anteriores. A configuração repetida sem mudança preserva hash e sessões. O usuário configurado deve usar de 1 a 64 caracteres entre letras ASCII, números, ponto, sublinhado, arroba e hífen. A senha de entrada aceita até 256 caracteres.

Não há cadastro, recuperação por e-mail, MFA, papéis múltiplos ou gerenciamento remoto de credenciais nesta etapa.
