import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api", () => {
  it("health returns true when status is ok", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ status: "ok" }), { status: 200 })));
    expect(await api.health()).toBe(true);
  });

  it("health returns false when the service is offline", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 503 })));
    expect(await api.health()).toBe(false);
  });

  it("login posts credentials and reports success", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ authenticated: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    expect(await api.login("admin", "monitor-pass")).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith("/login", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ username: "admin", password: "monitor-pass" }),
    }));
  });

  it("login reports failure on 401", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response('{"detail":"Credenciais inválidas"}', { status: 401 })));
    expect(await api.login("admin", "errada")).toBe(false);
  });

  it("authenticated falls back to false on network error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("offline"); }));
    expect(await api.authenticated()).toBe(false);
  });

  it("mode parses the current phase", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ mode: "slow" }), { status: 200 })));
    expect(await api.mode()).toEqual({ mode: "slow" });
  });

  it("setMode posts new mode with lab token", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ mode: "slow" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    expect(await api.setMode("slow", "test-token")).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith("/mode", expect.objectContaining({
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Lab-Token": "test-token",
      },
      body: JSON.stringify({ mode: "slow" }),
    }));
  });
});
