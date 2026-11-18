import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import Attacks, { statusLabel, verificationSummary } from "./Attacks";

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
});
