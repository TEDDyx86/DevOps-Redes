"""Read-only SQL collector. Snapshot publication is atomic between scrapes."""
import asyncio
import logging
import time

import psycopg
from prometheus_client import CollectorRegistry
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily


logger = logging.getLogger(__name__)
STATISTICS_SQL = """
SELECT numbackends, xact_commit, xact_rollback,
       pg_database_size(current_database()),
       current_setting('max_connections')::int,
       (SELECT COALESCE(sum(calls), 0) FROM pg_stat_statements
        WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
          AND userid = (SELECT oid FROM pg_roles WHERE rolname = 'lab_workload'))
FROM pg_stat_database WHERE datname = current_database()
"""
GAUGES = {
    "probe_success": "Success of the last connection and SELECT 1",
    "probe_duration_seconds": "Duration of connection and SELECT 1",
    "probe_checked_at_seconds": "Unix time of the last completed SQL probe",
    "stats_success": "Success of the latest statistics collection",
    "stats_checked_at_seconds": "Unix time of the latest successful statistics collection",
    "connections": "Open backends in the monitored database",
    "connections_limit": "Configured max_connections for this dedicated cluster",
    "database_bytes": "Size of the monitored database in bytes",
}
COUNTERS = {
    "commits": "Committed database transactions since PostgreSQL statistics reset",
    "rollbacks": "Rolled back database transactions since PostgreSQL statistics reset",
    "workload_statements": "SQL commands executed by lab_workload since pg_stat_statements reset",
}


class PostgresProbe:
    def __init__(self):
        self.snapshot = None
        self.registry = CollectorRegistry()
        self.registry.register(self)

    def collect(self):
        snapshot = self.snapshot
        if snapshot is None:
            return
        for name, description in GAUGES.items():
            if name in snapshot:
                yield GaugeMetricFamily(f"postgres_{name}", description, value=snapshot[name])
        for name, description in COUNTERS.items():
            if name in snapshot:
                yield CounterMetricFamily(f"postgres_{name}", description, value=snapshot[name])

    async def sample(self, dsn):
        snapshot = {"probe_success": 0, "stats_success": 0}
        started = time.perf_counter()
        connection = None
        try:
            async with asyncio.timeout(3):
                connection = await psycopg.AsyncConnection.connect(
                    dsn, autocommit=True, connect_timeout=2,
                    options="-c statement_timeout=2500 -c default_transaction_read_only=on",
                )
                await connection.execute("SELECT 1")
                snapshot.update(probe_success=1, probe_duration_seconds=time.perf_counter() - started)
            try:
                async with asyncio.timeout(3):
                    cursor = await connection.execute(STATISTICS_SQL)
                    row = await cursor.fetchone()
                    if row is not None:
                        connections, commits, rollbacks, size, limit, queries = row
                        snapshot.update(connections=connections, commits=commits, rollbacks=rollbacks,
                                        database_bytes=size, connections_limit=limit,
                                        workload_statements=float(queries), stats_success=1,
                                        stats_checked_at_seconds=time.time())
            except (psycopg.Error, TimeoutError):
                # A slow statistics query cannot undo a successful SELECT 1.
                logger.warning("Estatísticas PostgreSQL indisponíveis; verifique extensão e permissões.")
        except (psycopg.Error, TimeoutError):
            logger.info("Sonda PostgreSQL sem resposta")
        finally:
            if connection is not None:
                await connection.close()
        snapshot["probe_checked_at_seconds"] = time.time()
        self.snapshot = snapshot

    async def run(self, dsn, interval=5):
        while True:
            await self.sample(dsn)
            await asyncio.sleep(interval)


async def run_workload(dsn, interval=2):
    """Real bounded reads/writes; every fifth transaction is deliberately rolled back."""
    iteration = 0
    while True:
        try:
            async with await psycopg.AsyncConnection.connect(dsn, connect_timeout=2, options="-c statement_timeout=2500") as connection:
                while True:
                    iteration += 1
                    await connection.execute("SELECT value FROM lab_items WHERE id = %s", ((iteration % 1000) + 1,))
                    await connection.execute("UPDATE lab_items SET value = value + 1 WHERE id = %s", ((iteration % 1000) + 1,))
                    if iteration % 5 == 0:
                        await connection.rollback()
                    else:
                        await connection.commit()
                    await asyncio.sleep(interval)
        except (psycopg.Error, OSError):
            logger.info("Carga SQL aguardando reconexão ao laboratório")
            await asyncio.sleep(interval)
