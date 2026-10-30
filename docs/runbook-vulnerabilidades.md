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

Em 30/10, foi aplicada uma [atualização preventiva do gosu na imagem PostgreSQL](runbook-postgres-remediation.md), com backup restaurado, 50 pacotes catalogados e redução de 3 críticos/32 altos para zero críticos/altos. Os avisos eram associados à versão Go do utilitário, sem prova de exploração SQL. Os cinco achados restantes e os avisos das outras imagens continuam publicados. Em seguida, três ciclos históricos de 29/10 que ficaram abertos durante uma interrupção foram [reconciliados por resoluções posteriores persistidas](runbook-incidentes.md), preservando o término original como desconhecido. Os dois alertas altos atuais de HTTP/SMTP continuam ativos. A conferência visual de Incidentes/Segurança foi concluída em desktop e celular, com filtros, paginação e tabelas com rolagem interna, sem transbordamento da página.

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
