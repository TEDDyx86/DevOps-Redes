import type { Window } from "./types";

export type ResourceValues = { cpu_cores: number | null; memory_bytes: number | null;
  memory_total_bytes: number | null; engine_memory_limit_bytes: number | null;
  read_bps: number | null; write_bps: number | null };
export interface ResourceService {
  id: string; name: string; status: "ok" | "warning" | "partial" | "unknown";
  available: boolean; reason: string | null; observed_at: number | null;
  container_id: string | null; started_at: string | null; values: ResourceValues;
  budgets: { cpu_cores: number; memory_bytes: number; io_bps: number };
}
export interface ResourceOverview {
  generated_at: number; service: string; window: Window; history_available: boolean;
  services: ResourceService[];
  host: { available: boolean; free_bytes: number | null; total_bytes: number | null };
  series: { timestamp: number; cpu_cores: number | null; memory_bytes: number | null;
    read_bps: number | null; write_bps: number | null }[];
}

export function currentResources(data: ResourceOverview, now: number): ResourceOverview {
  const fresh = (at: number | null) => at !== null && Number.isFinite(at) && now - at >= -5 && now - at <= 20;
  return {...data, services: data.services.map(row => fresh(data.generated_at) && fresh(row.observed_at) ? row : {
    ...row, status: "unknown", available: false, reason: "expired",
    values: {cpu_cores: null, memory_bytes: null, memory_total_bytes: null,
      engine_memory_limit_bytes: null, read_bps: null, write_bps: null},
  })};
}
