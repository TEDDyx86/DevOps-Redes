import { afterEach, describe, expect, it } from "vitest";
import {
  readSidebarPreference,
  saveSidebarPreference,
} from "./sidebarPreference";

type Store = Record<string, string>;

function fakeWindow(store: Store) {
  return {
    localStorage: {
      getItem: (key: string) => (key in store ? store[key] : null),
      setItem: (key: string, value: string) => {
        store[key] = value;
      },
      removeItem: (key: string) => {
        delete store[key];
      },
    },
  };
}

const originalWindow = (globalThis as { window?: unknown }).window;

afterEach(() => {
  (globalThis as { window?: unknown }).window = originalWindow;
});

describe("preferência do menu lateral", () => {
  it("sem window, assume expandido e não falha ao salvar", () => {
    expect(readSidebarPreference()).toBe(false);
    expect(() => saveSidebarPreference(true)).not.toThrow();
  });

  it("persiste recolhido e volta ao expandido usando o armazenamento", () => {
    const store: Store = {};
    (globalThis as { window?: unknown }).window = fakeWindow(store);
    expect(readSidebarPreference()).toBe(false);
    saveSidebarPreference(true);
    expect(readSidebarPreference()).toBe(true);
    saveSidebarPreference(false);
    expect(readSidebarPreference()).toBe(false);
  });

  it("armazenamento indisponível é ignorado", () => {
    (globalThis as { window?: unknown }).window = { localStorage: null };
    expect(readSidebarPreference()).toBe(false);
    expect(() => saveSidebarPreference(true)).not.toThrow();
  });
});
