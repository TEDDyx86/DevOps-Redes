"""Bounded protocol workload, exclusively against configured local services."""
import asyncio
import copy
import smtplib
import socket
import time
import uuid

import dns.asyncquery
import dns.exception
import dns.message
import httpx
import psycopg

from .dns_probe import valid_answer
from .traffic_smtp import send_local_message


RATES = {"web-demo":5,"postgres":10,"dns":10,"smtp":1}


class TrafficLoad:
    def __init__(self, settings):
        self.settings = settings
        self.task = None
        self.job = {"status":"idle","services":{},"duration":0,"started_at":None,"ended_at":None}

    def overview(self):
        return copy.deepcopy(self.job)

    def start(self, service, duration):
        if self.task is not None and not self.task.done():
            raise ValueError("Já existe um teste de tráfego em execução.")
        if service not in {*RATES,"all"} or isinstance(duration,bool) or not isinstance(duration,int) or not 30<=duration<=90:
            raise ValueError("Alvo ou duração inválidos.")
        selected = list(RATES) if service=="all" else [service]
        configured = {"web-demo":bool(self.settings.demo_url),"postgres":bool(self.settings.postgres_workload_dsn),
                      "dns":bool(self.settings.dns_server),"smtp":bool(self.settings.smtp_host)}
        if not all(configured[item] for item in selected):
            raise ValueError("O serviço selecionado não está configurado neste laboratório.")
        self.job = {"id":uuid.uuid4().hex,"status":"running","duration":duration,"started_at":time.time(),"ended_at":None,
                    "services":{item:{"attempted":0,"successful":0,"failed":0,"cancelled":0,"rate_limit":RATES[item]} for item in selected}}
        self.task = asyncio.create_task(self.run(selected,duration))
        return self.overview()

    async def worker(self, service, duration):
        counts = self.job["services"][service]
        connection = None
        address = None
        settings = self.settings
        try:
            async with httpx.AsyncClient(timeout=3,trust_env=False) as client:
                for _ in range(RATES[service]*duration):
                    started = time.monotonic()
                    counts["attempted"] += 1
                    try:
                        async with asyncio.timeout(3):
                            if service=="web-demo":
                                response = await client.get(f"{settings.demo_url}/work")
                                response.raise_for_status()
                            elif service=="postgres":
                                if connection is None or connection.closed:
                                    connection = await psycopg.AsyncConnection.connect(settings.postgres_workload_dsn,autocommit=True,connect_timeout=2,options="-c statement_timeout=1500")
                                await connection.execute("SELECT 1")
                            elif service=="dns":
                                if address is None:
                                    result = await asyncio.get_running_loop().getaddrinfo(settings.dns_server,settings.dns_port,type=socket.SOCK_DGRAM)
                                    address = result[0][4][0]
                                answer = await dns.asyncquery.udp(dns.message.make_query(settings.dns_name,"A"),address,port=settings.dns_port,timeout=2)
                                if not valid_answer(answer,settings.dns_name,settings.dns_expected):
                                    raise ValueError("Resposta DNS diferente da esperada")
                            else:
                                await send_local_message(settings.smtp_host,settings.smtp_port)
                        counts["successful"] += 1
                    except asyncio.CancelledError:
                        counts["cancelled"] += 1
                        raise
                    except (OSError,TimeoutError,ValueError,httpx.HTTPError,psycopg.Error,dns.exception.DNSException,smtplib.SMTPException):
                        counts["failed"] += 1
                        if connection is not None:
                            await connection.close()
                            connection = None
                        address = None
                    await asyncio.sleep(max(0,1/RATES[service]-(time.monotonic()-started)))
        finally:
            if connection is not None:
                await connection.close()

    async def run(self, selected, duration):
        workers = [asyncio.create_task(self.worker(service,duration)) for service in selected]
        try:
            async with asyncio.timeout(duration):
                await asyncio.gather(*workers)
            self.job["status"] = "completed"
        except TimeoutError:
            self.job["status"] = "completed"
        except asyncio.CancelledError:
            self.job["status"] = "cancelled"
            raise
        except Exception:
            self.job["status"] = "failed"
            # No exception text is exposed: database connection errors can carry credentials.
        finally:
            for task in workers:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*workers,return_exceptions=True)
            self.job["ended_at"] = time.time()

    async def stop(self):
        if self.task is not None and not self.task.done():
            self.task.cancel()
            await asyncio.gather(self.task,return_exceptions=True)
        if self.job["status"] == "running":
            # A task cancelled before its first turn never enters run()/finally.
            self.job["status"] = "cancelled"
            self.job["ended_at"] = time.time()
        return self.overview()
