"""Small cancellable SMTP client for the fixed local traffic demonstration."""
import asyncio
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import formatdate,make_msgid


async def send_local_message(host,port):
    writer = None
    try:
        reader,writer = await asyncio.open_connection(host,port)
        async def reply(expected):
            for _ in range(50):
                line = await reader.readline()
                if len(line)<4 or len(line)>1024 or not line[:3].isdigit() or line[3:4] not in {b" ",b"-"}:
                    raise ValueError("Invalid local SMTP response")
                if int(line[:3]) != expected:
                    raise ValueError("Local SMTP refused the operation")
                if line[3:4]==b" ":
                    return
            raise ValueError("Local SMTP response exceeded the line limit")
        async def command(value,expected):
            writer.write(value+b"\r\n");await writer.drain();await reply(expected)
        await reply(220)
        await command(b"EHLO aularedes.test",250)
        await command(b"MAIL FROM:<laboratorio@aularedes.test>",250)
        await command(b"RCPT TO:<aluno@aularedes.test>",250)
        await command(b"DATA",354)
        message=EmailMessage(policy=SMTP)
        message["From"]="laboratorio@aularedes.test"
        message["To"]="aluno@aularedes.test"
        message["Subject"]="AulaRedes: local traffic demonstration"
        message["Message-ID"]=make_msgid(domain="aularedes.test")
        message["Date"]=formatdate(usegmt=True)
        message.set_content("Controlled SMTP traffic, delivered only to the local laboratory.")
        content=message.as_bytes().replace(b"\r\n.",b"\r\n..")
        writer.write(content.rstrip(b"\r\n")+b"\r\n.\r\n");await writer.drain()
        await reply(250)
    finally:
        if writer is not None:
            writer.close()
            try:
                async with asyncio.timeout(1):
                    await writer.wait_closed()
            except (TimeoutError,OSError):
                pass
