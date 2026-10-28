"""Real integration check. Requires the local Compose stack to be running.

Temporarily changes only the demonstration service and restores it in finally.
Results do not include credentials. Run with .venv/Scripts/python scripts/verify_lab.py.
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]


def main():
    env = dict(line.split("=", 1) for line in (ROOT / ".env").read_text().splitlines() if "=" in line and not line.startswith("#"))
    results = []
    started_at = datetime.now(timezone.utc)
    with httpx.Client(timeout=8, trust_env=False) as client:
        def get(path):
            response = client.get("http://localhost:8000" + path)
            response.raise_for_status()
            return response.json()

        def mode(value):
            response = client.post("http://localhost:8000/api/lab/mode", headers={"X-Lab-Token": env["LAB_TOKEN"]}, json={"mode": value})
            response.raise_for_status()

        def wait_for(label, predicate, timeout=80):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if predicate():
                    results.append({"check": label, "passed": True})
                    print("PASS: " + label, flush=True)
                    return
                time.sleep(2)
            raise AssertionError("Tempo esgotado: " + label)

        def incident(name, status):
            return any(item["name"] == name and item["status"] == status
                       and datetime.fromisoformat(item["started_at"].replace("Z", "+00:00")) >= started_at
                       for item in get("/api/incidents")["incidents"])

        def mailbox():
            response = client.get("http://localhost:8025/api/v1/messages")
            response.raise_for_status()
            return response.json()

        initial_emails = mailbox()["total"]
        existing_mail_ids = {item["ID"] for item in mailbox()["messages"]}
        try:
            mode("normal")
            wait_for("HTTP operacional e coleta real", lambda: get("/api/overview")["service"]["status"] == "ok")
            wait_for("Tráfego saudável com taxa de erro zero", lambda: get("/api/overview")["service"]["error_percent"] == 0)
            mode("slow")
            print("Aguardando confirmação da regra de lentidão (30 s + coleta/avaliação)…", flush=True)
            wait_for("Estado de atenção observado", lambda: get("/api/overview")["service"]["status"] == "warning")
            wait_for("Incidente de lentidão persistido", lambda: incident("HTTPLento", "firing"))
            wait_for("E-mail de alerta recebido via SMTP", lambda: mailbox()["total"] > initial_emails)
            mode("offline")
            wait_for("HTTP indisponível observado", lambda: get("/api/overview")["service"]["status"] == "critical")
            wait_for("Incidente crítico persistido", lambda: incident("HTTPIndisponivel", "firing"))
            wait_for("Métricas preservadas durante falha", lambda: get("/api/overview")["service"]["rps"] is not None)
            mode("normal")
            wait_for("Estado operacional recuperado", lambda: get("/api/overview")["service"]["status"] == "ok")
            wait_for("Incidente crítico resolvido", lambda: incident("HTTPIndisponivel", "resolved"))
            wait_for("Incidente de lentidão resolvido", lambda: incident("HTTPLento", "resolved"))
            wait_for("E-mail de recuperação recebido", lambda: any("resolved" in item["Subject"] and item["ID"] not in existing_mail_ids for item in mailbox()["messages"]))
            report = {"passed": True, "checks": results, "emails_before": initial_emails, "emails_after": mailbox()["total"], "service": get("/api/overview")["service"]}
            out = ROOT / "tmp" / "e2e-result.json"
            out.parent.mkdir(exist_ok=True)
            out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Resultado: {len(results)} verificações passaram. Evidência em tmp/e2e-result.json", flush=True)
        finally:
            mode("normal")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
