import { describe, expect, it } from "vitest";
import { combinedStatus, currentService, servicePage } from "./serviceState";
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
  it("abre o detalhe correspondente ao serviço selecionado", () => {
    expect(servicePage("dns")).toBe("dns");
    expect(servicePage("postgres")).toBe("postgres");
    expect(servicePage("web-demo")).toBe("service");
    expect(servicePage("smtp")).toBe("smtp");
  });
  it("inclui DNS sem esconder falha ou ausência do terceiro serviço", () => {
    expect(combinedStatus(["ok", "ok", "critical"])).toBe("critical");
    expect(combinedStatus(["ok", "ok", "unknown"])).toBe("unknown");
    expect(combinedStatus(["ok", "ok", "ok"])).toBe("ok");
  });
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
