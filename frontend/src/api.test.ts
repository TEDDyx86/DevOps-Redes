import { afterEach, describe, expect, it, vi } from "vitest";
import { formatMetric, request } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("métricas sem coleta", () => {
  it("diferencia zero medido de ausência de dados", () => {
    expect(formatMetric(null)).toBe("—");
    expect(formatMetric(undefined)).toBe("—");
    expect(formatMetric(NaN)).toBe("—");
    expect(formatMetric(0)).toBe("0,0");
  });

  it("encerra uma requisição sem resposta em vez de conservar o estado antigo", async () => {
    vi.stubGlobal(
      "fetch",
      (_path: string, options: RequestInit) =>
        new Promise((_resolve, reject) => {
          options.signal?.addEventListener("abort", () =>
            reject(options.signal?.reason),
          );
        }),
    );
    await expect(request("/api/overview")).rejects.toThrow("8 segundos");
  }, 10000);
});
