"""Conexões ativas HTTP no demo (Gauge demo_http_requests_inflight)."""
import asyncio

import httpx
from fastapi.testclient import TestClient

from demo.config import HTTPConfig
from demo.main import create_demo


def valor_inflight(app):
    return app.state.registry.get_sample_value("demo_http_requests_inflight")


def test_gauge_existe_e_volta_a_zero_depois_das_requisicoes():
    app = create_demo("demo-secret")
    with TestClient(app) as client:
        client.get("/health")
        client.get("/work")
        client.get("/metrics")
    assert valor_inflight(app) == 0


def test_contagem_durante_requisicoes_concorrentes():
    config = HTTPConfig(work_delay_seconds=0.4)
    app = create_demo("demo-secret", runtime_config=config)
    peak = 0

    async def cenario():
        nonlocal peak
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://demo", trust_env=False) as client:
            async def uma():
                resposta = await client.get("/work")
                assert resposta.status_code == 200

            tarefa = asyncio.create_task(uma())
            await asyncio.sleep(0.1)
            peak = valor_inflight(app)
            await tarefa

    asyncio.run(cenario())
    assert peak == 1
    assert valor_inflight(app) == 0
