"""Local authentication demonstration; no secrets in output or report."""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from lab_session import authenticate, credentials


ROOT = Path(__file__).resolve().parents[1]
BASE = "http://localhost:8000"


def main():
    started = datetime.now(timezone.utc)
    checks = []
    with httpx.Client(timeout=8, trust_env=False) as client, httpx.Client(timeout=8, trust_env=False) as anonymous:
        def passed(label):
            checks.append(label)
            print("PASS: " + label, flush=True)

        def get(path):
            response = client.get(BASE + path)
            response.raise_for_status()
            return response.json()

        def wait_for(label, predicate, timeout=100):
            deadline = time.monotonic()+timeout
            while time.monotonic() < deadline:
                if predicate():
                    passed(label)
                    return
                time.sleep(2)
            raise AssertionError("Tempo esgotado: " + label)

        def mail():
            response = client.get("http://localhost:8025/api/v1/messages", params={"limit": 200})
            response.raise_for_status()
            return response.json()["messages"]

        before_mail = {item["ID"] for item in mail()}

        def incident(status):
            return any(item["name"] == "AutenticacaoSuspeita" and item["status"] == status
                       and datetime.fromisoformat(item["started_at"].replace("Z", "+00:00")) >= started
                       for item in get("/api/incidents")["incidents"])

        def email(status):
            return any(item["ID"] not in before_mail and "Tentativas repetidas de acesso" in item["Subject"] and status in item["Subject"] for item in mail())

        for path in ["/api/overview", "/api/postgres", "/api/dns", "/api/smtp", "/api/incidents", "/api/security", "/docs", "/openapi.json"]:
            assert anonymous.get(BASE+path).status_code == 401
        passed("Dados dos quatro serviços, eventos e documentação exigem login")
        for path in ["/health", "/metrics"]:
            assert anonymous.get(BASE+path).status_code == 200
        passed("Health e coleta do Prometheus continuam acessíveis")
        authenticate(client)
        passed("Credenciais locais iniciam uma sessão real")
        cookie = client.cookies.get("aularedes_session")
        csrf = client.headers["X-CSRF-Token"]
        assert anonymous.post(BASE+"/api/auth/logout", cookies={"aularedes_session":cookie}).status_code == 403
        passed("Cookie sem CSRF não permite encerrar sessão")
        assert client.post(BASE+"/api/auth/logout", headers={"Origin":"http://foreign.test"}).status_code == 403
        passed("Origem externa rejeitada mesmo com sessão e CSRF")
        # Existing session survives an API restart, and monitoring resumes.
        subprocess.run(["docker","compose","restart","api"], cwd=ROOT, check=True, capture_output=True)
        def session_restored():
            try:
                return client.get(BASE+"/api/auth/session").status_code == 200
            except httpx.HTTPError:
                return False
        wait_for("Sessão persistiu ao reiniciar a API", session_restored)
        wait_for("Quatro serviços recuperaram as sondas após reinício", lambda: all(get(path)["service"]["status"] == "ok" for path in ["/api/overview","/api/postgres","/api/dns","/api/smtp"]))
        baseline = get("/api/security")["totals"]["failure"]
        for number in range(5):
            response = anonymous.post(BASE+"/api/auth/login", headers={"X-Forwarded-For":f"192.0.2.{number}"}, json={"username":"admin","password":"incorrect-verification-password"})
            assert response.status_code == 401
        passed("Cinco falhas registradas sem confiar em IP informado pelo cliente")
        response = anonymous.post(BASE+"/api/auth/login", json=credentials())
        assert response.status_code == 429 and int(response.headers["Retry-After"]) > 0
        passed("Sexta tentativa recebe 429 e Retry-After, inclusive com senha correta")
        stats = get("/api/security")
        assert stats["totals"]["failure"] == baseline+5 and stats["failures_recent"]["ip"] >= 5
        assert credentials()["password"] not in json.dumps(stats) and cookie not in json.dumps(stats) and csrf not in json.dumps(stats)
        passed("Eventos e contadores persistidos sem senha, cookie ou CSRF")
        assert client.get(BASE+"/api/smtp").status_code == 200
        passed("Sessão existente continua operando durante bloqueio de login")
        wait_for("Incidente de autenticação suspeita persistido", lambda: incident("firing"))
        wait_for("E-mail de autenticação suspeita recebido", lambda: email("firing"))
        wait_for("Janela de falhas expirou automaticamente", lambda: get("/api/security")["failures_recent"]["ip"] == 0)
        wait_for("Incidente de autenticação resolvido", lambda: incident("resolved"))
        wait_for("E-mail de recuperação recebido", lambda: email("resolved"))
        assert client.post(BASE+"/api/auth/logout").status_code == 200
        anonymous.cookies.set("aularedes_session",cookie)
        assert anonymous.get(BASE+"/api/incidents").status_code == 401
        anonymous.cookies.clear()
        passed("Logout revogou a sessão também contra reutilização do cookie")
        authenticate(client)
        passed("Novo login permitido após expirar a janela")
        assert all(get(path)["service"]["status"] == "ok" for path in ["/api/overview","/api/postgres","/api/dns","/api/smtp"])
        passed("HTTP, SQL, DNS e SMTP operacionais ao final")
        report = {"passed":True,"checks":checks,"totals":get("/api/security")["totals"]}
        output = ROOT / "tmp/auth-e2e-result.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
        print(f"Resultado: {len(checks)} verificações passaram.",flush=True)
        client.post(BASE+"/api/auth/logout")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
