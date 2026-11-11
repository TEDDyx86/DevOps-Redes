# Vulnerabilidades conhecidas por serviço

A aba **Segurança → Vulnerabilidades conhecidas** acompanha as imagens usadas por HTTP, PostgreSQL, DNS e SMTP. Syft cataloga os pacotes; Grype compara esse inventário com a base pública de avisos da Anchore. Cada achado associa advisory/CVE, pacote, tipo e versão instalada. Isso exige triagem de aplicabilidade e não comprova exploração.

HTTP e SMTP usam a mesma imagem e compartilham o resultado completo dessa imagem. A contagem representa combinações únicas de aviso + pacote + tipo + versão, não o número de ataques nem o total de CVEs únicos. A maior severidade é preservada quando há duplicatas; versões corrigidas são unidas. A tabela permite filtrar serviço/severidade e navegar em páginas de 50 itens.

## Iniciar

No Windows, `scripts/start.ps1` prepara o ambiente, inicia a stack e solicita o monitor em segundo plano. Para execução por comandos:

```powershell
python scripts/configure.py
docker compose up -d --build --wait
python scripts/scan_vulnerabilities.py --background
```

O worker exige Python 3.13+ com a biblioteca padrão e Docker Desktop funcionando. Não requer instalação local de Grype/Syft. As imagens oficiais têm versão e digest fixados no script. A primeira execução baixa as ferramentas e a base; pode demorar alguns minutos e precisa de internet para acessar o registry e a base pública.

Para acompanhar em um terminal, use `python scripts/scan_vulnerabilities.py --watch`. Para uma rodada única, execute sem argumentos. Uma trava do sistema operacional permite um worker por checkout; uma segunda execução informa que já existe monitor e não inicia análise concorrente.

```powershell
python scripts/scan_vulnerabilities.py --stop
```

O pedido de encerramento é observado a cada 30 s. O worker termina/recolhe seus comandos e containers antes de liberar a trava, inclusive exportação de imagem. Para forçar uma nova rodada, solicite parada, aguarde o encerramento e execute a rodada única; depois retome `--background`. Antes de encerrar definitivamente o laboratório, solicite `--stop` e então use `docker compose down`. O processo oculto não é um serviço do Windows e deve ser iniciado novamente após reiniciar o computador.

Logs em `.runtime/vulnerabilities/worker.log`; inventário e relatórios normalizados no mesmo diretório, ignorado pelo Git. Não apague a base/reference de integridade para resolver um erro de scanner.

## Coleta, validade e falhas

O worker consulta o inventário das imagens a cada 30 s, agenda novas imagens e repete scans a cada 6 h. O scanner roda em thread separada, permitindo manter o inventário atualizado durante a análise. Em falha, mantém o relatório anterior e tenta novamente após 5 min. Falhas e tentativas interrompidas são preservadas ao reiniciar o worker; não são convertidas em análise bem-sucedida.

A API lê a fonte a cada 5 s. Uma análise só é atual quando todas as condições se verificam:

- Inventário válido, obtido há no máximo 120 s, e leitura da API com no máximo 20 s.
- Image ID do relatório igual ao observado no container; a exportação também tem o digest interno da configuração conferido com Syft/Grype.
- Scan bem-sucedido há no máximo 24 h e base construída há no máximo 120 h, com datas finitas e tolerância de futuro de até 5 s.
- Pacotes efetivamente catalogados, achados válidos e contagens consistentes.
- Nenhuma tentativa falha posterior para a mesma imagem.

Durante reanálise, o relatório anterior continua utilizável enquanto válido. Sem essas condições, o painel mostra **Sem análise atual**, oculta contagens atuais e informa o motivo. Metadados do relatório anterior podem continuar visíveis como evidência histórica. Zero só significa que uma análise válida não encontrou avisos conhecidos naquela imagem/base; não garante ausência de vulnerabilidades.

Uma troca de imagem exige nova análise. Estar sem análise atual não muda a classificação de disponibilidade do protocolo; HTTP/SQL/DNS/SMTP continuam tendo suas próprias sondas. Uma falha em arquivo de relatório não interrompe login, outros monitores ou métricas.

