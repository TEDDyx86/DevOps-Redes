# DNS: terceiro serviço monitorado

Autorização: o usuário pediu para seguir para DNS na arquitetura local já aprovada.

## Entrega

CoreDNS autoritativo para `aularedes.test`, em container separado, porta interna 1053 UDP/TCP e métricas 9153. Nenhuma porta DNS é publicada no host e o DNS do computador não é alterado. A zona de teste não depende de servidores externos.

## Monitoramento

- Sonda independente verifica `app.aularedes.test. A = 192.0.2.10` por UDP e TCP. Sucesso exige NOERROR e o registro esperado nos dois protocolos. O IP é reservado para documentação, não representa o endereço de uma aplicação externa.
- A duração é o maior tempo das duas sondas executadas em paralelo. Limite de atenção: 100 ms por 30 s. Falha persistente: crítico após 15 s.
- Coleta nativa do CoreDNS: consultas/s, p95 do processamento no servidor, erros de servidor (SERVFAIL/REFUSED/FORMERR/NOTIMP) e NXDOMAIN separadamente. NXDOMAIN esperado não é tratado como indisponibilidade.
- Gerador limitado consulta os registros app/db e um nome inexistente de teste a cada 2 s. Não há cache na sonda nem consultas à internet.
- `falha.aularedes.test` retorna SERVFAIL intencional para testar a classificação de códigos DNS. Esse registro não é usado pela sonda de saúde nem pelo tráfego periódico normal.
- Amostra ausente ou acima de 20 s é desconhecida. Falha DNS não impede HTTP, SQL, API ou incidentes. Perda apenas das métricas nativas não equivale a falha da resolução.

## Interface e validação

Rota `/api/dns?window=15m`, página DNS, terceira linha consolidada e gráficos com valores reais. Mesma linguagem visual e expiração independente. Runbook com stop/start do container DNS, sem acesso Docker na API.

Testar contratos, respostas DNS reais codificadas, endereço incorreto, NXDOMAIN, falha de um protocolo, dados antigos, regra de alertas, parada/recuperação reais, independência HTTP/SQL e e-mails. Revisão independente ao final.
