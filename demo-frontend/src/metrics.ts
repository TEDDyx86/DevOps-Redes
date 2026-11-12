export interface RequestCounters {
  total: number;
  byStatus: Record<string, number>;
  work: number;
}

export function parseDemoCounters(text: string): RequestCounters {
  const byStatus: Record<string, number> = {};
  let total = 0;
  let work = 0;
  for (const line of text.split("\n")) {
    if (!line.startsWith("demo_http_requests_total{")) continue;
    const value = Number(line.slice(line.lastIndexOf("}") + 1).trim());
    if (!Number.isFinite(value)) continue;
    total += value;
    const path = /path="([^"]*)"/.exec(line)?.[1] ?? "";
    const status = /status="([^"]*)"/.exec(line)?.[1] ?? "";
    if (path === "/work") work += value;
    byStatus[status] = (byStatus[status] ?? 0) + value;
  }
  return { total, byStatus, work };
}
