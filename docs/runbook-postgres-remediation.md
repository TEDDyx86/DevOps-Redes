# Atualização preventiva da imagem PostgreSQL

## Motivo e aplicabilidade

Em 30/10/2026, a análise da imagem oficial `postgres:17.11-alpine3.24` encontrou três avisos críticos associados à biblioteca padrão **Go 1.24.6** do binário `/usr/local/bin/gosu`. O servidor SQL é PostgreSQL 17.11; `gosu` é o utilitário que troca o usuário root por postgres durante a inicialização. O PID 1 do serviço em operação é o PostgreSQL, com UID/GID 70.

| Aviso | Função afetada segundo o mantenedor Go | Aplicabilidade observada |
|---|---|---|
| [GO-2026-4337 / CVE-2025-68121](https://pkg.go.dev/vuln/GO-2026-4337) | Retomada de sessão TLS com alterações nas autoridades certificadoras | O gosu não implementa cliente/servidor TLS; não foi demonstrado caminho explorável no laboratório |
| [GO-2026-6604 / CVE-2026-56857](https://pkg.go.dev/vuln/GO-2026-6604) | Operações de `os.Root` sobre junções no Windows | A imagem executa Linux; esse cenário específico não se aplica à plataforma |
| [GO-2026-6612 / CVE-2026-78663](https://pkg.go.dev/vuln/GO-2026-6612) | Controle de fluxo de servidor HTTP/2 | O gosu não oferece servidor HTTP/2; não foi demonstrado caminho explorável no laboratório |

A [política de segurança do gosu](https://github.com/tianon/gosu/blob/1.19/SECURITY.md) explica por que o projeto não recompila cada release para avisos de interfaces Go que não utiliza. A análise de versão do Grype não equivale à prova de alcance de uma função vulnerável. Não foi realizada exploração nem análise completa de alcançabilidade com govulncheck. A decisão local foi atualizar preventivamente o compilador, mantendo a detecção sem supressões e registrando essa distinção. Não se deve apresentar os três avisos como três falhas comprovadas do servidor SQL.

## Construção

O Compose constrói `aularedes-postgres:17.11-gosu1.19-go1.27.3` usando somente `infra/postgres-image/` como contexto. O Dockerfile mantém a mesma base PostgreSQL, seu entrypoint e configurações. Recompila o mesmo código gosu 1.19 e preserva suas dependências, verificadas por go.sum. Copia somente binário e licença para o estágio final, sem compilador, fonte ou credenciais.

- Base: `postgres:17.11-alpine3.24@sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b`.
- Compilador: `golang:1.27.3-alpine3.24@sha256:d200d2dd76b03a99b52651fd1325aff7dcd35422c35c01bac56571b0507f3deb`.
- Fonte: tag gosu 1.19, arquivo SHA-256 `cd9719b775dbfedae53923c9b0dc792b66d42c51e0b36652ed6f747fbadc0164`, conferido por `ADD --checksum`.
- `CGO_ENABLED=0`, `GOTOOLCHAIN=local`, módulos sem atualização implícita. Não é usado `-s`, para preservar a inspeção Go. A versão funcional continua `1.19`; o módulo principal é registrado como `(devel)` por ser uma compilação a partir do arquivo-fonte, enquanto as versões das dependências e do Go permanecem no binário.

Fontes: [Dockerfile oficial PostgreSQL analisado](https://github.com/docker-library/postgres/blob/2603e26e245e558218728ee14e0a42dcb020dc7f/17/alpine3.24/Dockerfile), [compilação original gosu 1.19](https://github.com/tianon/gosu/blob/1.19/Dockerfile), [versões Go](https://go.dev/dl/) e [política de versões PostgreSQL](https://www.postgresql.org/support/versioning/).

```powershell
docker compose build postgres
```

Na instalação inicial, `scripts/start.ps1` constrói esse serviço junto à plataforma. A compilação precisa de internet para obter as imagens, fonte e módulos públicos verificados. Reconstruções podem gerar outro image ID por metadados/proveniência; a comparação e a análise devem usar o ID real, mesmo com os mesmos pacotes.

## Procedimento de atualização com dados existentes

1. Registrar image ID e nome do volume montado em `/var/lib/postgresql/data`. Manter a imagem anterior disponível para reversão.
2. Construir e analisar o candidato isoladamente com o mesmo Worker/Syft/Grype. Gravar seus relatórios em pasta separada, sem alterar o inventário dos serviços. Conferir a ausência dos três avisos e um inventário real; não concluir pelo desaparecimento de um alerta.
3. Inicializar candidato temporário sem rede e sem volume do laboratório, com as configurações/scripts reais de bootstrap. Esperar o **postmaster final** ser PID 1 e estar pronto; o servidor temporário do initdb também aceita conexões, mas ainda não significa inicialização concluída. Conferir 1.000 linhas, extensão, papéis, UID/GID/HOME e encerramento normal.
4. Pausar a API para suspender a carga SQL. Criar `pg_dump -Fc -U lab_admin -d lab_network` e `pg_dumpall --globals-only -U lab_admin`, gravando stdout binário diretamente em `.runtime/backups/`. Registrar tamanho/SHA-256 e impressão digital SHA-256 de `COPY (SELECT * FROM lab_items ORDER BY id) TO STDOUT WITH CSV`. Retomar a API no finally. Os globais contêm hashes de senhas: não imprimir, publicar nem versionar seus conteúdos.
5. Restaurar em outro PostgreSQL temporário com o mesmo usuário administrativo `lab_admin`, sem os scripts de bootstrap do laboratório. No fluxo de restauração dos globais, omitir **somente** a linha exata `CREATE ROLE lab_admin;`, pois esse papel já foi criado pelo initdb. Exigir uma única ocorrência; preservar o backup original. Executar o restante com `psql -v ON_ERROR_STOP=1 -U lab_admin -d postgres`, para preservar também o grantor `lab_admin` dos `GRANTED BY` de PostgreSQL 17. Em seguida, executar `pg_restore --exit-on-error --create -U lab_admin -d postgres` com o dump. Conferir conteúdo e permissões. Não ignorar genericamente erros de criação ou de concessão.
6. Pausar novamente a API e registrar a impressão digital atual antes da troca. Aplicar a imagem **já analisada**, sem nova compilação:

   ```powershell
   docker compose up -d --no-deps --no-build --wait postgres
   ```

7. Com a carga ainda pausada, exigir volume original, image ID do candidato, PostgreSQL 17.11 e impressão digital idêntica. Retomar a API somente após todas as verificações passarem ou após reversão confirmada, também conferindo volume e conteúdo. O finally deve respeitar essa condição; se atualização e reversão falharem, manter a carga pausada para investigação. Não executar `down -v`, `volume rm` ou initdb sobre os dados existentes.
8. Esperar o worker descobrir a imagem em execução e concluir sua análise. Conferir o ID no painel/API, a validade e as contagens. Confirmar resolução do incidente crítico e e-mail local, sem tratar apenas a resolução como prova da atualização.
9. Executar, sequencialmente:

   ```powershell
   .\.venv\Scripts\python.exe scripts/verify_postgres.py
   .\.venv\Scripts\python.exe scripts/verify_vulnerabilities.py
   ```

Os backups e artefatos operacionais permanecem ignorados pelo Git. A evidência pública resumida está em `docs/evidencias/postgres-remediation.json`.

## Reversão

Se a verificação falhar, manter a carga pausada e reaplicar a imagem anterior no **mesmo volume**. Como não houve mudança da versão SQL nem migração de esquema, essa reversão não exige restauração do dump. Não restaurar um backup sobre o volume corrente durante uma reversão de imagem.

Criar `.runtime/postgres-rollback.yaml`:

```yaml
services:
  postgres:
    image: postgres:17.11-alpine3.24@sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b
```

```powershell
docker compose stop api
if ($LASTEXITCODE -ne 0) { throw 'Falha ao pausar a carga; interromper a reversão.' }
docker compose -f compose.yaml -f .runtime/postgres-rollback.yaml up -d --no-deps --no-build --wait postgres
if ($LASTEXITCODE -ne 0) { throw 'Reversão falhou; manter a API parada.' }
```

Após o comando terminar com sucesso, conferir a imagem anterior, o mesmo nome de volume registrado e a impressão digital idêntica dos dados. **Somente após essas verificações passarem**, retomar a carga:

```powershell
docker compose start api
```

Caso a reversão ou sua validação falhe, manter a API parada e investigar antes de permitir novas escritas. O override deve continuar sendo usado enquanto a reversão for necessária; um `compose up` sem ele voltará à imagem definida no Compose principal. A análise da imagem antiga voltará a apresentar seus achados.

## Resultado e limites

Resultados completos desta execução constam da evidência e de `docs/validacao.md`. A análise candidata catalogou os mesmos **50 pacotes**, passando de **3 críticos / 32 altos / 26 médios / 2 baixos / 1 não classificado** para **0 críticos / 0 altos / 4 médios / 1 baixo** com a mesma base de avisos. Os cinco restantes envolvem BusyBox e dependências do gosu; continuam publicados para triagem. Não houve supressão nem alteração de severidade. As imagens HTTP/SMTP e DNS não fazem parte desta atualização e conservam seus achados próprios.

A base e as fontes estão fixadas para reprodução; atualizar sua versão/digest no futuro exige repetir a validação. Zero crítico/alto reflete somente a imagem, catálogo e base utilizados naquela data; não é garantia de segurança integral. A análise visual desktop/mobile inicialmente pendente foi concluída na [etapa seguinte de reconciliação de incidentes](runbook-incidentes.md), com evidências em `docs/evidencias/incident-reconciliation.json`. A evidência JSON desta atualização PostgreSQL preserva o estado e as pendências observados no momento de sua execução.
