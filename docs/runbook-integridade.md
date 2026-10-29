# Integridade dos arquivos de configuração

Na aba **Segurança**, o monitor compara o SHA-256 dos bytes em disco com uma referência aprovada. Consulta os oito arquivos abaixo a cada 5 s; amostras com mais de 20 s ficam desconhecidas. Não compara conteúdo textual, não modifica configurações e não identifica quem fez uma alteração no host.

| Arquivo relativo a `infra/` | Uso real |
|---|---|
| `http.json` | Mensagem e atrasos do serviço HTTP, carregados na inicialização |
| `postgres/postgresql.conf` | Configuração principal do PostgreSQL dedicado |
| `dns/Corefile` | Configuração do CoreDNS |
| `dns/db.aularedes.test` | Zona DNS local |
| `smtp.json` | Limite de mensagem e capacidade da fila SMTP, carregados na inicialização |
| `prometheus.yml` | Coleta e avaliação de métricas |
| `alerts.yml` | Regras de alerta |
| `alertmanager.yml` | Roteamento e canal de notificações |

Os diretórios de configuração são montados somente leitura nos containers. Uma substituição atômica pelo editor continua visível pelo diretório montado. Segredos permanecem em `.env` e `.runtime/secrets`, fora da lista e do diretório observado. A credencial de webhook do Alertmanager é montada separadamente em `/run/aularedes/webhook-token`.

## Primeira referência

1. Confira os arquivos no repositório e confirme que são os valores esperados para o laboratório.
2. Entre no painel e abra **Segurança → Revisar e aprovar uma referência**.
3. Escolha **Todas as referências iniciais pendentes** e **Preparar revisão dos hashes**. Confira os SHA-256 completos. No PowerShell, por exemplo: `Get-FileHash -Algorithm SHA256 .\infra\http.json`.
4. Informe `LAB_TOKEN` do `.env` no campo de aprovação e clique em **Aprovar estes hashes**.

Nenhum primeiro hash é aceito automaticamente pelo monitor. A revisão captura os hashes; se um arquivo mudar, a interface exige nova revisão e o servidor rejeita o hash antigo com 409. O servidor relê todos os arquivos antes de persistir um lote, sem aprovar parcialmente um lote obsoleto. Sessão, CSRF e token de laboratório são obrigatórios. A aprovação registra usuário, horário e hash, sem armazenar o conteúdo do arquivo.

Para uma mudança intencional posterior, confira o conteúdo e selecione **somente o arquivo correspondente**. Aprovar aceita seus bytes atuais como nova referência e encerra a condição de alteração. Não use essa ação apenas para silenciar um aviso sem revisar a mudança.

## Estados e alertas

| Estado | Significado / ação |
|---|---|
| Íntegro | Bytes iguais à referência aprovada |
| Referência pendente | Legível, sem referência; aviso após 2 min |
| Alterado | SHA-256 diferente; alerta após 15 s |
| Ausente | Arquivo requerido não encontrado; alerta após 15 s, mesmo sem referência |
| Leitura indisponível | Permissão, link, tipo especial, tamanho acima de 1 MiB ou alteração durante leitura; aviso após 30 s |
| Sem dados atuais | Sem primeira amostra ou coleta vencida; verificação indisponível após 30 s |

Os tempos começam na observação do Prometheus, com avaliação e coleta a cada 5 s. O Alertmanager envia os alertas para a [caixa local](http://localhost:8025) e os incidentes para a API. Restaurar exatamente os bytes originais resolve a condição sem nova aprovação. Alterações de espaços, comentários e finais de linha também mudam o hash.

As métricas `security_config_*` usam somente IDs fixos e serviços como labels; hashes e conteúdo não entram nas séries. Uma falha de armazenamento de integridade deixa seus checks indisponíveis e é repetida, sem interromper as métricas dos protocolos nem o login. O histórico retorna no máximo 100 eventos, tem teto de 10.000 registros e poda periódica de 7 dias. Referências e última observação persistem em `integrity.sqlite`, no volume `incidents`, separado do PostgreSQL monitorado; não são redefinidas ao reiniciar.

## Demonstração reproduzível

Com a stack iniciada e os arquivos conhecidos conferidos:

```powershell
.\.venv\Scripts\python.exe scripts/verify_integrity.py
```

O roteiro autentica, compara os hashes do container com os arquivos locais e aprova **somente referências iniciais ausentes**. Interrompe se alguma referência existente divergir dos bytes locais. Esse bootstrap explícito pertence ao roteiro de demonstração; não é aprendizado automático do monitor.

Acrescenta espaços aos JSON de HTTP/SMTP e comentários válidos ao PostgreSQL/zona DNS. Espera quatro estados alterados, quatro incidentes e quatro e-mails; restaura os bytes exatos e confirma quatro resoluções e e-mails. Reinicia a API e verifica persistência e ausência de duplicação. O `finally` restaura somente arquivos que ainda correspondam ao payload de teste; preserva e informa uma alteração concorrente. Não edite esses quatro arquivos enquanto o roteiro estiver executando. O resultado sem credenciais fica em `tmp/integrity-e2e-result.json`.

O teste demonstra detecção em disco; os comentários/espaços não exigem reiniciar os serviços. Para aplicar mudanças funcionais, siga o procedimento de cada serviço. HTTP e SMTP leem JSON na inicialização; no PostgreSQL alguns parâmetros exigem restart. Prometheus e Alertmanager exigem recarga ou reinicialização. Nunca confunda referência aprovada com confirmação de que todos os processos carregaram a configuração.

## Limites

A lista é fixa: não monitora `pg_hba.conf`, segredos, toda a configuração do host ou arquivos externos. No Linux, descritores relativos e `O_NOFOLLOW` impedem seguir links nos componentes; arquivos especiais são recusados antes da leitura. No Windows há verificação de links/junções e do caminho resolvido, sem a mesma garantia contra troca concorrente de componentes. O ambiente de demonstração usa containers Linux.

Não há assinatura externa, autoria da edição ou proteção contra um administrador que comprometa o host, a API, as regras ou o volume da referência. Interrupções muito breves entre duas amostras podem não ser observadas. O alerta depende de Prometheus/Alertmanager e do canal de e-mail operacional.

Referências: [localização dos arquivos no PostgreSQL 17](https://www.postgresql.org/docs/17/runtime-config-file-locations.html) e [descritores relativos na biblioteca os do Python](https://docs.python.org/3/library/os.html).
