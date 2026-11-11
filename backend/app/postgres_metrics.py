import asyncio
import time

from .metrics import WINDOWS, classify, finite, scalar


PREFIX = '{job="platform"}'


class PostgresMetrics:
    def __init__(self, prometheus):
        self.prometheus = prometheus

    async def overview(self, window):
        now = time.time()
        qps = f"rate(postgres_workload_statements_total{PREFIX}[1m])"
        latency_query = f"postgres_probe_duration_seconds{PREFIX}"
        growth_query = f"rate(postgres_database_bytes{PREFIX}[1h]) * 86400"
        read_latency_query = (f"rate(postgres_io_read_time_milliseconds_total{PREFIX}[1m]) / "
                              f"rate(postgres_io_reads_total{PREFIX}[1m])")
        write_latency_query = (f"rate(postgres_io_write_time_milliseconds_total{PREFIX}[1m]) / "
                               f"rate(postgres_io_writes_total{PREFIX}[1m])")
        expressions = [
            f"postgres_probe_success{PREFIX}", latency_query,
            f"postgres_probe_checked_at_seconds{PREFIX}",
            f"postgres_stats_success{PREFIX}", f"postgres_stats_checked_at_seconds{PREFIX}",
            f"postgres_connections{PREFIX}", f"postgres_connections_limit{PREFIX}",
            f"postgres_database_bytes{PREFIX}", f"rate(postgres_commits_total{PREFIX}[1m])",
            f"rate(postgres_rollbacks_total{PREFIX}[1m])", qps,
            f"avg_over_time(postgres_probe_success{PREFIX}[{window}]) * 100",
            f"postgres_connections_active{PREFIX}", f"postgres_connections_idle{PREFIX}",
            f"postgres_slow_statements{PREFIX}", growth_query,
            read_latency_query, write_latency_query,
        ]
        values = await asyncio.gather(*(self.prometheus.query(q) for q in expressions))
        (success, latency, checked, stats_ok, stats_at, connections, limit, size, commits, rollbacks, queries,
         availability, active, idle, slow, growth, disk_read, disk_write) = map(scalar, values)
        status = classify(success, latency, checked, now)
        stats_available = success == 1 and status != "unknown" and stats_ok == 1 and stats_at is not None and 0 <= now - stats_at <= 20
        if not stats_available:
            connections = limit = size = commits = rollbacks = queries = None
            active = idle = slow = growth = disk_read = disk_write = None
        elif connections is not None and limit and connections / limit > .8:
            status = "warning"
        if success != 1 or status == "unknown":
            latency = None
        seconds = WINDOWS[window]
        ranges = await asyncio.gather(*(
            self.prometheus.query(q, now - seconds, now, max(5, seconds // 180))
            for q in [f"({qps}) and on(job, instance) (postgres_probe_success{PREFIX} == 1)", latency_query]
        ))
        rows = {}
        for field, result in zip(["qps", "latency_ms"], ranges):
            for metric in result.get("result", []):
                for stamp, value in metric["values"]:
                    number = finite(value)
                    row = rows.setdefault(float(stamp), {"timestamp": float(stamp), "qps": None, "latency_ms": None})
                    row[field] = number * 1000 if field == "latency_ms" and number is not None else number
        return {
            "window": window, "generated_at": now,
            "service": {"id": "postgres", "name": "PostgreSQL", "protocol": "SQL", "target": "postgres:5432/lab_network",
                        "status": status, "checked_at": checked,
                        "latency_ms": latency * 1000 if latency is not None else None,
                        "availability_percent": availability},
            "stats": {"available": stats_available, "connections": connections, "connection_limit": limit,
                      "database_bytes": size, "commits_per_second": commits,
                      "rollbacks_per_second": rollbacks, "qps": queries,
                      "connections_active": active, "connections_idle": idle,
                      "slow_statements": slow, "growth_bytes_per_day": growth,
                      "disk_read_ms": disk_read, "disk_write_ms": disk_write},
            "series": [rows[key] for key in sorted(rows)],
        }
