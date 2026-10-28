export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const deadline = AbortSignal.timeout(8000);
  const signal = options.signal
    ? AbortSignal.any([options.signal, deadline])
    : deadline;
  let response: Response;
  try {
    response = await fetch(path, { ...options, signal });
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
    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : `Não foi possível concluir a solicitação (${response.status}).`,
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
