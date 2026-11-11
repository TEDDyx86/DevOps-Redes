"""Demonstrate service authentication failure counting on the monitored web-demo.

Sends repeated POST /mode requests with an invalid token (expected 401) and
prints the resulting counter from the service /metrics endpoint. No synthetic
data is published to Prometheus; the counter belongs to the web-demo job.
"""
import argparse
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8001"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempts", type=int, default=6)
    arguments = parser.parse_args()

    codes = []
    for _ in range(arguments.attempts):
        request = urllib.request.Request(
            f"{BASE}/mode",
            data=b'{"mode":"slow"}',
            headers={"X-Lab-Token": "token-invalido-propositado", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                codes.append(response.status)
        except urllib.error.HTTPError as error:
            codes.append(error.code)
    print("Códigos HTTP:", " ".join(str(code) for code in codes))

    metrics = urllib.request.urlopen(f"{BASE}/metrics", timeout=5).read().decode()
    for line in metrics.splitlines():
        if line.startswith("demo_auth_attempts_total{") and 'result="failed"' in line:
            print("Contador após as tentativas:", line)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
