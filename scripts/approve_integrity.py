"""Approve observed configuration hashes that match trusted repository bytes.

Used after intentional edits to monitored files in infra/. Never adopts a
divergence: approval only proceeds when the container observation equals the
current repository bytes. Requires an authenticated session and LAB_TOKEN.
"""
import hashlib
import json
import sys
from pathlib import Path

import httpx
from lab_session import authenticate

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://localhost:8000"


def main():
    env = dict(line.split("=", 1) for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
               if "=" in line and not line.lstrip().startswith("#"))
    with httpx.Client(timeout=8, trust_env=False) as client:
        authenticate(client)
        overview = client.get(BASE + "/api/security/integrity").json()
        pending = []
        for row in overview["files"]:
            path = (ROOT / "infra" / row["path"]).resolve()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if row["approved_sha256"] == digest:
                continue
            if row["observed_sha256"] is None or row["observed_sha256"] != digest:
                print(f"IGNORADO {row['id']}: container não observa os bytes atuais do repositório.", flush=True)
                continue
            pending.append({"file_id": row["id"], "observed_sha256": digest})
        if not pending:
            print("Nada a aprovar; todas as referências conferem com o repositório.", flush=True)
            return
        response = client.post(BASE + "/api/security/integrity/approve",
                               headers={"X-Lab-Token": env["LAB_TOKEN"]}, json={"items": pending})
        response.raise_for_status()
        after = client.get(BASE + "/api/security/integrity").json()
        approved = [row["id"] for row in after["files"] if row["status"] == "ok"]
        print(f"Aprovados e íntegros: {', '.join(approved)}", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
