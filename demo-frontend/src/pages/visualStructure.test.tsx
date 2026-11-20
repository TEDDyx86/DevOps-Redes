import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import Landing from "./Landing";
import Panel from "./Panel";

describe("public storefront visual structure", () => {
  it("renders a clean production storefront without internal infra flags or attack buttons", () => {
    const markup = renderToStaticMarkup(createElement(Landing));

    expect(markup).toContain("WORKBYTE");
    expect(markup).toContain("STORE");
    expect(markup).toContain("Consoles, Periféricos &amp; Hardware");
    expect(markup).not.toContain("Painel / Ataques");
    expect(markup).not.toContain("TESTAR 404");
    expect(markup).not.toContain("PostgreSQL");
    expect(markup).not.toContain("SMTP");
    expect(markup).not.toContain("Mailpit");
    expect(markup).not.toContain("Banco SQL");
    expect(markup).not.toContain("HTTP ONLINE");
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
