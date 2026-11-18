"""Backend da Mini Loja Workbyte integrado ao PostgreSQL e ao servidor SMTP."""
import asyncio
import copy
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import make_msgid
import json
import logging
import os
import secrets
import smtplib
import threading

import psycopg


logger = logging.getLogger(__name__)

SEED_PRODUCTS = [
    {
        "slug": "steam-deck-oled-512",
        "name": "Valve Steam Deck OLED 512GB",
        "category": "Consoles",
        "description": "Console portátil PC com tela HDR OLED de 7,4\", bateria de longa duração e controles hápticos.",
        "specs": "7.4\" OLED 90Hz · 512GB NVMe · Wi-Fi 6E",
        "price_cents": 449900,
        "stock": 8,
        "image_key": "steamdeck",
    },
    {
        "slug": "nintendo-switch-oled",
        "name": "Nintendo Switch OLED Branco 64GB",
        "category": "Consoles",
        "description": "Console híbrido portátil e de mesa com tela OLED vibrante e dock com porta Ethernet RJ-45.",
        "specs": "Tela OLED 7\" · 64GB · Dock LAN RJ-45",
        "price_cents": 219900,
        "stock": 14,
        "image_key": "switcholed",
    },
    {
        "slug": "anbernic-rg35xx-plus",
        "name": "Anbernic RG35XX Plus Retrô 64GB",
        "category": "Consoles",
        "description": "Portátil retrô clássico para sistemas 8-bit, 16-bit e PS1 com Wi-Fi 5G e saída mini-HDMI.",
        "specs": "IPS 3.5\" 640x480 · Wi-Fi 5G · 3300mAh",
        "price_cents": 47900,
        "stock": 19,
        "image_key": "rg35xx",
    },
    {
        "slug": "8bitdo-sn30-pro",
        "name": "Controle 8BitDo SN30 Pro Bluetooth",
        "category": "Controles",
        "description": "Controle retrô clássico com analógicos Hall Effect, D-pad preciso e vibração rumble.",
        "specs": "Hall Effect · USB-C · Switch / PC / Android",
        "price_cents": 29900,
        "stock": 25,
        "image_key": "sn30pro",
    },
    {
        "slug": "dualsense-ps5-preto",
        "name": "Controle Sony DualSense Midnight Black",
        "category": "Controles",
        "description": "Controle oficial PlayStation 5 e PC com gatilhos adaptáveis e feedback háptico preciso.",
        "specs": "Gatilhos Adaptáveis · Háptico · USB-C",
        "price_cents": 44900,
        "stock": 21,
        "image_key": "dualsense",
    },
    {
        "slug": "keychron-k2-pro",
        "name": "Teclado Mecânico Keychron K2 Pro QMK",
        "category": "Periféricos",
        "description": "Teclado mecânico 75% sem fio programável via QMK/VIA com keycaps PBT double-shot e RGB.",
        "specs": "75% Hot-Swap · Keycaps PBT · BT 5.1 / Cabo",
        "price_cents": 78900,
        "stock": 15,
        "image_key": "keychron",
    },
    {
        "slug": "logitech-g-pro-x2",
        "name": "Mouse Logitech G Pro X Superlight 2",
        "category": "Periféricos",
        "description": "Mouse gamer sem fio ultraleve para esports com sensor HERO 2 e switches LIGHTFORCE.",
        "specs": "HERO 2 32K DPI · 60g · LIGHTSPEED 4000Hz",
        "price_cents": 89900,
        "stock": 17,
        "image_key": "gprox2",
    },
    {
        "slug": "hyperx-cloud-iii-wl",
        "name": "Headset HyperX Cloud III Wireless",
        "category": "Áudio",
        "description": "Headset sem fio com arco em alumínio, memory foam e microfone destacável com cancelamento.",
        "specs": "Drivers 53mm · DTS:X · Bateria até 120h",
        "price_cents": 84900,
        "stock": 12,
        "image_key": "cloud3",
    },
    {
        "slug": "lg-ultragear-oled-27",
        "name": "Monitor LG UltraGear OLED 27\" QHD",
        "category": "Monitores",
        "description": "Monitor gamer OLED antirreflexo 240Hz com tempo de resposta de 0,03ms e G-SYNC.",
        "specs": "27\" QHD OLED · 240Hz · 0.03ms GtG",
        "price_cents": 529900,
        "stock": 5,
        "image_key": "ultragear",
    },
    {
        "slug": "rtx-4070-super-asus",
        "name": "Placa de Vídeo ASUS Dual RTX 4070 Super",
        "category": "Hardware",
        "description": "GPU Ada Lovelace para jogos em 1440p no máximo com DLSS 3.5, Ray Tracing e dual fan.",
        "specs": "12GB GDDR6X · DLSS 3.5 · Axial-tech",
        "price_cents": 439900,
        "stock": 6,
        "image_key": "rtx4070",
    },
    {
        "slug": "ssd-samsung-990-pro-2tb",
        "name": "SSD NVMe Samsung 990 PRO 2TB M.2",
        "category": "Hardware",
        "description": "SSD PCIe 4.0 x4 de altíssima velocidade para loadings instantâneos em PC e PS5.",
        "specs": "PCIe 4.0 · Leitura 7450 MB/s · M.2 2280",
        "price_cents": 124900,
        "stock": 22,
        "image_key": "ssd990",
    },
    {
        "slug": "cartucho-zelda-alttp-16bit",
        "name": "Zelda: A Link to the Past (Ed. Colecionador)",
        "category": "Retrô",
        "description": "Cartucho clássico 16-bit revisado com bateria de save nova, label preservada e case acrílico.",
        "specs": "SNES 16-Bit · Bateria CR2032 Nova · Case",
        "price_cents": 38900,
        "stock": 9,
        "image_key": "cartridge",
    },
]


