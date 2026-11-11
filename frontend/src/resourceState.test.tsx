import { describe, expect, it } from "vitest";
import { currentResources, type ResourceOverview } from "./resourceState";

const data: ResourceOverview = { generated_at: 1000, service: "postgres", window: "15m", history_available: true, series: [],
  host: { available: true, free_bytes: 3 * 1024 ** 3, total_bytes: 10 * 1024 ** 3 },
  services: [{ id: "postgres", name: "PostgreSQL", status: "ok", available: true, reason: null, observed_at: 1000,
    container_id: "a".repeat(64), started_at: "1970-01-01T00:00:01Z",
    values: { cpu_cores: 0, memory_bytes: 1024, memory_total_bytes: 2048, engine_memory_limit_bytes: 1e9, read_bps: 0, write_bps: 0 },
    budgets: { cpu_cores: .8, memory_bytes: 256 * 1024 ** 2, io_bps: 10 * 1024 ** 2 } }] };

describe("recursos atuais", () => {
  it("mantém zeros medidos e memória parcial", () => {
    expect(currentResources(data, 1001).services[0].values.cpu_cores).toBe(0);
    const partial = { ...data, services: [{...data.services[0], status: "partial" as const, values: {...data.services[0].values, cpu_cores: null}}] };
    expect(currentResources(partial, 1001).services[0].values.memory_bytes).toBe(1024);
  });
  it("expira resposta ou medição sem apagar o histórico", () => {
    const stale = currentResources(data, 1021);
    expect(stale.services[0].status).toBe("unknown");
    expect(Object.values(stale.services[0].values).every(v => v === null)).toBe(true);
    expect(stale.services[0].observed_at).toBe(1000);
    expect(stale.history_available).toBe(true);
    expect(currentResources({...data, generated_at: 1020}, 1021).services[0].values.cpu_cores).toBeNull();
  });
});
