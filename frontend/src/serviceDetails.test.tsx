import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ServiceDetails } from "./components";
import type { Overview } from "./types";

const baseService: Overview["service"] = {
  id: "web-demo",
  name: "Aplicação HTTP",
  protocol: "HTTP",
  target: "web-demo:8001",
  status: "ok",
  checked_at: 1_700_000_000,
  latency_ms: 15,
  p95_ms: 25,
  rps: 3.5,
  error_percent: 0,
  availability_percent: 100,
  connections: 12,
  error_codes: {},
};

describe("detalhes do serviço HTTP", () => {
  it("exibe conexões ativas e códigos de erro quando disponíveis", () => {
    const html = renderToStaticMarkup(
      <ServiceDetails
        service={{
          ...baseService,
          connections: 12,
          error_codes: { "404": 2, "503": 5 },
        }}
        onTestFailure={() => {}}
      />,
    );
    expect(html).toContain("Conexões ativas");
    expect(html).toContain(">12<");
    expect(html).toContain("Códigos de erro (janela)");
    expect(html).toContain("404: 2");
    expect(html).toContain("503: 5");
  });

  it("exibe traço quando conexões e códigos estão ausentes", () => {
    const html = renderToStaticMarkup(
      <ServiceDetails
        service={{
          ...baseService,
          connections: null,
          error_codes: null,
        }}
        onTestFailure={() => {}}
      />,
    );
    expect(html).toContain("Conexões ativas");
    expect(html).toContain(">—<");
  });

  it("indica ausência de erros no período quando a contagem é vazia", () => {
    const html = renderToStaticMarkup(
      <ServiceDetails
        service={{
          ...baseService,
          connections: 0,
          error_codes: {},
        }}
        onTestFailure={() => {}}
      />,
    );
    expect(html).toContain(">0<");
    expect(html).toContain("Sem erros no período");
  });
});
