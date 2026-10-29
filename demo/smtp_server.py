"""Local SMTP MTA with a durable spool and a dedicated Mailpit receiver."""
import asyncio
import logging
import os
import smtplib
import sqlite3
from contextlib import asynccontextmanager

from aiosmtpd.controller import Controller
from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .smtp_queue import SMTPQueue
from .config import load_smtp_config


class QueueHandler:
    def __init__(self, queue):
        self.queue = queue

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        if address.lower() != "aluno@aularedes.test" or envelope.rcpt_tos:
            await asyncio.to_thread(self.queue.reject)
            return "550 5.1.1 Only aluno@aularedes.test is accepted"
        envelope.rcpt_tos.append(address)
        return "250 2.1.5 OK"

    async def handle_DATA(self, server, session, envelope):
        try:
            key = await asyncio.to_thread(self.queue.accept, envelope.mail_from, envelope.rcpt_tos[0], envelope.original_content)
        except (OverflowError, sqlite3.Error, OSError):
            return "452 4.3.1 Queue temporarily unavailable"
        return f"250 2.0.0 Queued as {key}"


def forward(item, host, port):
    try:
        with smtplib.SMTP(host, port, timeout=3) as smtp:
            smtp.sendmail(item["sender"], [item["recipient"]], item["content"])
        return "sent"
    except smtplib.SMTPRecipientsRefused as error:
        return "failed" if all(code >= 500 for code, _ in error.recipients.values()) else "retry"
    except smtplib.SMTPResponseException as error:
        return "failed" if error.smtp_code >= 500 else "retry"
    except (OSError, smtplib.SMTPException):
        return "retry"


async def deliver(queue, host, port):
    item = None
    outcome = None
    while True:
        try:
            if item is None:
                item = await asyncio.to_thread(queue.claim)
            if item:
                if outcome is None:
                    outcome = await asyncio.to_thread(forward, item, host, port)
                await asyncio.to_thread(queue.finish, item["id"], outcome)
                item = outcome = None
        except (OSError, sqlite3.Error):
            # Retain the claim and forwarding result across a transient DB error.
            # Retrying only finish() avoids sending an acknowledged message twice.
            logging.exception("SMTP spool unavailable; retrying")
        await asyncio.sleep(.5)


@asynccontextmanager
async def lifespan(app):
    config=load_smtp_config()
    queue = SMTPQueue(os.getenv("SMTP_QUEUE_PATH", "/data/smtp.sqlite"),capacity=config.queue_capacity)
    controller = Controller(QueueHandler(queue), hostname="0.0.0.0", port=2525,
                            data_size_limit=config.message_size_limit, enable_SMTPUTF8=False, timeout=30,
                            command_call_limit=100)
    controller.start()
    app.state.queue = queue
    task = asyncio.create_task(deliver(queue, "smtp-inbox", 1025))
    app.state.worker = task
    try:
        yield
    finally:
        controller.stop()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


app = FastAPI(lifespan=lifespan)


@app.get("/metrics")
def metrics():
    if app.state.worker.done():
        return Response(status_code=503)
    return Response(generate_latest(app.state.queue.registry), media_type=CONTENT_TYPE_LATEST)
