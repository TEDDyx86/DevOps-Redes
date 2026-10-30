"""Verify real local reports, alert delivery and optional collector outage; never inject findings."""
import argparse
import json
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path

import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.lab_session import authenticate
BASE="http://localhost:8000"
SERVICES={"web-demo","postgres","dns","smtp"}


class AnalysisChanged(Exception):
    """Retry the verification when a live report expires or changes between requests."""


def require_same_analysis(value,expected):
    current=next(item for item in value["services"] if item["id"]==expected["id"])
    fields=("image_id","scanned_at","db_built_at","counts")
    if current["status"]=="unknown" or current["counts"] is None or any(current.get(key)!=expected.get(key) for key in fields):
        raise AnalysisChanged()


def collect_pages(fetch,expected):
    findings=[];total=sum(expected["counts"].values())
    for page in range(1,max(1,(total+49)//50)+1):
        value=fetch(f'/api/security/vulnerabilities?service={expected["id"]}&page={page}')
        require_same_analysis(value,expected)
        data=value["findings"]
        assert data["total"]==total and len(data["items"])<=50
        findings+=data["items"]
    assert len(findings)==total
    return findings


def main(exercise_outage=False):
    checks=[];outage=False
    with httpx.Client(timeout=8,trust_env=False) as client:
        authenticate(client)
        def passed(label):checks.append(label);print("PASS: "+label,flush=True)
        def get(path):
            response=client.get(BASE+path);response.raise_for_status();return response.json()
        def wait_for(label,predicate,timeout=180):
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                try:
                    if predicate():passed(label);return
                except httpx.HTTPError:pass
                time.sleep(2)
            raise AssertionError("Tempo esgotado: "+label)
        def overview():return get("/api/security/vulnerabilities")
        def incidents():return get("/api/incidents")["incidents"]
        def emails():
            response=client.get("http://localhost:8025/api/v1/messages",params={"limit":200});response.raise_for_status();return response.json()["messages"]
        def monitor(option):
            subprocess.run([sys.executable,str(ROOT/"scripts/scan_vulnerabilities.py"),option],cwd=ROOT,check=True,capture_output=True,timeout=15)
        try:
            assert httpx.get(BASE+"/api/security/vulnerabilities",trust_env=False).status_code==401
            passed("Relatórios exigem login")
            assert client.get(BASE+"/api/security/vulnerabilities?service=external").status_code==422
            assert client.get(BASE+"/api/security/vulnerabilities?page=0").status_code==422
            assert client.post(BASE+"/api/security/vulnerabilities").status_code==405
            passed("Filtros fixos e ausência de execução do scanner pela API")
            wait_for("Quatro análises reais atuais",lambda:overview()["enabled"] and all(row["status"]!="unknown" for row in overview()["services"]),timeout=900)
            before=overview();rows={row["id"]:row for row in before["services"]}
            inventory=json.loads((ROOT/".runtime/vulnerabilities/inventory.json").read_text(encoding="utf-8"))
            assert set(rows)==SERVICES and inventory["ok"]
            for service,row in rows.items():
                assert row["image_id"]==inventory["services"][service]["image_id"]
                assert row["package_count"]>0 and row["scanned_at"] and row["db_built_at"]
                result=subprocess.run(["docker","compose","ps","-a","-q",service],cwd=ROOT,check=True,capture_output=True,text=True,timeout=10)
                observed=subprocess.run(["docker","inspect","--format","{{.Image}}",result.stdout.strip()],cwd=ROOT,check=True,capture_output=True,text=True,timeout=10).stdout.strip()
                assert row["image_id"]==observed
            passed("Identidade das quatro imagens confere com os containers e o inventário")
            assert rows["web-demo"]["image_id"]==rows["smtp"]["image_id"] and rows["web-demo"]["counts"]==rows["smtp"]["counts"]
            passed("Imagem compartilhada tem o mesmo resultado para HTTP e SMTP")
            def verify_reports():
                current={row["id"]:row for row in overview()["services"]}
                if any(row["counts"] is None for row in current.values()):return False
                try:
                    for service,row in current.items():
                        findings=collect_pages(get,row)
                        assert len({(item["id"],item["package"],item["package_type"],item["installed_version"]) for item in findings})==len(findings)
                        for severity,count in row["counts"].items():
                            value=get(f"/api/security/vulnerabilities?service={service}&severity={severity}")
                            require_same_analysis(value,row)
                            selected=value["findings"]
                            assert selected["total"]==count and all(item["severity"]==severity for item in selected["items"])
                except AnalysisChanged:return False
                rows.update(current)
                return True
            wait_for("Paginação, deduplicação e seis filtros conferem com todas as contagens",verify_reports)
            metrics=client.get(BASE+"/metrics").text
            lines=[line for line in metrics.splitlines() if line.startswith("security_vulnerability_findings{")]
            assert len(lines)==24 and all("CVE-" not in line and "sha256:" not in line and "package=" not in line for line in lines)
            passed("Métricas de achados têm cardinalidade fixa e não incluem CVEs ou hashes")
            expected={service:("VulnerabilidadeCritica" if row["counts"]["critical"] else "VulnerabilidadeAlta") for service,row in rows.items() if row["counts"]["critical"] or row["counts"]["high"]}
            wait_for("Incidentes compatíveis com os achados reais",lambda:all(any(item["name"]==name and item["service"]==service and item["status"]=="firing" for item in incidents()) for service,name in expected.items()))
            wait_for("E-mails locais dos achados reais recebidos",lambda:all(any("firing" in item["Subject"] and "Vulnerabilidade" in item["Subject"] and service in item["Subject"] for item in emails()) for service in expected))
            if exercise_outage:
                previous_mail={item["ID"] for item in emails()}
                monitor("--stop");outage=True
                wait_for("Inventário vencido oculta contagens atuais nos quatro serviços",lambda:all(row["status"]=="unknown" and row["counts"] is None for row in overview()["services"]),timeout=210)
                metrics=client.get(BASE+"/metrics").text
                assert not any(line.startswith("security_vulnerability_findings{") for line in metrics.splitlines())
                passed("Falha da análise omite achados atuais em vez de publicar zero")
                wait_for("Quatro incidentes de análise indisponível confirmados",lambda:all(any(item["name"]=="VulnerabilidadeAnaliseIndisponivel" and item["service"]==service and item["status"]=="firing" for item in incidents()) for service in SERVICES))
                wait_for("Quatro e-mails de análise indisponível recebidos",lambda:all(any(item["ID"] not in previous_mail and "firing" in item["Subject"] and "Análise de vulnerabilidades indisponível" in item["Subject"] and service in item["Subject"] for item in emails()) for service in SERVICES))
                monitor("--background");outage=False
                wait_for("Relatórios reais recuperados com as mesmas contagens",lambda:all(row["counts"]==rows[row["id"]]["counts"] for row in overview()["services"]))
                wait_for("Avisos de análise indisponível resolvidos",lambda:not any(item["name"]=="VulnerabilidadeAnaliseIndisponivel" and item["status"]=="firing" for item in incidents()))
                wait_for("Quatro e-mails de recuperação da análise recebidos",lambda:all(any(item["ID"] not in previous_mail and "resolved" in item["Subject"] and "Análise de vulnerabilidades indisponível" in item["Subject"] and service in item["Subject"] for item in emails()) for service in SERVICES))
            before_ids={row["id"]:row["image_id"] for row in overview()["services"]}
            subprocess.run(["docker","compose","restart","api"],cwd=ROOT,check=True,capture_output=True,timeout=60)
            wait_for("Relatórios preservados após restart da API",lambda:all(row["counts"]==rows[row["id"]]["counts"] and row["image_id"]==before_ids[row["id"]] for row in overview()["services"]))
            wait_for("Quatro protocolos operacionais e oito configurações íntegras",lambda:all(get(path)["service"]["status"]=="ok" for path in ["/api/overview","/api/postgres","/api/dns","/api/smtp"]) and all(row["status"]=="ok" for row in get("/api/security/integrity")["files"]))
            report={"passed":True,"checks":checks,"outage_exercised":exercise_outage,"vulnerabilities":overview()}
            output=ROOT/"tmp/vulnerabilities-e2e-result.json";output.parent.mkdir(exist_ok=True);output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
            print(f"Resultado: {len(checks)} verificações passaram.",flush=True)
        finally:
            if outage:monitor("--background")
            # A cleanup timeout must not hide the verification that actually failed.
            with suppress(httpx.HTTPError):
                client.post(BASE+"/api/auth/logout")


if __name__=="__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--exercise-outage",action="store_true")
    main(parser.parse_args().exercise_outage)
