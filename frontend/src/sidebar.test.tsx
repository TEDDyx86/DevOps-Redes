import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Bell, LayoutDashboard, Server } from "lucide-react";
import Sidebar from "./Sidebar";
import type { Page } from "./types";

const navigation = [
  { id: "overview" as Page, label: "Visão geral", icon: LayoutDashboard },
  { id: "service" as Page, label: "Serviço HTTP", icon: Server },
  { id: "incidents" as Page, label: "Incidentes", icon: Bell },
];

const base = {
  navigation,
  page: "overview" as Page,
  activeIncidents: 2,
  onToggle: () => {},
  onCloseMobile: () => {},
};

describe("menu lateral", () => {
  it("expandido mostra rótulos, área ativa e contador de incidentes", () => {
    const html = renderToStaticMarkup(
      <Sidebar {...base} collapsed={false} mobileOpen={false} />,
    );
    expect(html).toContain("Visão geral");
    expect(html).toContain("OBSERVABILIDADE");
    expect(html).toContain('aria-current="page"');
    expect(html).toContain(">2</span>");
    expect(html).toContain('aria-expanded="true"');
  });

  it("recolhido preserva ícones, área ativa e nome acessível", () => {
    const html = renderToStaticMarkup(
      <Sidebar {...base} collapsed={true} mobileOpen={false} />,
    );
    expect(html).toContain('aria-expanded="false"');
    expect(html).not.toContain("OBSERVABILIDADE");
    expect(html).toContain('title="Serviço HTTP"');
    expect(html).toContain('aria-label="Incidentes"');
    expect(html).toContain(">2</span>");
  });
});
