# SMTP — laboratório local

Continuação autorizada pelo usuário em 28/10. Servidor SMTP Python/aiosmtpd com fila SQLite persistente e entrega para uma segunda instância Mailpit. O Mailpit existente permanece dedicado aos alertas.

- SMTP interno `smtp:2525`; métricas HTTP `smtp:8027`; receptor `smtp-inbox:1025`, caixa web localhost:8026.
- Aceitar somente aluno@aularedes.test, mensagem até 64 KiB, fila até 1.000 pendências. Sem encaminhamento externo, autenticação ou TLS nesta rede local isolada.
- Confirmar DATA com 250 somente após persistência. Repetir entrega temporariamente falha após 5 s. Falhas definitivas 5xx são contabilizadas separadamente. Recuperar mensagens em trânsito no reinício (entrega pelo menos uma vez; pode haver duplicata após queda no instante da confirmação).
- Disponibilidade por EHLO + NOOP; volume real a cada 15 s; contadores persistentes de aceitas, entregues, tentativas, rejeições e falhas definitivas; fila; volume minuto/hora e p95 do tempo aceitação → receptor.
- Taxa acumulada de entrega = entregues / aceitas. Aceitação SMTP não equivale a entrega. Não representa recebimento em provedor externo ou leitura pelo destinatário.
- Alerta crítico: sonda falha por 15 s. Aviso: fila >=5 por 30 s; sonda >500 ms por 30 s. Estatísticas ausentes devem ser explícitas.
- Painel SMTP, quarto serviço na visão geral, incidentes e runbook de parada/recuperação. Dados antigos desaparecem após 20 s.
- Validação: SMTP real, destinatário inválido, persistência, receptor parado → fila → retomada, MTA parado → incidente/e-mail → recuperação, demais serviços preservados.

Referências: [aiosmtpd handlers](https://aiosmtpd.aio-libs.org/en/latest/handlers.html), [Controller](https://aiosmtpd.aio-libs.org/en/latest/controller.html), [limite SIZE](https://aiosmtpd.aio-libs.org/en/stable/smtp.html).
