import { describe, expect, it } from "vitest";
import { statusLabel, verificationLine } from "./attacksView";

describe("rótulos de fase da fila", () => {
  it("traduz os estados do motor para o painel", () => {
    expect(statusLabel("agendado")).toBe("Agendado");
    expect(statusLabel("preparando")).toBe("Preparando");
    expect(statusLabel("executando")).toBe("Executando");
    expect(statusLabel("verificando")).toBe("Verificando");
    expect(statusLabel("concluido")).toBe("Concluído");
    expect(statusLabel("interrompido")).toBe("Interrompido");
    expect(statusLabel("interrompendo")).toBe("Interrompendo");
    expect(statusLabel("falhou")).toBe("Falhou");
  });

  it("estado desconhecido volta ao texto original", () => {
    expect(statusLabel("outro")).toBe("outro");
  });
});

describe("linha de verificação do alerta", () => {
  it("confirma quando o alerta disparou", () => {
    expect(
      verificationLine({ available: true, fired: ["DNSIndisponivel"], missing: [] }),
    ).toBe("Disparou: DNSIndisponivel");
  });

  it("avisa quando o alerta não disparou", () => {
    expect(
      verificationLine({ available: true, fired: [], missing: ["TrafegoAnormal"] }),
    ).toBe("Não disparou (verificar): TrafegoAnormal");
  });

  it("indica verificação indisponível quando o Prometheus falhou", () => {
    expect(
      verificationLine({ available: false, fired: [], missing: ["HTTPIndisponivel"] }),
    ).toBe("Verificação indisponível");
  });

  it("aguarda verificação enquanto o resultado não chegou", () => {
    expect(verificationLine(null)).toBe("Aguardando verificação");
  });
});
