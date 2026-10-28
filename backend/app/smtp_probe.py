import asyncio
import smtplib
import time
from email.message import EmailMessage
from email.utils import make_msgid

from prometheus_client import CollectorRegistry
from prometheus_client.core import GaugeMetricFamily


def check(host, port):
    started = time.perf_counter()
    try:
        with smtplib.SMTP(host, port, timeout=2) as smtp:
            if smtp.ehlo()[0] != 250 or smtp.noop()[0] != 250:
                return {"success": 0}
        return {"success": 1, "duration_seconds": time.perf_counter() - started}
    except (OSError, smtplib.SMTPException):
        return {"success": 0}


class SMTPProbe:
    def __init__(self):
        self.snapshot = None
        self.registry = CollectorRegistry()
        self.registry.register(self)

    def collect(self):
        snapshot = self.snapshot
        if snapshot:
            for key, value in snapshot.items():
                yield GaugeMetricFamily(f"smtp_probe_{key}", key, value=value)

    async def run(self, host, port):
        while True:
            result = await asyncio.to_thread(check, host, port)
            self.snapshot = {**result, "checked_at_seconds": time.time()}
            await asyncio.sleep(5)


def send_message(host, port):
    message = EmailMessage()
    message["From"] = "laboratorio@aularedes.test"
    message["To"] = "aluno@aularedes.test"
    message["Subject"] = "AulaRedes: tráfego SMTP de laboratório"
    message["Message-ID"] = make_msgid(domain="aularedes.test")
    message.set_content("Mensagem local gerada a cada 15 segundos para medir a entrega SMTP.")
    with smtplib.SMTP(host, port, timeout=3) as smtp:
        smtp.send_message(message)


async def run_smtp_workload(host, port):
    while True:
        try:
            await asyncio.to_thread(send_message, host, port)
        except (OSError, smtplib.SMTPException):
            pass
        await asyncio.sleep(15)