class StoreUnavailableError(RuntimeError):
    """Raised when the backing PostgreSQL database cannot be reached."""


class ProductNotFoundError(LookupError):
    """Raised when a requested product slug does not exist."""


class StockConflictError(ValueError):
    """Raised when requested quantity exceeds available stock."""


def format_brl(cents: int) -> str:
    reais = cents / 100
    formatted = f"{reais:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def send_order_confirmation_email(
    host: str,
    port: int,
    order_code: str,
    customer_name: str,
    customer_email: str,
    items: list[dict],
    total_cents: int,
) -> bool:
    lines = [
        f"Pedido {order_code} confirmado na Workbyte Store!",
        "",
        f"Cliente: {customer_name} ({customer_email})",
        "",
        "Itens:",
        *[
            f"- {item['quantity']}x {item['name']} ({format_brl(item['price_cents'] * item['quantity'])})"
            for item in items
        ],
        "",
        f"Total: {format_brl(total_cents)}",
        "",
        "Mensagem enviada pelo serviço SMTP monitorado do laboratório AulaRedes.",
    ]
    message = EmailMessage()
    message["From"] = "loja@aularedes.test"
    message["To"] = "aluno@aularedes.test"
    message["Subject"] = f"Workbyte Store · Pedido {order_code} confirmado"
    message["Message-ID"] = make_msgid(domain="aularedes.test")
    message.set_content("\n".join(lines))
    try:
        with smtplib.SMTP(host, port, timeout=3) as client:
            client.send_message(message)
        return True
    except (OSError, smtplib.SMTPException):
        logger.warning("Não foi possível enviar confirmação do pedido %s via SMTP", order_code)
        return False


def _probe_smtp(host: str, port: int) -> bool:
    try:
        with smtplib.SMTP(host, port, timeout=1.5) as client:
            return client.ehlo()[0] == 250 and client.noop()[0] == 250
    except (OSError, smtplib.SMTPException):
        return False


