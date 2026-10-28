"""Uncached DNS checks against the laboratory's own authoritative server."""
import asyncio
import socket
import time

import dns.asyncquery
import dns.exception
import dns.message
import dns.name
import dns.rcode
import dns.rdatatype
from prometheus_client import CollectorRegistry
from prometheus_client.core import GaugeMetricFamily


def valid_answer(response, name, expected):
    question_name = dns.name.from_text(name)
    if response.rcode() != dns.rcode.NOERROR or len(response.question) != 1:
        return False
    question = response.question[0]
    if question.name != question_name or question.rdtype != dns.rdatatype.A:
        return False
    addresses = {record.address for rrset in response.answer
                 if rrset.name == question_name and rrset.rdtype == dns.rdatatype.A
                 for record in rrset}
    return addresses == {expected}


class DNSProbe:
    def __init__(self):
        self.snapshot = None
        self.registry = CollectorRegistry()
        self.registry.register(self)

    def collect(self):
        snapshot = self.snapshot
        if snapshot is None:
            return
        descriptions = {
            "success": "Correct A record returned over both UDP and TCP",
            "duration_seconds": "Maximum of the UDP and TCP query durations",
            "checked_at_seconds": "Time of the last completed DNS probe",
            "udp_success": "Correct record returned by UDP",
            "tcp_success": "Correct record returned by TCP",
            "udp_rcode": "Last UDP response code, omitted on timeout",
            "tcp_rcode": "Last TCP response code, omitted on timeout",
        }
        for name, description in descriptions.items():
            if name in snapshot:
                yield GaugeMetricFamily(f"dns_probe_{name}", description, value=snapshot[name])

    async def server_address(self, server, port):
        # Resolve only the Docker service name using the container resolver.
        # The monitored question is sent directly to the resulting server IP.
        result = await asyncio.get_running_loop().getaddrinfo(server, port, type=socket.SOCK_DGRAM)
        return result[0][4][0]

    async def query(self, address, port, name, expected, tcp=False):
        question = dns.message.make_query(name, "A")
        started = time.perf_counter()
        try:
            operation = dns.asyncquery.tcp if tcp else dns.asyncquery.udp
            response = await operation(question, address, port=port, timeout=1.5)
            return {"success": int(valid_answer(response, name, expected)),
                    "duration": time.perf_counter() - started, "rcode": response.rcode()}
        except (dns.exception.DNSException, OSError, TimeoutError):
            return {"success": 0}

    async def sample(self, server, port, name, expected):
        snapshot = {"success": 0, "udp_success": 0, "tcp_success": 0}
        try:
            async with asyncio.timeout(4):
                address = await self.server_address(server, port)
                udp, tcp = await asyncio.gather(self.query(address, port, name, expected), self.query(address, port, name, expected, tcp=True))
                snapshot.update(success=int(udp["success"] == 1 and tcp["success"] == 1), udp_success=udp["success"], tcp_success=tcp["success"])
                for protocol, result in [("udp", udp), ("tcp", tcp)]:
                    if "rcode" in result:
                        snapshot[f"{protocol}_rcode"] = result["rcode"]
                if snapshot["success"]:
                    snapshot["duration_seconds"] = max(udp["duration"], tcp["duration"])
        except (OSError, TimeoutError):
            pass
        snapshot["checked_at_seconds"] = time.time()
        self.snapshot = snapshot

    async def run(self, server, port, name, expected, interval=5):
        while True:
            await self.sample(server, port, name, expected)
            await asyncio.sleep(interval)


async def run_dns_workload(server, port):
    probe = DNSProbe()
    names = ["app.aularedes.test.", "db.aularedes.test.", "app.aularedes.test.", "ausente.aularedes.test."]
    iteration = 0
    while True:
        try:
            async with asyncio.timeout(3):
                address = await probe.server_address(server, port)
                question = dns.message.make_query(names[iteration % len(names)], "A")
                await dns.asyncquery.udp(question, address, port=port, timeout=1.5)
        except (dns.exception.DNSException, OSError, TimeoutError):
            pass
        iteration += 1
        await asyncio.sleep(2)
