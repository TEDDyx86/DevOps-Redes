import { useCallback, useEffect, useMemo, useState } from "react";
import {
  api,
  type StoreOrder,
  type StoreProduct,
  type StoreStatus,
} from "../api";
import hero8Bit from "../assets/hero-8bit.jpg";
import realCartridge from "../assets/real-cartridge.jpg";
import realCloud3 from "../assets/real-cloud3.jpg";
import realDualsense from "../assets/real-dualsense.jpg";
import realGprox2 from "../assets/real-gprox2.jpg";
import realKeychron from "../assets/real-keychron.jpg";
import realRg35xx from "../assets/real-rg35xx.jpg";
import realRtx4070 from "../assets/real-rtx4070.jpg";
import realSn30pro from "../assets/real-sn30pro.jpg";
import realSsd990 from "../assets/real-ssd990.jpg";
import realSteamdeck from "../assets/real-steamdeck.jpg";
import realSwitchOled from "../assets/real-switch-oled.jpg";
import realUltragear from "../assets/real-ultragear.jpg";

const PRODUCT_IMAGES: Record<string, string> = {
  steamdeck: realSteamdeck,
  switcholed: realSwitchOled,
  rg35xx: realRg35xx,
  sn30pro: realSn30pro,
  dualsense: realDualsense,
  keychron: realKeychron,
  gprox2: realGprox2,
  cloud3: realCloud3,
  ultragear: realUltragear,
  rtx4070: realRtx4070,
  ssd990: realSsd990,
  cartridge: realCartridge,
};

const CATEGORIES = [
  "Todas",
  "Consoles",
  "Controles",
  "Periféricos",
  "Áudio",
  "Monitores",
  "Hardware",
  "Retrô",
] as const;

interface CartItem {
  product: StoreProduct;
  quantity: number;
}

