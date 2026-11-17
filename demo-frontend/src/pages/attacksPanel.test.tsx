import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Attack, QueueEntry, QueueSnapshot } from "../api";
import AttacksSection from "./AttacksSection";
import Panel from "./Panel";

const ataque: Attack = {
  id: "indisponibilidade-http",
  name: "Indisponibilidade do web-demo",
  target: "web-demo",
  description: "Modo offline via POST /mode; sondas HTTP falham.",
  params: [{ name: "duracao", type: "int", default: 45, min: 20, max: 120 }],
  expected_alerts: ["HTTPIndisponivel"],
};

const entrada: QueueEntry = {
  entry_id: "e1",
  attack: "indisponibilidade-http",
  status: "executando",
  params: { duracao: 45 },
  expected_alerts: ["HTTPIndisponivel"],
  counters: { segundos_restantes: 30 },
  verification: null,
  error: null,
  started_at: null,
  ended_at: null,
};

const fila: QueueSnapshot = { current: entrada, queue: [], history: [] };

describe("navegação do painel", () => {
  it("oferece aba de simulação de ataques junto ao serviço", () => {
    const markup = renderToStaticMarkup(createElement(Panel));
    expect(markup).toContain("Simulação de ataques");
    expect(markup).toContain("Serviço");
  });
});

describe("seção de ataques", () => {
  it("mostra cartões do catálogo com parâmetros e botão iniciar", () => {
    const markup = renderToStaticMarkup(
      createElement(AttacksSection, {
        attacks: [ataque],
        queue: null,
        busyId: null,
        events: [],
        onStart: () => {},
        onCancel: () => {},
      }),
    );
    expect(markup).toContain("Indisponibilidade do web-demo");
    expect(markup).toContain("duracao");
    expect(markup).toContain('value="45"');
    expect(markup).toContain("Iniciar");
    expect(markup).toContain("HTTPIndisponivel");
  });

  it("mostra fila em execução com fase, contadores e interrupção", () => {
    const markup = renderToStaticMarkup(
      createElement(AttacksSection, {
        attacks: [ataque],
        queue: fila,
        busyId: null,
        events: [],
        onStart: () => {},
        onCancel: () => {},
      }),
    );
    expect(markup).toContain("Executando");
    expect(markup).toContain("segundos_restantes");
    expect(markup).toContain("Interromper");
  });

  it("mostra resultado da verificação no histórico", () => {
    const concluido: QueueSnapshot = {
      current: null,
      queue: [],
      history: [
        { ...entrada, status: "concluido", verification: { available: true, fired: ["HTTPIndisponivel"], missing: [] } },
      ],
    };
    const markup = renderToStaticMarkup(
      createElement(AttacksSection, {
        attacks: [ataque],
        queue: concluido,
        busyId: null,
        events: [],
        onStart: () => {},
        onCancel: () => {},
      }),
    );
    expect(markup).toContain("Disparou: HTTPIndisponivel");
    expect(markup).toContain("Concluído");
  });
});
