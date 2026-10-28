import asyncio
import time

import dns.rcode

from .metrics import WINDOWS, classify, finite, scalar


PROBE = 'dns_probe_success{job="platform"}'
DURATION = 'dns_probe_duration_seconds{job="platform"}'
QPS = 'sum(rate(coredns_dns_requests_total{job="dns"}[1m]))'
ERROR_PERCENT = '(sum(rate(coredns_dns_responses_total{job="dns",rcode=~"SERVFAIL|REFUSED|FORMERR|NOTIMP"}[1m])) or vector(0)) / sum(rate(coredns_dns_responses_total{job="dns"}[1m])) * 100'
NXDOMAIN_PERCENT = '(sum(rate(coredns_dns_responses_total{job="dns",rcode="NXDOMAIN"}[1m])) or vector(0)) / sum(rate(coredns_dns_responses_total{job="dns"}[1m])) * 100'
SERVER_P95 = 'histogram_quantile(0.95, sum by(le)(rate(coredns_dns_request_duration_seconds_bucket{job="dns"}[1m])))'


def rcode_text(value):
    return dns.rcode.to_text(int(value)) if value is not None and value.is_integer() and 0 <= value <= 4095 else None


def merge_series(ranges, start, end, step):
    if not any(metric.get("values") for result in ranges for metric in result.get("result", [])):
        return []
    # Seed the complete query grid so missing samples break the plotted line.
    # Without explicit nulls, a chart joins pre-outage and post-outage samples.
    start_ms, end_ms, step_ms = round(start * 1000), round(end * 1000), step * 1000
    rows = {stamp: {"timestamp": stamp / 1000, "qps": None, "latency_ms": None}
            for stamp in range(start_ms, end_ms + 1, step_ms)}
    for field, result in zip(["qps", "latency_ms"], ranges):
        for metric in result.get("result", []):
            for stamp, value in metric["values"]:
                key = round(float(stamp) * 1000)
                number = finite(value)
                if key in rows:
                    rows[key][field] = number * 1000 if field == "latency_ms" and number is not None else number
    return [rows[key] for key in sorted(rows)]


class DNSMetrics:
    def __init__(self, prometheus, name="app.aularedes.test.", expected="192.0.2.10"):
        self.prometheus = prometheus
        self.name = name
        self.expected = expected

    async def overview(self, window):
        now = time.time()
        expressions = [PROBE, DURATION, 'dns_probe_checked_at_seconds{job="platform"}',
                       'dns_probe_udp_success{job="platform"}', 'dns_probe_tcp_success{job="platform"}',
                       'dns_probe_udp_rcode{job="platform"}', 'dns_probe_tcp_rcode{job="platform"}',
                       'up{job="dns"}', 'timestamp(up{job="dns"})', QPS, ERROR_PERCENT, NXDOMAIN_PERCENT, SERVER_P95,
                       f"avg_over_time({PROBE}[{window}]) * 100"]
        results = await asyncio.gather(*(self.prometheus.query(query) for query in expressions))
        success, duration, checked, udp, tcp, udp_rcode, tcp_rcode, native_up, native_at, qps, errors, nxdomain, p95, availability = map(scalar, results)
        status = classify(success, duration, checked, now, warning_seconds=.1)
        fresh = checked is not None and 0 <= now - checked <= 20
        stats_available = success == 1 and fresh and native_up == 1 and native_at is not None and 0 <= now - native_at <= 20
        if not stats_available:
            qps = errors = nxdomain = p95 = None
        elif errors is not None and errors > 10:
            status = "warning"
        if not fresh:
            udp = tcp = udp_rcode = tcp_rcode = None
        if success != 1 or not fresh:
            duration = None
        seconds = WINDOWS[window]
        end = round(now, 3)
        start = round(end - seconds, 3)
        step = max(5, seconds // 180)
        ranges = await asyncio.gather(*(
            self.prometheus.query(query, start, end, step)
            for query in [f'({QPS}) and on() (min(up{{job="dns"}}) == 1)', DURATION]
        ))
        return {
            "window": window, "generated_at": now,
            "service": {"id": "dns", "name": "DNS", "protocol": "DNS", "target": "dns:1053 / aularedes.test",
                        "status": status, "checked_at": checked, "latency_ms": duration * 1000 if duration is not None else None,
                        "availability_percent": availability},
            "question": {"name": self.name, "type": "A", "expected": self.expected},
            "stats": {"available": stats_available, "udp_success": udp == 1 if udp is not None else None,
                      "tcp_success": tcp == 1 if tcp is not None else None,
                      "udp_rcode": rcode_text(udp_rcode), "tcp_rcode": rcode_text(tcp_rcode),
                      "qps": qps, "server_error_percent": errors, "nxdomain_percent": nxdomain,
                      "server_p95_ms": p95 * 1000 if p95 is not None else None},
            "series": merge_series(ranges, start, end, step),
        }
