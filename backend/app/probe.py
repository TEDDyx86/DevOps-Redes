import asyncio
import logging
import time

import httpx
from prometheus_client import CollectorRegistry, Gauge


logger = logging.getLogger(__name__)


class Probe:
    def __init__(self):
        self.registry = CollectorRegistry()
        self.success = Gauge("probe_success", "Last HTTP health probe success", registry=self.registry)
        self.duration = Gauge("probe_duration_seconds", "HTTP health probe duration", registry=self.registry)
        self.checked_at = Gauge("probe_checked_at_seconds", "Time of last completed probe", registry=self.registry)
        self.ready = False

    async def run(self, client, base_url, interval):
        while True:
            started = time.perf_counter()
            success = 0
            try:
                response = await client.get(f"{base_url}/health", timeout=3)
                success = int(200 <= response.status_code < 300)
            except httpx.HTTPError:
                logger.info("Sonda HTTP sem resposta")
            self.success.set(success)
            self.duration.set(time.perf_counter() - started)
            self.checked_at.set(time.time())
            self.ready = True
            # Actual laboratory traffic, not invented metrics. Kept separate from the health probe.
            try:
                await client.get(f"{base_url}/work", timeout=3)
            except httpx.HTTPError:
                pass
            await asyncio.sleep(interval)
