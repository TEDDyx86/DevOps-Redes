import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import Landing from "./Landing";

describe("landing pública", () => {
  it("apresenta a plataforma e o acesso ao painel sem dados operacionais", () => {
    const html = renderToStaticMarkup(<Landing onEnter={() => {}} />);
    expect(html).toContain("WORK");
    expect(html).toContain("Um ponto de observação.");
    expect(html).toContain("Acessar o painel");
    expect(html).not.toContain("Incidentes");
    expect(html).not.toContain('aria-current="page"');
  });
});
