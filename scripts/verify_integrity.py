"""Local file-integrity E2E. Changes only allowlisted non-secret files and restores bytes."""
import hashlib
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
TEST_FILES={"http-runtime":"http.json","postgres-runtime":"postgres/postgresql.conf","dns-zone":"dns/db.aularedes.test","smtp-runtime":"smtp.json"}


def main():
    checks=[];changes={};started=datetime.now(timezone.utc)
    env=dict(line.split("=",1) for line in (ROOT/".env").read_text(encoding="utf-8").splitlines() if "=" in line and not line.lstrip().startswith("#"))
    with httpx.Client(timeout=8,trust_env=False) as client:
        authenticate(client)
        def passed(label):checks.append(label);print("PASS: "+label,flush=True)
        def get(path):
            response=client.get(BASE+path);response.raise_for_status();return response.json()
        def wait_for(label,predicate,timeout=120):
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                try:
                    if predicate():passed(label);return
                except httpx.HTTPError:pass
                time.sleep(2)
            raise AssertionError("Tempo esgotado: "+label)
        def overview():return get("/api/security/integrity")
        def approve(items):return client.post(BASE+"/api/security/integrity/approve",headers={"X-Lab-Token":env["LAB_TOKEN"]},json={"items":items})
        def mail():
            response=client.get("http://localhost:8025/api/v1/messages",params={"limit":200});response.raise_for_status();return response.json()["messages"]
        previous_mail={item["ID"] for item in mail()}
        def incidents(status):
            return {item["service"] for item in get("/api/incidents")["incidents"] if item["name"]=="ConfiguracaoAlterada" and item["status"]==status and datetime.fromisoformat(item["started_at"].replace("Z","+00:00"))>=started}
        def emails(status):
            messages=mail()
            return all(any(item["ID"] not in previous_mail and key in item["Subject"] and status in item["Subject"] for item in messages) for key in TEST_FILES)
        def restore():
            conflicts=[]
            for path,(original,payload) in changes.items():
                if not path.exists():conflicts.append(path.name);continue
                current=path.read_bytes()
                if current==payload:path.write_bytes(original)
                elif current!=original:conflicts.append(path.name)
            if conflicts:raise RuntimeError("Alteração concorrente preservada; restauração manual necessária: "+", ".join(conflicts))
        try:
            assert httpx.get(BASE+"/api/security/integrity",trust_env=False).status_code==401
            passed("Integridade exige sessão autenticada")
            wait_for("Oito arquivos reais legíveis",lambda:overview()["enabled"] and all(row["observed_sha256"] for row in overview()["files"]))
            rows=overview()["files"]
            assert len(rows)==8 and set(TEST_FILES)<=set(row["id"] for row in rows)
            # Only establish an absent first reference, and only when the container
            # observation matches the current trusted repository bytes. Never adopt
            # a divergence from an existing approved reference.
            pending=[]
            for row in rows:
                path=(ROOT/"infra"/row["path"]).resolve()
                assert path.is_relative_to((ROOT/"infra").resolve())
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                assert digest==row["observed_sha256"],"Container não está observando o arquivo atual do repositório"
                assert row["approved_sha256"] in (None,digest),"Referência divergente: revise manualmente antes da demonstração"
                if row["approved_sha256"] is None:pending.append({"file_id":row["id"],"observed_sha256":digest})
            passed("Hashes do container conferem com os bytes locais; referências existentes preservadas")
            body={"items":[{"file_id":rows[0]["id"],"observed_sha256":rows[0]["observed_sha256"]}]}
            assert client.post(BASE+"/api/security/integrity/approve",json=body).status_code==401
            passed("Aprovação exige token adicional do laboratório")
            if pending:approve(pending).raise_for_status()
            wait_for("Oito referências aprovadas e íntegras",lambda:all(row["status"]=="ok" for row in overview()["files"]))
            baseline={row["id"]:row["approved_sha256"] for row in overview()["files"]}
            assert approve([{"file_id":"http-runtime","observed_sha256":"0"*64}]).status_code==409
            passed("Hash não observado rejeitado sem alterar referência")
            for key,relative in TEST_FILES.items():
                path=(ROOT/"infra"/relative).resolve()
                assert path.is_relative_to((ROOT/"infra").resolve())
                original=path.read_bytes()
                assert hashlib.sha256(original).hexdigest()==baseline[key]
                suffix=b"\n \n" if path.suffix==".json" else b"\n; integrity demonstration\n" if key=="dns-zone" else b"\n# integrity demonstration\n"
                payload=original+suffix;changes[path]=(original,payload)
                assert path.read_bytes()==original
                path.write_bytes(payload)
            wait_for("Mudanças reais detectadas nos quatro serviços",lambda:sum(row["status"]=="changed" for row in overview()["files"] if row["id"] in TEST_FILES)==4)
            assert {row["id"]:row["approved_sha256"] for row in overview()["files"]}==baseline
            passed("Referências permanecem fixas durante as alterações")
            wait_for("Quatro incidentes de configuração persistidos",lambda:incidents("firing")=={"web-demo","postgres","dns","smtp"})
            wait_for("Quatro e-mails de alteração recebidos",lambda:emails("firing"))
            restore()
            wait_for("Bytes originais restaurados e oito arquivos íntegros",lambda:all(row["status"]=="ok" for row in overview()["files"]))
            wait_for("Quatro incidentes resolvidos",lambda:incidents("resolved")=={"web-demo","postgres","dns","smtp"})
            wait_for("Quatro e-mails de recuperação recebidos",lambda:emails("resolved"))
            before=overview();before_ids={item["id"] for item in before["events"]}
            subprocess.run(["docker","compose","restart","api"],cwd=ROOT,check=True,capture_output=True)
            wait_for("Referências preservadas após reiniciar API",lambda:all(row["status"]=="ok" for row in overview()["files"]))
            after=overview();assert {row["id"]:row["approved_sha256"] for row in after["files"]}==baseline
            assert {item["id"] for item in after["events"]}==before_ids
            passed("Reinício não duplica eventos nem redefine referências")
            wait_for("HTTP, SQL, DNS e SMTP operacionais ao final",lambda:all(get(path)["service"]["status"]=="ok" for path in ["/api/overview","/api/postgres","/api/dns","/api/smtp"]))
            report={"passed":True,"checks":checks,"integrity":after}
            output=ROOT/"tmp/integrity-e2e-result.json";output.parent.mkdir(exist_ok=True);output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
            print(f"Resultado: {len(checks)} verificações passaram.",flush=True)
        finally:
            try:restore()
            finally:client.post(BASE+"/api/auth/logout")


if __name__=="__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
