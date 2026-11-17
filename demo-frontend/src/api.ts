export type Mode = "normal" | "slow" | "offline";

export interface WorkResult {
  message: string;
  timestamp: number;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export const api = {
  async health(): Promise<boolean> {
    try {
      const data = await requestJson<{ status: string }>("/health");
      return data.status === "ok";
    } catch {
      return false;
    }
  },
  mode(): Promise<{ mode: Mode }> {
    return requestJson<{ mode: Mode }>("/mode");
  },
  async setMode(mode: Mode, labToken: string): Promise<boolean> {
    const response = await fetch("/mode", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Lab-Token": labToken,
      },
      body: JSON.stringify({ mode }),
    });
    return response.ok;
  },
  work(): Promise<WorkResult> {
    return requestJson<WorkResult>("/work");
  },
  async metrics(): Promise<string> {
    const response = await fetch("/metrics");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.text();
  },
  async authenticated(): Promise<boolean> {
    try {
      const data = await requestJson<{ authenticated: boolean }>("/login");
      return data.authenticated;
    } catch {
      return false;
    }
  },
  async login(username: string, password: string): Promise<boolean> {
    const response = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    return response.ok;
  },
  async logout(): Promise<void> {
    const response = await fetch("/logout", { method: "POST" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
  },
};

export function navigate(path: string): void {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}
