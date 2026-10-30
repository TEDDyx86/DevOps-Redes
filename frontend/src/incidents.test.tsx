import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { IncidentsList } from "./components";
import type { Incident } from "./types";

const incident: Incident = {
  fingerprint: "same-alert", started_at: "2020-01-01T12:00:00Z", ended_at: null,
  name: "PostgreSQLIndisponivel", summary: "Banco indisponível", description: "Sonda SQL falhando",
  severity: "critical", service: "postgres", status: "firing",
};

describe("incidentes reconciliados", () => {
  it("identifica a inferência, sua evidência e o término original desconhecido", () => {
    const value = { ...incident, status: "resolved" as const, resolution_source: "later_resolved_event" as const,
      reconciled_at: "2020-01-03T12:00:00Z", resolution_evidence_started_at: "2020-01-02T12:00:00Z",
      resolution_evidence_ended_at: "2020-01-02T12:05:00Z" };
    const html = renderToStaticMarkup(<IncidentsList incidents={[value]} />);
    expect(html).toContain("Reconciliado");
    expect(html).toContain("Resolução confirmada por evento posterior em");
    expect(html).toContain("Término original não recebido.");
    expect(html).toContain("Banco indisponível");
    expect(html).not.toContain("Crítico</span>");
  });

  it("mantém a distinção entre alertas ativos e resoluções diretas", () => {
    const active = renderToStaticMarkup(<IncidentsList incidents={[incident]} />);
    const resolved = renderToStaticMarkup(<IncidentsList incidents={[{...incident, status: "resolved", ended_at: "2020-01-01T12:05:00Z"}]} />);
    expect(active).toContain("Crítico");
    expect(resolved).toContain("Resolvido");
    expect(active + resolved).not.toContain("Reconciliado");
    expect(active + resolved).not.toContain("Término original não recebido.");
  });
});
