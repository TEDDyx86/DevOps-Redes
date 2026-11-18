"""Testes dos endpoints da Mini Loja Workbyte (catálogo, pedidos, erros HTTP e métricas)."""
from fastapi.testclient import TestClient

from demo.main import create_demo
from demo.store import StoreBackend, StoreUnavailableError


class FailingStore(StoreBackend):
    async def list_products(self, category=None, query=None):
        raise StoreUnavailableError("Banco de dados PostgreSQL indisponível.")

    async def get_product(self, slug):
        raise StoreUnavailableError("Banco de dados PostgreSQL indisponível.")

    async def create_order(self, customer_name, customer_email, requested_items):
        raise StoreUnavailableError("Banco de dados PostgreSQL indisponível.")

    async def list_orders(self, limit=12):
        raise StoreUnavailableError("Banco de dados PostgreSQL indisponível.")


def test_store_catalog_checkout_and_error_metrics():
    app = create_demo("demo-secret", store=StoreBackend(dsn="", smtp_host=""))
    with TestClient(app) as client:
        catalog = client.get("/api/products")
        assert catalog.status_code == 200
        products = catalog.json()["products"]
        assert len(products) == 12
        first = products[0]

        missing = client.get("/api/products/produto-que-nao-existe")
        assert missing.status_code == 404

        order = client.post(
            "/api/orders",
            json={
                "customer_name": "Ana Rede",
                "customer_email": "ana@aularedes.test",
                "items": [{"slug": first["slug"], "quantity": 2}],
            },
        )
        assert order.status_code == 201
        created = order.json()
        assert created["order_code"].startswith("WB-")
        assert created["total_cents"] == first["price_cents"] * 2

        updated = client.get(f"/api/products/{first['slug']}").json()
        assert updated["stock"] == first["stock"] - 2

        orders = client.get("/api/orders").json()["orders"]
        assert orders[0]["order_code"] == created["order_code"]

        # Quantidade acima do estoque gera 409
        conflict = client.post(
            "/api/orders",
            json={
                "customer_name": "Ana Rede",
                "customer_email": "ana@aularedes.test",
                "items": [{"slug": first["slug"], "quantity": 20}],
            },
        )
        metrics = client.get("/metrics").text
        assert 'path="/api/products/{slug}",status="404"' in metrics
        assert 'path="/api/orders",status="201"' in metrics
        if first["stock"] - 2 < 20:
            assert conflict.status_code == 409
            assert 'path="/api/orders",status="409"' in metrics


def test_store_returns_503_when_postgres_is_down():
    app = create_demo("demo-secret", store=FailingStore(dsn="postgresql://unused", smtp_host=""))
    with TestClient(app) as client:
        assert client.get("/api/products").status_code == 503
        assert client.post(
            "/api/orders",
            json={
                "customer_name": "Ana",
                "customer_email": "ana@aularedes.test",
                "items": [{"slug": "steam-deck-oled-512", "quantity": 1}],
            },
        ).status_code == 503
        # /health e /work continuam independentes quando só o banco cai
        assert client.get("/health").status_code == 200
        assert client.get("/work").status_code == 200
