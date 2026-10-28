import { describe, expect, it } from "vitest";
import { combinedStatus, currentService } from "./serviceState";
import type { ServiceSummary } from "./types";

const service: ServiceSummary = {
  id: "postgres",
  name: "PostgreSQL",
  protocol: "SQL",
  target: "postgres:5432",
  status: "ok",
  checked_at: 99,
  latency_ms: 10,
  availability_percent: 100,
};

describe("serviços independentes na visão consolidada", () => {
  it("não deixa HTTP saudável esconder banco indisponível", () => {
    expect(combinedStatus(["ok", "critical"])).toBe("critical");
    expect(combinedStatus(["ok", "unknown"])).toBe("unknown");
    expect(combinedStatus(["ok", "warning"])).toBe("warning");
    expect(combinedStatus(["ok", "ok"])).toBe("ok");
  });
  it("expira o serviço individualmente sem apagar o outro", () => {
    const stale = currentService(service, 99, 130);
    expect(stale.status).toBe("unknown");
    expect(stale.latency_ms).toBeNull();
    expect(
      currentService({ ...service, checked_at: 129 }, 129, 130).status,
    ).toBe("ok");
  });
});
