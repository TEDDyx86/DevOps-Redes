import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import Landing from "./Landing";
import Panel from "./Panel";

describe("public landing visual structure", () => {
  it("keeps a direct login path and removes simulated showcase sections", () => {
    const markup = renderToStaticMarkup(createElement(Landing));

    expect(markup).toContain("START / ENTRAR");
    expect(markup).toContain("Sinal do serviço");
    expect(markup).toContain("Métricas HTTP");
    expect(markup).not.toContain("POP-UPS &amp; DIÁLOGOS RETRÔ");
    expect(markup).not.toContain("RADAR &amp; CONSOLE VETORIAL");
    expect(markup).not.toContain("DESKTOP MONOCROMÁTICO");
  });
});

describe("authenticated panel visual structure", () => {
  it("shows observed service data without simulated telemetry", () => {
    const markup = renderToStaticMarkup(createElement(Panel));

    expect(markup).toContain("SINAL DO SERVIÇO");
    expect(markup).toContain("Executar /work");
    expect(markup).toContain("Distribuição por código HTTP");
    expect(markup).not.toContain("DISTRIBUIÇÃO DE FLUXO");
    expect(markup).not.toContain("RADAR DE SERVIÇOS");
    expect(markup).not.toContain("crt-scanlines");
  });
});
