import asyncio
import math
import time

import httpx


WINDOWS = {"15m": 900, "1h": 3600, "6h": 21600, "24h": 86400}
PROBE = 'probe_success{job="platform"}'
LATENCY = 'probe_duration_seconds{job="platform"}'
RPS = 'sum(rate(demo_http_requests_total{job="web-demo",path="/work"}[1m]))'
P95 = 'histogram_quantile(0.95, sum by(le)(rate(demo_http_duration_seconds_bucket{job="web-demo",path="/work"}[1m])))'
ERROR_RATE = '(sum(rate(demo_http_requests_total{job="web-demo",path="/work",status=~"4..|5.."}[1m])) or vector(0)) / sum(rate(demo_http_requests_total{job="web-demo",path="/work"}[1m])) * 100'


def finite(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError):
        return None


def scalar(data):
    result = data.get("result", [])
    return finite(result[0]["value"][1]) if result else None


def classify(success, latency, checked_at, now, warning_seconds=.5):
    if success is None or checked_at is None or now - checked_at > 20 or checked_at > now + 5:
        return "unknown"
    if success == 0:
        return "critical"
    if latency is None:
        return "unknown"
    return "warning" if latency > warning_seconds else "ok"


class PrometheusClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str):
        self.client = client
        self.base_url = base_url.rstrip("/")

    async def query(self, expression, start=None, end=None, step=None):
        path = "query_range" if start is not None else "query"
        params = {"query": expression}
        if start is not None:
            params.update(start=start, end=end, step=step)
        response = await self.client.get(f"{self.base_url}/api/v1/{path}", params=params)
        response.raise_for_status()
        result = response.json()
        if result.get("status") != "success" or "data" not in result:
            raise ValueError("Resposta inválida do Prometheus")
        return result["data"]

    async def overview(self, window):
        now = time.time()
        seconds = WINDOWS[window]
        expressions = [
            PROBE, LATENCY,
            'probe_checked_at_seconds{job="platform"}',
            RPS, P95, ERROR_RATE,
            f"avg_over_time({PROBE}[{window}]) * 100",
            'max(timestamp(demo_http_requests_total{job="web-demo",path="/work"}))',
        ]
        values = await asyncio.gather(*(self.query(q) for q in expressions))
        success, latency, checked_at, rps, p95, errors, availability, demo_at = map(scalar, values)
        status = classify(success, latency, checked_at, now)
        # Prometheus lookback can return old values after a target disappears.
        if demo_at is None or now - demo_at > 20:
            rps = p95 = errors = None
        if status == "unknown":
            latency = None
        series_data = await asyncio.gather(*(
            self.query(q, now - seconds, now, max(5, seconds // 180))
            for q in [RPS, P95]
        ))
        rows = {}
        for field, result in zip(["rps", "latency_ms"], series_data):
            for metric in result.get("result", []):
                for stamp, value in metric["values"]:
                    number = finite(value)
                    row = rows.setdefault(float(stamp), {"timestamp": float(stamp), "rps": None, "latency_ms": None})
                    row[field] = number * 1000 if field == "latency_ms" and number is not None else number
        return {
            "window": window,
            "generated_at": now,
            "service": {
                "id": "web-demo", "name": "Aplicação HTTP", "protocol": "HTTP", "target": "web-demo:8001",
                "status": status, "checked_at": checked_at,
                "latency_ms": latency * 1000 if latency is not None else None,
                "p95_ms": p95 * 1000 if p95 is not None else None,
                "rps": rps, "error_percent": errors, "availability_percent": availability,
            },
            "series": [rows[key] for key in sorted(rows)],
        }
