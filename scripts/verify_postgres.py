"""Real PostgreSQL failure/recovery check for the local Compose laboratory."""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]


def docker(*arguments, check=True):
    return subprocess.run(["docker", "compose", *arguments], cwd=ROOT, capture_output=True, text=True, check=check)


def sql(query):
    return docker("exec", "-T", "postgres", "psql", "-v", "ON_ERROR_STOP=1", "-U", "lab_admin", "-d", "lab_network", "-At", "-c", query).stdout.strip()


def main():
    checks = []
    started = datetime.now(timezone.utc)
    with httpx.Client(timeout=8, trust_env=False) as client:
        def get(path):
            response = client.get("http://localhost:8000" + path)
            response.raise_for_status()
            return response.json()

        def mail():
            response = client.get("http://localhost:8025/api/v1/messages")
            response.raise_for_status()
            return response.json()["messages"]

        existing_mail = {item["ID"] for item in mail()}

        def wait_for(label, predicate, timeout=90):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if predicate():
                    checks.append(label)
                    print("PASS: " + label, flush=True)
                    return
                time.sleep(2)
            raise AssertionError("Tempo esgotado: " + label)

        def incident(status):
            return any(item["name"] == "PostgreSQLIndisponivel" and item["status"] == status
                       and datetime.fromisoformat(item["started_at"].replace("Z", "+00:00")) >= started
                       for item in get("/api/incidents")["incidents"])

        def new_email(status):
            return any(item["ID"] not in existing_mail and "PostgreSQL" in item["Subject"] and status in item["Subject"] for item in mail())

        try:
            docker("start", "postgres")
            wait_for("PostgreSQL operacional com estatísticas reais", lambda: get("/api/postgres")["service"]["status"] == "ok" and get("/api/postgres")["stats"]["available"])
            wait_for("Comandos SQL e commits medidos", lambda: (get("/api/postgres")["stats"]["qps"] or 0) > 0 and (get("/api/postgres")["stats"]["commits_per_second"] or 0) > 0)
            wait_for("Rollbacks reais observados", lambda: (get("/api/postgres")["stats"]["rollbacks_per_second"] or 0) > 0)
            baseline_sum = int(sql("SELECT sum(value) FROM lab_items"))
            assert sql("SELECT count(*) FROM lab_items") == "1000"
            denial = docker("exec", "-T", "postgres", "psql", "-v", "ON_ERROR_STOP=1", "-U", "lab_admin", "-d", "lab_network", "-c", "SET ROLE lab_monitor; UPDATE lab_items SET value=0 WHERE id=1", check=False)
            assert denial.returncode != 0 and "permission denied" in denial.stderr
            checks.append("Papel de monitoramento não pode alterar dados")
            print("PASS: " + checks[-1], flush=True)
            docker("stop", "postgres")
            wait_for("Parada real detectada", lambda: get("/api/postgres")["service"]["status"] == "critical")
            down = get("/api/postgres")
            assert down["stats"]["connections"] is None and down["stats"]["qps"] is None
            checks.append("Estatísticas antigas ocultadas durante a falha")
            print("PASS: " + checks[-1], flush=True)
            wait_for("HTTP continua operacional com PostgreSQL parado", lambda: get("/api/overview")["service"]["status"] == "ok")
            wait_for("Incidente PostgreSQL persistido sem depender do banco", lambda: incident("firing"))
            wait_for("E-mail crítico PostgreSQL recebido", lambda: new_email("firing"))
            docker("start", "postgres")
            wait_for("Banco recuperado e coletor reconectado", lambda: get("/api/postgres")["service"]["status"] == "ok" and get("/api/postgres")["stats"]["available"])
            wait_for("Taxas SQL voltam após a recuperação", lambda: (get("/api/postgres")["stats"]["qps"] or 0) > 0 and (get("/api/postgres")["stats"]["commits_per_second"] or 0) > 0)
            assert sql("SELECT count(*) FROM lab_items") == "1000"
            assert int(sql("SELECT sum(value) FROM lab_items")) >= baseline_sum
            checks.append("Tabela e atualizações preservadas no volume")
            print("PASS: " + checks[-1], flush=True)
            wait_for("Incidente PostgreSQL resolvido", lambda: incident("resolved"))
            wait_for("E-mail de recuperação PostgreSQL recebido", lambda: new_email("resolved"))
            report = {"passed": True, "checks": checks, "database": get("/api/postgres")}
            out = ROOT / "tmp" / "postgres-e2e-result.json"
            out.parent.mkdir(exist_ok=True)
            out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Resultado: {len(checks)} verificações passaram.", flush=True)
        finally:
            docker("start", "postgres")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
