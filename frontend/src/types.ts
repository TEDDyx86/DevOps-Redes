export type Status = "ok" | "warning" | "critical" | "unknown";
export type Window = "15m" | "1h" | "6h" | "24h";
export type Mode = "normal" | "slow" | "offline";
export type Page = "overview" | "service" | "postgres" | "incidents" | "lab";

export interface ServiceSummary {
  id: string;
  name: string;
  protocol: string;
  target: string;
  status: Status;
  checked_at: number | null;
  latency_ms: number | null;
  availability_percent: number | null;
}

export interface ChartSample {
  timestamp: number;
  rps?: number | null;
  qps?: number | null;
  latency_ms: number | null;
}

export interface PostgresOverview {
  window: Window;
  generated_at: number;
  service: ServiceSummary;
  stats: {
    available: boolean;
    connections: number | null;
    connection_limit: number | null;
    database_bytes: number | null;
    commits_per_second: number | null;
    rollbacks_per_second: number | null;
    qps: number | null;
  };
  series: ChartSample[];
}

export interface Overview {
  window: Window;
  generated_at: number;
  service: {
    id: string;
    name: string;
    protocol: string;
    target: string;
    status: Status;
    checked_at: number | null;
    latency_ms: number | null;
    p95_ms: number | null;
    rps: number | null;
    error_percent: number | null;
    availability_percent: number | null;
  };
  series: {
    timestamp: number;
    rps: number | null;
    latency_ms: number | null;
  }[];
}

export interface Incident {
  fingerprint: string;
  started_at: string;
  ended_at: string | null;
  name: string;
  summary: string;
  description: string;
  severity: string;
  service: string;
  status: "firing" | "resolved";
}
export interface Lab {
  mode: Mode | null;
  available: boolean;
  traffic_interval_seconds: number;
}
