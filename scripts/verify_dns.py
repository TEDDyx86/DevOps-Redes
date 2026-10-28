"""Exercise only the local DNS service and restore it even when verification fails."""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from lab_session import authenticate


ROOT = Path(__file__).resolve().parents[1]


def docker(*args):
    return subprocess.run(["docker", "compose", *args], cwd=ROOT, capture_output=True, text=True, check=True)


def query(name, tcp=False):
    # Runs inside the API container so the DNS port stays internal to Compose.
    program = """import json, socket, dns.message, dns.query, dns.rcode
name, tcp = __import__('sys').argv[1:]
address = socket.gethostbyname('dns')
operation = dns.query.tcp if tcp == 'true' else dns.query.udp
answer = operation(dns.message.make_query(name, 'A'), address, port=1053, timeout=2)
print(json.dumps({'rcode': dns.rcode.to_text(answer.rcode()), 'answers': [r.address for rr in answer.answer if rr.rdtype == 1 for r in rr]}))
"""
    return json.loads(docker("exec", "-T", "api", "python", "-c", program, name, str(tcp).lower()).stdout)


def main():
    checks = []
    started = datetime.now(timezone.utc)
    with httpx.Client(timeout=8, trust_env=False) as client:
        authenticate(client)
        def get(path):
            response = client.get("http://localhost:8000" + path)
            response.raise_for_status()
            return response.json()

        def mail():
            response = client.get("http://localhost:8025/api/v1/messages")
            response.raise_for_status()
            return response.json()["messages"]

        previous_mail = {item["ID"] for item in mail()}

        def passed(label):
            checks.append(label)
            print("PASS: " + label, flush=True)

        def wait_for(label, predicate, timeout=90):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if predicate():
                    passed(label)
                    return
                time.sleep(2)
            raise AssertionError("Tempo esgotado: " + label)

        def incident(status):
            return any(item["name"] == "DNSIndisponivel" and item["status"] == status
                       and datetime.fromisoformat(item["started_at"].replace("Z", "+00:00")) >= started
                       for item in get("/api/incidents")["incidents"])

        def email(status):
            return any(item["ID"] not in previous_mail and "DNS indisponível" in item["Subject"] and status in item["Subject"] for item in mail())

        def error_counter_observed():
            response = client.get("http://localhost:9090/api/v1/query", params={"query": 'sum(coredns_dns_responses_total{job="dns",rcode="SERVFAIL"})'})
            response.raise_for_status()
            result = response.json()["data"]["result"]
            return bool(result) and float(result[0]["value"][1]) >= 1

        try:
            docker("start", "dns")
            wait_for("DNS operacional em UDP e TCP", lambda: get("/api/dns")["service"]["status"] == "ok")
            for tcp in [False, True]:
                result = query("app.aularedes.test.", tcp)
                assert result == {"rcode": "NOERROR", "answers": ["192.0.2.10"]}
                passed("Registro A correto via " + ("TCP" if tcp else "UDP"))
            assert query("db.aularedes.test.")["answers"] == ["192.0.2.20"]
            passed("Segundo registro da zona resolvido")
            assert query("nao-existe.aularedes.test.")["rcode"] == "NXDOMAIN"
            wait_for("NXDOMAIN medido sem virar erro de servidor", lambda: (get("/api/dns")["stats"]["nxdomain_percent"] or 0) > 0 and get("/api/dns")["stats"]["server_error_percent"] == 0)
            wait_for("Consultas por segundo medidas no CoreDNS", lambda: (get("/api/dns")["stats"]["qps"] or 0) > 0)
            assert query("falha.aularedes.test.")["rcode"] == "SERVFAIL"
            passed("Resposta SERVFAIL controlada verificada")
            # A new rcode series needs a sampled baseline before rate() can
            # measure a subsequent increment; a single first packet is not a rate.
            wait_for("Contador SERVFAIL coletado pelo Prometheus", error_counter_observed)
            assert query("falha.aularedes.test.")["rcode"] == "SERVFAIL"
            wait_for("Falha do servidor registrada na métrica correta", lambda: (get("/api/dns")["stats"]["server_error_percent"] or 0) > 0)
            docker("stop", "dns")
            wait_for("Parada real do DNS detectada", lambda: get("/api/dns")["service"]["status"] == "critical")
            assert get("/api/dns")["stats"]["qps"] is None
            passed("Estatísticas antigas ocultadas durante a falha")
            wait_for("HTTP e SQL continuam operacionais", lambda: get("/api/overview")["service"]["status"] == "ok" and get("/api/postgres")["service"]["status"] == "ok")
            wait_for("Incidente DNS persistido", lambda: incident("firing"))
            wait_for("E-mail crítico DNS recebido", lambda: email("firing"))
            docker("start", "dns")
            wait_for("Resolução DNS recuperada em ambos os protocolos", lambda: get("/api/dns")["service"]["status"] == "ok")
            wait_for("Métricas nativas e taxas recuperadas", lambda: get("/api/dns")["stats"]["available"] and (get("/api/dns")["stats"]["qps"] or 0) > 0)
            wait_for("Incidente DNS resolvido", lambda: incident("resolved"))
            wait_for("E-mail de recuperação DNS recebido", lambda: email("resolved"))
            report = {"passed": True, "checks": checks, "dns": get("/api/dns")}
            out = ROOT / "tmp" / "dns-e2e-result.json"
            out.parent.mkdir(exist_ok=True)
            out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Resultado: {len(checks)} verificações passaram.", flush=True)
        finally:
            docker("start", "dns")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
