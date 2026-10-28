"""Real, local SMTP delivery/queue/failure checks. Always restore both services."""
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]


def docker(*args):
    return subprocess.run(["docker", "compose", *args], cwd=ROOT, capture_output=True, text=True, check=True)


def send(count=1, recipient="aluno@aularedes.test"):
    program = """import json, smtplib, sys
from email.message import EmailMessage
batch, count, recipient = sys.argv[1:]
ids=[]
with smtplib.SMTP('smtp',2525,timeout=3) as smtp:
    for number in range(int(count)):
        message=EmailMessage()
        message['From']='verificacao@aularedes.test'
        message['To']=recipient
        message['Subject']='AulaRedes SMTP verification '+batch
        key=f'{batch}.{number}@aularedes.test'
        message['Message-ID']='<'+key+'>'
        message.set_content('Mensagem de verificacao inteiramente local.')
        try:
            smtp.send_message(message)
            ids.append(key)
        except smtplib.SMTPRecipientsRefused as error:
            print(json.dumps({'rejected':error.recipients[recipient][0]}))
            sys.exit(0)
print(json.dumps({'ids':ids}))
"""
    return json.loads(docker("exec", "-T", "api", "python", "-c", program, uuid.uuid4().hex, str(count), recipient).stdout)


def main():
    checks = []
    started = datetime.now(timezone.utc)
    with httpx.Client(timeout=8, trust_env=False) as client:
        def get(path):
            response = client.get("http://localhost:8000" + path)
            response.raise_for_status()
            return response.json()

        def mail(port):
            response = client.get(f"http://localhost:{port}/api/v1/messages", params={"limit": 200})
            response.raise_for_status()
            return response.json()["messages"]

        before_mail = {item["ID"] for item in mail(8025)}

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

        def incident(name, status):
            return any(item["name"] == name and item["status"] == status
                       and datetime.fromisoformat(item["started_at"].replace("Z", "+00:00")) >= started
                       for item in get("/api/incidents")["incidents"])

        def email(subject, status):
            return any(item["ID"] not in before_mail and subject in item["Subject"] and status in item["Subject"] for item in mail(8025))

        def delivered(ids):
            return set(ids).issubset({item["MessageID"] for item in mail(8026)})

        try:
            docker("start", "smtp", "smtp-inbox")
            wait_for("SMTP operacional e métricas nativas disponíveis", lambda: get("/api/smtp")["service"]["status"] == "ok" and get("/api/smtp")["stats"]["available"])
            initial = get("/api/smtp")["stats"]
            ids = send()["ids"]
            wait_for("Mensagem real recebida e correlacionada por Message-ID", lambda: delivered(ids))
            assert send(recipient="rejeitado@aularedes.test") == {"rejected": 550}
            passed("Destinatário não autorizado rejeitado com SMTP 550")
            wait_for("Rejeição contabilizada no servidor", lambda: (get("/api/smtp")["stats"]["rejected"] or 0) > initial["rejected"])
            wait_for("Volume, entrega e histograma medidos", lambda: (get("/api/smtp")["stats"]["last_minute"] or 0) > 0 and get("/api/smtp")["stats"]["delivery_p95_ms"] is not None)
            docker("stop", "smtp-inbox")
            queued_ids = send(6)["ids"]
            wait_for("SMTP continua respondendo com receptor parado e fila ≥6", lambda: (get("/api/smtp")["stats"]["queue"] or 0) >= 6 and get("/api/smtp")["service"]["status"] == "warning")
            assert get("/api/smtp")["stats"]["delivery_percent"] < 100
            passed("Aceitação distinta da entrega durante falha do receptor")
            wait_for("Tentativas malsucedidas medidas", lambda: (get("/api/smtp")["stats"]["failed_attempts_per_minute"] or 0) > 0)
            wait_for("Aviso de fila persistido", lambda: incident("SMTPFilaElevada", "firing"))
            wait_for("E-mail de fila recebido em canal independente", lambda: email("SMTP com mensagens pendentes", "firing"))
            # Restart the MTA while the sink is down to prove durable pending data.
            accepted = get("/api/smtp")["stats"]["accepted"]
            docker("restart", "smtp")
            wait_for("Fila e contadores preservados no reinício do SMTP", lambda: get("/api/smtp")["stats"]["available"] and (get("/api/smtp")["stats"]["accepted"] or 0) >= accepted and (get("/api/smtp")["stats"]["queue"] or 0) >= 6)
            docker("start", "smtp-inbox")
            wait_for("Todas as mensagens pendentes chegaram ao receptor", lambda: delivered(queued_ids))
            wait_for("Fila esvaziou e SMTP voltou ao normal", lambda: get("/api/smtp")["stats"]["queue"] == 0 and get("/api/smtp")["service"]["status"] == "ok")
            wait_for("Aviso de fila resolvido", lambda: incident("SMTPFilaElevada", "resolved"))
            wait_for("E-mail de recuperação da fila recebido", lambda: email("SMTP com mensagens pendentes", "resolved"))
            docker("stop", "smtp")
            wait_for("Parada real do SMTP detectada", lambda: get("/api/smtp")["service"]["status"] == "critical")
            assert get("/api/smtp")["stats"]["queue"] is None
            passed("Valores antigos ocultados durante indisponibilidade")
            wait_for("HTTP, PostgreSQL e DNS continuam operacionais", lambda: all(get(path)["service"]["status"] == "ok" for path in ["/api/overview", "/api/postgres", "/api/dns"]))
            wait_for("Incidente crítico SMTP persistido", lambda: incident("SMTPIndisponivel", "firing"))
            wait_for("E-mail crítico recebido mesmo com SMTP monitorado parado", lambda: email("SMTP indisponível", "firing"))
            docker("start", "smtp")
            wait_for("SMTP e suas métricas recuperados", lambda: get("/api/smtp")["service"]["status"] == "ok" and get("/api/smtp")["stats"]["available"])
            wait_for("Incidente crítico resolvido", lambda: incident("SMTPIndisponivel", "resolved"))
            wait_for("E-mail de recuperação SMTP recebido", lambda: email("SMTP indisponível", "resolved"))
            report = {"passed": True, "checks": checks, "smtp": get("/api/smtp")}
            output = ROOT / "tmp" / "smtp-e2e-result.json"
            output.parent.mkdir(exist_ok=True)
            output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Resultado: {len(checks)} verificações passaram.", flush=True)
        finally:
            docker("start", "smtp", "smtp-inbox")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