## Alertas e interpretação de resolução

| Regra | Condição persistente | Nível |
|---|---|---|
| `VulnerabilidadeCritica` | Ao menos um achado crítico por 30 s | Crítico |
| `VulnerabilidadeAlta` | Achado alto e nenhum crítico por 30 s | Atenção |
| `VulnerabilidadeAnaliseIndisponivel` | Sem análise válida por 2 min | Atenção |

Os intervalos começam quando o Prometheus observa a condição, com coleta/avaliação a cada 5 s. Incidentes e e-mails seguem o Alertmanager e o [Mailpit de alertas](http://localhost:8025). Médias, baixas, desprezíveis e não classificadas permanecem disponíveis para revisão, sem acionar os dois limiares de achados altos/críticos.

**Resolução de alerta não equivale automaticamente a vulnerabilidade corrigida.** Quando a análise fica indisponível, a métrica de achados atuais é omitida, o alerta de achado deixa de estar confirmado e o aviso de análise indisponível assume após sua janela. As próprias descrições dos alertas avisam esse limite. Confirme uma nova análise válida da imagem correta antes de declarar correção. Ao recuperar a análise, achados ainda presentes voltam a gerar o alerta correspondente.

## Triagem e correção

1. Selecione o serviço e a severidade; confira imagem, data do scan, data da base e pacote/versão instalada.
2. Abra a fonte HTTPS do aviso e confira a aplicabilidade ao sistema, distribuição e uso real. Achados sem severidade também exigem revisão.
3. Confira versões corrigidas e compatibilidade com os serviços. Não considere a ausência de versão corrigida uma liberação de risco.
4. Planeje atualização da imagem base/dependência, reconstrua o serviço e espere a análise da nova imagem.
5. Registre a evidência de correção somente com relatório atual e regressão dos protocolos. Revise referências de configuração apenas quando o arquivo tiver mudado de forma intencional.

Esta etapa não atualiza pacotes/imagens automaticamente nem instala versões vulneráveis para criar uma demonstração. Os achados atuais são reais e podem permanecer abertos ao final dos testes.

Em 30/10, foi aplicada uma [atualização preventiva do gosu na imagem PostgreSQL](runbook-postgres-remediation.md), com backup restaurado, 50 pacotes catalogados e redução de 3 críticos/32 altos para zero críticos/altos. Os avisos eram associados à versão Go do utilitário, sem prova de exploração SQL. Os cinco achados restantes e os avisos das outras imagens continuam publicados. Em seguida, três ciclos históricos de 29/10 que ficaram abertos durante uma interrupção foram [reconciliados por resoluções posteriores persistidas](runbook-incidentes.md), preservando o término original como desconhecido. A conferência visual de Incidentes/Segurança foi concluída em desktop e celular, com filtros, paginação e tabelas com rolagem interna, sem transbordamento da página.

## Triagem de 11/11 contra as imagens atuais

O inventário anterior (04/11) referenciava imagens antigas e a análise da plataforma tinha falhado (`scanner_failed`); esta triagem usa somente relatórios válidos das imagens em execução após a reconstrução completa de 09/11 e a atualização da base em 11/11. A falha histórica do scanner da plataforma foi causada por um contêiner referenciando imagem não exportável (corrigido recriando contêineres a partir das tags atuais) e por uma corrida de escrita no Windows — um leitor concorrente bloqueia `os.replace` com `PermissionError` e o worker passou a repetir a substituição por até 5 s antes de falhar (`scripts/scan_vulnerabilities.py`).

**Imagem da plataforma** (`aularedes-platform:local`, base `python:3.13-slim` Debian 13; HTTP e SMTP): 202 combinações de aviso+pacote+tipo+versão — 0 críticos, 61 altos, 62 médios, 15 baixos, 49 desprezíveis, 15 não classificados. A contagem não é o número de CVEs únicos: um mesmo aviso aparece por pacote afetado (por exemplo, os quatro CVEs do util-linux repetem em `mount`, `libblkid1`, `libuuid1`).

- Dos 61 altos, **59 são `wont-fix`**: a equipe de segurança do Debian 13 declara que não haverá correção nessa série para essas versões de bibliotecas de base (util-linux 4 avisos, glibc 3, ncurses 1, perl-base 2, gcc/libgcc/libstdc++ 2, libacl 2, libsqlite3 3). Sem versão corrigida publicável; atualizar a base não os elimina.
- **2 altos com correção publicada** (`CVE-2026-76844` e `CVE-2026-85091`, `zlib1g` → `1.3.1-1+deb13u1`): em 11/11 foi reconstruída a plataforma com `docker compose build --pull` (base mais recente) e a imagem nova foi reanalisada. O diff entre os relatórios foi zero — a base atual do `python:3.13-slim` ainda entrega `zlib1g 1.3.1-1+b1`; a correção `deb13u1` ainda não propagou. Achados permanecem abertos e a tentativa fica registrada; reavaliar em futuras rodadas (reanálise a cada 6 h) e reconstruir quando a base incorporar a correção.
- Dos 62 médios, 59 são `wont-fix` (mesmos pacotes de base) e 3 têm correção: dois no interpretador `python` 3.13.18 exigindo salto para 3.15/3.16 (não aplicável agora) e o `CVE-2026-27171` do mesmo `zlib1g` pendente na base.
- Aplicabilidade: todos os achados são de bibliotecas/pacotes de base do sistema, não de dependências do aplicativo (`requirements.lock.txt`). Os contêineres rodam como usuário dedicado (uid 10001), `no-new-privileges`, com capacidades removidas, filesystem raiz somente leitura e sem shell remoto exposto; apenas o painel publica porta no host. Não há evidência de explorabilidade em nenhum achado.
- **Decisão: aceitar e monitorar.** O alerta `VulnerabilidadeAlta` permanece ativo enquanto houver achado alto — comportamento intencional, sem supressão, porque a plataforma não tem mecanismo de “achado aceito” e silenciá-lo esconderia avisos reais. A seção de alertas acima já declara que a ausência de alerta não prova correção; o inverso também vale: alerta ativo não indica exploração.

**DNS** (`coredns/coredns:1.15.0` upstream): 4 achados — 2 altos (`GO-2026-6860` `golang.org/x/net` v0.60.0 → 0.62.0; `GO-2026-6865` `github.com/klauspost/compress` v1.19.1 → 1.20.2), 1 médio e 1 não classificado, todos com versão corrigida já publicada. O binário é compilado pelo upstream; não construímos o CoreDNS no laboratório, então a remediação depende de uma tag nova do upstream com dependências atualizadas. **Decisão: acompanhar lançamentos do CoreDNS e atualizar a imagem fixada quando houver; sem correção local viável.**

**PostgreSQL** (`aularedes-postgres:17.11-gosu1.19-go1.27.3`): em 04/11 a imagem em execução (`aa939f67…`, contêiner criado em 30/10 antes da remediação do gosu) ficou em estado inconsistente no Docker — o contêiner referenciava um ID de imagem não exportável (`docker image save`/`inspect` falhavam), o que explica os `scanner_failed` persistentes. A recriação do contêiner a partir da tag atual (dados preservados em volume nomeado) e a reanálise revelaram, com a base de avisos de 11/11, 1 crítico (`CVE-2026-4738`, `zlib`) e 12 altos (`krb5-libs`, `libxslt`), todos com versão corrigida publicada. `docker compose build --pull` não resolveu: o digest mais recente do upstream `postgres:17.11-alpine3.24` ainda traz `zlib 1.3.2-r1`, `krb5-libs 1.22.2-r1` e `libxslt 1.1.43-r3`. Seguindo o precedente do gosu de 30/10, a correção foi aplicada no Dockerfile da imagem com versões fixadas do repositório Alpine (`apk add zlib=1.4-r0 krb5-libs=1.22.3-r0 libxslt=1.1.43-r4`) e o pin da base foi atualizado para o digest atual (`e5d2edd2…`). A imagem nova (`87ad9221…`) foi recriada com dados preservados (1.000 registros) e reanalisada: **0 críticos, 0 altos**, com os mesmos 5 achados residuais de 04/11 — `CVE-2025-60876` do busybox do Alpine em três pacotes (médio, sem correção publicada), `GHSA-mjcv-p78q-w5fw` de `moby/sys/user` na construção do gosu (médio; o gosu 1.19 é a versão mais recente do upstream) e `GO-2026-5024` de `golang.org/x/sys` (baixo, também de build). **Decisão: manter os residuais; nova remediação do gosu só faz sentido quando o upstream publicar dependências atualizadas. As futuras atualizações do pin da base devem repetir o padrão: atualizar digest, recriar contêiner, reanalisar e conferir regressão dos protocolos.**

Médios, baixos, desprezíveis e não classificados não acionam limiares de alerta por desenho da plataforma; permanecem visíveis na aba Segurança para revisão. Nenhuma atualização automática de pacote foi instalada e nenhum dado sintético foi criado para demonstrar correção.

## Verificação reproduzível

Com os quatro serviços e o worker ativos:

```powershell
.\.venv\Scripts\python.exe scripts/verify_vulnerabilities.py
```

O roteiro confere login, filtros, IDs contra Docker, pacotes, deduplicação/páginas/contagens, cardinalidade das métricas, incidentes/e-mails aplicáveis aos achados reais, persistência após restart da API e operação dos protocolos/integridade das configurações.

Para demonstrar falha e recuperação reais do processo de análise:

```powershell
.\.venv\Scripts\python.exe scripts/verify_vulnerabilities.py --exercise-outage
```

Esse modo encerra temporariamente o worker, espera o inventário vencer, confirma contagens ocultas, quatro avisos/e-mails de análise indisponível e retoma o worker. Confirma recuperação dos relatórios, dos avisos e dos e-mails. O `finally` retoma o worker se uma verificação falhar. Pode levar cerca de cinco minutos porque respeita as janelas reais; execute sem reconstruir/interromper a stack. Não injeta achados fictícios. Relatório sem credenciais em `tmp/vulnerabilities-e2e-result.json`.

As regras também têm testes sintéticos isolados em `backend/tests/fixtures/vulnerability-rules.test.yml`, executados com `promtool test rules`; esses dados não são publicados no Prometheus do laboratório.

## Isolamento e limites

Somente o script no host chama Docker CLI. O backend tem um mount de relatórios somente leitura, sem acesso ao socket Docker. Os scanners recebem um arquivo de imagem/SBOM somente leitura, sem volumes dos serviços ou `.env`. Não há upload de inventário: somente o atualizador da base tem rede, sem imagem/SBOM montados; catalogação e comparação usam rede desabilitada. Containers têm filesystem somente leitura, capacidades removidas, `no-new-privileges`, CPU/memória/tmpfs limitados.

Imagens aceitas têm até 1 GiB; arquivo de exportação até 2 GiB. Saídas são limitadas durante execução a 32 MiB e stderr a 64 KiB, com término do comando quando excedidas. Manifesto da API tem limite de 64 KiB; relatórios normalizados de 8 MiB, 10.000 achados e 100.000 pacotes. JSON incompleto, contraditório ou ilegível fica indisponível. Arquivos raw/exportações temporários são removidos por caminhos fixos após a rodada; cache público fica no volume `aularedes-vulnerability-cache`.

A análise cobre o conteúdo da imagem e depende dos catalogadores/base. Não inclui volumes, host, configuração, plugins baixados em execução, garantia de detectar JavaScript embutido no frontend ou prova de explorabilidade. O administrador do host pode alterar o worker/relatórios; não há assinatura externa que proteja contra comprometimento total do laboratório.

Fontes oficiais: [alvos de análise](https://oss.anchore.com/docs/guides/vulnerability/scan-targets/), [base e validade](https://oss.anchore.com/docs/guides/vulnerability/database/), [JSON Grype](https://oss.anchore.com/docs/guides/vulnerability/json/), [Grype 0.121.0](https://github.com/anchore/grype/releases/tag/v0.121.0) e [Syft 1.55.0](https://github.com/anchore/syft/releases/tag/v1.55.0).
