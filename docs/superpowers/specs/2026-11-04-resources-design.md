# Recursos dos contêineres monitorados

Etapa autorizada pelo usuário após reconciliação/QA. O PDF recomenda CPU, memória, I/O e latência de disco para SQL; esta entrega cobre CPU, memória e movimentação de blocos nos quatro serviços. Latência de disco, espaço livre do host, pools e queries lentas continuam separados.

## Decisão

Coletor Python local com SDK oficial Docker, em ambiente virtual próprio ignorado pelo Git. O SDK usa o endpoint local do contexto Docker atual (named pipe Windows ou Unix socket); nenhuma porta Docker TCP é criada. Somente o host consulta estatísticas; API recebe snapshot normalizado via diretório somente leitura. cAdvisor exigiria mounts/permissões adicionais; a saída resumida do CLI arredonda I/O. Usar a API de estatísticas preserva os contadores exatos.

Dependências fixadas com hashes em `requirements-resources.lock.txt`, instaladas uma vez em `.runtime/resource-worker-venv`. O launcher/start.ps1 prepara esse ambiente sem instalar pacotes globais. Sem SDK Docker na imagem da plataforma.

## Contrato

- Serviços fixos: web-demo, postgres, dns, smtp. Uma instância por serviço; outras ou duplicadas não geram medições fictícias. Consultas de estatísticas são GET e usam somente IDs validados. Não coletar/publicar variáveis de ambiente, configuração secreta ou volumes.
- Amostragem a cada 5 s. Memória total e working set (uso menos cache inativo) em bytes; falta/contradição de campo não vira zero. Limite retornado pelo Engine pode ser o da VM compartilhada, portanto não tratá-lo como orçamento individual.
- CPU em núcleos equivalentes = delta de nanossegundos CPU / intervalo real / 1e9 (1,0 equivale a um núcleo). Leitura/escrita em B/s a partir dos contadores de blocos do Engine. Primeiro ponto, reinício/troca de contêiner, contador regressivo, relógio/intervalo inválido: taxas desconhecidas até nova amostra. Usar ID e início do contêiner para separar execuções, conferidos antes/depois.
- I/O ausente não equivale a zero; movimentação de blocos não mede ocupação, latência ou todas as operações de arquivos/cache. Não prometer IOPS quando não fornecidas.
- Snapshot atômico limitado a 64 KiB, com quatro serviços, identidade/execução, horário da medição e métricas normalizadas. Fonte com mais de 20 s ou relógio futuro além de 5 s é desconhecida. Erro por serviço não impede os demais. Worker único, comandos/leituras com prazo, encerramento controlado e arquivos raw nunca servidos.
- API autenticada `/api/resources?service=...&window=...`, métricas Prometheus com rótulos fixos serviço/métrica, sem IDs ou caminhos. Valores atuais vêm do snapshot; histórico Prometheus com lacunas e disponibilidade por métrica, sem reutilizar valores anteriores durante aquecimento/falha.
- Página Recursos com tabela consolidada dos quatro serviços, serviço/período selecionáveis e gráficos CPU/memória/I/O. Estados parcial, desconhecido, normal e atenção; falha de recursos não determina indisponibilidade de HTTP/SQL/DNS/SMTP.
- Orçamentos didáticos explícitos: CPU 0,8 núcleo, RAM 128 MiB (PostgreSQL 256 MiB), I/O combinado 10 MiB/s, persistentes por 30 s. São limiares de observação, sem impor limites ao contêiner nem afirmar saturação do host. Coleta indisponível por 30 s gera atenção separada; resolução sem dados não comprova normalização. Alertas/e-mails usam infraestrutura existente.

## Verificação e preservação

Testes antes do código: deltas/execução/cache/ausência/zeros/NaN/infinitos/relógio, identidade divergente, falha isolada e fonte expirada, métricas sem cardinalidade arbitrária, endpoints protegidos e histórico com lacunas. Dependências em venv isolada. Regras promtool com casos sintéticos isolados. Verificar CPU real com processo temporário limitado no HTTP, incidente/e-mail e recuperação; interromper/retomar somente o coletor, confirmando dados desconhecidos e quatro protocolos operacionais. Sem carga fictícia publicada. Validar desktop/mobile, navegação, gráficos e console. Preservar volumes SQL/histórico e 1.000 linhas; atualizar somente referência de alerts.yml após revisão e validação. Excluir gerarrelatório.py preexistente.
