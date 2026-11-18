import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import Landing from "./Landing";
import Panel from "./Panel";

describe("public storefront visual structure", () => {
  it("renders the mini store catalog shell without attack panel button", () => {
    const markup = renderToStaticMarkup(createElement(Landing));

    expect(markup).toContain("WORKBYTE");
    expect(markup).toContain("STORE");
    expect(markup).toContain("Consoles, Periféricos &amp; Hardware");
    expect(markup).not.toContain("Painel / Ataques");
    expect(markup).not.toContain("TESTAR 404");
    expect(markup).toContain("Últimos pedidos gravados no PostgreSQL");
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