class StoreBackend:
    def __init__(self, dsn: str | None = None, smtp_host: str | None = None, smtp_port: int = 2525):
        self.dsn = dsn if dsn is not None else os.getenv("POSTGRES_WORKLOAD_DSN", "").strip()
        self.smtp_host = smtp_host if smtp_host is not None else os.getenv("SMTP_HOST", "").strip()
        self.smtp_port = smtp_port
        self._lock = threading.Lock()
        self._memory_products = {row["slug"]: copy.deepcopy(row) for row in SEED_PRODUCTS}
        self._memory_orders: list[dict] = []

    async def _connect(self):
        return await psycopg.AsyncConnection.connect(
            self.dsn,
            connect_timeout=2,
            options="-c statement_timeout=2500",
        )

    async def list_products(self, category: str | None = None, query: str | None = None) -> list[dict]:
        cat = (category or "").strip()
        q = (query or "").strip().lower()
        if not self.dsn:
            with self._lock:
                items = [copy.deepcopy(item) for item in self._memory_products.values()]
            return [
                item
                for item in items
                if (not cat or cat == "Todas" or item["category"] == cat)
                and (not q or q in item["name"].lower() or q in item["description"].lower() or q in item["specs"].lower())
            ]

        sql = """
            SELECT slug, name, category, description, specs, price_cents, stock, image_key
            FROM store_products
            WHERE (%s = '' OR category = %s)
              AND (%s = '' OR lower(name) LIKE %s OR lower(description) LIKE %s OR lower(specs) LIKE %s)
            ORDER BY price_cents DESC
        """
        cat_filter = "" if not cat or cat == "Todas" else cat
        like = f"%{q}%"
        try:
            async with asyncio.timeout(3):
                async with await self._connect() as conn:
                    cursor = await conn.execute(sql, (cat_filter, cat_filter, q, like, like, like))
                    rows = await cursor.fetchall()
        except (psycopg.Error, OSError, TimeoutError) as error:
            raise StoreUnavailableError("Banco de dados PostgreSQL indisponível.") from error
        return [
            {
                "slug": row[0],
                "name": row[1],
                "category": row[2],
                "description": row[3],
                "specs": row[4],
                "price_cents": row[5],
                "stock": row[6],
                "image_key": row[7],
            }
            for row in rows
        ]

    async def get_product(self, slug: str) -> dict:
        if not self.dsn:
            with self._lock:
                item = self._memory_products.get(slug)
                if item is None:
                    raise ProductNotFoundError(slug)
                return copy.deepcopy(item)
        try:
            async with asyncio.timeout(3):
                async with await self._connect() as conn:
                    cursor = await conn.execute(
                        "SELECT slug, name, category, description, specs, price_cents, stock, image_key "
                        "FROM store_products WHERE slug = %s",
                        (slug,),
                    )
                    row = await cursor.fetchone()
        except (psycopg.Error, OSError, TimeoutError) as error:
            raise StoreUnavailableError("Banco de dados PostgreSQL indisponível.") from error
        if row is None:
            raise ProductNotFoundError(slug)
        return {
            "slug": row[0],
            "name": row[1],
            "category": row[2],
            "description": row[3],
            "specs": row[4],
            "price_cents": row[5],
            "stock": row[6],
            "image_key": row[7],
        }

    async def create_order(self, customer_name: str, customer_email: str, requested_items: list[dict]) -> dict:
        order_code = f"WB-{secrets.token_hex(3).upper()}"
        created_at = datetime.now(timezone.utc).isoformat()
        merged: dict[str, int] = {}
        for entry in requested_items:
            slug = entry["slug"]
            merged[slug] = merged.get(slug, 0) + entry["quantity"]

        if not self.dsn:
            with self._lock:
                resolved = []
                total = 0
                for slug, qty in merged.items():
                    product = self._memory_products.get(slug)
                    if product is None:
                        raise ProductNotFoundError(slug)
                    if product["stock"] < qty:
                        raise StockConflictError(f"Estoque insuficiente para {product['name']}.")
                for slug, qty in merged.items():
                    product = self._memory_products[slug]
                    product["stock"] -= qty
                    resolved.append(
                        {
                            "slug": slug,
                            "name": product["name"],
                            "price_cents": product["price_cents"],
                            "quantity": qty,
                        }
                    )
                    total += product["price_cents"] * qty
                email_sent = False
                if self.smtp_host:
                    email_sent = await asyncio.to_thread(
                        send_order_confirmation_email,
                        self.smtp_host,
                        self.smtp_port,
                        order_code,
                        customer_name,
                        customer_email,
                        resolved,
                        total,
                    )
                order = {
                    "order_code": order_code,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "total_cents": total,
                    "items": resolved,
                    "email_sent": email_sent,
                    "created_at": created_at,
                }
                self._memory_orders.insert(0, order)
                del self._memory_orders[25:]
                return copy.deepcopy(order)

        resolved = []
        total = 0
        try:
            async with asyncio.timeout(4):
                async with await self._connect() as conn:
                    async with conn.transaction():
                        for slug in sorted(merged):
                            qty = merged[slug]
                            cur = await conn.execute(
                                "SELECT name, price_cents, stock FROM store_products WHERE slug = %s FOR UPDATE",
                                (slug,),
                            )
                            row = await cur.fetchone()
                            if row is None:
                                raise ProductNotFoundError(slug)
                            name, price_cents, stock = row
                            if stock < qty:
                                raise StockConflictError(f"Estoque insuficiente para {name}.")
                            await conn.execute(
                                "UPDATE store_products SET stock = stock - %s WHERE slug = %s",
                                (qty, slug),
                            )
                            resolved.append(
                                {
                                    "slug": slug,
                                    "name": name,
                                    "price_cents": price_cents,
                                    "quantity": qty,
                                }
                            )
                            total += price_cents * qty
                        cur = await conn.execute(
                            "INSERT INTO store_orders (order_code, customer_name, customer_email, total_cents, items_json, email_sent) "
                            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING created_at",
                            (order_code, customer_name, customer_email, total, json.dumps(resolved), False),
                        )
                        ts_row = await cur.fetchone()
                        if ts_row and ts_row[0] is not None:
                            created_at = ts_row[0].astimezone(timezone.utc).isoformat()
        except (ProductNotFoundError, StockConflictError):
            raise
        except (psycopg.Error, OSError, TimeoutError) as error:
            raise StoreUnavailableError("Banco de dados PostgreSQL indisponível.") from error

        email_sent = False
        if self.smtp_host:
            email_sent = await asyncio.to_thread(
                send_order_confirmation_email,
                self.smtp_host,
                self.smtp_port,
                order_code,
                customer_name,
                customer_email,
                resolved,
                total,
            )
            if email_sent:
                try:
                    async with asyncio.timeout(3):
                        async with await self._connect() as conn:
                            await conn.execute(
                                "UPDATE store_orders SET email_sent = TRUE WHERE order_code = %s",
                                (order_code,),
                            )
                except (psycopg.Error, OSError, TimeoutError):
                    pass

        return {
            "order_code": order_code,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "total_cents": total,
            "items": resolved,
            "email_sent": email_sent,
            "created_at": created_at,
        }

    async def list_orders(self, limit: int = 12) -> list[dict]:
        if not self.dsn:
            with self._lock:
                return copy.deepcopy(self._memory_orders[:limit])
        try:
            async with asyncio.timeout(3):
                async with await self._connect() as conn:
                    cur = await conn.execute(
                        "SELECT order_code, customer_name, customer_email, total_cents, items_json, email_sent, created_at "
                        "FROM store_orders ORDER BY id DESC LIMIT %s",
                        (limit,),
                    )
                    rows = await cur.fetchall()
        except (psycopg.Error, OSError, TimeoutError) as error:
            raise StoreUnavailableError("Banco de dados PostgreSQL indisponível.") from error
        return [
            {
                "order_code": row[0],
                "customer_name": row[1],
                "customer_email": row[2],
                "total_cents": row[3],
                "items": json.loads(row[4]),
                "email_sent": bool(row[5]),
                "created_at": row[6].astimezone(timezone.utc).isoformat() if row[6] else None,
            }
            for row in rows
        ]

    async def status(self) -> dict:
        if not self.dsn:
            pg_state = "memory"
        else:
            try:
                async with asyncio.timeout(2):
                    async with await self._connect() as conn:
                        await conn.execute("SELECT 1")
                pg_state = "ok"
            except (psycopg.Error, OSError, TimeoutError):
                pg_state = "down"

        if not self.smtp_host:
            smtp_state = "disabled"
        else:
            smtp_ok = await asyncio.to_thread(_probe_smtp, self.smtp_host, self.smtp_port)
            smtp_state = "ok" if smtp_ok else "down"

        return {"postgres": pg_state, "smtp": smtp_state}
