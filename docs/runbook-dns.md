# Runbook DNS

## Arquitetura

CoreDNS 1.15.0 responde pela zona autoritativa `aularedes.test` na porta interna 1053 UDP/TCP. Métricas nativas ficam na porta interna 9153. Nenhuma porta DNS é publicada no host; o DNS do Windows e a resolução dos outros serviços não são alterados.

O binário oficial carrega a capacidade `NET_BIND_SERVICE`. O Compose mantém somente essa capacidade no conjunto permitido, executa como UID 65532 e aplica `no-new-privileges`. Retirar essa capacidade do conjunto permitido impede a execução do binário oficial, mesmo usando porta acima de 1024.

## Registros de teste

| Nome | Tipo | Resposta |
|---|---|---|
| app.aularedes.test. | A | 192.0.2.10 |
| db.aularedes.test. | A | 192.0.2.20 |
| ns.aularedes.test. | A | 192.0.2.53 |
| ausente.aularedes.test. | A | NXDOMAIN |
| falha.aularedes.test. | A | SERVFAIL controlado pelo plugin template |

Os endereços 192.0.2.x são de documentação, sem destino externo. A zona responde localmente, sem encaminhamento à internet. Alterações na zona precisam de serial atualizado e reinício ou recarga apropriada do CoreDNS.

## Indicadores

- Disponibilidade: exige NOERROR e exatamente o registro A esperado em UDP e TCP. Não basta o processo estar executando.
- Latência das sondas: maior duração das duas consultas paralelas, sem cache do cliente. Não inclui a resolução do nome interno do container DNS.
- Consultas/s: taxa do contador nativo `coredns_dns_requests_total`, incluindo sondas, gerador e consultas manuais.
- p95 do servidor: histograma do tempo de processamento no CoreDNS; diferente da latência de rede observada pela sonda.
- Erros do servidor: SERVFAIL, REFUSED, FORMERR e NOTIMP como percentual das respostas.
- NXDOMAIN: nome inexistente, mostrado separadamente. O gerador consulta um nome ausente intencionalmente a cada quatro consultas, sem significar indisponibilidade.

O gerador emite uma consulta UDP a cada 2 s. A sonda executa UDP e TCP em paralelo a cada ciclo de aproximadamente 5 s. Consultas têm prazo de 1,5 s; o ciclo da sonda é limitado a 4 s. Uma falha não bloqueia tarefas HTTP/SQL.

Taxas usam janela móvel de 1 minuto. Um novo código de resposta precisa de uma primeira amostra e um incremento posterior para que `rate` o meça. O teste integrado respeita essa característica. Lacunas de coleta são preservadas no histórico; a linha não conecta artificialmente pontos antes e depois da indisponibilidade.

## Alertas

- `DNSIndisponivel`: falha de um protocolo ou registro incorreto durante 15 s.
- `DNSLento`: latência acima de 100 ms durante 30 s, com registro correto.
- `DNSErrosElevados`: mais de 10% de erros de servidor durante 30 s. NXDOMAIN é excluído.

Os tempos começam quando o Prometheus observa a condição, acrescidos dos intervalos de coleta e avaliação. Se apenas a porta de métricas falhar, a resolução pode continuar operacional; a interface informa a ausência das métricas detalhadas separadamente.

## Parada e recuperação

1. Abra http://localhost:8000/#dns e confira UDP/TCP operacionais.
2. Execute `docker compose stop dns`.
3. Veja a terceira linha indisponível na visão geral, sem interrupção HTTP/SQL.
4. Confira incidente e e-mail local em http://localhost:8025.
5. Execute `docker compose start dns`.
6. Confirme retorno das duas sondas, taxas, resolução do incidente e e-mail de recuperação.

Não pare todos os containers para simular uma falha apenas do DNS.

## Diagnóstico

```powershell
docker compose ps dns
docker compose logs --tail 50 dns api
```

Consulta UDP real a partir do container API:

```powershell
docker compose exec api python -c "import socket,dns.message,dns.query; print(dns.query.udp(dns.message.make_query('app.aularedes.test.', 'A'), socket.gethostbyname('dns'), port=1053, timeout=2))"
```

Para TCP, substitua `dns.query.udp` por `dns.query.tcp`. Para os códigos, substitua o nome por `ausente.aularedes.test.` ou `falha.aularedes.test.`. O domínio SERVFAIL é proposital e não é usado pela sonda de saúde.

## Verificação reproduzível

```powershell
.\.venv\Scripts\python.exe scripts/verify_dns.py
```

O teste confirma consultas, códigos, métricas, parada real, independência HTTP/SQL, incidentes, e-mails e recuperação. Restaura DNS em `finally` e grava evidência sem credenciais em `tmp/dns-e2e-result.json`.

## Referências

- [Métricas do CoreDNS](https://coredns.io/plugins/metrics/)
- [Plugin template](https://coredns.io/plugins/template/)
- [Consultas assíncronas dnspython](https://dnspython.readthedocs.io/en/latest/async.html)
- [Imagem oficial e capacidade do binário](https://github.com/coredns/coredns/blob/v1.15.0/Dockerfile)