function formatBrl(cents: number): string {
  return (cents / 100).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function statusPillClass(value: string | undefined): string {
  if (value === "ok" || value === "online") {
    return "border-emerald-400/70 bg-emerald-500/15 text-emerald-300";
  }
  if (value === "memory" || value === "disabled") {
    return "border-amber/70 bg-amber/15 text-amber";
  }
  return "border-magenta/70 bg-magenta/15 text-magenta";
}

function formatServiceLabel(value: string | undefined): string {
  if (!value) return "...";
  if (value === "ok") return "ONLINE";
  if (value === "memory") return "MEMÓRIA";
  if (value === "disabled") return "OFF";
  if (value === "down") return "FALHA";
  return value.toUpperCase();
}

export function Landing() {
  const [products, setProducts] = useState<StoreProduct[]>([]);
  const [orders, setOrders] = useState<StoreOrder[]>([]);
  const [status, setStatus] = useState<StoreStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [category, setCategory] = useState<string>("Todas");
  const [search, setSearch] = useState<string>("");
  const [selectedProduct, setSelectedProduct] = useState<StoreProduct | null>(null);

  const [cart, setCart] = useState<CartItem[]>([]);
  const [cartOpen, setCartOpen] = useState(false);

  const [customerName, setCustomerName] = useState("Player One");
  const [customerEmail, setCustomerEmail] = useState("player1@workbyte.local");
  const [checkoutBusy, setCheckoutBusy] = useState(false);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [lastOrder, setLastOrder] = useState<StoreOrder | null>(null);

  const refreshAll = useCallback(async () => {
    try {
      setLoadError(null);
      const [catalog, recentOrders, storeStatus] = await Promise.all([
        api.products(),
        api.orders(),
        api.storeStatus(),
      ]);
      setProducts(catalog);
      setOrders(recentOrders);
      setStatus(storeStatus);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Erro ao carregar loja.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  const filteredProducts = useMemo(() => {
    const q = search.trim().toLowerCase();
    return products.filter((item) => {
      if (category !== "Todas" && item.category !== category) return false;
      if (!q) return true;
      return (
        item.name.toLowerCase().includes(q) ||
        item.description.toLowerCase().includes(q) ||
        item.specs.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q)
      );
    });
  }, [products, category, search]);

  const cartCount = useMemo(
    () => cart.reduce((acc, entry) => acc + entry.quantity, 0),
    [cart],
  );

  const cartTotalCents = useMemo(
    () => cart.reduce((acc, entry) => acc + entry.product.price_cents * entry.quantity, 0),
    [cart],
  );

  const addToCart = (product: StoreProduct, qty = 1) => {
    if (product.stock <= 0) return;
    setCheckoutError(null);
    setCart((prev) => {
      const existing = prev.find((item) => item.product.slug === product.slug);
      if (existing) {
        return prev.map((item) =>
          item.product.slug === product.slug
            ? { ...item, quantity: Math.min(product.stock, item.quantity + qty) }
            : item,
        );
      }
      return [...prev, { product, quantity: Math.min(product.stock, qty) }];
    });
  };

  const updateCartQty = (slug: string, delta: number) => {
    setCart((prev) =>
      prev
        .map((item) =>
          item.product.slug === slug
            ? {
                ...item,
                quantity: Math.min(item.product.stock, item.quantity + delta),
              }
            : item,
        )
        .filter((item) => item.quantity > 0),
    );
  };

  const removeFromCart = (slug: string) => {
    setCart((prev) => prev.filter((item) => item.product.slug !== slug));
  };

  const handleCheckout = async (e: React.FormEvent) => {
    e.preventDefault();
    if (cart.length === 0 || checkoutBusy) return;
    setCheckoutBusy(true);
    setCheckoutError(null);
    try {
      const created = await api.createOrder({
        customer_name: customerName.trim(),
        customer_email: customerEmail.trim(),
        items: cart.map((entry) => ({
          slug: entry.product.slug,
          quantity: entry.quantity,
        })),
      });
      setLastOrder(created);
      setCart([]);
      await refreshAll();
    } catch (err) {
      setCheckoutError(err instanceof Error ? err.message : "Falha ao concluir pedido.");
    } finally {
      setCheckoutBusy(false);
    }
  };

  return (
    <div className="pixel-grid-bg min-h-screen bg-bg text-slate-100">
      {/* Arcade HUD Topbar */}
      <header className="sticky top-0 z-40 border-b-2 border-cyan/50 bg-[#05060f]/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="arcade-box-cyan flex h-10 w-10 items-center justify-center border-2 border-cyan bg-cyan/15 font-pixel text-xs text-cyan">
              8B
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="pixel-text-3d font-pixel text-sm tracking-wider text-white sm:text-base">
                  WORKBYTE
                </span>
                <span className="border-2 border-magenta bg-magenta/15 px-2 py-0.5 font-pixel text-[9px] text-magenta">
                  STORE
                </span>
              </div>
              <p className="mt-0.5 font-mono text-[11px] uppercase tracking-widest text-cyan/80">
                8-BIT GAMER SHOP · CONSOLES &amp; HARDWARE
              </p>
            </div>
          </div>

          {/* Live Arcade Hardware LEDs */}
          <div className="hidden items-center gap-2 md:flex">
            <span
              className={`border-2 px-2 py-1 font-mono text-[11px] uppercase ${statusPillClass(
                status?.http ?? "ok",
              )}`}
            >
              HTTP {formatServiceLabel(status?.http ?? "ok")}
            </span>
            <span
              className={`border-2 px-2 py-1 font-mono text-[11px] uppercase ${statusPillClass(
                status?.postgres,
              )}`}
            >
              PG {formatServiceLabel(status?.postgres)}
            </span>
            <span
              className={`border-2 px-2 py-1 font-mono text-[11px] uppercase ${statusPillClass(
                status?.smtp,
              )}`}
            >
              SMTP {formatServiceLabel(status?.smtp)}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setCartOpen(true)}
              className={`arcade-btn border-2 px-3 py-2 font-pixel text-[10px] ${
                cartCount > 0
                  ? "border-amber bg-amber/20 text-amber"
                  : "border-cyan/60 bg-cyan/10 text-cyan"
              }`}
            >
              MOCHILA [{cartCount}]
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-10 px-4 py-8 sm:px-6">
        {/* Hero Arcade Stage */}
        <section className="arcade-box-cyan relative overflow-hidden border-2 border-cyan/60 bg-panel">
          <div className="grid items-center gap-6 lg:grid-cols-12">
            <div className="space-y-5 p-6 sm:p-8 lg:col-span-6">
              <div className="inline-flex items-center gap-2 border-2 border-amber/80 bg-amber/15 px-3 py-1 font-pixel text-[9px] text-amber">
                <span>★ PLAYER 1 READY · {products.length || 12} ITENS NO CATÁLOGO</span>
              </div>

              <h1 className="pixel-text-cyan-3d font-pixel text-xl leading-relaxed text-white sm:text-2xl lg:text-[26px]">
                LEVEL UP NO SEU SETUP &amp; HOMELAB{" "}
                <span className="whitespace-nowrap text-cyan">8-BIT</span>
              </h1>

              <p className="font-mono text-sm leading-relaxed text-slate-300">
                Equipamentos reais para jogar e montar seu setup:{" "}
                <strong className="text-cyan">Consoles, Periféricos &amp; Hardware</strong> — Steam Deck OLED,
                Switch OLED, controles 8BitDo e Sony, GPUs RTX, SSDs NVMe e clássicos retrô. Cada pedido
                grava estoque real no PostgreSQL e dispara recibo SMTP no Mailpit.
              </p>

              <div className="flex flex-wrap gap-3 pt-1">
                <a
                  href="#catalogo"
                  className="arcade-btn border-2 border-cyan bg-cyan px-4 py-3 font-pixel text-[10px] text-bg hover:bg-cyan/90"
                >
                  EXPLORAR CATÁLOGO
                </a>
                <button
                  type="button"
                  onClick={() => setCartOpen(true)}
                  className="arcade-btn border-2 border-amber bg-panel px-4 py-3 font-pixel text-[10px] text-amber hover:bg-amber/15"
                >
                  CHECKOUT ({formatBrl(cartTotalCents)})
                </button>
              </div>

              {/* Mini HUD Stats */}
              <div className="grid grid-cols-3 gap-2 pt-2">
                <div className="border-2 border-panel-edge bg-bg/80 p-2.5">
                  <div className="font-mono text-[10px] uppercase text-slate-400">SKUs Ativos</div>
                  <div className="mt-1 font-pixel text-xs text-cyan">{products.length || 12}</div>
                </div>
                <div className="border-2 border-panel-edge bg-bg/80 p-2.5">
                  <div className="font-mono text-[10px] uppercase text-slate-400">Banco SQL</div>
                  <div className="mt-1 font-pixel text-xs text-emerald-300">
                    {formatServiceLabel(status?.postgres)}
                  </div>
                </div>
                <div className="border-2 border-panel-edge bg-bg/80 p-2.5">
                  <div className="font-mono text-[10px] uppercase text-slate-400">Pedidos</div>
                  <div className="mt-1 font-pixel text-xs text-magenta">{orders.length}</div>
                </div>
              </div>
            </div>

            <div className="relative h-full min-h-[260px] border-t-2 border-cyan/40 bg-[#070812] lg:col-span-6 lg:border-l-2 lg:border-t-0">
              <img
                src={hero8Bit}
                alt="Arcade Cyberpunk 8-bit Hardware Store"
                className="pixelated-art h-full w-full object-cover"
              />
              <div className="arcade-scanlines pointer-events-none absolute inset-0" />
              <div className="absolute bottom-3 right-3 border-2 border-magenta bg-bg/90 px-3 py-1 font-pixel text-[9px] text-magenta">
                BOSS LOOT · 16-BIT EDITION
              </div>
            </div>
          </div>
        </section>

        {/* Stage Select / Search & Categories */}
        <section id="catalogo" className="space-y-5">
          <div className="arcade-box border-2 border-panel-edge bg-panel p-4 sm:p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="font-pixel text-sm text-cyan sm:text-base">
                  CATÁLOGO DE LOOT ({filteredProducts.length}/{products.length})
                </h2>
                <p className="mt-1 font-mono text-xs text-slate-400">
                  Filtre por classe de equipamento ou busque por especificação técnica.
                </p>
              </div>

              <div className="w-full lg:w-80">
                <input
                  id="catalog-search"
                  name="catalog-search"
                  type="search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="BUSCAR CONSOLE, GPU, CONTROLE..."
                  className="w-full border-2 border-cyan/50 bg-bg px-3 py-2 font-mono text-xs text-white placeholder:text-slate-500 focus:border-magenta focus:outline-none"
                />
              </div>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              {CATEGORIES.map((cat) => {
                const active = category === cat;
                return (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setCategory(cat)}
                    className={`arcade-btn border-2 px-2.5 py-1.5 font-mono text-xs uppercase transition ${
                      active
                        ? "border-magenta bg-magenta/25 font-bold text-white"
                        : "border-panel-edge bg-bg text-slate-300 hover:border-cyan hover:text-cyan"
                    }`}
                  >
                    {cat}
                  </button>
                );
              })}
            </div>
          </div>

          {loadError && (
            <div className="arcade-box border-2 border-magenta bg-magenta/10 p-4 font-mono text-sm text-magenta">
              ERRO DE CARREGAMENTO: {loadError}
            </div>
          )}

          {loading ? (
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {Array.from({ length: 8 }).map((_, idx) => (
                <div
                  key={idx}
                  className="arcade-box h-80 animate-pulse border-2 border-panel-edge bg-panel"
                />
              ))}
            </div>
          ) : filteredProducts.length === 0 ? (
            <div className="arcade-box border-2 border-amber/60 bg-panel p-8 text-center font-mono text-sm text-amber">
              NENHUM ITEM ENCONTRADO PARA ESTE FILTRO. TENTE OUTRA CATEGORIA!
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {filteredProducts.map((product) => {
                const imageSrc = PRODUCT_IMAGES[product.image_key] ?? realSteamdeck;
                const soldOut = product.stock <= 0;
                return (
                  <article
                    key={product.slug}
                    className="arcade-box flex flex-col justify-between border-2 border-panel-edge bg-panel transition hover:border-cyan"
                  >
                    <div>
                      <div className="flex items-center justify-between border-b-2 border-panel-edge bg-bg px-3 py-2">
                        <span className="font-pixel text-[8px] uppercase text-cyan">
                          {product.category}
                        </span>
                        <span
                          className={`font-mono text-[11px] font-bold ${
                            soldOut ? "text-magenta" : "text-emerald-300"
                          }`}
                        >
                          {soldOut ? "ESGOTADO" : `QTD: ${product.stock}`}
                        </span>
                      </div>

                      <button
                        type="button"
                        onClick={() => setSelectedProduct(product)}
                        className="group relative block aspect-square w-full overflow-hidden border-b-2 border-panel-edge bg-[#0a0b14]"
                      >
                        <img
                          src={imageSrc}
                          alt={product.name}
                          className="h-full w-full object-cover transition duration-200 group-hover:scale-105"
                        />
                        <span className="absolute bottom-2 right-2 border border-cyan/60 bg-bg/85 px-2 py-0.5 font-mono text-[10px] text-cyan opacity-90 group-hover:border-magenta group-hover:text-magenta">
                          + DETALHES
                        </span>
                      </button>

                      <div className="space-y-2 p-4">
                        <h3 className="font-pixel text-[11px] leading-snug text-white">
                          {product.name}
                        </h3>
                        <p className="font-mono text-[11px] text-cyan/90">{product.specs}</p>
                        <p className="line-clamp-2 font-mono text-xs leading-relaxed text-slate-400">
                          {product.description}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between gap-2 border-t-2 border-panel-edge bg-bg/70 px-4 py-3">
                      <span className="font-pixel text-xs text-amber">
                        {formatBrl(product.price_cents)}
                      </span>

                      <button
                        type="button"
                        disabled={soldOut}
                        onClick={() => addToCart(product, 1)}
                        className="arcade-btn border-2 border-cyan bg-cyan/15 px-3 py-1.5 font-pixel text-[9px] text-cyan hover:bg-cyan hover:text-bg disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {soldOut ? "SEM LOOT" : "+ EQUIPAR"}
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        {/* Recent PostgreSQL Orders Ledger */}
        <section className="arcade-box-magenta border-2 border-magenta/50 bg-panel p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-panel-edge pb-4">
            <div>
              <h2 className="font-pixel text-xs text-magenta sm:text-sm">
                Últimos pedidos gravados no PostgreSQL
              </h2>
              <p className="mt-1 font-mono text-xs text-slate-400">
                Registro em tempo real das compras finalizadas com confirmação SMTP.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void refreshAll()}
              className="arcade-btn border-2 border-cyan/60 bg-bg px-3 py-1.5 font-mono text-xs text-cyan hover:border-cyan"
            >
              ATUALIZAR LOG
            </button>
          </div>

          {orders.length === 0 ? (
            <p className="py-6 text-center font-mono text-xs text-slate-400">
              NENHUM PEDIDO REGISTRADO AINDA. ADICIONE ITENS À MOCHILA PARA GERAR UM NOVO LOG!
            </p>
          ) : (
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {orders.slice(0, 6).map((order) => (
                <div
                  key={order.order_code}
                  className="border-2 border-panel-edge bg-bg p-3 font-mono text-xs"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-pixel text-[10px] text-amber">{order.order_code}</span>
                    <span
                      className={`border px-2 py-0.5 text-[10px] ${
                        order.email_sent
                          ? "border-emerald-400/60 bg-emerald-500/15 text-emerald-300"
                          : "border-amber/60 bg-amber/15 text-amber"
                      }`}
                    >
                      {order.email_sent ? "SMTP OK" : "SMTP PENDENTE"}
                    </span>
                  </div>
                  <div className="mt-2 text-slate-200">
                    {order.customer_name} &lt;{order.customer_email}&gt;
                  </div>
                  <div className="mt-1 flex items-center justify-between text-slate-400">
                    <span>
                      {order.items.map((it) => `${it.quantity}x ${it.name}`).join(" · ")}
                    </span>
                    <span className="font-bold text-cyan">{formatBrl(order.total_cents)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>

      {/* Product Detail Modal */}
      {selectedProduct && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
          onClick={() => setSelectedProduct(null)}
        >
          <div
            className="arcade-box-cyan w-full max-w-2xl border-2 border-cyan bg-panel p-5 sm:p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4 border-b-2 border-panel-edge pb-3">
              <div>
                <span className="font-pixel text-[9px] text-magenta">
                  CLASSE: {selectedProduct.category}
                </span>
                <h3 className="mt-1 font-pixel text-sm text-white sm:text-base">
                  {selectedProduct.name}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedProduct(null)}
                className="arcade-btn border-2 border-slate-600 bg-bg px-2.5 py-1 font-pixel text-[10px] text-slate-300 hover:border-magenta hover:text-magenta"
              >
                X
              </button>
            </div>

            <div className="mt-4 grid gap-5 sm:grid-cols-2">
              <div className="aspect-square overflow-hidden border-2 border-panel-edge bg-[#0a0b14]">
                <img
                  src={PRODUCT_IMAGES[selectedProduct.image_key] ?? realSteamdeck}
                  alt={selectedProduct.name}
                  className="h-full w-full object-cover"
                />
              </div>

              <div className="flex flex-col justify-between space-y-4">
                <div className="space-y-3">
                  <div className="border-2 border-cyan/40 bg-bg px-3 py-2 font-mono text-xs text-cyan">
                    {selectedProduct.specs}
                  </div>
                  <p className="font-mono text-xs leading-relaxed text-slate-300">
                    {selectedProduct.description}
                  </p>
                  <div className="font-mono text-xs text-emerald-300">
                    ESTOQUE DISPONÍVEL: {selectedProduct.stock} UNIDADES
                  </div>
                </div>

                <div className="space-y-3 border-t-2 border-panel-edge pt-4">
                  <div className="font-pixel text-base text-amber">
                    {formatBrl(selectedProduct.price_cents)}
                  </div>
                  <button
                    type="button"
                    disabled={selectedProduct.stock <= 0}
                    onClick={() => {
                      addToCart(selectedProduct, 1);
                      setSelectedProduct(null);
                      setCartOpen(true);
                    }}
                    className="arcade-btn w-full border-2 border-cyan bg-cyan px-4 py-3 font-pixel text-[10px] text-bg hover:bg-cyan/90 disabled:opacity-40"
                  >
                    EQUIPAR NA MOCHILA
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Cart & Checkout Drawer */}
      {cartOpen && (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-black/75 backdrop-blur-sm"
          onClick={() => setCartOpen(false)}
        >
          <aside
            className="flex h-full w-full max-w-md flex-col justify-between border-l-2 border-amber bg-panel p-5 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="space-y-4 overflow-y-auto pr-1">
              <div className="flex items-center justify-between border-b-2 border-panel-edge pb-3">
                <h2 className="font-pixel text-xs text-amber sm:text-sm">
                  MOCHILA DE INVENTÁRIO ({cartCount})
                </h2>
                <button
                  type="button"
                  onClick={() => setCartOpen(false)}
                  className="arcade-btn border-2 border-slate-600 bg-bg px-2.5 py-1 font-pixel text-[10px] text-slate-300"
                >
                  X
                </button>
              </div>

              {lastOrder && (
                <div className="arcade-box-cyan border-2 border-emerald-400 bg-emerald-500/10 p-3 font-mono text-xs text-emerald-200">
                  <div className="font-pixel text-[10px] text-emerald-300">
                    QUEST CONCLUÍDA: {lastOrder.order_code}
                  </div>
                  <p className="mt-1">
                    Pedido salvo no PostgreSQL!{" "}
                    {lastOrder.email_sent
                      ? "Recibo enviado via SMTP para o Mailpit (:8026)."
                      : "SMTP indisponível no momento."}
                  </p>
                </div>
              )}

              {cart.length === 0 ? (
                <div className="border-2 border-panel-edge bg-bg p-6 text-center font-mono text-xs text-slate-400">
                  SUA MOCHILA ESTÁ VAZIA. SELECIONE ITENS NO CATÁLOGO 8-BIT!
                </div>
              ) : (
                <div className="space-y-3">
                  {cart.map((entry) => (
                    <div
                      key={entry.product.slug}
                      className="flex items-center gap-3 border-2 border-panel-edge bg-bg p-3"
                    >
                      <img
                        src={PRODUCT_IMAGES[entry.product.image_key] ?? realSteamdeck}
                        alt={entry.product.name}
                        className="h-14 w-14 border border-cyan/40 object-cover"
                      />
                      <div className="min-w-0 flex-1">
                        <div className="truncate font-pixel text-[9px] text-white">
                          {entry.product.name}
                        </div>
                        <div className="mt-1 font-mono text-xs text-amber">
                          {formatBrl(entry.product.price_cents * entry.quantity)}
                        </div>
                        <div className="mt-2 flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => updateCartQty(entry.product.slug, -1)}
                            className="border border-slate-600 bg-panel px-2 py-0.5 font-mono text-xs text-white"
                          >
                            -
                          </button>
                          <span className="font-mono text-xs text-cyan">{entry.quantity}</span>
                          <button
                            type="button"
                            onClick={() => updateCartQty(entry.product.slug, 1)}
                            className="border border-slate-600 bg-panel px-2 py-0.5 font-mono text-xs text-white"
                          >
                            +
                          </button>
                          <button
                            type="button"
                            onClick={() => removeFromCart(entry.product.slug)}
                            className="ml-auto font-mono text-[11px] text-magenta hover:underline"
                          >
                            REMOVER
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <form
              onSubmit={handleCheckout}
              className="mt-4 space-y-3 border-t-2 border-panel-edge pt-4"
            >
              <div className="flex items-center justify-between font-pixel text-xs">
                <span className="text-slate-300">TOTAL</span>
                <span className="text-amber">{formatBrl(cartTotalCents)}</span>
              </div>

              <input
                type="text"
                required
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="Nome do jogador / cliente"
                className="w-full border-2 border-panel-edge bg-bg px-3 py-2 font-mono text-xs text-white focus:border-cyan focus:outline-none"
              />
              <input
                type="email"
                required
                value={customerEmail}
                onChange={(e) => setCustomerEmail(e.target.value)}
                placeholder="E-mail para recibo SMTP"
                className="w-full border-2 border-panel-edge bg-bg px-3 py-2 font-mono text-xs text-white focus:border-cyan focus:outline-none"
              />

              {checkoutError && (
                <div className="border-2 border-magenta bg-magenta/10 px-3 py-2 font-mono text-xs text-magenta">
                  {checkoutError}
                </div>
              )}

              <button
                type="submit"
                disabled={cart.length === 0 || checkoutBusy}
                className="arcade-btn w-full border-2 border-magenta bg-magenta px-4 py-3 font-pixel text-[10px] text-white hover:bg-magenta/90 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {checkoutBusy ? "GRAVANDO PEDIDO..." : "FINALIZAR COMPRA"}
              </button>
            </form>
          </aside>
        </div>
      )}
    </div>
  );
}

export default Landing;
