# Integridade das configurações

Próximo passo autorizado após a detecção de tráfego: monitorar alterações nos arquivos de configuração dos quatro serviços e da infraestrutura de alertas.

## Arquivos e uso real

Lista fixa em `infra/`: `http.json`, `smtp.json`, `postgres/postgresql.conf`, `dns/Corefile`, `dns/db.aularedes.test`, `prometheus.yml`, `alerts.yml`, `alertmanager.yml`. HTTP e SMTP passam a ler os JSON no início do processo; PostgreSQL usa o arquivo conf externo com diretórios de dados/HBA explícitos. DNS e infraestrutura já usam esses arquivos. Montar diretórios em modo somente leitura para enxergar substituições atômicas. A API recebe apenas `infra/`, nunca `.env` ou segredos.

Monitorar arquivos em disco não prova que o processo já aplicou a configuração: JSONs, PostgreSQL e Corefile podem exigir restart; a zona segue regras próprias do CoreDNS. Não alterar funcionamento/limites atuais ao extrair as configurações existentes.

## Referência e detecção

SHA-256 dos bytes, em leitura limitada a 1 MiB por arquivo, a cada 5 s. Só arquivos regulares dentro da raiz permitida; rejeitar links simbólicos/junções, escapes, arquivos especiais e leitura instável. No Linux usar descritores relativos com O_NOFOLLOW para percorrer os diretórios. Conferir metadados antes/depois da leitura. Nunca devolver conteúdo nem diff; expor apenas caminho relativo conhecido, hashes, horário, ator da aprovação e estado.

SQLite próprio no volume de incidentes guarda referências aprovadas e estado anterior para deduplicar eventos após restart. Publicar snapshot só depois do commit. Histórico limitado a 10.000 eventos/7 dias, interface últimos 100. Estados: sem referência, íntegro, alterado, ausente, leitura indisponível, desconhecido/obsoleto após 20 s. Ausência confirmada é diferente de não conseguir verificar.

Não confiar automaticamente no primeiro hash. Aprovação explícita exige administrador autenticado, CSRF, origem e LAB_TOKEN. Corpo limitado aos IDs permitidos e hashes observados; reler antes do commit e recusar 409 se já mudou. Lotes de até 8 itens são atômicos; não aceitar IDs repetidos. Aprovação idempotente não cria eventos repetidos. Alterar referência não modifica arquivos nem reinicia serviços. Restaurar os bytes originais resolve a divergência sem trocar a referência.

API leitura `/api/security/integrity`; aprovação `/api/security/integrity/approve`. Exportador com rótulos fixos file_id/service, sem hashes como labels. Alertas: arquivo alterado/ausente por 15 s; verificação indisponível por 30 s; referência legível pendente por 2 min. A resolução de um alerta por perda de dados não prova integridade: conferir o estado e o alerta de verificação.

## Demonstração e limites

Script local aprova somente referências ainda pendentes e coerentes com os arquivos deste workspace. Não substitui referências já divergentes. Adiciona comentários/espaços inofensivos em um arquivo de cada serviço, confirma quatro alertas/e-mails, restaura os bytes e confirma recuperação. `finally` restaura apenas se o arquivo ainda contém a versão do teste, preservando alterações concorrentes. Não oferece escrita de configurações no navegador nem socket Docker na API.

Na interface Segurança, tabela de hashes/estado, revisão/aprovação e eventos. Confirmação da referência é um ato administrativo local, não assinatura criptográfica. Quem controla o host/SQLite/código do monitor pode adulterar a própria detecção; não é armazenamento inviolável nem prova de autoria da alteração.
