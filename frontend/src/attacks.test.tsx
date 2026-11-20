import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import Attacks, {
  resolvedExpectedAlerts,
  statusLabel,
  verificationSummary,
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
});
