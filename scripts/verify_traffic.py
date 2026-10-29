"""Bounded real traffic demonstration. Never changes external targets or secrets."""
import json
import subprocess
import sys
import time
from datetime import datetime,timezone
from pathlib import Path

import httpx
from lab_session import authenticate


ROOT=Path(__file__).resolve().parents[1]
BASE="http://localhost:8000"
SERVICES={"web-demo","postgres","dns","smtp"}


def main():
    checks=[]
    started=datetime.now(timezone.utc)
    env=dict(line.split("=",1) for line in (ROOT/".env").read_text(encoding="utf-8").splitlines() if "=" in line and not line.lstrip().startswith("#"))
    with httpx.Client(timeout=8,trust_env=False) as client:
        authenticate(client)
        def passed(label):
            checks.append(label);print("PASS: "+label,flush=True)
        def get(path):
            response=client.get(BASE+path);response.raise_for_status();return response.json()
        def wait_for(label,predicate,timeout=120):
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                try:
                    if predicate():passed(label);return
                except httpx.HTTPError:
                    pass
                time.sleep(2)
            raise AssertionError("Tempo esgotado: "+label)
        def rows():return get("/api/security/traffic")["services"]
        def request(method,body=None):
            return client.request(method,BASE+"/api/lab/traffic",headers={"X-Lab-Token":env["LAB_TOKEN"]},json=body)
        def mail():
            response=client.get("http://localhost:8025/api/v1/messages",params={"limit":200});response.raise_for_status();return response.json()["messages"]
        previous_mail={item["ID"] for item in mail()}
        def incidents(status):
            return {item["service"] for item in get("/api/incidents")["incidents"] if item["name"]=="TrafegoAnormal" and item["status"]==status and datetime.fromisoformat(item["started_at"].replace("Z","+00:00"))>=started}
        def emails(status):
            return all(any(item["ID"] not in previous_mail and "acima da refer" in item["Subject"] and service in item["Subject"] and status in item["Subject"] for item in mail()) for service in SERVICES)
        try:
            assert httpx.get(BASE+"/api/security/traffic",trust_env=False).status_code==401
            passed("Tabela de tráfego protegida por login")
            assert client.post(BASE+"/api/lab/traffic",json={"service":"all","duration":90}).status_code==401
            passed("Iniciar carga exige token adicional do laboratório")
            wait_for("Quatro referências prontas com volume habitual",lambda:all(row["status"]=="normal" for row in rows()),timeout=240)
            baseline={row["id"]:row["baseline"] for row in rows()}
            for row in rows():
                assert row["rate"] is not None and row["threshold"]>=row["baseline"]*3
            passed("Taxas reais e limiares por serviço disponíveis")
            response=request("POST",{"service":"web-demo","duration":30});response.raise_for_status()
            assert request("POST",{"service":"web-demo","duration":30}).status_code==409
            passed("Segundo job simultâneo rejeitado")
            response=request("DELETE");response.raise_for_status();assert response.json()["status"]=="cancelled"
            passed("Cancelamento do job confirmado")
            response=request("POST",{"service":"all","duration":90});response.raise_for_status()
            assert set(response.json()["services"])==SERVICES
            passed("Carga real iniciada com alvos e duração limitados")
            wait_for("Taxas dos quatro protocolos excederam seus limiares",lambda:all(row["status"]=="anomalous" for row in rows()),timeout=100)
            assert {row["id"]:row["baseline"] for row in rows()}==baseline
            passed("Referências permaneceram fixas durante o pico")
            assert client.post(BASE+"/api/security/traffic/calibrate",headers={"X-Lab-Token":env["LAB_TOKEN"]},json={"service":"dns"}).status_code==409
            passed("Recalibração bloqueada durante a demonstração")
            wait_for("Quatro incidentes de tráfego persistidos",lambda:incidents("firing")==SERVICES)
            wait_for("Quatro e-mails de alerta de tráfego recebidos",lambda:emails("firing"))
            wait_for("Carga encerrou automaticamente",lambda:get("/api/lab/traffic")["status"]=="completed")
            job=get("/api/lab/traffic")
            for counts in job["services"].values():
                assert 0<counts["successful"]<=counts["attempted"]<=counts["rate_limit"]*90
                assert counts["attempted"]==counts["successful"]+counts["failed"]+counts["cancelled"]
            passed("Operações reais contadas dentro do teto por serviço")
            wait_for("Taxas voltaram ao volume normal sem alterar referências",lambda:all(row["status"]=="normal" for row in rows()))
            assert {row["id"]:row["baseline"] for row in rows()}==baseline
            wait_for("Quatro incidentes de tráfego resolvidos",lambda:incidents("resolved")==SERVICES)
            wait_for("Quatro e-mails de recuperação recebidos",lambda:emails("resolved"))
            subprocess.run(["docker","compose","restart","api"],cwd=ROOT,check=True,capture_output=True)
            wait_for("Referências recuperadas após reiniciar a API",lambda:all(row["status"]=="normal" for row in rows()))
            assert {row["id"]:row["baseline"] for row in rows()}==baseline
            passed("Persistência das quatro referências confirmada")
            wait_for("HTTP, SQL, DNS e SMTP operacionais ao final",lambda:all(get(path)["service"]["status"]=="ok" for path in ["/api/overview","/api/postgres","/api/dns","/api/smtp"]))
            report={"passed":True,"checks":checks,"traffic":get("/api/security/traffic"),"job":job}
            output=ROOT/"tmp/traffic-e2e-result.json";output.parent.mkdir(exist_ok=True);output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
            print(f"Resultado: {len(checks)} verificações passaram.",flush=True)
        finally:
            try:request("DELETE")
            finally:client.post(BASE+"/api/auth/logout")


if __name__=="__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
