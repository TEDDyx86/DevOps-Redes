import os
from pathlib import Path

from pydantic import BaseModel,ConfigDict,Field


class HTTPConfig(BaseModel):
    model_config=ConfigDict(extra="forbid",frozen=True)
    work_delay_seconds: float=Field(default=.035,ge=0,le=2)
    slow_delay_seconds: float=Field(default=.85,ge=0,le=2)
    message: str=Field(default="Requisição real processada",min_length=1,max_length=200)


class SMTPConfig(BaseModel):
    model_config=ConfigDict(extra="forbid",frozen=True)
    message_size_limit: int=Field(default=65536,ge=1024,le=65536,strict=True)
    queue_capacity: int=Field(default=1000,ge=1,le=1000,strict=True)


def load_config(model,path):
    if not path:return model()
    try:
        with Path(path).open("rb") as stream:
            content=stream.read(1024*1024+1)
        if len(content)>1024*1024:raise ValueError()
        return model.model_validate_json(content)
    except (OSError,ValueError):
        raise ValueError("Configuração local indisponível ou inválida.") from None


def load_http_config(path=None):
    return load_config(HTTPConfig,path if path is not None else os.getenv("HTTP_CONFIG_FILE",""))


def load_smtp_config(path=None):
    return load_config(SMTPConfig,path if path is not None else os.getenv("SMTP_CONFIG_FILE",""))
