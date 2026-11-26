import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import Attacks, {
  acceptAttackEvent,
  collectNewHistoryIds,
  liveVerificationSummary,
  resolvedExpectedAlerts,
  statusLabel,
  verificationSummary,
  type QueueEntry,
} from "./Attacks";

describe("painel de ataques", () => {
  it("traduz estados e verificações do motor de ataques", () => {
    expect(statusLabel("executando")).toBe("Executando");
    expect(statusLabel("concluido")).toBe("Concluído");
    expect(
      verificationSummary({
        available: true,
        fired: ["HTTPLento"],
        missing: [],
      }),
    ).toBe("Disparou: HTTPLento");
    expect(
      verificationSummary({
        available: true,
        fired: [],
        missing: ["ConfiguracaoAlterada"],
      }),
    ).toBe("Não disparou: ConfiguracaoAlterada");
    expect(verificationSummary({ available: false, fired: [], missing: ["TrafegoAnormal"] })).toBe(
      "Prometheus indisponível durante a verificação",
    );
  });

  it("renderiza seções principais do catálogo, fila e histórico", () => {
    const html = renderToStaticMarkup(createElement(Attacks));
    expect(html).toContain("Fila de execução");
    expect(html).toContain("Catálogo de ataques");
    expect(html).toContain("Histórico recente");
    expect(html).toContain("Log de eventos ao vivo");
  });

  it("resolve alertas esperados dinâmicos por alvo em interrupcao-servico", () => {
    const interrupcao = {
      id: "interrupcao-servico",
      name: "Interrupção de serviço",
      target: "docker compose",
      description: "Para container.",
      params: [
        {
          name: "alvo",
          type: "str" as const,
          default: "dns",
          options: ["dns", "smtp", "web-demo", "postgres"],
        },
      ],
      expected_alerts: [],
      expected_alerts_by_target: {
        dns: ["DNSIndisponivel"],
        smtp: ["SMTPIndisponivel"],
        "web-demo": ["HTTPIndisponivel"],
        postgres: ["PostgreSQLIndisponivel"],
      },
    };
    expect(resolvedExpectedAlerts(interrupcao, {})).toEqual(["DNSIndisponivel"]);
    expect(resolvedExpectedAlerts(interrupcao, { alvo: "postgres" })).toEqual([
      "PostgreSQLIndisponivel",
    ]);

    const varredura = {
      id: "varredura-404",
      name: "Varredura de rotas",
      target: "web-demo (:8011)",
      description: "Erros 4xx.",
      params: [{ name: "requisicoes", type: "int" as const, default: 60 }],
      expected_alerts: [],
    };
    expect(resolvedExpectedAlerts(varredura, {})).toEqual([]);
  });

  it("detecta apenas entradas novas no histórico de ataques", () => {
    const mkEntry = (entry_id: string): QueueEntry => ({
      entry_id,
      attack: "varredura-404",
      status: "concluido",
      params: { requisicoes: 60 },
      expected_alerts: [],
      counters: { requisicoes: 60 },
      verification: { available: true, fired: [], missing: [] },
      error: null,
      started_at: "2026-11-24T11:00:00Z",
      ended_at: "2026-11-24T11:00:05Z",
    });

    const known = new Set(["a1", "a2"]);
    expect(collectNewHistoryIds(known, [mkEntry("a1"), mkEntry("a2")])).toEqual([]);
    expect(
      collectNewHistoryIds(known, [mkEntry("a1"), mkEntry("a2"), mkEntry("a3"), mkEntry("a3")]),
    ).toEqual(["a3"]);
  });

  it("ignora eventos SSE duplicados pelo seq durante reconexões", () => {
    const seen = new Set<number>();
    expect(acceptAttackEvent(seen, { seq: 1, type: "status", status: "concluido" })).toBe(true);
    expect(acceptAttackEvent(seen, { seq: 1, type: "status", status: "concluido" })).toBe(false);
    expect(acceptAttackEvent(seen, { seq: 2, type: "verification" })).toBe(true);
  });

  it("resume estado pending e firing em tempo real durante o ataque", () => {
    expect(
      liveVerificationSummary(
        { available: true, pending: ["HTTPLento"], fired: [], missing: [] },
        null,
      ),
    ).toEqual({
      tone: "warning",
      text: "Detectado no Prometheus (confirmando): HTTPLento",
    });
    expect(
      liveVerificationSummary(
        { available: true, pending: [], fired: ["HTTPLento"], missing: [] },
        null,
      ),
    ).toEqual({
      tone: "ok",
      text: "Alerta confirmado durante o ataque: HTTPLento",
    });
    expect(
      liveVerificationSummary(null, {
        available: true,
        fired: ["DNSIndisponivel"],
        missing: [],
      }),
    ).toEqual({
      tone: "ok",
      text: "Disparou: DNSIndisponivel",
    });
  });
});
