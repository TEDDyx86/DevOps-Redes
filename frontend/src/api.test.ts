import { afterEach, describe, expect, it, vi } from "vitest";
import { formatMetric, request, setCSRFToken } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("métricas sem coleta", () => {
  it("não encerra a sessão quando apenas o token do laboratório está errado", async () => {
    const page = new EventTarget();
    const expired = vi.fn();
    page.addEventListener("session-expired", expired);
    vi.stubGlobal("window", page);
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ detail: "Token inválido" }), {
            status: 401,
          }),
        )
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              detail: "Entre novamente",
              code: "session_required",
            }),
            { status: 401 },
          ),
        ),
    );
    await expect(
      request("/api/lab/mode", { method: "POST" }),
    ).rejects.toMatchObject({ status: 401 });
    expect(expired).not.toHaveBeenCalled();
    await expect(request("/api/incidents")).rejects.toMatchObject({
      status: 401,
    });
    expect(expired).toHaveBeenCalledOnce();
  });
  it("envia CSRF em mutações e distingue sessão expirada", async () => {
    const fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Entre novamente" }), {
        status: 401,
      }),
    );
    vi.stubGlobal("fetch", fetch);
    setCSRFToken("csrf-test");
    await expect(
      request("/api/lab/mode", { method: "POST" }),
    ).rejects.toMatchObject({ status: 401 });
    expect(
      new Headers(fetch.mock.calls[0][1].headers).get("X-CSRF-Token"),
    ).toBe("csrf-test");
    expect(fetch.mock.calls[0][1].credentials).toBe("same-origin");
    setCSRFToken(null);
  });
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
