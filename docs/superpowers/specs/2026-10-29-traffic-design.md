# Tráfego acima da referência

Próximo passo autorizado pelo usuário em 29/10/2026: detecção de aumentos de volume nos quatro serviços. Esta etapa não identifica origem maliciosa nem substitui análise de ataque.

## Detecção

Taxas reais de 1 minuto do Prometheus: HTTP `/work` req/s; comandos SQL/s de lab_workload; consultas CoreDNS/s; mensagens SMTP aceitas/s. Só aceitar amostras com sonda, fonte nativa e estatísticas necessárias saudáveis e recentes (20 s). Falta de dados é estado desconhecido; zero medido é um valor válido.

Referência inicial por serviço: média de pelo menos 25 amostras válidas abrangendo 120 s, sem intervalo >15 s. Requer ambiente em operação habitual durante aprendizado. Valores e data persistem em SQLite separado dos serviços monitorados. A referência fica fixa depois de calculada: um pico prolongado não a eleva automaticamente. Recalibração explícita autenticada por serviço inicia outra janela de 2 min; sem escrita automática durante anomalia. Alternativa de média móvel foi descartada para evitar incorporar carga sustentada; ML seria desnecessário neste laboratório.

Limiar = max(3 × referência, piso): HTTP 2 req/s, SQL 5 comandos/s, DNS 5 consultas/s, SMTP 0,15 mensagens/s (9/min). Estado anômalo usa comparação estrita `taxa > limiar`. A tabela SMTP exibe msg/min, com conversão de taxa/referência/limiar consistente. Não chamar ausência de referência de operação normal.

Sondagem independente a cada 5 s. Snapshots atômicos em memória; exportador omite taxa e anomalia quando desconhecidas e informa sucesso/estado de calibração. Séries por serviço, sem IP ou outros rótulos não limitados. Alertas: `TrafegoAnormal` por 30 s, aviso por serviço; `TrafegoColetaIndisponivel` por 30 s quando fonte não responde. A resolução do alerta sozinha não prova recuperação se a fonte ficar sem dados; conferir estado/alerta de coleta. Interface mantém essa distinção.

## Demonstração

Um job local por vez, alvo fixo configurado (HTTP, SQL, DNS, SMTP ou todos). Até 90 s: 5 req/s HTTP, 10 comandos/s SQL, 10 consultas/s DNS e 1 mensagem/s SMTP. Uma operação por serviço de cada vez, timeout e contadores de tentativas/sucessos/falhas. Limitar iterações ao teto taxa×duração e encerrar tarefas na parada da API. Sem comandos Docker, endereços externos ou parâmetros SQL livres. Iniciar/cancelar exige sessão, CSRF e LAB_TOKEN. GET de estado exige sessão.

Adicionar tabela de tráfego à aba Segurança e controles à aba Laboratório. Recalibração exige sessão/CSRF/LAB_TOKEN e operação saudável; não é um botão de silenciar alertas. Dados da tabela expiram em 20 s. Incidentes e e-mails reutilizam Prometheus/Alertmanager e o Mailpit independente.

## Verificação

Testar referência fixa/persistente, calibração com lacunas/falhas/zero, limiar e unidades, fonte desconhecida, ausência do Prometheus, proteção dos controles, limites/cancelamento do job e ausência de segredos. Teste integrado com os quatro tráfegos reais, taxas medidas, alertas/e-mails de abertura e recuperação, e fim automático da carga. Documentar escopo e evidências em desktop/mobile.
