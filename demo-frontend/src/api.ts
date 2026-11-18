export type Mode = "normal" | "slow" | "offline";

export interface AttackParam {
  name: string;
  type: string;
  default: number | string;
  min?: number;
  max?: number;
  options?: string[];
}

export interface Attack {
  id: string;
  name: string;
  target: string;
  description: string;
  params: AttackParam[];
  expected_alerts: string[];
}

export interface QueueEntry {
  entry_id: string;
  attack: string;
  status: string;
  params: Record<string, number | string>;
  expected_alerts: string[];
  counters: Record<string, number>;
  verification: { available: boolean; fired: string[]; missing: string[] } | null;
  error: string | null;
  started_at: string | null;
  ended_at: string | null;
}

export interface QueueSnapshot {
  current: QueueEntry | null;
  queue: QueueEntry[];
  history: QueueEntry[];
}

export interface AttackEvent {
  seq: number;
  type: string;
  entry_id?: string;
  attack?: string;
  status?: string;
  message?: string;
  counters?: Record<string, number>;
  data?: { available: boolean; fired: string[]; missing: string[] };
  [key: string]: unknown;
}

export interface WorkResult {
  message: string;
  timestamp: number;
}

export interface StoreProduct {
  slug: string;
  name: string;
  category: string;
  description: string;
  specs: string;
  price_cents: number;
  stock: number;
  image_key: string;
}

export interface StoreOrderItem {
  slug: string;
  name: string;
  price_cents: number;
  quantity: number;
}

export interface StoreOrder {
  order_code: string;
  customer_name: string;
  customer_email: string;
  total_cents: number;
  items: StoreOrderItem[];
  email_sent: boolean;
  created_at: string | null;
}

export interface StoreStatus {
  http: string;
  postgres: "ok" | "down" | "memory" | string;
  smtp: "ok" | "down" | "disabled" | string;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export const api = {
  async health(): Promise<boolean> {
    try {
      const data = await requestJson<{ status: string }>("/health");
      return data.status === "ok";
    } catch {
      return false;
    }
  },
  mode(): Promise<{ mode: Mode }> {
    return requestJson<{ mode: Mode }>("/mode");
  },
  async setMode(mode: Mode, labToken: string): Promise<boolean> {
    const response = await fetch("/mode", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Lab-Token": labToken,
      },
      body: JSON.stringify({ mode }),
    });
    return response.ok;
  },
  work(): Promise<WorkResult> {
    return requestJson<WorkResult>("/work");
  },
  async metrics(): Promise<string> {
    const response = await fetch("/metrics");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.text();
  },
  async authenticated(): Promise<boolean> {
    try {
      const data = await requestJson<{ authenticated: boolean }>("/login");
      return data.authenticated;
    } catch {
      return false;
    }
  },
  async login(username: string, password: string): Promise<boolean> {
    const response = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    return response.ok;
  },
  async logout(): Promise<void> {
    const response = await fetch("/logout", { method: "POST" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
  },
  async storeStatus(): Promise<StoreStatus> {
    return requestJson<StoreStatus>("/api/store/status");
  },
  async products(category?: string, query?: string): Promise<StoreProduct[]> {
    const params = new URLSearchParams();
    if (category && category !== "Todas") params.set("category", category);
    if (query?.trim()) params.set("q", query.trim());
    const qs = params.toString();
    const data = await requestJson<{ products: StoreProduct[] }>(
      `/api/products${qs ? `?${qs}` : ""}`,
    );
    return data.products;
  },
  async product(slug: string): Promise<StoreProduct> {
    return requestJson<StoreProduct>(`/api/products/${encodeURIComponent(slug)}`);
  },
  async orders(): Promise<StoreOrder[]> {
    const data = await requestJson<{ orders: StoreOrder[] }>("/api/orders");
    return data.orders;
  },
  async createOrder(payload: {
    customer_name: string;
    customer_email: string;
    items: { slug: string; quantity: number }[];
  }): Promise<StoreOrder> {
    const response = await fetch("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const body = (await response.json()) as { detail?: string };
        if (body.detail) detail = body.detail;
      } catch {
        // fallback to HTTP status
      }
      throw new Error(detail);
    }
    return (await response.json()) as StoreOrder;
  },
  attacks(): Promise<Attack[]> {
    return requestJson<{ attacks: Attack[] }>("/api/attacks").then((data) => data.attacks);
  },
  queue(): Promise<QueueSnapshot> {
    return requestJson<QueueSnapshot>("/api/queue");
  },
  async startAttack(attackId: string, params: Record<string, string>): Promise<QueueEntry> {
    const response = await fetch(`/api/attacks/${encodeURIComponent(attackId)}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ params }),
    });
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        detail = (await response.json()).detail ?? detail;
      } catch {
        // corpo sem JSON: mantém o código HTTP
      }
      throw new Error(detail);
    }
    return (await response.json()) as QueueEntry;
  },
  async cancelAttack(entryId: string): Promise<QueueEntry> {
    const response = await fetch(`/api/queue/${encodeURIComponent(entryId)}/cancel`, { method: "POST" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return (await response.json()) as QueueEntry;
  },
  subscribeEvents(onEvent: (event: AttackEvent) => void): () => void {
    const source = new EventSource("/api/events");
    source.onmessage = (message) => {
      try {
        onEvent(JSON.parse(message.data) as AttackEvent);
      } catch {
        // evento malformado é ignorado
      }
    };
    return () => source.close();
  },
};

export function navigate(path: string): void {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}
