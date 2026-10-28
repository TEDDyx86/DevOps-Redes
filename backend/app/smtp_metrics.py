import asyncio
import time

from .metrics import WINDOWS, classify, scalar
from .dns_metrics import merge_series


PROBE = 'smtp_probe_success{job="platform"}'
DURATION = 'smtp_probe_duration_seconds{job="platform"}'
VOLUME = 'rate(smtp_accepted_total{job="smtp"}[1m]) * 60'
P95 = 'histogram_quantile(0.95, sum by(le)(rate(smtp_delivery_latency_seconds_bucket{job="smtp"}[1m])))'
FIELDS = {
    "queue": "smtp_queue_messages", "accepted": "smtp_accepted_total", "delivered": "smtp_delivered_total",
    "failed": "smtp_failed_total", "rejected": "smtp_rejected_recipients_total",
    "last_minute": "smtp_accepted_last_minute", "last_hour": "smtp_accepted_last_hour",
}


class SMTPMetrics:
    def __init__(self, prometheus):
        self.prometheus = prometheus

    async def overview(self, window):
        now = time.time()
        queries = [PROBE, DURATION, 'smtp_probe_checked_at_seconds{job="platform"}',
                   'up{job="smtp"}', 'timestamp(up{job="smtp"})',
                   *[f'{metric}{{job="smtp"}}' for metric in FIELDS.values()],
                   'rate(smtp_delivery_attempts_total{job="smtp",outcome="failed"}[1m]) * 60',
                   P95, f"avg_over_time({PROBE}[{window}]) * 100"]
        values = list(map(scalar, await asyncio.gather(*(self.prometheus.query(q) for q in queries))))
        success, duration, checked, native_up, native_at = values[:5]
        status = classify(success, duration, checked, now)
        # A scrape may complete during the parallel queries, just after `now`.
        # Match classify()'s bounded clock tolerance instead of hiding fresh data.
        fresh = checked is not None and -5 <= now - checked <= 20
        available = success == 1 and fresh and native_up == 1 and native_at is not None and -5 <= now-native_at <= 20
        stats = {key: value if available else None for key, value in zip(FIELDS, values[5:12])}
        stats["available"] = available
        stats["failed_attempts_per_minute"] = values[12] if available else None
        stats["delivery_p95_ms"] = values[13] * 1000 if available and values[13] is not None else None
        stats["delivery_percent"] = stats["delivered"] / stats["accepted"] * 100 if stats["accepted"] else None
        if available and stats["queue"] is not None and stats["queue"] >= 5:
            status = "warning"
        if success != 1 or not fresh:
            duration = None
        seconds = WINDOWS[window]
        end = round(now, 3)
        start, step = round(end-seconds, 3), max(5, seconds//180)
        ranges = await asyncio.gather(*(self.prometheus.query(f'({q}) and on() (min(up{{job="smtp"}}) == 1)', start, end, step) for q in [VOLUME, P95]))
        series = [{"timestamp": row["timestamp"], "messages_per_minute": row["qps"], "latency_ms": row["latency_ms"]}
                  for row in merge_series(ranges, start, end, step)]
        return {"window": window, "generated_at": now,
                "service": {"id": "smtp", "name": "SMTP", "protocol": "SMTP", "target": "smtp:2525",
                            "status": status, "checked_at": checked,
                            "latency_ms": duration*1000 if duration is not None else None,
                            "availability_percent": values[14]}, "stats": stats, "series": series}
