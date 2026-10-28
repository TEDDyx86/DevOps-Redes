let csrfToken: string | null = null;

export function setCSRFToken(token: string | null) {
  csrfToken = token;
}

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const deadline = AbortSignal.timeout(8000);
  const signal = options.signal
    ? AbortSignal.any([options.signal, deadline])
    : deadline;
  let response: Response;
  const headers = new Headers(options.headers);
  if (
    csrfToken &&
    !["GET", "HEAD", "OPTIONS"].includes(
      (options.method ?? "GET").toUpperCase(),
    )
  )
    headers.set("X-CSRF-Token", csrfToken);
  try {
    response = await fetch(path, {
      ...options,
      credentials: "same-origin",
      headers,
      signal,
    });
  } catch (error) {
    if (deadline.aborted)
      throw new Error(
        "A plataforma não respondeu em 8 segundos. Verifique a conexão com o laboratório.",
      );
    if (error instanceof TypeError)
      throw new Error(
        "Sem conexão com a plataforma. Verifique se o laboratório está executando.",
      );
    throw error;
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    if (
      response.status === 401 &&
      body?.code === "session_required" &&
      !path.startsWith("/api/auth/") &&
      typeof window !== "undefined"
    )
      window.dispatchEvent(new Event("session-expired"));
    throw new APIError(
      typeof body?.detail === "string"
        ? body.detail
        : `Não foi possível concluir a solicitação (${response.status}).`,
      response.status,
    );
  }
  return response.json() as Promise<T>;
}

export function formatMetric(
  value: number | null | undefined,
  digits = 1,
): string {
  return value == null || !Number.isFinite(value)
    ? "—"
    : value.toLocaleString("pt-BR", {
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      });
}
