import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import IncidentsView from "./Incidents";
import type { Incident } from "./types";

const sample: Incident[] = [
  {
    fingerprint: "a",
    started_at: "2026-11-17T10:00:00Z",
    ended_at: null,
    name: "HTTPIndisponivel",
    summary: "Aplicação HTTP indisponível",
    description: "Sonda falhou",
    severity: "critical",
    service: "web-demo",
    status: "firing",
  },
  {
    fingerprint: "b",
    started_at: "2026-11-17T09:00:00Z",
    ended_at: "2026-11-17T09:05:00Z",
    name: "DNSLento",
    summary: "Resolução DNS lenta",
    description: "Acima de 100 ms",
    severity: "warning",
    service: "dns",
    status: "resolved",
    resolution_source: "alertmanager",
  },
  {
    fingerprint: "c",
    started_at: "2026-11-16T08:00:00Z",
    ended_at: null,
    name: "PostgreSQLIndisponivel",
    summary: "PostgreSQL indisponível",
    description: "Conexão recusada",
    severity: "critical",
    service: "postgres",
    status: "resolved",
    resolution_source: "later_resolved_event",
    resolution_evidence_ended_at: "2026-11-17T08:05:00Z",
  },
];

describe("página de incidentes", () => {
  it("exibe resumo por estado e filtros", () => {
    const html = renderToStaticMarkup(<IncidentsView incidents={sample} />);
    expect(html).toContain("Histórico de incidentes");
    expect(html).toContain("Todos (3)");
    expect(html).toContain("Ativos (1)");
    expect(html).toContain("Resolvidos (1)");
    expect(html).toContain("Reconciliados (1)");
    expect(html).toContain("HTTP (web-demo)");
  });
});
