"""Real resource/alert verification. CPU load is local, bounded, and cancelled in finally."""
import argparse
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from lab_session import authenticate

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://localhost:8000"
SERVICES = ("web-demo", "postgres", "dns", "smtp")


def docker(*arguments, timeout=30):
    return subprocess.run(["docker", *arguments], cwd=ROOT, check=True, capture_output=True,
                          text=True, timeout=timeout).stdout.strip()


def main(exercise_outage=False):
    started = datetime.now(timezone.utc)
    checks = []
    process = None
    worker_stopped = False
    identity = None
    stop_path = "/tmp/aularedes-resource-test-" + uuid.uuid4().hex + ".stop"
    with httpx.Client(timeout=10, trust_env=False) as client:
        assert client.get(BASE + "/api/resources").status_code == 401
        authenticate(client)

        def get(path):
            response = client.get(BASE + path); response.raise_for_status(); return response.json()

        def resources(): return get("/api/resources?service=postgres&window=15m")

        def rows(): return {row["id"]: row for row in resources()["services"]}

        def passed(label):
            checks.append(label); print("PASS: " + label, flush=True)

        def wait(label, predicate, timeout=120):
            until = time.monotonic() + timeout
            while time.monotonic() < until:
                try:
                    if predicate(): passed(label); return
                except httpx.HTTPError:
                    pass
                time.sleep(2)
            raise AssertionError("Tempo esgotado: " + label)

        def ready():
            current = rows()
            return len(current) == 4 and all(row["available"] and all(row["values"][field] is not None
                for field in ("cpu_cores", "memory_bytes", "read_bps", "write_bps")) for row in current.values())

        def mail():
            response = client.get("http://localhost:8025/api/v1/messages"); response.raise_for_status()
            return response.json()["messages"]

        def incident(name, service, status):
            return any(row["name"] == name and row["service"] == service and row["status"] == status
                and datetime.fromisoformat(row["started_at"].replace("Z", "+00:00")) >= started
                for row in get("/api/incidents")["incidents"])

        initial_mail = {row["ID"] for row in mail()}

        def email(text, service, status):
            return any(row["ID"] not in initial_mail and status in row["Subject"] and text in row["Subject"]
                       and service in row["Subject"] for row in mail())

        def monitor(option):
            subprocess.run([sys.executable, str(ROOT / "scripts/collect_resources.py"), option], cwd=ROOT,
                           check=True, capture_output=True, timeout=60)

        def cancel_cpu():
            if process is None or identity is None: return
            if process.poll() is None:
                docker("exec", identity, "python", "-c", f"from pathlib import Path; Path({stop_path!r}).touch()", timeout=10)
            try:
                process.wait(timeout=15)
            finally:
                docker("exec", identity, "python", "-c", f"from pathlib import Path; Path({stop_path!r}).unlink(missing_ok=True)", timeout=10)

        try:
            passed("Recursos exigem login e filtros são fixos")
            assert client.get(BASE + "/api/resources?service=other").status_code == 422
            assert client.get(BASE + "/api/resources?window=bad").status_code == 422
            wait("Quatro fontes atuais com CPU, RAM e I/O medidos", ready)
            for service, row in rows().items():
                observed = docker("compose", "ps", "-q", service)
                assert observed == row["container_id"]
                assert docker("inspect", "--format", "{{.State.StartedAt}}", observed) == row["started_at"]
            passed("IDs e início das quatro execuções conferem com Docker")
            wait("Histórico Prometheus possui amostras CPU e lacunas explícitas", lambda: resources()["history_available"]
                 and any(row["cpu_cores"] is not None for row in resources()["series"]))
            metrics = client.get(BASE + "/metrics").text
            assert sum(line.startswith("service_resource_metric_available{") for line in metrics.splitlines()) == 24
            assert "container_id=" not in metrics and "path=" not in metrics
            passed("Métricas têm cardinalidade fixa e não exportam identidades/caminhos como labels")
            identity = rows()["web-demo"]["container_id"]
            code = ("import hashlib,time\nfrom pathlib import Path\n"
                    f"stop=Path({stop_path!r})\nend=time.monotonic()+75\n"
                    "try:\n while time.monotonic()<end and not stop.exists():\n"
                    "  for _ in range(10000): hashlib.sha256(b'a'*4096).digest()\n"
                    "finally: stop.unlink(missing_ok=True)\n")
            flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
            process = subprocess.Popen(["docker", "exec", identity, "python", "-c", code], cwd=ROOT,
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **flags)
            wait("CPU real do HTTP excedeu 0,8 núcleo", lambda: (rows()["web-demo"]["values"]["cpu_cores"] or 0) > .8, timeout=50)
            wait("Incidente de CPU persistido após 30 s", lambda: incident("RecursoCPUElevada", "web-demo", "firing"), timeout=75)
            wait("E-mail local de CPU elevada recebido", lambda: email("Uso elevado de CPU", "web-demo", "firing"), timeout=30)
            peak = rows()["web-demo"]
            assert all(get(path)["service"]["status"] == "ok" for path in ("/api/overview", "/api/postgres", "/api/dns", "/api/smtp"))
            passed("Quatro protocolos responderam durante a carga CPU limitada")
            cancel_cpu()
            wait("CPU voltou ao orçamento após encerramento do processo temporário", lambda: rows()["web-demo"]["values"]["cpu_cores"] is not None and rows()["web-demo"]["values"]["cpu_cores"] < .2)
            wait("Incidente de CPU resolvido e e-mail de recuperação recebido", lambda: incident("RecursoCPUElevada", "web-demo", "resolved") and email("Uso elevado de CPU", "web-demo", "resolved"))
            if exercise_outage:
                monitor("--stop"); worker_stopped = True
                wait("Coletor parado: medições vencidas ficam desconhecidas nos quatro serviços", lambda: all(
                    row["status"] == "unknown" and all(value is None for value in row["values"].values()) for row in rows().values()))
                metrics = client.get(BASE + "/metrics").text
                assert not any(line.startswith("service_resource_cpu_cores{") or line.startswith("service_resource_memory_bytes{") for line in metrics.splitlines())
                passed("Coleta ausente omite gauges de consumo em vez de publicar zero")
                wait("Histórico interrompe a linha durante a perda da coleta", lambda: bool(resources()["series"])
                     and resources()["series"][-1]["cpu_cores"] is None
                     and any(row["cpu_cores"] is not None for row in resources()["series"]))
                wait("Quatro avisos de coleta e e-mails confirmados", lambda: all(
                    incident("RecursosColetaIndisponivel", service, "firing") and email("Coleta de recursos indisponível", service, "firing") for service in SERVICES))
                monitor("--background")
                recovery_at = time.time()
                wait("Coletor recuperado com novas taxas e memória reais", lambda: ready()
                     and all(row["observed_at"] >= recovery_at for row in rows().values()))
                worker_stopped = False
                wait("Quatro avisos de coleta resolvidos com e-mails de recuperação", lambda: all(
                    incident("RecursosColetaIndisponivel", service, "resolved") and email("Coleta de recursos indisponível", service, "resolved") for service in SERVICES))
            subprocess.run(["docker", "compose", "restart", "api"], cwd=ROOT, check=True, capture_output=True, timeout=60)
            wait("Snapshot e histórico permanecem utilizáveis após restart da API", lambda: ready() and any(row["cpu_cores"] is not None for row in resources()["series"]))
            wait("Quatro protocolos e oito configurações operacionais", lambda: all(get(path)["service"]["status"] == "ok"
                for path in ("/api/overview", "/api/postgres", "/api/dns", "/api/smtp"))
                and all(row["status"] == "ok" for row in get("/api/security/integrity")["files"]))
            assert docker("compose", "exec", "-T", "postgres", "psql", "-U", "lab_admin", "-d", "lab_network", "-At", "-c", "SELECT count(*) FROM lab_items") == "1000"
            passed("As 1.000 linhas PostgreSQL foram preservadas")
            output = ROOT / "tmp/resources-e2e-result.json"; output.parent.mkdir(exist_ok=True)
            output.write_text(json.dumps({"passed": True, "checks": checks, "outage_exercised": exercise_outage,
                "completed_at": datetime.now(timezone.utc).isoformat(), "peak": peak, "resources": resources()}, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Resultado: {len(checks)} verificações passaram.", flush=True)
        finally:
            try:
                cancel_cpu()
            except (subprocess.SubprocessError, OSError):
                print("Não foi possível confirmar o encerramento antecipado; a carga CPU tem limite próprio de 75 s.", file=sys.stderr)
            finally:
                if worker_stopped:
                    try:
                        monitor("--background")
                        recovery_at = time.time()
                        wait("Coletor retomado e nova coleta confirmada durante cleanup", lambda: ready()
                             and all(row["observed_at"] >= recovery_at for row in rows().values()), timeout=60)
                    except (subprocess.SubprocessError, OSError, AssertionError, httpx.HTTPError):
                        print("Não foi possível confirmar a recuperação do coletor; verifique scripts/collect_resources.py --background.", file=sys.stderr)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exercise-outage", action="store_true")
    main(parser.parse_args().exercise_outage)
